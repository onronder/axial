"""
Integrations API Endpoints

Provides dynamic connector discovery, OAuth handling, and integration management.
"""

import inspect
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import UUID

import httpx
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.concurrency import run_in_threadpool
from google_auth_oauthlib.flow import Flow
from pydantic import BaseModel, Field

from api.v1.dependencies import (
    get_effective_plan,
    get_user_organization_id,
    require_editor,
    require_paid_access,
    validate_team_access,
)
from api.v1.error_utils import ApiErrorCode, api_error, raise_http_error
from connectors.base import ConnectorAuthError, ConnectorTransientError
from connectors.registry import get_connector_manifest
from connectors.s3 import S3Connector
from connectors.sftp import SFTPConnector
from connectors.web import WebConnector
from core.config import settings
from core.db import get_supabase
from core.exceptions import QuotaExceededError
from core.ingestion_utils import require_canonical_provider
from core.rate_limit import limiter
from core.scopes import extract_item_ids_from_scope, get_scope_prefixes
from core.security import decrypt_token, encrypt_token, get_current_user
from services.audit import audit_logger, log_connector_sync
from services.quotas import check_admission, increment_usage
from services.team_service import team_service
from services.usage import check_feature_access
from services.web_crawl import queue_web_crawl

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(validate_team_access), Depends(require_paid_access)])


def _require_provider(provider: str) -> str:
    try:
        canonical = require_canonical_provider(provider)
        manifest = get_connector_manifest(canonical)
        if not manifest:
            raise ValueError(f"Unknown provider: {provider}")
        return canonical
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Unknown or unsupported provider.") from exc  # ALLOWED: literal


def _get_ingest_batch_size() -> int:
    return max(1, getattr(settings, "INGEST_DISPATCH_BATCH_SIZE", 50))


# =============================================================================
# Pydantic Request/Response Models
# =============================================================================

class ExchangeRequest(BaseModel):
    """OAuth code exchange request with validation."""
    code: str = Field(..., min_length=1, max_length=2048)  # OAuth codes can be long


class ConnectorDefinitionOut(BaseModel):
    id: str
    type: str
    name: str
    description: str | None = None
    icon_path: str | None = None
    category: str | None = None
    is_active: bool = True


class UserIntegrationOut(BaseModel):
    id: str
    connector_definition_id: str
    connector_type: str
    connector_name: str
    connector_icon: str | None = None
    category: str | None = None
    connected: bool = True
    last_sync_at: datetime | None = None


class IngestRequest(BaseModel):
    """Ingestion request with validation."""
    item_ids: list[str] = Field(..., max_length=100)  # Max 100 items per request


class WebCrawlRequest(BaseModel):
    """Web crawl request with validation."""
    url: str = Field(..., min_length=1, max_length=2048)
    crawl_type: str = Field(default="single")
    max_depth: int = Field(default=1, ge=1, le=10)
    respect_robots: bool = Field(default=True)
    max_pages: int = Field(default=500, ge=1, le=10000)
    allow_subdomains: bool = Field(default=False)


class SFTPConnectRequest(BaseModel):
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(default=22, ge=1, le=65535)
    username: str = Field(..., min_length=1, max_length=128)
    password: str | None = Field(default=None, max_length=4096)
    private_key: str | None = Field(default=None, max_length=16384)
    root_path: str = Field(default="/", min_length=1, max_length=1024)


class S3ConnectRequest(BaseModel):
    """
    Amazon S3 connection request with IAM credentials.

    ENTERPRISE ONLY: This connector requires Enterprise plan.
    """
    access_key_id: str = Field(
        ...,
        min_length=16,
        max_length=128,
        description="AWS Access Key ID (typically 20 characters)"
    )
    secret_access_key: str = Field(
        ...,
        min_length=16,
        max_length=128,
        description="AWS Secret Access Key (typically 40 characters)"
    )
    region: str = Field(
        default="us-east-1",
        description="AWS region (e.g., us-east-1, eu-west-1)"
    )
    bucket_name: str = Field(
        ...,
        min_length=3,
        max_length=63,
        pattern=r"^[a-z0-9][a-z0-9.-]*[a-z0-9]$",
        description="S3 bucket name"
    )
    prefix: str = Field(
        ...,
        min_length=1,
        max_length=1024,
        description="Folder prefix to sync (e.g., 'documents/'). Required for cost protection."
    )


class MicrosoftExchangeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=2048)
    target_type: Literal["onedrive", "sharepoint"]
    site_id: str | None = Field(default=None, max_length=512)
    code_verifier: str | None = Field(default=None, max_length=256)


class WebCrawlConfigResponse(BaseModel):
    """Response model for web crawl configuration."""
    id: str
    root_url: str
    crawl_type: str
    status: str
    max_depth: int
    max_pages: int
    allow_subdomains: bool
    total_pages_found: int
    pages_ingested: int
    pages_failed: int
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    completed_at: datetime | None = None


class WebCrawlConfigListResponse(BaseModel):
    """Response model for listing web crawl configurations."""
    items: list[WebCrawlConfigResponse]
    total: int
    has_more: bool


async def _resolve_org_and_plan(user_id: str) -> tuple[str, str]:
    """
    Determine org_id (team or user) and plan code for quota enforcement.
    """
    team = await team_service.get_user_team(user_id)
    org_id = user_id
    plan_code = None
    if team:
        org_id = team.get("id") or user_id
        plan_code = team.get("plan")
    if not plan_code:
        plan_code = await team_service.get_effective_plan(user_id)
    return org_id, plan_code


# =============================================================================
# Dynamic Connector Discovery Endpoints
# =============================================================================

@router.get("/integrations/available", response_model=list[ConnectorDefinitionOut])
@limiter.limit("100/minute")
async def get_available_connectors(request: Request):
    """
    Returns all active connector definitions.
    Frontend uses this to dynamically render available integrations.
    """
    supabase = get_supabase()

    try:
        response = supabase.table("connector_definitions").select("*").eq("is_active", True).execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Failed to fetch connector definitions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch available connectors")  # ALLOWED: literal


