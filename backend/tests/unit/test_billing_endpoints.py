from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from api.v1 import billing


def _make_mock_request(method="GET", path="/api/v1/billing"):
    """Create a mock request for rate-limited endpoints."""
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": [],
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 12345),
        "app": None,
    }
    return Request(scope=scope)


def _make_async_client(get_responses=None, post_responses=None, patch_responses=None):
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = False
    if get_responses is not None:
        client.get = AsyncMock(side_effect=get_responses)
    if post_responses is not None:
        client.post = AsyncMock(side_effect=post_responses)
    if patch_responses is not None:
        client.patch = AsyncMock(side_effect=patch_responses)
    return client


class TestGetCustomerId:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_none_without_team(self):
        with patch("api.v1.billing.team_service.get_user_team_member", new=AsyncMock(return_value=None)):
            result = await billing.get_customer_id_for_user("user-1")

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_customer_id_from_db(self):
        supabase = MagicMock()
        supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = Mock(
            data=[{"customer_id": "cust-1"}]
        )
        team_member = SimpleNamespace(team_id="team-1")

        with patch("api.v1.billing.team_service.get_user_team_member", new=AsyncMock(return_value=team_member)), \
             patch("api.v1.billing.get_supabase", return_value=supabase):
            result = await billing.get_customer_id_for_user("user-1")

        assert result == "cust-1"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_customer_id_from_polar_subscription(self):
        supabase = MagicMock()
        supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = Mock(
            data=[{"polar_id": "sub-1"}]
        )
        supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock(data=[{}])
        team_member = SimpleNamespace(team_id="team-1")

        response = Mock(status_code=200)
        response.json.return_value = {"customer": {"id": "cust-2"}}
        client = _make_async_client(get_responses=[response])

        with patch("api.v1.billing.team_service.get_user_team_member", new=AsyncMock(return_value=team_member)), \
             patch("api.v1.billing.get_supabase", return_value=supabase), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            result = await billing.get_customer_id_for_user("user-1")

        assert result == "cust-2"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_customer_id_from_email_lookup(self):
        supabase = MagicMock()
        supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = Mock(
            data=[]
        )
        supabase.auth.admin.get_user_by_id.return_value = SimpleNamespace(
            user=SimpleNamespace(email="user@example.com")
        )
        team_member = SimpleNamespace(team_id="team-1")

        response = Mock(status_code=200)
        response.json.return_value = {"items": [{"id": "cust-3"}]}
        client = _make_async_client(get_responses=[response])

        with patch("api.v1.billing.team_service.get_user_team_member", new=AsyncMock(return_value=team_member)), \
             patch("api.v1.billing.get_supabase", return_value=supabase), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            result = await billing.get_customer_id_for_user("user-1")

        assert result == "cust-3"


class TestListPlans:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_plans_returns_empty_without_token(self):
        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "", create=True):
            result = await billing.list_plans(request=_make_mock_request())

        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_plans_returns_sorted(self):
        items = [
            {
                "id": "prod-pro",
                "name": "Pro",
                "description": "",
                "prices": [{"price_amount": 2000, "price_currency": "usd", "recurring_interval": "month"}],
            },
            {
                "id": "prod-starter",
                "name": "Starter",
                "description": "",
                "prices": [{"price_amount": 1000, "price_currency": "usd", "recurring_interval": "month"}],
            },
        ]
        response = Mock(status_code=200)
        response.json.return_value = {"items": items}
        client = _make_async_client(get_responses=[response])

        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch.object(billing.settings, "POLAR_PRODUCT_ID_STARTER_MONTHLY", "prod-starter", create=True), \
             patch.object(billing.settings, "POLAR_PRODUCT_ID_PRO_MONTHLY", "prod-pro", create=True), \
             patch.object(billing.settings, "POLAR_PRODUCT_ID_ENTERPRISE", None, create=True), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            result = await billing.list_plans(request=_make_mock_request())

        assert [plan.type for plan in result] == ["starter", "pro", "enterprise"]


