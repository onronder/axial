from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Optional
from models import IngestResponse
from core.security import get_current_user
from core.db import get_supabase
from core.config import settings
from core.embeddings import EmbeddingFactory, EmbeddingTier
from connectors.factory import get_connector
import uuid
import datetime
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

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
    
    # 2. Semantic Chunking - Split documents into optimal chunks for embedding
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,       # Optimal for embedding models
        chunk_overlap=100,     # Preserve context at boundaries
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len
    )
    
    # Apply chunking to all documents
    chunked_docs = []
    for doc in docs:
        chunks = splitter.split_text(doc.page_content)
        for chunk in chunks:
            chunked_docs.append({
                "page_content": chunk,
                "metadata": doc.metadata
            })
    
    if not chunked_docs:
        return IngestResponse(status="skipped", doc_id="empty")
    
    logger.info(f"📄 [Ingest] Split {len(docs)} documents into {len(chunked_docs)} chunks")
    
    # 3. Embedding with cost-optimized tier selection
    # Auto-select tier based on chunk count (large batches use cheaper models)
    tier = EmbeddingFactory.auto_select(doc_count=len(chunked_docs), priority="normal")
    embeddings_model = EmbeddingFactory.get_embeddings(tier)
    
    chunk_texts = [d["page_content"] for d in chunked_docs]
    try:
        logger.info(f"🔢 [Ingest] Embedding {len(chunk_texts)} chunks with {tier.value} tier")
        chunk_embeddings = embeddings_model.embed_documents(chunk_texts)
        logger.info(f"🔢 [Ingest] ✅ Embedding complete")
    except Exception as e:
        logger.error(f"🔢 [Ingest] ❌ Embedding failed: {e}")
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

    # 4.2. Insert Chunks (using the chunked documents)
    chunk_records = []
    
    for i, chunk_doc in enumerate(chunked_docs):
        chunk_records.append({
            "document_id": parent_id,
            "content": chunk_doc["page_content"],
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