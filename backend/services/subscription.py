import hmac
import hashlib
import base64
import logging
from typing import Dict, Any, Optional

from core.config import settings
from core.db import get_supabase
from services.team_service import team_service

logger = logging.getLogger(__name__)

class SubscriptionService:
    """
    Handles subscription logic via Polar.sh webhooks.
    """

    def verify_signature(
        self, 
        payload: bytes, 
        header: str, 
        secret: str, 
        timestamp: Optional[str] = None, 
        msg_id: Optional[str] = None
    ) -> bool:
        """
        Verifies Standard Webhooks (Svix style).
        Header format expected: "v1,signature_base64"
        """
        try:
            if not header or not secret:
                return False

            # 1. Extract Signature from Header
            # Header is usually "v1,gH7..." or multiple "v1,sig1 v1,sig2"
            provided_sig = None
            
            # Try splitting by space for multiple signatures
            parts = header.split(" ")
            for part in parts:
                if part.startswith("v1,"):
                    provided_sig = part.split(",", 1)[1]
                    break
            
            if not provided_sig:
                logger.error(f"[Webhook Verify] Could not extract v1 signature from: {header}")
                return False

            # 2. Validate Timestamp
            if not timestamp:
                logger.error("[Webhook Verify] No timestamp provided in headers.")
                return False

            # 3. Construct Candidates for Signing
            # Standard Webhooks can be signed as: "msgId.timestamp.payload" (Svix Spec)
            # Or sometimes: "timestamp.payload"
            # We try both to be robust.
            messages_to_try = []
            
            # Format A: msgId.timestamp.payload (Strict Svix)
            if msg_id:
                msg_a = f"{msg_id}.{timestamp}.".encode("utf-8") + payload
                messages_to_try.append(msg_a)
            
            # Format B: timestamp.payload (Common fallback)
            msg_b = f"{timestamp}.".encode("utf-8") + payload
            messages_to_try.append(msg_b)

            # 4. Prepare Secret Candidates
            # The secret might be Base64 encoded (standard) or raw
            secret_candidates = []
            
            # Base64 Decode
            try:
                secret_candidates.append(("Base64", base64.b64decode(secret)))
            except:
                pass
            
            # Raw Bytes
            secret_candidates.append(("Raw", secret.encode("utf-8")))

            # Whsec prefix handling (strip 'whsec_' and decode)
            if secret.startswith("whsec_"):
                try:
                    stripped = secret.replace("whsec_", "")
                    secret_candidates.append(("Whsec_Base64", base64.b64decode(stripped)))
                except:
                    pass

            # 5. Brute-Force Verify
            for msg_bytes in messages_to_try:
                for key_name, key_bytes in secret_candidates:
                    try:
                        mac = hmac.new(key_bytes, msg_bytes, hashlib.sha256)
                        computed = base64.b64encode(mac.digest()).decode("utf-8")
                        
                        if hmac.compare_digest(computed, provided_sig):
                            logger.info(f"[Webhook Verify] ✅ Signature Verified! (Key: {key_name})")
                            return True
                    except Exception:
                        continue

            logger.warning(
                f"[Webhook Verify] Failed. TS={timestamp}, Sig={provided_sig[:10]}... "
                f"Tried {len(messages_to_try)} msg formats & {len(secret_candidates)} key formats."
            )
            return False

        except Exception as e:
            logger.error(f"[Webhook Verify] Fatal Error: {e}")
            return False

    async def handle_webhook(self, event_data: Dict[str, Any]):
        """
        Process the validated webhook event.
        """
        try:
            event_type = event_data.get("type")
            data = event_data.get("data", {})
            
            logger.info(f"📨 [SubscriptionService] Processing event: {event_type}")

            if event_type == "subscription.created":
                await self._handle_subscription_created(data)
            elif event_type == "subscription.updated":
                await self._handle_subscription_updated(data)
            elif event_type == "subscription.active":
                await self._handle_subscription_updated(data)
            elif event_type == "subscription.uncanceled":
                await self._handle_subscription_updated(data)
            elif event_type == "subscription.canceled":
                await self._handle_subscription_canceled(data)
            elif event_type == "subscription.revoked":
                await self._handle_subscription_revoked(data)
            else:
                logger.info(f"ℹ️ [SubscriptionService] Ignored event type: {event_type}")
        except Exception as e:
             logger.error(f"❌ [SubscriptionService] Logic Error: {e}")
    
    async def _handle_subscription_created(self, data: Dict[str, Any]):
        await self._upsert_subscription(data)
        
    async def _handle_subscription_updated(self, data: Dict[str, Any]):
        await self._upsert_subscription(data)

    async def _handle_subscription_canceled(self, data: Dict[str, Any]):
        await self._cancel_subscription(data, "canceled")
        
    async def _handle_subscription_revoked(self, data: Dict[str, Any]):
        await self._cancel_subscription(data, "revoked")

    async def _upsert_subscription(self, body: Dict[str, Any]):
        # Safe extraction of team_id from different possible locations
        metadata = body.get("metadata") or body.get("checkout", {}).get("metadata") or {}
        team_id = metadata.get("team_id")
        
        if not team_id:
            logger.warning("[SubscriptionService] No team_id in metadata, ignoring upsert.")
            return

        product_id = body.get("product_id")
        
        mapping = settings.POLAR_PRODUCT_MAPPING if hasattr(settings, 'POLAR_PRODUCT_MAPPING') else {}
        plan = mapping.get(product_id)
        
        if not plan:
            # IMPORTANT: Do not default to "free". If we don't recognize the product, ignore it.
            logger.warning(f"Webhook Product ID {product_id} not found in configuration mapping. Ignored.")
            return
        
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

    async def _cancel_subscription(self, body: Dict[str, Any], action: str):
        metadata = body.get("metadata") or body.get("checkout", {}).get("metadata") or {}
        team_id = metadata.get("team_id")
        
        if not team_id:
             logger.warning(f"[SubscriptionService] No team_id in metadata, ignoring {action}.")
             return

        supabase = get_supabase()
        supabase.table("subscriptions").update({
            "status": "canceled"
        }).eq("team_id", team_id).execute()
        
        team_service.invalidate_plan_cache(team_id)
        logger.info(f"Team {team_id} subscription {action}")

# Singleton instance
subscription_service = SubscriptionService()
