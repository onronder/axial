"""
Test Suite for Subscription Service

Tests webhook handling, signature verification, and plan updates.
"""

import pytest
from unittest.mock import patch, Mock, PropertyMock
from services.subscription import SubscriptionService
from core.config import Settings

class TestSubscriptionService:
    @pytest.fixture
    def subscription_service(self):
        return SubscriptionService()
    
    @pytest.mark.unit
    def test_verify_signature_success(self, subscription_service):
        with patch("core.config.settings.POLAR_WEBHOOK_SECRET", "test_secret"):
            # Mock hmac
            with patch("hmac.new") as mock_hmac:
                mock_hmac.return_value.digest.return_value = b"hashed_val"
                mock_hmac.return_value.hexdigest.return_value = "hash"
                with patch("hmac.compare_digest", return_value=True):
                    assert subscription_service.verify_signature(b"payload", "v1,whsec_hash", "test_secret", timestamp="1234567890") is True
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_webhook_created(self, subscription_service):
        payload = b"{}"
        signature = "valid_signature"
        data = {
            "type": "subscription.created",
            "data": {
                "metadata": {"team_id": "team-123"},
                "id": "sub-123",
                "product_id": "prod-starter"
            }
        }
        
        mock_supabase = Mock()
        mock_team_service = Mock()
        
        with patch.object(subscription_service, "verify_signature", return_value=True):
            with patch("services.subscription.get_supabase", return_value=mock_supabase):
                with patch("services.subscription.team_service", mock_team_service):
                    # Mock settings mapping property using PropertyMock on the Class
                    with patch("core.config.Settings.POLAR_PRODUCT_MAPPING", new_callable=PropertyMock) as mock_mapping:
                        mock_mapping.return_value = {"prod-starter": "starter"}
                        # Run
                        await subscription_service.handle_webhook(data)
                        
                        # Verify upsert
                        mock_supabase.table.return_value.upsert.assert_called_once()
                        call_args = mock_supabase.table.return_value.upsert.call_args[0][0]
                        assert call_args["plan_type"] == "starter"
                        assert call_args["status"] == "active"
                        
                        # Verify cache invalidation
                        mock_team_service.invalidate_plan_cache.assert_called_with("team-123")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_webhook_canceled(self, subscription_service):
        payload = b"{}"
        signature = "valid"
        data = {
            "type": "subscription.canceled",
            "data": {
                "metadata": {"team_id": "team-123"},
                "id": "sub-123"
            }
        }
        
        mock_supabase = Mock()
        mock_team_service = Mock()
        
        with patch.object(subscription_service, "verify_signature", return_value=True):
            with patch("services.subscription.get_supabase", return_value=mock_supabase):
                with patch("services.subscription.team_service", mock_team_service):
                    await subscription_service.handle_webhook(data)
                    
                    # Verify update
                    mock_supabase.table.return_value.update.assert_called_with({"status": "canceled"})
                    
                    mock_team_service.invalidate_plan_cache.assert_called_with("team-123")
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_missing_team_id_ignored(self, subscription_service):
        data = {"type": "product.updated", "data": {}}
        
        with patch.object(subscription_service, "verify_signature", return_value=True):
             await subscription_service.handle_webhook(data)
             # No side effects to check, just ensuring no crash
