"""
Celery Worker Tasks

Background tasks for heavy file processing (ingestion, parsing, embedding).
These run in a separate worker process to avoid blocking the FastAPI server.
"""

import logging
import inspect
import json
import base64
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from core.celery_app import celery_app
from core.db import get_supabase
from core.db_utils import insert_rows_with_retry, delete_rows_with_retry
from core.config import settings
from core.hashing import compute_content_hash
from core.ingestion_utils import normalize_provider, normalize_source_type
from core.job_counters import (
    init_ingest_job_counters,
    record_ingest_outcome,
    get_ingest_job_counters,
    mark_ingest_job_finalizing,
    clear_ingest_job_counters,
    record_ingest_job_update,
    record_ingest_file_update,
    init_crawl_counters,
    record_crawl_outcome,
    get_crawl_counters,
    mark_crawl_finalizing,
    clear_crawl_counters,
    record_crawl_job_update,
)
from services.parsers import DocumentProcessorFactory
from services.email import email_service
from connectors import get_connector
from connectors.limits import connector_fetch_limit
from services.embeddings import generate_embeddings_batch_sync
from services.malware import scan_content
from services.audit import audit_logger
try:
    from core.metrics import (
        job_counters_missing,
        job_counters_reconciled,
        job_counters_finalize,
        idempotency_hits,
        parser_rejections,
        timeout_total,
        status_updates_total,
    )
except Exception:
    job_counters_missing = None
    job_counters_reconciled = None
    job_counters_finalize = None
    idempotency_hits = None
    parser_rejections = None
    timeout_total = None
    status_updates_total = None

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
    total_files: int = None,
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
        if total_files is not None:
            update_data["total_files"] = total_files
        if error_message is not None:
            update_data["error_message"] = error_message
        if message is not None:
            update_data["message"] = message
            update_data["status_message"] = message
        if progress is not None:
            update_data["progress"] = progress
            
        supabase.table("ingestion_jobs").update(update_data).eq("id", job_id).execute()
        if status_updates_total:
            status_updates_total.labels("job", status).inc()
        record_ingest_job_update(job_id)
        logger.info(f"📊 [Job:{job_id}] Status: {status}, Processed: {processed_files}")
    except Exception as e:
        logger.error(f"❌ [Job:{job_id}] Failed to update status: {e}")


TEXT_LIKE_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".csv",
    ".log",
    ".doc",
    ".docx",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".xml",
    ".html",
    ".css",
    ".sql",
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".go",
    ".cpp",
    ".c",
    ".cs",
    ".rb",
    ".php",
    ".rs",
    ".scala",
    ".swift",
    ".kt",
}


def _resolve_org_scope(supabase, user_id: str) -> Dict[str, Optional[str]]:
    """
    Resolve org scope for dedup: prefers team_id if present, otherwise user_id.
    """
    team_id = None
    try:
        res = supabase.table("team_members").select("team_id").eq("member_user_id", user_id).limit(1).execute()
        if res.data:
            team_id = res.data[0].get("team_id")
    except Exception:
        pass

    if not team_id:
        try:
            owner_res = supabase.table("teams").select("id").eq("owner_id", user_id).limit(1).execute()
            if owner_res.data:
                team_id = owner_res.data[0].get("id")
        except Exception:
            pass

    return {"team_id": team_id, "user_id": user_id}


def _is_duplicate_document(supabase, content_hash: str, org_scope: Dict[str, Optional[str]], user_id: str) -> bool:
    """
    Check for existing document with same hash within org scope.
    """
    if not content_hash:
        return False
    try:
        query = supabase.table("documents").select("id").eq("content_hash", content_hash)
        if org_scope.get("team_id"):
            query = query.eq("team_id", org_scope["team_id"])
        else:
            query = query.eq("user_id", user_id)
        res = query.limit(1).execute()
        if res.data:
            # touch updated_at
            try:
                supabase.table("documents").update(
                    {"updated_at": datetime.now(timezone.utc).isoformat()}
                ).eq("id", res.data[0]["id"]).execute()
            except Exception:
                pass
            return True
    except Exception as exc:
        logger.warning(f"⚠️ [Dedup] Duplicate check failed: {exc}")
    return False


def get_parse_timeout_seconds(filename: str, mime_type: str | None) -> int | None:
    ext = os.path.splitext(filename or "")[1].lower()
    mime = (mime_type or "").lower()

    if ext == ".pdf" or mime == "application/pdf":
        return (
            settings.PDF_PARSE_TIMEOUT_OCR
            if settings.LLAMA_CLOUD_API_KEY
            else settings.PDF_PARSE_TIMEOUT
        )

    if ext in TEXT_LIKE_EXTENSIONS or mime.startswith("text/"):
        return settings.TEXT_PARSE_TIMEOUT

    return None


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
        if status_updates_total:
            status_updates_total.labels("job", "progress").inc()
        record_ingest_job_update(job_id)
    except Exception as e:
        logger.warning(f"⚠️ [Job:{job_id}] Failed to update progress: {e}")


def _should_emit_job_progress_update(job_id: str, processed: int, total: int) -> bool:
    if total <= 0 or processed <= 0:
        return False
    if processed >= total:
        return True
    batch_size = max(1, settings.REDIS_JOB_PROGRESS_UPDATE_BATCH)
    if processed == 1 or processed % batch_size == 0:
        return True
    try:
        import redis
        client = redis.from_url(settings.REDIS_URL)
        throttle_key = f"ingest_job:progress:{job_id}"
        return bool(
            client.set(
                throttle_key,
                "1",
                nx=True,
                ex=settings.REDIS_JOB_PROGRESS_UPDATE_INTERVAL,
            )
        )
    except Exception:
        return False


def _update_job_progress_from_counters(supabase, job_id: str, counters: Dict[str, int]) -> None:
    if not counters:
        return
    total = counters.get("total", 0)
    processed = counters.get("processed", 0)
    failed = counters.get("failed", 0)
    skipped = counters.get("skipped", 0)

    if total <= 0 or processed <= 0:
        return
    if not _should_emit_job_progress_update(job_id, processed, total):
        return

    progress = min(99, int((processed / total) * 100)) if processed < total else 100
    message = f"Processed {processed}/{total} files"
    if skipped:
        message += f", {skipped} skipped"
    if failed:
        message += f", {failed} failed"

    update_job_status(
        supabase,
        job_id,
        "processing",
        processed_files=processed,
        failed_files=failed,
        progress=progress,
        message=message,
    )


def _get_ingestion_counts_from_db(supabase, job_id: str) -> Dict[str, int]:
    counts = {"success": 0, "failed": 0, "skipped": 0}
    try:
        result = supabase.table("ingestion_file_status").select("status").eq("job_id", job_id).execute()
        for row in result.data or []:
            status = row.get("status")
            if status == "completed":
                counts["success"] += 1
            elif status == "failed":
                counts["failed"] += 1
            elif status == "skipped":
                counts["skipped"] += 1
    except Exception as e:
        logger.warning(f"⚠️ [Job:{job_id}] Failed to load file status counts: {e}")

    counts["processed"] = counts["success"] + counts["failed"] + counts["skipped"]
    return counts


def _record_ingest_outcome_and_maybe_finalize(
    supabase,
    user_id: str,
    job_id: str,
    file_status_id: str,
    outcome: str,
) -> None:
    if not job_id or not file_status_id:
        return

    counters = record_ingest_outcome(job_id, file_status_id, outcome)
    if not counters:
        if job_counters_missing:
            job_counters_missing.labels("ingest").inc()
        return

    _update_job_progress_from_counters(supabase, job_id, counters)

    total = counters.get("total", 0)
    processed = counters.get("processed", 0)
    if total <= 0:
        try:
            job_res = supabase.table("ingestion_jobs").select("total_files").eq("id", job_id).single().execute()
            total = job_res.data.get("total_files") if job_res.data else 0
        except Exception:
            total = 0
    if total > 0 and processed >= total:
        if mark_ingest_job_finalizing(job_id):
            finalize_job_task.apply_async(kwargs={"user_id": user_id, "job_id": job_id})


