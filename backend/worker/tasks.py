"""
Celery Worker Tasks

Background tasks for heavy file processing (ingestion, parsing, embedding).
These run in a separate worker process to avoid blocking the FastAPI server.
"""

import logging
import json
import base64
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from core.celery_app import celery_app
from core.db import get_supabase
from core.config import settings
from core.security import decrypt_token
from services.parsers import DocumentParser, DocumentProcessorFactory
from services.email import email_service
from connectors.factory import get_connector
from services.embeddings import generate_embeddings_batch

logger = logging.getLogger(__name__)
logger.info("✅ Worker tasks module loaded - Cache buster 001")


# ============================================================
# JOB PROGRESS HELPERS
# ============================================================

def update_job_status(
    supabase,
    job_id: str,
    status: str,
    processed_files: int = None,
    error_message: str = None,
    message: str = None,
    failed_files: int = None,
    progress: int = None,
):
    """Helper to update ingestion job status in the database."""
    try:
        update_data = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        if processed_files is not None:
            update_data["processed_files"] = processed_files
        if failed_files is not None:
            update_data["failed_files"] = failed_files
        if error_message is not None:
            update_data["error_message"] = error_message
        if message is not None:
            update_data["message"] = message
            update_data["status_message"] = message
        if progress is not None:
            update_data["progress"] = progress
            
        supabase.table("ingestion_jobs").update(update_data).eq("id", job_id).execute()
        logger.info(f"📊 [Job:{job_id}] Status: {status}, Processed: {processed_files}")
    except Exception as e:
        logger.error(f"❌ [Job:{job_id}] Failed to update status: {e}")


