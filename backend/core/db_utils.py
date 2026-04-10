"""
Database helper utilities with retry/backoff.
"""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Iterable
from typing import Any

from core.resilience import (
    RATE_LIMIT_STATUS_CODES,
    SUPABASE_RETRY_CONFIG,
    is_retryable_error,
)

try:
    from core.metrics import (
        operation_duration,
        retry_failure,
        retry_success,
        retry_total,
    )
except Exception:
    retry_total = None
    retry_success = None
    retry_failure = None
    operation_duration = None

logger = logging.getLogger(__name__)


def _log_retry_attempt(
    *,
    attempt: int,
    max_attempts: int,
    table: str,
    context: str,
    retryable: bool,
    status_code: int | None,
    error_type: str,
    error: Exception,
    error_code: Any,
    error_details: Any,
    error_hint: Any,
    error_repr: str,
    operation: str,
) -> None:
    log_method = logger.warning if attempt == 1 or attempt >= max_attempts else logger.debug
    log_method(
        "⚠️ [DB] %s attempt %s/%s failed for %s (%s). retryable=%s status=%s error_type=%s error=%s code=%s details=%s hint=%s repr=%s",
        operation,
        attempt,
        max_attempts,
        table,
        context,
        retryable,
        status_code,
        error_type,
        error,
        error_code,
        error_details,
        error_hint,
        error_repr,
    )


def _get_status_code(error: Exception) -> int | None:
    status_code = getattr(error, "status_code", None)
    response = getattr(error, "response", None)
    if status_code is None and response is not None:
        status_code = getattr(response, "status_code", None)
    return status_code


def is_retryable_supabase_error(error: Exception) -> bool:
    if is_retryable_error(error):
        return True
    status_code = _get_status_code(error)
    return status_code in RATE_LIMIT_STATUS_CODES


def insert_rows_with_retry(
    supabase: Any,
    table: str,
    rows: Iterable[dict],
    context: str,
    max_attempts: int = 3,
) -> tuple[Any, float]:
    """
    Insert rows into a Supabase table with retry + jitter.

    Returns (result, duration_seconds) on success.
    """
    rows = list(rows)
    if not rows:
        raise ValueError("insert_rows_with_retry requires at least one row")

    min_wait = SUPABASE_RETRY_CONFIG.get("min_wait", 1.0)
    max_wait = SUPABASE_RETRY_CONFIG.get("max_wait", 5.0)

    for attempt in range(1, max_attempts + 1):
        start = time.perf_counter()
        try:
            result = supabase.table(table).insert(rows).execute()
            duration = time.perf_counter() - start
            if operation_duration:
                operation_duration.labels("supabase_insert").observe(duration)
            if retry_success and attempt > 1:
                retry_success.labels("supabase", f"insert:{table}").inc()
            logger.info(
                "🧩 [DB] Inserted %s rows into %s in %.2fs (%s)",
                len(rows),
                table,
                duration,
                context,
            )
            return result, duration
        except Exception as exc:
            duration = time.perf_counter() - start
            retryable = is_retryable_supabase_error(exc)
            status_code = _get_status_code(exc)
            error_code = getattr(exc, "code", None)
            error_details = getattr(exc, "details", None) or getattr(exc, "detail", None)
            error_hint = getattr(exc, "hint", None)
            error_type = type(exc).__name__
            error_repr = repr(exc)
            if retry_total and retryable:
                retry_total.labels("supabase", f"insert:{table}").inc()
            _log_retry_attempt(
                attempt=attempt,
                max_attempts=max_attempts,
                table=table,
                context=context,
                retryable=retryable,
                status_code=status_code,
                error_type=error_type,
                error=exc,
                error_code=error_code,
                error_details=error_details,
                error_hint=error_hint,
                error_repr=error_repr,
                operation="Insert",
            )
            if attempt >= max_attempts or not retryable:
                if retry_failure:
                    retry_failure.labels("supabase", f"insert:{table}").inc()
                raise

            backoff = min(max_wait, min_wait * (2 ** (attempt - 1)))
            jitter = random.uniform(0.0, min(0.5, backoff * 0.25))
            time.sleep(backoff + jitter)

    raise RuntimeError("insert_rows_with_retry exhausted attempts unexpectedly")


def delete_rows_with_retry(
    supabase: Any,
    table: str,
    filter_column: str,
    filter_value: Any,
    context: str,
    max_attempts: int = 3,
) -> tuple[Any, float]:
    """
    Delete rows from a Supabase table with retry + jitter.

    Returns (result, duration_seconds) on success.
    """
    min_wait = SUPABASE_RETRY_CONFIG.get("min_wait", 1.0)
    max_wait = SUPABASE_RETRY_CONFIG.get("max_wait", 5.0)

    for attempt in range(1, max_attempts + 1):
        start = time.perf_counter()
        try:
            result = supabase.table(table).delete().eq(filter_column, filter_value).execute()
            duration = time.perf_counter() - start
            if operation_duration:
                operation_duration.labels("supabase_delete").observe(duration)
            if retry_success and attempt > 1:
                retry_success.labels("supabase", f"delete:{table}").inc()
            logger.info(
                "🧹 [DB] Deleted rows from %s where %s=%s in %.2fs (%s)",
                table,
                filter_column,
                filter_value,
                duration,
                context,
            )
            return result, duration
        except Exception as exc:
            duration = time.perf_counter() - start
            retryable = is_retryable_supabase_error(exc)
            status_code = _get_status_code(exc)
            error_code = getattr(exc, "code", None)
            error_details = getattr(exc, "details", None) or getattr(exc, "detail", None)
            error_hint = getattr(exc, "hint", None)
            error_type = type(exc).__name__
            error_repr = repr(exc)
            if retry_total and retryable:
                retry_total.labels("supabase", f"delete:{table}").inc()
            _log_retry_attempt(
                attempt=attempt,
                max_attempts=max_attempts,
                table=table,
                context=context,
                retryable=retryable,
                status_code=status_code,
                error_type=error_type,
                error=exc,
                error_code=error_code,
                error_details=error_details,
                error_hint=error_hint,
                error_repr=error_repr,
                operation="Delete",
            )
            if attempt >= max_attempts or not retryable:
                if retry_failure:
                    retry_failure.labels("supabase", f"delete:{table}").inc()
                raise

            backoff = min(max_wait, min_wait * (2 ** (attempt - 1)))
            jitter = random.uniform(0.0, min(0.5, backoff * 0.25))
            time.sleep(backoff + jitter)

    raise RuntimeError("delete_rows_with_retry exhausted attempts unexpectedly")