@router.get("/integrations/status", response_model=list[UserIntegrationOut])
@limiter.limit("60/minute")
async def get_user_integrations(
    request: Request,
    user_id: str = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """
    Returns the user's connected integrations with definition details.
    Joins user_integrations with connector_definitions for rich response.
    """
    supabase = get_supabase()

    try:
        # Join user_integrations with connector_definitions
        response = supabase.table("user_integrations").select(
            "id, connector_definition_id, last_sync_at, "
            "connector_definitions(type, name, icon_path, category)"
        ).eq("user_id", user_id).range(offset, offset + limit - 1).execute()

        # Transform the joined response
        result = []
        for item in response.data or []:
            definition = item.get("connector_definitions", {}) or {}
            result.append({
                "id": item["id"],
                "connector_definition_id": item["connector_definition_id"],
                "connector_type": definition.get("type", "unknown"),
                "connector_name": definition.get("name", "Unknown"),
                "connector_icon": definition.get("icon_path"),
                "category": definition.get("category"),
                "connected": True,
                "last_sync_at": item.get("last_sync_at")
            })

        return result
    except Exception as e:
        logger.error(f"Failed to fetch user integrations: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch integrations")  # ALLOWED: literal


# =============================================================================
# OAuth Token Exchange (Fixed Persistence)
# =============================================================================

@router.post("/integrations/google/exchange")
@limiter.limit("10/minute")
async def exchange_google_token(
    request: Request,
    body: ExchangeRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(require_editor)
):
    """
    Exchange Google OAuth code for tokens and persist to user_integrations.
    Uses proper upsert with connector_definition_id FK.
    """
    logger.info(f"🔐 [OAuth] Starting Google token exchange for user: {user_id}")

    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        logger.error("🔐 [OAuth] Google credentials not configured!")
        raise HTTPException(status_code=500, detail="Google credentials not configured")  # ALLOWED: literal

    supabase = get_supabase()

    # 1. Look up connector_definition_id for google_drive
    try:
        def_response = supabase.table("connector_definitions").select("id").eq("type", "google_drive").single().execute()
        if not def_response.data:
            raise HTTPException(status_code=500, detail="google_drive connector not found in definitions")  # ALLOWED: literal
        connector_definition_id = def_response.data["id"]
        logger.info(f"🔐 [OAuth] Found connector_definition_id: {connector_definition_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🔐 [OAuth] Failed to lookup connector definition: {e}")
        raise HTTPException(status_code=500, detail="Failed to lookup connector definition")  # ALLOWED: literal

    # 2. Exchange Code for Tokens
    try:
        logger.info(f"🔐 [OAuth] Redirect URI: {settings.GOOGLE_REDIRECT_URI}")
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=['https://www.googleapis.com/auth/drive.readonly'],
            redirect_uri=settings.GOOGLE_REDIRECT_URI
        )

        flow.fetch_token(code=body.code)
        creds = flow.credentials
        logger.info(f"🔐 [OAuth] ✅ Got credentials. Has refresh token: {creds.refresh_token is not None}")

    except Exception as e:
        logger.error(f"🔐 [OAuth] ❌ Token exchange failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise api_error(ApiErrorCode.OAUTH_ERROR, e, "oauth_exchange")

    # 3. Calculate expiry
    try:
        if creds.expiry:
            expires_at = creds.expiry.isoformat()
        else:
            expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    except Exception as e:
        logger.warning(f"🔐 [OAuth] Could not set expiry: {e}")
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    # 4. Upsert to user_integrations using the unique constraint
    # Encrypt tokens before storage for security
    encrypted_access_token = encrypt_token(creds.token) if creds.token else None
    encrypted_refresh_token = encrypt_token(creds.refresh_token) if creds.refresh_token else None

    data = {
        "user_id": user_id,
        "connector_definition_id": connector_definition_id,
        "access_token": encrypted_access_token,
        "refresh_token": encrypted_refresh_token,
        "expires_at": expires_at,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        # Reset status on successful reconnection
        "status": "active",
        "status_message": None,
    }

    logger.info("🔐 [OAuth] Tokens encrypted before storage")

    logger.info(f"🔐 [OAuth] Upserting to user_integrations: user_id={user_id}, connector_def={connector_definition_id}")

    try:
        # Upsert: insert or update on conflict
        upsert_res = supabase.table("user_integrations").upsert(
            data,
            on_conflict="user_id,connector_definition_id"
        ).execute()

        if not upsert_res.data:
            logger.error("🔐 [OAuth] ❌ Upsert returned no data!")
            raise HTTPException(status_code=500, detail="Database upsert returned no data")  # ALLOWED: literal

        logger.info(f"🔐 [OAuth] ✅ Upsert successful for integration ID: {upsert_res.data[0]['id']}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🔐 [OAuth] ❌ Database error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "oauth_exchange")

    # NOTE: We no longer auto-sync on connect to prevent unexpected behavior.
    # User should explicitly select files/folders to ingest via the Drive explorer.
    # This prevents the issue of re-ingesting old files after reconnecting.
    #
    # OLD CODE REMOVED:
    # integration_id = upsert_res.data[0]["id"]
    # try:
    #     from connectors.drive import DriveConnector
    #     connector = DriveConnector()
    #     background_tasks.add_task(connector.sync, user_id, integration_id)
    #     logger.info(f"🔐 [OAuth] Scheduled background sync for integration {integration_id}")
    # except Exception as e:
    #     logger.warning(f"🔐 [OAuth] Failed to schedule sync: {e}")

    integration_id = upsert_res.data[0]["id"]

    audit_logger.log_sync(
        user_id=user_id,
        action="connector.connect",
        resource_type="connector",
        resource_id="google_drive",
        details={"integration_id": integration_id},
    )
    logger.info(f"🔐 [OAuth] Connected Google Drive (integration: {integration_id}). User can now select files to ingest.")

    return {"status": "success", "provider": "google_drive", "integration_id": integration_id}


@router.post("/integrations/notion/exchange")
@limiter.limit("10/minute")
async def exchange_notion_token(
    request: Request,
    body: ExchangeRequest,
    user_id: str = Depends(require_editor)
):
    """
    Exchange Notion OAuth code for tokens and persist to user_integrations.
    Uses httpx for async HTTP request to Notion API.
    """
    logger.info(f"🔐 [OAuth] Starting Notion token exchange for user: {user_id}")

    if not settings.NOTION_CLIENT_ID or not settings.NOTION_CLIENT_SECRET:
        logger.error("🔐 [OAuth] Notion credentials not configured!")
        raise HTTPException(status_code=500, detail="Notion credentials not configured")  # ALLOWED: literal

    if not settings.NOTION_REDIRECT_URI:
        logger.error("🔐 [OAuth] Notion redirect URI not configured!")
        raise HTTPException(status_code=500, detail="Notion redirect URI not configured")  # ALLOWED: literal

    supabase = get_supabase()

    # 1. Look up connector_definition_id for notion
    try:
        def_response = supabase.table("connector_definitions").select("id").eq("type", "notion").single().execute()
        if not def_response.data:
            raise HTTPException(status_code=500, detail="notion connector not found in definitions")  # ALLOWED: literal
        connector_definition_id = def_response.data["id"]
        logger.info(f"🔐 [OAuth] Found connector_definition_id: {connector_definition_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🔐 [OAuth] Failed to lookup connector definition: {e}")
        raise HTTPException(status_code=500, detail="Failed to lookup connector definition")  # ALLOWED: literal

    # 2. Exchange Code for Tokens using httpx
    try:
        logger.info(f"🔐 [OAuth] Redirect URI: {settings.NOTION_REDIRECT_URI}")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.notion.com/v1/oauth/token",
                auth=(settings.NOTION_CLIENT_ID, settings.NOTION_CLIENT_SECRET),
                json={
                    "grant_type": "authorization_code",
                    "code": body.code,
                    "redirect_uri": settings.NOTION_REDIRECT_URI
                },
                headers={
                    "Content-Type": "application/json"
                }
            )

            if response.status_code != 200:
                logger.error(f"🔐 [OAuth] ❌ Notion API error: {response.status_code} {response.text}")
                raise HTTPException(
                    status_code=400,
                    detail="Notion token exchange failed. Please try connecting again."
                )  # ALLOWED: literal

            token_data = response.json()
            access_token = token_data.get("access_token")
            workspace_id = token_data.get("workspace_id")
            workspace_name = token_data.get("workspace_name")
            bot_id = token_data.get("bot_id")

            logger.info(f"🔐 [OAuth] ✅ Got Notion tokens. Workspace: {workspace_name} ({workspace_id})")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🔐 [OAuth] ❌ Notion token exchange failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise api_error(ApiErrorCode.OAUTH_ERROR, e, "oauth_exchange")

    # 3. Encrypt and store token
    encrypted_access_token = encrypt_token(access_token) if access_token else None

    data = {
        "user_id": user_id,
        "connector_definition_id": connector_definition_id,
        "access_token": encrypted_access_token,
        "refresh_token": None,  # Notion doesn't use refresh tokens
        "expires_at": None,  # Notion tokens don't expire
        "credentials": {
            "workspace_id": workspace_id,
            "workspace_name": workspace_name,
            "bot_id": bot_id
        },
        "updated_at": datetime.now(timezone.utc).isoformat(),
        # Reset status on successful reconnection
        "status": "active",
        "status_message": None,
    }

    logger.info("🔐 [OAuth] Token encrypted before storage")
    logger.info(f"🔐 [OAuth] Upserting to user_integrations: user_id={user_id}, connector_def={connector_definition_id}")

    try:
        # Upsert: insert or update on conflict
        upsert_res = supabase.table("user_integrations").upsert(
            data,
            on_conflict="user_id,connector_definition_id"
        ).execute()

        if not upsert_res.data:
            logger.error("🔐 [OAuth] ❌ Upsert returned no data!")
            raise HTTPException(status_code=500, detail="Database upsert returned no data")  # ALLOWED: literal

        logger.info(f"🔐 [OAuth] ✅ Upsert successful for integration ID: {upsert_res.data[0]['id']}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🔐 [OAuth] ❌ Database error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "oauth_exchange")

    integration_id = upsert_res.data[0]["id"]

    # 4. Trigger auto-ingestion in background
    # Fetch all accessible pages and start ingestion immediately
    try:

        # Fetch all accessible pages to ingest
        items = []
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.notion.com/v1/search",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Notion-Version": "2022-06-28",
                    "Content-Type": "application/json"
                },
                json={"page_size": 100}
            )
            if response.status_code == 200:
                search_data = response.json()
                items = [p["id"] for p in search_data.get("results", []) if p.get("object") == "page"]

        if items:
            org_id, plan_code = await _resolve_org_and_plan(user_id)
            try:
                check_admission(
                    org_id=org_id,
                    plan_code=plan_code,
                    file_size_bytes=None,
                    job_count_increment=max(1, len(items)),
                )
            except QuotaExceededError as exc:
                logger.warning("🚫 Admission denied for Org %s: %s", org_id, exc)
                raise_http_error(
                    status.HTTP_403_FORBIDDEN,
                    "PLAN_LIMIT_EXCEEDED",
                    str(exc),
                    exc.details if isinstance(exc, QuotaExceededError) else None,
                )
            # Create ingestion job
            job_data = {
                "user_id": user_id,
                "organization_id": org_id,
                "provider": "notion",
                "total_files": len(items),
                "processed_files": 0,
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            job_response = supabase.table("ingestion_jobs").insert(job_data).execute()

            if job_response.data:
                job_id = job_response.data[0]["id"]
                # Queue the unified ingestion task with integration_id for token refresh
                from worker.tasks import unified_ingest_task

                task = unified_ingest_task.delay(
                    user_id=user_id,
                    job_id=str(job_id),
                    connector_type="notion",
                    item_ids=items,
                    credentials={"integration_id": str(integration_id)},  # ✅ Pass integration_id for token refresh
                    plan_code=plan_code,
                    dispatch_batch_size=_get_ingest_batch_size(),
                )
                logger.info(f"📥 [OAuth] Auto-ingestion started: {len(items)} pages, job {job_id}, task: {task.id}")
                audit_logger.log_sync(
                    user_id=user_id,
                    action="ingest.queued",
                    resource_type="ingestion_job",
                    resource_id=str(job_id),
                    details={"provider": "notion", "item_count": len(items), "task_id": task.id},
                )
                try:
                    increment_usage(org_id=org_id, storage_bytes=None, job_count_increment=max(1, len(items)))
                except Exception as exc:
                    logger.warning("⚠️ [Quotas] Failed to increment usage for %s: %s", org_id, exc)
        else:
            logger.info("📥 [OAuth] No Notion pages found to ingest")

    except Exception as e:
        logger.warning(f"🔐 [OAuth] Auto-ingestion failed (non-critical): {e}")
        # Don't fail the OAuth just because auto-ingestion failed

    return {
        "status": "success",
        "provider": "notion",
        "integration_id": integration_id,
        "workspace_name": workspace_name
    }


# =============================================================================
# Microsoft OAuth (OneDrive / SharePoint)
# =============================================================================

@router.post("/integrations/microsoft/exchange")
@limiter.limit("10/minute")
async def exchange_microsoft_token(
    request: Request,
    body: MicrosoftExchangeRequest,
    user_id: str = Depends(require_editor)
):
    """
    Exchange Microsoft OAuth code for tokens and persist to user_integrations.
    Supports OneDrive and SharePoint via Graph API.
    """
    target_type = body.target_type
    logger.info(f"🔐 [OAuth] Starting Microsoft token exchange for user: {user_id} ({target_type})")

    if not settings.MICROSOFT_CLIENT_ID:
        logger.error("🔐 [OAuth] Microsoft client ID not configured!")
        raise HTTPException(status_code=500, detail="Microsoft client ID not configured")  # ALLOWED: literal

    if not settings.MICROSOFT_REDIRECT_URI:
        logger.error("🔐 [OAuth] Microsoft redirect URI not configured!")
        raise HTTPException(status_code=500, detail="Microsoft redirect URI not configured")  # ALLOWED: literal

    supabase = get_supabase()

    # 1. Lookup connector definition ID
    def_res = supabase.table("connector_definitions").select("id").eq("type", target_type).single().execute()
    if not def_res.data:
        raise HTTPException(status_code=500, detail="Microsoft connector not found in definitions")  # ALLOWED: literal

    connector_definition_id = def_res.data["id"]
    tenant = settings.MICROSOFT_TENANT_ID or "common"
    token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    scope = settings.MICROSOFT_SCOPES_SHAREPOINT if target_type == "sharepoint" else settings.MICROSOFT_SCOPES_ONEDRIVE

    # 2. Exchange code for tokens
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            token_payload = {
                "client_id": settings.MICROSOFT_CLIENT_ID,
                "grant_type": "authorization_code",
                "code": body.code,
                "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
                "scope": scope,
            }
            if body.code_verifier:
                token_payload["code_verifier"] = body.code_verifier
            if settings.MICROSOFT_CLIENT_SECRET:
                token_payload["client_secret"] = settings.MICROSOFT_CLIENT_SECRET

            client_id_suffix = (
                settings.MICROSOFT_CLIENT_ID[-6:] if settings.MICROSOFT_CLIENT_ID else "missing"
            )
            secret_len = len(settings.MICROSOFT_CLIENT_SECRET or "")
            verifier_len = len(body.code_verifier or "")
            code_len = len(body.code or "")
            logger.info(
                "🔐 [OAuth] Microsoft token request config: tenant=%s redirect_uri=%s scope=%s "
                "client_id_suffix=%s secret_present=%s secret_len=%s code_len=%s "
                "code_verifier_present=%s code_verifier_len=%s payload_keys=%s",
                tenant,
                settings.MICROSOFT_REDIRECT_URI,
                scope,
                client_id_suffix,
                bool(settings.MICROSOFT_CLIENT_SECRET),
                secret_len,
                code_len,
                bool(body.code_verifier),
                verifier_len,
                sorted(token_payload.keys()),
            )

            response = await client.post(
                token_url,
                data=token_payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if (
                response.status_code != 200
                and token_payload.get("client_secret")
                and "AADSTS700025" in response.text
            ):
                logger.warning(
                    "🔐 [OAuth] Microsoft rejected client_secret; retrying as public client."
                )
                token_payload.pop("client_secret", None)
                response = await client.post(
                    token_url,
                    data=token_payload,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
        if response.status_code != 200:
            logger.error(f"🔐 [OAuth] Microsoft token exchange failed: {response.text}")
            error_detail = "Microsoft token exchange failed"
            try:
                error_payload = response.json()
            except ValueError:
                error_payload = None
            if isinstance(error_payload, dict):
                error_codes = error_payload.get("error_codes") or []
                raw_desc = error_payload.get("error_description") or ""
                if "AADSTS9002327" in raw_desc or 9002327 in error_codes:
                    error_detail = (
                        "AADSTS9002327: This Microsoft app is registered as SPA. "
                        "Tokens must be redeemed via a browser cross-origin request. "
                        "Move the redirect URI to the Web platform (or remove it from SPA), "
                        "or exchange tokens in the frontend instead."
                    )
            raise HTTPException(status_code=400, detail=error_detail)  # ALLOWED: literal

        token_data = response.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🔐 [OAuth] Microsoft token exchange failed: {e}")
        raise HTTPException(status_code=400, detail="Microsoft token exchange failed") from e  # ALLOWED: literal

    if not access_token:
        raise HTTPException(status_code=400, detail="Microsoft token exchange returned no access token")  # ALLOWED: literal

    expires_at = None
    if expires_in:
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))).isoformat()

    # 3. Lightweight permission verification + optional drive/site IDs
    credentials = {}
    graph_headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=20.0) as client:
        if target_type == "onedrive":
            drive_res = await client.get("https://graph.microsoft.com/v1.0/me/drive", headers=graph_headers)
            if drive_res.status_code != 200:
                raise HTTPException(status_code=401, detail="Microsoft permissions invalid for OneDrive")  # ALLOWED: literal
            drive_data = drive_res.json()
            if drive_data.get("id"):
                credentials["drive_id"] = drive_data["id"]
        else:
            site_id = body.site_id
            if not site_id:
                site_res = await client.get("https://graph.microsoft.com/v1.0/sites/root", headers=graph_headers)
                if site_res.status_code != 200:
                    raise HTTPException(status_code=401, detail="Microsoft permissions invalid for SharePoint")  # ALLOWED: literal
                site_id = site_res.json().get("id")
            if not site_id:
                raise HTTPException(status_code=400, detail="SharePoint site_id could not be resolved")  # ALLOWED: literal
            credentials["site_id"] = site_id
            drive_res = await client.get(
                f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive",
                headers=graph_headers,
            )
            if drive_res.status_code == 200:
                drive_data = drive_res.json()
                if drive_data.get("id"):
                    credentials["drive_id"] = drive_data["id"]

    # 4. Persist integration
    data = {
        "user_id": user_id,
        "connector_definition_id": connector_definition_id,
        "access_token": encrypt_token(access_token),
        "refresh_token": encrypt_token(refresh_token) if refresh_token else None,
        "expires_at": expires_at,
        "credentials": credentials or None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        # Reset status on successful reconnection
        "status": "active",
        "status_message": None,
    }

    upsert_res = supabase.table("user_integrations").upsert(
        data,
        on_conflict="user_id,connector_definition_id",
    ).execute()

    if not upsert_res.data:
        raise HTTPException(status_code=500, detail="Failed to store Microsoft credentials")  # ALLOWED: literal

    integration_id = upsert_res.data[0]["id"]

    audit_logger.log_sync(
        user_id=user_id,
        action="connector.connect",
        resource_type="connector",
        resource_id=target_type,
        details={"integration_id": integration_id},
    )

    return {"status": "success", "provider": target_type, "integration_id": integration_id}


