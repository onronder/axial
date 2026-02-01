"""
Celery Application Configuration

Production-grade async task queue for heavy file processing.
Uses Redis as broker and result backend.
"""

# Suppress third-party deprecation warnings (MUST be first import)
import core.suppress_warnings  # noqa: F401

import os
import sys
from celery import Celery
from kombu import Queue
from celery.schedules import crontab  # Required for beat schedule
from core.config import settings

# =============================================================================
# Sentry Error Tracking + Logs for Celery Workers
# =============================================================================
def _is_test_runtime() -> bool:
    return (
        settings.ENVIRONMENT == "test"
        or "PYTEST_CURRENT_TEST" in os.environ
        or "pytest" in sys.modules
        or os.getenv("CELERY_TASK_ALWAYS_EAGER") == "1"
    )


def init_celery_sentry() -> None:
    if settings.SENTRY_DSN and settings.ENVIRONMENT != "test":
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


init_celery_sentry()

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

    # Reduce result backend overhead (we track progress in DB/Redis)
    task_ignore_result=True,
    task_store_errors_even_if_ignored=False,
    
    # Retry configuration
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,

    # Time limits (soft raises SoftTimeLimitExceeded, hard kills task)
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,

    # ============================================================
    # WORKER MEMORY MANAGEMENT (Enterprise OOM Protection)
    # ============================================================
    # Self-healing workers via automatic process recycling.
    # CRITICAL: Only works with --pool=prefork (NOT gevent)
    #
    # Memory Math (32GB Enterprise Node):
    #   Available: 28GB, Workers: 8, Limit: 3GB each
    #   Peak: 8 × 3GB = 24GB << 28GB available ✅
    
    # Kill & respawn worker when memory exceeds threshold (KB)
    # Releases ALL memory back to OS via clean process exit
    worker_max_memory_per_child=settings.CELERY_WORKER_MAX_MEMORY_PER_CHILD,
    
    # Kill & respawn worker after N tasks (catches slow memory leaks)
    worker_max_tasks_per_child=settings.CELERY_WORKER_MAX_TASKS_PER_CHILD,

    # ============================================================
    # Queue Topology (Stage Isolation)
    # ============================================================
    task_queues=(
        Queue("celery"),  # default/orchestration
        Queue("queues.parsing"),
        Queue("queues.embedding"),
        Queue("queues.indexing"),
    ),
    task_routes={
        "worker.tasks.unified_ingest_task": {"queue": "celery"},
        "worker.tasks.process_file_task": {"queue": "queues.parsing"},
        "worker.tasks.crawl_discovery_task": {"queue": "queues.parsing"},
        "worker.tasks.process_page_task": {"queue": "queues.parsing"},
        "worker.tasks.generate_embeddings_task": {"queue": "queues.embedding"},
        "worker.tasks.index_chunks_task": {"queue": "queues.indexing"},
        "worker.tasks.finalize_job_task": {"queue": "celery"},
        "worker.tasks.finalize_crawl_task": {"queue": "celery"},
    },
    
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
        # Cleanup orphan scope identity placeholders daily at 5am UTC
        # These are created during ingestion but may remain if jobs fail
        "cleanup-orphan-scope-placeholders-daily": {
            "task": "cleanup_orphan_scope_placeholders",
            "schedule": crontab(hour=5, minute=0),
        },
    },
)

# Avoid publishing test jobs to external brokers during pytest runs.
if _is_test_runtime():
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
    )

# =============================================================================
# GHOST PROTOCOL: Register Cleanup Signal Handlers
# =============================================================================
# Import signal handlers to ensure they're registered when workers start.
# This enables emergency cleanup of sensitive data on worker shutdown.

try:
    import worker.ghost_protocol_signals  # noqa: F401
except ImportError:
    pass  # Worker module not available (e.g., in API-only deployments)
