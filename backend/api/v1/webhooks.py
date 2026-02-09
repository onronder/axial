"""
Webhook Handlers - Production-Grade Implementation.

Features:
- Standard Webhooks (Svix) signature verification
- Redis-based idempotency with fail-closed behavior
- Dead Letter Queue (DLQ) for failed events
- Comprehensive error handling and logging
"""

import json
import logging
from datetime import datetime, timezone

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from api.v1.dependencies import require_admin
from core.config import settings
from core.db import get_supabase
from core.rate_limit import limiter
from services.subscription import subscription_service

router = APIRouter()
logger = logging.getLogger(__name__)


class WebhookDLQ:
    """
    Dead Letter Queue for webhook events that fail processing.
    Stores failed events in database for later retry.
    """

    @staticmethod
    def store_failed_event(
        event_id: str,
        event_type: str,
        payload: dict,
        error_message: str,
        source: str = "polar"
    ) -> bool:
        """
        Store a failed webhook event in the DLQ table.

        Args:
            event_id: Webhook event ID
            event_type: Type of event (e.g., subscription.created)
            payload: Full event payload
            error_message: Error message from failed processing
            source: Source of webhook (e.g., polar)

        Returns:
            True if stored successfully
        """
        try:
            supabase = get_supabase()

            dlq_entry = {
                "event_id": event_id,
                "event_type": event_type,
                "source": source,
                "payload": json.dumps(payload),
                "error_message": error_message[:2000],  # Truncate long errors
                "retry_count": 0,
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            supabase.table("webhook_dlq").upsert(
                dlq_entry,
                on_conflict="event_id,source"
            ).execute()

            logger.info(f"📥 [DLQ] Stored failed event: {event_id} ({event_type})")
            return True

        except Exception as e:
            logger.error(f"❌ [DLQ] Failed to store event {event_id}: {e}")
            return False

    @staticmethod
    async def retry_pending_events(max_events: int = 10) -> int:
        """
        Retry pending events from the DLQ.

        Args:
            max_events: Maximum number of events to retry

        Returns:
            Number of successfully processed events
        """
        try:
            supabase = get_supabase()

            # Get pending events with retry_count < 5
            result = supabase.table("webhook_dlq")\
                .select("*")\
                .eq("status", "pending")\
                .lt("retry_count", 5)\
                .order("created_at")\
                .limit(max_events)\
                .execute()

            if not result.data:
                return 0

            success_count = 0

            for event in result.data:
                try:
                    payload = json.loads(event["payload"])

                    # Attempt to process
                    await subscription_service.handle_webhook(payload)

                    # Mark as processed
                    supabase.table("webhook_dlq").update({
                        "status": "processed",
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }).eq("id", event["id"]).execute()

                    success_count += 1
                    logger.info(f"✅ [DLQ] Retry succeeded: {event['event_id']}")

                except Exception as e:
                    # Increment retry count
                    new_count = event["retry_count"] + 1
                    status = "failed" if new_count >= 5 else "pending"

                    supabase.table("webhook_dlq").update({
                        "retry_count": new_count,
                        "status": status,
                        "error_message": str(e)[:2000],
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }).eq("id", event["id"]).execute()

                    logger.warning(f"⚠️ [DLQ] Retry failed for {event['event_id']}: {e}")

            return success_count

        except Exception as e:
            logger.error(f"❌ [DLQ] Retry batch failed: {e}")
            return 0


async def check_idempotency(redis_client: redis.Redis, wh_id: str) -> tuple[bool, bool]:
    """
    Check if webhook has already been processed.

    Args:
        redis_client: Redis async client
        wh_id: Webhook ID

    Returns:
        Tuple of (is_duplicate, redis_available)
    """
    try:
        idempotency_key = f"webhook:polar:{wh_id}"
        if await redis_client.get(idempotency_key):
            return True, True
        return False, True
    except Exception as e:
        logger.error(f"[Webhooks] Redis check failed: {e}")
        return False, False


async def mark_processed(redis_client: redis.Redis, wh_id: str) -> bool:
    """
    Mark webhook as processed in Redis.

    Args:
        redis_client: Redis async client
        wh_id: Webhook ID

    Returns:
        True if successfully marked
    """
    try:
        idempotency_key = f"webhook:polar:{wh_id}"
        await redis_client.set(idempotency_key, "processed", ex=86400)  # 24h TTL
        return True
    except Exception as e:
        logger.error(f"[Webhooks] Failed to set idempotency key: {e}")
        return False


@router.post("/webhooks/polar")
async def polar_webhook(request: Request):
    """
    Handle Polar.sh webhooks with production-grade reliability.

    Security:
    - Standard Webhooks (Svix) signature verification
    - Fail-closed behavior for Redis failures
    - Idempotency guarantees

    Reliability:
    - Dead Letter Queue for failed events
    - Automatic retry mechanism
    """
    redis_client: redis.Redis | None = None
    wh_id: str | None = None
    event_data: dict | None = None

    try:
        # 1. Get RAW Body Bytes (Critical for signature verification)
        payload_bytes = await request.body()

        # 2. Get Headers (Standard Webhooks / Svix Style)
        wh_signature = request.headers.get("webhook-signature")
        wh_timestamp = request.headers.get("webhook-timestamp")
        wh_id = request.headers.get("webhook-id")

        logger.info(f"[Webhooks] Polar webhook received: ID={wh_id}, TS={wh_timestamp}")

        if not wh_signature:
            logger.warning("[Webhooks] Missing webhook-signature header")
            raise HTTPException(status_code=401, detail="Missing Signature")

        # ---------------------------------------------------------------------
        # IDEMPOTENCY CHECK (Redis) - FAIL-CLOSED
        # If Redis is unavailable, reject the webhook to prevent duplicates.
        # The webhook sender (Polar) will retry later.
        # ---------------------------------------------------------------------
        if wh_id:
            try:
                redis_client = redis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_timeout=5.0,
                    socket_connect_timeout=5.0
                )

                is_duplicate, redis_available = await check_idempotency(redis_client, wh_id)

                if not redis_available:
                    # FAIL-CLOSED: Redis unavailable, return 503 so Polar retries
                    logger.error("[Webhooks] Redis unavailable - returning 503 for retry")
                    raise HTTPException(
                        status_code=503,
                        detail="Service temporarily unavailable - please retry"
                    )

                if is_duplicate:
                    logger.info(f"[Webhooks] Idempotent success: {wh_id} already processed.")
                    await redis_client.aclose()
                    return {"status": "received", "idempotent": True}

            except HTTPException:
                raise
            except redis.ConnectionError as e:
                # FAIL-CLOSED: Connection error, return 503
                logger.error(f"[Webhooks] Redis connection error: {e}")
                raise HTTPException(
                    status_code=503,
                    detail="Service temporarily unavailable - please retry"
                )
            except Exception as e:
                logger.error(f"[Webhooks] Redis idempotency check failed: {e}")
                raise HTTPException(
                    status_code=503,
                    detail="Service temporarily unavailable - please retry"
                )

        # 3. Verify Signature
        is_valid = subscription_service.verify_signature(
            payload=payload_bytes,
            header=wh_signature,
            secret=settings.POLAR_WEBHOOK_SECRET,
            timestamp=wh_timestamp,
            msg_id=wh_id
        )

        if not is_valid:
            logger.warning("[Webhooks] Invalid signature from Polar")
            if redis_client:
                await redis_client.aclose()
            raise HTTPException(status_code=401, detail="Invalid Webhook Signature")

        # 4. Parse Event
        event_data = json.loads(payload_bytes)
        event_type = event_data.get('type', 'unknown')
        logger.info(f"[Webhooks] Processing Polar event: {event_type}")

        # 5. Process Event
        try:
            await subscription_service.handle_webhook(event_data)
        except Exception as process_error:
            # Processing failed - store in DLQ for retry
            logger.error(f"[Webhooks] Event processing failed: {process_error}")

            if wh_id and event_data:
                WebhookDLQ.store_failed_event(
                    event_id=wh_id,
                    event_type=event_type,
                    payload=event_data,
                    error_message=str(process_error),
                    source="polar"
                )

            # Still mark as "received" in Redis to prevent duplicate processing attempts
            # The DLQ will handle retries
            if wh_id and redis_client:
                await mark_processed(redis_client, wh_id)
                await redis_client.aclose()

            # Return 200 to acknowledge receipt - DLQ handles retry
            return {"status": "received", "queued_for_retry": True}

        # 6. Mark as processed in Redis
        if wh_id and redis_client:
            await mark_processed(redis_client, wh_id)
            await redis_client.aclose()

        return {"status": "received"}

    except HTTPException:
        if redis_client:
            try:
                await redis_client.aclose()
            except Exception as cleanup_err:
                logger.debug(f"[Webhooks] Failed to close Redis client: {cleanup_err}")
        raise
    except Exception as e:
        if redis_client:
            try:
                await redis_client.aclose()
            except Exception as cleanup_err:
                logger.debug(f"[Webhooks] Failed to close Redis client: {cleanup_err}")
        logger.error(f"[Webhooks] Unexpected error processing Polar webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/webhooks/dlq/retry")
