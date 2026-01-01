import hmac
import hashlib
import base64
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from core.config import settings
from core.db import get_supabase
from services.team_service import team_service

logger = logging.getLogger(__name__)

class SubscriptionService:
    """
    Handles subscription logic via Polar.sh webhooks.
    """

    def verify_signature(self, payload: bytes, header: str, secret: str) -> bool:
        """
        Verifies the Polar webhook signature.
        Includes extensive logging and multi-format secret trial to resolve 401 errors.
        """
        try:
            # 1. Extensive Debug Logging
            # SECURITY WARNING: masking part of the secret for logs
            safe_secret_preview = secret[:5] + "..." if secret else "None"
            logger.info(f"🔍 [Webhook Debug] Incoming Header: '{header}'")
            logger.info(f"🔍 [Webhook Debug] Payload Length: {len(payload)} bytes")
            logger.info(f"🔍 [Webhook Debug] Secret Preview: {safe_secret_preview}")

            if not header or not secret:
                logger.error("❌ [Webhook Verify] Missing header or secret configuration.")
                return False

            # 2. Parse Header (Standard Webhook Format: t=TIMESTAMP,v1=SIGNATURE)
            pairs = {}
            try:
                for part in header.split(","):
                    if "=" in part:
                        k, v = part.split("=", 1)
                        pairs[k.strip()] = v.strip()
            except Exception as e:
                logger.error(f"❌ [Webhook Verify] Failed to parse header string: {e}")
                return False

            timestamp = pairs.get("t")
            signature = pairs.get("v1")

            if not timestamp or not signature:
                logger.error(f"❌ [Webhook Verify] Missing 't' or 'v1' in header. Parsed: {pairs}")
                return False

            # 3. Construct Message (timestamp + "." + raw_payload)
            # Ensure timestamp is bytes
            to_sign = f"{timestamp}.".encode("utf-8") + payload

            # 4. Prepare Candidate Secrets
            # We try multiple formats because env vars often get copy-pasted differently
            candidate_keys = []

            # Method A: Base64 Decoded (Standard Spec)
            try:
                decoded = base64.b64decode(secret)
                candidate_keys.append(("Base64_Decoded", decoded))
            except:
                pass
            
            # Method B: Raw UTF-8 (Fallback)
            candidate_keys.append(("Raw_String", secret.encode("utf-8")))

            # Method C: 'whsec_' Prefix Handling (Common in some setups)
            if secret.startswith("whsec_"):
                try:
                    stripped = secret.replace("whsec_", "")
                    decoded_stripped = base64.b64decode(stripped)
                    candidate_keys.append(("Whsec_Stripped_Base64", decoded_stripped))
                except:
                    pass

            # 5. Brute-force Verification
            for key_name, key_bytes in candidate_keys:
                try:
                    mac = hmac.new(key_bytes, to_sign, hashlib.sha256)
                    computed_sig = base64.b64encode(mac.digest()).decode("utf-8")

                    if hmac.compare_digest(computed_sig, signature):
                        logger.info(f"✅ [Webhook Verify] SUCCESS! Matched using '{key_name}' logic.")
                        return True
                    else:
                        # Log mismatched for debugging (only showing first 10 chars to avoid log spam)
                        logger.debug(f"⚠️ [Webhook Verify] Failed {key_name}. Computed: {computed_sig[:10]}... != Expected: {signature[:10]}...")
                except Exception as e:
                    logger.warning(f"⚠️ [Webhook Verify] Error checking {key_name}: {e}")

            logger.error("❌ [Webhook Verify] All signature verification attempts failed.")
            return False

        except Exception as e:
            logger.error(f"❌ [Webhook Verify] Fatal Code Error: {e}")
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
                await self._handle_subscription_updated(data) # Treat active as updated
            elif event_type == "subscription.uncanceled":
                await self._handle_subscription_updated(data) # Treat uncanceled as updated
            elif event_type == "subscription.canceled":
                await self._handle_subscription_canceled(data)
            elif event_type == "subscription.revoked":
                await self._handle_subscription_revoked(data)
            else:
                logger.info(f"ℹ️ [SubscriptionService] Unhandled event type: {event_type}")
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
        # Logic extracted from previous implementation
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
        # Logic extracted from previous implementation
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
