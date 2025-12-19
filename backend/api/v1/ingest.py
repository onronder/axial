from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from models import IngestResponse
from core.security import get_current_user
from core.db import get_supabase
from core.config import settings
from connectors.factory import get_connector
import uuid
import datetime
import json
from langchain_openai import OpenAIEmbeddings

router = APIRouter()

from typing import Optional

@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    drive_id: Optional[str] = Form(None),
    metadata: str = Form(...),
    user_id: str = Depends(get_current_user)
):
    supabase = get_supabase()
    
    # 0. Parse metadata JSON string
    try:
        meta_dict = json.loads(metadata)
    except Exception:
        meta_dict = {}

    # 1. Process via Connector (Parsing & Chunking)
    try:
        source_type = "file"
        
        if url:
             connector = get_connector("web")
             source_type = "web"
             # New BaseConnector Interface
             docs = await connector.ingest(user_id, [url])
        elif drive_id:
             connector = get_connector("drive")
             source_type = "drive"
             # New BaseConnector Interface
             docs = await connector.ingest(user_id, [drive_id])
        elif file:
            connector = get_connector("file")
            # FileConnector specific method
            docs = await connector.process(file, metadata=meta_dict, user_id=user_id)
        else:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'file', 'url', or 'drive_id' must be provided."
            )
            
    except Exception as e:
        import traceback
        print(f"CRITICAL PROCESSING ERROR: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process content: {str(e)}"
        )

    if not docs:
        return IngestResponse(status="skipped", doc_id="empty")
    
    # 2. Embedding (Remains in Router/Service Layer for now)
    embeddings_model = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=settings.OPENAI_API_KEY
    )
    
    chunk_texts = [d.page_content for d in docs]
    try:
        chunk_embeddings = embeddings_model.embed_documents(chunk_texts)
    except Exception as e:
         raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate embeddings: {str(e)}"
        )
        
    # 3. DB Insertion (Relational)
    
    # 3.1. Insert Parent Document
    # Determine title based on source
    if url:
        doc_title = url
    elif drive_id:
        doc_title = docs[0].metadata.get('title', f"Drive: {drive_id}") if docs else drive_id
    elif file:
        doc_title = file.filename
    else:
        doc_title = "Untitled"
        
    source_url = url if url else (docs[0].metadata.get('source_url') if drive_id and docs else None)
    
    parent_doc_data = {
        "user_id": user_id,
        "title": doc_title,
        "source_type": source_type,
        "source_url": source_url,
        "metadata": meta_dict,
        "created_at": datetime.datetime.now().isoformat()
    }
    
    try:
        # Insert and return ID
        parent_res = supabase.table("documents").insert(parent_doc_data).execute()
        if not parent_res.data:
             raise Exception("Failed to create parent document")
        parent_id = parent_res.data[0]['id']
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database Insertion Error (Parent): {str(e)}")

    # 3.2. Insert Chunks
    chunk_records = []
    
    for i, doc in enumerate(docs):
        chunk_records.append({
            "document_id": parent_id,
            "content": doc.page_content,
            # Embedding is already computed
            "embedding": chunk_embeddings[i],
            "chunk_index": i,
            "created_at": datetime.datetime.now().isoformat()
        })
        
    try:
        # Batch insert chunks
        supabase.table("document_chunks").insert(chunk_records).execute()
    except Exception as e:
        # Rollback parent if chunks fail? 
        # Ideally yes, but Supabase-py doesn't strictly support multi-step transactions easily in this client mode without RPC.
        # We will attempt to delete parent.
        print(f"Chunk insertion failed: {e}")
        supabase.table("documents").delete().eq("id", parent_id).execute()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to insert document chunks: {str(e)}"
        )

    return IngestResponse(status="queued", doc_id=parent_id)