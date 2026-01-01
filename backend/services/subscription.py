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
        Verifies the Polar webhook signature using robust Standard Webhooks logic.
        Tries both Base64-decoded secret (Spec compliant) and Raw secret (Fallback).
        """
        try:
            if not header or not secret:
                return False

            # 1. Parse Header
            # Header format example: "t=12345,v1=abcdef..."
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

            # 2. Construct Message: timestamp + "." + payload
            # CRITICAL: Payload must be the exact raw bytes from the request body
            # Timestamp must be encoded to bytes
            to_sign = f"{timestamp}.".encode("utf-8") + payload

            # 3. Candidate Secrets (Try strict Base64 first, then Raw)
            candidate_keys = []
            
            # Option A: Base64 Decoded (Standard approach)
            try:
                decoded = base64.b64decode(secret)
                candidate_keys.append(("Base64", decoded))
            except Exception:
                pass

            # Option B: Raw String (If the provided secret is just a plain string)
            candidate_keys.append(("Raw", secret.encode("utf-8")))

            # 4. Verify against candidates
            for key_name, key_bytes in candidate_keys:
                try:
                    # Compute HMAC-SHA256
                    mac = hmac.new(key_bytes, to_sign, hashlib.sha256)
                    computed_sig = base64.b64encode(mac.digest()).decode("utf-8")

                    if hmac.compare_digest(computed_sig, signature):
                        logger.info(f"[Webhook] Signature Verified using {key_name} key logic.")
                        return True
                except Exception as e:
                    continue

            # 5. Debug Logging (Only if all failed)
            logger.warning(
                f"[Webhook] Signature Mismatch.\n"
                f"Timestamp: {timestamp}\n"
                f"Provided Sig: {signature}\n"
                f"Computed (last attempt): {computed_sig if 'computed_sig' in locals() else 'Error'}"
            )
            return False

        except Exception as e:
            logger.error(f"[Webhook] Verification Fatal Error: {e}")
            return False

    async def handle_webhook(self, event_data: Dict[str, Any]):
        """
        Process the validated webhook event.
        """
        event_type = event_data.get("type")
        data = event_data.get("data", {})
        
        logger.info(f"[SubscriptionService] Processing event: {event_type}")

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
            logger.info(f"[SubscriptionService] Ignored event type: {event_type}")
    
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
