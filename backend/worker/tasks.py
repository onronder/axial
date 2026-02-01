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
import shutil
import tempfile
import random
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from collections import deque
from urllib.parse import urlparse

from core.celery_app import celery_app
from core.db import get_supabase
from core.db_utils import insert_rows_with_retry, delete_rows_with_retry
from core.config import settings
from core.hashing import compute_content_hash
from core.ingestion_utils import normalize_provider, normalize_source_type
from core.job_counters import (
    init_ingest_job_counters,
    increment_ingest_job_total,
    record_ingest_outcome,
    get_ingest_job_counters,
    mark_ingest_job_discovery_done,
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
from services.malware import scan_content, MalwareScanException
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
logger.info("✅ Worker tasks module loaded - Cache buster 005 (Full Merge)")

DEFAULT_INGEST_DISPATCH_BATCH_SIZE = 50
STAGING_BUCKET = "ephemeral-staging"


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
    ".txt", ".md", ".markdown", ".csv", ".log", ".doc", ".docx", ".json", ".yaml", ".yml",
    ".toml", ".xml", ".html", ".css", ".sql", ".py", ".js", ".jsx", ".ts", ".tsx",
    ".java", ".go", ".cpp", ".c", ".cs", ".rb", ".php", ".rs", ".scala", ".swift", ".kt",
}


def _resolve_org_scope(supabase, user_id: str) -> Dict[str, Optional[str]]:
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


def _update_job_progress_from_counters(supabase, job_id: str, counters: Dict[str, int]) -> None:
    if not counters:
        return
    total = counters.get("total", 0)
    processed = counters.get("processed", 0)
    failed = counters.get("failed", 0)
    skipped = counters.get("skipped", 0)

    if total <= 0 or processed <= 0:
        return

    try:
        import redis
        client = redis.from_url(settings.REDIS_URL)
        throttle_key = f"ingest_job:progress:{job_id}"
        if not client.set(throttle_key, "1", nx=True, ex=settings.REDIS_JOB_PROGRESS_UPDATE_INTERVAL):
            if processed < total:
                return
    except Exception:
        pass

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

    discovery_done = counters.get("discovery_done")
    if discovery_done is None:
        discovery_done = 1
    if not discovery_done:
        return

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


# ============================================================
# INGESTION CORE
# ============================================================

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
    file_status_id: str = None,
    content_hash: str | None = None
) -> str:
    """
    Insert document and chunks in batches to prevent DB timeouts.
    Handles 'Atomic Replacement' to prevent Ghost Data.
    """
    DB_BATCH_SIZE = max(1, min(settings.CHUNK_INSERT_BATCH_SIZE, 200))
    source_type = normalize_source_type(source_type) or source_type
    
    existing_doc_id = None
    source_id = metadata.get("source_id")

    query = supabase.table("documents").select("id, content_hash").eq("user_id", user_id)

    if source_id:
        # 1. Lookup by Connector ID
        query = query.eq("metadata->>source_id", source_id)
    elif source_url:
        # 2. Lookup by URL
        query = query.eq("source_url", source_url)
    else:
        # 3. Lookup by Title + Type
        query = query.eq("title", doc_title).eq("source_type", source_type)

    try:
        res = query.limit(1).execute()
        if res.data:
            existing_doc = res.data[0]
            existing_doc_id = existing_doc["id"]
    except Exception as e:
        logger.warning(f"⚠️ [Ingest] Identity lookup failed: {e}")

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

    if existing_doc_id:
        if idempotency_hits:
            idempotency_hits.labels(source_type or "unknown").inc()

        logger.info(f"♻️ [Ingest] Updating existing document {existing_doc_id}")

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
    else:
        doc_result = supabase.table("documents").insert(doc_data).execute()
        if not doc_result.data:
            raise Exception("Failed to create document record")
        doc_id = doc_result.data[0]["id"]
        logger.info(f"📄 [Ingest] Created new document {doc_id}")
    
    total_chunks = len(chunks_payload)
    if total_chunks == 0:
        return str(doc_id)
    
    for i in range(0, total_chunks, DB_BATCH_SIZE):
        batch = chunks_payload[i:i + DB_BATCH_SIZE]
        for chunk in batch:
            chunk["document_id"] = str(doc_id)
            if "metadata" in chunk:
                del chunk["metadata"]
        
        try:
            insert_rows_with_retry(
                supabase,
                "document_chunks",
                batch,
                context=f"doc_id={doc_id} batch={i // DB_BATCH_SIZE + 1}",
            )
        except Exception as e:
            logger.error(f"❌ Failed to insert chunk batch {i//DB_BATCH_SIZE + 1}: {e}")
            continue

    logger.info(f"✅ [Ingest] Indexed chunks for {doc_id}")
    return str(doc_id)