class TestCheckout:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_checkout_invalid_plan(self):
        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.team_service.get_user_team_member", new=AsyncMock(return_value=SimpleNamespace(team_id="team-1"))):
            with pytest.raises(HTTPException):
                await billing.create_checkout_session(
                    request=_make_mock_request(method="POST"),
                    data=billing.CheckoutRequest(plan="bad"),
                    current_user_id="user-1",
                )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_checkout_success(self):
        response = Mock()
        response.raise_for_status = Mock()
        response.json.return_value = {"url": "https://checkout"}
        client = _make_async_client(post_responses=[response])

        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch.object(billing.settings, "POLAR_PRODUCT_ID_STARTER_MONTHLY", "prod-starter", create=True), \
             patch("api.v1.billing.team_service.get_user_team_member", new=AsyncMock(return_value=SimpleNamespace(team_id="team-1"))), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            result = await billing.create_checkout_session(
                request=_make_mock_request(method="POST"),
                data=billing.CheckoutRequest(plan="starter"),
                current_user_id="user-1",
            )

        assert result["url"] == "https://checkout"


class TestPortal:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_portal_requires_customer(self):
        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.get_customer_id_for_user", new=AsyncMock(return_value=None)):
            with pytest.raises(HTTPException):
                await billing.create_portal_session(request=_make_mock_request(method="POST"), current_user_id="user-1")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_portal_success(self):
        response = Mock(status_code=200, text="ok")
        response.json.return_value = {"customer_portal_url": "https://portal"}
        client = _make_async_client(post_responses=[response])

        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.get_customer_id_for_user", new=AsyncMock(return_value="cust-1")), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            result = await billing.create_portal_session(request=_make_mock_request(method="POST"), current_user_id="user-1")

        assert result.url == "https://portal"


class TestSubscription:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_current_subscription_none(self):
        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.get_customer_id_for_user", new=AsyncMock(return_value=None)):
            result = await billing.get_current_subscription(request=_make_mock_request(), current_user_id="user-1")

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_current_subscription_success(self):
        response = Mock(status_code=200)
        response.json.return_value = {
            "items": [
                {
                    "id": "sub-1",
                    "status": "active",
                    "product": {"name": "Pro", "prices": [{"price_amount": 2000, "price_currency": "usd", "recurring_interval": "month"}]},
                    "current_period_start": "2024-01-01",
                    "current_period_end": "2024-02-01",
                    "cancel_at_period_end": False,
                }
            ]
        }
        client = _make_async_client(get_responses=[response])

        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.get_customer_id_for_user", new=AsyncMock(return_value="cust-1")), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            result = await billing.get_current_subscription(request=_make_mock_request(), current_user_id="user-1")

        assert result.id == "sub-1"


class TestCancelSubscription:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_subscription_success(self):
        get_response = Mock(status_code=200)
        get_response.json.return_value = {"items": [{"id": "sub-1"}]}
        patch_response = Mock(status_code=200, text="ok")
        client = _make_async_client(get_responses=[get_response], patch_responses=[patch_response])

        supabase = MagicMock()
        supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock(data=[{}])

        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.get_customer_id_for_user", new=AsyncMock(return_value="cust-1")), \
             patch("api.v1.billing.team_service.get_user_team_member", new=AsyncMock(return_value=SimpleNamespace(team_id="team-1"))), \
             patch("api.v1.billing.get_supabase", return_value=supabase), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            result = await billing.cancel_subscription(request=_make_mock_request(method="POST"), current_user_id="user-1")

        assert result["status"] == "cancelled"


class TestBillingHistory:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_billing_history_returns_invoices(self):
        response = Mock(status_code=200)
        response.json.return_value = {
            "items": [
                {"id": "order-2", "amount": 2000, "currency": "usd", "status": "paid", "created_at": "2024-02-01", "product": {"name": "Pro"}},
                {"id": "order-1", "amount": 1000, "currency": "usd", "status": "paid", "created_at": "2024-01-01", "product": {"name": "Starter"}},
            ]
        }
        client = _make_async_client(get_responses=[response])

        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.get_customer_id_for_user", new=AsyncMock(return_value="cust-1")), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            result = await billing.get_billing_history(request=_make_mock_request(), current_user_id="user-1", limit=120, offset=0)

        assert result[0].id == "order-2"


