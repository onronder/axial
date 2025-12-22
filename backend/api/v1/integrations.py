"""
Integrations API Endpoints

Provides dynamic connector discovery, OAuth handling, and integration management.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from core.security import get_current_user
from core.db import get_supabase
from core.config import settings
from google_auth_oauthlib.flow import Flow
from datetime import datetime, timedelta
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Pydantic Request/Response Models
# =============================================================================

class ExchangeRequest(BaseModel):
    code: str


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
    item_ids: List[str]


# =============================================================================
# Dynamic Connector Discovery Endpoints
# =============================================================================

@router.get("/integrations/available", response_model=List[ConnectorDefinitionOut])
async def get_available_connectors():
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
async def get_user_integrations(
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
            expires_at = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    except Exception as e:
        logger.warning(f"🔐 [OAuth] Could not set expiry: {e}")
        expires_at = (datetime.utcnow() + timedelta(hours=1)).isoformat()

    # 4. Upsert to user_integrations using the unique constraint
    data = {
        "user_id": user_id,
        "connector_definition_id": connector_definition_id,
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "expires_at": expires_at,
        "updated_at": datetime.utcnow().isoformat()
    }
    
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


@router.post("/integrations/{provider}/ingest")
async def ingest_provider_items(
    provider: str,
    request: IngestRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Ingest items from a provider (Download, Parse, Embed, Store).
    """
    try:
        connector = get_connector(provider)
        
        # 1. Ingest (Download & Parse)
        docs = await connector.ingest(user_id, request.item_ids)
        
        if not docs:
            return {"status": "skipped", "message": "No content processed"}

        supabase = get_supabase()
        
        # 2. Embed & Store
        from langchain_openai import OpenAIEmbeddings
        embeddings_model = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.OPENAI_API_KEY
        )
        
        chunk_texts = [d.page_content for d in docs]
        chunk_embeddings = embeddings_model.embed_documents(chunk_texts)
        
        # Group by source
        from collections import defaultdict
        grouped = defaultdict(list)
        for i, doc in enumerate(docs):
            key = doc.metadata.get('source_url') or doc.metadata.get('file_id') or "unknown"
            grouped[key].append((doc, chunk_embeddings[i]))
        
        results = []
        
        for key, pairs in grouped.items():
            first_doc = pairs[0][0]
            
            # Create Parent Document
            parent_doc_data = {
                "user_id": user_id,
                "title": first_doc.metadata.get('title', 'Untitled'),
                "source_type": provider,
                "source_url": first_doc.metadata.get('source_url'),
                "metadata": first_doc.metadata,
                "created_at": datetime.utcnow().isoformat()
            }
            
            p_res = supabase.table("documents").insert(parent_doc_data).execute()
            if not p_res.data:
                continue
            parent_id = p_res.data[0]['id']
            
            # Create Chunks
            chunk_records = []
            for idx, (doc, emb) in enumerate(pairs):
                chunk_records.append({
                    "document_id": parent_id,
                    "content": doc.page_content,
                    "embedding": emb,
                    "chunk_index": idx,
                    "created_at": datetime.utcnow().isoformat()
                })
            
            supabase.table("document_chunks").insert(chunk_records).execute()
            results.append(parent_id)

        return {"status": "success", "ingested_ids": results}

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")
