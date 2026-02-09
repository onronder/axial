"""
Test Suite for Subscription Service

Tests webhook handling, signature verification, and plan updates.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, PropertyMock, call, patch

import pytest

from services.subscription import SubscriptionService


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
    def test_verify_signature_missing_header_or_secret(self, subscription_service):
        assert subscription_service.verify_signature(b"payload", "", "secret", timestamp="1") is False
        assert subscription_service.verify_signature(b"payload", "v1,abc", "", timestamp="1") is False

    @pytest.mark.unit
    def test_verify_signature_missing_v1(self, subscription_service):
        assert subscription_service.verify_signature(b"payload", "v2,abc", "secret", timestamp="1") is False

    @pytest.mark.unit
    def test_verify_signature_missing_timestamp(self, subscription_service):
        assert subscription_service.verify_signature(b"payload", "v1,abc", "secret") is False

    @pytest.mark.unit
    def test_verify_signature_no_match(self, subscription_service):
        with patch("hmac.new") as mock_hmac:
            mock_hmac.return_value.digest.return_value = b"hashed_val"
            with patch("hmac.compare_digest", return_value=False):
                assert subscription_service.verify_signature(
                    b"payload", "v1,abc", "secret", timestamp="123"
                ) is False

    @pytest.mark.unit
    def test_verify_signature_with_msg_id(self, subscription_service):
        with patch("hmac.new") as mock_hmac, \
             patch("base64.b64encode", return_value=b"sig"), \
             patch("hmac.compare_digest", return_value=True):
            mock_hmac.return_value.digest.return_value = b"hashed"
            assert subscription_service.verify_signature(
                b"payload",
                "v1,sig",
                "secret",
                timestamp="123",
                msg_id="msg-1",
            ) is True

    @pytest.mark.unit
    def test_verify_signature_whsec_secret(self, subscription_service):
        with patch("hmac.new") as mock_hmac, \
             patch("base64.b64encode", return_value=b"sig"), \
             patch("hmac.compare_digest", return_value=False):
            mock_hmac.return_value.digest.return_value = b"hashed"
            assert subscription_service.verify_signature(
                b"payload",
                "v1,sig",
                "whsec_dG9rZW4=",
                timestamp="123",
            ) is False

    @pytest.mark.unit
    def test_verify_signature_whsec_invalid_base64(self, subscription_service):
        with patch("base64.b64decode", side_effect=ValueError("bad base64")):
            assert subscription_service.verify_signature(
                b"payload",
                "v1,abc",
                "whsec_not_base64",
                timestamp="123",
            ) is False

    @pytest.mark.unit
    def test_verify_signature_handles_inner_error(self, subscription_service):
        with patch("hmac.new", side_effect=RuntimeError("boom")):
            assert subscription_service.verify_signature(
                b"payload",
                "v1,abc",
                "secret",
                timestamp="123",
            ) is False

    @pytest.mark.unit
    def test_verify_signature_handles_bad_header_type(self, subscription_service):
        assert subscription_service.verify_signature(
            b"payload",
            123,
            "secret",
            timestamp="123",
        ) is False

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
                    with patch("services.subscription.settings.POLAR_PRODUCT_ID_STARTER_MONTHLY", "prod-starter"):
                        # Run
                        await subscription_service.handle_webhook(data)

                        # Verify upsert
                        call_args = tables["subscriptions"].upsert.call_args[0][0]
                        assert call_args["plan_type"] == "starter"
                        assert call_args["status"] == "active"
                        assert tables["subscriptions"].upsert.called

                        # Verify cache invalidation
                        expected_calls = [call(owner_id), call(member_ids[0]), call(member_ids[1])]
                        actual_calls = mock_team_service.invalidate_plan_cache.call_args_list
                        assert all(call_item in actual_calls for call_item in expected_calls)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_webhook_updated_calls_update(self, subscription_service):
        data = {"type": "subscription.updated", "data": {"metadata": {"team_id": "team-123"}}}
        with patch.object(subscription_service, "_handle_subscription_updated", new=AsyncMock()) as handler:
            await subscription_service.handle_webhook(data)
            handler.assert_awaited_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_webhook_active_calls_update(self, subscription_service):
        data = {"type": "subscription.active", "data": {"metadata": {"team_id": "team-123"}}}
        with patch.object(subscription_service, "_handle_subscription_updated", new=AsyncMock()) as handler:
            await subscription_service.handle_webhook(data)
            handler.assert_awaited_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_webhook_uncanceled_calls_update(self, subscription_service):
        data = {"type": "subscription.uncanceled", "data": {"metadata": {"team_id": "team-123"}}}
        with patch.object(subscription_service, "_handle_subscription_updated", new=AsyncMock()) as handler:
            await subscription_service.handle_webhook(data)
            handler.assert_awaited_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_webhook_unknown_type(self, subscription_service):
        data = {"type": "unknown.event", "data": {}}
        with patch.object(subscription_service, "_handle_subscription_updated", new=AsyncMock()) as handler:
            await subscription_service.handle_webhook(data)
            handler.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_webhook_handles_errors(self, subscription_service):
        data = {"type": "subscription.created", "data": {}}
        with patch.object(subscription_service, "_handle_subscription_created", new=AsyncMock(side_effect=Exception("boom"))):
            await subscription_service.handle_webhook(data)

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

                    expected_calls = [call(owner_id), call(member_ids[0]), call(member_ids[1])]
                    actual_calls = mock_team_service.invalidate_plan_cache.call_args_list
                    assert all(call_item in actual_calls for call_item in expected_calls)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_webhook_revoked_calls_cancel(self, subscription_service):
        data = {"type": "subscription.revoked", "data": {"metadata": {"team_id": "team-123"}}}
        with patch.object(subscription_service, "_handle_subscription_revoked", new=AsyncMock()) as handler:
            await subscription_service.handle_webhook(data)
            handler.assert_awaited_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_missing_team_id_ignored(self, subscription_service):
        data = {"type": "product.updated", "data": {}}

        with patch.object(subscription_service, "verify_signature", return_value=True):
             await subscription_service.handle_webhook(data)
             # No side effects to check, just ensuring no crash

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_upsert_subscription_missing_team_id(self, subscription_service):
        await subscription_service._upsert_subscription({})

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_upsert_subscription_unknown_product(self, subscription_service):
        with patch("core.config.Settings.POLAR_PRODUCT_MAPPING", new_callable=PropertyMock) as mock_mapping:
            mock_mapping.return_value = {}
            await subscription_service._upsert_subscription(
                {"metadata": {"team_id": "team-1"}, "product_id": "unknown"}
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_upsert_subscription_enterprise_plan_override(self, subscription_service):
        mock_supabase = Mock()
        owner_id = "owner-123"
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
                    data=[]
                )
            elif table_name == "user_profiles":
                first = Mock()
                first.eq.return_value.execute.side_effect = Exception("boom")
                second = Mock()
                second.eq.return_value.execute.return_value = Mock()
                table.update.side_effect = [first, second]
            return table

        mock_supabase.table.side_effect = table_side_effect

        fake_settings = SimpleNamespace(
            POLAR_PRODUCT_MAPPING={"prod-ent": "pro"},
            POLAR_PRODUCT_ID_ENTERPRISE="prod-ent",
        )

        with patch("services.subscription.get_supabase", return_value=mock_supabase), \
             patch("services.subscription.team_service.invalidate_plan_cache", side_effect=Exception("boom")), \
             patch("services.subscription.settings", fake_settings):
            await subscription_service._upsert_subscription(
                {"metadata": {"team_id": "team-1"}, "product_id": "prod-ent", "id": "sub-1"}
            )

        call_args = tables["subscriptions"].upsert.call_args[0][0]
        assert call_args["plan_type"] == "enterprise"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_subscription_missing_team_id(self, subscription_service):
        await subscription_service._cancel_subscription({"metadata": {}}, "canceled")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_subscription_handles_invalidation_error(self, subscription_service):
        mock_supabase = Mock()

        def table_side_effect(table_name: str):
            table = Mock()
            if table_name == "subscriptions":
                table.update.return_value.eq.return_value.execute.return_value = Mock()
            elif table_name == "team_members":
                table.select.return_value.eq.return_value.neq.return_value.execute.side_effect = Exception("boom")
            elif table_name == "teams":
                table.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(data={})
            return table

        mock_supabase.table.side_effect = table_side_effect

        with patch("services.subscription.get_supabase", return_value=mock_supabase):
            await subscription_service._cancel_subscription({"metadata": {"team_id": "team-1"}}, "canceled")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_subscription_updated_calls_upsert(self, subscription_service):
        subscription_service._upsert_subscription = AsyncMock()

        await subscription_service._handle_subscription_updated({"id": "sub-1"})

        subscription_service._upsert_subscription.assert_awaited_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_subscription_revoked_calls_cancel(self, subscription_service):
        subscription_service._cancel_subscription = AsyncMock()

        await subscription_service._handle_subscription_revoked({"id": "sub-1"})

        subscription_service._cancel_subscription.assert_awaited_once_with({"id": "sub-1"}, "revoked")