class TestInvoices:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_download_invoice_returns_url(self):
        response = Mock(status_code=200)
        response.json.return_value = {"url": "https://invoice"}
        client = _make_async_client(get_responses=[response])

        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            result = await billing.download_invoice(request=_make_mock_request(), order_id="order-1", current_user_id="user-1")

        assert result["url"] == "https://invoice"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_download_invoice_generates(self):
        get_response = Mock(status_code=404)
        post_response = Mock(status_code=202)
        client = _make_async_client(get_responses=[get_response], post_responses=[post_response])

        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            result = await billing.download_invoice(request=_make_mock_request(), order_id="order-1", current_user_id="user-1")

        assert result["status"] == "generating"


class TestFixCustomerId:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fix_customer_id_updates(self):
        response = Mock(status_code=200, text="ok")
        response.json.return_value = {"customer": {"id": "cust-9"}}
        client = _make_async_client(get_responses=[response])

        supabase = MagicMock()
        supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = Mock(
            data=[{"polar_id": "sub-1", "customer_id": None}]
        )
        supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock(data=[{}])

        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.team_service.get_user_team_member", new=AsyncMock(return_value=SimpleNamespace(team_id="team-1"))), \
             patch("api.v1.billing.get_supabase", return_value=supabase), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            result = await billing.fix_customer_id(request=_make_mock_request(method="POST"), current_user_id="user-1")

        assert result["status"] == "ok"


