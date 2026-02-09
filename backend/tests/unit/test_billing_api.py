from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from starlette.requests import Request


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


@pytest.mark.asyncio
async def test_create_portal_session_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"customer_portal_url": "https://portal.example.com"}

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post.return_value = mock_response

    with patch("api.v1.billing.settings") as settings, \
         patch("api.v1.billing.get_customer_id_for_user", new=AsyncMock(return_value="cust-1")), \
         patch("httpx.AsyncClient", return_value=mock_client):
        settings.POLAR_ACCESS_TOKEN = "token"
        settings.APP_URL = "https://app.example.com"

        from api.v1.billing import create_portal_session

        result = await create_portal_session(request=_make_mock_request(method="POST"), current_user_id="user-1")
        assert result.url == "https://portal.example.com"


@pytest.mark.asyncio
async def test_create_portal_session_requires_customer():
    with patch("api.v1.billing.settings") as settings, \
         patch("api.v1.billing.get_customer_id_for_user", new=AsyncMock(return_value=None)):
        settings.POLAR_ACCESS_TOKEN = "token"
        settings.APP_URL = "https://app.example.com"

        from api.v1.billing import create_portal_session

        with pytest.raises(HTTPException) as exc:
            await create_portal_session(request=_make_mock_request(method="POST"), current_user_id="user-1")
        assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_get_current_subscription_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {
                "id": "sub-1",
                "status": "active",
                "product": {"name": "Pro", "prices": [{"price_amount": 1000, "price_currency": "usd", "recurring_interval": "month"}]},
                "current_period_start": "now",
                "current_period_end": "later",
            }
        ]
    }

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.return_value = mock_response

    with patch("api.v1.billing.settings") as settings, \
         patch("api.v1.billing.get_customer_id_for_user", new=AsyncMock(return_value="cust-1")), \
         patch("httpx.AsyncClient", return_value=mock_client):
        settings.POLAR_ACCESS_TOKEN = "token"

        from api.v1.billing import get_current_subscription

        result = await get_current_subscription(request=_make_mock_request(), current_user_id="user-1")
        assert result.id == "sub-1"
        assert result.plan_name == "Pro"


@pytest.mark.asyncio
async def test_cancel_subscription_success_updates_db():
    subs_response = MagicMock()
    subs_response.status_code = 200
    subs_response.json.return_value = {"items": [{"id": "sub-1"}]}

    cancel_response = MagicMock()
    cancel_response.status_code = 204

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.return_value = subs_response
    mock_client.patch.return_value = cancel_response

    supabase = MagicMock()
    supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])

    with patch("api.v1.billing.settings") as settings, \
         patch("api.v1.billing.get_customer_id_for_user", new=AsyncMock(return_value="cust-1")), \
         patch("api.v1.billing.team_service.get_user_team_member", new=AsyncMock(return_value=SimpleNamespace(team_id="team-1"))), \
         patch("api.v1.billing.get_supabase", return_value=supabase), \
         patch("httpx.AsyncClient", return_value=mock_client):
        settings.POLAR_ACCESS_TOKEN = "token"

        from api.v1.billing import cancel_subscription

        result = await cancel_subscription(request=_make_mock_request(method="POST"), current_user_id="user-1")
        assert result["status"] == "cancelled"


@pytest.mark.asyncio
async def test_get_billing_history_sorted():
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "items": [
            {"id": "1", "amount": 10, "created_at": "2023-01-01", "product": {"name": "Pro"}},
            {"id": "2", "amount": 20, "created_at": "2024-01-01", "product": {"name": "Pro"}},
        ]
    }
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.return_value = response

    with patch("api.v1.billing.settings") as settings, \
         patch("api.v1.billing.get_customer_id_for_user", new=AsyncMock(return_value="cust-1")), \
         patch("httpx.AsyncClient", return_value=mock_client):
        settings.POLAR_ACCESS_TOKEN = "token"

        from api.v1.billing import get_billing_history

        result = await get_billing_history(request=_make_mock_request(), current_user_id="user-1")
        assert result[0].id == "2"


@pytest.mark.asyncio
async def test_download_invoice_returns_url():
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"url": "https://invoice.example.com"}

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.return_value = response

    with patch("api.v1.billing.settings") as settings, \
         patch("httpx.AsyncClient", return_value=mock_client):
        settings.POLAR_ACCESS_TOKEN = "token"

        from api.v1.billing import download_invoice

        result = await download_invoice(request=_make_mock_request(), order_id="order-1", current_user_id="user-1")
        assert result["url"] == "https://invoice.example.com"


@pytest.mark.asyncio
async def test_fix_customer_id_already_present():
    supabase = MagicMock()
    table = MagicMock()
    table.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"polar_id": "sub-1", "customer_id": "cust-1"}]
    )
    supabase.table.return_value = table

    with patch("api.v1.billing.settings") as settings, \
         patch("api.v1.billing.get_supabase", return_value=supabase), \
         patch("api.v1.billing.team_service.get_user_team_member", new=AsyncMock(return_value=SimpleNamespace(team_id="team-1"))):
        settings.POLAR_ACCESS_TOKEN = "token"

        from api.v1.billing import fix_customer_id

        result = await fix_customer_id(request=_make_mock_request(method="POST"), current_user_id="user-1")
        assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_submit_enterprise_inquiry_success():
    with patch("services.email.email_service.send_enterprise_inquiry", return_value=True):
        from api.v1.billing import EnterpriseInquiryRequest, submit_enterprise_inquiry

        result = await submit_enterprise_inquiry(
            request=_make_mock_request(method="POST"),
            data=EnterpriseInquiryRequest(
                name="Test",
                email="test@example.com",
                company="Acme",
                message="Hello",
            ),
            current_user_id="user-1",
        )
        assert result["status"] == "ok"
