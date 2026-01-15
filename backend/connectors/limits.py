"""
Connector concurrency limits.

Provides a process-local semaphore per connector type to avoid
bursting external APIs beyond safe concurrency levels.
"""

from __future__ import annotations

import logging
import threading
import time
from contextlib import contextmanager
from typing import Dict, Tuple, Iterator

from core.config import settings

logger = logging.getLogger(__name__)

_LIMITERS: Dict[str, Tuple[int, threading.BoundedSemaphore]] = {}


def _normalize_connector_type(connector_type: str) -> str:
    return (connector_type or "").strip().lower()


def _get_limit(connector_type: str) -> int:
    normalized = _normalize_connector_type(connector_type)
    if normalized == "google_drive":
        return settings.CONNECTOR_CONCURRENCY_GOOGLE_DRIVE
    if normalized == "notion":
        return settings.CONNECTOR_CONCURRENCY_NOTION
    if normalized == "web":
        return settings.CONNECTOR_CONCURRENCY_WEB
    if normalized == "onedrive":
        return settings.CONNECTOR_CONCURRENCY_ONEDRIVE
    if normalized == "sharepoint":
        return settings.CONNECTOR_CONCURRENCY_SHAREPOINT
    if normalized == "dropbox":
        return settings.CONNECTOR_CONCURRENCY_DROPBOX
    if normalized == "github":
        return settings.CONNECTOR_CONCURRENCY_GITHUB
    if normalized == "file_upload":
        return 0
    return settings.CONNECTOR_CONCURRENCY_DEFAULT


def _get_limiter(connector_type: str) -> threading.BoundedSemaphore | None:
    limit = _get_limit(connector_type)
    if limit <= 0:
        return None

    normalized = _normalize_connector_type(connector_type)
    existing = _LIMITERS.get(normalized)
    if existing is None or existing[0] != limit:
        limiter = threading.BoundedSemaphore(limit)
        _LIMITERS[normalized] = (limit, limiter)
        return limiter
    return existing[1]


@contextmanager
def connector_fetch_limit(connector_type: str) -> Iterator[None]:
    """
    Context manager to cap concurrent fetch operations per connector type.
    """
    limiter = _get_limiter(connector_type)
    if limiter is None:
        yield
        return

    start_wait = time.perf_counter()
    limiter.acquire()
    wait_time = time.perf_counter() - start_wait
    if wait_time > 0:
        logger.info(
            "⏳ [ConnectorLimit] Waited %.2fs for %s fetch slot",
            wait_time,
            _normalize_connector_type(connector_type),
        )
    try:
        yield
    finally:
        limiter.release()
