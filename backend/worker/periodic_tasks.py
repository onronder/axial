"""
Periodic maintenance tasks for Celery Beat.

These tasks run on a schedule to maintain system health.
"""

import logging
from datetime import datetime, timedelta, timezone
import psutil
from core.celery_app import celery_app
from core.db import get_supabase
from core.resilience import check_memory_usage
from core.job_counters import is_ingest_job_discovery_done
from core.metrics import (
    MEMORY_USAGE,
    MEMORY_AVAILABLE_MB,
    MEMORY_WARNINGS,
    MEMORY_CRITICAL,
    PROCESS_CPU_PERCENT,
    OPEN_FILES,
)

logger = logging.getLogger(__name__)


@celery_app.task(name="cleanup_old_jobs", ignore_result=True)
def cleanup_old_jobs():
    """
    Clean up old completed ingestion jobs (older than 30 days).
    
    Runs daily at 2 AM via Celery Beat.
    """
    try:
        supabase = get_supabase()
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
        
        # Delete old completed jobs
        result = supabase.table("ingestion_jobs").delete().eq(
            "status", "completed"
        ).lt(
            "created_at", cutoff_date.isoformat()
        ).execute()
        
        deleted_count = len(result.data) if result.data else 0
        logger.info(f"🧹 [Cleanup] Deleted {deleted_count} old completed jobs")
        
        return {"deleted": deleted_count}
        
    except Exception as e:
        logger.error(f"❌ [Cleanup] Failed to clean up old jobs: {e}")
        return {"error": str(e)}


@celery_app.task(name="update_memory_metrics", ignore_result=True)
def update_memory_metrics():
    """
    Update Prometheus memory metrics.
    
    Runs every minute via Celery Beat.
    """
    try:
        status = check_memory_usage()
        
        # Update Prometheus gauges
        MEMORY_USAGE.set(status['percent'])
        MEMORY_AVAILABLE_MB.set(status['available_mb'])

        process = psutil.Process()
        PROCESS_CPU_PERCENT.set(process.cpu_percent(interval=None))
        OPEN_FILES.set(len(process.open_files()))
        
        # Increment counters if needed
        if status['warning']:
            MEMORY_WARNINGS.inc()
        if status['critical']:
            MEMORY_CRITICAL.inc()
        
        return status
        
    except Exception as e:
        logger.error(f"❌ [Metrics] Failed to update memory metrics: {e}")
        return {"error": str(e)}


# Register DLQ retry task
@celery_app.task(name="worker.dlq_worker.retry_failed_tasks", ignore_result=True)
def retry_failed_tasks_task():
    """
    Wrapper task for DLQ retry function.
    
    Runs every 5 minutes via Celery Beat.
    """
    from worker.dlq_worker import retry_failed_tasks
    return retry_failed_tasks()


# ============================================================
# DATA HYGIENE CLEANUP TASKS
# ============================================================

@celery_app.task(name="cleanup_old_file_status", ignore_result=True)
def cleanup_old_file_status():
    """
    Clean up old ingestion file status entries (older than 30 days).
    
    File status records are transient - only needed during/after ingestion.
    Runs daily at 3 AM via Celery Beat.
    """
    try:
        supabase = get_supabase()
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
        
        # Only delete terminal entries (not pending/active processing)
        result = supabase.table("ingestion_file_status").delete().in_(
            "status", ["completed", "failed", "skipped", "cancelled"]
        ).lt(
            "created_at", cutoff_date.isoformat()
        ).execute()
        
        deleted_count = len(result.data) if result.data else 0
        logger.info(f"🧹 [Cleanup] Deleted {deleted_count} old file status entries")
        
        return {"deleted": deleted_count}
        
    except Exception as e:
        logger.error(f"❌ [Cleanup] Failed to clean up file status: {e}")
        return {"error": str(e)}


@celery_app.task(name="cleanup_old_audit_logs", ignore_result=True)
def cleanup_old_audit_logs():
    """
    Clean up old audit log entries (older than 90 days).
    
    GDPR compliance: Retain audit logs for 90 days, then delete.
    Runs weekly on Sunday at 4 AM via Celery Beat.
    """
    try:
        supabase = get_supabase()
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=90)
        
        result = supabase.table("audit_logs").delete().lt(
            "created_at", cutoff_date.isoformat()
        ).execute()
        
        deleted_count = len(result.data) if result.data else 0
        logger.info(f"🧹 [Cleanup] Deleted {deleted_count} old audit log entries")
        
        return {"deleted": deleted_count}
        
    except Exception as e:
        logger.error(f"❌ [Cleanup] Failed to clean up audit logs: {e}")
        return {"error": str(e)}


