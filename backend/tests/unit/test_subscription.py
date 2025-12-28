"""
Test Suite for Subscription Service

Production-grade tests for:
- Webhook signature verification
- Product filtering (ignore unrelated products)
- Plan upgrade/downgrade flow
- Cache invalidation
"""

import pytest
import hmac
import hashlib
from unittest.mock import patch, Mock, AsyncMock

from core.quotas import PLANS


# Test UUIDs
OWNER_UUID = "11111111-1111-1111-1111-111111111111"
PRODUCT_STARTER_ID = "starter-product-uuid"
PRODUCT_PRO_ID = "pro-product-uuid"
PRODUCT_ENTERPRISE_ID = "enterprise-product-uuid"
UNRELATED_PRODUCT_ID = "other-product-uuid"


class TestSignatureVerification:
    """Tests for HMAC signature verification."""
    
    @pytest.fixture
    def subscription_service(self):
        from services.subscription import SubscriptionService
        service = SubscriptionService()
        service.webhook_secret = "test-secret-key"
        return service
    
    @pytest.mark.unit
    def test_valid_signature_passes(self, subscription_service):
        """Valid HMAC-SHA256 signature should pass verification."""
        payload = b'{"type": "subscription.created"}'
        
        # Compute correct signature
        signature = hmac.new(
            b"test-secret-key",
            payload,
            hashlib.sha256
        ).hexdigest()
        
        assert subscription_service.verify_signature(payload, signature) is True
    
    @pytest.mark.unit
    def test_invalid_signature_fails(self, subscription_service):
        """Invalid signature should fail verification."""
        payload = b'{"type": "subscription.created"}'
        bad_signature = "invalid-signature"
        
        assert subscription_service.verify_signature(payload, bad_signature) is False
    
    @pytest.mark.unit
    def test_no_secret_skips_verification(self):
        """When no secret is configured, verification should pass (dev mode)."""
        from services.subscription import SubscriptionService
        service = SubscriptionService()
        service.webhook_secret = None
        
        assert service.verify_signature(b"payload", "") is True


class TestProductFiltering:
    """Tests for strict product filtering."""
    
    @pytest.fixture
    def subscription_service(self):
        from services.subscription import SubscriptionService
        return SubscriptionService()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unrelated_product_is_ignored(self, subscription_service):
        """Events for unrelated products should be ignored gracefully."""
        payload = {
            "type": "subscription.created",
            "data": {
                "product_id": UNRELATED_PRODUCT_ID
            }
        }
        
        # Mock empty product mapping
        with patch("services.subscription.get_polar_product_mapping", return_value={}):
            result = await subscription_service.handle_webhook_event(
                payload=b"{}",
                signature="",
                parsed_payload=payload
            )
            
            assert result["status"] == "ignored"
            assert result["reason"] == "unrelated_product"
            assert result["product_id"] == UNRELATED_PRODUCT_ID
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_product_id_is_ignored(self, subscription_service):
        """Events without product_id should be ignored."""
        payload = {
            "type": "subscription.created",
            "data": {}
        }
        
        with patch("services.subscription.get_polar_product_mapping", return_value={}):
            result = await subscription_service.handle_webhook_event(
                payload=b"{}",
                signature="",
                parsed_payload=payload
            )
            
            assert result["status"] == "ignored"
            assert result["reason"] == "no_product_id"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_axio_hub_product_is_processed(self, subscription_service):
        """Events for Axio Hub products should be processed."""
        payload = {
            "type": "subscription.created",
            "data": {
                "product_id": PRODUCT_ENTERPRISE_ID,
                "metadata": {"user_id": OWNER_UUID}
            }
        }
        
        product_mapping = {PRODUCT_ENTERPRISE_ID: "enterprise"}
        
        mock_supabase = Mock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data={"user_id": OWNER_UUID, "plan": "free"}
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock(data=[{}])
        
        with patch("services.subscription.get_polar_product_mapping", return_value=product_mapping):
            with patch("services.subscription.get_supabase", return_value=mock_supabase):
                with patch.object(subscription_service, "_invalidate_team_member_caches", new_callable=AsyncMock):
                    result = await subscription_service.handle_webhook_event(
                        payload=b"{}",
                        signature="",
                        parsed_payload=payload
                    )
                    
                    assert result["status"] == "processed"
                    assert result["action"] == "plan_upgraded"
                    assert result["new_plan"] == "enterprise"


