"""
Celery Application Configuration

Production-grade async task queue for heavy file processing.
Uses Redis as broker and result backend.
"""

from celery import Celery
from core.config import settings

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
    # Reliability: Tasks are only acknowledged after successful completion
    # If worker crashes, task goes back to queue
    task_acks_late=True,
    
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
    },
)