# =============================================================================
# Dropbox OAuth (Personal & Business/Team accounts)
# =============================================================================

class DropboxExchangeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=2048)
    root_path: str | None = Field(default="", max_length=1024)


@router.post("/integrations/dropbox/exchange")
@limiter.limit("10/minute")
async def exchange_dropbox_token(
    request: Request,
    body: DropboxExchangeRequest,
    user_id: str = Depends(require_editor)
):
    """
    Exchange Dropbox OAuth code for tokens and persist to user_integrations.

    Supports both Personal and Business/Team accounts:
    - Detects Team accounts via root_info.root_namespace_id
    - Stores namespace_id for Dropbox-API-Path-Root header injection
    """
    logger.info(f"🔐 [OAuth] Starting Dropbox token exchange for user: {user_id}")

    if not settings.DROPBOX_CLIENT_ID or not settings.DROPBOX_CLIENT_SECRET:
        logger.error("🔐 [OAuth] Dropbox credentials not configured!")
        raise HTTPException(status_code=500, detail="Dropbox credentials not configured")  # ALLOWED: literal

    if not settings.DROPBOX_REDIRECT_URI:
        logger.error("🔐 [OAuth] Dropbox redirect URI not configured!")
        raise HTTPException(status_code=500, detail="Dropbox redirect URI not configured")  # ALLOWED: literal

    supabase = get_supabase()

    # 1. Lookup connector definition ID
    def_res = supabase.table("connector_definitions").select("id").eq("type", "dropbox").single().execute()
    if not def_res.data:
        raise HTTPException(status_code=500, detail="dropbox connector not found in definitions")  # ALLOWED: literal

    connector_definition_id = def_res.data["id"]

    # 2. Exchange code for tokens
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            token_payload = {
                "code": body.code,
                "grant_type": "authorization_code",
                "client_id": settings.DROPBOX_CLIENT_ID,
                "client_secret": settings.DROPBOX_CLIENT_SECRET,
                "redirect_uri": settings.DROPBOX_REDIRECT_URI,
            }

            response = await client.post(
                "https://api.dropboxapi.com/oauth2/token",
                data=token_payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        if response.status_code != 200:
            logger.error(f"🔐 [OAuth] Dropbox token exchange failed: {response.text}")
            raise HTTPException(status_code=400, detail="Dropbox token exchange failed")  # ALLOWED: literal

        token_data = response.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in")
        account_id = token_data.get("account_id")
        uid = token_data.get("uid")

        logger.info(f"🔐 [OAuth] ✅ Got Dropbox tokens. Account: {account_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🔐 [OAuth] Dropbox token exchange failed: {e}")
        raise HTTPException(status_code=400, detail="Dropbox token exchange failed") from e  # ALLOWED: literal

    if not access_token:
        raise HTTPException(status_code=400, detail="Dropbox token exchange returned no access token")  # ALLOWED: literal

    expires_at = None
    if expires_in:
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))).isoformat()

    # 3. Get account info to detect Team accounts and extract namespace_id
    credentials = {
        "account_id": account_id,
        "uid": uid,
        "root_path": body.root_path or "",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            account_response = await client.post(
                "https://api.dropboxapi.com/2/users/get_current_account",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                content="null",
            )

            if account_response.status_code == 200:
                account_info = account_response.json()

                # Extract Team namespace if present
                root_info = account_info.get("root_info", {})
                namespace_id = root_info.get("root_namespace_id")

                if namespace_id:
                    credentials["namespace_id"] = namespace_id
                    logger.info(f"🏢 [OAuth] Dropbox Team account detected, namespace: {namespace_id}")

                    # Also store team info if available
                    team = account_info.get("team", {})
                    if team:
                        credentials["team_name"] = team.get("name")
                        credentials["team_id"] = team.get("id")
                else:
                    logger.info("👤 [OAuth] Dropbox Personal account")

                # Store display name for UI
                name = account_info.get("name", {})
                credentials["display_name"] = name.get("display_name")
                credentials["email"] = account_info.get("email")
            else:
                logger.warning(f"⚠️ [OAuth] Failed to get Dropbox account info: {account_response.text}")

    except Exception as e:
        logger.warning(f"⚠️ [OAuth] Failed to get Dropbox account info: {e}")
        # Non-fatal - continue without namespace

    # 4. Persist integration
    data = {
        "user_id": user_id,
        "connector_definition_id": connector_definition_id,
        "access_token": encrypt_token(access_token),
        "refresh_token": encrypt_token(refresh_token) if refresh_token else None,
        "expires_at": expires_at,
        "credentials": credentials,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        # Reset status on successful reconnection
        "status": "active",
        "status_message": None,
    }

    upsert_res = supabase.table("user_integrations").upsert(
        data,
        on_conflict="user_id,connector_definition_id",
    ).execute()

    if not upsert_res.data:
        raise HTTPException(status_code=500, detail="Failed to store Dropbox credentials")  # ALLOWED: literal

    integration_id = upsert_res.data[0]["id"]

    audit_logger.log_sync(
        user_id=user_id,
        action="connector.connect",
        resource_type="connector",
        resource_id="dropbox",
        details={
            "integration_id": integration_id,
            "is_team_account": bool(credentials.get("namespace_id")),
        },
    )

    logger.info(f"🔐 [OAuth] ✅ Dropbox connected (integration: {integration_id})")

    return {
        "status": "success",
        "provider": "dropbox",
        "integration_id": integration_id,
        "is_team_account": bool(credentials.get("namespace_id")),
        "display_name": credentials.get("display_name"),
    }


# =============================================================================
# GitHub OAuth (Code Repository Integration)
# =============================================================================

class GitHubExchangeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=2048)


class GitHubRepoSelectionRequest(BaseModel):
    """Request to save selected repositories for sync."""
    selected_repositories: list[dict] = Field(..., max_length=100)


@router.post("/integrations/github/exchange")
@limiter.limit("10/minute")
async def exchange_github_token(
    request: Request,
    body: GitHubExchangeRequest,
    user_id: str = Depends(require_editor)
):
    """
    Exchange GitHub OAuth code for tokens and persist to user_integrations.

    GitHub tokens do not expire by default, so no refresh_token handling needed.
    After this, the user must select repositories via /github/repos/select.
    """
    logger.info(f"🔐 [OAuth] Starting GitHub token exchange for user: {user_id}")

    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
        logger.error("🔐 [OAuth] GitHub credentials not configured!")
        raise HTTPException(status_code=500, detail="GitHub credentials not configured")  # ALLOWED: literal

    supabase = get_supabase()

    # 1. Lookup connector definition ID
    def_res = supabase.table("connector_definitions").select("id").eq("type", "github").single().execute()
    if not def_res.data:
        raise HTTPException(status_code=500, detail="github connector not found in definitions")  # ALLOWED: literal

    connector_definition_id = def_res.data["id"]

    # 2. Exchange code for token
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            token_payload = {
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": body.code,
            }
            if settings.GITHUB_REDIRECT_URI:
                token_payload["redirect_uri"] = settings.GITHUB_REDIRECT_URI

            response = await client.post(
                "https://github.com/login/oauth/access_token",
                data=token_payload,
                headers={"Accept": "application/json"},
            )

        if response.status_code != 200:
            logger.error(f"🔐 [OAuth] GitHub token exchange failed: {response.text}")
            raise HTTPException(status_code=400, detail="GitHub token exchange failed")  # ALLOWED: literal

        token_data = response.json()

        if "error" in token_data:
            error_desc = token_data.get("error_description", token_data.get("error"))
            logger.error(f"🔐 [OAuth] GitHub OAuth error: {error_desc}")
            raise HTTPException(status_code=400, detail="GitHub OAuth exchange failed. Please try connecting again.")  # ALLOWED: literal

        access_token = token_data.get("access_token")
        scope = token_data.get("scope", "")
        token_type = token_data.get("token_type", "bearer")

        logger.info(f"🔐 [OAuth] ✅ Got GitHub token. Scope: {scope}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🔐 [OAuth] GitHub token exchange failed: {e}")
        raise HTTPException(status_code=400, detail="GitHub token exchange failed") from e  # ALLOWED: literal

    if not access_token:
        raise HTTPException(status_code=400, detail="GitHub token exchange returned no access token")  # ALLOWED: literal

    # 3. Get user info to validate token and get GitHub user ID
    credentials = {"scope": scope}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            user_response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )

            if user_response.status_code == 200:
                user_info = user_response.json()
                credentials["github_user_id"] = user_info.get("id")
                credentials["github_login"] = user_info.get("login")
                credentials["github_name"] = user_info.get("name")
                credentials["github_avatar_url"] = user_info.get("avatar_url")
                logger.info(f"🔐 [OAuth] GitHub user: {user_info.get('login')}")
            else:
                logger.warning(f"⚠️ [OAuth] Failed to get GitHub user info: {user_response.text}")

    except Exception as e:
        logger.warning(f"⚠️ [OAuth] Failed to get GitHub user info: {e}")

    # 4. Persist integration (no expiry for GitHub tokens)
    data = {
        "user_id": user_id,
        "connector_definition_id": connector_definition_id,
        "access_token": encrypt_token(access_token),
        "refresh_token": None,  # GitHub doesn't use refresh tokens
        "expires_at": None,  # GitHub tokens don't expire
        "credentials": credentials,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        # Reset status on successful reconnection
        "status": "active",
        "status_message": None,
    }

    upsert_res = supabase.table("user_integrations").upsert(
        data,
        on_conflict="user_id,connector_definition_id",
    ).execute()

    if not upsert_res.data:
        raise HTTPException(status_code=500, detail="Failed to store GitHub credentials")  # ALLOWED: literal

    integration_id = upsert_res.data[0]["id"]

    audit_logger.log_sync(
        user_id=user_id,
        action="connector.connect",
        resource_type="connector",
        resource_id="github",
        details={
            "integration_id": integration_id,
            "github_login": credentials.get("github_login"),
        },
    )

    logger.info(f"🔐 [OAuth] ✅ GitHub connected (integration: {integration_id})")

    return {
        "status": "success",
        "provider": "github",
        "integration_id": integration_id,
        "github_login": credentials.get("github_login"),
        "github_name": credentials.get("github_name"),
    }


