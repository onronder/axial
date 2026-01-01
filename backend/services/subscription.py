import hmac
import hashlib
import base64
import logging
from core.config import settings
from core.db import get_supabase
from services.team_service import team_service

logger = logging.getLogger(__name__)

class SubscriptionService:
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        secret = settings.POLAR_WEBHOOK_SECRET
        if not secret:
            logger.error("Verify Signature Failed: POLAR_WEBHOOK_SECRET is missing/empty")
            return False
        
        try:
            # Compute Base64 Signature (Standard Polar v1)
            mac = hmac.new(secret.encode(), payload, hashlib.sha256)
            computed_base64 = base64.b64encode(mac.digest()).decode()
            expected_v1 = f"v1,{computed_base64}"
            
            # Compute Hex Signature (Legacy/Alternative)
            computed_hex = mac.hexdigest()
            expected_whsec = f"whsec_{computed_hex}"
            
            # Debug logging
            masked_secret = secret[:10] + "..." if secret and len(secret) > 10 else "SHORT"
            logger.info(
                f"[Webhook Debug] Secret='{masked_secret}', "
                f"PayloadLen={len(payload)}, "
                f"HeaderSig='{signature}', "
                f"ComputedV1='{expected_v1}', "
                f"ComputedWhsec='{expected_whsec}'"
            )
            
            # Check matches
            if hmac.compare_digest(expected_v1, signature):
                return True
            if hmac.compare_digest(expected_whsec, signature):
                return True
            if hmac.compare_digest(computed_hex, signature): # Check raw hex just in case
                return True
                   
            logger.warning(f"[Webhook Debug] Signature Mismatch!")
            return False
            
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False

    async def handle_webhook_event(self, payload: bytes, signature: str, data: dict):
        if not self.verify_signature(payload, signature):
            raise ValueError("Invalid Webhook Signature")

        event_type = data.get("type")
        body = data.get("data", {})
        
        # Safe extraction of team_id from different possible locations
        metadata = body.get("metadata") or body.get("checkout", {}).get("metadata") or {}
        team_id = metadata.get("team_id")
        
        logger.info(f"Webhook Received: {event_type} for Team: {team_id}")

        if not team_id:
            # Some events might not have team_id (like generic product updates), ignore them safely.
            return {"status": "ignored", "reason": "no team_id in metadata"}

        if event_type in ["subscription.created", "subscription.updated", "subscription.active", "subscription.uncanceled"]:
            product_id = body.get("product_id")
            
            mapping = settings.POLAR_PRODUCT_MAPPING if hasattr(settings, 'POLAR_PRODUCT_MAPPING') else {}
            plan = mapping.get(product_id)
            
            if not plan:
                # IMPORTANT: Do not default to "free". If we don't recognize the product, ignore it.
                # Defaulting to free would downgrade users who bought a valid but unconfigured product.
                logger.warning(f"Webhook Product ID {product_id} not found in configuration mapping. Ignored.")
                return {"status": "ignored", "reason": f"Unknown product_id {product_id}"}
            
            supabase = get_supabase()
            
            # Logic: If Enterprise Product ID matches, force enterprise
            if product_id == settings.POLAR_PRODUCT_ID_ENTERPRISE:
                plan = "enterprise"

            supabase.table("subscriptions").upsert({
                "team_id": team_id,
                "polar_id": body.get("id"),
                "status": "active",
                "plan_type": plan,
                "seats": 1  # Default to 1, future: body.get("quantity", 1)
            }, on_conflict="team_id").execute()
            
            team_service.invalidate_plan_cache(team_id)
            logger.info(f"SUCCESS: Team {team_id} plan updated to {plan}")
            return {"status": "processed", "team_id": team_id, "plan": plan}

        elif event_type in ["subscription.canceled", "subscription.revoked"]:
            supabase = get_supabase()
            supabase.table("subscriptions").update({
                "status": "canceled"
            }).eq("team_id", team_id).execute()
            
            team_service.invalidate_plan_cache(team_id)
            logger.info(f"Team {team_id} subscription canceled")
            return {"status": "processed", "team_id": team_id, "action": "canceled"}

        return {"status": "acknowledged", "event_type": event_type}

subscription_service = SubscriptionService()
