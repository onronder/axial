import hmac
import hashlib
import base64
import logging
from core.config import settings
from core.db import get_supabase
from services.team_service import team_service

logger = logging.getLogger(__name__)

class SubscriptionService:
    def verify_signature(self, payload: bytes, signature: str, timestamp: str = None, webhook_id: str = None) -> bool:
        secret = settings.POLAR_WEBHOOK_SECRET
        if not secret:
            logger.error("Verify Signature Failed: POLAR_WEBHOOK_SECRET is missing/empty")
            return False
        
        try:
            # 1. Parse the signature (strip 'v1,')
            if signature.startswith("v1,"):
                actual_signature = signature.split(",")[1]
            else:
                actual_signature = signature
            
            if not timestamp:
                logger.error("[Webhook] Missing timestamp for signature verification")
                return False

            # 2. Construct the message: timestamp + "." + raw_payload
            to_sign = f"{timestamp}.".encode("utf-8") + payload
            
            # 3. Prepare the secret (Try Base64 first, fallback to Raw)
            try:
                secret_bytes = base64.b64decode(secret)
            except Exception:
                secret_bytes = secret.encode("utf-8")

            # 4. Compute HMAC-SHA256
            mac = hmac.new(secret_bytes, to_sign, hashlib.sha256)
            computed_sig = base64.b64encode(mac.digest()).decode("utf-8")
            
            # Debug logging
            masked_secret = secret[:10] + "..." if secret and len(secret) > 10 else "SHORT"
            logger.info(
                f"[Webhook Debug] Secret='{masked_secret}', "
                f"PayloadLen={len(payload)}, "
                f"Timestamp='{timestamp}', "
                f"HeaderSig='{signature}', "
                f"ExtractedSig='{actual_signature}', "
                f"ComputedSig='{computed_sig}'"
            )
            
            # 5. Compare (Timing-safe)
            if hmac.compare_digest(computed_sig, actual_signature):
                return True
                
            # Fallback: Try verifying with raw secret bytes if base64 failed or vice-versa?
            # Actually, let's try computing with RAW secret if the first attempt failed
            # This covers the case where the secret LOOKS like base64 but is actually raw
            mac_raw = hmac.new(secret.encode("utf-8"), to_sign, hashlib.sha256)
            computed_sig_raw = base64.b64encode(mac_raw.digest()).decode("utf-8")
            
            if hmac.compare_digest(computed_sig_raw, actual_signature):
                logger.info("[Webhook DEBUG] Matched with RAW secret encoding")
                return True

            logger.warning(f"[Webhook Debug] Signature Mismatch!")
            return False
            
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False

    async def handle_webhook_event(self, payload: bytes, signature: str, data: dict, timestamp: str = None, webhook_id: str = None):
        if not self.verify_signature(payload, signature, timestamp, webhook_id):
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
