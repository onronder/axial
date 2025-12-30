import hmac
import hashlib
import logging
from core.config import settings
from core.db import get_supabase
from services.team_service import team_service

logger = logging.getLogger(__name__)

class SubscriptionService:
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        if not settings.POLAR_WEBHOOK_SECRET:
            return True
        
        try:
            expected = hmac.new(
                settings.POLAR_WEBHOOK_SECRET.encode(), payload, hashlib.sha256
            ).hexdigest()
            
            # Check both formats (with and without prefix) to be safe
            return hmac.compare_digest(f"whsec_{expected}", signature) or \
                   hmac.compare_digest(expected, signature)
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
            return

        if event_type in ["subscription.created", "subscription.updated", "subscription.active"]:
            product_id = body.get("product_id")
            plan = settings.POLAR_PRODUCT_MAPPING.get(product_id, "free")
            
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

        elif event_type in ["subscription.canceled", "subscription.revoked"]:
            supabase = get_supabase()
            supabase.table("subscriptions").update({
                "status": "canceled"
            }).eq("team_id", team_id).execute()
            
            team_service.invalidate_plan_cache(team_id)
            logger.info(f"Team {team_id} subscription canceled")

subscription_service = SubscriptionService()
