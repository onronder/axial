import logging
import json
import redis.asyncio as redis
from fastapi import APIRouter, Request, HTTPException, Header
from core.config import settings
from services.subscription import subscription_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/webhooks/polar")
async def polar_webhook(request: Request):
    """
    Handle Polar.sh webhooks.
    Supports Standard Webhooks (Svix) verification.
    """
    try:
        # 1. Get RAW Body Bytes (Critical for signature verification)
        payload_bytes = await request.body()
        
        # 2. Get Headers (Standard Webhooks / Svix Style)
        wh_signature = request.headers.get("webhook-signature")
        wh_timestamp = request.headers.get("webhook-timestamp")
        wh_id = request.headers.get("webhook-id")

        # Debug logs to verify we are getting the headers
        logger.info(f"[Webhooks] Headers: Sig={wh_signature}, TS={wh_timestamp}, ID={wh_id}")

        if not wh_signature:
            logger.warning("[Webhooks] Missing webhook-signature header")
            raise HTTPException(status_code=401, detail="Missing Signature")

        # ---------------------------------------------------------------------
        # IDEMPOTENCY CHECK (Redis)
        # Prevent double-processing of the same event
        # ---------------------------------------------------------------------
        if wh_id:
            try:
                redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
                idempotency_key = f"webhook:polar:{wh_id}"
                
                # Check if already processed
                if await redis_client.get(idempotency_key):
                    logger.info(f"[Webhooks] Idempotent success: {wh_id} already processed.")
                    await redis_client.close()
                    return {"status": "received", "idempotent": True}
                
            except Exception as e:
                # Log usage error but don't block processing if Redis fails?
                # For production grade, we might want to fail-open or fail-closed.
                # Here we log and proceed to ensure we don't drop webhooks just because Redis blipped,
                # relying on signature verification for security.
                logger.error(f"[Webhooks] Redis idempotency check failed: {e}")
                redis_client = None

        # 3. Verify Signature
        # We pass the separate timestamp and ID to the service
        is_valid = subscription_service.verify_signature(
            payload=payload_bytes,
            header=wh_signature,
            secret=settings.POLAR_WEBHOOK_SECRET,
            timestamp=wh_timestamp,
            msg_id=wh_id
        )

        if not is_valid:
            logger.warning("[Webhooks] Invalid signature from Polar")
            if redis_client: await redis_client.close()
            raise HTTPException(status_code=401, detail="Invalid Webhook Signature")

        # 4. Process Event
        event_data = json.loads(payload_bytes)
        logger.info(f"[Webhooks] Received Polar event: {event_data.get('type')}")
        
        await subscription_service.handle_webhook(event_data)

        # Mark as processed in Redis (24h TTL)
        if wh_id and redis_client:
            try:
                await redis_client.set(idempotency_key, "processed", ex=86400)
                await redis_client.close()
            except Exception as e:
                 logger.error(f"[Webhooks] Failed to set idempotency key: {e}")

        return {"status": "received"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Webhooks] Error processing Polar webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/webhooks/health")
async def webhook_health():
    """
    Health check endpoint for webhook monitoring.
    """
    return {"status": "healthy", "service": "webhooks"}
