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
        expected = hmac.new(
            settings.POLAR_WEBHOOK_SECRET.encode(), payload, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest("whsec_" + expected, signature) or hmac.compare_digest(expected, signature)

    async def handle_webhook_event(self, payload: bytes, signature: str, data: dict):
        # 1. Verify
        if not self.verify_signature(payload, signature):
            raise ValueError("Invalid Signature")

        event_type = data.get("type")
        body = data.get("data", {})
        
        # 2. Extract Team ID from Metadata
        # Note: Structure depends on event. Checkouts carry metadata directly.
        # Subscriptions might need lookup or carry it if passed during checkout.
        team_id = body.get("metadata", {}).get("team_id")
        
        if not team_id:
            logger.warning(f"Webhook {event_type} missing team_id in metadata. Ignoring.")
            return

        # 3. Handle Events
        if event_type in ["subscription.created", "subscription.updated", "subscription.active"]:
            product_id = body.get("product_id")
            plan = settings.POLAR_PRODUCT_MAPPING.get(product_id, "free")
            
            supabase = get_supabase()
            supabase.table("subscriptions").upsert({
                "team_id": team_id,
                "polar_id": body.get("id"),
                "status": "active",
                "plan_type": plan,
                "seats": 1  # Logic to update seats if Pro
            }, on_conflict="team_id").execute()
            
            # 4. Invalidate Cache
            team_service.invalidate_plan_cache(team_id)
            logger.info(f"Team {team_id} upgraded to {plan}")

        elif event_type in ["subscription.canceled", "subscription.revoked"]:
            supabase = get_supabase()
            supabase.table("subscriptions").update({
                "status": "canceled"
            }).eq("team_id", team_id).execute()
            team_service.invalidate_plan_cache(team_id)

subscription_service = SubscriptionService()
