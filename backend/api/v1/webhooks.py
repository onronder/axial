"""
Webhooks API Router

Handles incoming webhooks from payment providers.
Currently supports Polar.sh for subscription management.
"""

import logging
from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel
from typing import Optional

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
    - Validates HMAC-SHA256 signature from polar-webhook-signature header
    - Returns 401 if signature is invalid
    
    Returns:
    - 200: Event processed or ignored (see status for details)
    - 401: Invalid signature
    - 500: Processing error
    """
    try:
        # Get raw body for signature verification
        raw_body = await request.body()
        
        # Get signature header (check both standard and Polar-specific names)
        signature = request.headers.get("polar-webhook-signature") or request.headers.get("webhook-signature", "")
        timestamp = request.headers.get("webhook-timestamp", "")
        webhook_id = request.headers.get("webhook-id", "")
        
        # DEBUG: Log headers to identify why signature might be missing
        if not signature:
            logger.warning(
                f"[Webhooks Debug] Missing 'polar-webhook-signature'. "
                f"Available Headers: {list(request.headers.keys())}"
            )
        
        # Parse JSON payload
        try:
            payload = await request.json()
        except Exception as e:
            logger.warning(f"[Webhooks] Invalid JSON payload: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload"
            )
        
        # Log incoming event (without sensitive data)
        event_type = payload.get("type", "unknown")
        logger.info(f"[Webhooks] Received Polar event: {event_type}")
        
        # Process the webhook
        result = await subscription_service.handle_webhook_event(
            payload=raw_body,
            signature=signature,
            data=payload,
            timestamp=timestamp,
            webhook_id=webhook_id
        )
        
        # Handle different result statuses
        result_status = result.get("status", "unknown")
        
        if result_status == "processed":
            logger.info(f"[Webhooks] Event processed: {result}")
            return WebhookResponse(
                status="processed",
                message="Subscription updated successfully",
                details=result
            )
        
        elif result_status == "ignored":
            reason = result.get("reason", "unknown")
            logger.info(f"[Webhooks] Event ignored: {reason}")
            return WebhookResponse(
                status="ignored",
                message=f"Event ignored: {reason}",
                details=result
            )
        
        elif result_status == "acknowledged":
            return WebhookResponse(
                status="acknowledged",
                message="Event received"
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
                details=result
            )
            
    except ValueError as e:
        # Signature verification failed
        logger.warning(f"[Webhooks] Signature verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )
        
    except Exception as e:
        logger.error(f"[Webhooks] Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )


@router.get("/webhooks/health")
async def webhook_health():
    """
    Health check endpoint for webhook monitoring.
    
    Can be used to verify the webhook endpoint is accessible.
    """
    return {"status": "healthy", "service": "webhooks"}