def _record_crawl_outcome_and_maybe_finalize(
    supabase,
    user_id: str,
    crawl_id: Optional[str],
    url: str,
    outcome: str,
    job_id: Optional[str] = None,
) -> None:
    if not crawl_id:
        return

    counters = record_crawl_outcome(crawl_id, url, outcome)
    if not counters:
        if job_counters_missing:
            job_counters_missing.labels("crawl").inc()
        return

    total = counters.get("total", 0)
    processed = counters.get("processed", 0)
    if total <= 0:
        try:
            config_res = supabase.table("web_crawl_configs").select("total_pages_found").eq(
                "id", crawl_id
            ).single().execute()
            total = config_res.data.get("total_pages_found") if config_res.data else 0
        except Exception:
            total = 0
    if total > 0 and processed >= total:
        if mark_crawl_finalizing(crawl_id):
            finalize_crawl_task.apply_async(kwargs={"user_id": user_id, "crawl_id": crawl_id})

    if job_id:
        try:
            progress = None
            if total:
                progress = min(100, int((processed / total) * 100))
            update_job_status(
                supabase,
                job_id,
                status="processing",
                processed_files=processed,
                failed_files=counters.get("failed", 0),
                progress=progress,
            )
        except Exception:
            pass


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
    file_status_id: str = None,  # NEW: for per-file progress tracking
    content_hash: str | None = None
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
    DB_BATCH_SIZE = max(1, min(settings.CHUNK_INSERT_BATCH_SIZE, 200))  # Configurable batch size to prevent timeouts
    source_type = normalize_source_type(source_type) or source_type
    
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
        "content_hash": content_hash,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    
    existing_doc_id = None
    if content_hash:
        existing = supabase.table("documents").select("id").eq("user_id", user_id).eq(
            "title", doc_title
        ).eq("content_hash", content_hash).limit(1).execute()
        existing_data = existing.data if isinstance(getattr(existing, "data", None), list) else []
        if existing_data:
            existing_doc_id = existing_data[0]["id"]

    if existing_doc_id:
        if idempotency_hits:
            idempotency_hits.labels(source_type or "unknown").inc()
        delete_rows_with_retry(
            supabase,
            "document_chunks",
            "document_id",
            existing_doc_id,
            context=f"replace doc_id={existing_doc_id}",
        )
        update_data = {**doc_data, "updated_at": datetime.now(timezone.utc).isoformat()}
        update_data.pop("created_at", None)
        supabase.table("documents").update(update_data).eq("id", existing_doc_id).execute()
        doc_id = existing_doc_id
        logger.info(f"♻️ Reusing document {doc_id} for {doc_title}")
    else:
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
        
        # Insert this batch
        try:
            insert_rows_with_retry(
                supabase,
                "document_chunks",
                batch,
                context=f"doc_id={doc_id} batch={i // DB_BATCH_SIZE + 1}",
            )
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
    job_id: str = None,
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
        job_id: Parent ingestion job ID for metrics and counters
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
        if status_updates_total:
            status_updates_total.labels("file", status or "unknown").inc()
        if job_id:
            record_ingest_file_update(job_id)
        
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
                    .maybe_single()\
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
            user_response = supabase.table("user_profiles").select(
                "display_name,full_name,email"
            ).eq("user_id", user_id).single().execute()
            user_data = user_response.data
            if not isinstance(user_data, dict):
                legacy_response = supabase.table("profiles").select(
                    "display_name,full_name,email"
                ).eq("user_id", user_id).single().execute()
                user_data = legacy_response.data
            if hasattr(user_data, "data") and isinstance(user_data.data, dict):
                user_data = user_data.data
            if not isinstance(user_data, dict):
                logger.warning(f"📧 [Email] No profile found for user {user_id}")
                return
            name = user_data.get("display_name") or user_data.get("full_name") or "there"
        except Exception:
            logger.warning(f"📧 [Email] Failed to fetch profile for user {user_id}")
            return
            
        # Fetch email from Auth Admin (requires Service Role key)
        email = None
        if isinstance(user_data, dict) and "email" in user_data:
            email = user_data.get("email")
            if not email:
                logger.warning(f"📧 [Email] No email in profile for user {user_id}")
                return
        else:
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
            user_response = supabase.table("user_profiles").select("display_name,full_name").eq("user_id", user_id).single().execute()
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


def _sanitize_text(value: str) -> str:
    if not value:
        return value
    if "\x00" in value:
        return value.replace("\x00", "")
    return value


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
        update_file_status(supabase, file_status_id, job_id, status="parsing", progress=25, message="Extracting content...")
        
        # Handle both bytes and string content
        if isinstance(content, str):
            content_bytes = content.encode('utf-8')
        else:
            content_bytes = content

        if len(content_bytes) > settings.MAX_FILE_SIZE:
            if parser_rejections:
                parser_rejections.labels("file_too_large", source_type or "unknown").inc()
            update_file_status(supabase, file_status_id, job_id, status="failed",
                progress=0,
                message=f"File exceeds {settings.MAX_FILE_SIZE // (1024 * 1024)}MB limit",
                error="File too large",
            )
            return ProcessResult(success=False, error="File too large")

        content_hash = compute_content_hash(content_bytes)
        parse_timeout = get_parse_timeout_seconds(filename, metadata.get("mime_type") if metadata else None)
        parse_start = time.time()

        # Process through document factory
        result = DocumentProcessorFactory.process(
            content=content_bytes,
            filename=filename,
            mime_type=metadata.get('mime_type') if metadata else None
        )

        parse_elapsed = time.time() - parse_start
        if parse_timeout and parse_elapsed > parse_timeout:
            if timeout_total:
                timeout_total.labels("parse").inc()
            if parser_rejections:
                parser_rejections.labels("parse_timeout", source_type or "unknown").inc()
            update_file_status(supabase, file_status_id, job_id, status="failed",
                progress=0,
                message=f"Parsing exceeded {parse_timeout}s (took {int(parse_elapsed)}s)",
                error="Parsing timeout",
            )
            return ProcessResult(success=False, error="Parsing timeout")

        if result.file_type == "unsupported":
            reason = (result.metadata or {}).get("unsupported_reason")
            message = "Unsupported file type"
            if reason == "binary_content":
                message = "Unsupported binary file"
            if parser_rejections:
                parser_rejections.labels("unsupported", source_type or "unknown").inc()
            update_file_status(supabase, file_status_id, job_id, status="skipped",
                progress=100,
                message=message,
                chunks_total=0,
                chunks_processed=0
            )
            return ProcessResult(success=True, chunks_count=0)
        
        if not result.chunks:
            if parser_rejections:
                parser_rejections.labels("empty", source_type or "unknown").inc()
            update_file_status(supabase, file_status_id, job_id, status="skipped", progress=100, message="No content found")
            return ProcessResult(success=True, chunks_count=0)
        
        update_file_status(supabase, file_status_id, job_id, progress=40, message=f"Parsed {len(result.chunks)} chunks",
            chunks_total=len(result.chunks))
        
        # 2. Generate embeddings
        update_file_status(supabase, file_status_id, job_id, status="embedding", progress=50, message="Generating embeddings...")
        
        chunk_texts = [_sanitize_text(chunk.content) for chunk in result.chunks]
        token_counts = [chunk.token_count for chunk in result.chunks]
        chunk_embeddings = generate_embeddings_batch_sync(chunk_texts, token_counts=token_counts)
        
        update_file_status(supabase, file_status_id, job_id, progress=70, message="Embeddings complete")
        
        # 3. Build chunks payload
        chunks_payload = []
        for chunk, embedding, chunk_text in zip(result.chunks, chunk_embeddings, chunk_texts):
            if embedding is None:
                continue
            chunks_payload.append({
                "content": chunk_text,
                "embedding": embedding,
                "chunk_index": chunk.chunk_index,
                "metadata": {
                    **chunk.metadata,
                    "token_count": chunk.token_count,
                }
            })
        
        # 4. Index in database
        update_file_status(supabase, file_status_id, job_id, status="indexing", progress=80, message="Saving to database...")
        
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
            file_status_id=file_status_id,
            content_hash=content_hash
        )
        
        # 5. Complete
        if doc_id:
            update_file_status(supabase, file_status_id, job_id, status="completed", progress=100, message="Complete",
                chunks_processed=len(chunks_payload), document_id=doc_id)
            
            return ProcessResult(
                success=True,
                document_id=doc_id,
                chunks_count=len(chunks_payload)
            )
        else:
            update_file_status(supabase, file_status_id, job_id, status="failed", progress=0, error="Failed to save document")
            return ProcessResult(success=False, error="Database insert failed")
            
    except Exception as e:
        update_file_status(supabase, file_status_id, job_id, status="failed", progress=0, error=str(e))
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


