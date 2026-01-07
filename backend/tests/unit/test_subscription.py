"""
Test Suite for Subscription Service

Tests webhook handling, signature verification, and plan updates.
"""

import pytest
from unittest.mock import patch, Mock, PropertyMock, call
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
        owner_id = "owner-123"
        member_ids = ["member-1", "member-2"]

        tables = {}

        def table_side_effect(table_name: str):
            table = Mock()
            tables[table_name] = table
            if table_name == "subscriptions":
                table.upsert.return_value.execute.return_value = Mock()
            elif table_name == "teams":
                table.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
                    data={"owner_id": owner_id}
                )
            elif table_name == "team_members":
                table.select.return_value.eq.return_value.neq.return_value.execute.return_value = Mock(
                    data=[{"member_user_id": member_id} for member_id in member_ids]
                )
            elif table_name == "user_profiles":
                table.update.return_value.eq.return_value.execute.return_value = Mock()
            return table

        mock_supabase.table.side_effect = table_side_effect
        
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
                        call_args = tables["subscriptions"].upsert.call_args[0][0]
                        assert call_args["plan_type"] == "starter"
                        assert call_args["status"] == "active"
                        assert tables["subscriptions"].upsert.called
                        
                        # Verify cache invalidation
                        expected_calls = {call(owner_id), call(member_ids[0]), call(member_ids[1])}
                        actual_calls = set(mock_team_service.invalidate_plan_cache.call_args_list)
                        assert expected_calls.issubset(actual_calls)

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
        owner_id = "owner-123"
        member_ids = ["member-1", "member-2"]

        tables = {}

        def table_side_effect(table_name: str):
            table = Mock()
            tables[table_name] = table
            if table_name == "subscriptions":
                table.update.return_value.eq.return_value.execute.return_value = Mock()
            elif table_name == "teams":
                table.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
                    data={"owner_id": owner_id}
                )
            elif table_name == "team_members":
                table.select.return_value.eq.return_value.neq.return_value.execute.return_value = Mock(
                    data=[{"member_user_id": member_id} for member_id in member_ids]
                )
            return table

        mock_supabase.table.side_effect = table_side_effect
        
        with patch.object(subscription_service, "verify_signature", return_value=True):
            with patch("services.subscription.get_supabase", return_value=mock_supabase):
                with patch("services.subscription.team_service", mock_team_service):
                    await subscription_service.handle_webhook(data)
                    
                    # Verify update
                    assert tables["subscriptions"].update.called
                    
                    expected_calls = {call(owner_id), call(member_ids[0]), call(member_ids[1])}
                    actual_calls = set(mock_team_service.invalidate_plan_cache.call_args_list)
                    assert expected_calls.issubset(actual_calls)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_missing_team_id_ignored(self, subscription_service):
        data = {"type": "product.updated", "data": {}}
        
        with patch.object(subscription_service, "verify_signature", return_value=True):
             await subscription_service.handle_webhook(data)
             # No side effects to check, just ensuring no crash
