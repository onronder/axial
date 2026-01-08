"""
Celery Application Configuration

Production-grade async task queue for heavy file processing.
Uses Redis as broker and result backend.
"""

import os
from celery import Celery
from celery.schedules import crontab  # Required for beat schedule
from core.config import settings

# =============================================================================
# Sentry Error Tracking + Logs for Celery Workers
# =============================================================================
if settings.SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        import logging
        
        logging_integration = LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR
        )
        
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
            environment=os.getenv("ENVIRONMENT", "development"),
            integrations=[
                CeleryIntegration(),
                logging_integration,
            ],
            release=os.getenv("RAILWAY_GIT_COMMIT_SHA", "local"),
            _experiments={
                "enable_logs": True,
            },
        )
    except ImportError:
        pass  # sentry-sdk not installed
    except Exception:
        pass  # Sentry init failed

# Initialize Celery with Redis
celery_app = Celery(
    "axial_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["worker.tasks"]  # Auto-discover tasks
)

# ============================================================
# CRITICAL PRODUCTION CONFIGURATION
# ============================================================

celery_app.conf.update(
    # Connection retry on startup (Celery 6.0+ compatibility)
    broker_connection_retry_on_startup=True,
    
    # Reliability: Tasks are only acknowledged after successful completion
    # If worker crashes, task goes back to queue
    task_acks_late=True,
    
    # Resilience: Requeue task if worker is killed/lost
    task_reject_on_worker_lost=True,
    
    # Memory Safety: Worker takes ONLY 1 task at a time
    # Vital for large file processing (prevents memory exhaustion)
    worker_prefetch_multiplier=1,
    
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Timezone
    timezone="UTC",
    enable_utc=True,
    
    # Task result expiration (24 hours)
    result_expires=86400,
    
    # Retry configuration
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    
    # ============================================================
    # CELERY BEAT - Scheduled Tasks
    # ============================================================
    beat_schedule={
        # Check for scheduled re-crawls every hour
        "check-scheduled-crawls-hourly": {
            "task": "worker.tasks.check_scheduled_crawls",
            "schedule": 3600.0,  # Every hour (in seconds)
        },
        # Cleanup old completed/failed jobs daily at midnight UTC
        "cleanup-old-jobs-daily": {
            "task": "worker.tasks.cleanup_old_jobs",
            "schedule": 86400.0,  # Every 24 hours (in seconds)
        },
        # Retry failed tasks from DLQ every 5 minutes
        "retry-failed-tasks": {
            "task": "worker.dlq_worker.retry_failed_tasks",
            "schedule": 300.0,  # Every 5 minutes
        },
        # Reconcile ingestion jobs in case counters are missing/delayed
        "reconcile-ingestion-jobs": {
            "task": "worker.periodic_tasks.reconcile_ingestion_jobs",
            "schedule": 300.0,  # Every 5 minutes
        },
        # Update memory metrics every minute
        "update-memory-metrics": {
            "task": "worker.periodic_tasks.update_memory_metrics",
            "schedule": 60.0,  # Every minute
        },
        # Cleanup old file status records daily at 3am UTC
        "cleanup-old-file-status-daily": {
            "task": "worker.periodic_tasks.cleanup_old_file_status",
            "schedule": crontab(hour=3, minute=0),
        },
        # Cleanup old audit logs weekly on Sunday at 4am UTC
        "cleanup-old-audit-logs-weekly": {
            "task": "worker.periodic_tasks.cleanup_old_audit_logs",
            "schedule": crontab(day_of_week=0, hour=4, minute=0),
        },
    },
)
