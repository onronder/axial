"""
Periodic maintenance tasks for Celery Beat.

These tasks run on a schedule to maintain system health.
"""

import logging
from datetime import datetime, timedelta, timezone
from core.celery_app import celery_app
from core.db import get_supabase
from core.resilience import check_memory_usage
from core.metrics import memory_usage_percent, memory_available_mb, memory_warnings, memory_critical

logger = logging.getLogger(__name__)


@celery_app.task(name="cleanup_old_jobs")
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


@celery_app.task(name="update_memory_metrics")
def update_memory_metrics():
    """
    Update Prometheus memory metrics.
    
    Runs every minute via Celery Beat.
    """
    try:
        status = check_memory_usage()
        
        # Update Prometheus gauges
        memory_usage_percent.set(status['percent'])
        memory_available_mb.set(status['available_mb'])
        
        # Increment counters if needed
        if status['warning']:
            memory_warnings.inc()
        if status['critical']:
            memory_critical.inc()
        
        return status
        
    except Exception as e:
        logger.error(f"❌ [Metrics] Failed to update memory metrics: {e}")
        return {"error": str(e)}


# Register DLQ retry task
@celery_app.task(name="worker.dlq_worker.retry_failed_tasks")
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

@celery_app.task(name="cleanup_old_file_status")
def cleanup_old_file_status():
    """
    Clean up old ingestion file status entries (older than 30 days).
    
    File status records are transient - only needed during/after ingestion.
    Runs daily at 3 AM via Celery Beat.
    """
    try:
        supabase = get_supabase()
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
        
        # Only delete completed or failed entries (not pending/processing)
        result = supabase.table("ingestion_file_status").delete().in_(
            "status", ["completed", "failed", "cancelled"]
        ).lt(
            "created_at", cutoff_date.isoformat()
        ).execute()
        
        deleted_count = len(result.data) if result.data else 0
        logger.info(f"🧹 [Cleanup] Deleted {deleted_count} old file status entries")
        
        return {"deleted": deleted_count}
        
    except Exception as e:
        logger.error(f"❌ [Cleanup] Failed to clean up file status: {e}")
        return {"error": str(e)}


@celery_app.task(name="cleanup_old_audit_logs")
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