@router.get("/integrations/github/repos")
@limiter.limit("30/minute")
async def list_github_repos(
    request: Request,
    user_id: str = Depends(get_current_user)
):
    """
    List GitHub repositories the user has access to.

    Used by frontend for repository selection UI.
    Returns both personal repos and organization repos.
    """
    supabase = get_supabase()

    # Get user's GitHub integration
    def_res = supabase.table("connector_definitions").select("id").eq("type", "github").single().execute()
    if not def_res.data:
        raise HTTPException(status_code=500, detail="GitHub connector not found")  # ALLOWED: literal

    int_res = supabase.table("user_integrations").select(
        "id, access_token, credentials"
    ).eq("user_id", user_id).eq("connector_definition_id", def_res.data["id"]).single().execute()

    if not int_res.data or not int_res.data.get("access_token"):
        raise HTTPException(status_code=401, detail="GitHub not connected. Please connect GitHub first.")  # ALLOWED: literal

    # Decrypt token
    access_token = decrypt_token(int_res.data["access_token"])

    if not access_token:
        raise HTTPException(status_code=401, detail="GitHub token invalid. Please reconnect.")  # ALLOWED: literal

    # Use connector to fetch repos
    try:
        from connectors.github import GitHubConnector
        connector = GitHubConnector()
        repos = await run_in_threadpool(
            lambda: connector.get_available_repositories(access_token)
        )

        return {
            "repositories": repos,
            "total": len(repos),
        }
    except ConnectorAuthError as e:
        logger.warning(f"⚠️ [GitHub] Auth error listing repos: {e}")
        raise_http_error(
            status.HTTP_401_UNAUTHORIZED,
            "INTEGRATION_AUTH_FAILED",
            "GitHub authentication failed. Please reconnect your integration.",
            {"provider": "github", "reason": str(e)},
        )
    except Exception as e:
        logger.error(f"❌ [GitHub] Failed to list repos: {e}")
        raise_http_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "CONNECTOR_FAILED",
            "Failed to list GitHub repositories.",
            {"provider": "github", "reason": str(e)},
        )


@router.post("/integrations/github/repos/select")
@limiter.limit("20/minute")
async def select_github_repos(
    request: Request,
    body: GitHubRepoSelectionRequest,
    user_id: str = Depends(require_editor)
):
    """
    Save selected repositories for GitHub sync.

    Expected format for each repo:
    {
        "full_name": "owner/repo",
        "branch": "main",  # optional, uses default if not specified
        "enabled": true
    }
    """
    supabase = get_supabase()

    # Get user's GitHub integration
    def_res = supabase.table("connector_definitions").select("id").eq("type", "github").single().execute()
    if not def_res.data:
        raise HTTPException(status_code=500, detail="GitHub connector not found")  # ALLOWED: literal

    int_res = supabase.table("user_integrations").select(
        "id, credentials"
    ).eq("user_id", user_id).eq("connector_definition_id", def_res.data["id"]).single().execute()

    if not int_res.data:
        raise HTTPException(status_code=401, detail="GitHub not connected")  # ALLOWED: literal

    integration_id = int_res.data["id"]
    existing_credentials = int_res.data.get("credentials") or {}

    # Update credentials with selected repositories
    updated_credentials = {
        **existing_credentials,
        "selected_repositories": body.selected_repositories,
        "repos_selected_at": datetime.now(timezone.utc).isoformat(),
    }

    # Update integration
    update_res = supabase.table("user_integrations").update({
        "credentials": updated_credentials,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", integration_id).execute()

    if not update_res.data:
        raise HTTPException(status_code=500, detail="Failed to save repository selection")  # ALLOWED: literal

    enabled_count = sum(1 for r in body.selected_repositories if r.get("enabled", True))

    audit_logger.log_sync(
        user_id=user_id,
        action="connector.configure",
        resource_type="connector",
        resource_id="github",
        details={
            "integration_id": integration_id,
            "repos_selected": enabled_count,
        },
    )

    logger.info(f"✅ [GitHub] Saved {enabled_count} repos for user {user_id}")

    return {
        "status": "success",
        "integration_id": integration_id,
        "repos_selected": enabled_count,
    }


# =============================================================================
# Box OAuth
# =============================================================================

class BoxExchangeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=2048)


@router.post("/integrations/box/exchange")
@limiter.limit("10/minute")
async def exchange_box_token(
    request: Request,
    body: BoxExchangeRequest,
    user_id: str = Depends(require_editor)
):
    """
    Exchange Box OAuth code for tokens and persist to user_integrations.

    CRITICAL: Box refresh tokens are SINGLE-USE and rotate on each refresh.
    Both access_token AND refresh_token must be stored and updated atomically.
    """
    logger.info(f"🔐 [OAuth] Starting Box token exchange for user: {user_id}")

    if not settings.BOX_CLIENT_ID or not settings.BOX_CLIENT_SECRET:
        logger.error("🔐 [OAuth] Box credentials not configured!")
        raise HTTPException(status_code=500, detail="Box credentials not configured")  # ALLOWED: literal

    supabase = get_supabase()

    # 1. Lookup connector definition ID
    def_res = supabase.table("connector_definitions").select("id").eq("type", "box").single().execute()
    if not def_res.data:
        raise HTTPException(status_code=500, detail="box connector not found in definitions")  # ALLOWED: literal

    connector_definition_id = def_res.data["id"]

    # 2. Exchange code for tokens
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            token_payload = {
                "grant_type": "authorization_code",
                "client_id": settings.BOX_CLIENT_ID,
                "client_secret": settings.BOX_CLIENT_SECRET,
                "code": body.code,
            }
            if settings.BOX_REDIRECT_URI:
                token_payload["redirect_uri"] = settings.BOX_REDIRECT_URI

            response = await client.post(
                "https://api.box.com/oauth2/token",
                data=token_payload,
            )

        if response.status_code != 200:
            logger.error(f"🔐 [OAuth] Box token exchange failed: {response.text}")
            raise HTTPException(status_code=400, detail="Box token exchange failed")  # ALLOWED: literal

        token_data = response.json()

        if "error" in token_data:
            error_desc = token_data.get("error_description", token_data.get("error"))
            logger.error(f"🔐 [OAuth] Box OAuth error: {error_desc}")
            raise HTTPException(status_code=400, detail="Box OAuth exchange failed. Please try connecting again.")  # ALLOWED: literal

        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")  # CRITICAL: Box tokens rotate
        expires_in = token_data.get("expires_in")

        logger.info(f"🔐 [OAuth] ✅ Got Box tokens. Expires in: {expires_in}s")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🔐 [OAuth] Box token exchange failed: {e}")
        raise HTTPException(status_code=400, detail="Box token exchange failed") from e  # ALLOWED: literal

    if not access_token:
        raise HTTPException(status_code=400, detail="Box token exchange returned no access token")  # ALLOWED: literal

    if not refresh_token:
        logger.warning("⚠️ [OAuth] Box did not return refresh token - may have issues with token refresh")

    # 3. Get user info to validate token and get Box user ID
    credentials = {}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            user_response = await client.get(
                "https://api.box.com/2.0/users/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if user_response.status_code == 200:
                user_info = user_response.json()
                credentials["box_user_id"] = user_info.get("id")
                credentials["box_login"] = user_info.get("login")
                credentials["box_name"] = user_info.get("name")
                credentials["box_avatar_url"] = user_info.get("avatar_url")
                # Check if enterprise account
                enterprise = user_info.get("enterprise")
                if enterprise:
                    credentials["box_enterprise_id"] = enterprise.get("id")
                    credentials["box_enterprise_name"] = enterprise.get("name")
                logger.info(f"🔐 [OAuth] Box user: {user_info.get('login')}")
            else:
                logger.warning(f"⚠️ [OAuth] Failed to get Box user info: {user_response.text}")

    except Exception as e:
        logger.warning(f"⚠️ [OAuth] Failed to get Box user info: {e}")

    # 4. Calculate expiration time
    expires_at = None
    if expires_in:
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))).isoformat()

    # 5. Persist integration (BOTH tokens - Box refresh tokens rotate!)
    data = {
        "user_id": user_id,
        "connector_definition_id": connector_definition_id,
        "access_token": encrypt_token(access_token),
        "refresh_token": encrypt_token(refresh_token) if refresh_token else None,
        "expires_at": expires_at,
        "credentials": credentials,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        # Reset status on successful reconnection
        "status": "active",
        "status_message": None,
    }

    upsert_res = supabase.table("user_integrations").upsert(
        data,
        on_conflict="user_id,connector_definition_id",
    ).execute()

    if not upsert_res.data:
        raise HTTPException(status_code=500, detail="Failed to store Box credentials")  # ALLOWED: literal

    integration_id = upsert_res.data[0]["id"]

    audit_logger.log_sync(
        user_id=user_id,
        action="connector.connect",
        resource_type="connector",
        resource_id="box",
        details={
            "integration_id": integration_id,
            "box_login": credentials.get("box_login"),
            "is_enterprise": "box_enterprise_id" in credentials,
        },
    )

    logger.info(f"🔐 [OAuth] ✅ Box connected (integration: {integration_id})")

    return {
        "status": "success",
        "provider": "box",
        "integration_id": integration_id,
        "box_login": credentials.get("box_login"),
        "box_name": credentials.get("box_name"),
        "is_enterprise": "box_enterprise_id" in credentials,
    }


# =============================================================================
# Integration Management Endpoints
# =============================================================================

