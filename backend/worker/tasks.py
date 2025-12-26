"""
Celery Worker Tasks

Background tasks for heavy file processing (ingestion, parsing, embedding).
These run in a separate worker process to avoid blocking the FastAPI server.
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from core.celery_app import celery_app
from core.db import get_supabase
from core.config import settings
from core.security import decrypt_token
from services.parsers import DocumentParser
from services.email import email_service

logger = logging.getLogger(__name__)


# ============================================================
# JOB PROGRESS HELPERS
# ============================================================

def update_job_status(supabase, job_id: str, status: str, processed_files: int = None, error_message: str = None):
    """Helper to update ingestion job status in the database."""
    try:
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }
        if processed_files is not None:
            update_data["processed_files"] = processed_files
        if error_message is not None:
            update_data["error_message"] = error_message
            
        supabase.table("ingestion_jobs").update(update_data).eq("id", job_id).execute()
        logger.info(f"📊 [Job:{job_id}] Status: {status}, Processed: {processed_files}")
    except Exception as e:
        logger.error(f"❌ [Job:{job_id}] Failed to update status: {e}")


def create_notification(
    supabase,
    user_id: str,
    title: str,
    message: str = None,
    notification_type: str = "info",
    metadata: dict = None
):
    """
    Create a notification for the user.
    
    Args:
        supabase: Supabase client
        user_id: User's ID
        title: Notification title
        message: Optional detailed message
        notification_type: 'info', 'success', 'warning', 'error'
        metadata: Optional extra data
    """
    try:
        notification_data = {
            "user_id": user_id,
            "title": title,
            "message": message,
            "type": notification_type,
            "is_read": False,
            # Serialize dict as JSON string for extra_data column
            "extra_data": json.dumps(metadata) if metadata else None,
            "created_at": datetime.utcnow().isoformat()
        }
        
        supabase.table("notifications").insert(notification_data).execute()
        logger.info(f"🔔 [Notification] Created {notification_type}: {title}")
    except Exception as e:
        logger.error(f"❌ [Notification] Failed to create: {e}")


def send_email_notification(
    supabase,
    user_id: str,
    total_files: int
):
    """
    Send email notification for completed ingestion.
    
    This is fail-safe: errors are logged but never raised.
    Job status updates must succeed even if email fails.
    
    Args:
        supabase: Supabase client
        user_id: User's ID
        total_files: Number of processed files
    """
    try:
        # Fetch user profile for email and name
        user_response = supabase.table("profiles").select("email, display_name, full_name").eq("id", user_id).single().execute()
        
        if not user_response.data:
            logger.warning(f"📧 [Email] User profile not found for {user_id}")
            return
        
        user_data = user_response.data
        email = user_data.get("email")
        name = user_data.get("display_name") or user_data.get("full_name") or "there"
        
        if not email:
            logger.warning(f"📧 [Email] No email found for user {user_id}")
            return
        
        # Check user preference in user_notification_settings (key-value table)
        # Default to True if no explicit setting exists
        settings_response = supabase.table("user_notification_settings").select("enabled").eq("user_id", user_id).eq("setting_key", "email_on_ingestion_complete").maybeSingle().execute()
        
        email_enabled = True  # Default if no setting exists
        if settings_response.data:
            email_enabled = settings_response.data.get("enabled", True)
        
        if not email_enabled:
            logger.info(f"📧 [Email] User {user_id} has email notifications disabled")
            return
        
        # Send the email (EmailService handles its own errors)
        email_service.send_ingestion_complete(
            to_email=email,
            name=name,
            total_files=total_files
        )
        
    except Exception as e:
        # CRITICAL: Log but never raise - email is secondary functionality
        logger.error(f"📧 [Email] Failed to send notification: {e}")


def send_failure_email_notification(
    supabase,
    user_id: str,
    filename: str,
    error_message: str
):
    """
    Send email notification when ingestion fails.
    
    This is fail-safe: errors are logged but never raised.
    
    Args:
        supabase: Supabase client
        user_id: User's ID
        filename: Name of the file that failed
        error_message: Error details
    """
    try:
        # Fetch user profile for email and name
        user_response = supabase.table("profiles").select("email, display_name, full_name").eq("id", user_id).single().execute()
        
        if not user_response.data:
            logger.warning(f"📧 [Email] User profile not found for {user_id}")
            return
        
        user_data = user_response.data
        email = user_data.get("email")
        name = user_data.get("display_name") or user_data.get("full_name") or "there"
        
        if not email:
            logger.warning(f"📧 [Email] No email found for user {user_id}")
            return
        
        # Check user preference (respect opt-out for error emails too)
        settings_response = supabase.table("user_notification_settings").select("enabled").eq("user_id", user_id).eq("setting_key", "email_on_ingestion_complete").maybeSingle().execute()
        
        email_enabled = True
        if settings_response.data:
            email_enabled = settings_response.data.get("enabled", True)
        
        if not email_enabled:
            logger.info(f"📧 [Email] User {user_id} has email notifications disabled")
            return
        
        # Send the failure email
        email_service.send_ingestion_failed(
            to_email=email,
            name=name,
            filename=filename,
            error_message=str(error_message)[:500]
        )
        
    except Exception as e:
        logger.error(f"📧 [Email] Failed to send failure notification: {e}")

# ============================================================
# ZERO-COPY FILE INGESTION TASK
# ============================================================

STAGING_BUCKET = "ephemeral-staging"

@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError, OSError, Exception),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
    acks_late=True
)
def ingest_file_task(
    self,
    user_id: str,
    job_id: str,
    storage_path: str,
    filename: str,
    metadata: Dict[str, Any] = None
):
    """
    Zero-Copy File Ingestion Task.
    
    Architecture: Store-Forward-Process-Delete
    1. Download file from Supabase Storage to /tmp
    2. Parse and chunk the file
    3. Embed and store via atomic RPC
    4. Delete file from /tmp AND Storage (zero-copy cleanup)
    
    Args:
        user_id: User's ID for multi-tenancy
        job_id: Ingestion job ID for progress tracking
        storage_path: Path in ephemeral-staging bucket
        filename: Original filename
        metadata: Optional metadata dict
    """
    import os
    import tempfile
    
    task_id = self.request.id
    logger.info(f"📥 [Worker:{task_id}] Starting zero-copy ingestion for {filename}")
    
    supabase = get_supabase()
    local_path = None
    
    try:
        # Update job to processing
        update_job_status(supabase, job_id, "processing", 0)
        
        create_notification(
            supabase, user_id,
            "Processing File",
            f"Ingesting {filename}",
            "info",
            {"job_id": job_id, "filename": filename}
        )
        
        # ========== STEP 1: Download from Storage ==========
        logger.info(f"📦 [Worker:{task_id}] Downloading from storage: {storage_path}")
        
        file_data = supabase.storage.from_(STAGING_BUCKET).download(storage_path)
        
        # Write to temp file
        file_ext = os.path.splitext(filename)[1] if filename else ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            tmp.write(file_data)
            local_path = tmp.name
        
        logger.info(f"📦 [Worker:{task_id}] Downloaded to: {local_path}")
        
        # ========== STEP 2: Smart Parse & Chunk (Format-Specific) ==========
        from services.parsers import DocumentProcessorFactory
        
        # Process file with format-specific strategy
        result = DocumentProcessorFactory.process(
            file_path=local_path,
            filename=filename
        )
        
        if not result.chunks:
            logger.warning(f"📥 [Worker:{task_id}] No content extracted from {filename}")
            update_job_status(supabase, job_id, "completed", 1)
            return {"status": "skipped", "message": "No content extracted"}
        
        logger.info(f"📄 [Worker:{task_id}] {result.file_type}: {len(result.chunks)} chunks, {result.total_tokens} tokens")
        
        # ========== STEP 3: Embed ==========
        from langchain_openai import OpenAIEmbeddings
        
        embeddings_model = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.OPENAI_API_KEY
        )
        
        # Get chunk texts for embedding
        chunk_texts = [chunk.content for chunk in result.chunks]
        chunk_embeddings = embeddings_model.embed_documents(chunk_texts)
        logger.info(f"🔢 [Worker:{task_id}] Embedded {len(chunk_texts)} chunks")
        
        # ========== STEP 4: Atomic RPC Insert ==========
        # Prepare chunks payload with enriched metadata
        chunks_payload = []
        for chunk, embedding in zip(result.chunks, chunk_embeddings):
            chunks_payload.append({
                "content": chunk.content,
                "embedding": embedding,
                "chunk_index": chunk.chunk_index,
                # Extended metadata from factory
                "metadata": {
                    **chunk.metadata,
                    "token_count": chunk.token_count,
                }
            })
        
        # Merge document metadata
        doc_metadata = {
            **(metadata or {}),
            "file_type": result.file_type,
            "total_tokens": result.total_tokens,
            "total_chunks": len(result.chunks),
            **(result.metadata or {}),
        }
        
        # Call atomic ingestion RPC
        rpc_result = supabase.rpc("ingest_document_with_chunks", {
            "p_user_id": user_id,
            "p_doc_title": filename,
            "p_source_type": "file",
            "p_source_url": None,
            "p_metadata": json.dumps(doc_metadata),
            "p_chunks": json.dumps(chunks_payload)
        }).execute()
        
        if rpc_result.data:
            doc_id = rpc_result.data
            logger.info(f"✅ [Worker:{task_id}] Document stored: {doc_id}")
        else:
            raise Exception("RPC returned no document ID")
        
        # Update job to completed
        update_job_status(supabase, job_id, "completed", 1)
        
        create_notification(
            supabase, user_id,
            "Ingestion Complete",
            f"Successfully processed {filename} ({len(chunks)} chunks)",
            "success",
            {"job_id": job_id, "document_id": str(doc_id)}
        )
        
        send_email_notification(supabase, user_id, 1)
        
        return {"status": "success", "document_id": str(doc_id), "chunks": len(chunks)}
        
    except Exception as e:
        logger.error(f"❌ [Worker:{task_id}] Failed: {e}")
        
        update_job_status(supabase, job_id, "failed", 0, str(e))
        
        create_notification(
            supabase, user_id,
            "Ingestion Failed",
            f"Failed to process {filename}: {str(e)[:200]}",
            "error",
            {"job_id": job_id, "error": str(e)}
        )
        
        # Send failure email (fail-safe, respects user preferences)
        send_failure_email_notification(supabase, user_id, filename, str(e))
        
        raise
        
    finally:
        # ========== ZERO-COPY CLEANUP ==========
        # Delete local temp file
        if local_path and os.path.exists(local_path):
            try:
                os.remove(local_path)
                logger.info(f"🗑️ [Worker:{task_id}] Deleted local temp: {local_path}")
            except Exception as e:
                logger.warning(f"⚠️ [Worker:{task_id}] Failed to delete temp: {e}")
        
        # Delete from Supabase Storage
        try:
            supabase.storage.from_(STAGING_BUCKET).remove([storage_path])
            logger.info(f"🗑️ [Worker:{task_id}] Deleted from storage: {storage_path}")
            logger.info(f"🔒 [Worker:{task_id}] File destroyed securely after processing")
        except Exception as e:
            logger.warning(f"⚠️ [Worker:{task_id}] Failed to delete from storage: {e}")


# ============================================================
# CONNECTOR INGESTION TASK (Drive, Notion)
# ============================================================

@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
    acks_late=True
)
def ingest_connector_task(
    self,
    user_id: str,
    job_id: str,
    connector_type: str,
    item_id: str,
    credentials: Dict[str, Any] = None
):
    """
    Background task to ingest files from cloud connectors (Drive, Notion).
    
    Uses atomic RPC for database insertion.
    
    Args:
        user_id: User's ID for multi-tenancy
        job_id: Ingestion job ID for progress tracking
        connector_type: 'drive' or 'notion'
        item_id: File/page ID to ingest
        credentials: Optional OAuth credentials
    """
    task_id = self.request.id
    logger.info(f"📥 [Worker:{task_id}] Starting connector ingestion for user {user_id}")
    logger.info(f"📥 [Worker:{task_id}] Connector: {connector_type}, Item: {item_id}, Job: {job_id}")
    
    supabase = get_supabase()
    
    try:
        update_job_status(supabase, job_id, "processing", 0)
        
        create_notification(
            supabase,
            user_id,
            "Ingestion Started",
            f"Processing from {connector_type.replace('_', ' ').title()}",
            "info",
            {"job_id": job_id, "connector": connector_type}
        )
        
        # 1. Decrypt credentials if provided
        decrypted_creds = {}
        if credentials:
            for key, value in credentials.items():
                if isinstance(value, str):
                    decrypted_creds[key] = decrypt_token(value)
                else:
                    decrypted_creds[key] = value
        
        # 2. Get connector and ingest
        from connectors.factory import get_connector
        connector = get_connector(connector_type)
        
        # Prepare config for standardized ingest interface
        ingest_config = {
            "user_id": user_id,
            "item_ids": [item_id],
            "credentials": decrypted_creds,
            "provider": connector_type
        }
        
        # Call synchronous ingest (worker-compatible)
        docs = connector.ingest(ingest_config)
        
        if not docs:
            logger.warning(f"📥 [Worker:{task_id}] No content processed")
            update_job_status(supabase, job_id, "completed", 1)
            return {"status": "skipped", "message": "No content processed"}
        
        # 3. Process each document through DocumentProcessorFactory
        from services.parsers import DocumentProcessorFactory
        from langchain_openai import OpenAIEmbeddings
        
        embeddings_model = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.OPENAI_API_KEY
        )
        
        # Map connector to source_type enum
        CONNECTOR_TYPE_TO_ENUM = {
            "google_drive": "drive",
            "drive": "drive",
            "notion": "notion",
            "file_upload": "file",
            "file": "file",
            "web": "web",
        }
        source_type_enum = CONNECTOR_TYPE_TO_ENUM.get(connector_type, "file")
        
        results = []
        processed_count = 0
        
        for doc in docs:
            doc_title = doc.metadata.get('title', 'Untitled')
            doc_content = doc.page_content
            source_url = doc.metadata.get('source_url')
            
            # Route through appropriate processor based on connector type
            if connector_type in ["notion"]:
                # Notion: Treat as markdown (has headers, lists, etc.)
                result = DocumentProcessorFactory.process_web_content(
                    doc_content,
                    source_url or doc_title
                )
            else:
                # Drive and others: Use extension/mime_type routing
                content_bytes = doc_content.encode('utf-8')
                mime_type = doc.metadata.get('mime_type', 'text/plain')
                
                # Try to get file extension from title
                filename = doc_title
                if not any(filename.endswith(ext) for ext in ['.pdf', '.docx', '.md', '.txt', '.py', '.js']):
                    # Add extension based on mime type
                    if 'pdf' in mime_type:
                        filename = f"{doc_title}.pdf"
                    elif 'markdown' in mime_type:
                        filename = f"{doc_title}.md"
                    elif 'document' in mime_type:
                        filename = f"{doc_title}.docx"
                
                result = DocumentProcessorFactory.process(
                    content=content_bytes,
                    filename=filename,
                    mime_type=mime_type
                )
            
            if not result.chunks:
                logger.warning(f"⚠️ [Worker:{task_id}] No chunks from: {doc_title}")
                continue
            
            # Embed chunks
            chunk_texts = [chunk.content for chunk in result.chunks]
            chunk_embeddings = embeddings_model.embed_documents(chunk_texts)
            
            # Build chunks payload with enriched metadata
            chunks_payload = []
            for chunk, embedding in zip(result.chunks, chunk_embeddings):
                chunks_payload.append({
                    "content": chunk.content,
                    "embedding": embedding,
                    "chunk_index": chunk.chunk_index,
                    "metadata": {
                        **chunk.metadata,
                        "token_count": chunk.token_count,
                    }
                })
            
            # Document metadata
            doc_metadata = {
                **doc.metadata,
                "file_type": result.file_type,
                "total_tokens": result.total_tokens,
                "total_chunks": len(result.chunks),
                **(result.metadata or {}),
            }
            
            # ATOMIC RPC: Insert document with all chunks
            rpc_result = supabase.rpc("ingest_document_with_chunks", {
                "p_user_id": user_id,
                "p_doc_title": doc_title,
                "p_source_type": source_type_enum,
                "p_source_url": source_url,
                "p_metadata": json.dumps(doc_metadata),
                "p_chunks": json.dumps(chunks_payload)
            }).execute()
            
            if rpc_result.data:
                doc_id = rpc_result.data
                results.append(str(doc_id))
                logger.info(f"📄 [Worker:{task_id}] {doc_title}: {len(result.chunks)} chunks via {result.file_type}")
            else:
                logger.warning(f"⚠️ [Worker:{task_id}] RPC returned no data for {doc_title}")
            
            # Update progress
            processed_count += 1
            if job_id:
                update_job_status(supabase, job_id, "processing", processed_count)
        
        # Mark job as completed
        if job_id:
            update_job_status(supabase, job_id, "completed", 1)
        
        # Create "success" notification
        create_notification(
            supabase,
            user_id,
            f"Ingestion Complete",
            f"Successfully processed {len(results)} documents from {connector_type.replace('_', ' ').title()}",
            "success",
            {"job_id": job_id, "connector": connector_type, "document_count": len(results)}
        )
        
        # Send email notification (fail-safe, respects user preferences)
        send_email_notification(supabase, user_id, len(results))
        
        logger.info(f"✅ [Worker:{task_id}] Ingestion complete: {len(results)} documents (via DocumentProcessorFactory)")
        return {"status": "success", "ingested_ids": results, "task_id": task_id, "job_id": job_id}
        
    except Exception as e:
        logger.error(f"❌ [Worker:{task_id}] Ingestion failed: {e}")
        
        # Update job status to failed
        if job_id:
            update_job_status(supabase, job_id, "failed", 0, str(e))
        
        # Create "error" notification
        create_notification(
            supabase,
            user_id,
            f"Ingestion Failed",
            f"Failed to process files from {connector_type.replace('_', ' ').title()}: {str(e)[:200]}",
            "error",
            {"job_id": job_id, "connector": connector_type, "error": str(e)}
        )
        
        # Re-raise for Celery retry mechanism
        raise


# ============================================================
# WEB CRAWL TASK
# ============================================================

def update_crawl_status(
    supabase,
    crawl_id: str,
    status: str = None,
    total_pages: int = None,
    pages_ingested: int = None,
    pages_failed: int = None,
    error_message: str = None
):
    """Helper to update web crawl config status."""
    try:
        update_data = {"updated_at": datetime.utcnow().isoformat()}
        
        if status:
            update_data["status"] = status
        if total_pages is not None:
            update_data["total_pages_found"] = total_pages
        if pages_ingested is not None:
            update_data["pages_ingested"] = pages_ingested
        if pages_failed is not None:
            update_data["pages_failed"] = pages_failed
        if error_message:
            update_data["error_message"] = error_message
        if status == "completed":
            update_data["completed_at"] = datetime.utcnow().isoformat()
            
        supabase.table("web_crawl_configs").update(update_data).eq("id", crawl_id).execute()
        logger.info(f"🕸️ [Crawl:{crawl_id}] Status: {status}, Ingested: {pages_ingested}")
    except Exception as e:
        logger.error(f"❌ [Crawl:{crawl_id}] Failed to update status: {e}")


@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=2,
    acks_late=True
)
def crawl_web_task(
    self,
    user_id: str,
    root_url: str,
    crawl_config: Dict[str, Any]
):
    """
    Background task for advanced web crawling.
    
    Supports:
    - Single page crawling
    - Sitemap-based crawling
    - Recursive link following
    - YouTube transcript extraction
    
    Args:
        user_id: User's ID for multi-tenancy
        root_url: Starting URL to crawl
        crawl_config: Dict with:
            - 'crawl_id': UUID of WebCrawlConfig record
            - 'crawl_type': 'single', 'recursive', 'sitemap'
            - 'max_depth': int (1-10)
            - 'respect_robots': bool
    """
    import time
    import random
    from collections import deque
    
    task_id = self.request.id
    crawl_id = crawl_config.get("crawl_id")
    crawl_type = crawl_config.get("crawl_type", "single")
    max_depth = min(crawl_config.get("max_depth", 1), 10)
    respect_robots = crawl_config.get("respect_robots", True)
    
    logger.info(f"🕸️ [Worker:{task_id}] Starting web crawl for user {user_id}")
    logger.info(f"🕸️ [Worker:{task_id}] URL: {root_url}, Type: {crawl_type}, Depth: {max_depth}")
    
    supabase = get_supabase()
    
    # Import connector
    from connectors.web import WebConnector
    connector = WebConnector()
    
    # Track progress
    urls_to_process: List[str] = []
    processed_urls: set = set()
    ingested_count = 0
    failed_count = 0
    
    try:
        # ===== PHASE 1: DISCOVERY =====
        if crawl_id:
            update_crawl_status(supabase, crawl_id, status="discovering")
        
        create_notification(
            supabase, user_id,
            "Web Crawl Started",
            f"Discovering pages from {root_url}",
            "info",
            {"crawl_id": crawl_id, "crawl_type": crawl_type}
        )
        
        if crawl_type == "sitemap":
            # Parse sitemap.xml
            logger.info(f"🗺️ [Crawl] Parsing sitemap: {root_url}")
            urls_to_process = connector.parse_sitemap(root_url)
            
        elif crawl_type == "recursive":
            # BFS crawl with depth limit
            logger.info(f"🔄 [Crawl] Recursive crawl from: {root_url}")
            queue = deque([(root_url, 0)])  # (url, depth)
            seen = {root_url}
            
            while queue:
                url, depth = queue.popleft()
                urls_to_process.append(url)
                
                if depth < max_depth:
                    # Fetch page and extract links
                    html = connector.fetch_html(url)
                    if html:
                        links = connector.extract_links(html, url)
                        for link in links:
                            if link not in seen:
                                seen.add(link)
                                queue.append((link, depth + 1))
                    
                    # Rate limit during discovery
                    time.sleep(random.uniform(0.5, 1.0))
            
        else:  # single
            urls_to_process = [root_url]
        
        total_pages = len(urls_to_process)
        logger.info(f"📊 [Crawl] Discovered {total_pages} URLs to process")
        
        if crawl_id:
            update_crawl_status(supabase, crawl_id, status="processing", total_pages=total_pages)
        
        if total_pages == 0:
            if crawl_id:
                update_crawl_status(supabase, crawl_id, status="completed", total_pages=0)
            return {"status": "completed", "message": "No pages found to crawl"}
        
        # ===== PHASE 2: PROCESSING =====
        documents = []
        
        for i, url in enumerate(urls_to_process):
            if url in processed_urls:
                continue
            processed_urls.add(url)
            
            try:
                # Rate limiting (polite crawling)
                if i > 0:
                    time.sleep(random.uniform(1.0, 2.0))
                
                # Ingest this URL
                docs = connector.ingest({
                    "item_ids": [url],
                    "respect_robots": respect_robots
                })
                
                if docs:
                    documents.extend(docs)
                    ingested_count += 1
                    logger.info(f"✅ [Crawl] Ingested ({ingested_count}/{total_pages}): {url}")
                else:
                    failed_count += 1
                    logger.warning(f"⚠️ [Crawl] No content from: {url}")
                
            except Exception as e:
                failed_count += 1
                logger.error(f"❌ [Crawl] Failed to process {url}: {e}")
            
            # Update progress every 5 pages
            if crawl_id and (i + 1) % 5 == 0:
                update_crawl_status(
                    supabase, crawl_id,
                    pages_ingested=ingested_count,
                    pages_failed=failed_count
                )
        
        # ===== PHASE 3: EMBEDDING & STORAGE (ATOMIC RPC) =====
        if documents:
            logger.info(f"🔢 [Crawl] Embedding {len(documents)} documents...")
            
            from langchain_openai import OpenAIEmbeddings
            embeddings_model = OpenAIEmbeddings(
                model="text-embedding-3-small",
                api_key=settings.OPENAI_API_KEY
            )
            
            chunk_texts = [d.page_content for d in documents]
            chunk_embeddings = embeddings_model.embed_documents(chunk_texts)
            
            # Store in database using ATOMIC RPC
            for i, doc in enumerate(documents):
                # Prepare chunk payload for atomic RPC (single chunk per page)
                chunks_payload = [{
                    "content": doc.page_content,
                    "embedding": chunk_embeddings[i],
                    "chunk_index": 0
                }]
                
                # ATOMIC RPC: Insert document with all chunks in single transaction
                rpc_result = supabase.rpc("ingest_document_with_chunks", {
                    "p_user_id": user_id,
                    "p_doc_title": doc.metadata.get("title", "Web Page"),
                    "p_source_type": "web",
                    "p_source_url": doc.metadata.get("source_url"),
                    "p_metadata": json.dumps(doc.metadata if isinstance(doc.metadata, dict) else {}),
                    "p_chunks": json.dumps(chunks_payload)
                }).execute()
                
                if rpc_result.data:
                    logger.debug(f"📄 [Crawl] Stored via RPC: {doc.metadata.get('title', 'Web Page')}")
        
        # ===== COMPLETE =====
        if crawl_id:
            update_crawl_status(
                supabase, crawl_id,
                status="completed",
                pages_ingested=ingested_count,
                pages_failed=failed_count
            )
        
        create_notification(
            supabase, user_id,
            "Web Crawl Complete",
            f"Successfully ingested {ingested_count} pages from {root_url}",
            "success",
            {"crawl_id": crawl_id, "pages_ingested": ingested_count}
        )
        
        logger.info(f"✅ [Worker:{task_id}] Crawl complete: {ingested_count} pages ingested")
        return {
            "status": "success",
            "crawl_id": crawl_id,
            "pages_discovered": total_pages,
            "pages_ingested": ingested_count,
            "pages_failed": failed_count
        }
        
    except Exception as e:
        logger.error(f"❌ [Worker:{task_id}] Crawl failed: {e}")
        
        if crawl_id:
            update_crawl_status(
                supabase, crawl_id,
                status="failed",
                error_message=str(e)
            )
        
        create_notification(
            supabase, user_id,
            "Web Crawl Failed",
            f"Failed to crawl {root_url}: {str(e)[:200]}",
            "error",
            {"crawl_id": crawl_id, "error": str(e)}
        )
        
        raise


# ============================================================
# DISTRIBUTED CRAWLER: Master-Worker Pattern
# ============================================================

@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    max_retries=2
)
def crawl_discovery_task(
    self,
    user_id: str,
    root_url: str,
    crawl_config: Dict[str, Any]
):
    """
    Master task for distributed web crawling.
    
    Discovers URLs (via sitemap or recursive) and dispatches
    individual page processing tasks using Celery groups.
    
    This pattern prevents Celery Soft Time Limit issues when
    crawling large sites (10,000+ pages).
    """
    from celery import group
    from collections import deque
    import time
    import random
    
    task_id = self.request.id
    crawl_id = crawl_config.get("crawl_id")
    crawl_type = crawl_config.get("crawl_type", "single")
    max_depth = min(crawl_config.get("max_depth", 1), 10)
    respect_robots = crawl_config.get("respect_robots", True)
    
    logger.info(f"🕸️ [Discovery:{task_id}] Starting distributed crawl for user {user_id}")
    logger.info(f"🕸️ [Discovery:{task_id}] URL: {root_url}, Type: {crawl_type}, Depth: {max_depth}")
    
    supabase = get_supabase()
    
    try:
        # Import connector
        from connectors.web import WebConnector
        connector = WebConnector()
        
        # Update status
        if crawl_id:
            update_crawl_status(supabase, crawl_id, status="discovering")
        
        create_notification(
            supabase, user_id,
            "Web Crawl Started",
            f"Discovering pages from {root_url}",
            "info",
            {"crawl_id": crawl_id, "crawl_type": crawl_type}
        )
        
        # ===== DISCOVERY PHASE =====
        urls_to_process: List[str] = []
        
        if crawl_type == "sitemap":
            logger.info(f"🗺️ [Discovery] Parsing sitemap: {root_url}")
            urls_to_process = connector.parse_sitemap(root_url)
            
        elif crawl_type == "recursive":
            logger.info(f"🔄 [Discovery] Recursive crawl from: {root_url}")
            queue = deque([(root_url, 0)])
            seen = {root_url}
            
            while queue:
                url, depth = queue.popleft()
                urls_to_process.append(url)
                
                if depth < max_depth:
                    html = connector.fetch_html(url)
                    if html:
                        links = connector.extract_links(html, url)
                        for link in links:
                            if link not in seen:
                                seen.add(link)
                                queue.append((link, depth + 1))
                    
                    # Rate limit during discovery
                    time.sleep(random.uniform(0.3, 0.6))
        else:
            urls_to_process = [root_url]
        
        total_pages = len(urls_to_process)
        logger.info(f"📊 [Discovery] Discovered {total_pages} URLs")
        
        if crawl_id:
            update_crawl_status(supabase, crawl_id, status="processing", total_pages=total_pages)
        
        if total_pages == 0:
            if crawl_id:
                update_crawl_status(supabase, crawl_id, status="completed", total_pages=0)
            return {"status": "completed", "message": "No pages found"}
        
        # ===== DISPATCH PHASE: Parallel processing =====
        # Create a group of tasks for parallel execution
        page_tasks = group(
            process_page_task.s(
                user_id=user_id,
                url=url,
                crawl_id=crawl_id,
                respect_robots=respect_robots
            ) for url in urls_to_process
        )
        
        # Execute all tasks in parallel
        result = page_tasks.apply_async()
        
        logger.info(f"🚀 [Discovery:{task_id}] Dispatched {total_pages} page tasks")
        
        return {
            "status": "dispatched",
            "crawl_id": crawl_id,
            "total_pages": total_pages,
            "group_id": str(result.id)
        }
        
    except Exception as e:
        logger.error(f"❌ [Discovery:{task_id}] Failed: {e}")
        
        if crawl_id:
            update_crawl_status(
                supabase, crawl_id,
                status="failed",
                error_message=str(e)
            )
        
        create_notification(
            supabase, user_id,
            "Web Crawl Failed",
            f"Discovery failed for {root_url}: {str(e)[:200]}",
            "error",
            {"crawl_id": crawl_id, "error": str(e)}
        )
        
        raise


@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    max_retries=3,
    rate_limit='10/s'  # Rate limit: max 10 pages per second
)
def process_page_task(
    self,
    user_id: str,
    url: str,
    crawl_id: str = None,
    respect_robots: bool = True
):
    """
    Worker task for processing a single web page.
    
    Downloads, parses, embeds, and stores a single URL.
    Uses rate limiting to be polite to target servers.
    """
    task_id = self.request.id
    logger.info(f"📄 [Page:{task_id}] Processing: {url}")
    
    supabase = get_supabase()
    
    try:
        from connectors.web import WebConnector
        from services.parsers import DocumentProcessorFactory
        
        connector = WebConnector()
        
        # Fetch and parse page
        docs = connector.ingest({
            "item_ids": [url],
            "respect_robots": respect_robots
        })
        
        if not docs:
            logger.warning(f"⚠️ [Page:{task_id}] No content from: {url}")
            return {"status": "skipped", "url": url}
        
        # Get page content and title
        page_content = docs[0].page_content if docs else ""
        page_title = docs[0].metadata.get("title", "Web Page") if docs else "Web Page"
        page_metadata = docs[0].metadata if docs else {}
        
        # Process using MarkdownProcessor (treats web content as markdown)
        result = DocumentProcessorFactory.process_web_content(page_content, url)
        
        if not result.chunks:
            logger.warning(f"⚠️ [Page:{task_id}] No chunks generated from: {url}")
            return {"status": "skipped", "url": url}
        
        # Embed
        from langchain_openai import OpenAIEmbeddings
        embeddings_model = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.OPENAI_API_KEY
        )
        
        chunk_texts = [chunk.content for chunk in result.chunks]
        chunk_embeddings = embeddings_model.embed_documents(chunk_texts)
        
        # Build chunks payload with enriched metadata
        chunks_payload = []
        for chunk, embedding in zip(result.chunks, chunk_embeddings):
            chunks_payload.append({
                "content": chunk.content,
                "embedding": embedding,
                "chunk_index": chunk.chunk_index,
                "metadata": {
                    **chunk.metadata,
                    "token_count": chunk.token_count,
                }
            })
        
        # Document metadata
        doc_metadata = {
            **page_metadata,
            "file_type": "web",
            "total_tokens": result.total_tokens,
            "total_chunks": len(result.chunks),
        }
        
        # Store using atomic RPC
        rpc_result = supabase.rpc("ingest_document_with_chunks", {
            "p_user_id": user_id,
            "p_doc_title": page_title,
            "p_source_type": "web",
            "p_source_url": url,
            "p_metadata": json.dumps(doc_metadata),
            "p_chunks": json.dumps(chunks_payload)
        }).execute()
        
        logger.info(f"✅ [Page:{task_id}] Stored: {url} ({len(result.chunks)} chunks)")
        
        # Update crawl progress
        if crawl_id:
            try:
                supabase.rpc("increment_crawl_counter", {
                    "p_crawl_id": crawl_id,
                    "p_field": "pages_ingested"
                }).execute()
            except Exception:
                pass  # Non-critical
        
        return {"status": "success", "url": url}
        
    except Exception as e:
        logger.error(f"❌ [Page:{task_id}] Failed {url}: {e}")
        
        # Increment failure counter
        if crawl_id:
            try:
                supabase.rpc("increment_crawl_counter", {
                    "p_crawl_id": crawl_id,
                    "p_field": "pages_failed"
                }).execute()
            except Exception:
                pass
        
        # Send failure email for web page (fail-safe)
        send_failure_email_notification(supabase, user_id, url, str(e))
        
        raise


# ============================================================
# SCHEDULED RE-CRAWL TASK (Living Knowledge)
# ============================================================

@celery_app.task(bind=True)
def check_scheduled_crawls(self):
    """
    Celery Beat task to check for scheduled re-crawls.
    
    Runs hourly via Celery Beat.
    Finds completed crawls that are due for refresh and triggers them.
    """
    from datetime import timedelta
    
    task_id = self.request.id
    logger.info(f"⏰ [Scheduler:{task_id}] Checking for scheduled re-crawls...")
    
    supabase = get_supabase()
    now = datetime.utcnow()
    
    try:
        # Find crawls that are due for refresh
        # Status = completed, refresh_interval != never, next_crawl_at <= now
        result = supabase.table("web_crawl_configs").select("*").eq(
            "status", "completed"
        ).neq(
            "refresh_interval", "never"
        ).lte(
            "next_crawl_at", now.isoformat()
        ).execute()
        
        if not result.data:
            logger.info(f"⏰ [Scheduler:{task_id}] No crawls due for refresh")
            return {"status": "ok", "crawls_triggered": 0}
        
        crawls_triggered = 0
        
        for config in result.data:
            try:
                crawl_id = str(config["id"])
                user_id = str(config["user_id"])
                root_url = config["root_url"]
                crawl_type = config["crawl_type"]
                max_depth = config["max_depth"]
                refresh_interval = config["refresh_interval"]
                
                logger.info(f"🔄 [Scheduler] Triggering re-crawl: {root_url} ({refresh_interval})")
                
                # Reset status to pending for re-crawl
                supabase.table("web_crawl_configs").update({
                    "status": "pending",
                    "pages_ingested": 0,
                    "pages_failed": 0,
                    "total_pages_found": 0,
                    "error_message": None,
                    "updated_at": now.isoformat()
                }).eq("id", crawl_id).execute()
                
                # Trigger the crawl task
                task = crawl_web_task.delay(
                    user_id=user_id,
                    root_url=root_url,
                    crawl_config={
                        "crawl_id": crawl_id,
                        "crawl_type": crawl_type,
                        "max_depth": max_depth,
                        "respect_robots": config.get("respect_robots_txt", True),
                        "is_recrawl": True  # Flag for re-crawl
                    }
                )
                
                # Calculate next_crawl_at based on interval
                if refresh_interval == "daily":
                    next_crawl = now + timedelta(days=1)
                elif refresh_interval == "weekly":
                    next_crawl = now + timedelta(weeks=1)
                elif refresh_interval == "monthly":
                    next_crawl = now + timedelta(days=30)
                else:
                    next_crawl = None
                
                # Update with new task ID and next crawl time
                update_data = {
                    "celery_task_id": task.id,
                    "last_crawl_at": now.isoformat()
                }
                if next_crawl:
                    update_data["next_crawl_at"] = next_crawl.isoformat()
                
                supabase.table("web_crawl_configs").update(update_data).eq("id", crawl_id).execute()
                
                crawls_triggered += 1
                
            except Exception as e:
                logger.error(f"❌ [Scheduler] Failed to trigger re-crawl for {config.get('root_url')}: {e}")
                continue
        
        logger.info(f"✅ [Scheduler:{task_id}] Triggered {crawls_triggered} re-crawls")
        return {"status": "ok", "crawls_triggered": crawls_triggered}
        
    except Exception as e:
        logger.error(f"❌ [Scheduler:{task_id}] Failed: {e}")
        return {"status": "error", "error": str(e)}


# ============================================================
# DISTRIBUTED WEB CRAWLER - MASTER/WORKER ARCHITECTURE
# ============================================================
# 
# Master task (crawl_discovery_task):
#   - Discovers all URLs (sitemap, recursive, single)
#   - Deduplicates against existing documents
#   - Dispatches process_page_task for each URL via Celery Group
#
# Worker task (process_page_task):
#   - Processes a single URL
#   - Rate limited per domain
#   - Saves via atomic RPC
#

# Redis key prefix for rate limiting
RATE_LIMIT_PREFIX = "crawl_ratelimit:"
RATE_LIMIT_WINDOW = 1  # seconds
RATE_LIMIT_MAX_REQUESTS = 5  # max requests per window per domain


def get_domain_rate_limit_key(url: str) -> str:
    """Get Redis key for domain rate limiting."""
    from urllib.parse import urlparse
    domain = urlparse(url).netloc
    return f"{RATE_LIMIT_PREFIX}{domain}"


def check_rate_limit(supabase, url: str) -> bool:
    """
    Check if we can make a request to this domain.
    Uses simple counter with TTL for rate limiting.
    
    Returns True if allowed, False if rate limited.
    """
    import redis
    from core.config import settings
    
    try:
        r = redis.from_url(settings.REDIS_URL)
        key = get_domain_rate_limit_key(url)
        
        current = r.get(key)
        if current is None:
            r.setex(key, RATE_LIMIT_WINDOW, 1)
            return True
        
        if int(current) >= RATE_LIMIT_MAX_REQUESTS:
            return False
        
        r.incr(key)
        return True
        
    except Exception as e:
        logger.warning(f"⚠️ Rate limit check failed: {e}")
        return True  # Allow on error


@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=3,
    acks_late=True
)
def process_page_task(
    self,
    url: str,
    user_id: str,
    crawl_id: str
):
    """
    Worker task: Process a single URL.
    
    Designed for distributed execution - many of these run in parallel.
    
    Args:
        url: Single URL to process
        user_id: User ID for multi-tenancy
        crawl_id: Parent crawl config ID for progress updates
    """
    import time
    import random
    
    task_id = self.request.id
    logger.info(f"🔗 [PageWorker:{task_id}] Processing: {url}")
    
    supabase = get_supabase()
    
    try:
        # Rate limiting - wait if needed
        max_wait = 5
        waited = 0
        while not check_rate_limit(supabase, url) and waited < max_wait:
            time.sleep(0.5)
            waited += 0.5
        
        if waited >= max_wait:
            logger.warning(f"⏳ [PageWorker:{task_id}] Rate limit timeout for: {url}")
        
        # Import connector
        from connectors.web import WebConnector
        connector = WebConnector()
        
        # Ingest this URL
        docs = connector.ingest({
            "item_ids": [url],
            "respect_robots": True
        })
        
        if not docs:
            logger.warning(f"⚠️ [PageWorker:{task_id}] No content from: {url}")
            return {"status": "skipped", "url": url}
        
        # Embed
        from langchain_openai import OpenAIEmbeddings
        embeddings_model = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.OPENAI_API_KEY
        )
        
        doc = docs[0]  # Single URL = single doc
        chunk_embedding = embeddings_model.embed_documents([doc.page_content])[0]
        
        # Prepare for RPC
        chunks_payload = [{
            "content": doc.page_content,
            "embedding": chunk_embedding,
            "chunk_index": 0
        }]
        
        # Atomic insert via RPC
        rpc_result = supabase.rpc("ingest_document_with_chunks", {
            "p_user_id": user_id,
            "p_doc_title": doc.metadata.get("title", url),
            "p_source_type": doc.metadata.get("source", "web"),
            "p_source_url": url,
            "p_metadata": json.dumps(doc.metadata),
            "p_chunks": json.dumps(chunks_payload)
        }).execute()
        
        if rpc_result.data:
            logger.info(f"✅ [PageWorker:{task_id}] Ingested: {url}")
            return {"status": "success", "url": url, "doc_id": str(rpc_result.data)}
        else:
            raise Exception("RPC returned no document ID")
        
    except Exception as e:
        logger.error(f"❌ [PageWorker:{task_id}] Failed {url}: {e}")
        return {"status": "failed", "url": url, "error": str(e)}


@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=2,
    acks_late=True
)
def crawl_discovery_task(
    self,
    user_id: str,
    root_url: str,
    crawl_config: Dict[str, Any]
):
    """
    Master task: Discover URLs and dispatch worker tasks.
    
    This is the "Conductor" that:
    1. Discovers all URLs (sitemap/recursive/single)
    2. Deduplicates against existing documents
    3. Dispatches process_page_task for each URL
    4. Uses Celery Group for parallel execution
    
    Args:
        user_id: User's ID
        root_url: Starting URL
        crawl_config: Configuration dict with crawl_id, type, depth, etc.
    """
    from celery import group
    from collections import deque
    import time
    import random
    
    task_id = self.request.id
    crawl_id = crawl_config.get("crawl_id")
    crawl_type = crawl_config.get("crawl_type", "single")
    max_depth = min(crawl_config.get("max_depth", 1), 10)
    
    logger.info(f"🕸️ [Master:{task_id}] Starting discovery for: {root_url}")
    logger.info(f"🕸️ [Master:{task_id}] Type: {crawl_type}, Depth: {max_depth}")
    
    supabase = get_supabase()
    
    try:
        # Update status to discovering
        if crawl_id:
            update_crawl_status(supabase, crawl_id, status="discovering")
        
        create_notification(
            supabase, user_id,
            "Web Crawl Started",
            f"Discovering pages from {root_url}",
            "info",
            {"crawl_id": crawl_id, "crawl_type": crawl_type}
        )
        
        # ===== PHASE 1: DISCOVERY =====
        from connectors.web import WebConnector
        connector = WebConnector()
        
        discovered_urls: List[str] = []
        
        if crawl_type == "sitemap":
            logger.info(f"🗺️ [Master:{task_id}] Parsing sitemap...")
            discovered_urls = connector.parse_sitemap(root_url)
            
        elif crawl_type == "recursive":
            logger.info(f"🔄 [Master:{task_id}] Recursive discovery...")
            queue = deque([(root_url, 0)])
            seen = {root_url}
            
            while queue:
                url, depth = queue.popleft()
                discovered_urls.append(url)
                
                if depth < max_depth:
                    html = connector.fetch_html(url)
                    if html:
                        links = connector.extract_links(html, url)
                        for link in links:
                            if link not in seen:
                                seen.add(link)
                                queue.append((link, depth + 1))
                    
                    time.sleep(random.uniform(0.3, 0.6))
                
                # Limit discovery to prevent runaway
                if len(discovered_urls) > 10000:
                    logger.warning(f"⚠️ [Master:{task_id}] Discovery limit reached (10k)")
                    break
        else:
            discovered_urls = [root_url]
        
        total_discovered = len(discovered_urls)
        logger.info(f"📊 [Master:{task_id}] Discovered {total_discovered} URLs")
        
        # ===== PHASE 2: DEDUPLICATION =====
        # Check which URLs are already in the database
        existing_urls = set()
        try:
            existing_res = supabase.table("documents").select("source_url").eq(
                "user_id", user_id
            ).in_(
                "source_url", discovered_urls[:1000]  # Batch limit
            ).execute()
            
            if existing_res.data:
                existing_urls = {d["source_url"] for d in existing_res.data if d.get("source_url")}
        except Exception as e:
            logger.warning(f"⚠️ [Master:{task_id}] Dedup query failed: {e}")
        
        # Filter out existing URLs (unless this is a re-crawl)
        is_recrawl = crawl_config.get("is_recrawl", False)
        if not is_recrawl:
            new_urls = [url for url in discovered_urls if url not in existing_urls]
            logger.info(f"📊 [Master:{task_id}] After dedup: {len(new_urls)} new URLs (skipped {len(existing_urls)} existing)")
        else:
            new_urls = discovered_urls
            logger.info(f"📊 [Master:{task_id}] Re-crawl mode: processing all {len(new_urls)} URLs")
        
        if not new_urls:
            if crawl_id:
                update_crawl_status(supabase, crawl_id, status="completed", total_pages=0)
            return {"status": "completed", "message": "No new URLs to crawl"}
        
        # Update total pages found
        if crawl_id:
            update_crawl_status(supabase, crawl_id, status="processing", total_pages=len(new_urls))
        
        # ===== PHASE 3: DISPATCH WORKERS =====
        logger.info(f"🚀 [Master:{task_id}] Dispatching {len(new_urls)} worker tasks...")
        
        # Create Celery Group for parallel execution
        job = group(
            process_page_task.s(url, user_id, crawl_id)
            for url in new_urls
        )
        
        # Apply async - workers will process in parallel
        result = job.apply_async()
        
        # Wait for completion and collect results
        # Note: For very large crawls, consider using a callback instead
        try:
            results = result.get(timeout=3600)  # 1 hour max
            
            success_count = sum(1 for r in results if r.get("status") == "success")
            failed_count = sum(1 for r in results if r.get("status") == "failed")
            
            logger.info(f"✅ [Master:{task_id}] Crawl complete: {success_count} success, {failed_count} failed")
            
            if crawl_id:
                update_crawl_status(
                    supabase, crawl_id,
                    status="completed",
                    pages_ingested=success_count,
                    pages_failed=failed_count
                )
            
            create_notification(
                supabase, user_id,
                "Web Crawl Complete",
                f"Successfully ingested {success_count} pages from {root_url}",
                "success",
                {"crawl_id": crawl_id, "pages_ingested": success_count}
            )
            
            return {
                "status": "success",
                "discovered": total_discovered,
                "processed": len(new_urls),
                "success": success_count,
                "failed": failed_count
            }
            
        except Exception as e:
            logger.error(f"❌ [Master:{task_id}] Worker group failed: {e}")
            raise
        
    except Exception as e:
        logger.error(f"❌ [Master:{task_id}] Discovery failed: {e}")
        
        if crawl_id:
            update_crawl_status(supabase, crawl_id, status="failed", error_message=str(e))
        
        create_notification(
            supabase, user_id,
            "Web Crawl Failed",
            f"Failed to crawl {root_url}: {str(e)[:200]}",
            "error",
            {"crawl_id": crawl_id, "error": str(e)}
        )
        
        raise


@celery_app.task(bind=True)
def health_check_task(self):
    """Simple task to verify worker is running."""
    return {"status": "healthy", "task_id": self.request.id}

