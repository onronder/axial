from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from core.security import get_current_user
from core.db import get_supabase
from core.config import settings
from google_auth_oauthlib.flow import Flow
from datetime import datetime, timedelta
import json

router = APIRouter()

class ExchangeRequest(BaseModel):
    code: str

@router.post("/integrations/google/exchange")
async def exchange_google_token(
    request: ExchangeRequest,
    user_id: str = Depends(get_current_user)
):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
         raise HTTPException(status_code=500, detail="Google credentials not configured")

    # 1. Exchange Code for Tokens
    try:
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
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {str(e)}")

    # 2. Store in Supabase
    supabase = get_supabase()
    
    expires_at = (datetime.utcnow() + timedelta(seconds=creds.expiry.timestamp() - datetime.now().timestamp() if creds.expiry else 3600)).isoformat()
    
    data = {
        "user_id": user_id,
        "provider": "google_drive",
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "expires_at": expires_at,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    # We rely on an upsert logic. Assuming 'user_id' + 'provider' is unique key or similar constraint.
    # If standard Supabase, we might need a unique constraint or primary key on (user_id, provider).
    # Trying upsert on conflict.
    
    try:
        # Check if exists to determine insert/update or just upsert if unique constraint exists
        # To be safe, we'll try to delete existing for this provider/user and insert new, 
        # or assume there's a unique constraint on (user_id, provider).
        # Let's try upsert assuming a unique constraint exists.
        
        res = supabase.table("user_integrations").upsert(data, on_conflict="user_id,provider").execute()
        
    except Exception as e:
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
