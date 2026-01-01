import logging
import json
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
            raise HTTPException(status_code=401, detail="Invalid Webhook Signature")

        # 4. Process Event
        event_data = json.loads(payload_bytes)
        logger.info(f"[Webhooks] Received Polar event: {event_data.get('type')}")
        
        await subscription_service.handle_webhook(event_data)

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