class TestBillingErrorPaths:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_customer_id_handles_admin_error(self):
        supabase = MagicMock()
        supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = Mock(
            data=[]
        )
        supabase.auth.admin.get_user_by_id.side_effect = RuntimeError("boom")
        team_member = SimpleNamespace(team_id="team-1")

        with patch("api.v1.billing.team_service.get_user_team_member", new=AsyncMock(return_value=team_member)), \
             patch("api.v1.billing.get_supabase", return_value=supabase):
            result = await billing.get_customer_id_for_user("user-1")

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_customer_id_handles_unexpected_error(self):
        with patch("api.v1.billing.team_service.get_user_team_member", side_effect=RuntimeError("boom")):
            result = await billing.get_customer_id_for_user("user-1")

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_customer_id_email_lookup_empty(self):
        supabase = MagicMock()
        supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = Mock(
            data=[]
        )
        supabase.auth.admin.get_user_by_id.return_value = SimpleNamespace(
            user=SimpleNamespace(email="user@example.com")
        )
        team_member = SimpleNamespace(team_id="team-1")

        response = Mock(status_code=200)
        response.json.return_value = {"items": []}
        client = _make_async_client(get_responses=[response])

        with patch("api.v1.billing.team_service.get_user_team_member", new=AsyncMock(return_value=team_member)), \
             patch("api.v1.billing.get_supabase", return_value=supabase), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            result = await billing.get_customer_id_for_user("user-1")

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_plans_handles_status_error(self):
        response = Mock(status_code=500)
        response.text = "error"
        client = _make_async_client(get_responses=[response])

        with patch.object(billing, "_plans_cache", None), \
             patch.object(billing, "_plans_cache_time", 0), \
             patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            result = await billing.list_plans(request=_make_mock_request())

        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_plans_skips_missing_prices(self):
        items = [
            {"id": "prod-starter", "name": "Starter", "description": "", "prices": []},
        ]
        response = Mock(status_code=200)
        response.json.return_value = {"items": items}
        client = _make_async_client(get_responses=[response])

        with patch.object(billing, "_plans_cache", None), \
             patch.object(billing, "_plans_cache_time", 0), \
             patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch.object(billing.settings, "POLAR_PRODUCT_ID_STARTER_MONTHLY", "prod-starter", create=True), \
             patch.object(billing.settings, "POLAR_PRODUCT_ID_PRO_MONTHLY", "prod-pro", create=True), \
             patch.object(billing.settings, "POLAR_PRODUCT_ID_ENTERPRISE", None, create=True), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            result = await billing.list_plans(request=_make_mock_request())

        assert [plan.type for plan in result] == ["enterprise"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_checkout_requires_token(self):
        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", None, create=True):
            with pytest.raises(HTTPException):
                await billing.create_checkout_session(
                    request=_make_mock_request(method="POST"),
                    data=billing.CheckoutRequest(plan="starter"),
                    current_user_id="user-1",
                )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_checkout_requires_team(self):
        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch.object(billing.settings, "POLAR_PRODUCT_ID_STARTER_MONTHLY", "prod-starter", create=True), \
             patch("api.v1.billing.team_service.get_user_team_member", new=AsyncMock(return_value=None)):
            with pytest.raises(HTTPException):
                await billing.create_checkout_session(
                    request=_make_mock_request(method="POST"),
                    data=billing.CheckoutRequest(plan="starter"),
                    current_user_id="user-1",
                )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_checkout_handles_http_error(self):
        response = Mock()
        response.raise_for_status.side_effect = RuntimeError("bad")
        client = _make_async_client(post_responses=[response])

        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch.object(billing.settings, "POLAR_PRODUCT_ID_STARTER_MONTHLY", "prod-starter", create=True), \
             patch("api.v1.billing.team_service.get_user_team_member", new=AsyncMock(return_value=SimpleNamespace(team_id="team-1"))), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            with pytest.raises(HTTPException):
                await billing.create_checkout_session(
                    request=_make_mock_request(method="POST"),
                    data=billing.CheckoutRequest(plan="starter"),
                    current_user_id="user-1",
                )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_portal_requires_token(self):
        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", None, create=True):
            with pytest.raises(HTTPException):
                await billing.create_portal_session(request=_make_mock_request(method="POST"), current_user_id="user-1")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_portal_handles_status_error(self):
        response = Mock(status_code=500, text="error")
        client = _make_async_client(post_responses=[response])

        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.get_customer_id_for_user", new=AsyncMock(return_value="cust-1")), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            with pytest.raises(HTTPException):
                await billing.create_portal_session(request=_make_mock_request(method="POST"), current_user_id="user-1")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_portal_handles_exception(self):
        client = _make_async_client()
        client.post.side_effect = RuntimeError("boom")

        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.get_customer_id_for_user", new=AsyncMock(return_value="cust-1")), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            with pytest.raises(HTTPException):
                await billing.create_portal_session(request=_make_mock_request(method="POST"), current_user_id="user-1")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_current_subscription_no_token(self):
        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", None, create=True):
            result = await billing.get_current_subscription(request=_make_mock_request(), current_user_id="user-1")

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_current_subscription_status_error(self):
        response = Mock(status_code=500)
        client = _make_async_client(get_responses=[response])

        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.get_customer_id_for_user", new=AsyncMock(return_value="cust-1")), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            result = await billing.get_current_subscription(request=_make_mock_request(), current_user_id="user-1")

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_current_subscription_empty_items(self):
        response = Mock(status_code=200)
        response.json.return_value = {"items": []}
        client = _make_async_client(get_responses=[response])

        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.get_customer_id_for_user", new=AsyncMock(return_value="cust-1")), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            result = await billing.get_current_subscription(request=_make_mock_request(), current_user_id="user-1")

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_current_subscription_handles_exception(self):
        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.get_customer_id_for_user", new=AsyncMock(side_effect=RuntimeError("boom"))):
            result = await billing.get_current_subscription(request=_make_mock_request(), current_user_id="user-1")

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_subscription_no_token(self):
        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", None, create=True):
            with pytest.raises(HTTPException):
                await billing.cancel_subscription(request=_make_mock_request(method="POST"), current_user_id="user-1")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_subscription_no_customer(self):
        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.get_customer_id_for_user", new=AsyncMock(return_value=None)):
            with pytest.raises(HTTPException):
                await billing.cancel_subscription(request=_make_mock_request(method="POST"), current_user_id="user-1")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_subscription_fetch_error(self):
        get_response = Mock(status_code=500, text="error")
        client = _make_async_client(get_responses=[get_response])

        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.get_customer_id_for_user", new=AsyncMock(return_value="cust-1")), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            with pytest.raises(HTTPException):
                await billing.cancel_subscription(request=_make_mock_request(method="POST"), current_user_id="user-1")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_subscription_no_items(self):
        get_response = Mock(status_code=200)
        get_response.json.return_value = {"items": []}
        client = _make_async_client(get_responses=[get_response])

        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.get_customer_id_for_user", new=AsyncMock(return_value="cust-1")), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            with pytest.raises(HTTPException):
                await billing.cancel_subscription(request=_make_mock_request(method="POST"), current_user_id="user-1")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_subscription_missing_subscription_id(self):
        get_response = Mock(status_code=200)
        get_response.json.return_value = {"items": [{"id": None}]}
        client = _make_async_client(get_responses=[get_response])

        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.get_customer_id_for_user", new=AsyncMock(return_value="cust-1")), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            with pytest.raises(HTTPException):
                await billing.cancel_subscription(request=_make_mock_request(method="POST"), current_user_id="user-1")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_subscription_cancel_failed(self):
        get_response = Mock(status_code=200)
        get_response.json.return_value = {"items": [{"id": "sub-1"}]}
        patch_response = Mock(status_code=500, text="error")
        client = _make_async_client(get_responses=[get_response], patch_responses=[patch_response])

        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.get_customer_id_for_user", new=AsyncMock(return_value="cust-1")), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            with pytest.raises(HTTPException):
                await billing.cancel_subscription(request=_make_mock_request(method="POST"), current_user_id="user-1")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_subscription_exception(self):
        client = _make_async_client()
        client.get.side_effect = RuntimeError("boom")

        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.get_customer_id_for_user", new=AsyncMock(return_value="cust-1")), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            with pytest.raises(HTTPException):
                await billing.cancel_subscription(request=_make_mock_request(method="POST"), current_user_id="user-1")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_billing_history_no_token(self):
        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", None, create=True):
            result = await billing.get_billing_history(request=_make_mock_request(), current_user_id="user-1", limit=120, offset=0)

        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_billing_history_no_customer(self):
        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.get_customer_id_for_user", new=AsyncMock(return_value=None)):
            result = await billing.get_billing_history(request=_make_mock_request(), current_user_id="user-1", limit=120, offset=0)

        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_billing_history_status_error(self):
        response = Mock(status_code=500)
        client = _make_async_client(get_responses=[response])

        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.get_customer_id_for_user", new=AsyncMock(return_value="cust-1")), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            result = await billing.get_billing_history(request=_make_mock_request(), current_user_id="user-1", limit=120, offset=0)

        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_billing_history_exception(self):
        client = _make_async_client()
        client.get.side_effect = RuntimeError("boom")

        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.get_customer_id_for_user", new=AsyncMock(return_value="cust-1")), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            result = await billing.get_billing_history(request=_make_mock_request(), current_user_id="user-1", limit=120, offset=0)

        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_download_invoice_no_token(self):
        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", None, create=True):
            with pytest.raises(HTTPException):
                await billing.download_invoice(request=_make_mock_request(), order_id="order-1", current_user_id="user-1")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_download_invoice_not_found(self):
        get_response = Mock(status_code=404)
        post_response = Mock(status_code=500)
        client = _make_async_client(get_responses=[get_response], post_responses=[post_response])

        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            with pytest.raises(HTTPException) as exc:
                await billing.download_invoice(request=_make_mock_request(), order_id="order-1", current_user_id="user-1")

        assert exc.value.status_code == 404

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_download_invoice_exception(self):
        client = _make_async_client()
        client.get.side_effect = RuntimeError("boom")

        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            with pytest.raises(HTTPException):
                await billing.download_invoice(request=_make_mock_request(), order_id="order-1", current_user_id="user-1")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fix_customer_id_no_token(self):
        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", None, create=True):
            with pytest.raises(HTTPException):
                await billing.fix_customer_id(request=_make_mock_request(method="POST"), current_user_id="user-1")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fix_customer_id_no_team(self):
        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.team_service.get_user_team_member", new=AsyncMock(return_value=None)):
            with pytest.raises(HTTPException):
                await billing.fix_customer_id(request=_make_mock_request(method="POST"), current_user_id="user-1")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fix_customer_id_no_subscription(self):
        supabase = MagicMock()
        supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = Mock(
            data=[]
        )

        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.team_service.get_user_team_member", new=AsyncMock(return_value=SimpleNamespace(team_id="team-1"))), \
             patch("api.v1.billing.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException):
                await billing.fix_customer_id(request=_make_mock_request(method="POST"), current_user_id="user-1")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fix_customer_id_no_polar_id(self):
        supabase = MagicMock()
        supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = Mock(
            data=[{"polar_id": None, "customer_id": None}]
        )

        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.team_service.get_user_team_member", new=AsyncMock(return_value=SimpleNamespace(team_id="team-1"))), \
             patch("api.v1.billing.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException):
                await billing.fix_customer_id(request=_make_mock_request(method="POST"), current_user_id="user-1")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fix_customer_id_missing_customer(self):
        response = Mock(status_code=200, text="ok")
        response.json.return_value = {"customer": {}}
        client = _make_async_client(get_responses=[response])

        supabase = MagicMock()
        supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = Mock(
            data=[{"polar_id": "sub-1", "customer_id": None}]
        )

        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.team_service.get_user_team_member", new=AsyncMock(return_value=SimpleNamespace(team_id="team-1"))), \
             patch("api.v1.billing.get_supabase", return_value=supabase), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            result = await billing.fix_customer_id(request=_make_mock_request(method="POST"), current_user_id="user-1")

        assert result["status"] == "error"
        assert "No customer" in result["message"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fix_customer_id_polar_error(self):
        response = Mock(status_code=500, text="error")
        client = _make_async_client(get_responses=[response])

        supabase = MagicMock()
        supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = Mock(
            data=[{"polar_id": "sub-1", "customer_id": None}]
        )

        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.team_service.get_user_team_member", new=AsyncMock(return_value=SimpleNamespace(team_id="team-1"))), \
             patch("api.v1.billing.get_supabase", return_value=supabase), \
             patch("api.v1.billing.httpx.AsyncClient", return_value=client):
            result = await billing.fix_customer_id(request=_make_mock_request(method="POST"), current_user_id="user-1")

        assert result["status"] == "error"
        assert "Polar API error" in result["message"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fix_customer_id_exception(self):
        supabase = MagicMock()
        supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = RuntimeError("boom")

        with patch.object(billing.settings, "POLAR_ACCESS_TOKEN", "token", create=True), \
             patch("api.v1.billing.team_service.get_user_team_member", new=AsyncMock(return_value=SimpleNamespace(team_id="team-1"))), \
             patch("api.v1.billing.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException):
                await billing.fix_customer_id(request=_make_mock_request(method="POST"), current_user_id="user-1")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_enterprise_inquiry_failure_path(self):
        with patch("services.email.email_service.send_enterprise_inquiry", return_value=False):
            result = await billing.submit_enterprise_inquiry(
                request=_make_mock_request(method="POST"),
                data=billing.EnterpriseInquiryRequest(
                    name="Test",
                    email="test@example.com",
                    company="Acme",
                    message="Hello",
                ),
                current_user_id="user-1",
            )

        assert result["status"] == "ok"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_enterprise_inquiry_exception(self):
        with patch("services.email.email_service.send_enterprise_inquiry", side_effect=RuntimeError("boom")):
            result = await billing.submit_enterprise_inquiry(
                request=_make_mock_request(method="POST"),
                data=billing.EnterpriseInquiryRequest(
                    name="Test",
                    email="test@example.com",
                    company="Acme",
                    message="Hello",
                ),
                current_user_id="user-1",
            )

        assert result["status"] == "ok"