@router.post("/integrations/sftp/connect")
@limiter.limit("10/minute")
async def connect_sftp(
    request: Request,
    body: SFTPConnectRequest,
    user_id: str = Depends(require_editor),
):
    """
    Connect an SFTP server by storing encrypted credentials in user_integrations.
    """
    if not body.password and not body.private_key:
        raise HTTPException(status_code=400, detail="Either password or private_key is required.")  # ALLOWED: literal

    supabase = get_supabase()
    conn_def = supabase.table("connector_definitions").select("id").eq("type", "sftp").single().execute()
    if not conn_def.data:
        raise HTTPException(status_code=500, detail="sftp connector not found in definitions")  # ALLOWED: literal

    connector = SFTPConnector()
    config = body.model_dump()

    try:
        connector.verify_connection(config)
    except ValueError as exc:
        raise_http_error(
            status.HTTP_400_BAD_REQUEST,
            "CONNECTOR_VALIDATION_FAILED",
            str(exc),
            {"provider": "sftp"},
        )
    except ConnectorAuthError as exc:
        raise_http_error(
            status.HTTP_401_UNAUTHORIZED,
            "INTEGRATION_AUTH_FAILED",
            "SFTP authentication failed. Please verify your credentials.",
            {"provider": "sftp", "reason": str(exc)},
        )
    except ConnectorTransientError as exc:
        raise_http_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "CONNECTOR_UNAVAILABLE",
            f"SFTP connection failed: {exc}",
            {"provider": "sftp"},
        )

    credentials = {
        "host": body.host,
        "port": body.port,
        "username": body.username,
        "password": encrypt_token(body.password) if body.password else None,
        "private_key": encrypt_token(body.private_key) if body.private_key else None,
        "root_path": body.root_path,
    }

    data = {
        "user_id": user_id,
        "connector_definition_id": conn_def.data["id"],
        "credentials": credentials,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    upsert_res = supabase.table("user_integrations").upsert(
        data,
        on_conflict="user_id,connector_definition_id",
    ).execute()

    if not upsert_res.data:
        raise HTTPException(status_code=500, detail="Failed to store SFTP credentials")  # ALLOWED: literal

    audit_logger.log_sync(
        user_id=user_id,
        action="connector.connect",
        resource_type="connector",
        resource_id="sftp",
        details={"host": body.host, "port": body.port, "root_path": body.root_path},
    )

    return {
        "status": "success",
        "provider": "sftp",
        "integration_id": upsert_res.data[0]["id"],
    }


# =============================================================================
# S3 Connector (ENTERPRISE ONLY)
# =============================================================================

# Enterprise plan identifiers for S3 gate
ENTERPRISE_PLANS = frozenset({
    "enterprise",
    "enterprise_small",
    "enterprise_medium",
    "enterprise_large",
})


@router.post("/integrations/s3/connect")
@limiter.limit("5/minute")
async def connect_s3(
    request: Request,
    body: S3ConnectRequest,
    user_id: str = Depends(require_editor),
    plan: str = Depends(get_effective_plan),
):
    """
    Connect Amazon S3 bucket with IAM credentials.

    **ENTERPRISE ONLY**: This connector requires an Enterprise plan subscription.

    SECURITY NOTES:
    - Credentials are encrypted at rest using Fernet
    - Only read operations (ListBucket, GetObject) are supported
    - Provide a read-only IAM policy for maximum security

    COST PROTECTION:
    - Prefix is required to prevent full bucket scans
    - Only supported file extensions are processed

    IAM Policy Template (MINIMUM REQUIRED):
    ```json
    {
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Action": ["s3:GetObject", "s3:ListBucket"],
        "Resource": ["arn:aws:s3:::BUCKET", "arn:aws:s3:::BUCKET/*"]
      }]
    }
    ```
    """
    # =================================================================
    # ENTERPRISE GATE: Non-negotiable business rule
    # =================================================================
    if plan not in ENTERPRISE_PLANS:
        logger.warning(
            f"🚫 [S3] Enterprise gate blocked user {user_id[:8]}... "
            f"(plan={plan})"
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": "ENTERPRISE_REQUIRED",
                "current_plan": plan,
                "message": (
                    "Amazon S3 connector is available exclusively on Enterprise plans. "
                    "Please upgrade your subscription to access cloud storage integrations."
                ),
                "upgrade_url": "/settings/billing",
            }
        )  # ALLOWED: plan is user's own subscription data, not an internal leak

    # =================================================================
    # Verify S3 Access
    # =================================================================
    supabase = get_supabase()

    # Get S3 connector definition
    conn_def = supabase.table("connector_definitions").select("id").eq(
        "type", "s3"
    ).single().execute()

    if not conn_def.data:
        raise HTTPException(
            status_code=500,
            detail="S3 connector not configured. Please contact support."
        )  # ALLOWED: literal

    # Verify credentials and bucket access
    connector = S3Connector()
    config = {
        "access_key_id": body.access_key_id,
        "secret_access_key": body.secret_access_key,
        "region": body.region,
        "bucket_name": body.bucket_name,
        "prefix": body.prefix,
    }

    try:
        connector._verify_access(config)
    except ValueError as exc:
        # Prefix validation error
        raise_http_error(
            status.HTTP_400_BAD_REQUEST,
            "CONNECTOR_VALIDATION_FAILED",
            str(exc),
            {"provider": "s3"},
        )
    except ConnectorAuthError as exc:
        raise_http_error(
            status.HTTP_401_UNAUTHORIZED,
            "INTEGRATION_AUTH_FAILED",
            "S3 authentication failed. Please verify your credentials.",
            {"provider": "s3", "reason": str(exc)},
        )
    except ConnectorTransientError as exc:
        raise_http_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "CONNECTOR_UNAVAILABLE",
            f"S3 connection failed: {exc}",
            {"provider": "s3"},
        )

    # =================================================================
    # Store Encrypted Credentials
    # =================================================================
    credentials = {
        "access_key_id": encrypt_token(body.access_key_id),
        "secret_access_key": encrypt_token(body.secret_access_key),
        "region": body.region,
        "bucket_name": body.bucket_name,
        "prefix": body.prefix,
    }

    data = {
        "user_id": user_id,
        "connector_definition_id": conn_def.data["id"],
        "credentials": credentials,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    upsert_res = supabase.table("user_integrations").upsert(
        data,
        on_conflict="user_id,connector_definition_id",
    ).execute()

    if not upsert_res.data:
        raise HTTPException(status_code=500, detail="Failed to store S3 credentials")  # ALLOWED: literal

    # Audit log (never log credentials)
    audit_logger.log_sync(
        user_id=user_id,
        action="connector.connect",
        resource_type="connector",
        resource_id="s3",
        details={
            "bucket": body.bucket_name,
            "region": body.region,
            "prefix": body.prefix,
        },
    )

    logger.info(
        f"🔐 [S3] ✅ S3 connected for user {user_id[:8]}... "
        f"(bucket={body.bucket_name}, region={body.region})"
    )

    return {
        "status": "success",
        "provider": "s3",
        "integration_id": upsert_res.data[0]["id"],
        "bucket": body.bucket_name,
        "region": body.region,
        "prefix": body.prefix,
    }


@router.get("/integrations/{provider}/status")
async def get_provider_status(
    provider: str,
    user_id: str = Depends(get_current_user)
):
    """Check if a specific provider is connected for the user."""
    supabase = get_supabase()
    provider = _require_provider(provider)

    try:
        # Lookup connector definition by type
        def_res = supabase.table("connector_definitions").select("id").eq("type", provider).single().execute()
        if not def_res.data:
            return {"connected": False, "error": "Unknown provider"}

        connector_def_id = def_res.data["id"]

        # Check if user has this integration
        int_res = supabase.table("user_integrations").select("id").eq(
            "user_id", user_id
        ).eq("connector_definition_id", connector_def_id).execute()

        return {"connected": len(int_res.data or []) > 0}
    except Exception:
        return {"connected": False}


@router.delete("/integrations/{provider}")
@limiter.limit("10/minute")
async def disconnect_provider(
    request: Request,
    provider: str,
    user_id: str = Depends(require_editor),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    Disconnect a provider integration.
    Attempts to revoke the OAuth token with the provider before deleting records.
    """
    supabase = get_supabase()
    provider = _require_provider(provider)

    # Initialize cleanup counters before try block to ensure they're always defined
    deleted_docs = 0
    deleted_identity_docs = 0
    deleted_identity_scopes = 0
    deleted_jobs = 0
    deleted_sync = 0

    try:
        # Lookup connector definition by type
        def_res = supabase.table("connector_definitions").select("id").eq("type", provider).single().execute()
        if not def_res.data:
            raise HTTPException(status_code=404, detail="Unknown provider")  # ALLOWED: literal

        connector_def_id = def_res.data["id"]

        # 1. Fetch credentials before deletion to perform revocation
        try:
            int_res = supabase.table("user_integrations").select("access_token").eq(
                "user_id", user_id
            ).eq("connector_definition_id", connector_def_id).single().execute()

            if int_res.data and int_res.data.get("access_token"):
                encrypted_token = int_res.data["access_token"]
                token = decrypt_token(encrypted_token)

                if token:
                    logger.info(f"🔌 [Disconnect] Attempting to revoke {provider} token...")
                    async with httpx.AsyncClient() as client:
                        if provider == "google_drive":
                            # Google Revocation
                            await client.post(
                                "https://oauth2.googleapis.com/revoke",
                                params={"token": token},
                                timeout=5.0
                            )
                            logger.info("🔌 [Disconnect] Google token revoked")

                        elif provider == "dropbox":
                            await client.post(
                                "https://api.dropboxapi.com/2/auth/token/revoke",
                                headers={"Authorization": f"Bearer {token}"},
                                timeout=5.0,
                            )
                            logger.info("🔌 [Disconnect] Dropbox token revoked")

                        elif provider == "github":
                            if settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET:
                                await client.request(
                                    "DELETE",
                                    f"https://api.github.com/applications/{settings.GITHUB_CLIENT_ID}/token",
                                    auth=(settings.GITHUB_CLIENT_ID, settings.GITHUB_CLIENT_SECRET),
                                    headers={
                                        "Accept": "application/vnd.github+json",
                                        "X-GitHub-Api-Version": "2022-11-28",
                                    },
                                    json={"access_token": token},
                                    timeout=5.0,
                                )
                                logger.info("🔌 [Disconnect] GitHub token revoked")
                            else:
                                logger.warning("⚠️ [Disconnect] GitHub client credentials missing; skipping provider revoke")

                        elif provider == "box":
                            if settings.BOX_CLIENT_ID and settings.BOX_CLIENT_SECRET:
                                await client.post(
                                    "https://api.box.com/oauth2/revoke",
                                    data={
                                        "client_id": settings.BOX_CLIENT_ID,
                                        "client_secret": settings.BOX_CLIENT_SECRET,
                                        "token": token,
                                    },
                                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                                    timeout=5.0,
                                )
                                logger.info("🔌 [Disconnect] Box token revoked")
                            else:
                                logger.warning("⚠️ [Disconnect] Box client credentials missing; skipping provider revoke")

                        elif provider == "notion":
                            # Notion doesn't have a standardized revoke endpoint for simple OAuth,
                            # but we attempt standard best practices or just log.
                            # Notion revocation usually implies removing the bot from workspace UI.
                            pass

        except Exception as e:
            # Non-blocking failure - continue to delete from our DB
            logger.warning(f"⚠️ [Disconnect] Revocation attempt failed (continuing): {e}")

        # =================================================================
        # 2. DEEP CLEAN: Delete all associated data before removing integration
        # =================================================================
        # Map provider to source_type values used in documents table
        source_types = [provider]

        logger.info(f"🧹 [Disconnect] Deep cleaning data for {provider} (source_type={source_types})...")

        # 2a. Delete Documents (cascades to document_chunks via FK)
        try:
            doc_result = supabase.table("documents").delete().eq(
                "user_id", user_id
            ).eq("organization_id", organization_id).in_("source_type", source_types).execute()

            deleted_docs = len(doc_result.data) if doc_result.data else 0
            logger.info(f"🧹 [Disconnect] Deleted {deleted_docs} documents")
        except Exception as e:
            logger.warning(f"⚠️ [Disconnect] Document cleanup failed: {e}")

        # 2a.1 Delete identity documents + scope identities tied to this provider
        scope_prefixes = get_scope_prefixes(provider)
        if scope_prefixes:
            try:
                deleted_identity_docs = 0
                deleted_identity_scopes = 0
                for scope_prefix in scope_prefixes:
                    identity_docs = (
                        supabase.table("documents")
                        .delete()
                        .eq("organization_id", organization_id)
                        .eq("user_id", user_id)
                        .eq("source_type", "identity")
                        .like("scope_id", f"{scope_prefix}%")
                        .execute()
                    )
                    deleted_identity_docs += len(identity_docs.data) if identity_docs.data else 0

                    identity_scopes = (
                        supabase.table("scope_identities")
                        .delete()
                        .eq("organization_id", organization_id)
                        .eq("user_id", user_id)
                        .like("id", f"{scope_prefix}%")
                        .execute()
                    )
                    deleted_identity_scopes += len(identity_scopes.data) if identity_scopes.data else 0

                logger.info(
                    f"🧹 [Disconnect] Deleted {deleted_identity_docs} identity documents "
                    f"and {deleted_identity_scopes} scope identities for {provider}"
                )
            except Exception as e:
                logger.warning(f"⚠️ [Disconnect] Identity cleanup failed: {e}")

        # 2b. Delete Ingestion Jobs and associated file statuses
        try:
            # First, find all job IDs for this provider
            jobs_res = supabase.table("ingestion_jobs").select("id").eq(
                "user_id", user_id
            ).eq("organization_id", organization_id).eq("provider", provider).execute()

            job_ids = [job["id"] for job in (jobs_res.data or [])]

            # Delete file statuses for these jobs
            if job_ids:
                for job_id in job_ids:
                    supabase.table("ingestion_file_status").delete().eq("job_id", job_id).execute()
                logger.info(f"🧹 [Disconnect] Deleted file statuses for {len(job_ids)} jobs")

            # Then delete the jobs
            job_result = supabase.table("ingestion_jobs").delete().eq(
                "user_id", user_id
            ).eq("organization_id", organization_id).eq("provider", provider).execute()

            deleted_jobs = len(job_result.data) if job_result.data else 0
            logger.info(f"🧹 [Disconnect] Deleted {deleted_jobs} ingestion jobs")
        except Exception as e:
            logger.warning(f"⚠️ [Disconnect] Job cleanup failed: {e}")

        # 2c. Delete sync state (cursors, tokens, etc.)
        try:
            sync_result = supabase.table("sync_state").delete().eq(
                "user_id", user_id
            ).eq("provider", provider).execute()

            deleted_sync = len(sync_result.data) if sync_result.data else 0
            logger.info(f"🧹 [Disconnect] Deleted {deleted_sync} sync state records")
        except Exception as e:
            logger.warning(f"⚠️ [Disconnect] Sync state cleanup failed: {e}")

        # =================================================================
        # 3. Delete the user integration record
        # =================================================================
        supabase.table("user_integrations").delete().eq(
            "user_id", user_id
        ).eq("connector_definition_id", connector_def_id).execute()

        logger.info(f"✅ [Disconnect] {provider} disconnected and all data cleaned for user {user_id}")

        audit_logger.log_sync(
            user_id=user_id,
            action="connector.disconnect",
            resource_type="connector",
            resource_id=provider,
            details={
                "documents_deleted": deleted_docs,
                "identity_documents_deleted": deleted_identity_docs,
                "identity_scopes_deleted": deleted_identity_scopes,
                "jobs_deleted": deleted_jobs,
                "sync_deleted": deleted_sync,
            },
        )

        return {
            "status": "success",
            "provider": provider,
            "cleanup": {
                "documents_deleted": deleted_docs,
                "identity_documents_deleted": deleted_identity_docs,
                "identity_scopes_deleted": deleted_identity_scopes,
                "jobs_deleted": deleted_jobs,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "disconnect")


# =============================================================================
# Provider Items & Ingestion
# =============================================================================

from connectors import get_connector


@router.get("/integrations/{provider}/items")
async def list_provider_items(
    provider: str,
    parent_id: str | None = None,
    user_id: str = Depends(get_current_user)
):
    """
    List items from a connected provider (folders, files, etc.).

    Handles both async and sync connectors:
    - Async connectors (Google Drive, Notion, OneDrive, SharePoint): awaited directly
    - Sync connectors (Dropbox, SFTP): offloaded to threadpool to prevent blocking

    This prevents the main event loop from being blocked by sync I/O operations.
    """
    try:
        provider = _require_provider(provider)
        connector = get_connector(provider)
        config = {"user_id": user_id, "parent_id": parent_id, "provider": provider}

        # =================================================================
        # Async/Sync Bridge: Handle both coroutine and generator connectors
        # =================================================================
        list_files_method = connector.list_files

        if inspect.iscoroutinefunction(list_files_method):
            # Async connector (e.g., Google Drive, Notion, OneDrive)
            # Safe to await directly
            raw_items = await list_files_method(config)
        else:
            # Sync connector (e.g., Dropbox, SFTP) - returns generator
            # CRITICAL: Offload to threadpool to prevent blocking the event loop
            #
            # Why this matters:
            # - Dropbox uses synchronous `requests` library
            # - Each API call blocks while waiting for network response
            # - Without threadpool, ALL other users would freeze during this
            # - run_in_threadpool executes in a separate thread, keeping event loop free
            #
            # The lambda consumes the generator into a list within the thread,
            # ensuring all network I/O happens off the main event loop.
            raw_items = await run_in_threadpool(lambda: list(list_files_method(config)))

        # =================================================================
        # Item Mapping
        # =================================================================
        def _map_item(item: Any) -> dict | None:
            # Handle dataclass-like objects or dicts
            if hasattr(item, "__dict__"):
                data = item.__dict__
            elif isinstance(item, dict):
                data = item
            else:
                return None

            mime = data.get("mime_type") or data.get("mimeType")
            name = data.get("name") or data.get("id") or "Untitled"
            item_type = "file"
            # Infer folder-like types
            if data.get("is_dir") or mime in {
                "application/vnd.google-apps.folder",
                "application/vnd.notion.page",
                "application/vnd.notion.database",
                "application/vnd.github.folder",
                "application/vnd.github.repository",
                "inode/directory",
                "application/x-directory",
            }:
                item_type = "folder"
            item_id = data.get("id")
            if not item_id:
                return None
            return {
                "id": item_id,
                "name": name,
                "type": item_type,
                "mimeType": mime,
                "size": data.get("size"),
                "parent_id": data.get("parent_id"),
                "web_view_url": data.get("web_view_url"),
            }

        items = [_map_item(it) for it in (raw_items or []) if it]
        items = [it for it in items if it]
        return items
    except ConnectorAuthError as e:
        # Auth errors should return 401, not 500
        logger.warning(f"⚠️ [ListItems] Auth error for {provider}: {e}")
        raise_http_error(
            status.HTTP_401_UNAUTHORIZED,
            "INTEGRATION_AUTH_FAILED",
            "Authentication failed. Please reconnect your integration.",
            {"provider": provider, "reason": str(e)},
        )
    except ConnectorTransientError as e:
        # Transient errors (rate limits, network) - return 503
        logger.warning(f"⚠️ [ListItems] Transient error for {provider}: {e}")
        raise_http_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "CONNECTOR_UNAVAILABLE",
            "Service temporarily unavailable. Please retry shortly.",
            {"provider": provider, "reason": str(e)},
        )
    except Exception as e:
        logger.error(f"❌ [ListItems] Failed to list items for {provider}: {e}")
        raise_http_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "CONNECTOR_FAILED",
            "Failed to list items.",
            {"provider": provider, "reason": str(e)},
        )


# =============================================================================
# Web Crawl Configuration Endpoints
# =============================================================================

@router.get("/integrations/web/crawl", response_model=WebCrawlConfigListResponse)
@limiter.limit("60/minute")
async def list_web_crawl_configs(
    request: Request,
    user_id: str = Depends(get_current_user),
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    """
    List user's web crawl configurations.

    Supports filtering by status:
    - pending: Queued for crawling
    - discovering: Finding URLs
    - processing: Actively crawling
    - completed: Successfully finished
    - failed: Encountered errors
    - cancelled: Manually cancelled

    Results are ordered by created_at descending (newest first).
    """

    supabase = get_supabase()

    try:
        # Build query
        query = supabase.table("web_crawl_configs")\
            .select("*", count="exact")\
            .eq("user_id", user_id)

        # Apply status filter if provided
        if status:
            valid_statuses = {"pending", "discovering", "processing", "completed", "failed", "cancelled"}
            if status not in valid_statuses:
                raise HTTPException(status_code=400, detail="Invalid status. Must be one of: pending, discovering, processing, completed, failed, cancelled")  # ALLOWED: literal
            query = query.eq("status", status)

        # Execute with pagination
        result = query\
            .order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()

        total = result.count if result.count is not None else 0
        items = [WebCrawlConfigResponse(
            id=str(config["id"]),
            root_url=config["root_url"],
            crawl_type=config["crawl_type"],
            status=config["status"],
            max_depth=config["max_depth"],
            max_pages=config.get("max_pages", 500),
            allow_subdomains=config.get("allow_subdomains", False),
            total_pages_found=config.get("total_pages_found", 0),
            pages_ingested=config.get("pages_ingested", 0),
            pages_failed=config.get("pages_failed", 0),
            error_message=config.get("error_message"),
            created_at=config.get("created_at"),
            updated_at=config.get("updated_at"),
            completed_at=config.get("completed_at"),
        ) for config in (result.data or [])]

        return WebCrawlConfigListResponse(
            items=items,
            total=total,
            has_more=(offset + limit) < total
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list web crawl configs: {e}")
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "list_web_crawl_configs")


@router.get("/integrations/web/crawl/active", response_model=WebCrawlConfigResponse | None)
@limiter.limit("120/minute")
async def get_active_web_crawl(
    request: Request,
    user_id: str = Depends(get_current_user),
):
    """
    Get the user's most recent active web crawl (if any).

    Active statuses: pending, discovering, processing

    Returns None (204) if no active crawl exists.
    Used by frontend to restore crawl state after navigation.
    """
    supabase = get_supabase()

    try:
        # Query for active crawls
        result = supabase.table("web_crawl_configs")\
            .select("*")\
            .eq("user_id", user_id)\
            .in_("status", ["pending", "discovering", "processing"])\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()

        if not result.data:
            return None

        config = result.data[0]
        return WebCrawlConfigResponse(
            id=str(config["id"]),
            root_url=config["root_url"],
            crawl_type=config["crawl_type"],
            status=config["status"],
            max_depth=config["max_depth"],
            max_pages=config.get("max_pages", 500),
            allow_subdomains=config.get("allow_subdomains", False),
            total_pages_found=config.get("total_pages_found", 0),
            pages_ingested=config.get("pages_ingested", 0),
            pages_failed=config.get("pages_failed", 0),
            error_message=config.get("error_message"),
            created_at=config.get("created_at"),
            updated_at=config.get("updated_at"),
            completed_at=config.get("completed_at"),
        )

    except Exception as e:
        logger.error(f"Failed to get active web crawl: {e}")
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "get_active_web_crawl")


@router.get("/integrations/web/crawl/{config_id}", response_model=WebCrawlConfigResponse)
@limiter.limit("60/minute")
async def get_web_crawl_config(
    request: Request,
    config_id: str,
    user_id: str = Depends(get_current_user),
):
    """
    Get a specific web crawl configuration by ID.

    Ensures users can only access their own configurations (RLS enforced).
    """
    supabase = get_supabase()

    try:
        result = supabase.table("web_crawl_configs")\
            .select("*")\
            .eq("id", config_id)\
            .eq("user_id", user_id)\
            .maybe_single()\
            .execute()

        if not result or not result.data:
            raise HTTPException(status_code=404, detail="Crawl configuration not found")  # ALLOWED: literal

        config = result.data
        return WebCrawlConfigResponse(
            id=str(config["id"]),
            root_url=config["root_url"],
            crawl_type=config["crawl_type"],
            status=config["status"],
            max_depth=config["max_depth"],
            max_pages=config.get("max_pages", 500),
            allow_subdomains=config.get("allow_subdomains", False),
            total_pages_found=config.get("total_pages_found", 0),
            pages_ingested=config.get("pages_ingested", 0),
            pages_failed=config.get("pages_failed", 0),
            error_message=config.get("error_message"),
            created_at=config.get("created_at"),
            updated_at=config.get("updated_at"),
            completed_at=config.get("completed_at"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get web crawl config: {e}")
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "get_web_crawl_config")


@router.post("/integrations/web/crawl", status_code=202)
@limiter.limit("10/minute")
async def crawl_web(
    request: Request,
    body: WebCrawlRequest,
    user_id: str = Depends(require_editor)
):
    """Queue a web crawl with best-practice defaults."""
    try:
        feature_check = await check_feature_access(UUID(user_id), "web_crawl")
        if not feature_check["allowed"]:
            raise HTTPException(status_code=403, detail="Web crawl is not available on your current plan.")  # ALLOWED: literal

        connector = WebConnector()
        normalized_url = connector.normalize_url(body.url)
        if not normalized_url:
            raise HTTPException(status_code=400, detail="Invalid URL for crawling.")  # ALLOWED: literal
        if not connector._is_safe_url(normalized_url):
            raise HTTPException(status_code=400, detail="URL is not allowed for crawling.")  # ALLOWED: literal

        crawl_type = body.crawl_type.lower()
        if crawl_type not in {"single", "recursive", "sitemap"}:
            raise HTTPException(status_code=400, detail="Invalid crawl_type.")  # ALLOWED: literal

        max_depth = body.max_depth if crawl_type == "recursive" else 1
        max_pages = body.max_pages
        if crawl_type == "single":
            max_pages = 1

        try:
            organization_id = await team_service.get_organization_id(user_id)
            result = queue_web_crawl(
                user_id=user_id,
                organization_id=organization_id,
                root_url=normalized_url,
                crawl_type=crawl_type,
                max_depth=max_depth,
                respect_robots=body.respect_robots,
                max_pages=max_pages,
                allow_subdomains=body.allow_subdomains,
                include_job_id=True,
            )
        except Exception as crawl_exc:
            logger.error("❌ [Crawl] Queue failed for %s: %s", normalized_url, crawl_exc)
            raise HTTPException(status_code=500, detail="Failed to queue web crawl.")  # ALLOWED: literal

        return {
            "status": "queued",
            "crawl_id": result["crawl_id"],
            "task_id": result["task_id"],
            "job_id": result.get("job_id"),
            "root_url": normalized_url,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [Crawl] Failed to queue web crawl (unexpected): {e}")
        raise HTTPException(status_code=500, detail="Failed to queue web crawl.")  # ALLOWED: literal


@router.delete("/integrations/web/crawl/{config_id}")
@limiter.limit("10/minute")
async def delete_crawl_config(
    request: Request,
    config_id: str,
    user_id: str = Depends(require_editor)
):
    """
    Delete a web crawl configuration.

    This will:
    - Cancel any running crawl task
    - Delete the configuration record
    - Optionally cascade delete associated documents (via FK/trigger)
    """
    supabase = get_supabase()

    try:
        # Verify ownership
        config_response = supabase.table("web_crawl_configs")\
            .select("id, celery_task_id, status")\
            .eq("id", config_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()

        if not config_response.data:
            raise HTTPException(status_code=404, detail="Crawl configuration not found")  # ALLOWED: literal

        config = config_response.data

        # Cancel running task if exists
        if config.get("celery_task_id") and config.get("status") in ["pending", "processing"]:
            try:
                from celery.result import AsyncResult

                from core.celery_app import celery_app

                result = AsyncResult(config["celery_task_id"], app=celery_app)
                result.revoke(terminate=True)
                logger.info(f"🛑 [Crawl] Cancelled task {config['celery_task_id']}")
            except Exception as e:
                logger.warning(f"⚠️ [Crawl] Failed to cancel task: {e}")

        # Delete the configuration
        supabase.table("web_crawl_configs")\
            .delete()\
            .eq("id", config_id)\
            .eq("user_id", user_id)\
            .execute()

        logger.info(f"🗑️ [Crawl] Deleted crawl config {config_id}")

        return {
            "status": "success",
            "message": "Crawl configuration deleted",
            "config_id": config_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete crawl config: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete crawl configuration")  # ALLOWED: literal


@router.post("/integrations/{provider}/ingest", status_code=202)
@limiter.limit("10/minute")
async def ingest_provider_items(
    request: Request,
    provider: str,
    body: IngestRequest,
    user_id: str = Depends(require_editor)
):
    """
    Ingest items from a provider (Download, Parse, Embed, Store).

    This endpoint returns 202 Accepted immediately and processes
    files asynchronously via Celery worker. Creates an ingestion job
    for progress tracking.
    """
    try:
        provider = _require_provider(provider)
        org_id, plan_code = await _resolve_org_and_plan(user_id)
        try:
            check_admission(
                org_id=org_id,
                plan_code=plan_code,
                file_size_bytes=None,
                job_count_increment=max(1, len(body.item_ids)),
            )
        except QuotaExceededError as exc:
            logger.warning("🚫 Admission denied for Org %s: %s", org_id, exc)
            raise_http_error(
                status.HTTP_403_FORBIDDEN,
                "PLAN_LIMIT_EXCEEDED",
                str(exc),
                exc.details if isinstance(exc, QuotaExceededError) else None,
            )

        if provider == "web":
            if len(body.item_ids) != 1:
                raise HTTPException(
                    status_code=400,
                    detail="Web ingest supports a single URL. Use /integrations/web/crawl for advanced options."
                )  # ALLOWED: literal

            feature_check = await check_feature_access(UUID(user_id), "web_crawl")
            if not feature_check["allowed"]:
                raise HTTPException(status_code=403, detail="Web crawl is not available on your current plan.")  # ALLOWED: literal

            connector = WebConnector()
            normalized_url = connector.normalize_url(body.item_ids[0])
            if not normalized_url:
                raise HTTPException(status_code=400, detail="Invalid URL for crawling.")  # ALLOWED: literal
            if not connector._is_safe_url(normalized_url):
                raise HTTPException(status_code=400, detail="URL is not allowed for crawling.")  # ALLOWED: literal

            result = queue_web_crawl(
                user_id=user_id,
                organization_id=org_id,
                root_url=normalized_url,
                crawl_type="single",
                max_depth=1,
                respect_robots=True,
                max_pages=1,
                allow_subdomains=False,
                include_job_id=True,
            )

            try:
                increment_usage(org_id=org_id, storage_bytes=None, job_count_increment=1)
            except Exception as exc:
                logger.warning("⚠️ [Quotas] Failed to increment usage for %s: %s", org_id, exc)

            audit_logger.log_sync(
                user_id=user_id,
                action="ingest.queued",
                resource_type="web_crawl",
                resource_id=result.get("crawl_id"),
                details={
                    "provider": "web",
                    "root_url": normalized_url,
                    "job_id": result.get("job_id"),
                    "task_id": result.get("task_id"),
                },
            )

            return {
                "status": "queued",
                "crawl_id": result["crawl_id"],
                "task_id": result["task_id"],
                "job_id": result.get("job_id"),
                "root_url": normalized_url,
            }

        # 1. Get user's credentials for this provider
        supabase = get_supabase()

        # Find connector definition
        conn_def = supabase.table("connector_definitions").select("id").eq("type", provider).single().execute()
        if not conn_def.data:
            raise HTTPException(status_code=400, detail="Unknown or unsupported provider")  # ALLOWED: literal

        # Get user's integration
        try:
            integration_res = supabase.table("user_integrations").select(
                "id, access_token, refresh_token, credentials"
            ).eq("user_id", user_id).eq("connector_definition_id", conn_def.data['id']).single().execute()
            integration = integration_res.data if integration_res.data else None
        except Exception as e:
            logger.warning(f"⚠️ [Ingest] Failed to fetch integration: {e}")
            integration = None

        # Prepare credentials based on connector type
        if provider in ["google_drive", "notion", "onedrive", "sharepoint", "dropbox", "github", "box"]:
            # OAuth connectors: Pass integration_id for automatic token refresh
            if not integration or not integration.get('access_token'):
                raise HTTPException(status_code=401, detail="Not connected to this provider. Please reconnect.")  # ALLOWED: literal

            credentials = {
                "integration_id": str(integration['id'])  # ✅ Pass integration_id for token refresh
            }
            logger.info(f"📥 [Ingest] Passing integration_id for OAuth connector: {provider}")
        else:
            # Other connectors: Use stored credentials
            if not integration or not integration.get('credentials'):
                raise HTTPException(status_code=401, detail="Not connected to this provider")  # ALLOWED: literal
            credentials = integration['credentials']

        # 2. Create ingestion job for progress tracking
        from datetime import datetime
        job_data = {
            "user_id": user_id,
            "organization_id": org_id,
            "provider": provider,
            "total_files": len(body.item_ids),
            "processed_files": 0,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        job_response = supabase.table("ingestion_jobs").insert(job_data).execute()
        if not job_response.data:
            raise HTTPException(status_code=500, detail="Failed to create ingestion job")  # ALLOWED: literal

        job_id = job_response.data[0]["id"]
        logger.info(f"📋 [Ingest] Created job {job_id} for {len(body.item_ids)} items")

        # 3. Queue the unified ingestion task
        from worker.tasks import unified_ingest_task

        try:
            task = unified_ingest_task.delay(
                user_id=user_id,
                job_id=str(job_id),
                connector_type=provider,
                item_ids=body.item_ids,
                credentials=credentials,
                plan_code=plan_code,
                dispatch_batch_size=_get_ingest_batch_size(),
            )
        except Exception as e:
            logger.error(f"❌ [Ingest] Failed to queue task for job {job_id}: {e}")
            supabase.table("ingestion_jobs").update({
                "status": "failed",
                "error_message": "Failed to queue ingestion task. Please try again.",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", job_id).execute()
            raise HTTPException(
                status_code=503,
                detail="Background worker is temporarily unavailable. Please try again in a few minutes."
            )
        try:
            increment_usage(org_id=org_id, storage_bytes=None, job_count_increment=max(1, len(body.item_ids)))
        except Exception as exc:
            logger.warning("⚠️ [Quotas] Failed to increment usage for %s: %s", org_id, exc)

        logger.info(f"📥 [Ingest] Queued task {task.id} for job {job_id}")
        audit_logger.log_sync(
            user_id=user_id,
            action="ingest.queued",
            resource_type="ingestion_job",
            resource_id=str(job_id),
            details={"provider": provider, "item_count": len(body.item_ids), "task_id": task.id},
        )

        # 4. Return 202 Accepted with job info
        return {
            "status": "accepted",
            "message": f"Ingestion queued for {len(body.item_ids)} items",
            "task_id": task.id,
            "job_id": str(job_id)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [Ingest] Failed to queue task: {e}")
        raise api_error(ApiErrorCode.PROCESSING_ERROR, e, "ingest_items")


# =============================================================================
# SYNC WORKER (Background Task)
# =============================================================================

async def run_background_sync(job_id: str, provider: str, user_id: str, integration_id: str):
    """
    Background wrapper to run a full provider sync through unified ingestion.
    """
    supabase = get_supabase()
    org_id, plan_code = await _resolve_org_and_plan(user_id)

    try:
        # 1. Update status to processing
        supabase.table("ingestion_jobs").update({
            "status": "processing",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", job_id).execute()

        log_connector_sync(
            user_id=user_id,
            connector_type=provider,
            status="start",
            details={"job_id": job_id},
        )

        supabase.table("ingestion_jobs").update({
            "progress": 1,
            "message": "Discovering files...",
            "status_message": "Discovering files...",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", job_id).execute()

        # 2. Resolve items to sync FROM EXISTING SCOPE IDENTITIES
        # Sync re-processes previously-ingested items only.
        # New items must be added via the "Browse" flow.
        # This prevents new scope creation and quota errors.
        scope_prefixes = get_scope_prefixes(provider)
        if not scope_prefixes:
            raise RuntimeError(f"No scope prefixes for provider '{provider}' — cannot sync")

        item_ids: list[str] = []
        query_failed = False

        # Use only the first (canonical) prefix — build_scope_uri() is the sole writer
        # of scope_identities and always emits the canonical form (e.g. "gdrive://").
        # Legacy aliases (drive://, google_drive://) are NOT expected in stored data.
        # disconnect_provider() loops ALL prefixes defensively for deletion safety,
        # but sync can rely on canonical-only. If legacy data is discovered, change
        # this to loop all prefixes.
        canonical_prefix = scope_prefixes[0]

        if canonical_prefix:
            try:
                scope_res = (
                    supabase.table("scope_identities")
                    .select("id")
                    .eq("organization_id", org_id)
                    .like("id", f"{canonical_prefix}%")
                    .execute()
                )
                for row in (scope_res.data or []):
                    item_ids.extend(extract_item_ids_from_scope(row["id"]))
            except Exception as e:
                logger.error(f"❌ [SyncJob] Failed to query scopes for {provider}: {e}")
                query_failed = True

        # Deduplicate while preserving order
        seen: set[str] = set()
        item_ids = [x for x in item_ids if not (x in seen or seen.add(x))]

        logger.info(f"[SyncJob] Resolved {len(item_ids)} item(s) from existing scopes for {provider}")

        if not item_ids and query_failed:
            raise RuntimeError(f"Scope query failed for {provider} — cannot determine items to sync")

        if not item_ids:
            supabase.table("ingestion_jobs").update({
                "status": "completed",
                "processed_files": 0,
                "message": "No items to sync",
                "status_message": "No items to sync",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", job_id).execute()
            logger.info(f"✅ [SyncJob] Completed {job_id}: no items to sync")
            log_connector_sync(
                user_id=user_id,
                connector_type=provider,
                status="success",
                details={"job_id": job_id, "reason": "no_items"},
            )
            return

        supabase.table("ingestion_jobs").update({
            "total_files": len(item_ids),
            "message": f"Queued sync for {len(item_ids)} items",
            "status_message": f"Queued sync for {len(item_ids)} items",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", job_id).execute()

        credentials = None
        if provider in {"google_drive", "notion", "onedrive", "sharepoint", "dropbox"}:
            credentials = {"integration_id": integration_id}

        from worker.tasks import unified_ingest_task
        try:
            check_admission(
                org_id=org_id,
                plan_code=plan_code,
                file_size_bytes=None,
                job_count_increment=max(1, len(item_ids)),
            )
        except QuotaExceededError as exc:
            logger.warning("🚫 Admission denied for Org %s: %s", org_id, exc)
            supabase.table("ingestion_jobs").update({
                "status": "failed",
                "error_message": str(exc),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", job_id).execute()
            log_connector_sync(
                user_id=user_id,
                connector_type=provider,
                status="fail",
                details={"job_id": job_id, "reason": str(exc)},
            )
            return

        task = unified_ingest_task.delay(
            user_id=user_id,
            job_id=str(job_id),
            connector_type=provider,
            item_ids=item_ids,
            credentials=credentials,
            plan_code=plan_code,
            dispatch_batch_size=_get_ingest_batch_size(),
            is_sync=True,
        )

        logger.info(f"✅ [SyncJob] Queued unified ingest {task.id} for job {job_id}")
        log_connector_sync(
            user_id=user_id,
            connector_type=provider,
            status="success",
            details={"job_id": job_id, "task_id": task.id, "item_count": len(item_ids)},
        )
        try:
            increment_usage(org_id=org_id, storage_bytes=None, job_count_increment=max(1, len(item_ids)))
        except Exception as exc:
            logger.warning("⚠️ [Quotas] Failed to increment usage for %s: %s", org_id, exc)

    except Exception as e:
        logger.error(f"❌ [SyncJob] Failed {job_id}: {e}")

        # Determine strict error message
        error_msg = str(e)
        if "invalid_grant" in error_msg or "Token has been expired" in error_msg or "reconnection" in error_msg:
            error_msg = "Authentication failed. Please reconnect integration."

            # Since we can't update user_integrations.status (no column), we just log heavily
            # Ideally we would set user_integrations.connected = False or similar if schema allowed
            logger.critical(f"🚨 [SyncJob] Auth failure for provider {provider}. User interaction required.")

        supabase.table("ingestion_jobs").update({
            "status": "failed",
            "error_message": error_msg,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", job_id).execute()
        log_connector_sync(
            user_id=user_id,
            connector_type=provider,
            status="fail",
            details={"job_id": job_id, "reason": error_msg},
        )


@router.post("/integrations/{integration_id}/sync")
@limiter.limit("10/minute")
async def sync_integration(
    request: Request,
    integration_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(require_editor)
):
    """
    Trigger a manual sync for an integration.
    Creates an ingestion job and runs sync in background.
    """
    supabase = get_supabase()

    try:
        # 1. Verify ownership and get provider type
        int_res = supabase.table("user_integrations").select(
            "id, connector_definition_id, connector_definitions(type)"
        ).eq("id", integration_id).eq("user_id", user_id).single().execute()

        if not int_res.data:
            raise HTTPException(status_code=404, detail="Integration not found")  # ALLOWED: literal

        provider = int_res.data["connector_definitions"]["type"]
        org_id, _ = await _resolve_org_and_plan(user_id)

        # 2. Rate limit check (simple check for pending jobs)
        existing_jobs = supabase.table("ingestion_jobs").select("id").eq(
            "user_id", user_id
        ).eq("provider", provider).eq("status", "pending").execute()

        if len(existing_jobs.data) > 0:
            # Allow retry for debugging, but typically block
            # raise HTTPException(status_code=429, detail="A sync is already pending")
            pass

        # 3. Create ingestion job
        job_data = {
            "user_id": user_id,
            "organization_id": org_id,
            "provider": provider,
            "total_files": 0,
            "processed_files": 0,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        job_res = supabase.table("ingestion_jobs").insert(job_data).execute()
        if not job_res.data:
            raise HTTPException(status_code=500, detail="Failed to create ingestion job")  # ALLOWED: literal

        job_id = job_res.data[0]["id"]

        # 4. Dispatch Background Task
        background_tasks.add_task(run_background_sync, job_id, provider, user_id, integration_id)

        return {
            "status": "accepted",
            "job_id": job_id,
            "message": f"Sync started for {provider}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [Sync] Failed to trigger sync: {e}")
        raise api_error(ApiErrorCode.PROCESSING_ERROR, e, "sync_integration")


# =============================================================================
# Sync History Endpoint
# =============================================================================

@router.get("/integrations/{integration_id}/sync-history")
async def get_sync_history(
    integration_id: str,
    user_id: str = Depends(get_current_user),
    limit: int = 20
):
    """
    Get sync history for an integration.

    Returns the sync_state records showing when syncs occurred,
    their status, and any associated metadata.
    """
    supabase = get_supabase()

    try:
        # First verify ownership of the integration
        int_check = supabase.table("user_integrations")\
            .select("id, connector_definitions(type)")\
            .eq("id", integration_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()

        if not int_check.data:
            raise HTTPException(status_code=404, detail="Integration not found")  # ALLOWED: literal

        provider = int_check.data["connector_definitions"]["type"]

        # Fetch sync_state records for this user and provider
        sync_response = supabase.table("sync_state")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("provider", provider)\
            .order("updated_at", desc=True)\
            .limit(limit)\
            .execute()

        return {
            "integration_id": integration_id,
            "provider": provider,
            "history": sync_response.data or []
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get sync history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get sync history")  # ALLOWED: literal


# =============================================================================
# Ingested Files Endpoint (for FileBrowser "already added" indicator)
# =============================================================================

class IngestedFilesResponse(BaseModel):
    """Response model for ingested files lookup."""
    source_type: str
    ingested_ids: list[str]
    total_count: int


@router.get("/integrations/{provider}/ingested-files", response_model=IngestedFilesResponse)
@limiter.limit("60/minute")
async def get_ingested_files(
    request: Request,
    provider: str,
    user_id: str = Depends(get_current_user),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    Get list of file IDs that have already been ingested from a specific connector.

    Used by FileBrowser to show "already added" indicators for files that
    are already in the knowledge base.

    Returns:
        - source_type: Normalized provider name
        - ingested_ids: List of source_id values (original file IDs from the connector)
        - total_count: Total number of ingested files from this source
    """
    supabase = get_supabase()

    try:
        # Normalize provider name
        canonical_provider = _require_provider(provider)

        # Query documents table for this source type within the organization
        # The source_id field contains the original file ID from the connector
        docs_response = supabase.table("documents")\
            .select("source_id")\
            .eq("organization_id", organization_id)\
            .eq("source_type", canonical_provider)\
            .execute()

        # Extract unique source_ids (filter out None values)
        ingested_ids = list({
            str(d["source_id"])
            for d in (docs_response.data or [])
            if d.get("source_id")
        })

        logger.debug(
            f"[IngestedFiles] Found {len(ingested_ids)} ingested files "
            f"for {canonical_provider} in org {organization_id}"
        )

        return IngestedFilesResponse(
            source_type=canonical_provider,
            ingested_ids=ingested_ids,
            total_count=len(ingested_ids),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get ingested files for {provider}: {e}")
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "get_ingested_files")