def update_job_progress(supabase, job_id: str, progress: int, message: str = None):
    """Update job progress percentage for granular UX feedback."""
    try:
        update_data = {
            "progress": progress,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        if message:
            update_data["message"] = message
            update_data["status_message"] = message
            
        supabase.table("ingestion_jobs").update(update_data).eq("id", job_id).execute()
    except Exception as e:
        logger.warning(f"⚠️ [Job:{job_id}] Failed to update progress: {e}")


def ingest_document_batched(
    supabase,
    user_id: str,
    doc_title: str,
    source_type: str,
    metadata: dict,
    chunks_payload: list,
    file_size_bytes: int = 0,
    job_id: str = None,
    source_url: str = None,
    file_status_id: str = None  # NEW: for per-file progress tracking
) -> str:
    """
    Insert document and chunks in batches to prevent DB timeouts.
    
    This replaces the single-RPC approach which times out on large documents.
    
    Args:
        supabase: Supabase client
        user_id: User ID
        doc_title: Document title
        source_type: Source type (file, drive, notion, web)
        metadata: Document metadata dict
        chunks_payload: List of chunk dicts with content, embedding, etc.
        file_size_bytes: File size for quota tracking
        job_id: Optional job ID for progress updates
        source_url: Optional source URL
        file_status_id: Optional file status ID for per-file chunk progress
        
    Returns:
        Document ID (UUID string)
    """
    DB_BATCH_SIZE = 50  # Insert 50 chunks at a time to prevent timeouts
    
    # Step 1: Create parent document record FIRST
    # NOTE: Using actual column names from migrations:
    # - file_size_bytes (not file_size)
    # - chunk_count doesn't exist in schema
    doc_data = {
        "user_id": user_id,
        "title": doc_title,
        "source_type": source_type,
        "source_url": source_url,
        "metadata": metadata,
        "file_size_bytes": file_size_bytes,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    
    doc_result = supabase.table("documents").insert(doc_data).execute()
    if not doc_result.data:
        raise Exception("Failed to create document record")
    
    doc_id = doc_result.data[0]["id"]
    logger.info(f"📄 Created document {doc_id}: {doc_title}")
    
    # Step 2: Insert chunks in batches with progress tracking
    total_chunks = len(chunks_payload)
    
    if total_chunks == 0:
        return str(doc_id)
    
    inserted_count = 0
    for i in range(0, total_chunks, DB_BATCH_SIZE):
        batch = chunks_payload[i:i + DB_BATCH_SIZE]
        
        # Add document_id to each chunk
        for chunk in batch:
            chunk["document_id"] = str(doc_id)
            # Schema Fix: Remove metadata from chunk as column doesn't exist in document_chunks
            if "metadata" in chunk:
                del chunk["metadata"]
            # Schema Fix: Remove metadata from chunk as column doesn't exist in document_chunks
            if "metadata" in chunk:
                del chunk["metadata"]
        
        # Insert this batch
        try:
            supabase.table("document_chunks").insert(batch).execute()
            inserted_count += len(batch)
        except Exception as e:
            logger.error(f"❌ Failed to insert chunk batch {i//DB_BATCH_SIZE + 1}: {e}")
            # Continue with other batches - partial ingestion is better than none
            continue
        
        # Per-chunk progress updates intentionally omitted (stage-based updates only).
    
    logger.info(f"✅ Inserted {inserted_count} chunks for document {doc_id}")
    return str(doc_id)



# ============================================================
# PER-FILE STATUS TRACKING HELPERS
# ============================================================

def create_file_status(
    supabase, 
    job_id: str, 
    user_id: str, 
    filename: str, 
    file_size: int = 0
) -> Optional[str]:
    """
    Create a file status record for granular progress tracking.
    
    Args:
        supabase: Supabase client
        job_id: Parent ingestion job ID
        user_id: User ID
        filename: Name of the file being processed
        file_size: File size in bytes
        
    Returns:
        File status record ID (UUID string) or None on error
    """
    try:
        result = supabase.table("ingestion_file_status").insert({
            "job_id": job_id,
            "user_id": user_id,
            "filename": filename,
            "file_size_bytes": file_size,
            "status": "pending",
            "progress": 0,
            "status_message": "Queued for processing"
        }).execute()
        
        if result.data:
            file_status_id = result.data[0]["id"]
            logger.debug(f"📄 Created file status: {filename} ({file_status_id[:8]}...)")
            return file_status_id
        return None
    except Exception as e:
        logger.warning(f"⚠️ Failed to create file status for {filename}: {e}")
        return None


def update_file_status(
    supabase,
    file_status_id: str,
    status: str = None,
    progress: int = None,
    message: str = None,
    error: str = None,
    chunks_total: int = None,
    chunks_processed: int = None,
    document_id: str = None
):
    """
    Update file processing status for real-time UI feedback.
    
    Status progression: pending → uploading → parsing → embedding → indexing → completed/failed/skipped
    
    Args:
        file_status_id: The file status record ID
        status: New status (pending/uploading/parsing/embedding/indexing/completed/failed/skipped)
        progress: Progress percentage (0-100)
        message: Human-readable status message
        error: Error message (for failed status)
        chunks_total: Total chunks for this file
        chunks_processed: Chunks processed so far
        document_id: Final document ID after successful ingestion
    """
    if not file_status_id:
        return
        
    try:
        update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
        
        if status:
            update_data["status"] = status
        if progress is not None:
            update_data["progress"] = min(100, max(0, progress))
        if message:
            update_data["status_message"] = message
        if error:
            update_data["error_message"] = error
        if chunks_total is not None:
            update_data["chunks_total"] = chunks_total
        if chunks_processed is not None:
            update_data["chunks_processed"] = chunks_processed
        if document_id:
            update_data["document_id"] = document_id
            
        supabase.table("ingestion_file_status").update(update_data).eq("id", file_status_id).execute()
        
    except Exception as e:
        logger.warning(f"⚠️ Failed to update file status {file_status_id[:8]}...: {e}")


# ============================================================
# JOB CANCELLATION HELPERS
# ============================================================

def check_job_cancelled(supabase, job_id: str) -> bool:
    """
    Check if a job has been cancelled.
    
    Call this periodically in processing loops to support cancellation.
    
    Args:
        supabase: Supabase client
        job_id: Job ID to check
        
    Returns:
        True if job is cancelled, False otherwise
    """
    if not job_id:
        return False
    
    try:
        result = supabase.table("ingestion_jobs")\
            .select("status")\
            .eq("id", job_id)\
            .single()\
            .execute()
        
        return result.data and result.data.get("status") == "cancelled"
    except Exception as e:
        logger.warning(f"⚠️ Failed to check job cancellation status: {e}")
        return False


def store_celery_task_id(supabase, job_id: str, celery_task_id: str):
    """
    Store the Celery task ID for a job to enable task revocation.
    
    Args:
        supabase: Supabase client
        job_id: Job ID
        celery_task_id: Celery task ID from self.request.id
    """
    if not job_id or not celery_task_id:
        return
    
    try:
        supabase.table("ingestion_jobs").update({
            "celery_task_id": celery_task_id
        }).eq("id", job_id).execute()
        
        logger.debug(f"📝 Stored Celery task ID {celery_task_id} for job {job_id}")
    except Exception as e:
        logger.warning(f"⚠️ Failed to store Celery task ID: {e}")


def create_notification(
    supabase,
    user_id: str,
    title: str,
    message: str = None,
    notification_type: str = "info",
    metadata: dict = None,
    action_url: str = None,
    check_setting_key: str = None
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
        action_url: Optional URL to navigate to when clicked (e.g., '/dashboard/chat')
        check_setting_key: Optional setting key to check. If user has this
                          setting disabled, notification will not be created.
    """
    try:
        # Check user preference if setting key provided
        if check_setting_key:
            try:
                pref = supabase.table("user_notification_settings")\
                    .select("enabled")\
                    .eq("user_id", user_id)\
                    .eq("setting_key", check_setting_key)\
                    .maybeSingle()\
                    .execute()
                
                # If preference exists and is explicitly False, skip notification
                if pref.data and pref.data.get("enabled") is False:
                    logger.info(f"🔕 [Notification] Skipped for {user_id}: {check_setting_key} is disabled")
                    return
            except Exception as e:
                # Fail open - don't block notifications on preference check errors
                logger.warning(f"⚠️ [Notification] Failed to check preference: {e}")
        
        # Include action_url in metadata if provided
        meta = metadata.copy() if metadata else {}
        if action_url:
            meta["action_url"] = action_url
        
        notification_data = {
            "user_id": user_id,
            "title": title,
            "message": message,
            "type": notification_type,
            "is_read": False,
            # Serialize dict as JSON string for extra_data column
            "extra_data": json.dumps(meta) if meta else None,
            "created_at": datetime.now(timezone.utc).isoformat()
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
        # Fetch user name from profile (table does not have email)
        try:
            user_response = supabase.table("user_profiles").select("display_name, full_name").eq("user_id", user_id).single().execute()
            user_data = user_response.data or {}
            name = user_data.get("display_name") or user_data.get("full_name") or "there"
        except Exception:
            name = "there"
            
        # Fetch email from Auth Admin (requires Service Role key)
        email = None
        try:
            # tasks.py uses the global supabase client which has SECRET_KEY (Admin)
            auth_user = supabase.auth.admin.get_user_by_id(user_id)
            if auth_user and auth_user.user:
                email = auth_user.user.email
        except Exception as auth_error:
            logger.warning(f"📧 [Email] Failed to fetch auth user details: {auth_error}")
            
        if not email:
            logger.warning(f"📧 [Email] No email found for user {user_id}")
            return
        
        # Check user preference in user_notification_settings (key-value table)
        # Default to True if no explicit setting exists - fail-safe approach
        email_enabled = True  # Default if no setting or on error
        try:
            settings_response = supabase.table("user_notification_settings") \
                .select("enabled") \
                .eq("user_id", user_id) \
                .eq("setting_key", "email_on_ingestion_complete") \
                .maybe_single().execute()
            
            if settings_response and settings_response.data:
                email_enabled = settings_response.data.get("enabled", True)
        except Exception as settings_error:
            logger.warning(f"📧 [Email] Could not fetch settings (defaulting to enabled): {settings_error}")
        
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
        # Fetch user name from profile (table does not have email)
        try:
            user_response = supabase.table("user_profiles").select("display_name, full_name").eq("user_id", user_id).single().execute()
            user_data = user_response.data or {}
            name = user_data.get("display_name") or user_data.get("full_name") or "there"
        except Exception:
            name = "there"
            
        # Fetch email from Auth Admin (requires Service Role key)
        email = None
        try:
            # tasks.py uses the global supabase client which has SECRET_KEY (Admin)
            auth_user = supabase.auth.admin.get_user_by_id(user_id)
            if auth_user and auth_user.user:
                email = auth_user.user.email
        except Exception as auth_error:
            logger.warning(f"📧 [Email] Failed to fetch auth user details: {auth_error}")
            
        if not email:
            logger.warning(f"📧 [Email] No email found for user {user_id}")
            return
        
        # Check user preference (respect opt-out for error emails too) - fail-safe
        email_enabled = True  # Default if no setting or on error
        try:
            settings_response = supabase.table("user_notification_settings") \
                .select("enabled") \
                .eq("user_id", user_id) \
                .eq("setting_key", "email_on_ingestion_complete") \
                .maybe_single().execute()
            
            if settings_response and settings_response.data:
                email_enabled = settings_response.data.get("enabled", True)
        except Exception as settings_error:
            logger.warning(f"📧 [Email] Could not fetch settings (defaulting to enabled): {settings_error}")
        
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
# UNIFIED DOCUMENT PROCESSING PIPELINE
# ============================================================

from dataclasses import dataclass

@dataclass
class ProcessResult:
    """Result of processing a single document."""
    success: bool
    document_id: str = None
    chunks_count: int = 0
    error: str = None


def process_document_pipeline(
    supabase,
    content: bytes | str,
    filename: str,
    user_id: str,
    job_id: str,
    file_status_id: str,
    source_type: str,
    metadata: dict = None,
    source_url: str = None
) -> ProcessResult:
    """
    Unified document processing pipeline.
    
    Handles the common flow for all document types:
    1. Parse content → chunks
    2. Generate embeddings
    3. Insert into database (batched)
    4. Update file status throughout
    
    Args:
        supabase: Supabase client
        content: File content as bytes or string
        filename: Original filename
        user_id: User ID
        job_id: Parent ingestion job ID
        file_status_id: Per-file status tracking ID
        source_type: Source type (file, drive, notion, web)
        metadata: Optional additional metadata
        source_url: Optional source URL
        
    Returns:
        ProcessResult with success status, document_id, chunk count
    """
    try:
        # 1. Parse content
        update_file_status(supabase, file_status_id,
            status="parsing", progress=25, message="Extracting content...")
        
        # Handle both bytes and string content
        if isinstance(content, str):
            content_bytes = content.encode('utf-8')
        else:
            content_bytes = content
        
        # Process through document factory
        result = DocumentProcessorFactory.process(
            content=content_bytes,
            filename=filename,
            mime_type=metadata.get('mime_type') if metadata else None
        )
        
        if not result.chunks:
            update_file_status(supabase, file_status_id,
                status="skipped", progress=100, message="No content found")
            return ProcessResult(success=True, chunks_count=0)
        
        update_file_status(supabase, file_status_id,
            progress=40, message=f"Parsed {len(result.chunks)} chunks",
            chunks_total=len(result.chunks))
        
        # 2. Generate embeddings
        update_file_status(supabase, file_status_id,
            status="embedding", progress=50, message="Generating embeddings...")
        
        chunk_texts = [chunk.content for chunk in result.chunks]
        chunk_embeddings = generate_embeddings_batch(chunk_texts)
        
        update_file_status(supabase, file_status_id,
            progress=70, message="Embeddings complete")
        
        # 3. Build chunks payload
        chunks_payload = []
        for chunk, embedding in zip(result.chunks, chunk_embeddings):
            if embedding is None:
                continue
            chunks_payload.append({
                "content": chunk.content,
                "embedding": embedding,
                "chunk_index": chunk.chunk_index,
                "metadata": {
                    **chunk.metadata,
                    "token_count": chunk.token_count,
                }
            })
        
        # 4. Index in database
        update_file_status(supabase, file_status_id,
            status="indexing", progress=80, message="Saving to database...")
        
        # Merge metadata
        doc_metadata = {
            **(metadata or {}),
            "file_type": result.file_type,
            "total_tokens": result.total_tokens,
            "total_chunks": len(result.chunks),
            **(result.metadata or {}),
        }
        
        doc_id = ingest_document_batched(
            supabase=supabase,
            user_id=user_id,
            doc_title=filename,
            source_type=source_type,
            metadata=doc_metadata,
            chunks_payload=chunks_payload,
            file_size_bytes=len(content_bytes),
            job_id=job_id,
            source_url=source_url,
            file_status_id=file_status_id
        )
        
        # 5. Complete
        if doc_id:
            update_file_status(supabase, file_status_id,
                status="completed", progress=100, message="Complete",
                chunks_processed=len(chunks_payload), document_id=doc_id)
            
            return ProcessResult(
                success=True,
                document_id=doc_id,
                chunks_count=len(chunks_payload)
            )
        else:
            update_file_status(supabase, file_status_id,
                status="failed", progress=0, error="Failed to save document")
            return ProcessResult(success=False, error="Database insert failed")
            
    except Exception as e:
        update_file_status(supabase, file_status_id,
            status="failed", progress=0, error=str(e))
        return ProcessResult(success=False, error=str(e))


# ============================================================
# UNIFIED INGESTION TASK (NEW ARCHITECTURE)
# ============================================================

STAGING_BUCKET = "ephemeral-staging"



# ============================================================
# UNIFIED INGESTION TASK - Production Grade with DLQ
# ============================================================

def handle_task_failure(self, exc, task_id, args, kwargs, einfo):
    """
    Handle task failure by logging to dead letter queue.
    
    This callback is triggered when a Celery task fails after all retries.
    It logs the failure to the failed_tasks table for tracking and potential retry.
    """
    try:
        from worker.dlq_worker import log_task_failure
        
        # Extract user_id and job_id from kwargs
        user_id = kwargs.get('user_id')
        job_id = kwargs.get('job_id')
        
        # Log to DLQ with full context
        log_task_failure(
            task_id=task_id,
            task_name=self.name,
            args=args,
            kwargs=kwargs,
            exc=exc,
            traceback_str=str(einfo),
            user_id=user_id,
            job_id=job_id
        )
        
        logger.info(f"📥 [DLQ] Logged failed task {task_id} to dead letter queue")
        
    except Exception as e:
        logger.error(f"❌ [DLQ] Failed to log task failure to DLQ: {e}")




@celery_app.task(
    bind=True,
    name="unified_ingest_task",
    on_failure=handle_task_failure,
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
    acks_late=True
)
def unified_ingest_task(
    self,
    user_id: str,
    job_id: str,
    connector_type: str,
    item_ids: list,
    credentials: Dict[str, Any] = None
):
    """
    UNIFIED ingestion task for ALL data sources.
    
    Now uses FAN-OUT PATTERN for true parallel processing:
    1. Fetch all files from connector
    2. Create file status records
    3. Dispatch parallel process_file_task for each file
    4. chord callback aggregates results
    
    Args:
        user_id: User ID
        job_id: Job ID for tracking
        connector_type: 'file_upload', 'google_drive', 'notion', 'web', etc.
        item_ids: List of items to ingest (paths, IDs, URLs)
        credentials: Optional auth credentials
    """
    import asyncio
    import base64
    from celery import chord, group
    from connectors import get_connector
    
    task_id = self.request.id
    logger.info(f"[UnifiedIngest:{task_id}] Starting FAN-OUT: {connector_type}, Job: {job_id}")
    
    supabase = get_supabase()
    
    try:
        # Store Celery task ID for cancellation support
        store_celery_task_id(supabase, job_id, task_id)
        
        # Check if job was cancelled before we start
        if check_job_cancelled(supabase, job_id):
            logger.info(f"🛑 [UnifiedIngest:{task_id}] Job cancelled before start")
            return {"status": "cancelled"}
        
        # Update job status
        update_job_status(supabase, job_id, "processing")
        
        # Create notification
        create_notification(
            supabase, user_id,
            "Processing Started",
            f"Ingesting documents from {connector_type.replace('_', ' ').title()}",
            "info",
            {"job_id": job_id}
        )
        
        # Get connector instance
        connector = get_connector(connector_type)
        
        # STEP 1: Fetch all documents from connector
        logger.info(f"[UnifiedIngest:{task_id}] Fetching documents from {connector_type}...")
        
        async def collect_documents():
            documents = []
            async for doc in connector.fetch_documents(item_ids, credentials, user_id=user_id):
                documents.append(doc)
            return documents
        
        documents = asyncio.run(collect_documents())
        total_files = len(documents)
        
        logger.info(f"[UnifiedIngest:{task_id}] Collected {total_files} documents for parallel processing")
        
        if total_files == 0:
            update_job_status(
                supabase,
                job_id,
                "completed",
                processed_files=0,
                message="No documents to process",
                progress=100,
            )
            return {"status": "completed", "message": "No documents"}
        
        # Update job with total count
        supabase.table("ingestion_jobs").update({
            "total_files": total_files,
            "progress": 5,
            "message": f"Preparing {total_files} files for parallel processing...",
            "status_message": f"Preparing {total_files} files for parallel processing..."
        }).eq("id", job_id).execute()
        
        # STEP 2: Create file status records and serialize documents
        file_tasks = []
        
        for i, doc in enumerate(documents):
            # Create file status record
            file_status_result = supabase.table("ingestion_file_status").insert({
                "job_id": job_id,
                "user_id": user_id,
                "filename": doc.filename,
                "file_size_bytes": doc.size_bytes,  # FIXED: was "file_size"
                "status": "pending",
                "progress": 0,
                "status_message": "Queued for processing..."  # FIXED: was "message"
            }).execute()
            
            file_status_id = file_status_result.data[0]["id"]
            
            # Serialize document content to base64 for Celery
            content_b64 = base64.b64encode(doc.content).decode('utf-8')
            
            file_data = {
                "filename": doc.filename,
                "content_b64": content_b64,
                "size_bytes": doc.size_bytes,
                "mime_type": doc.mime_type
            }
            
            # Create task signature
            file_tasks.append(
                process_file_task.s(
                    user_id=user_id,
                    job_id=job_id,
                    file_data=file_data,
                    file_status_id=file_status_id,
                    connector_type=connector_type
                )
            )
        
        logger.info(f"[UnifiedIngest:{task_id}] Dispatching {len(file_tasks)} parallel tasks...")
        
        # Update job status
        supabase.table("ingestion_jobs").update({
            "progress": 10,
            "message": f"Processing {total_files} files in parallel...",
            "status_message": f"Processing {total_files} files in parallel..."
        }).eq("id", job_id).execute()
        
        # STEP 3: Dispatch all tasks in parallel using chord
        # chord = group of tasks + callback when all complete
        job = chord(
            group(file_tasks),
            finalize_job_task.s(user_id=user_id, job_id=job_id, total_files=total_files)
        )
        
        result = job.apply_async()
        
        logger.info(f"[UnifiedIngest:{task_id}] ✅ Dispatched chord with {total_files} tasks, chord_id: {result.id}")
        
        return {
            "status": "dispatched",
            "job_id": job_id,
            "total_files": total_files,
            "chord_id": result.id
        }
        
    except Exception as e:
        logger.error(f"[UnifiedIngest:{task_id}] Failed: {e}")
        update_job_status(supabase, job_id, "failed", error_message=str(e))
        
        # Create failure notification
        create_notification(
            supabase, user_id,
            "Ingestion Failed",
            f"Failed to process {connector_type}: {str(e)}",
            "error",
            {"job_id": job_id, "connector": connector_type}
        )
        raise


# ============================================================
# FAN-OUT PARALLEL PROCESSING TASKS
# ============================================================

@celery_app.task(
    bind=True,
    name="process_file_task",
    on_failure=handle_task_failure,
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=2,
    acks_late=True,
    soft_time_limit=600,  # 10 min per file
    time_limit=660  # Hard kill at 11 min
)
def process_file_task(
    self,
    user_id: str,
    job_id: str,
    file_data: Dict[str, Any],
    file_status_id: str,
    connector_type: str
):
    """
    Process a SINGLE file independently.
    
    This task is spawned by unified_ingest_task for each file,
    enabling true parallel processing across all Celery workers.
    
    Args:
        user_id: User ID
        job_id: Parent job ID
        file_data: Serialized file data (filename, content_b64, size, mime_type)
        file_status_id: ID of the file status record for progress tracking
        connector_type: Source type for metadata
    """
    import asyncio
    import base64
    import tempfile
    import os
    import time
    from services.parsers import DocumentFactory
    from services.embeddings import generate_embeddings_batch
    
    task_id = self.request.id
    filename = file_data.get("filename", "unknown")
    logger.info(f"[ProcessFile:{task_id}] Starting: {filename} (job: {job_id})")
    
    supabase = get_supabase()
    local_path = None
    start_time = time.time()
    
    try:
        update_file_status(
            supabase,
            file_status_id,
            status="uploading",
            progress=10,
            message="Preparing file..."
        )
        
        # STEP 1: Decode content and write to temp file
        content_b64 = file_data.get("content_b64")
        if not content_b64:
            raise ValueError("No content provided")
        
        content = base64.b64decode(content_b64)
        
        suffix = os.path.splitext(filename)[1] or ".bin"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            local_path = tmp.name
        
        # STEP 2: Parse document
        update_file_status(
            supabase,
            file_status_id,
            status="parsing",
            progress=30,
            message="Extracting content (may take 30-90s for PDFs)..."
        )
        
        async def parse_document():
            factory = DocumentFactory()
            return await factory.process(local_path, filename)
        
        chunks = asyncio.run(parse_document())
        
        if not chunks:
            update_file_status(
                supabase,
                file_status_id,
                status="skipped",
                progress=100,
                message="No content extracted",
                chunks_total=0
            )
            return {"status": "skipped", "filename": filename, "reason": "empty"}
        
        # STEP 3: Generate embeddings
        update_file_status(
            supabase,
            file_status_id,
            status="embedding",
            progress=60,
            message=f"Generating embeddings for {len(chunks)} chunks...",
            chunks_total=len(chunks)
        )
        
        async def generate_embeddings():
            texts = [c["text"] for c in chunks]
            return await generate_embeddings_batch(texts)
        
        embeddings = asyncio.run(generate_embeddings())
        
        # STEP 4: Store in database
        update_file_status(
            supabase,
            file_status_id,
            status="indexing",
            progress=85,
            message="Storing in database..."
        )
        
        # Create document record
        doc_result = supabase.table("documents").insert({
            "user_id": user_id,
            "title": filename,
            "source_type": connector_type,
            "file_size_bytes": file_data.get("size_bytes", len(content)),
            "metadata": {
                "job_id": job_id,
                "mime_type": file_data.get("mime_type", "application/octet-stream"),
            },
        }).execute()
        
        doc_id = doc_result.data[0]["id"]
        
        # Insert chunks in batches
        BATCH_SIZE = 50
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i:i+BATCH_SIZE]
            batch_embeddings = embeddings[i:i+BATCH_SIZE]
            
            chunk_records = []
            for j, (chunk, embedding) in enumerate(zip(batch, batch_embeddings)):
                chunk_records.append({
                    "document_id": doc_id,
                    "content": chunk["text"],
                    "embedding": embedding,
                    "chunk_index": i + j,
                })

            supabase.table("document_chunks").insert(chunk_records).execute()
        
        # STEP 5: Success
        total_time = int(time.time() - start_time)
        update_file_status(
            supabase,
            file_status_id,
            status="completed",
            progress=100,
            message=f"✅ Completed in {total_time}s",
            chunks_total=len(chunks),
            chunks_processed=len(chunks),
            document_id=doc_id
        )
        
        logger.info(f"[ProcessFile:{task_id}] ✅ {filename}: {len(chunks)} chunks in {total_time}s")
        
        return {
            "status": "success",
            "filename": filename,
            "doc_id": doc_id,
            "chunks": len(chunks),
            "time": total_time
        }
        
    except Exception as e:
        logger.error(f"[ProcessFile:{task_id}] ❌ {filename}: {e}")
        
        update_file_status(
            supabase,
            file_status_id,
            status="failed",
            progress=0,
            message=str(e)[:500],
            error=str(e)[:1000]
        )
        
        return {
            "status": "failed",
            "filename": filename,
            "error": str(e)
        }
        
    finally:
        # Cleanup temp file
        if local_path and os.path.exists(local_path):
            try:
                os.unlink(local_path)
            except:
                pass


@celery_app.task(
    bind=True,
    name="finalize_job_task"
)
def finalize_job_task(self, results: list, user_id: str, job_id: str, total_files: int):
    """
    Callback task that runs after all file processing tasks complete.
    
    Aggregates results and updates job status.
    
    Args:
        results: List of results from all process_file_task calls
        user_id: User ID
        job_id: Job ID
        total_files: Total number of files submitted
    """
    task_id = self.request.id
    logger.info(f"[FinalizeJob:{task_id}] Aggregating results for job {job_id}")
    
    supabase = get_supabase()
    
    # Count successes and failures
    successful = [r for r in results if r and r.get("status") == "success"]
    failed = [r for r in results if r and r.get("status") == "failed"]
    skipped = [r for r in results if r and r.get("status") == "skipped"]

    successful_count = len(successful)
    failed_count = len(failed)
    skipped_count = len(skipped)
    processed_count = successful_count + skipped_count

    total_chunks = sum(r.get("chunks", 0) for r in successful)

    # Determine final status
    if failed_count == 0:
        final_status = "completed"
    elif processed_count > 0:
        final_status = "completed"
    else:
        final_status = "failed"

    if final_status == "failed":
        status_msg = f"All {failed_count} files failed"
    else:
        status_parts = [f"Processed {processed_count}/{total_files} files"]
        if skipped_count:
            status_parts.append(f"{skipped_count} skipped")
        if failed_count:
            status_parts.append(f"{failed_count} failed")
        if total_chunks:
            status_parts.append(f"{total_chunks} chunks")
        status_msg = ", ".join(status_parts)

    # Update job status
    supabase.table("ingestion_jobs").update({
        "status": final_status,
        "progress": 100,
        "message": status_msg,
        "status_message": status_msg,
        "processed_files": processed_count,
        "failed_files": failed_count,
        "total_files": total_files,
        "error_message": status_msg if final_status == "failed" else None,
    }).eq("id", job_id).execute()

    # Create completion notification
    if final_status == "failed":
        notification_type = "error"
    elif failed_count > 0:
        notification_type = "warning"
    else:
        notification_type = "success"
    create_notification(
        supabase, user_id,
        "Ingestion Complete" if final_status != "failed" else "Ingestion Failed",
        status_msg,
        notification_type,
        {"job_id": job_id, "successful": successful_count, "failed": failed_count, "skipped": skipped_count}
    )
    
    # Send email if configured
    if len(successful) > 0:
        send_email_notification(supabase, user_id, len(successful))
    
    logger.info(f"[FinalizeJob:{task_id}] ✅ Job {job_id}: {status_msg}")
    
    return {
        "job_id": job_id,
        "status": final_status,
        "successful": len(successful),
        "failed": len(failed),
        "skipped": len(skipped),
        "total_chunks": total_chunks
    }


# ============================================================
# LEGACY FILE INGESTION TASK (TO BE DEPRECATED)
# ============================================================

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
        from services.embeddings import generate_embeddings_batch
        
        chunk_texts = [chunk.content for chunk in result.chunks]
        chunk_embeddings = generate_embeddings_batch(chunk_texts)
        
        # Build chunks payload with enriched metadata
        chunks_payload = []
        failed_chunks = 0
        for chunk, embedding in zip(result.chunks, chunk_embeddings):
            if embedding is None:
                failed_chunks += 1
                logger.warning(f"⚠️ [Page:{task_id}] Skipped chunk {chunk.chunk_index} for {url} due to failed embedding")
                continue
                
            chunks_payload.append({
                "content": chunk.content,
                "embedding": embedding,
                "chunk_index": chunk.chunk_index,
                "metadata": {
                    **chunk.metadata,
                    "token_count": chunk.token_count,
                }
            })
        
        # Check for partial failure
        if failed_chunks > 0:
            total_chunks = len(result.chunks)
            if failed_chunks / total_chunks > 0.5:
                logger.error(f"❌ [Page:{task_id}] High embedding failure rate: {failed_chunks}/{total_chunks} chunks failed for {url}")
        
        # Document metadata
        doc_metadata = {
            **page_metadata,
            "file_type": "web",
            "total_tokens": result.total_tokens,
            "total_chunks": len(result.chunks),
        }
        
        # Store using atomic RPC
        content_size = len(html_content.encode('utf-8')) if 'html_content' in dir() else 0
        rpc_result = supabase.rpc("ingest_document_with_chunks", {
            "p_user_id": user_id,
            "p_doc_title": page_title,
            "p_source_type": "web",
            "p_source_url": url,
            "p_metadata": json.dumps(doc_metadata),
            "p_chunks": json.dumps(chunks_payload),
            "p_file_size_bytes": content_size
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
    now = datetime.now(timezone.utc)
    
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
                
                # Queue unified ingestion task for web crawl
                from worker.tasks import unified_ingest_task
                task = unified_ingest_task.delay(
                    user_id=user_id,
                    job_id=crawl_id,
                    connector_type="web",
                    item_ids=[root_url],
                    credentials=None
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
        from services.embeddings import generate_embeddings_batch
        
        doc = docs[0]  # Single URL = single doc
        chunk_embeddings = generate_embeddings_batch([doc.page_content])
        chunk_embedding = chunk_embeddings[0]
        
        # Prepare for RPC
        chunks_payload = [{
            "content": doc.page_content,
            "embedding": chunk_embedding,
            "chunk_index": 0
        }]
        
        # Atomic insert via RPC
        content_size = len(doc.page_content.encode('utf-8'))
        rpc_result = supabase.rpc("ingest_document_with_chunks", {
            "p_user_id": user_id,
            "p_doc_title": doc.metadata.get("title", url),
            "p_source_type": doc.metadata.get("source", "web"),
            "p_source_url": url,
            "p_metadata": json.dumps(doc.metadata),
            "p_chunks": json.dumps(chunks_payload),
            "p_file_size_bytes": content_size
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


# ============================================================
# DATABASE CLEANUP TASK
# ============================================================

@celery_app.task(bind=True)
def cleanup_old_jobs(self):
    """
    Clean up old completed/failed ingestion jobs.
    
    Runs daily via Celery Beat to prevent database bloat.
    Deletes jobs older than 30 days that are no longer active.
    """
    from core.db import get_supabase
    from datetime import datetime, timedelta, timezone
    
    task_id = self.request.id[:8] if self.request.id else "cleanup"
    logger.info(f"🧹 [Cleanup:{task_id}] Starting database cleanup...")
    
    try:
        supabase = get_supabase()
        
        # Calculate cutoff date (30 days ago)
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        
        # Delete old completed jobs
        completed_result = supabase.table("ingestion_jobs")\
            .delete()\
            .in_("status", ["completed", "failed"])\
            .lt("created_at", cutoff_date)\
            .execute()
        
        deleted_count = len(completed_result.data) if completed_result.data else 0
        logger.info(f"🧹 [Cleanup:{task_id}] Deleted {deleted_count} old ingestion jobs")
        
        # Delete old read notifications (keep unread ones)
        notif_result = supabase.table("notifications")\
            .delete()\
            .eq("is_read", True)\
            .lt("created_at", cutoff_date)\
            .execute()
        
        notif_deleted = len(notif_result.data) if notif_result.data else 0
        logger.info(f"🧹 [Cleanup:{task_id}] Deleted {notif_deleted} old notifications")
        
        return {
            "status": "success",
            "jobs_deleted": deleted_count,
            "notifications_deleted": notif_deleted
        }
        
    except Exception as e:
        logger.error(f"❌ [Cleanup:{task_id}] Cleanup failed: {e}")
        return {"status": "error", "error": str(e)}
