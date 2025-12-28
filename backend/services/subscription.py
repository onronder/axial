"""
Subscription Service

Handles Polar.sh webhook events for subscription management.
Implements strict product filtering to ignore events from unrelated products.

Key Features:
- HMAC-SHA256 signature verification
- Product ID filtering (only processes Axio Hub products)
- Plan updates with cache invalidation
- Graceful handling of unknown products (ignore, don't crash)
"""

import hmac
import hashlib
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from core.config import settings, get_polar_product_mapping
from core.db import get_supabase
from services.team_service import team_service

logger = logging.getLogger(__name__)


class SubscriptionService:
    """
    Service for handling Polar.sh subscription webhooks.
    
    Implements strict filtering to only process events for
    Axio Hub products, ignoring all others.
    """
    
    def __init__(self):
        self.webhook_secret = settings.POLAR_WEBHOOK_SECRET
    
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify Polar webhook signature using HMAC-SHA256.
        
        Args:
            payload: Raw request body bytes
            signature: Signature from polar-webhook-signature header
            
        Returns:
            True if signature is valid, False otherwise
        """
        if not self.webhook_secret:
            logger.warning("[Subscription] No webhook secret configured, skipping verification")
            return True  # Skip verification in development
        
        try:
            # Compute expected signature
            expected = hmac.new(
                self.webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures (timing-safe comparison)
            return hmac.compare_digest(expected, signature)
            
        except Exception as e:
            logger.error(f"[Subscription] Signature verification failed: {e}")
            return False
    
    def _extract_product_id(self, payload: dict) -> Optional[str]:
        """
        Extract product_id from webhook payload.
        
        Polar.sh payloads can have product_id in different locations
        depending on the event type.
        """
        data = payload.get("data", {})
        
        # Try common locations
        product_id = data.get("product_id")
        
        if not product_id:
            # Try nested in product object
            product = data.get("product", {})
            product_id = product.get("id")
        
        if not product_id:
            # Try in attributes (some event types)
            attributes = data.get("attributes", {})
            product_id = attributes.get("product_id")
        
        return product_id
    
    def _extract_user_identifier(self, payload: dict) -> tuple[Optional[str], Optional[str]]:
        """
        Extract user identifier from webhook payload.
        
        Returns:
            Tuple of (user_id, email) - at least one should be present
        """
        data = payload.get("data", {})
        
        # Try to get user_id from metadata
        metadata = data.get("metadata", {})
        user_id = metadata.get("user_id")
        
        # Get email from customer info
        customer = data.get("customer", {})
        email = customer.get("email")
        
        if not email:
            # Try nested in user object
            user = data.get("user", {})
            email = user.get("email")
        
        return user_id, email
    
    async def handle_webhook_event(
        self, 
        payload: bytes,
        signature: str,
        parsed_payload: dict
    ) -> Dict[str, Any]:
        """
        Process a Polar.sh webhook event.
        
        Implements strict filtering - only processes events for
        configured Axio Hub products. Unknown products are ignored.
        
        Args:
            payload: Raw request body bytes
            signature: polar-webhook-signature header value
            parsed_payload: Parsed JSON payload
            
        Returns:
            Dict with processing status
            
        Raises:
            ValueError: If signature verification fails
        """
        # Step 1: Verify Signature
        if signature and not self.verify_signature(payload, signature):
            logger.warning("[Subscription] Invalid webhook signature")
            raise ValueError("Invalid webhook signature")
        
        event_type = parsed_payload.get("type", "unknown")
        logger.info(f"[Subscription] Processing event: {event_type}")
        
        # Step 2: Extract and Filter by Product ID
        product_id = self._extract_product_id(parsed_payload)
        product_mapping = get_polar_product_mapping()
        
        if not product_id:
            logger.info("[Subscription] No product_id in event, ignoring")
            return {"status": "ignored", "reason": "no_product_id"}
        
        if product_id not in product_mapping:
            logger.info(f"[Subscription] Ignoring webhook for unrelated product: {product_id}")
            return {"status": "ignored", "reason": "unrelated_product", "product_id": product_id}
        
        # Product is ours - determine the plan
        new_plan = product_mapping[product_id]
        logger.info(f"[Subscription] Processing for Axio Hub product: {product_id} -> {new_plan}")
        
        # Step 3: Process Based on Event Type
        if event_type in ["subscription.created", "subscription.updated", "subscription.active"]:
            return await self._handle_subscription_active(parsed_payload, new_plan)
        
        elif event_type in ["subscription.canceled", "subscription.revoked"]:
            return await self._handle_subscription_canceled(parsed_payload)
        
        elif event_type == "checkout.created":
            # Checkout started - no action needed yet
            logger.info("[Subscription] Checkout created, waiting for completion")
            return {"status": "acknowledged", "event": event_type}
        
        elif event_type == "order.created":
            # Order created - treat like subscription activation for one-time purchases
            return await self._handle_subscription_active(parsed_payload, new_plan)
        
        else:
            logger.info(f"[Subscription] Unhandled event type: {event_type}")
            return {"status": "ignored", "reason": "unhandled_event", "event": event_type}
    
    async def _handle_subscription_active(
        self, 
        payload: dict, 
        new_plan: str
    ) -> Dict[str, Any]:
        """
        Handle subscription activation/update.
        
        Updates user's plan and invalidates cache.
        """
        user_id, email = self._extract_user_identifier(payload)
        
        if not user_id and not email:
            logger.warning("[Subscription] No user identifier in payload")
            return {"status": "error", "reason": "no_user_identifier"}
        
        try:
            supabase = get_supabase()
            data = payload.get("data", {})
            
            # Find user by ID or email
            if user_id:
                profile_response = supabase.table("user_profiles").select(
                    "user_id, plan"
                ).eq("user_id", user_id).single().execute()
            else:
                # Lookup by email through auth.users (need to use service role)
                # For now, try to find in user_profiles by querying with email pattern
                # This is a simplification - in production, use auth.users lookup
                logger.info(f"[Subscription] Looking up user by email: {email}")
                return {"status": "error", "reason": "email_lookup_not_implemented"}
            
            if not profile_response.data:
                logger.warning(f"[Subscription] User not found: {user_id or email}")
                return {"status": "error", "reason": "user_not_found"}
            
            current_plan = profile_response.data.get("plan", "free")
            actual_user_id = profile_response.data.get("user_id")
            
            # Update the user's plan
            subscription_id = data.get("id") or data.get("subscription_id")
            
            # Determine subscription status from Polar
            # Polar sends status in the data object
            polar_status = data.get("status", "active")
            
            # Map Polar status to our status
            if polar_status == "trialing":
                subscription_status = "trialing"
            elif polar_status in ["active", "incomplete"]:
                subscription_status = "active"
            else:
                subscription_status = "active"  # Default to active for subscription events
            
            update_data = {
                "plan": new_plan,
                "subscription_status": subscription_status,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            supabase.table("user_profiles").update(
                update_data
            ).eq("user_id", actual_user_id).execute()
            
            logger.info(f"[Subscription] Upgraded user {actual_user_id[:8]}... from {current_plan} to {new_plan}")
            
            # CRITICAL: Invalidate plan cache for the user AND their team members
            team_service.invalidate_plan_cache(actual_user_id)
            
            # Also invalidate cache for all team members (they inherit owner's plan)
            await self._invalidate_team_member_caches(actual_user_id)
            
            return {
                "status": "processed",
                "action": "plan_upgraded",
                "user_id": actual_user_id,
                "old_plan": current_plan,
                "new_plan": new_plan
            }
            
        except Exception as e:
            logger.error(f"[Subscription] Failed to process activation: {e}")
            return {"status": "error", "reason": str(e)}
    
    async def _handle_subscription_canceled(self, payload: dict) -> Dict[str, Any]:
        """
        Handle subscription cancellation.
        
        Updates status to 'canceled' but doesn't immediately downgrade.
        User keeps access until billing period ends.
        """
        user_id, email = self._extract_user_identifier(payload)
        
        if not user_id:
            logger.warning("[Subscription] No user_id in cancellation payload")
            return {"status": "error", "reason": "no_user_id"}
        
        try:
            supabase = get_supabase()
            
            # Update subscription status
            supabase.table("user_profiles").update({
                "subscription_status": "canceled",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("user_id", user_id).execute()
            
            logger.info(f"[Subscription] Subscription canceled for user {user_id[:8]}...")
            
            # Note: Don't downgrade immediately - user has access until period ends
            # A separate job should handle downgrades at period end
            
            return {
                "status": "processed",
                "action": "subscription_canceled",
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"[Subscription] Failed to process cancellation: {e}")
            return {"status": "error", "reason": str(e)}
    
    async def _invalidate_team_member_caches(self, owner_id: str) -> None:
        """
        Invalidate plan cache for all team members.
        
        When an owner's plan changes, all team members inherit the new plan,
        so we need to invalidate their cached plans.
        """
        try:
            supabase = get_supabase()
            
            # Get owner's team
            team_response = supabase.table("teams").select(
                "id"
            ).eq("owner_id", owner_id).single().execute()
            
            if not team_response.data:
                return
            
            team_id = team_response.data.get("id")
            
            # Get all team members
            members_response = supabase.table("team_members").select(
                "member_user_id"
            ).eq("team_id", team_id).neq("member_user_id", owner_id).execute()
            
            if members_response.data:
                for member in members_response.data:
                    member_id = member.get("member_user_id")
                    if member_id:
                        team_service.invalidate_plan_cache(member_id)
                        
                logger.info(f"[Subscription] Invalidated cache for {len(members_response.data)} team members")
                
        except Exception as e:
            logger.warning(f"[Subscription] Failed to invalidate team caches: {e}")


# Singleton instance
subscription_service = SubscriptionService()
