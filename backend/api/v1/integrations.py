from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from core.security import get_current_user
from core.db import get_supabase
from core.config import settings
from google_auth_oauthlib.flow import Flow
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class ExchangeRequest(BaseModel):
    code: str

@router.post("/integrations/google/exchange")
async def exchange_google_token(
    request: ExchangeRequest,
    user_id: str = Depends(get_current_user)
):
    logger.info(f"🔐 [OAuth] Starting Google token exchange for user: {user_id}")
    
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        logger.error("🔐 [OAuth] Google credentials not configured!")
        raise HTTPException(status_code=500, detail="Google credentials not configured")

    # 1. Exchange Code for Tokens
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

    # 2. Store in Supabase
    supabase = get_supabase()
    
    try:
        expires_at = None
        if creds.expiry:
            expires_at = creds.expiry.isoformat()
        else:
            expires_at = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    except Exception as e:
        logger.warning(f"🔐 [OAuth] Could not set expiry: {e}")
        expires_at = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    
    data = {
        "user_id": user_id,
        "provider": "google_drive",
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "expires_at": expires_at,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"🔐 [OAuth] Saving to user_integrations: user_id={user_id}, provider=google_drive")
    logger.info(f"🔐 [OAuth] Data (tokens redacted): expires_at={expires_at}, has_refresh={creds.refresh_token is not None}")
    
    try:
        # Delete existing record first (if any)
        del_res = supabase.table("user_integrations").delete().eq("user_id", user_id).eq("provider", "google_drive").execute()
        logger.info(f"🔐 [OAuth] Delete old record result: {del_res.data}")
        
        # Insert new record
        ins_res = supabase.table("user_integrations").insert(data).execute()
        logger.info(f"🔐 [OAuth] ✅ Insert result: {ins_res.data}")
        
        if not ins_res.data:
            logger.error("🔐 [OAuth] ❌ Insert returned no data!")
            raise HTTPException(status_code=500, detail="Database insert returned no data")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🔐 [OAuth] ❌ Database error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return {"status": "success", "provider": "google_drive"}


# --- Generic Integration Endpoints ---

from connectors.factory import get_connector
from typing import Optional, List

@router.get("/integrations/{provider}/status")
async def get_provider_status(
    provider: str,
    user_id: str = Depends(get_current_user)
):
    try:
        connector = get_connector(provider)
        is_connected = await connector.authorize(user_id)
        return {"connected": is_connected}
    except Exception:
        return {"connected": False}

@router.get("/integrations/status")
async def get_all_status(
    user_id: str = Depends(get_current_user)
):
    try:
        supabase = get_supabase()
        response = supabase.table("user_integrations").select("provider").eq("user_id", user_id).execute()
        
        connected_providers = {item['provider']: True for item in response.data}
        
        # Ensure we return false for known providers if not in DB
        # List of known providers could be dynamic, but hardcoding known ones for now
        all_providers = ["google_drive", "web"]
        
        status = {}
        for p in all_providers:
            status[p] = connected_providers.get(p, False)
            
        return status
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Failed to fetch statuses: {str(e)}")

@router.delete("/integrations/{provider}")
async def disconnect_provider(
    provider: str,
    user_id: str = Depends(get_current_user)
):
    try:
        supabase = get_supabase()
        response = supabase.table("user_integrations").delete().eq("user_id", user_id).eq("provider", provider).execute()
        
        # In a real app, we might also want to call provider revocation endpoint here.
        # e.g. https://accounts.google.com/o/oauth2/revoke?token={token}
        
        return {"status": "success", "provider": provider}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disconnect: {str(e)}")


@router.get("/integrations/{provider}/items")
async def list_provider_items(
    provider: str,
    parent_id: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    try:
        connector = get_connector(provider)
        items = await connector.list_items(user_id, parent_id)
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list items: {str(e)}")

class IngestRequest(BaseModel):
    item_ids: List[str]

@router.post("/integrations/{provider}/ingest")
async def ingest_provider_items(
    provider: str,
    request: IngestRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Generic ingestion endpoint for Source-based connectors (Drive, Web).
    Not used for direct File uploads.
    """
    try:
        connector = get_connector(provider)
        
        # 1. Ingest (Download & Parse)
        docs = await connector.ingest(user_id, request.item_ids)
        
        if not docs:
             return {"status": "skipped", "message": "No content processed"}

        supabase = get_supabase()
        
        # 2. Embed & Store (Should ideally be a shared Service - reusing logic from ingest.py roughly here)
        # For DRY, we duplicate simplified logic here or import.
        # Let's simple duplicate for MVP speed, then refactor to service.
        
        from langchain_openai import OpenAIEmbeddings
        embeddings_model = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.OPENAI_API_KEY
        )
        
        chunk_texts = [d.page_content for d in docs]
        chunk_embeddings = embeddings_model.embed_documents(chunk_texts)
        
        # Group docs by source item? Or just stream all chunks?
        # Current Schema: One Parent Document -> Many Chunks.
        # Here we might have multiple source items (Multiple Files).
        # We should create ONE Parent Document per source item.
        
        # Regroup by file_id?
        # Our ConnectorDocument metadata has 'file_id' or 'source_url'.
        
        # Group by unique source identifier
        from collections import defaultdict
        grouped = defaultdict(list)
        for i, doc in enumerate(docs):
            key = doc.metadata.get('source_url') or doc.metadata.get('file_id') or "unknown"
            grouped[key].append((doc, chunk_embeddings[i]))
            
        results = []
        
        for key, pairs in grouped.items():
            first_doc = pairs[0][0]
            
            # Create Parent
            parent_doc_data = {
                "user_id": user_id,
                "title": first_doc.metadata.get('title', 'Untitled'),
                "source_type": provider,
                "source_url": first_doc.metadata.get('source_url'),
                "metadata": first_doc.metadata,
                "created_at": datetime.utcnow().isoformat()
            }
            
            p_res = supabase.table("documents").insert(parent_doc_data).execute()
            if not p_res.data: continue
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
