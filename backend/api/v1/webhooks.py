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
    Handle Polar.sh webhooks (subscriptions, payments).
    Uses Standard Webhooks protocol verification.
    """
    try:
        # 1. Get RAW Body Bytes (Critical for signature verification)
        # We must read bytes before any JSON parsing
        payload_bytes = await request.body()
        
        # 2. Get Signature Header
        webhook_signature = request.headers.get("webhook-signature")
        if not webhook_signature:
            logger.warning("[Webhooks] Missing webhook-signature header")
            raise HTTPException(status_code=401, detail="Missing Webhook Signature")

        # 3. Verify Signature
        # Uses settings.POLAR_WEBHOOK_SECRET (now imported correctly)
        is_valid = subscription_service.verify_signature(
            payload=payload_bytes,
            header=webhook_signature,
            secret=settings.POLAR_WEBHOOK_SECRET
        )

        if not is_valid:
            logger.warning("[Webhooks] Invalid signature from Polar")
            raise HTTPException(status_code=401, detail="Invalid Webhook Signature")

        # 4. Parse JSON only AFTER verification passes
        event_data = json.loads(payload_bytes)
        
        logger.info(f"[Webhooks] Received Polar event: {event_data.get('type')}")

        # 5. Process the event
        await subscription_service.handle_webhook(event_data)

        return {"status": "received"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Webhooks] Error processing Polar webhook: {e}")
        # Return generic error to avoid leaking details
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/webhooks/health")
async def webhook_health():
    """
    Health check endpoint for webhook monitoring.
    
    Can be used to verify the webhook endpoint is accessible.
    """
    return {"status": "healthy", "service": "webhooks"}
