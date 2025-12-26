from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.concurrency import run_in_threadpool
from typing import Optional
from models import IngestResponse
from core.security import get_current_user
from core.db import get_supabase
from core.config import settings
from core.embeddings import EmbeddingFactory, EmbeddingTier
from connectors.factory import get_connector
from slowapi import Limiter
from slowapi.util import get_remote_address
import magic
import uuid
import datetime
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Rate limiter instance (uses same key_func as main.py)
limiter = Limiter(key_func=get_remote_address)

# Allowed MIME types for uploaded files
ALLOWED_MIME_TYPES = {
    "application/pdf": [".pdf"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    "text/plain": [".txt"],
    "text/markdown": [".md"],
    "text/html": [".html", ".htm"],
}

# Dangerous MIME types that should always be rejected
DANGEROUS_MIME_TYPES = [
    "application/x-dosexec",
    "application/x-executable",
    "application/x-msdownload",
    "application/x-msdos-program",
]


@router.post("/ingest", response_model=IngestResponse)
@limiter.limit("10/minute")
async def ingest_document(
    request: Request,
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    drive_id: Optional[str] = Form(None),
    notion_page_id: Optional[str] = Form(None),
    notion_token: Optional[str] = Form(None),
    metadata: str = Form(...),
    user_id: str = Depends(get_current_user)
):
    supabase = get_supabase()
    
    # SECURITY: Validate file content type using magic bytes
    if file:
        try:
            # Read first 2048 bytes for MIME detection
            header = await file.read(2048)
            await file.seek(0)  # Reset file position
            
            detected_mime = magic.from_buffer(header, mime=True)
            
            # Check for dangerous MIME types
            if detected_mime in DANGEROUS_MIME_TYPES:
                logger.warning(f"🚨 [Ingest] Blocked dangerous file: {file.filename}, detected MIME: {detected_mime}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File type not allowed: detected as {detected_mime}"
                )
            
            # Validate extension matches detected MIME type
            file_ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
            if detected_mime in ALLOWED_MIME_TYPES:
                allowed_extensions = ALLOWED_MIME_TYPES[detected_mime]
                if file_ext and file_ext not in allowed_extensions:
                    logger.warning(f"🚨 [Ingest] Extension mismatch: {file.filename} ({file_ext}) vs detected {detected_mime}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"File extension mismatch: {file_ext} does not match detected type {detected_mime}"
                    )
            
            logger.info(f"✅ [Ingest] File validated: {file.filename}, MIME: {detected_mime}")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ [Ingest] MIME validation error: {e}")
            # Continue with upload - don't block on validation errors
    
    # 0. Parse metadata JSON string
    try:
        meta_dict = json.loads(metadata)
    except Exception:
        meta_dict = {}

    # 1. Process via Connector (Parsing & Chunking)
    try:
        source_type = "file"
        
        if url:
            # ===== ASYNC WEB CRAWLING =====
            # Extract optional crawl options from metadata
            crawl_type = meta_dict.get("crawl_type", "single")  # single, recursive, sitemap
            max_depth = min(int(meta_dict.get("depth", 1)), 10)
            respect_robots = meta_dict.get("respect_robots", True)
            
            # Create WebCrawlConfig record for tracking
            from datetime import datetime as dt
            crawl_config_data = {
                "user_id": user_id,
                "root_url": url,
                "crawl_type": crawl_type,
                "max_depth": max_depth,
                "respect_robots_txt": respect_robots,
                "status": "pending",
                "created_at": dt.utcnow().isoformat(),
                "updated_at": dt.utcnow().isoformat()
            }
            
            crawl_res = supabase.table("web_crawl_configs").insert(crawl_config_data).execute()
            if not crawl_res.data:
                raise HTTPException(status_code=500, detail="Failed to create crawl config")
            
            crawl_id = str(crawl_res.data[0]["id"])
            
            # Dispatch Celery task
            from worker.tasks import crawl_web_task
            task = crawl_web_task.delay(
                user_id=user_id,
                root_url=url,
                crawl_config={
                    "crawl_id": crawl_id,
                    "crawl_type": crawl_type,
                    "max_depth": max_depth,
                    "respect_robots": respect_robots
                }
            )
            
            # Update task ID reference
            supabase.table("web_crawl_configs").update({
                "celery_task_id": task.id
            }).eq("id", crawl_id).execute()
            
            logger.info(f"🕸️ [Ingest] Web crawl queued: {url}, type={crawl_type}, task={task.id}")
            
            # Return immediately with job reference
            return IngestResponse(status="queued", doc_id=crawl_id)
        elif drive_id:
             connector = get_connector("drive")
             source_type = "drive"
             # Fix: Use run_in_threadpool + config (DriveConnector will fetch its own creds via user_id fallback)
             config = {"item_ids": [drive_id], "user_id": user_id, "provider": "drive"}
             docs = await run_in_threadpool(connector.ingest, config)
        elif notion_page_id:
             connector = get_connector("notion")
             source_type = "notion"
             # Prepare config (Hybrid: Token from request OR DB fallback handled by connector)
             config = {
                 "user_id": user_id,
                 "item_ids": [notion_page_id],
                 "provider": "notion",
                 "credentials": {"access_token": notion_token} if notion_token else None
             }
             docs = await run_in_threadpool(connector.ingest, config)
        elif file:
            connector = get_connector("file")
            # FileConnector specific method
            docs = await connector.process(file, metadata=meta_dict, user_id=user_id)
        else:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'file', 'url', 'drive_id', or 'notion_page_id' must be provided."
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