class TestPlanUpgrade:
    """Tests for plan upgrade flow."""
    
    @pytest.fixture
    def subscription_service(self):
        from services.subscription import SubscriptionService
        return SubscriptionService()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_upgrade_updates_user_plan(self, subscription_service):
        """Subscription activation should update user's plan."""
        payload = {
            "type": "subscription.created",
            "data": {
                "product_id": PRODUCT_PRO_ID,
                "metadata": {"user_id": OWNER_UUID},
                "id": "sub_123"
            }
        }
        
        product_mapping = {PRODUCT_PRO_ID: "pro"}
        
        mock_supabase = Mock()
        # Return user profile
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data={"user_id": OWNER_UUID, "plan": "free"}
        )
        # Update should succeed
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock(data=[{}])
        
        with patch("services.subscription.get_polar_product_mapping", return_value=product_mapping):
            with patch("services.subscription.get_supabase", return_value=mock_supabase):
                with patch.object(subscription_service, "_invalidate_team_member_caches", new_callable=AsyncMock):
                    with patch("services.subscription.team_service") as mock_team_service:
                        result = await subscription_service.handle_webhook_event(
                            payload=b"{}",
                            signature="",
                            parsed_payload=payload
                        )
                        
                        assert result["status"] == "processed"
                        assert result["old_plan"] == "free"
                        assert result["new_plan"] == "pro"
                        
                        # Verify cache was invalidated
                        mock_team_service.invalidate_plan_cache.assert_called_once_with(OWNER_UUID)


class TestCacheInvalidation:
    """Tests for cache invalidation on plan changes."""
    
    @pytest.fixture
    def subscription_service(self):
        from services.subscription import SubscriptionService
        return SubscriptionService()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_team_members_cache_invalidated_on_owner_upgrade(self, subscription_service):
        """When owner upgrades, all team members' caches should be invalidated."""
        mock_supabase = Mock()
        
        # Owner's team
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data={"id": "team-uuid"}
        )
        
        # Team members
        mock_supabase.table.return_value.select.return_value.eq.return_value.neq.return_value.execute.return_value = Mock(
            data=[
                {"member_user_id": "member-1-uuid"},
                {"member_user_id": "member-2-uuid"}
            ]
        )
        
        with patch("services.subscription.get_supabase", return_value=mock_supabase):
            with patch("services.subscription.team_service") as mock_team_service:
                await subscription_service._invalidate_team_member_caches(OWNER_UUID)
                
                # Each member's cache should be invalidated
                assert mock_team_service.invalidate_plan_cache.call_count == 2


class TestEventTypes:
    """Tests for different webhook event types."""
    
    @pytest.fixture
    def subscription_service(self):
        from services.subscription import SubscriptionService
        return SubscriptionService()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_checkout_created_acknowledged(self, subscription_service):
        """checkout.created events should be acknowledged but not processed."""
        payload = {
            "type": "checkout.created",
            "data": {
                "product_id": PRODUCT_PRO_ID
            }
        }
        
        product_mapping = {PRODUCT_PRO_ID: "pro"}
        
        with patch("services.subscription.get_polar_product_mapping", return_value=product_mapping):
            result = await subscription_service.handle_webhook_event(
                payload=b"{}",
                signature="",
                parsed_payload=payload
            )
            
            assert result["status"] == "acknowledged"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_subscription_canceled_updates_status(self, subscription_service):
        """subscription.canceled should update status to canceled."""
        payload = {
            "type": "subscription.canceled",
            "data": {
                "product_id": PRODUCT_PRO_ID,
                "metadata": {"user_id": OWNER_UUID}
            }
        }
        
        product_mapping = {PRODUCT_PRO_ID: "pro"}
        
        mock_supabase = Mock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock(data=[{}])
        
        with patch("services.subscription.get_polar_product_mapping", return_value=product_mapping):
            with patch("services.subscription.get_supabase", return_value=mock_supabase):
                result = await subscription_service.handle_webhook_event(
                    payload=b"{}",
                    signature="",
                    parsed_payload=payload
                )
                
                assert result["status"] == "processed"
                assert result["action"] == "subscription_canceled"


class TestSingletonInstance:
    """Test singleton is properly configured."""
    
    @pytest.mark.unit
    def test_singleton_exists(self):
        from services.subscription import subscription_service
        assert subscription_service is not None
    
    @pytest.mark.unit
    def test_singleton_has_required_methods(self):
        from services.subscription import subscription_service
        
        assert hasattr(subscription_service, "verify_signature")
        assert hasattr(subscription_service, "handle_webhook_event")
        assert callable(subscription_service.verify_signature)
