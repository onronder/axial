"""
Redis-backed job counters for large fan-out workflows.

Tracks completion counts without Celery chord result payloads.
"""

from __future__ import annotations

import hashlib
import logging

from core.config import settings

logger = logging.getLogger(__name__)

OUTCOME_FIELDS = {"success", "failed", "skipped"}
UPDATE_FIELDS = {"job_status_updates", "file_status_updates"}

INGEST_NAMESPACE = "ingest_job"
CRAWL_NAMESPACE = "crawl_job"


def _hash_item_id(item_id: str) -> str:
    return hashlib.sha1(item_id.encode("utf-8")).hexdigest()


def _normalize_item_id(item_id: str) -> str | None:
    if not item_id:
        return None
    return _hash_item_id(str(item_id))


def _counter_key(namespace: str, job_id: str) -> str:
    return f"{namespace}:counter:{job_id}"


def _item_key(namespace: str, job_id: str, item_id: str) -> str:
    normalized = _normalize_item_id(item_id)
    if not normalized:
        raise ValueError("item_id is required for counter tracking")
    return f"{namespace}:item:{job_id}:{normalized}"


def _finalize_key(namespace: str, job_id: str) -> str:
    return f"{namespace}:finalize:{job_id}"


def _to_int(value: str | None) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _get_redis_client():
    try:
        import redis
        return redis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception as exc:
        logger.warning("[Counters] Redis unavailable: %s", exc)
        return None


def init_job_counters(namespace: str, job_id: str, total: int) -> bool:
    if not job_id:
        return False
    client = _get_redis_client()
    if not client:
        return False
    try:
        counter_key = _counter_key(namespace, job_id)
        client.hset(
            counter_key,
            mapping={
                "total": int(total),
                "processed": 0,
                "success": 0,
                "failed": 0,
                "skipped": 0,
                "discovery_done": 0,
                "job_status_updates": 0,
                "file_status_updates": 0,
            },
        )
        client.expire(counter_key, settings.REDIS_JOB_COUNTER_TTL_SECONDS)
        return True
    except Exception as exc:
        logger.warning("[Counters] Failed to init counters for %s: %s", job_id, exc)
        return False


def get_job_counters(namespace: str, job_id: str, client=None) -> dict[str, int] | None:
    if not job_id:
        return None
    if client is None:
        client = _get_redis_client()
    if not client:
        return None
    try:
        counter_key = _counter_key(namespace, job_id)
        values = client.hmget(
            counter_key,
            [
                "total",
                "processed",
                "success",
                "failed",
                "skipped",
                "discovery_done",
                "job_status_updates",
                "file_status_updates",
            ],
        )
        if all(value is None for value in values):
            return None
        return {
            "total": _to_int(values[0]),
            "processed": _to_int(values[1]),
            "success": _to_int(values[2]),
            "failed": _to_int(values[3]),
            "skipped": _to_int(values[4]),
            "discovery_done": _to_int(values[5]),
            "job_status_updates": _to_int(values[6]),
            "file_status_updates": _to_int(values[7]),
        }
    except Exception as exc:
        logger.warning("[Counters] Failed to read counters for %s: %s", job_id, exc)
        return None


def record_job_outcome(
    namespace: str,
    job_id: str,
    item_id: str,
    outcome: str,
) -> dict[str, int] | None:
    if not job_id or not item_id:
        return None
    client = _get_redis_client()
    if not client:
        return None

    normalized_outcome = outcome if outcome in OUTCOME_FIELDS else "failed"
    counter_key = _counter_key(namespace, job_id)

    try:
        item_key = _item_key(namespace, job_id, item_id)
        previous = client.get(item_key)
        if previous == normalized_outcome:
            return get_job_counters(namespace, job_id, client=client)

        pipe = client.pipeline()
        if previous is None:
            pipe.hincrby(counter_key, "processed", 1)
        elif previous in OUTCOME_FIELDS:
            pipe.hincrby(counter_key, previous, -1)

        pipe.hincrby(counter_key, normalized_outcome, 1)
        pipe.set(item_key, normalized_outcome)
        pipe.expire(counter_key, settings.REDIS_JOB_COUNTER_TTL_SECONDS)
        pipe.expire(item_key, settings.REDIS_JOB_COUNTER_TTL_SECONDS)
        pipe.execute()
    except Exception as exc:
        logger.warning("[Counters] Failed to record outcome for %s: %s", job_id, exc)
        return None

    return get_job_counters(namespace, job_id, client=client)


def record_job_update(namespace: str, job_id: str, field: str) -> None:
    if not job_id:
        return
    if field not in UPDATE_FIELDS:
        logger.warning("[Counters] Unknown update field for %s: %s", job_id, field)
        return
    client = _get_redis_client()
    if not client:
        return
    try:
        counter_key = _counter_key(namespace, job_id)
        client.hincrby(counter_key, field, 1)
        client.expire(counter_key, settings.REDIS_JOB_COUNTER_TTL_SECONDS)
    except Exception as exc:
        logger.warning("[Counters] Failed to record update for %s: %s", job_id, exc)