@limiter.limit("5/minute")
async def retry_dlq_events(request: Request, max_events: int = Query(default=10, ge=1, le=100), _: str = Depends(require_admin)):
    """
    Manually trigger DLQ retry for failed webhook events.

    This endpoint can be called by a cron job or admin.
    Requires admin authentication.
    """
    count = await WebhookDLQ.retry_pending_events(max_events)
    return {"status": "ok", "processed": count}


@router.get("/webhooks/dlq/stats")
async def dlq_stats(_: str = Depends(require_admin)):
    """
    Get DLQ statistics for monitoring.

    Requires admin authentication.
    """
    try:
        supabase = get_supabase()

        # Count by status
        pending = supabase.table("webhook_dlq")\
            .select("id", count="exact")\
            .eq("status", "pending")\
            .execute()

        failed = supabase.table("webhook_dlq")\
            .select("id", count="exact")\
            .eq("status", "failed")\
            .execute()

        processed = supabase.table("webhook_dlq")\
            .select("id", count="exact")\
            .eq("status", "processed")\
            .execute()

        return {
            "pending": pending.count or 0,
            "failed": failed.count or 0,
            "processed": processed.count or 0
        }
    except Exception as e:
        logger.error(f"[DLQ] Failed to get stats: {e}")
        return {"pending": 0, "failed": 0, "processed": 0, "error": str(e)}


@router.get("/webhooks/health")
async def webhook_health():
    """
    Health check endpoint for webhook monitoring.
    Checks Redis connectivity.
    """
    redis_status = "unknown"

    try:
        redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=2.0,
            socket_connect_timeout=2.0
        )
        await redis_client.ping()
        redis_status = "healthy"
        await redis_client.aclose()
    except Exception as e:
        redis_status = f"unhealthy: {str(e)[:100]}"

    return {
        "status": "healthy" if redis_status == "healthy" else "degraded",
        "service": "webhooks",
        "redis": redis_status
    }