def _collect_documents_sync(connector, item_ids, credentials, user_id):
    fetch_sync = getattr(connector, "fetch_documents_sync", None)
    if not fetch_sync:
        raise RuntimeError("Connector does not support synchronous fetch (fetch_documents_sync)")

    if inspect.iscoroutinefunction(fetch_sync):
        raise RuntimeError("fetch_documents_sync must be synchronous for worker pipelines")

    documents_iter = fetch_sync(item_ids, credentials, user_id=user_id)
    if inspect.isawaitable(documents_iter) or inspect.isasyncgen(documents_iter):
        raise RuntimeError("fetch_documents_sync returned async results; use a sync connector implementation")

    return list(documents_iter)



@celery_app.task(
    bind=True,
    name="unified_ingest_task",
    on_failure=handle_task_failure,
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
    acks_late=True,
    ignore_result=True
)
def unified_ingest_task(
    self,
    user_id: str,
    job_id: str,
    connector_type: str,
    item_ids: Optional[List[str]] = None,
    credentials: Dict[str, Any] = None,
    item_id: Optional[str] = None,
    plan_code: Optional[str] = None,
):
    """
    UNIFIED ingestion task for ALL data sources.
    
    Now uses FAN-OUT PATTERN for true parallel processing:
    1. Fetch all files from connector
    2. Create file status records
    3. Dispatch parallel process_file_task for each file
    4. Redis counters trigger finalize when all files complete
    
    Args:
        user_id: User ID
        job_id: Job ID for tracking
        connector_type: 'file_upload', 'google_drive', 'notion', 'web', etc.
        item_ids: List of items to ingest (paths, IDs, URLs)
        credentials: Optional auth credentials
    """
    import base64
    from celery import group
    
    task_id = self.request.id
    raw_connector_type = connector_type
    connector_type = normalize_provider(connector_type)
    if not connector_type:
        raise ValueError("connector_type is required")

    if item_ids is None:
        item_ids = [item_id] if item_id else []
    elif not isinstance(item_ids, list):
        item_ids = [item_ids]

    logger.info(f"[UnifiedIngest:{task_id}] Starting FAN-OUT: {connector_type}, Job: {job_id}, Plan: {plan_code or 'starter'}")
    
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

        if raw_connector_type and raw_connector_type != connector_type:
            try:
                supabase.table("ingestion_jobs").update({
                    "provider": connector_type
                }).eq("id", job_id).execute()
            except Exception as e:
                logger.warning(f"[UnifiedIngest:{task_id}] ⚠️ Failed to normalize provider: {e}")
        
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
        
        with connector_fetch_limit(connector_type):
            documents = _collect_documents_sync(connector, item_ids, credentials, user_id)
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
                "file_size_bytes": doc.size_bytes or 0,  # FIXED: was "file_size"
                "status": "pending",
                "progress": 0,
                "status_message": "Queued for processing..."  # FIXED: was "message"
            }).execute()
            
            file_status_id = file_status_result.data[0]["id"]
            
            # Serialize document content to base64 for Celery
            content = doc.content
            if isinstance(content, bytes):
                content_b64 = base64.b64encode(content).decode("utf-8")
            elif isinstance(content, str):
                mime_type = (doc.mime_type or "").lower()
                is_text = mime_type.startswith("text/") or mime_type in {
                    "application/json",
                    "application/xml",
                    "application/xhtml+xml",
                    "application/x-yaml",
                }
                if is_text:
                    content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
                else:
                    # Binary connectors (e.g., Drive) may already return base64 strings.
                    try:
                        base64.b64decode(content, validate=True)
                        content_b64 = content
                    except Exception:
                        content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
            else:
                raise ValueError(f"Unsupported document content type: {type(content)}")
            
            doc_metadata = doc.metadata or {}
            storage_path = doc_metadata.get("storage_path")
            source_url = doc_metadata.get("source_url") or doc_metadata.get("url")
            doc_source_type = doc.source_type.value if hasattr(doc.source_type, "value") else str(doc.source_type)
            size_bytes = doc.size_bytes or doc_metadata.get("file_size") or doc_metadata.get("size") or 0

            file_data = {
                "filename": doc.filename,
                "content_b64": content_b64,
                "size_bytes": size_bytes,
                "mime_type": doc.mime_type,
                "storage_path": storage_path,
                "source_id": doc.source_id,
                "parent_id": doc.parent_id,
                "source_url": source_url,
                "source_type": doc_source_type,
                "metadata": doc_metadata,
            }
            
            # Create task signature
            file_tasks.append(
                process_file_task.s(
                    user_id=user_id,
                    job_id=job_id,
                    file_data=file_data,
                    file_status_id=file_status_id,
                    connector_type=connector_type,
                    plan_code=plan_code,
                )
            )
        
        logger.info(f"[UnifiedIngest:{task_id}] Dispatching {len(file_tasks)} parallel tasks...")
        
        # Update job status
        supabase.table("ingestion_jobs").update({
            "progress": 10,
            "message": f"Processing {total_files} files in parallel...",
            "status_message": f"Processing {total_files} files in parallel..."
        }).eq("id", job_id).execute()
        
        counters_ready = init_ingest_job_counters(job_id, total_files)
        if not counters_ready:
            logger.warning(f"[UnifiedIngest:{task_id}] ⚠️ Redis counters unavailable; relying on reconciliation")
        
        # STEP 3: Dispatch all tasks in parallel using a group
        result = group(file_tasks).apply_async()
        
        logger.info(f"[UnifiedIngest:{task_id}] ✅ Dispatched group with {total_files} tasks, group_id: {result.id}")
        
        return {
            "status": "dispatched",
            "job_id": job_id,
            "total_files": total_files,
            "group_id": result.id
        }
        
    except Exception as e:
        logger.error(f"[UnifiedIngest:{task_id}] Failed: {e}")
        update_job_status(
            supabase,
            job_id,
            "failed",
            error_message=str(e),
            message=str(e),
            progress=0,
        )
        
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
    time_limit=660,  # Hard kill at 11 min
    ignore_result=True,
    queue="queues.parsing",
)
def process_file_task(
    self,
    user_id: str,
    job_id: str,
    file_data: Dict[str, Any],
    file_status_id: str,
    connector_type: str,
    plan_code: Optional[str] = None,
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
    import base64
    import tempfile
    import os
    from services.parsers import DocumentProcessorFactory
    from services.embeddings import generate_embeddings_batch_sync
    
    task_id = self.request.id
    filename = file_data.get("filename", "unknown")
    logger.info(f"[ProcessFile:{task_id}] Starting: {filename} (job: {job_id})")
    
    supabase = get_supabase()
    source_type = normalize_source_type(file_data.get("source_type") or connector_type) or (connector_type or "unknown")
    metadata = file_data.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    source_url = file_data.get("source_url") or metadata.get("source_url") or metadata.get("url")
    source_id = file_data.get("source_id") or metadata.get("source_id") or metadata.get("file_id")
    parent_id = file_data.get("parent_id") or metadata.get("parent_id")
    mime_type = file_data.get("mime_type") or metadata.get("mime_type")
    local_path = None
    start_time = time.time()
    
    try:
        update_file_status(supabase, file_status_id, job_id, status="uploading",
            progress=10,
            message="Preparing file..."
        )
        
        # STEP 1: Download from storage (preferred) or decode base64 payload
        storage_path = file_data.get("storage_path")
        content_b64 = file_data.get("content_b64")
        content = None

        if storage_path:
            content = supabase.storage.from_(STAGING_BUCKET).download(storage_path)
        elif content_b64:
            content = base64.b64decode(content_b64)
        else:
            raise ValueError("No content provided")

        if isinstance(content, str):
            content = content.encode("utf-8")

        # Security: malware scan (stub)
        scan_result = scan_content(content)
        if not scan_result.get("safe"):
            reason = scan_result.get("reason") or "Security Violation: Malware Detected"
            logger.critical(f"[ProcessFile:{task_id}] 🚫 Malware detected in {filename}: {reason}")
            update_file_status(
                supabase,
                file_status_id,
                job_id,
                status="failed",
                progress=0,
                message="Security Violation: Malware Detected",
                error=reason,
            )
            _record_ingest_outcome_and_maybe_finalize(
                supabase,
                user_id,
                job_id,
                file_status_id,
                "failed",
            )
            audit_logger.log_sync(
                user_id=user_id,
                action="ingest.reject.malware",
                resource_type="ingestion_job",
                resource_id=job_id,
                details={"filename": filename, "reason": reason},
            )
            return {"status": "failed", "filename": filename, "error": "Malware detected"}

        if len(content) > settings.MAX_FILE_SIZE:
            if parser_rejections:
                parser_rejections.labels("file_too_large", source_type or "unknown").inc()
            update_file_status(supabase, file_status_id, job_id, status="failed",
                progress=0,
                message=f"File exceeds {settings.MAX_FILE_SIZE // (1024 * 1024)}MB limit",
                error="File too large",
            )
            _record_ingest_outcome_and_maybe_finalize(
                supabase,
                user_id,
                job_id,
                file_status_id,
                "failed",
            )
            return {"status": "failed", "filename": filename, "error": "File too large"}

        content_hash = compute_content_hash(content)
        
        suffix = os.path.splitext(filename)[1] or ".bin"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            local_path = tmp.name
        
        # STEP 2: Parse document
        update_file_status(supabase, file_status_id, job_id, status="parsing",
            progress=30,
            message="Extracting content (may take 30-90s for PDFs)..."
        )
        
        parse_timeout = get_parse_timeout_seconds(filename, mime_type)
        parse_start = time.time()
        result = DocumentProcessorFactory.process(
            file_path=local_path,
            filename=filename,
            mime_type=mime_type
        )
        parse_elapsed = time.time() - parse_start
        if parse_timeout and parse_elapsed > parse_timeout:
            if timeout_total:
                timeout_total.labels("parse").inc()
            if parser_rejections:
                parser_rejections.labels("parse_timeout", source_type or "unknown").inc()
            update_file_status(supabase, file_status_id, job_id, status="failed",
                progress=0,
                message=f"Parsing exceeded {parse_timeout}s (took {int(parse_elapsed)}s)",
                error="Parsing timeout",
            )
            _record_ingest_outcome_and_maybe_finalize(
                supabase,
                user_id,
                job_id,
                file_status_id,
                "failed",
            )
            return {"status": "failed", "filename": filename, "error": "Parsing timeout"}

        if result.file_type == "unsupported":
            reason = (result.metadata or {}).get("unsupported_reason")
            message = "Unsupported file type"
            if reason == "binary_content":
                message = "Unsupported binary file"
            if parser_rejections:
                parser_rejections.labels("unsupported", source_type or "unknown").inc()
            update_file_status(supabase, file_status_id, job_id, status="skipped",
                progress=100,
                message=message,
                chunks_total=0,
                chunks_processed=0
            )
            _record_ingest_outcome_and_maybe_finalize(
                supabase,
                user_id,
                job_id,
                file_status_id,
                "skipped",
            )
            return {"status": "skipped", "filename": filename, "reason": reason or "unsupported"}
        chunks = result.chunks
        
        if not chunks:
            skip_message = "No content extracted"
            if result.file_type == "pdf":
                skip_message = "No text extracted (OCR required)"
            if parser_rejections:
                parser_rejections.labels("empty", source_type or "unknown").inc()
            update_file_status(supabase, file_status_id, job_id, status="skipped",
                progress=100,
                message=skip_message,
                chunks_total=0,
                chunks_processed=0
            )
            _record_ingest_outcome_and_maybe_finalize(
                supabase,
                user_id,
                job_id,
                file_status_id,
                "skipped",
            )
            return {"status": "skipped", "filename": filename, "reason": "empty"}
        
        # STEP 3: Dispatch embeddings task (queue isolation)
        update_file_status(
            supabase,
            file_status_id,
            job_id,
            status="embedding",
            progress=60,
            message=f"Queueing embeddings for {len(chunks)} chunks...",
            chunks_total=len(chunks),
            chunks_processed=0,
        )

        chunk_payload = []
        for chunk in chunks:
            chunk_payload.append(
                {
                    "content": _sanitize_text(chunk.content),
                    "chunk_index": chunk.chunk_index,
                    "token_count": chunk.token_count,
                    "metadata": chunk.metadata or {},
                }
            )

        doc_payload = {
            "user_id": user_id,
            "title": filename,
            "source_type": source_type,
            "source_url": source_url,
            "file_size_bytes": file_data.get("size_bytes") or metadata.get("file_size") or metadata.get("size") or len(content),
            "content_hash": content_hash,
            "metadata": {
                **metadata,
                "job_id": job_id,
                "mime_type": mime_type or "application/octet-stream",
                "source_id": source_id,
                "source_url": source_url,
                "parent_id": parent_id,
                "file_type": result.file_type,
                "total_tokens": result.total_tokens,
                "total_chunks": len(chunks),
            },
            "job_id": job_id,
            "file_status_id": file_status_id,
            "connector_type": connector_type,
            "filename": filename,
            "plan_code": plan_code,
        }

        generate_embeddings_task.apply_async(
            args=[chunk_payload, doc_payload, plan_code],
            queue="queues.embedding",
        )

        logger.info(
            f"[ProcessFile:{task_id}] ✅ Dispatched embedding task for {filename} (job: {job_id}, plan={plan_code or 'starter'})"
        )
        return {"status": "queued_embedding", "filename": filename}
        
    except Exception as e:
        logger.error(f"[ProcessFile:{task_id}] ❌ {filename}: {e}")
        
        update_file_status(supabase, file_status_id, job_id, status="failed",
            progress=0,
            message=str(e)[:500],
            error=str(e)[:1000]
        )
        
        _record_ingest_outcome_and_maybe_finalize(
            supabase,
            user_id,
            job_id,
            file_status_id,
            "failed",
        )
        audit_logger.log_sync(
            user_id=user_id,
            action="ingest.failed",
            resource_type="ingestion_job",
            resource_id=job_id,
            details={"filename": filename, "error": str(e)},
        )
        
        return {
            "status": "failed",
            "filename": filename,
            "error": str(e)
        }
        
    finally:
        if source_type == "file_upload":
            storage_path = file_data.get("storage_path")
            if storage_path:
                try:
                    supabase.storage.from_(STAGING_BUCKET).remove([storage_path])
                    logger.info(f"[ProcessFile:{task_id}] 🧹 Removed staged upload: {storage_path}")
                except Exception as e:
                    logger.warning(f"[ProcessFile:{task_id}] ⚠️ Failed to remove staged upload: {e}")

        # Cleanup temp file
        if local_path and os.path.exists(local_path):
            try:
                os.unlink(local_path)
            except:
                pass


@celery_app.task(
    bind=True,
    queue="queues.embedding",
    ignore_result=True,
)
def generate_embeddings_task(self, chunk_payload: list, doc_payload: dict, plan_code: Optional[str] = None):
    """
    Generate embeddings for parsed chunks on the embedding queue, then dispatch indexing.
    """
    task_id = self.request.id
    supabase = get_supabase()
    job_id = doc_payload.get("job_id")
    file_status_id = doc_payload.get("file_status_id")
    user_id = doc_payload.get("user_id")
    filename = doc_payload.get("filename", "unknown")
    plan_label = plan_code or doc_payload.get("plan_code") or settings.PLAN_STARTER

    try:
        update_file_status(
            supabase,
            file_status_id,
            job_id,
            status="embedding",
            progress=65,
            message=f"Embedding {len(chunk_payload)} chunks...",
            chunks_total=len(chunk_payload),
            chunks_processed=0,
        )

        texts = [c.get("content") or "" for c in chunk_payload]
        token_counts = [c.get("token_count") for c in chunk_payload]

        embeddings = generate_embeddings_batch_sync(
            texts,
            token_counts=token_counts,
            plan_code=plan_label,
        )

        enriched_chunks = []
        for chunk, embedding in zip(chunk_payload, embeddings):
            if embedding is None:
                continue
            enriched = {
                "content": chunk.get("content") or "",
                "embedding": embedding,
                "chunk_index": chunk.get("chunk_index", 0),
                "token_count": chunk.get("token_count"),
            }
            enriched_chunks.append(enriched)

        if not enriched_chunks:
            raise ValueError("No embeddings generated")

        index_chunks_task.apply_async(
            args=[enriched_chunks, doc_payload],
            queue="queues.indexing",
        )
        logger.info(
            f"[EmbedTask:{task_id}] ✅ Dispatched indexing for {filename} (job: {job_id}, plan={plan_label})"
        )

    except Exception as exc:
        logger.error(f"[EmbedTask:{task_id}] ❌ {filename}: {exc}")
        update_file_status(
            supabase,
            file_status_id,
            job_id,
            status="failed",
            progress=0,
            message=str(exc)[:300],
            error=str(exc)[:500],
        )
        _record_ingest_outcome_and_maybe_finalize(
            supabase,
            user_id,
            job_id,
            file_status_id,
            "failed",
        )


@celery_app.task(
    bind=True,
    queue="queues.indexing",
    ignore_result=True,
)
def index_chunks_task(self, chunk_payload: list, doc_payload: dict):
    """
    Persist document and chunk embeddings on the indexing queue.
    """
    task_id = self.request.id
    supabase = get_supabase()
    user_id = doc_payload.get("user_id")
    job_id = doc_payload.get("job_id")
    file_status_id = doc_payload.get("file_status_id")
    filename = doc_payload.get("filename", "unknown")

    try:
        update_file_status(
            supabase,
            file_status_id,
            job_id,
            status="indexing",
            progress=85,
            message="Storing in database...",
            chunks_total=len(chunk_payload),
            chunks_processed=0,
        )

        chunk_records = []
        for chunk in chunk_payload:
            embedding = chunk.get("embedding")
            if embedding is None:
                continue
            chunk_records.append(
                {
                    "content": chunk.get("content") or "",
                    "embedding": embedding,
                    "chunk_index": chunk.get("chunk_index", 0),
                    "metadata": {"token_count": chunk.get("token_count")},
                }
            )

        if not chunk_records:
            raise ValueError("No embeddings generated")

        doc_id = ingest_document_batched(
            supabase=supabase,
            user_id=user_id,
            doc_title=doc_payload.get("title") or filename,
            source_type=doc_payload.get("source_type") or "unknown",
            metadata=doc_payload.get("metadata") or {},
            chunks_payload=chunk_records,
            file_size_bytes=doc_payload.get("file_size_bytes") or 0,
            job_id=job_id,
            source_url=doc_payload.get("source_url"),
            file_status_id=file_status_id,
            content_hash=doc_payload.get("content_hash"),
        )

        total_chunks = len(chunk_records)
        update_file_status(
            supabase,
            file_status_id,
            job_id,
            status="completed",
            progress=100,
            message="✅ Completed",
            chunks_total=total_chunks,
            chunks_processed=total_chunks,
            document_id=doc_id,
        )

        _record_ingest_outcome_and_maybe_finalize(
            supabase,
            user_id,
            job_id,
            file_status_id,
            "success",
        )
        logger.info(f"[IndexTask:{task_id}] ✅ Stored {total_chunks} chunks for {filename} (doc={doc_id})")

    except Exception as exc:
        logger.error(f"[IndexTask:{task_id}] ❌ {filename}: {exc}")
        update_file_status(
            supabase,
            file_status_id,
            job_id,
            status="failed",
            progress=0,
            message=str(exc)[:300],
            error=str(exc)[:500],
        )
        _record_ingest_outcome_and_maybe_finalize(
            supabase,
            user_id,
            job_id,
            file_status_id,
            "failed",
        )


@celery_app.task(
    bind=True,
    name="finalize_job_task",
    ignore_result=True
)
def finalize_job_task(self, user_id: str, job_id: str):
    """
    Finalize an ingestion job based on Redis counters or DB reconciliation.
    """
    task_id = self.request.id
    logger.info(f"[FinalizeJob:{task_id}] Finalizing job {job_id}")

    supabase = get_supabase()

    job_res = supabase.table("ingestion_jobs").select("status,total_files").eq("id", job_id).single().execute()
    if not job_res.data:
        logger.warning(f"[FinalizeJob:{task_id}] Job {job_id} not found")
        return

    current_status = job_res.data.get("status")
    if current_status in {"completed", "failed", "cancelled"}:
        logger.info(f"[FinalizeJob:{task_id}] Job {job_id} already {current_status}")
        return

    total_files = job_res.data.get("total_files") or 0
    counters = get_ingest_job_counters(job_id)
    counts_source = "redis"

    if counters:
        counts = counters
        if not total_files:
            total_files = counters.get("total", 0)

        db_counts = _get_ingestion_counts_from_db(supabase, job_id)
        if db_counts.get("processed", 0) and db_counts["processed"] != counters.get("processed", 0):
            counts = db_counts
            counts_source = "db"
            if job_counters_reconciled:
                job_counters_reconciled.labels("ingest").inc()
    else:
        if job_counters_missing:
            job_counters_missing.labels("ingest").inc()
        counts = _get_ingestion_counts_from_db(supabase, job_id)
        counts_source = "db"
        if job_counters_reconciled:
            job_counters_reconciled.labels("ingest").inc()

    success_count = counts.get("success", 0)
    failed_count = counts.get("failed", 0)
    skipped_count = counts.get("skipped", 0)
    processed_total = success_count + failed_count + skipped_count
    job_updates = counts.get("job_status_updates", 0)
    file_updates = counts.get("file_status_updates", 0)

    if job_updates or file_updates:
        logger.info(
            f"[FinalizeJob:{task_id}] Job {job_id} status updates: "
            f"job={job_updates} file={file_updates} source={counts_source}"
        )

    if total_files <= 0:
        total_files = processed_total

    if total_files > 0 and processed_total < total_files:
        logger.info(
            f"[FinalizeJob:{task_id}] Job {job_id} not complete ({processed_total}/{total_files})"
        )
        return

    if failed_count == 0:
        final_status = "completed"
    elif (success_count + skipped_count) > 0:
        final_status = "completed"
    else:
        final_status = "failed"

    if final_status == "failed":
        status_msg = f"All {failed_count} files failed"
    else:
        status_parts = [f"Processed {processed_total}/{total_files} files"]
        if skipped_count:
            status_parts.append(f"{skipped_count} skipped")
        if failed_count:
            status_parts.append(f"{failed_count} failed")
        status_msg = ", ".join(status_parts)

    supabase.table("ingestion_jobs").update({
        "status": final_status,
        "progress": 100,
        "message": status_msg,
        "status_message": status_msg,
        "processed_files": processed_total,
        "failed_files": failed_count,
        "total_files": total_files,
        "error_message": status_msg if final_status == "failed" else None,
    }).eq("id", job_id).execute()

    if job_counters_finalize:
        job_counters_finalize.labels("ingest", counts_source).inc()

    clear_ingest_job_counters(job_id)

    notification_type = "error" if final_status == "failed" else "warning" if failed_count > 0 else "success"
    create_notification(
        supabase, user_id,
        "Ingestion Complete" if final_status != "failed" else "Ingestion Failed",
        status_msg,
        notification_type,
        {
            "job_id": job_id,
            "successful": success_count,
            "failed": failed_count,
            "skipped": skipped_count,
        }
    )

    if success_count > 0:
        send_email_notification(supabase, user_id, success_count)

    logger.info(f"[FinalizeJob:{task_id}] ✅ Job {job_id}: {status_msg}")


# ============================================================
# LEGACY FILE INGESTION TASK (TO BE DEPRECATED)
# ============================================================

# ============================================================
# DISTRIBUTED CRAWLER: Master-Worker Pattern
# ============================================================

def update_crawl_status(
    supabase,
    crawl_id: str,
    *,
    status: Optional[str] = None,
    total_pages: Optional[int] = None,
    pages_ingested: Optional[int] = None,
    pages_failed: Optional[int] = None,
    error_message: Optional[str] = None,
    job_id: Optional[str] = None,
    message: Optional[str] = None,
) -> None:
    """Update crawl progress in web_crawl_configs with safe defaults."""
    try:
        update_data: Dict[str, Any] = {
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        if status is not None:
            update_data["status"] = status
            if status in {"completed", "failed", "cancelled"}:
                update_data["completed_at"] = datetime.now(timezone.utc).isoformat()
        if total_pages is not None:
            update_data["total_pages_found"] = total_pages
        if pages_ingested is not None:
            update_data["pages_ingested"] = pages_ingested
        if pages_failed is not None:
            update_data["pages_failed"] = pages_failed
        if error_message is not None:
            update_data["error_message"] = error_message
        if message is not None:
            update_data["status_message"] = message
        job_ref = job_id or crawl_id
        if job_ref:
            try:
                progress = None
                processed_total = None
                total = total_pages
                if total_pages is not None and total_pages >= 0:
                    total = total_pages
                if pages_ingested is not None or pages_failed is not None:
                    processed_total = (pages_ingested or 0) + (pages_failed or 0)
                    if total:
                        progress = min(100, int((processed_total / total) * 100)) if total > 0 else None
                if progress is None and status in {"completed", "failed", "cancelled"}:
                    progress = 100

                job_update: Dict[str, Any] = {
                    "updated_at": update_data["updated_at"],
                }
                if status:
                    job_update["status"] = status if status != "processing" else "processing"
                if total is not None:
                    job_update["total_files"] = total
                if processed_total is not None:
                    job_update["processed_files"] = processed_total
                if pages_failed is not None:
                    job_update["failed_files"] = pages_failed
                if progress is not None:
                    job_update["progress"] = progress
                if message:
                    job_update["message"] = message
                    job_update["status_message"] = message
                if error_message:
                    job_update["error_message"] = error_message

                if len(job_update) > 1:  # more than updated_at
                    supabase.table("ingestion_jobs").update(job_update).eq("id", job_ref).execute()
            except Exception as job_err:
                logger.debug(f"⚠️ [Crawl] Failed to mirror status to ingestion_jobs: {job_err}")

        supabase.table("web_crawl_configs").update(update_data).eq("id", crawl_id).execute()
        if status_updates_total:
            status_updates_total.labels("crawl", status or "update").inc()
        record_crawl_job_update(crawl_id)
    except Exception as e:
        logger.warning(f"⚠️ [Crawl] Failed to update status for {crawl_id}: {e}")


@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    max_retries=2,
    ignore_result=True,
    queue="queues.parsing",
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
    individual page processing tasks using Redis counters + group.
    """
    from celery import group
    from collections import deque
    import time
    import random
    from urllib.parse import urlparse
    
    task_id = self.request.id
    crawl_id = crawl_config.get("crawl_id")
    job_id = crawl_config.get("job_id") or crawl_id
    crawl_type = crawl_config.get("crawl_type", "single")
    max_depth = min(int(crawl_config.get("max_depth", 1)), 10)
    max_pages = min(int(crawl_config.get("max_pages", 500)), 10000)
    max_pages = max(1, max_pages)
    respect_robots = bool(crawl_config.get("respect_robots", True))
    allow_subdomains = bool(crawl_config.get("allow_subdomains", False))
    is_recrawl = bool(crawl_config.get("is_recrawl", False))
    
    logger.info(f"🕸️ [Discovery:{task_id}] Starting crawl for user {user_id}")
    logger.info(f"🕸️ [Discovery:{task_id}] URL: {root_url}, Type: {crawl_type}, Depth: {max_depth}, Max: {max_pages}")
    
    supabase = get_supabase()
    
    try:
        # Import connector
        from connectors.web import WebConnector
        connector = WebConnector()
        
        normalized_root = connector.normalize_url(root_url)
        if not normalized_root:
            raise ValueError("Invalid URL provided for crawl")
        if not connector.is_safe_url(normalized_root):
            raise ValueError("URL is not allowed for crawling")
        root_url = normalized_root
        
        # Update status
        if crawl_id:
            update_crawl_status(
                supabase,
                crawl_id,
                status="discovering",
                job_id=job_id,
                message="Discovering pages..."
            )
        if job_id:
            try:
                update_job_status(
                    supabase,
                    job_id,
                    status="processing",
                    progress=5,
                    message="Discovering pages..."
                )
            except Exception:
                pass
        
        create_notification(
            supabase, user_id,
            "Web Crawl Started",
            f"Discovering pages from {root_url}",
            "info",
            {"crawl_id": crawl_id, "crawl_type": crawl_type}
        )
        
        # ===== DISCOVERY PHASE =====
        urls_to_process: List[str] = []
        parsed_root = urlparse(root_url)
        base_domain = parsed_root.hostname or ""
        
        if crawl_type == "sitemap":
            logger.info(f"🗺️ [Discovery] Parsing sitemap: {root_url}")
            sitemap_urls = connector.parse_sitemap(root_url)
            seen = set()
            for url in sitemap_urls:
                normalized = connector.normalize_url(url)
                if not normalized:
                    continue
                if normalized in seen:
                    continue
                if connector.is_allowed_domain(urlparse(normalized).hostname or "", base_domain, allow_subdomains):
                    seen.add(normalized)
                    urls_to_process.append(normalized)
                if len(urls_to_process) >= max_pages:
                    break
            
        elif crawl_type == "recursive":
            logger.info(f"🔄 [Discovery] Recursive crawl from: {root_url}")
            queue = deque([(root_url, 0)])
            seen = {root_url}
            
            while queue and len(urls_to_process) < max_pages:
                url, depth = queue.popleft()
                urls_to_process.append(url)
                
                if depth < max_depth:
                    html = connector.fetch_html(url)
                    if html:
                        links = connector.extract_links(
                            html,
                            url,
                            base_domain=base_domain,
                            allow_subdomains=allow_subdomains
                        )
                        for link in links:
                            if link not in seen:
                                seen.add(link)
                                queue.append((link, depth + 1))
                    
                    # Rate limit during discovery
                    time.sleep(random.uniform(0.3, 0.6))
        else:
            urls_to_process = [root_url]
        
        if respect_robots:
            urls_to_process = [
                url for url in urls_to_process
                if connector.check_robots_txt(url, connector.USER_AGENT)
            ]
        
        total_pages = len(urls_to_process)
        logger.info(f"📊 [Discovery] Discovered {total_pages} URLs after filtering")
        
        if crawl_id:
            update_crawl_status(
                supabase,
                crawl_id,
                status="processing",
                total_pages=total_pages,
                job_id=job_id,
                message="Preparing pages for crawling..."
            )
        
        if total_pages == 0:
            if crawl_id:
                update_crawl_status(supabase, crawl_id, status="completed", total_pages=0, job_id=job_id)
            return {"status": "completed", "message": "No pages found"}
        
        # ===== DEDUP AGAINST EXISTING =====
        if not is_recrawl:
            existing_urls = set()
            try:
                batch_size = 1000
                for i in range(0, len(urls_to_process), batch_size):
                    batch = urls_to_process[i:i + batch_size]
                    existing_res = supabase.table("documents").select("source_url").eq(
                        "user_id", user_id
                    ).in_(
                        "source_url", batch
                    ).execute()
                    for row in existing_res.data or []:
                        src = row.get("source_url")
                        normalized = connector.normalize_url(src) if src else None
                        if normalized:
                            existing_urls.add(normalized)
                        elif src:
                            existing_urls.add(src)
            except Exception as e:
                logger.warning(f"⚠️ [Discovery] Dedup query failed: {e}")
            
            if existing_urls:
                urls_to_process = [url for url in urls_to_process if url not in existing_urls]
                logger.info(f"📊 [Discovery] After dedup: {len(urls_to_process)} new URLs")
        
        if not urls_to_process:
            if crawl_id:
                update_crawl_status(supabase, crawl_id, status="completed", total_pages=0, job_id=job_id)
            return {"status": "completed", "message": "No new URLs to crawl"}
        
        if crawl_id:
            update_crawl_status(
                supabase,
                crawl_id,
                status="processing",
                total_pages=len(urls_to_process),
                job_id=job_id,
                message=f"Processing {len(urls_to_process)} pages..."
            )
        
        # ===== DISPATCH PHASE: Parallel processing =====
        if job_id:
            counters_ready = init_ingest_job_counters(job_id, len(urls_to_process))
            if not counters_ready:
                logger.warning(f"🕸️ [Discovery:{task_id}] ⚠️ Redis counters unavailable for ingestion job")
            try:
                supabase.table("ingestion_file_status").delete().eq("job_id", job_id).execute()
            except Exception as cleanup_err:
                logger.debug(f"⚠️ [Discovery:{task_id}] Failed to reset file statuses for job {job_id}: {cleanup_err}")

        if crawl_id:
            counters_ready = init_crawl_counters(crawl_id, len(urls_to_process))
            if not counters_ready:
                logger.warning(f"🕸️ [Discovery:{task_id}] ⚠️ Redis counters unavailable; relying on reconciliation")

        file_status_ids: List[Optional[str]] = []
        if job_id:
            for url in urls_to_process:
                file_status_ids.append(create_file_status(
                    supabase,
                    job_id,
                    user_id,
                    filename=url,
                    file_size=0,
                ))
        else:
            file_status_ids = [None for _ in urls_to_process]

        page_tasks = group([
            process_page_task.s(
                user_id=user_id,
                url=url,
                crawl_id=crawl_id,
                respect_robots=respect_robots,
                job_id=job_id,
                file_status_id=file_status_ids[idx] if idx < len(file_status_ids) else None,
            ) for idx, url in enumerate(urls_to_process)
        ])
        
        result = page_tasks.apply_async()
        
        logger.info(f"🚀 [Discovery:{task_id}] Dispatched {len(urls_to_process)} page tasks")
        
        return {
            "status": "dispatched",
            "crawl_id": crawl_id,
            "total_pages": len(urls_to_process),
            "group_id": str(result.id)
        }
        
    except Exception as e:
        logger.error(f"❌ [Discovery:{task_id}] Failed: {e}")
        
        if crawl_id:
            update_crawl_status(
                supabase, crawl_id,
                status="failed",
                error_message=str(e),
                job_id=job_id,
                message=str(e)
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
    rate_limit="10/s",
    ignore_result=True,
    queue="queues.parsing",
)
def process_page_task(
    self,
    user_id: str,
    url: str,
    crawl_id: str = None,
    respect_robots: bool = True,
    job_id: str = None,
    file_status_id: str = None
):
    """
    Worker task for processing a single web page.
    
    Downloads, parses, embeds, and stores a single URL.
    Uses rate limiting to be polite to target servers.
    """
    import time
    import random
    
    task_id = self.request.id
    logger.info(f"📄 [Page:{task_id}] Processing: {url}")
    
    supabase = get_supabase()
    job_ref = job_id

    def mark_file_status(
        status: str,
        progress: int | None = None,
        message: str | None = None,
        error: str | None = None,
        chunks_total: int | None = None,
        chunks_processed: int | None = None,
        document_id: str | None = None,
    ) -> None:
        update_file_status(
            supabase,
            file_status_id,
            job_id=job_ref,
            status=status,
            progress=progress,
            message=message,
            error=error,
            chunks_total=chunks_total,
            chunks_processed=chunks_processed,
            document_id=document_id,
        )

    def record_ingest_outcome(outcome: str) -> None:
        if not job_ref or not file_status_id:
            return
        _record_ingest_outcome_and_maybe_finalize(
            supabase,
            user_id,
            job_ref,
            file_status_id,
            outcome,
        )
    
    try:
        from connectors.web import WebConnector
        from services.parsers import DocumentProcessorFactory
        
        connector = WebConnector()
        mark_file_status("uploading", progress=10, message="Fetching page...")
        if not connector.is_safe_url(url):
            logger.warning(f"⚠️ [Page:{task_id}] Unsafe URL blocked: {url}")
            if crawl_id:
                supabase.rpc("increment_crawl_counter", {
                    "p_crawl_id": crawl_id,
                    "p_field": "pages_failed"
                }).execute()
            _record_crawl_outcome_and_maybe_finalize(
                supabase,
                user_id,
                crawl_id,
                url,
                "failed",
                job_id=job_ref,
            )
            mark_file_status("failed", progress=0, message="URL blocked", error="unsafe_url")
            record_ingest_outcome("failed")
            return {"status": "failed", "url": url, "error": "unsafe_url"}
        
        # Rate limiting - wait if needed
        max_wait = 5
        waited = 0.0
        while not check_rate_limit(supabase, url) and waited < max_wait:
            time.sleep(0.5)
            waited += 0.5
        
        crawl_delay = connector.get_crawl_delay(url, connector.USER_AGENT) if respect_robots else None
        if crawl_delay:
            time.sleep(min(crawl_delay, 10.0) + random.uniform(0.1, 0.3))
        
        # Fetch and parse page
        docs = list(connector.fetch_documents_sync(
            [url],
            credentials=None,
            respect_robots=respect_robots,
        ))
        
        if not docs:
            logger.warning(f"⚠️ [Page:{task_id}] No content from: {url}")
            if crawl_id:
                supabase.rpc("increment_crawl_counter", {
                    "p_crawl_id": crawl_id,
                    "p_field": "pages_failed"
                }).execute()
            _record_crawl_outcome_and_maybe_finalize(
                supabase,
                user_id,
                crawl_id,
                url,
                "skipped",
                job_id=job_ref,
            )
            mark_file_status("failed", progress=0, message="No content retrieved", error="no_content")
            record_ingest_outcome("skipped")
            return {"status": "skipped", "url": url}
        
        doc = docs[0]
        page_content = doc.content
        if isinstance(page_content, bytes):
            page_content = page_content.decode("utf-8", errors="replace")
        page_metadata = doc.metadata or {}
        page_title = page_metadata.get("title", "Web Page")
        source_url = (
            page_metadata.get("source_url")
            or page_metadata.get("url")
            or getattr(doc, "source_id", None)
            or url
        )
        
        # Process using MarkdownProcessor (treats web content as markdown)
        result = DocumentProcessorFactory.process_web_content(page_content, source_url)
        mark_file_status("processing", progress=40, message="Parsing page content...")
        
        if not result.chunks:
            logger.warning(f"⚠️ [Page:{task_id}] No chunks generated from: {url}")
            if crawl_id:
                supabase.rpc("increment_crawl_counter", {
                    "p_crawl_id": crawl_id,
                    "p_field": "pages_failed"
                }).execute()
            _record_crawl_outcome_and_maybe_finalize(
                supabase,
                user_id,
                crawl_id,
                url,
                "skipped",
                job_id=job_ref,
            )
            mark_file_status("failed", progress=0, message="No extractable content", error="no_chunks")
            record_ingest_outcome("skipped")
            return {"status": "skipped", "url": url}
        
        # Embed
        from services.embeddings import generate_embeddings_batch_sync
        mark_file_status("embedding", progress=55, message=f"Embedding {len(result.chunks)} chunks...")
        
        chunk_texts = [_sanitize_text(chunk.content) for chunk in result.chunks]
        token_counts = [chunk.token_count for chunk in result.chunks]
        chunk_embeddings = generate_embeddings_batch_sync(chunk_texts, token_counts=token_counts)
        
        # Build chunks payload with enriched metadata
        chunks_payload = []
        failed_chunks = 0
        for chunk, embedding, chunk_text in zip(result.chunks, chunk_embeddings, chunk_texts):
            if embedding is None:
                failed_chunks += 1
                logger.warning(f"⚠️ [Page:{task_id}] Skipped chunk {chunk.chunk_index} for {url} due to failed embedding")
                continue
                
            chunks_payload.append({
                "content": chunk_text,
                "embedding": embedding,
                "chunk_index": chunk.chunk_index,
                "metadata": {
                    **chunk.metadata,
                    "token_count": chunk.token_count,
                }
            })
        
        if not chunks_payload:
            logger.warning(f"⚠️ [Page:{task_id}] No embeddings for: {url}")
            if crawl_id:
                supabase.rpc("increment_crawl_counter", {
                    "p_crawl_id": crawl_id,
                    "p_field": "pages_failed"
                }).execute()
            _record_crawl_outcome_and_maybe_finalize(
                supabase,
                user_id,
                crawl_id,
                url,
                "failed",
                job_id=job_ref,
            )
            mark_file_status("failed", progress=0, message="Embedding failed", error="no_embeddings")
            record_ingest_outcome("failed")
            return {"status": "failed", "url": url, "error": "no_embeddings"}
        
        # Document metadata
        doc_metadata = {
            **page_metadata,
            "file_type": "web",
            "crawl_id": crawl_id,
            "total_tokens": result.total_tokens,
            "total_chunks": len(result.chunks),
        }
        
        content_bytes = page_content.encode("utf-8")
        content_size = len(content_bytes)
        content_hash = compute_content_hash(content_bytes)
        org_scope = _resolve_org_scope(supabase, user_id)
        if _is_duplicate_document(supabase, content_hash, org_scope, user_id):
            # Treat as skipped/duplicate; do not parse/embed
            update_file_status(
                supabase,
                file_status_id,
                job_id,
                status="skipped",
                progress=100,
                message="Duplicate detected; reusing existing document",
            )
            _record_ingest_outcome_and_maybe_finalize(
                supabase,
                user_id,
                job_id,
                file_status_id,
                "skipped",
            )
            logger.info(f"[ProcessFile:{task_id}] ♻️ Duplicate file detected (hash={content_hash}); skipping processing")
            return {"status": "duplicate_skipped", "filename": filename}
        mark_file_status("indexing", progress=80, message="Saving to database...")

        doc_id = ingest_document_batched(
            supabase=supabase,
            user_id=user_id,
            doc_title=page_title,
            source_type="web",
            metadata=doc_metadata,
            chunks_payload=chunks_payload,
            file_size_bytes=content_size,
            source_url=source_url,
            content_hash=content_hash,
        )

        if not doc_id:
            logger.warning(f"⚠️ [Page:{task_id}] Failed to store: {url}")
            if crawl_id:
                supabase.rpc("increment_crawl_counter", {
                    "p_crawl_id": crawl_id,
                    "p_field": "pages_failed"
                }).execute()
            _record_crawl_outcome_and_maybe_finalize(
                supabase,
                user_id,
                crawl_id,
                url,
                "failed",
                job_id=job_ref,
            )
            mark_file_status("failed", progress=0, message="Database insert failed", error="db_insert_failed")
            record_ingest_outcome("failed")
            return {"status": "failed", "url": url, "error": "db_insert_failed"}
        
        logger.info(f"✅ [Page:{task_id}] Stored: {url} ({len(result.chunks)} chunks)")
        
        if crawl_id:
            try:
                supabase.rpc("increment_crawl_counter", {
                    "p_crawl_id": crawl_id,
                    "p_field": "pages_ingested"
                }).execute()
            except Exception:
                pass
        
        _record_crawl_outcome_and_maybe_finalize(
            supabase,
            user_id,
            crawl_id,
            url,
            "success",
            job_id=job_ref,
        )
        mark_file_status("completed", progress=100, message="Indexed", document_id=doc_id, chunks_total=len(chunks_payload), chunks_processed=len(chunks_payload))
        record_ingest_outcome("success")
        
        return {"status": "success", "url": url}
        
    except Exception as e:
        logger.error(f"❌ [Page:{task_id}] Failed {url}: {e}")
        
        try:
            if crawl_id:
                try:
                    supabase.rpc("increment_crawl_counter", {
                        "p_crawl_id": crawl_id,
                        "p_field": "pages_failed"
                    }).execute()
                except Exception:
                    pass
            
            _record_crawl_outcome_and_maybe_finalize(
                supabase,
                user_id,
                crawl_id,
                url,
                "failed",
                job_id=job_ref,
            )
            mark_file_status("failed", progress=0, message="Unexpected error", error=str(e)[:200])
            record_ingest_outcome("failed")
        finally:
            try:
                send_failure_email_notification(supabase, user_id, url, str(e))
            except Exception:
                pass
        
        raise


@celery_app.task(bind=True, ignore_result=True)
def finalize_crawl_task(
    self,
    user_id: str,
    crawl_id: str
):
    """Finalize crawl after all page tasks complete."""
    task_id = self.request.id
    supabase = get_supabase()

    config_res = supabase.table("web_crawl_configs").select(
        "status,root_url,total_pages_found,pages_ingested,pages_failed"
    ).eq("id", crawl_id).single().execute()
    if not config_res.data:
        logger.warning(f"[FinalizeCrawl:{task_id}] Crawl {crawl_id} not found")
        return

    config = config_res.data
    current_status = config.get("status")
    if current_status in {"completed", "failed", "cancelled"}:
        logger.info(f"[FinalizeCrawl:{task_id}] Crawl {crawl_id} already {current_status}")
        return

    total_pages = config.get("total_pages_found") or 0
    counters = get_crawl_counters(crawl_id)
    counts_source = "redis"

    if counters:
        success_count = counters.get("success", 0)
        failed_count = counters.get("failed", 0)
        skipped_count = counters.get("skipped", 0)
        if not total_pages:
            total_pages = counters.get("total", 0)

        db_success = config.get("pages_ingested") or 0
        db_failed = config.get("pages_failed") or 0
        if (db_success + db_failed) and (db_success != success_count or db_failed != failed_count):
            success_count = db_success
            failed_count = db_failed
            counts_source = "db"
            if job_counters_reconciled:
                job_counters_reconciled.labels("crawl").inc()
    else:
        if job_counters_missing:
            job_counters_missing.labels("crawl").inc()
        success_count = config.get("pages_ingested") or 0
        failed_count = config.get("pages_failed") or 0
        skipped_count = 0
        counts_source = "db"
        if job_counters_reconciled:
            job_counters_reconciled.labels("crawl").inc()

    processed_total = success_count + failed_count + skipped_count
    if total_pages > 0 and processed_total < total_pages:
        logger.info(
            f"[FinalizeCrawl:{task_id}] Crawl {crawl_id} not complete ({processed_total}/{total_pages})"
        )
        return

    logger.info(
        f"✅ [FinalizeCrawl:{task_id}] Crawl done: {success_count} success, {failed_count} failed, {skipped_count} skipped"
    )

    final_status = "completed" if success_count > 0 or skipped_count > 0 else "failed"
    if final_status == "failed":
        status_msg = f"All {failed_count} pages failed"
    else:
        status_parts = [f"Processed {processed_total}/{total_pages or processed_total} pages"]
        if skipped_count:
            status_parts.append(f"{skipped_count} skipped")
        if failed_count:
            status_parts.append(f"{failed_count} failed")
        status_msg = ", ".join(status_parts)
    update_crawl_status(
        supabase,
        crawl_id,
        status=final_status,
        pages_ingested=success_count,
        pages_failed=failed_count,
        job_id=crawl_id,
        message=status_msg
    )

    try:
        update_job_status(
            supabase,
            crawl_id,
            status=final_status,
            processed_files=processed_total,
            failed_files=failed_count,
            progress=100,
            message=status_msg,
        )
    except Exception:
        pass

    if job_counters_finalize:
        job_counters_finalize.labels("crawl", counts_source).inc()

    clear_crawl_counters(crawl_id)

    root_url = config.get("root_url") or "website"
    create_notification(
        supabase, user_id,
        "Web Crawl Complete" if final_status == "completed" else "Web Crawl Failed",
        f"Ingested {success_count} pages from {root_url}" if final_status == "completed" else f"Failed to crawl {root_url}",
        "success" if final_status == "completed" else "error",
        {"crawl_id": crawl_id, "pages_ingested": success_count, "pages_failed": failed_count}
    )


# Legacy alias (backward compatibility)
crawl_web_task = crawl_discovery_task


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
                max_pages = config.get("max_pages", 500)
                allow_subdomains = config.get("allow_subdomains", False)
                respect_robots = config.get("respect_robots_txt", True)
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

                try:
                    supabase.table("ingestion_jobs").upsert({
                        "id": crawl_id,
                        "user_id": user_id,
                        "provider": "web",
                        "status": "pending",
                        "total_files": 0,
                        "processed_files": 0,
                        "failed_files": 0,
                        "progress": 0,
                        "message": f"Queued crawl for {root_url}",
                        "status_message": f"Queued crawl for {root_url}",
                    }, on_conflict="id").execute()
                except Exception as job_exc:
                    try:
                        supabase.table("ingestion_jobs").insert({
                            "id": crawl_id,
                            "user_id": user_id,
                            "provider": "web",
                            "status": "pending",
                            "total_files": 0,
                            "processed_files": 0,
                            "failed_files": 0,
                            "progress": 0,
                            "message": f"Queued crawl for {root_url}",
                            "status_message": f"Queued crawl for {root_url}",
                        }).execute()
                    except Exception as inner_err:
                        logger.warning(f"⚠️ [Scheduler] Failed to upsert ingestion job for crawl {crawl_id}: {inner_err}")
                        inner_err = None
                
                # Queue crawl discovery task for web crawl
                task = crawl_discovery_task.delay(
                    user_id=user_id,
                    root_url=root_url,
                    crawl_config={
                        "crawl_id": crawl_id,
                        "crawl_type": crawl_type,
                        "max_depth": max_depth,
                        "max_pages": max_pages,
                        "respect_robots": respect_robots,
                        "allow_subdomains": allow_subdomains,
                        "is_recrawl": True,
                        "job_id": crawl_id,
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
                try:
                    supabase.table("ingestion_jobs").update({
                        "celery_task_id": task.id,
                        "status": "processing",
                        "message": "Queued for scheduled crawl"
                    }).eq("id", crawl_id).execute()
                except Exception:
                    pass
                
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
# WEB CRAWL RATE LIMITING HELPERS
# ============================================================

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
    from datetime import datetime, timedelta, timezone
    
    task_id = self.request.id[:8] if self.request.id else "cleanup"
    logger.info(f"🧹 [Cleanup:{task_id}] Starting database cleanup...")
    
    try:
        from core import db

        supabase_fn = get_supabase
        if getattr(supabase_fn, "__module__", "") == "core.db" and getattr(db, "get_supabase", None):
            supabase_fn = db.get_supabase

        supabase = supabase_fn()
        
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