def increment_job_total(namespace: str, job_id: str, increment: int) -> int | None:
    if not job_id or increment <= 0:
        return None
    client = _get_redis_client()
    if not client:
        return None
    try:
        counter_key = _counter_key(namespace, job_id)
        total = client.hincrby(counter_key, "total", int(increment))
        client.expire(counter_key, settings.REDIS_JOB_COUNTER_TTL_SECONDS)
        return total
    except Exception as exc:
        logger.warning("[Counters] Failed to increment total for %s: %s", job_id, exc)
        return None


def mark_job_discovery_done(namespace: str, job_id: str) -> bool:
    if not job_id:
        return False
    client = _get_redis_client()
    if not client:
        return False
    try:
        counter_key = _counter_key(namespace, job_id)
        client.hset(counter_key, mapping={"discovery_done": 1})
        client.expire(counter_key, settings.REDIS_JOB_COUNTER_TTL_SECONDS)
        return True
    except Exception as exc:
        logger.warning("[Counters] Failed to mark discovery done for %s: %s", job_id, exc)
        return False


def is_job_discovery_done(namespace: str, job_id: str) -> bool:
    if not job_id:
        return True
    counters = get_job_counters(namespace, job_id)
    if not counters:
        return True
    discovery_done = counters.get("discovery_done")
    if discovery_done is None:
        return True
    return bool(discovery_done)


def mark_job_finalizing(namespace: str, job_id: str) -> bool:
    if not job_id:
        return False
    client = _get_redis_client()
    if not client:
        return False
    try:
        return bool(
            client.set(
                _finalize_key(namespace, job_id),
                "1",
                nx=True,
                ex=settings.REDIS_JOB_FINALIZE_TTL_SECONDS,
            )
        )
    except Exception as exc:
        logger.warning("[Counters] Failed to mark finalizing for %s: %s", job_id, exc)
        return False


def clear_job_counters(namespace: str, job_id: str) -> None:
    if not job_id:
        return
    client = _get_redis_client()
    if not client:
        return
    try:
        client.delete(_counter_key(namespace, job_id), _finalize_key(namespace, job_id))
    except Exception as exc:
        logger.warning("[Counters] Failed to clear counters for %s: %s", job_id, exc)


def init_ingest_job_counters(job_id: str, total_files: int) -> bool:
    return init_job_counters(INGEST_NAMESPACE, job_id, total_files)


def record_ingest_outcome(job_id: str, file_status_id: str, outcome: str) -> dict[str, int] | None:
    return record_job_outcome(INGEST_NAMESPACE, job_id, file_status_id, outcome)


def increment_ingest_job_total(job_id: str, increment: int) -> int | None:
    return increment_job_total(INGEST_NAMESPACE, job_id, increment)


def mark_ingest_job_discovery_done(job_id: str) -> bool:
    return mark_job_discovery_done(INGEST_NAMESPACE, job_id)


def is_ingest_job_discovery_done(job_id: str) -> bool:
    return is_job_discovery_done(INGEST_NAMESPACE, job_id)


def get_ingest_job_counters(job_id: str) -> dict[str, int] | None:
    return get_job_counters(INGEST_NAMESPACE, job_id)


def mark_ingest_job_finalizing(job_id: str) -> bool:
    return mark_job_finalizing(INGEST_NAMESPACE, job_id)


def clear_ingest_job_counters(job_id: str) -> None:
    clear_job_counters(INGEST_NAMESPACE, job_id)


def init_crawl_counters(crawl_id: str, total_pages: int) -> bool:
    return init_job_counters(CRAWL_NAMESPACE, crawl_id, total_pages)


def record_ingest_job_update(job_id: str) -> None:
    record_job_update(INGEST_NAMESPACE, job_id, "job_status_updates")


def record_ingest_file_update(job_id: str) -> None:
    record_job_update(INGEST_NAMESPACE, job_id, "file_status_updates")


def record_crawl_job_update(crawl_id: str) -> None:
    record_job_update(CRAWL_NAMESPACE, crawl_id, "job_status_updates")


def record_crawl_outcome(crawl_id: str, url: str, outcome: str) -> dict[str, int] | None:
    return record_job_outcome(CRAWL_NAMESPACE, crawl_id, url, outcome)


def get_crawl_counters(crawl_id: str) -> dict[str, int] | None:
    return get_job_counters(CRAWL_NAMESPACE, crawl_id)


def mark_crawl_finalizing(crawl_id: str) -> bool:
    return mark_job_finalizing(CRAWL_NAMESPACE, crawl_id)


def clear_crawl_counters(crawl_id: str) -> None:
    clear_job_counters(CRAWL_NAMESPACE, crawl_id)
