"""
Webhooks API Router

Handles incoming webhooks from payment providers.
Currently supports Polar.sh for subscription management.
"""

import logging
from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel
from typing import Optional
import json

from services.subscription import subscription_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================
# MODELS
# ============================================================

class WebhookResponse(BaseModel):
    """Standard webhook response."""
    status: str
    message: Optional[str] = None
    details: Optional[dict] = None


# ============================================================
# POLAR.SH WEBHOOKS
# ============================================================

@router.post("/webhooks/polar", response_model=WebhookResponse)
async def handle_polar_webhook(request: Request):
    """
    Handle Polar.sh subscription webhooks.
    
    Processes subscription events with strict product filtering.
    Only events for configured Axio Hub products are processed.
    Events for other products are acknowledged but ignored.
    
    Security:
    - Validates HMAC-SHA256 signature using robust Standard Webhooks logic
    - Returns 401 if signature is invalid
    
    Returns:
    - 200: Event processed or ignored (see status for details)
    - 401: Invalid signature
    - 500: Processing error
    """
    try:
        # 1. Get RAW Body Bytes (Critical for signature verification)
        payload_bytes = await request.body()
        
        # 2. Get Signature Header
        # Standard Webhooks usually puts everything in "webhook-signature" or "polar-webhook-signature"
        # We need the full header string explicitly for verification logic which parses t=... and v1=...
        webhook_signature = request.headers.get("webhook-signature") or request.headers.get("polar-webhook-signature")
        
        if not webhook_signature:
            logger.warning("[Webhooks] Missing webhook-signature header")
            # DEBUG: Log available headers to debug why it's missing
            logger.warning(f"Available headers: {list(request.headers.keys())}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Missing Webhook Signature"
            )

        # 3. Verify Signature
        is_valid = subscription_service.verify_signature(
            payload=payload_bytes,
            header=webhook_signature,
            secret=settings.POLAR_WEBHOOK_SECRET
        )

        if not is_valid:
            logger.warning("[Webhooks] Invalid signature from Polar")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid Webhook Signature"
            )

        # 4. Parse JSON only AFTER verification
        try:
            event_data = json.loads(payload_bytes)
        except json.JSONDecodeError:
            logger.error("[Webhooks] Failed to decode JSON from verified payload")
            raise HTTPException(status_code=400, detail="Invalid JSON format")
        
        logger.info(f"[Webhooks] Received Polar event: {event_data.get('type')}")

        # 5. Process the event
        result = await subscription_service.handle_webhook(data=event_data)

        # Handle different result statuses (map result dict to WebhookResponse)
        result_status = result.get("status", "unknown")
        
        if result_status == "processed":
            logger.info(f"[Webhooks] Event processed: {result}")
            return WebhookResponse(
                status="processed",
                message="Subscription updated successfully",
                details=result
            )
        elif result_status == "ignored":
            logger.info(f"[Webhooks] Event ignored: {result.get('reason')}")
            return WebhookResponse(
                status="ignored",
                message=f"Ignored:{result.get('reason')}",
                details=result
            )
        elif result_status == "error":
            logger.error(f"[Webhooks] Processing error: {result}")
            return WebhookResponse(
                status="error",
                message=result.get("reason", "Unknown error"),
                details=result
            )
        else:
            return WebhookResponse(
                status=result_status,
                message="Event handled",
                details=result
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Webhooks] Error processing Polar webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error"
        )


@router.get("/webhooks/health")
async def webhook_health():
    """
    Health check endpoint for webhook monitoring.
    
    Can be used to verify the webhook endpoint is accessible.
    """
    return {"status": "healthy", "service": "webhooks"}
