import hmac
import hashlib
import base64
import logging
from typing import Dict, Any, Optional

from core.config import settings
from core.db import get_supabase
from services.team_service import team_service

logger = logging.getLogger(__name__)


def _check_webhook_idempotency(supabase, event_id: str, source: str, event_type: str = None) -> bool:
    """
    Check if webhook has already been processed using atomic database operation.
    
    Returns True if this is the first time seeing this event (should process).
    Returns False if already processed (should skip).
    
    RACE CONDITION FIX: Uses database RPC for atomic check-and-insert.
    """
    if not event_id:
        # No event_id means we can't deduplicate, process anyway
        logger.warning("⚠️ [Webhook] No event_id provided, skipping idempotency check")
        return True
    
    try:
        # Try atomic idempotency check via RPC
        result = supabase.rpc(
            "try_process_webhook",
            {
                "p_event_id": event_id,
                "p_source": source,
                "p_event_type": event_type,
            }
        ).execute()
        
        # RPC returns boolean - true if we should process, false if duplicate
        should_process = result.data if isinstance(result.data, bool) else True
        
        if not should_process:
            logger.info(f"🔄 [Webhook] Duplicate event detected: {event_id} from {source}")
        
        return should_process
        
    except Exception as exc:
        error_msg = str(exc)
        if "function" in error_msg.lower() and "does not exist" in error_msg.lower():
            # RPC doesn't exist yet (migration not applied), process anyway
            logger.warning("⚠️ [Webhook] try_process_webhook RPC not found, skipping idempotency check")
            return True
        
        # Other errors - log but don't block processing
        logger.error(f"❌ [Webhook] Idempotency check failed: {exc}")
        return True  # Fail open to avoid blocking legitimate events

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
        # RACE CONDITION FIX: Check idempotency first
        supabase = get_supabase()
        event_id = body.get("id")
        event_type = body.get("type", "subscription.upsert")
        
        if not _check_webhook_idempotency(supabase, event_id, "polar", event_type):
            logger.info(f"[SubscriptionService] Duplicate webhook {event_id}, skipping")
            return
        
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
        
        # Note: supabase already obtained at top of method for idempotency check
        
        # Logic: If Enterprise Product ID matches, force enterprise
        if product_id == settings.POLAR_PRODUCT_ID_ENTERPRISE:
            plan = "enterprise"

        # Extract customer_id from webhook data (needed for Customer Portal sessions)
        customer = body.get("customer", {})
        customer_id = customer.get("id") if isinstance(customer, dict) else None
        
        # ==========================================================================
        # SUBSCRIPTION STATUS HANDLING (Polar-Managed Billing)
        # ==========================================================================
        # Map Polar status to our internal status:
        # - "active" → "active" (full access)
        # - "trialing" → "active" (trial has full plan access until expiry)
        # - "past_due" → "active" (grace period, still has access)
        # - "canceled" → handled by _cancel_subscription
        # - "incomplete" → "pending" (payment not completed)
        # ==========================================================================
        polar_status = body.get("status", "active")
        internal_status = "active"
        
        if polar_status == "incomplete":
            internal_status = "pending"
            logger.info(f"[SubscriptionService] Subscription incomplete for team {team_id}, status=pending")
        elif polar_status == "trialing":
            # Trial has FULL plan access - this is critical for the trial experience
            internal_status = "active"
            logger.info(f"[SubscriptionService] Trial active for team {team_id}, granting {plan} access")
        
        # supabase already obtained at top of method for idempotency check
        supabase.table("subscriptions").upsert({
            "team_id": team_id,
            "polar_id": body.get("id"),
            "customer_id": customer_id,  # Store for Customer Portal API
            "status": internal_status,
            "plan_type": plan,
            "seats": 1  # Default to 1, future: body.get("quantity", 1)
        }, on_conflict="team_id").execute()
        
        # ALSO UPDATE user_profiles.plan for the team owner (keeps both tables in sync)
        # NOTE: subscription_status column was removed from user_profiles; status is tracked in subscriptions table
        owner_id = None
        try:
            team_response = supabase.table("teams").select("owner_id").eq("id", team_id).single().execute()
            if team_response.data and team_response.data.get("owner_id"):
                owner_id = team_response.data["owner_id"]
                supabase.table("user_profiles").update({
                    "plan": plan
                }).eq("user_id", owner_id).execute()
                logger.info(f"[SubscriptionService] Updated user_profiles.plan for owner {owner_id[:8]}... to {plan}")
        except Exception as e:
            logger.warning(f"[SubscriptionService] Failed to update user_profiles: {e}")
        
        # Invalidate cached plans for all team members (owner + members)
        try:
            member_rows = supabase.table("team_members").select(
                "member_user_id"
            ).eq("team_id", team_id).neq("status", "removed").execute()
            member_ids = {row.get("member_user_id") for row in (member_rows.data or []) if row.get("member_user_id")}
            if owner_id:
                member_ids.add(owner_id)
            for member_id in member_ids:
                team_service.invalidate_plan_cache(member_id)
        except Exception as e:
            logger.warning(f"[SubscriptionService] Failed to invalidate plan cache for team {team_id}: {e}")

        logger.info(f"SUCCESS: Team {team_id} plan updated to {plan}")

    async def _cancel_subscription(self, body: Dict[str, Any], action: str):
        """
        Handle subscription cancellation or revocation.
        
        CRITICAL: This is the enforcement point for the "Hard Zero" rule.
        When a subscription is canceled:
        1. Update subscriptions table status to "canceled"
        2. Update user_profiles.plan to "free" (max_scopes=0)
        3. Invalidate all plan caches
        
        This ensures that ALL ingestion stops immediately when a trial
        expires or payment fails.
        """
        metadata = body.get("metadata") or body.get("checkout", {}).get("metadata") or {}
        team_id = metadata.get("team_id")
        
        if not team_id:
             logger.warning(f"[SubscriptionService] No team_id in metadata, ignoring {action}.")
             return

        supabase = get_supabase()
        
        # Update subscriptions table
        supabase.table("subscriptions").update({
            "status": "canceled"
        }).eq("team_id", team_id).execute()
        
        # ==========================================================================
        # HARD ZERO ENFORCEMENT: Downgrade to "free" plan
        # ==========================================================================
        # When canceled, the team loses all plan privileges immediately.
        # The "free" plan has max_scopes=0, which blocks ALL ingestion.
        # NOTE: subscription_status column was removed from user_profiles; status is tracked in subscriptions table
        # ==========================================================================
        owner_id = None
        try:
            team_response = supabase.table("teams").select("owner_id").eq("id", team_id).single().execute()
            owner_id = team_response.data.get("owner_id") if team_response.data else None
            if owner_id:
                supabase.table("user_profiles").update({
                    "plan": "free"
                }).eq("user_id", owner_id).execute()
                logger.warning(
                    f"[SubscriptionService] Team {team_id[:8]}... downgraded to FREE plan. "
                    f"Action: {action}. Owner: {owner_id[:8]}..."
                )
        except Exception as e:
            logger.error(f"[SubscriptionService] Failed to downgrade plan for team {team_id}: {e}")

        # Invalidate cached plans for all team members (owner + members)
        try:
            member_rows = supabase.table("team_members").select(
                "member_user_id"
            ).eq("team_id", team_id).neq("status", "removed").execute()
            member_ids = {row.get("member_user_id") for row in (member_rows.data or []) if row.get("member_user_id")}
            if owner_id:
                member_ids.add(owner_id)
            for member_id in member_ids:
                team_service.invalidate_plan_cache(member_id)
        except Exception as e:
            logger.warning(f"[SubscriptionService] Failed to invalidate plan cache for team {team_id}: {e}")

        logger.info(f"Team {team_id} subscription {action} - plan downgraded to FREE")

# Singleton instance
subscription_service = SubscriptionService()