# ============================================================
# RECONCILIATION TASKS
# ============================================================

@celery_app.task(name="cleanup_orphan_scope_placeholders", ignore_result=True)
def cleanup_orphan_scope_placeholders():
    """
    Clean up orphan scope identity placeholders.
    
    Placeholders are created before document ingestion to satisfy FK constraints.
    If ingestion fails or is cancelled, these placeholders can remain and:
    1. Count toward the user's scope quota
    2. Show "Generating identity..." in UI
    3. Clutter the database
    
    Cleanup criteria:
    - status = 'placeholder'
    - is_placeholder = true in attributes
    - No associated documents exist
    - Created more than 24 hours ago (allows time for slow ingestions)
    
    Runs daily at 5 AM via Celery Beat.
    """
    try:
        supabase = get_supabase()
        cutoff_date = datetime.now(timezone.utc) - timedelta(hours=24)
        
        # Find placeholder scope identities older than 24 hours
        placeholders_res = supabase.table("scope_identities").select(
            "id, organization_id, user_id, created_at"
        ).eq("status", "placeholder").lt(
            "updated_at", cutoff_date.isoformat()
        ).execute()
        
        placeholders = placeholders_res.data or []
        if not placeholders:
            logger.info("🧹 [Cleanup] No orphan scope placeholders found")
            return {"deleted": 0, "checked": 0}
        
        deleted_count = 0
        checked_count = len(placeholders)
        
        for placeholder in placeholders:
            scope_id = placeholder.get("id")
            org_id = placeholder.get("organization_id")
            
            if not scope_id or not org_id:
                continue
            
            # Check if any documents reference this scope
            docs_res = supabase.table("documents").select(
                "id", count="exact"
            ).eq("organization_id", org_id).eq("scope_id", scope_id).limit(1).execute()
            
            doc_count = docs_res.count or 0
            
            if doc_count == 0:
                # No documents - safe to delete this orphan placeholder
                try:
                    supabase.table("scope_identities").delete().eq(
                        "organization_id", org_id
                    ).eq("id", scope_id).eq("status", "placeholder").execute()
                    
                    deleted_count += 1
                    logger.info(f"🧹 [Cleanup] Deleted orphan placeholder: {scope_id[:50]}...")
                except Exception as del_err:
                    logger.warning(f"⚠️ [Cleanup] Failed to delete placeholder {scope_id}: {del_err}")
        
        logger.info(f"🧹 [Cleanup] Deleted {deleted_count}/{checked_count} orphan scope placeholders")
        
        return {"deleted": deleted_count, "checked": checked_count}
        
    except Exception as e:
        logger.error(f"❌ [Cleanup] Failed to clean up orphan placeholders: {e}")
        return {"error": str(e)}


@celery_app.task(name="worker.periodic_tasks.reconcile_ingestion_jobs", ignore_result=True)
def reconcile_ingestion_jobs():
    """
    Reconcile ingestion jobs when Redis counters are missing or delayed.

    Ensures jobs complete based on database file status counts.
    """
    try:
        supabase = get_supabase()
        jobs_res = supabase.table("ingestion_jobs").select("id,user_id,total_files,status").eq(
            "status", "processing"
        ).execute()

        jobs = jobs_res.data or []
        if not jobs:
            return {"status": "ok", "jobs_checked": 0, "jobs_finalized": 0}

        jobs_finalized = 0
        for job in jobs:
            job_id = job.get("id")
            user_id = job.get("user_id")
            total_files = job.get("total_files") or 0
            if not job_id or total_files <= 0:
                continue
            if not is_ingest_job_discovery_done(job_id):
                continue

            status_res = supabase.table("ingestion_file_status").select("status").eq(
                "job_id", job_id
            ).execute()

            counts = {"completed": 0, "failed": 0, "skipped": 0}
            for row in status_res.data or []:
                status = row.get("status")
                if status in counts:
                    counts[status] += 1

            processed_total = counts["completed"] + counts["failed"] + counts["skipped"]
            if processed_total >= total_files:
                from worker.tasks import finalize_job_task
                finalize_job_task.apply_async(kwargs={"user_id": user_id, "job_id": job_id})
                jobs_finalized += 1

        return {
            "status": "ok",
            "jobs_checked": len(jobs),
            "jobs_finalized": jobs_finalized,
        }
    except Exception as e:
        logger.error(f"❌ [Reconcile] Failed to reconcile jobs: {e}")
        return {"error": str(e)}
