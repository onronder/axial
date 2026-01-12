"""
Integrations API Endpoints

Provides dynamic connector discovery, OAuth handling, and integration management.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, Field
from core.security import get_current_user, encrypt_token, decrypt_token
from core.db import get_supabase
from core.config import settings
from core.rate_limit import limiter
from api.v1.dependencies import validate_team_access, require_editor
from services.quotas import check_admission, increment_usage
from services.team_service import team_service
from core.exceptions import QuotaExceededError
from services.usage import check_feature_access
from services.web_crawl import queue_web_crawl
from connectors.web import WebConnector
from core.ingestion_utils import require_canonical_provider
from connectors.registry import get_connector_manifest
from google_auth_oauthlib.flow import Flow
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from uuid import UUID
import logging
import httpx

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(validate_team_access)])


def _require_provider(provider: str) -> str:
    try:
        canonical = require_canonical_provider(provider)
        manifest = get_connector_manifest(canonical)
        if not manifest:
            raise ValueError(f"Unknown provider: {provider}")
        return canonical
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
    description: Optional[str] = None
    icon_path: Optional[str] = None
    category: Optional[str] = None
    is_active: bool = True


class UserIntegrationOut(BaseModel):
    id: str
    connector_definition_id: str
    connector_type: str
    connector_name: str
    connector_icon: Optional[str] = None
    category: Optional[str] = None
    connected: bool = True
    last_sync_at: Optional[datetime] = None


class IngestRequest(BaseModel):
    """Ingestion request with validation."""
    item_ids: List[str] = Field(..., max_length=100)  # Max 100 items per request


class WebCrawlRequest(BaseModel):
    """Web crawl request with validation."""
    url: str = Field(..., min_length=1, max_length=2048)
    crawl_type: str = Field(default="single")
    max_depth: int = Field(default=1, ge=1, le=10)
    respect_robots: bool = Field(default=True)
    max_pages: int = Field(default=500, ge=1, le=10000)
    allow_subdomains: bool = Field(default=False)


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

@router.get("/integrations/available", response_model=List[ConnectorDefinitionOut])
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
        raise HTTPException(status_code=500, detail="Failed to fetch available connectors")


@router.get("/integrations/status", response_model=List[UserIntegrationOut])
@limiter.limit("60/minute")
async def get_user_integrations(
    request: Request,
    user_id: str = Depends(get_current_user)
):
    """
    Returns all of the user's connected integrations with definition details.
    Joins user_integrations with connector_definitions for rich response.
    """
    supabase = get_supabase()
    
    try:
        # Join user_integrations with connector_definitions
        response = supabase.table("user_integrations").select(
            "id, connector_definition_id, last_sync_at, "
            "connector_definitions(type, name, icon_path, category)"
        ).eq("user_id", user_id).execute()
        
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
        raise HTTPException(status_code=500, detail="Failed to fetch integrations")


# =============================================================================
# OAuth Token Exchange (Fixed Persistence)
# =============================================================================

@router.post("/integrations/google/exchange")
async def exchange_google_token(
    request: ExchangeRequest,
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
        raise HTTPException(status_code=500, detail="Google credentials not configured")

    supabase = get_supabase()

    # 1. Look up connector_definition_id for google_drive
    try:
        def_response = supabase.table("connector_definitions").select("id").eq("type", "google_drive").single().execute()
        if not def_response.data:
            raise HTTPException(status_code=500, detail="google_drive connector not found in definitions")
        connector_definition_id = def_response.data["id"]
        logger.info(f"🔐 [OAuth] Found connector_definition_id: {connector_definition_id}")
    except Exception as e:
        logger.error(f"🔐 [OAuth] Failed to lookup connector definition: {e}")
        raise HTTPException(status_code=500, detail="Failed to lookup connector definition")

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
        
        flow.fetch_token(code=request.code)
        creds = flow.credentials
        logger.info(f"🔐 [OAuth] ✅ Got credentials. Has refresh token: {creds.refresh_token is not None}")
        
    except Exception as e:
        logger.error(f"🔐 [OAuth] ❌ Token exchange failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {str(e)}")

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
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    logger.info(f"🔐 [OAuth] Tokens encrypted before storage")
    
    logger.info(f"🔐 [OAuth] Upserting to user_integrations: user_id={user_id}, connector_def={connector_definition_id}")
    
    try:
        # Upsert: insert or update on conflict
        upsert_res = supabase.table("user_integrations").upsert(
            data,
            on_conflict="user_id,connector_definition_id"
        ).execute()
        
        if not upsert_res.data:
            logger.error("🔐 [OAuth] ❌ Upsert returned no data!")
            raise HTTPException(status_code=500, detail="Database upsert returned no data")
         
        logger.info(f"🔐 [OAuth] ✅ Upsert successful for integration ID: {upsert_res.data[0]['id']}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🔐 [OAuth] ❌ Database error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

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
    logger.info(f"🔐 [OAuth] Connected Google Drive (integration: {integration_id}). User can now select files to ingest.")

    return {"status": "success", "provider": "google_drive", "integration_id": integration_id}


@router.post("/integrations/notion/exchange")
async def exchange_notion_token(
    request: ExchangeRequest,
    user_id: str = Depends(require_editor)
):
    """
    Exchange Notion OAuth code for tokens and persist to user_integrations.
    Uses httpx for async HTTP request to Notion API.
    """
    logger.info(f"🔐 [OAuth] Starting Notion token exchange for user: {user_id}")
    
    if not settings.NOTION_CLIENT_ID or not settings.NOTION_CLIENT_SECRET:
        logger.error("🔐 [OAuth] Notion credentials not configured!")
        raise HTTPException(status_code=500, detail="Notion credentials not configured")
    
    if not settings.NOTION_REDIRECT_URI:
        logger.error("🔐 [OAuth] Notion redirect URI not configured!")
        raise HTTPException(status_code=500, detail="Notion redirect URI not configured")

    supabase = get_supabase()

    # 1. Look up connector_definition_id for notion
    try:
        def_response = supabase.table("connector_definitions").select("id").eq("type", "notion").single().execute()
        if not def_response.data:
            raise HTTPException(status_code=500, detail="notion connector not found in definitions")
        connector_definition_id = def_response.data["id"]
        logger.info(f"🔐 [OAuth] Found connector_definition_id: {connector_definition_id}")
    except Exception as e:
        logger.error(f"🔐 [OAuth] Failed to lookup connector definition: {e}")
        raise HTTPException(status_code=500, detail="Failed to lookup connector definition")

    # 2. Exchange Code for Tokens using httpx
    try:
        logger.info(f"🔐 [OAuth] Redirect URI: {settings.NOTION_REDIRECT_URI}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.notion.com/v1/oauth/token",
                auth=(settings.NOTION_CLIENT_ID, settings.NOTION_CLIENT_SECRET),
                json={
                    "grant_type": "authorization_code",
                    "code": request.code,
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
                    detail=f"Notion token exchange failed: {response.json().get('error', 'Unknown error')}"
                )
            
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
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {str(e)}")

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
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    logger.info(f"🔐 [OAuth] Token encrypted before storage")
    logger.info(f"🔐 [OAuth] Upserting to user_integrations: user_id={user_id}, connector_def={connector_definition_id}")
    
    try:
        # Upsert: insert or update on conflict
        upsert_res = supabase.table("user_integrations").upsert(
            data,
            on_conflict="user_id,connector_definition_id"
        ).execute()
        
        if not upsert_res.data:
            logger.error("🔐 [OAuth] ❌ Upsert returned no data!")
            raise HTTPException(status_code=500, detail="Database upsert returned no data")

        logger.info(f"🔐 [OAuth] ✅ Upsert successful for integration ID: {upsert_res.data[0]['id']}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🔐 [OAuth] ❌ Database error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

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
                raise HTTPException(status_code=403, detail=str(exc))
            # Create ingestion job
            job_data = {
                "user_id": user_id,
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
                )
                logger.info(f"📥 [OAuth] Auto-ingestion started: {len(items)} pages, job {job_id}, task: {task.id}")
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
# Integration Management Endpoints
# =============================================================================

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
async def disconnect_provider(
    provider: str,
    user_id: str = Depends(require_editor)
):
    """
    Disconnect a provider integration.
    Attempts to revoke the OAuth token with the provider before deleting records.
    """
    supabase = get_supabase()
    provider = _require_provider(provider)
    
    try:
        # Lookup connector definition by type
        def_res = supabase.table("connector_definitions").select("id").eq("type", provider).single().execute()
        if not def_res.data:
            raise HTTPException(status_code=404, detail="Unknown provider")
        
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
                            logger.info(f"🔌 [Disconnect] Google token revoked")
                            
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
            ).in_("source_type", source_types).execute()
            
            deleted_docs = len(doc_result.data) if doc_result.data else 0
            logger.info(f"🧹 [Disconnect] Deleted {deleted_docs} documents")
        except Exception as e:
            logger.warning(f"⚠️ [Disconnect] Document cleanup failed: {e}")
        
        # 2b. Delete Ingestion Jobs and associated file statuses
        try:
            # First, find all job IDs for this provider
            jobs_res = supabase.table("ingestion_jobs").select("id").eq(
                "user_id", user_id
            ).eq("provider", provider).execute()
            
            job_ids = [job["id"] for job in (jobs_res.data or [])]
            
            # Delete file statuses for these jobs
            if job_ids:
                for job_id in job_ids:
                    supabase.table("ingestion_file_status").delete().eq("job_id", job_id).execute()
                logger.info(f"🧹 [Disconnect] Deleted file statuses for {len(job_ids)} jobs")
            
            # Then delete the jobs
            job_result = supabase.table("ingestion_jobs").delete().eq(
                "user_id", user_id
            ).eq("provider", provider).execute()
            
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
        
        return {
            "status": "success", 
            "provider": provider,
            "cleanup": {
                "documents_deleted": deleted_docs if 'deleted_docs' in dir() else 0,
                "jobs_deleted": deleted_jobs if 'deleted_jobs' in dir() else 0
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disconnect: {str(e)}")


# =============================================================================
# Provider Items & Ingestion
# =============================================================================

from connectors import get_connector


@router.get("/integrations/{provider}/items")
async def list_provider_items(
    provider: str,
    parent_id: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """List items from a connected provider (folders, files, etc.)."""
    try:
        provider = _require_provider(provider)
        connector = get_connector(provider)
        items = await connector.list_items(user_id, parent_id)
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list items: {str(e)}")


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
            raise HTTPException(status_code=403, detail=feature_check["reason"])

        connector = WebConnector()
        normalized_url = connector.normalize_url(body.url)
        if not normalized_url:
            raise HTTPException(status_code=400, detail="Invalid URL for crawling.")
        if not connector.is_safe_url(normalized_url):
            raise HTTPException(status_code=400, detail="URL is not allowed for crawling.")

        crawl_type = body.crawl_type.lower()
        if crawl_type not in {"single", "recursive", "sitemap"}:
            raise HTTPException(status_code=400, detail="Invalid crawl_type.")

        max_depth = body.max_depth if crawl_type == "recursive" else 1
        max_pages = body.max_pages
        if crawl_type == "single":
            max_pages = 1

        try:
            result = queue_web_crawl(
                user_id=user_id,
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
            raise HTTPException(status_code=500, detail="Failed to queue web crawl.")

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
        raise HTTPException(status_code=500, detail="Failed to queue web crawl.")


@router.delete("/integrations/web/crawl/{config_id}")
async def delete_crawl_config(
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
            raise HTTPException(status_code=404, detail="Crawl configuration not found")
        
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
        raise HTTPException(status_code=500, detail="Failed to delete crawl configuration")


@router.post("/integrations/{provider}/ingest", status_code=202)
async def ingest_provider_items(
    provider: str,
    request: IngestRequest,
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
                job_count_increment=max(1, len(request.item_ids)),
            )
        except QuotaExceededError as exc:
            logger.warning("🚫 Admission denied for Org %s: %s", org_id, exc)
            raise HTTPException(status_code=403, detail=str(exc))

        if provider == "web":
            if len(request.item_ids) != 1:
                raise HTTPException(
                    status_code=400,
                    detail="Web ingest supports a single URL. Use /integrations/web/crawl for advanced options."
                )

            feature_check = await check_feature_access(UUID(user_id), "web_crawl")
            if not feature_check["allowed"]:
                raise HTTPException(status_code=403, detail=feature_check["reason"])

            connector = WebConnector()
            normalized_url = connector.normalize_url(request.item_ids[0])
            if not normalized_url:
                raise HTTPException(status_code=400, detail="Invalid URL for crawling.")
            if not connector.is_safe_url(normalized_url):
                raise HTTPException(status_code=400, detail="URL is not allowed for crawling.")

            result = queue_web_crawl(
                user_id=user_id,
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
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
        
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
        if provider in ["google_drive", "notion"]:
            # OAuth connectors: Pass integration_id for automatic token refresh
            if not integration or not integration.get('access_token'):
                raise HTTPException(status_code=401, detail=f"Not connected to {provider}. Please reconnect.")
            
            credentials = {
                "integration_id": str(integration['id'])  # ✅ Pass integration_id for token refresh
            }
            logger.info(f"📥 [Ingest] Passing integration_id for OAuth connector: {provider}")
        else:
            # Other connectors: Use stored credentials
            if not integration or not integration.get('credentials'):
                raise HTTPException(status_code=401, detail=f"Not connected to {provider}")
            credentials = integration['credentials']
        
        # 2. Create ingestion job for progress tracking
        from datetime import datetime
        job_data = {
            "user_id": user_id,
            "provider": provider,
            "total_files": len(request.item_ids),
            "processed_files": 0,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        job_response = supabase.table("ingestion_jobs").insert(job_data).execute()
        if not job_response.data:
            raise HTTPException(status_code=500, detail="Failed to create ingestion job")
        
        job_id = job_response.data[0]["id"]
        logger.info(f"📋 [Ingest] Created job {job_id} for {len(request.item_ids)} items")
        
        # 3. Queue the unified ingestion task
        from worker.tasks import unified_ingest_task
        
        task = unified_ingest_task.delay(
            user_id=user_id,
            job_id=str(job_id),
            connector_type=provider,
            item_ids=request.item_ids,  # Pass all items at once
            credentials=credentials,
            plan_code=plan_code,
        )
        try:
            increment_usage(org_id=org_id, storage_bytes=None, job_count_increment=max(1, len(request.item_ids)))
        except Exception as exc:
            logger.warning("⚠️ [Quotas] Failed to increment usage for %s: %s", org_id, exc)
        
        logger.info(f"📥 [Ingest] Queued task {task.id} for job {job_id}")
        
        # 4. Return 202 Accepted with job info
        return {
            "status": "accepted",
            "message": f"Ingestion queued for {len(request.item_ids)} items",
            "task_id": task.id,
            "job_id": str(job_id)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [Ingest] Failed to queue task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to queue ingestion: {str(e)}")


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
        
        # 2. Get Connector
        from connectors import get_connector
        try:
            connector = get_connector(provider)
        except Exception:
            logger.error(f"❌ [SyncJob] Connector factory failed for {provider}")
            raise

        # 3. Resolve root items to sync
        root_items = await connector.list_items(user_id, parent_id=None)
        item_ids = [item.id for item in (root_items or [])]

        if not item_ids:
            supabase.table("ingestion_jobs").update({
                "status": "completed",
                "processed_files": 0,
                "message": "No items to sync",
                "status_message": "No items to sync",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", job_id).execute()
            logger.info(f"✅ [SyncJob] Completed {job_id}: no items to sync")
            return

        supabase.table("ingestion_jobs").update({
            "total_files": len(item_ids),
            "message": f"Queued sync for {len(item_ids)} items",
            "status_message": f"Queued sync for {len(item_ids)} items",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", job_id).execute()

        credentials = None
        if provider in {"google_drive", "notion"}:
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
            return

        task = unified_ingest_task.delay(
            user_id=user_id,
            job_id=str(job_id),
            connector_type=provider,
            item_ids=item_ids,
            credentials=credentials,
            plan_code=plan_code,
        )

        logger.info(f"✅ [SyncJob] Queued unified ingest {task.id} for job {job_id}")
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


@router.post("/integrations/{integration_id}/sync")
async def sync_integration(
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
            raise HTTPException(status_code=404, detail="Integration not found")
        
        provider = int_res.data["connector_definitions"]["type"]
        
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
            "provider": provider,
            "total_files": 0,
            "processed_files": 0,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        job_res = supabase.table("ingestion_jobs").insert(job_data).execute()
        if not job_res.data:
            raise HTTPException(status_code=500, detail="Failed to create ingestion job")
        
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
        raise HTTPException(status_code=500, detail=f"Failed to trigger sync: {str(e)}")


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
            raise HTTPException(status_code=404, detail="Integration not found")
        
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
        raise HTTPException(status_code=500, detail="Failed to get sync history")
