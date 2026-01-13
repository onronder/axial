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
