"""
Database helper utilities with retry/backoff.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any, Iterable, Tuple

from core.resilience import SUPABASE_RETRY_CONFIG, RATE_LIMIT_STATUS_CODES, is_retryable_error

logger = logging.getLogger(__name__)


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
) -> Tuple[Any, float]:
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
            logger.warning(
                "⚠️ [DB] Insert attempt %s/%s failed for %s (%s). retryable=%s status=%s error=%s",
                attempt,
                max_attempts,
                table,
                context,
                retryable,
                status_code,
                exc,
            )
            if attempt >= max_attempts or not retryable:
                raise

            backoff = min(max_wait, min_wait * (2 ** (attempt - 1)))
            jitter = random.uniform(0.0, min(0.5, backoff * 0.25))
            time.sleep(backoff + jitter)

    raise RuntimeError("insert_rows_with_retry exhausted attempts unexpectedly")
