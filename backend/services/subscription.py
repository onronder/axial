import hmac
import hashlib
import base64
import logging
from core.config import settings
from core.db import get_supabase
from services.team_service import team_service

logger = logging.getLogger(__name__)

class SubscriptionService:
    def verify_signature(self, payload: bytes, header: str, secret: str) -> bool:
        """
        Verifies the Polar webhook signature using robust Standard Webhooks logic.
        
        The Standard Webhooks protocol (used by Polar) requires:
        1. The secret key to be Base64 decoded.
        2. The message to be "timestamp.raw_payload".
        3. HMAC-SHA256 hashing.
        """
        try:
            if not header or not secret:
                return False

            # 1. Parse the Header (e.g., "t=12345,v1=abcdef...")
            pairs = {}
            for part in header.split(","):
                if "=" in part:
                    k, v = part.split("=", 1)
                    pairs[k.strip()] = v.strip()

            timestamp = pairs.get("t")
            signature = pairs.get("v1")

            if not timestamp or not signature:
                logger.error("[Webhook] Missing timestamp or signature in header")
                return False

            # 2. Construct the Message
            # Format must be: <timestamp>.<raw_body>
            # payload MUST be the exact raw bytes from the request
            to_sign = f"{timestamp}.".encode("utf-8") + payload

            # 3. Determine the Secret Key Bytes
            # We try two approaches to be safe:
            # A) Base64 Decode (Standard approach for "whsec_..." keys)
            # B) Raw UTF-8 (Fallback if the secret is just a random string)
            candidate_keys = []
            
            try:
                candidate_keys.append(("Base64", base64.b64decode(secret)))
            except Exception:
                pass # Not valid base64
            
            candidate_keys.append(("Raw", secret.encode("utf-8")))

            # 4. Verify
            for key_name, key_bytes in candidate_keys:
                try:
                    mac = hmac.new(key_bytes, to_sign, hashlib.sha256)
                    computed_sig = base64.b64encode(mac.digest()).decode("utf-8")

                    if hmac.compare_digest(computed_sig, signature):
                        # Valid signature found
                        return True
                except Exception:
                    continue

            # 5. Log failure if no match found
            logger.warning(
                f"[Webhook] Signature Verification Failed.\n"
                f"Timestamp: {timestamp}\n"
                f"Provided Sig: {signature}\n"
                f"Computed Sig (using {candidate_keys[0][0]} method): {computed_sig if 'computed_sig' in locals() else 'N/A'}"
            )
            return False

        except Exception as e:
            logger.error(f"[Webhook] Verification Fatal Error: {e}")
            return False

    async def handle_webhook(self, data: dict):


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