def create_file_status(supabase, job_id: str, user_id: str, filename: str, file_size: int = 0) -> Optional[str]:
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
        return result.data[0]["id"] if result.data else None
    except Exception as e:
        logger.warning(f"⚠️ Failed to create file status for {filename}: {e}")
        return None


def store_celery_task_id(supabase, job_id: str, celery_task_id: str):
    if not job_id: return
    try:
        supabase.table("ingestion_jobs").update({"celery_task_id": celery_task_id}).eq("id", job_id).execute()
    except Exception: pass


def check_job_cancelled(supabase, job_id: str) -> bool:
    if not job_id: return False
    try:
        res = supabase.table("ingestion_jobs").select("status").eq("id", job_id).single().execute()
        return res.data and res.data.get("status") == "cancelled"
    except Exception:
        return False


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
    try:
        if check_setting_key:
            try:
                pref = supabase.table("user_notification_settings").select("enabled").eq("user_id", user_id).eq("setting_key", check_setting_key).maybe_single().execute()
                if pref.data and pref.data.get("enabled") is False:
                    return
            except Exception: pass

        meta = metadata.copy() if metadata else {}
        if action_url:
            meta["action_url"] = action_url

        supabase.table("notifications").insert({
            "user_id": user_id,
            "title": title,
            "message": message,
            "type": notification_type,
            "is_read": False,
            "extra_data": json.dumps(meta) if meta else None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()
    except Exception as e:
        logger.error(f"❌ Failed to create notification: {e}")


def send_email_notification(supabase, user_id: str, total_files: int):
    try:
        try:
            user_response = supabase.table("user_profiles").select("display_name,full_name,email").eq("user_id", user_id).single().execute()
            user_data = user_response.data or {}
            name = user_data.get("display_name") or user_data.get("full_name") or "there"
            email = user_data.get("email")
        except Exception:
            return

        if not email:
            try:
                auth_user = supabase.auth.admin.get_user_by_id(user_id)
                if auth_user and auth_user.user:
                    email = auth_user.user.email
            except Exception:
                pass
        
        if not email: return

        email_enabled = True
        try:
            settings_res = supabase.table("user_notification_settings").select("enabled").eq("user_id", user_id).eq("setting_key", "email_on_ingestion_complete").maybe_single().execute()
            if settings_res and settings_res.data:
                email_enabled = settings_res.data.get("enabled", True)
        except Exception: pass

        if email_enabled:
            email_service.send_ingestion_complete(to_email=email, name=name, total_files=total_files)

    except Exception as e:
        logger.error(f"📧 [Email] Failed: {e}")


def send_failure_email_notification(supabase, user_id: str, filename: str, error_message: str):
    try:
        try:
            user_response = supabase.table("user_profiles").select("display_name,full_name").eq("user_id", user_id).single().execute()
            user_data = user_response.data or {}
            name = user_data.get("display_name") or user_data.get("full_name") or "there"
        except Exception:
            name = "there"

        email = None
        try:
            auth_user = supabase.auth.admin.get_user_by_id(user_id)
            if auth_user and auth_user.user:
                email = auth_user.user.email
        except Exception: pass

        if not email: return

        email_enabled = True
        try:
            settings_res = supabase.table("user_notification_settings").select("enabled").eq("user_id", user_id).eq("setting_key", "email_on_ingestion_complete").maybe_single().execute()
            if settings_res and settings_res.data:
                email_enabled = settings_res.data.get("enabled", True)
        except Exception: pass

        if email_enabled:
            email_service.send_ingestion_failed(to_email=email, name=name, filename=filename, error_message=str(error_message)[:500])

    except Exception as e:
        logger.error(f"📧 [Email] Failed failure notice: {e}")


def _sanitize_text(value: str) -> str:
    if not value: return value
    return value.replace("\x00", "")


def handle_task_failure(self, exc, task_id, args, kwargs, einfo):
    try:
        from worker.dlq_worker import log_task_failure
        log_task_failure(task_id, self.name, args, kwargs, exc, str(einfo), kwargs.get('user_id'), kwargs.get('job_id'))
    except Exception as e:
        logger.error(f"❌ Failed to log to DLQ: {e}")


def _collect_documents_sync(connector, item_ids, credentials, user_id):
    fetch_sync = getattr(connector, "fetch_documents_sync", None)
    if not fetch_sync:
        raise RuntimeError("Connector does not support synchronous fetch (fetch_documents_sync)")
    return fetch_sync(item_ids, credentials, user_id=user_id)


# ============================================================
# UNIFIED INGESTION TASK (FAN-OUT)
# ============================================================

@celery_app.task(
    bind=True,
    name="unified_ingest_task",
    on_failure=handle_task_failure,
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    max_retries=3,
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
    dispatch_batch_size: Optional[int] = None,
):
    from celery import group
    
    task_id = self.request.id
    connector_type = normalize_provider(connector_type)
    item_ids = item_ids or ([item_id] if item_id else [])
    
    logger.info(f"[UnifiedIngest:{task_id}] Fan-out start: {connector_type} Job: {job_id}")
    supabase = get_supabase()
    store_celery_task_id(supabase, job_id, task_id)
    
    if check_job_cancelled(supabase, job_id):
        return {"status": "cancelled"}
        
    update_job_status(supabase, job_id, "processing")

    try:
        connector = get_connector(connector_type)
        batch_size = max(1, dispatch_batch_size or getattr(settings, "INGEST_DISPATCH_BATCH_SIZE", DEFAULT_INGEST_DISPATCH_BATCH_SIZE))
        
        counters_ready = init_ingest_job_counters(job_id, 0)
        file_tasks = []
        total_files = 0

        with connector_fetch_limit(connector_type):
            documents = _collect_documents_sync(connector, item_ids, credentials, user_id)

            for doc in documents:
                file_status_id = create_file_status(supabase, job_id, user_id, doc.filename, doc.size_bytes or 0)
                
                content_b64 = None
                if not doc.metadata.get("storage_path"):
                    if isinstance(doc.content, bytes):
                        content_b64 = base64.b64encode(doc.content).decode("utf-8")
                    elif isinstance(doc.content, str):
                        content_b64 = base64.b64encode(doc.content.encode("utf-8")).decode("utf-8")
                
                file_data = {
                    "filename": doc.filename,
                    "content_b64": content_b64,
                    "size_bytes": doc.size_bytes,
                    "mime_type": doc.mime_type,
                    "storage_path": doc.metadata.get("storage_path"),
                    "source_id": doc.source_id,
                    "parent_id": doc.parent_id,
                    "source_url": doc.metadata.get("source_url") or doc.metadata.get("url"),
                    "source_type": normalize_source_type(doc.source_type) or str(doc.source_type),
                    "metadata": doc.metadata or {},
                }
                
                file_tasks.append(
                    process_file_task.s(
                        user_id=user_id,
                        job_id=job_id,
                        file_data=file_data,
                        file_status_id=file_status_id,
                        connector_type=connector_type,
                        plan_code=plan_code
                    )
                )
                total_files += 1

                if len(file_tasks) >= batch_size:
                    if counters_ready: increment_ingest_job_total(job_id, len(file_tasks))
                    group(file_tasks).apply_async()
                    file_tasks = []

        if file_tasks:
            if counters_ready: increment_ingest_job_total(job_id, len(file_tasks))
            group(file_tasks).apply_async()

        if total_files == 0:
            update_job_status(supabase, job_id, "completed", message="No documents found", progress=100)
            return

        supabase.table("ingestion_jobs").update({"total_files": total_files}).eq("id", job_id).execute()
        if counters_ready:
            mark_ingest_job_discovery_done(job_id)

    except Exception as e:
        logger.error(f"[UnifiedIngest] Failed: {e}")
        update_job_status(supabase, job_id, "failed", error_message=str(e))
        raise


# ============================================================
# PROCESS FILE TASK (The Heavy Lifter)
# ============================================================

@celery_app.task(
    bind=True,
    name="process_file_task",
    on_failure=handle_task_failure,
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    max_retries=2,
    soft_time_limit=600,
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
    task_id = self.request.id
    filename = file_data.get("filename", "unknown")
    supabase = get_supabase()
    local_path = None
    
    try:
        update_file_status(supabase, file_status_id, job_id, status="processing", progress=10, message="Downloading...")
        
        storage_path = file_data.get("storage_path")
        content_b64 = file_data.get("content_b64")
        
        suffix = os.path.splitext(filename)[1] or ".bin"
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        local_path = tmp_file.name
        
        if storage_path:
            try:
                data = supabase.storage.from_(STAGING_BUCKET).download(storage_path)
                tmp_file.write(data)
                tmp_file.close()
                del data
            except Exception as e:
                raise ValueError(f"Failed to download {storage_path}: {e}")
        elif content_b64:
            tmp_file.write(base64.b64decode(content_b64))
            tmp_file.close()
        else:
            tmp_file.close()
            raise ValueError("No content provided (path or b64 missing)")

        file_size = os.path.getsize(local_path)
        if file_size > settings.MAX_FILE_SIZE:
            raise ValueError(f"File too large: {file_size} bytes")

        update_file_status(supabase, file_status_id, job_id, status="parsing", progress=30, message="Parsing...")
        
        # Scan content first chunk
        with open(local_path, "rb") as f:
            head = f.read(8192)

        result = DocumentProcessorFactory.process(
            file_path=local_path,
            filename=filename,
            mime_type=file_data.get("mime_type")
        )
        
        if result.file_type == "unsupported":
            update_file_status(supabase, file_status_id, job_id, status="skipped", progress=100, message="Unsupported format")
            _record_ingest_outcome_and_maybe_finalize(supabase, user_id, job_id, file_status_id, "skipped")
            return

        if not result.chunks:
            update_file_status(supabase, file_status_id, job_id, status="skipped", progress=100, message="No content extracted")
            _record_ingest_outcome_and_maybe_finalize(supabase, user_id, job_id, file_status_id, "skipped")
            return

        update_file_status(supabase, file_status_id, job_id, status="embedding", progress=60, message=f"Embedding {len(result.chunks)} chunks...")

        chunk_payload = []
        for chunk in result.chunks:
            chunk_payload.append({
                "content": _sanitize_text(chunk.content),
                "chunk_index": chunk.chunk_index,
                "token_count": chunk.token_count,
                "metadata": chunk.metadata
            })

        doc_payload = {
            "user_id": user_id,
            "title": filename,
            "source_type": file_data.get("source_type") or connector_type,
            "source_url": file_data.get("source_url"),
            "file_size_bytes": file_size,
            "content_hash": compute_content_hash(open(local_path, "rb").read()),
            "metadata": {
                **(file_data.get("metadata") or {}),
                "source_id": file_data.get("source_id"),
                "file_type": result.file_type
            },
            "job_id": job_id,
            "file_status_id": file_status_id,
            "filename": filename,
            "plan_code": plan_code
        }

        generate_embeddings_task.apply_async(
            args=[chunk_payload, doc_payload, plan_code],
            queue="queues.embedding"
        )
        
    except Exception as e:
        logger.error(f"[ProcessFile:{task_id}] Error: {e}")
        update_file_status(supabase, file_status_id, job_id, status="failed", error=str(e)[:500])
        _record_ingest_outcome_and_maybe_finalize(supabase, user_id, job_id, file_status_id, "failed")
        send_failure_email_notification(supabase, user_id, filename, str(e))
        
    finally:
        if local_path and os.path.exists(local_path):
            try: os.remove(local_path)
            except: pass
        if storage_path:
            try: supabase.storage.from_(STAGING_BUCKET).remove([storage_path])
            except: pass


@celery_app.task(bind=True, queue="queues.embedding", ignore_result=True)
def generate_embeddings_task(self, chunk_payload: list, doc_payload: dict, plan_code: Optional[str] = None):
    try:
        texts = [c["content"] for c in chunk_payload]
        tokens = [c["token_count"] for c in chunk_payload]
        embeddings = generate_embeddings_batch_sync(texts, token_counts=tokens, plan_code=plan_code)

        enriched = []
        for i, emb in enumerate(embeddings):
            if emb:
                item = chunk_payload[i]
                item["embedding"] = emb
                enriched.append(item)

        index_chunks_task.apply_async(
            args=[enriched, doc_payload],
            queue="queues.indexing"
        )
    except Exception as e:
        supabase = get_supabase()
        update_file_status(supabase, doc_payload.get("file_status_id"), doc_payload.get("job_id"), status="failed", error=str(e))
        _record_ingest_outcome_and_maybe_finalize(supabase, doc_payload.get("user_id"), doc_payload.get("job_id"), doc_payload.get("file_status_id"), "failed")


@celery_app.task(bind=True, queue="queues.indexing", ignore_result=True)
def index_chunks_task(self, chunk_payload: list, doc_payload: dict):
    supabase = get_supabase()
    try:
        update_file_status(supabase, doc_payload.get("file_status_id"), doc_payload.get("job_id"), status="indexing", progress=90)

        doc_id = ingest_document_batched(
            supabase=supabase,
            user_id=doc_payload["user_id"],
            doc_title=doc_payload["title"],
            source_type=doc_payload["source_type"],
            metadata=doc_payload["metadata"],
            chunks_payload=chunk_payload,
            file_size_bytes=doc_payload["file_size_bytes"],
            job_id=doc_payload["job_id"],
            source_url=doc_payload.get("source_url"),
            file_status_id=doc_payload.get("file_status_id"),
            content_hash=doc_payload.get("content_hash")
        )

        if doc_id:
            update_file_status(supabase, doc_payload.get("file_status_id"), doc_payload.get("job_id"), status="completed", progress=100, document_id=doc_id)
            _record_ingest_outcome_and_maybe_finalize(supabase, doc_payload.get("user_id"), doc_payload.get("job_id"), doc_payload.get("file_status_id"), "success")

    except Exception as e:
        logger.error(f"[IndexTask] Failed: {e}")
        update_file_status(supabase, doc_payload.get("file_status_id"), doc_payload.get("job_id"), status="failed", error=str(e))
        _record_ingest_outcome_and_maybe_finalize(supabase, doc_payload.get("user_id"), doc_payload.get("job_id"), doc_payload.get("file_status_id"), "failed")


@celery_app.task(bind=True, name="finalize_job_task", ignore_result=True)
def finalize_job_task(self, user_id: str, job_id: str):
    logger.info(f"[FinalizeJob:{self.request.id}] Finalizing job {job_id}")
    supabase = get_supabase()

    job_res = supabase.table("ingestion_jobs").select("status,total_files").eq("id", job_id).single().execute()
    if not job_res.data:
        return

    if job_res.data.get("status") in {"completed", "failed", "cancelled"}:
        return

    total_files = job_res.data.get("total_files") or 0
    counters = get_ingest_job_counters(job_id)
    counts_source = "redis"

    if counters:
        counts = counters
        if not total_files:
            total_files = counters.get("total", 0)
        db_counts = _get_ingestion_counts_from_db(supabase, job_id)
        if db_counts.get("processed", 0) != counters.get("processed", 0):
            counts = db_counts
            counts_source = "db"
    else:
        counts = _get_ingestion_counts_from_db(supabase, job_id)
        counts_source = "db"

    processed_total = counts.get("processed", 0)
    if total_files > 0 and processed_total < total_files:
        return

    success = counts.get("success", 0)
    failed = counts.get("failed", 0)
    final_status = "completed" if (success + counts.get("skipped", 0)) > 0 else "failed"
    status_msg = f"Processed {processed_total}/{total_files} files"

    supabase.table("ingestion_jobs").update({
        "status": final_status,
        "progress": 100,
        "message": status_msg,
        "processed_files": processed_total,
        "failed_files": failed,
    }).eq("id", job_id).execute()

    clear_ingest_job_counters(job_id)
    create_notification(supabase, user_id, "Ingestion Complete" if final_status == "completed" else "Ingestion Failed", status_msg)
    if success > 0:
        send_email_notification(supabase, user_id, success)


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

                if len(job_update) > 1:
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
    from celery import group
    from collections import deque
    
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
    supabase = get_supabase()
    
    try:
        from connectors.web import WebConnector
        connector = WebConnector()
        normalized_root = connector.normalize_url(root_url)
        if not normalized_root: raise ValueError("Invalid URL")
        if not connector.is_safe_url(normalized_root): raise ValueError("URL not allowed")
        root_url = normalized_root
        
        if crawl_id: update_crawl_status(supabase, crawl_id, status="discovering", job_id=job_id, message="Discovering pages...")
        if job_id:
            try: supabase.table("ingestion_jobs").update({"status": "processing", "progress": 5}).eq("id", job_id).execute()
            except: pass
        
        create_notification(supabase, user_id, "Web Crawl Started", f"Discovering pages from {root_url}", "info", {"crawl_id": crawl_id})
        
        urls_to_process = []
        parsed_root = urlparse(root_url)
        base_domain = parsed_root.hostname or ""
        
        if crawl_type == "sitemap":
            sitemap_urls = connector.parse_sitemap(root_url)
            seen = set()
            for url in sitemap_urls:
                norm = connector.normalize_url(url)
                if norm and norm not in seen and connector.is_allowed_domain(urlparse(norm).hostname, base_domain, allow_subdomains):
                    seen.add(norm)
                    urls_to_process.append(norm)
                if len(urls_to_process) >= max_pages: break
        elif crawl_type == "recursive":
            queue = deque([(root_url, 0)])
            seen = {root_url}
            while queue and len(urls_to_process) < max_pages:
                url, depth = queue.popleft()
                urls_to_process.append(url)
                if depth < max_depth:
                    html = connector.fetch_html(url)
                    if html:
                        links = connector.extract_links(html, url, base_domain=base_domain, allow_subdomains=allow_subdomains)
                        for link in links:
                            if link not in seen:
                                seen.add(link)
                                queue.append((link, depth+1))
                    time.sleep(random.uniform(0.3, 0.6))
        else:
            urls_to_process = [root_url]

        if respect_robots:
            urls_to_process = [u for u in urls_to_process if connector.check_robots_txt(u, connector.USER_AGENT)]

        total_pages = len(urls_to_process)
        if crawl_id: update_crawl_status(supabase, crawl_id, status="processing", total_pages=total_pages, job_id=job_id, message=f"Processing {total_pages} pages...")
        
        if total_pages == 0:
            if crawl_id: update_crawl_status(supabase, crawl_id, status="completed", total_pages=0, job_id=job_id)
            return

        # Dedup against existing
        if not is_recrawl:
            existing_urls = set()
            try:
                # Naive batch check
                res = supabase.table("documents").select("source_url").eq("user_id", user_id).in_("source_url", urls_to_process[:1000]).execute()
                for r in res.data or []: existing_urls.add(r["source_url"])
            except: pass
            urls_to_process = [u for u in urls_to_process if u not in existing_urls]
            
        if not urls_to_process:
            if crawl_id: update_crawl_status(supabase, crawl_id, status="completed", total_pages=0, job_id=job_id)
            return

        # Dispatch
        if job_id:
            init_ingest_job_counters(job_id, len(urls_to_process))
            try: supabase.table("ingestion_file_status").delete().eq("job_id", job_id).execute()
            except: pass

        file_status_ids = []
        if job_id:
            for url in urls_to_process:
                file_status_ids.append(create_file_status(supabase, job_id, user_id, url, 0))
        else:
            file_status_ids = [None] * len(urls_to_process)

        page_tasks = group([
            process_page_task.s(
                user_id=user_id,
                url=url,
                crawl_id=crawl_id,
                respect_robots=respect_robots,
                job_id=job_id,
                file_status_id=file_status_ids[i]
            ) for i, url in enumerate(urls_to_process)
        ])
        page_tasks.apply_async()
        
    except Exception as e:
        logger.error(f"❌ [Discovery] Failed: {e}")
        if crawl_id: update_crawl_status(supabase, crawl_id, status="failed", error_message=str(e), job_id=job_id)
        create_notification(supabase, user_id, "Web Crawl Failed", str(e)[:200], "error")
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
    task_id = self.request.id
    supabase = get_supabase()
    
    try:
        from connectors.web import WebConnector
        connector = WebConnector()
        
        if file_status_id: update_file_status(supabase, file_status_id, job_id, status="uploading", progress=10, message="Fetching...")
        
        if not connector.is_safe_url(url):
            raise ValueError("Unsafe URL")

        # Rate limit
        waited = 0
        while not check_rate_limit(supabase, url) and waited < 5:
            time.sleep(0.5); waited += 0.5

        docs = list(connector.fetch_documents_sync([url], None, respect_robots))
        if not docs:
            if file_status_id: update_file_status(supabase, file_status_id, job_id, status="skipped", progress=100)
            _record_crawl_outcome_and_maybe_finalize(supabase, user_id, crawl_id, url, "skipped", job_id)
            return

        doc = docs[0]
        content = doc.content
        if isinstance(content, bytes): content = content.decode("utf-8", errors="replace")
        
        result = DocumentProcessorFactory.process_web_content(content, url)
        
        if not result.chunks:
            if file_status_id: update_file_status(supabase, file_status_id, job_id, status="skipped", progress=100)
            _record_crawl_outcome_and_maybe_finalize(supabase, user_id, crawl_id, url, "skipped", job_id)
            return

        if file_status_id: update_file_status(supabase, file_status_id, job_id, status="embedding", progress=50)
        
        chunk_payload = []
        texts = [c.content for c in result.chunks]
        tokens = [c.token_count for c in result.chunks]
        embeddings = generate_embeddings_batch_sync(texts, token_counts=tokens)
        
        for i, chunk in enumerate(result.chunks):
            if embeddings[i]:
                chunk_payload.append({
                    "content": _sanitize_text(chunk.content),
                    "embedding": embeddings[i],
                    "chunk_index": chunk.chunk_index,
                    "metadata": chunk.metadata
                })
        
        if not chunk_payload:
            raise ValueError("No embeddings")

        if file_status_id: update_file_status(supabase, file_status_id, job_id, status="indexing", progress=80)
        
        doc_id = ingest_document_batched(
            supabase=supabase,
            user_id=user_id,
            doc_title=doc.metadata.get("title", "Web Page"),
            source_type="web",
            metadata={**doc.metadata, "file_type": "web", "crawl_id": crawl_id},
            chunks_payload=chunk_payload,
            file_size_bytes=len(content.encode("utf-8")),
            source_url=url,
            content_hash=compute_content_hash(content.encode("utf-8"))
        )
        
        if file_status_id: update_file_status(supabase, file_status_id, job_id, status="completed", progress=100, document_id=doc_id)
        _record_crawl_outcome_and_maybe_finalize(supabase, user_id, crawl_id, url, "success", job_id)
        _record_ingest_outcome_and_maybe_finalize(supabase, user_id, job_id, file_status_id, "success")
        
    except Exception as e:
        logger.error(f"❌ [Page:{task_id}] Failed {url}: {e}")
        if file_status_id: update_file_status(supabase, file_status_id, job_id, status="failed", error=str(e))
        if crawl_id:
            try: supabase.rpc("increment_crawl_counter", {"p_crawl_id": crawl_id, "p_field": "pages_failed"}).execute()
            except: pass
        _record_crawl_outcome_and_maybe_finalize(supabase, user_id, crawl_id, url, "failed", job_id)
        _record_ingest_outcome_and_maybe_finalize(supabase, user_id, job_id, file_status_id, "failed")
        raise


@celery_app.task(bind=True, ignore_result=True)
def finalize_crawl_task(
    self,
    user_id: str,
    crawl_id: str
):
    supabase = get_supabase()
    config = supabase.table("web_crawl_configs").select("*").eq("id", crawl_id).single().execute().data
    if not config: return

    if config["status"] in {"completed", "failed", "cancelled"}: return

    counters = get_crawl_counters(crawl_id)
    success = counters.get("success", 0) if counters else config.get("pages_ingested", 0)
    failed = counters.get("failed", 0) if counters else config.get("pages_failed", 0)

    final_status = "completed" if success > 0 else "failed"
    update_crawl_status(supabase, crawl_id, status=final_status, pages_ingested=success, pages_failed=failed)

    try:
        supabase.table("ingestion_jobs").update({
            "status": final_status,
            "progress": 100,
            "processed_files": success + failed
        }).eq("id", crawl_id).execute()
    except: pass

    clear_crawl_counters(crawl_id)
    create_notification(supabase, user_id, "Crawl Finished", f"Ingested {success} pages", "success")


@celery_app.task(bind=True)
def check_scheduled_crawls(self):
    supabase = get_supabase()
    now = datetime.now(timezone.utc)
    res = supabase.table("web_crawl_configs").select("*").eq("status", "completed").neq("refresh_interval", "never").lte("next_crawl_at", now.isoformat()).execute()
    
    triggered = 0
    for config in res.data or []:
        try:
            task = crawl_discovery_task.delay(config["user_id"], config["root_url"], {"crawl_id": config["id"], "is_recrawl": True})

            next_run = None
            if config["refresh_interval"] == "daily": next_run = now + timedelta(days=1)
            elif config["refresh_interval"] == "weekly": next_run = now + timedelta(weeks=1)

            update = {"celery_task_id": task.id, "last_crawl_at": now.isoformat(), "status": "pending"}
            if next_run: update["next_crawl_at"] = next_run.isoformat()

            supabase.table("web_crawl_configs").update(update).eq("id", config["id"]).execute()
            triggered += 1
        except Exception as e:
            logger.error(f"Failed to schedule crawl {config['id']}: {e}")

    return {"status": "ok", "triggered": triggered}


RATE_LIMIT_PREFIX = "crawl_ratelimit:"

def get_domain_rate_limit_key(url: str) -> str:
    domain = urlparse(url).netloc
    return f"{RATE_LIMIT_PREFIX}{domain}"

def check_rate_limit(supabase, url: str) -> bool:
    import redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        key = get_domain_rate_limit_key(url)
        current = r.get(key)
        if current and int(current) >= 5: return False
        r.incr(key)
        r.expire(key, 1)
        return True
    except: return True


@celery_app.task(bind=True)
def cleanup_old_jobs(self):
    supabase = get_supabase()
    # Simple cleanup logic
    try:
        supabase.table("ingestion_jobs").delete().in_("status", ["completed", "failed"]).lt("created_at", (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()).execute()
    except: pass
    return {"status": "ok"}

@celery_app.task(bind=True)
def health_check_task(self):
    return {"status": "healthy", "task_id": self.request.id}

crawl_web_task = crawl_discovery_task
