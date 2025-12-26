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

# ============================================================
# INGESTION TASK
# ============================================================

@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,  # Exponential backoff: 1s, 2s, 4s, 8s...
    retry_backoff_max=600,  # Max 10 minutes between retries
    max_retries=3,
    acks_late=True
)
def ingest_file_task(
    self,
    user_id: str,
    provider: str,
    item_ids: List[str],
    credentials: Dict[str, Any],
    job_id: str = None
):
    """
    Background task to ingest files from a provider.
    
    This runs in a separate Celery worker process, so it:
    - Doesn't block the FastAPI server
    - Handles large files without memory issues (prefetch=1)
    - Retries automatically on failure
    - Updates job progress for frontend polling
    
    Args:
        user_id: The user's ID for multi-tenancy
        provider: Provider type (e.g., 'google_drive')
        item_ids: List of file IDs to ingest
        credentials: Encrypted OAuth credentials
        job_id: Optional job ID for progress tracking
    """
    task_id = self.request.id
    logger.info(f"📥 [Worker:{task_id}] Starting ingestion for user {user_id}")
    logger.info(f"📥 [Worker:{task_id}] Provider: {provider}, Items: {len(item_ids)}, Job: {job_id}")
    
    supabase = get_supabase()
    processed_count = 0
    
    try:
        # Update job to processing
        if job_id:
            update_job_status(supabase, job_id, "processing", processed_count)
        
        # Create "started" notification
        create_notification(
            supabase,
            user_id,
            f"Ingestion Started",
            f"Processing {len(item_ids)} files from {provider.replace('_', ' ').title()}",
            "info",
            {"job_id": job_id, "provider": provider, "file_count": len(item_ids)}
        )
        
        # 1. Decrypt credentials
        decrypted_creds = {}
        for key, value in credentials.items():
            if isinstance(value, str):
                decrypted_creds[key] = decrypt_token(value)
            else:
                decrypted_creds[key] = value
        
        # 2. Get connector and ingest
        from connectors.factory import get_connector
        connector = get_connector(provider)
        
        # Prepare config for standardized ingest interface
        ingest_config = {
            "user_id": user_id,
            "item_ids": item_ids,
            "credentials": decrypted_creds,
            "provider": provider
        }
        
        # Call synchronous ingest (worker-compatible)
        docs = connector.ingest(ingest_config)
        
        if not docs:
            logger.warning(f"📥 [Worker:{task_id}] No content processed")
            if job_id:
                update_job_status(supabase, job_id, "completed", len(item_ids))
            return {"status": "skipped", "message": "No content processed"}
        
        # 3. Embed documents
        from langchain_openai import OpenAIEmbeddings
        embeddings_model = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.OPENAI_API_KEY
        )
        
        chunk_texts = [d.page_content for d in docs]
        chunk_embeddings = embeddings_model.embed_documents(chunk_texts)
        
        logger.info(f"📥 [Worker:{task_id}] Embedded {len(chunk_texts)} chunks")
        
        # 4. Map provider to source_type enum
        CONNECTOR_TYPE_TO_ENUM = {
            "google_drive": "drive",
            "drive": "drive",
            "notion": "notion",
            "file_upload": "file",
            "file": "file",
            "web": "web",
        }
        source_type_enum = CONNECTOR_TYPE_TO_ENUM.get(provider, "file")
        
        # 5. Group by source and store
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
                "source_type": source_type_enum,
                "source_url": first_doc.metadata.get('source_url'),
                "metadata": first_doc.metadata,
                "created_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"📄 [Worker:{task_id}] Creating document: {parent_doc_data['title']}")
            
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
            
            # Update progress after each document group
            processed_count += 1
            if job_id:
                update_job_status(supabase, job_id, "processing", processed_count)
        
        # Mark job as completed
        if job_id:
            update_job_status(supabase, job_id, "completed", len(item_ids))
        
        # Create "success" notification
        create_notification(
            supabase,
            user_id,
            f"Ingestion Complete",
            f"Successfully processed {len(results)} documents from {provider.replace('_', ' ').title()}",
            "success",
            {"job_id": job_id, "provider": provider, "document_count": len(results)}
        )
        
        # Send email notification (fail-safe, respects user preferences)
        send_email_notification(supabase, user_id, len(results))
        
        logger.info(f"✅ [Worker:{task_id}] Ingestion complete: {len(results)} documents")
        return {"status": "success", "ingested_ids": results, "task_id": task_id, "job_id": job_id}
        
    except Exception as e:
        logger.error(f"❌ [Worker:{task_id}] Ingestion failed: {e}")
        
        # Update job status to failed
        if job_id:
            update_job_status(supabase, job_id, "failed", processed_count, str(e))
        
        # Create "error" notification
        create_notification(
            supabase,
            user_id,
            f"Ingestion Failed",
            f"Failed to process files from {provider.replace('_', ' ').title()}: {str(e)[:200]}",
            "error",
            {"job_id": job_id, "provider": provider, "error": str(e)}
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
        
        # ===== PHASE 3: EMBEDDING & STORAGE =====
        if documents:
            logger.info(f"🔢 [Crawl] Embedding {len(documents)} documents...")
            
            from langchain_openai import OpenAIEmbeddings
            embeddings_model = OpenAIEmbeddings(
                model="text-embedding-3-small",
                api_key=settings.OPENAI_API_KEY
            )
            
            chunk_texts = [d.page_content for d in documents]
            chunk_embeddings = embeddings_model.embed_documents(chunk_texts)
            
            # Store in database
            for i, doc in enumerate(documents):
                parent_doc_data = {
                    "user_id": user_id,
                    "title": doc.metadata.get("title", "Web Page"),
                    "source_type": doc.metadata.get("source", "web"),
                    "source_url": doc.metadata.get("source_url"),
                    "metadata": doc.metadata,
                    "created_at": datetime.utcnow().isoformat()
                }
                
                p_res = supabase.table("documents").insert(parent_doc_data).execute()
                if p_res.data:
                    parent_id = p_res.data[0]["id"]
                    
                    # Insert chunk
                    chunk_record = {
                        "document_id": parent_id,
                        "content": doc.page_content,
                        "embedding": chunk_embeddings[i],
                        "chunk_index": 0,
                        "created_at": datetime.utcnow().isoformat()
                    }
                    supabase.table("document_chunks").insert(chunk_record).execute()
        
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


@celery_app.task(bind=True)
def health_check_task(self):
    """Simple task to verify worker is running."""
    return {"status": "healthy", "task_id": self.request.id}

