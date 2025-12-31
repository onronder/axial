"""
Integrations API Endpoints

Provides dynamic connector discovery, OAuth handling, and integration management.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, Field
from core.security import get_current_user, encrypt_token
from core.db import get_supabase
from core.config import settings
from core.rate_limit import limiter
from google_auth_oauthlib.flow import Flow
from datetime import datetime, timedelta, timezone
from typing import Optional, List
import logging
import httpx

logger = logging.getLogger(__name__)
router = APIRouter()


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
    user_id: str = Depends(get_current_user)
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
        
        logger.info(f"🔐 [OAuth] ✅ Upsert result: {upsert_res.data}")
        
        if not upsert_res.data:
            logger.error("🔐 [OAuth] ❌ Upsert returned no data!")
            raise HTTPException(status_code=500, detail="Database upsert returned no data")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🔐 [OAuth] ❌ Database error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    # 5. Schedule background sync
    integration_id = upsert_res.data[0]["id"]
    try:
        from connectors.drive import DriveConnector
        connector = DriveConnector()
        background_tasks.add_task(connector.sync, user_id, integration_id)
        logger.info(f"🔐 [OAuth] Scheduled background sync for integration {integration_id}")
    except Exception as e:
        logger.warning(f"🔐 [OAuth] Failed to schedule sync: {e}")
        # Don't fail the OAuth just because sync scheduling failed

    return {"status": "success", "provider": "google_drive", "integration_id": integration_id}


@router.post("/integrations/notion/exchange")
async def exchange_notion_token(
    request: ExchangeRequest,
    user_id: str = Depends(get_current_user)
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
        
        logger.info(f"🔐 [OAuth] ✅ Upsert result: {upsert_res.data}")
        
        if not upsert_res.data:
            logger.error("🔐 [OAuth] ❌ Upsert returned no data!")
            raise HTTPException(status_code=500, detail="Database upsert returned no data")
        
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
        from connectors.notion import NotionConnector
        from worker.tasks import ingest_file_task
        
        connector = NotionConnector()
        
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
                # Queue the ingestion task
                task = ingest_file_task.delay(
                    user_id=user_id,
                    provider="notion",
                    item_ids=items,
                    credentials={"access_token": access_token},
                    job_id=str(job_id)
                )
                logger.info(f"📥 [OAuth] Auto-ingestion started: {len(items)} pages, job {job_id}, task {task.id}")
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
    user_id: str = Depends(get_current_user)
):
    """Disconnect a provider integration."""
    supabase = get_supabase()
    
    try:
        # Lookup connector definition by type
        def_res = supabase.table("connector_definitions").select("id").eq("type", provider).single().execute()
        if not def_res.data:
            raise HTTPException(status_code=404, detail="Unknown provider")
        
        connector_def_id = def_res.data["id"]
        
        # Delete the user integration
        supabase.table("user_integrations").delete().eq(
            "user_id", user_id
        ).eq("connector_definition_id", connector_def_id).execute()
        
        return {"status": "success", "provider": provider}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disconnect: {str(e)}")


# =============================================================================
# Provider Items & Ingestion
# =============================================================================

from connectors.factory import get_connector


@router.get("/integrations/{provider}/items")
async def list_provider_items(
    provider: str,
    parent_id: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """List items from a connected provider (folders, files, etc.)."""
    try:
        connector = get_connector(provider)
        items = await connector.list_items(user_id, parent_id)
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list items: {str(e)}")


@router.post("/integrations/{provider}/ingest", status_code=202)
async def ingest_provider_items(
    provider: str,
    request: IngestRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Ingest items from a provider (Download, Parse, Embed, Store).
    
    This endpoint returns 202 Accepted immediately and processes
    files asynchronously via Celery worker. Creates an ingestion job
    for progress tracking.
    """
    try:
        # 1. Get user's credentials for this provider
        supabase = get_supabase()
        
        # Find connector definition
        conn_def = supabase.table("connector_definitions").select("id").eq("type", provider).single().execute()
        if not conn_def.data:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
        
        # Get user's integration with credentials
        # Use maybe_single() or handle PGRST116 manually since not all providers require connection
        try:
            integration_res = supabase.table("user_integrations").select("credentials").eq("user_id", user_id).eq("connector_definition_id", conn_def.data['id']).execute()
            integration_data = integration_res.data[0] if integration_res.data else None
        except Exception as e:
            logger.warning(f"⚠️ [Ingest] Failed to fetch integration: {e}")
            integration_data = None
        
        # Web provider doesn't require explicit connection, others do
        if provider == "web":
             credentials = {}
             if integration_data:
                 credentials = integration_data.get('credentials', {}) or {}
        else:
            if not integration_data or not integration_data.get('credentials'):
                raise HTTPException(status_code=401, detail=f"Not connected to {provider}")
            credentials = integration_data['credentials']
        
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
        
        # 3. Queue the ingestion task with job_id
        from worker.tasks import ingest_file_task
        
        task = ingest_file_task.delay(
            user_id=user_id,
            provider=provider,
            item_ids=request.item_ids,
            credentials=credentials,
            job_id=str(job_id)
        )
        
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


