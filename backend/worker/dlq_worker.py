"""
Dead Letter Queue Worker

Handles failed task tracking and automatic retry logic.
"""

import logging
import traceback
from datetime import datetime, timedelta, timezone
from typing import Any

from core.db import get_supabase

logger = logging.getLogger(__name__)

SENSITIVE_KEYS = {
    "content_b64",
    "access_token",
    "refresh_token",
    "token",
    "authorization",
    "api_key",
    "openai_api_key",
    "supabase_service_key",
    "supabase_secret_key",
    "secret",
    "password",
    "credentials",
}


def _redact_value(value: Any) -> str:
    if isinstance(value, (bytes, bytearray)):
        return f"<redacted:{len(value)} bytes>"
    if isinstance(value, str):
        return "<redacted>"
    return "<redacted>"


def redact_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        redacted = {}
        for key, value in payload.items():
            if key and str(key).lower() in SENSITIVE_KEYS:
                redacted[key] = _redact_value(value)
            else:
                redacted[key] = redact_payload(value)
        return redacted
    if isinstance(payload, list):
        return [redact_payload(item) for item in payload]
    if isinstance(payload, tuple):
        return [redact_payload(item) for item in payload]
    return payload


def log_task_failure(
    task_id: str,
    task_name: str,
    args: tuple | None,
    kwargs: dict | None,
    exc: Exception,
    traceback_str: str,
    user_id: str | None = None,
    job_id: str | None = None,
    supabase_client=None,
) -> None:
    """
    Log failed task to dead letter queue.

    Args:
        task_id: Celery task ID
        task_name: Name of the task
        args: Task positional arguments
        kwargs: Task keyword arguments
        exc: Exception that caused failure
        traceback_str: Full traceback string
        user_id: Optional user ID
        job_id: Optional job ID
    """
    try:
        supabase = supabase_client or get_supabase()

        # Calculate next retry time (exponential backoff)
        # First retry: 5 minutes, second: 15 minutes, third: 1 hour
        retry_delays = [5, 15, 60]  # minutes

        safe_args = redact_payload(list(args) if args else [])
        safe_kwargs = redact_payload(kwargs or {})

        # Check if task already exists in DLQ
        existing = supabase.table("failed_tasks").select("*").eq(
            "task_id", task_id
        ).execute()

        existing_data = existing.data if isinstance(getattr(existing, "data", None), list) else []

        if existing_data:
            # Update existing record
            attempt_count = existing_data[0].get("attempt_count", 0) + 1

            if attempt_count <= 3:
                # Schedule retry
                delay_minutes = retry_delays[min(attempt_count - 1, len(retry_delays) - 1)]
                next_retry = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
                status = 'pending_retry'
            else:
                # Permanently failed
                next_retry = None
                status = 'permanently_failed'

            supabase.table("failed_tasks").update({
                "attempt_count": attempt_count,
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "traceback": traceback_str,
                "args": safe_args,
                "kwargs": safe_kwargs,
                "status": status,
                "next_retry_at": next_retry.isoformat() if next_retry else None,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("task_id", task_id).execute()

            logger.warning(
                f"📥 [DLQ] Updated failed task {task_id}: "
                f"attempt {attempt_count}/3, status={status}"
            )
        else:
            # Create new record
            next_retry = datetime.now(timezone.utc) + timedelta(minutes=retry_delays[0])

            supabase.table("failed_tasks").insert({
                "task_id": task_id,
                "task_name": task_name,
                "user_id": user_id,
                "job_id": job_id,
                "args": safe_args,
                "kwargs": safe_kwargs,
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "traceback": traceback_str,
                "attempt_count": 1,
                "max_retries": 3,
                "next_retry_at": next_retry.isoformat(),
                "status": "pending_retry"
            }).execute()

            logger.warning(
                f"📥 [DLQ] Logged failed task {task_id} ({task_name}): "
                f"will retry in {retry_delays[0]} minutes"
            )

    except Exception as e:
        logger.error(f"❌ [DLQ] Failed to log task failure: {e}")


def log_failed_task(
    supabase,
    task_id: str,
    task_name: str,
    exception: Exception,
    user_id: str | None = None,
    job_id: str | None = None,
    kwargs: dict | None = None,
    args: tuple | None = None,
) -> None:
    """
    Backwards-compatible wrapper for logging failed tasks.

    Maintains older call signature used in tests and legacy code.
    """
    trace = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
    log_task_failure(
        task_id=task_id,
        task_name=task_name,
        args=args,
        kwargs=kwargs,
        exc=exception,
        traceback_str=trace,
        user_id=user_id,
        job_id=job_id,
        supabase_client=supabase,
    )


def retry_failed_tasks() -> dict[str, Any]:
    """
    Retry tasks from dead letter queue that are ready for retry.

    This should be called periodically (e.g., every 5 minutes) by a Celery beat task.

    Returns:
        Dict with retry statistics
    """
    try:
        supabase = get_supabase()
        now = datetime.now(timezone.utc)

        # Get tasks ready for retry
        tasks = supabase.table("failed_tasks").select("*").eq(
            "status", "pending_retry"
        ).lte(
            "next_retry_at", now.isoformat()
        ).execute()

        if not tasks.data:
            logger.info("📥 [DLQ] No tasks ready for retry")
            return {"retried": 0, "failed": 0}

        retried = 0
        failed = 0

        for task in tasks.data:
            try:
                # Atomic claim: Only update if still pending_retry (optimistic locking)
                # This prevents race conditions when multiple workers try to claim the same task
                claim_result = supabase.table("failed_tasks").update({
                    "status": "retrying",
                    "updated_at": now.isoformat()
                }).eq("id", task['id']).eq("status", "pending_retry").execute()

                # Check if we successfully claimed the task
                if not claim_result.data:
                    # Another worker already claimed this task, skip it
                    logger.debug(f"📥 [DLQ] Task {task['task_id']} already claimed by another worker")
                    continue

                # Import and dispatch the task
                from worker.tasks import unified_ingest_task

                # Retry the task
                if task['task_name'] == 'unified_ingest_task':
                    kwargs = task['kwargs']
                    unified_ingest_task.apply_async(
                        kwargs=kwargs,
                        task_id=f"{task['task_id']}_retry_{task['attempt_count']}"
                    )
                    retried += 1
                    logger.info(
                        f"📥 [DLQ] Retrying task {task['task_id']} "
                        f"(attempt {task['attempt_count']}/3)"
                    )
                else:
                    logger.warning(f"📥 [DLQ] Unknown task type: {task['task_name']}")
                    failed += 1

            except Exception as e:
                logger.error(f"❌ [DLQ] Failed to retry task {task['task_id']}: {e}")
                failed += 1

                # Mark as failed again
                supabase.table("failed_tasks").update({
                    "status": "failed",
                    "updated_at": now.isoformat()
                }).eq("id", task['id']).execute()

        logger.info(f"📥 [DLQ] Retry summary: {retried} retried, {failed} failed")
        return {"retried": retried, "failed": failed}

    except Exception as e:
        logger.error(f"❌ [DLQ] Failed to process retry queue: {e}")
        return {"retried": 0, "failed": 0, "error": str(e)}
