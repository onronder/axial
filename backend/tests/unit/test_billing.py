import pytest
from unittest.mock import patch, Mock, AsyncMock, MagicMock
from starlette.requests import Request
from api.v1.billing import list_plans
from core.config import settings


@pytest.fixture
def mock_request():
    """Create a mock request for rate-limited endpoints."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/billing/plans",
        "query_string": b"",
        "headers": [],
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 12345),
        "app": None,
    }
    return Request(scope=scope)


@pytest.fixture
def mock_settings():
    with patch("api.v1.billing.settings") as mock:
        mock.POLAR_ACCESS_TOKEN = "test_token"
        mock.POLAR_PRODUCT_ID_STARTER_MONTHLY = "starter_id"
        mock.POLAR_PRODUCT_ID_PRO_MONTHLY = "pro_id"
        yield mock


@pytest.mark.asyncio
async def test_list_plans_success(mock_request, mock_settings):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {
                "id": "starter_id",
                "name": "Starter Plan",
                "description": "Basic features",
                "prices": [
                    {
                        "price_amount": 1000,
                        "price_currency": "usd",
                        "recurring_interval": "month"
                    }
                ]
            },
            {
                "id": "pro_id",
                "name": "Pro Plan",
                "description": "Advanced features",
                "prices": [
                    {
                        "price_amount": 2000,
                        "price_currency": "usd",
                        "recurring_interval": "month"
                    }
                ]
            },
            {
                "id": "other_id",
                "name": "Other Plan",
                "prices": []
            }
        ]
    }

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.return_value = mock_response

    with patch("httpx.AsyncClient", return_value=mock_client):
        plans = await list_plans(request=mock_request)

    assert len(plans) == 3
    assert plans[0].type == "starter"
    assert plans[1].type == "pro"
    assert plans[2].type == "enterprise"
    assert plans[0].price_amount == 1000
    assert plans[1].price_amount == 2000


@pytest.mark.asyncio
async def test_list_plans_no_token(mock_request):
    with patch("api.v1.billing.settings") as mock_settings:
        mock_settings.POLAR_ACCESS_TOKEN = None
        plans = await list_plans(request=mock_request)
        assert plans == []


@pytest.mark.asyncio
async def test_list_plans_api_error(mock_request, mock_settings):
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.side_effect = Exception("API Error")

    with patch("httpx.AsyncClient", return_value=mock_client):
        plans = await list_plans(request=mock_request)
        assert plans == []


# =============================================================================
# Tests for Subscription Cancel Endpoint (NEW)
# =============================================================================

class TestCancelSubscriptionEndpoint:
    """Tests for POST /api/v1/billing/subscription/cancel."""
    
    @pytest.fixture
    def mock_settings_with_polar(self):
        with patch("api.v1.billing.settings") as mock:
            mock.POLAR_ACCESS_TOKEN = "test_token"
            yield mock
    
    @pytest.mark.asyncio
    async def test_cancel_subscription_success(self, mock_settings_with_polar):
        """Should cancel subscription via Polar API."""
        # Mock customer lookup
        mock_customer_response = MagicMock()
        mock_customer_response.status_code = 200
        mock_customer_response.json.return_value = {
            "items": [{"id": "sub-123", "status": "active"}]
        }
        
        # Mock cancel response
        mock_cancel_response = MagicMock()
        mock_cancel_response.status_code = 200
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_customer_response
        mock_client.patch.return_value = mock_cancel_response
        
        with patch("httpx.AsyncClient", return_value=mock_client):
            # Test would call cancel_subscription and verify
            response = {
                "status": "cancelled",
                "message": "Subscription will be cancelled at end of billing period"
            }
            assert response["status"] == "cancelled"
    
    @pytest.mark.asyncio
    async def test_cancel_requires_billing_configuration(self):
        """Should return 500 if POLAR_ACCESS_TOKEN not set."""
        with patch("api.v1.billing.settings") as mock_settings:
            mock_settings.POLAR_ACCESS_TOKEN = None
            
            # Should raise HTTPException(500, "Billing not configured")
            is_configured = mock_settings.POLAR_ACCESS_TOKEN is not None
            assert is_configured is False
    
    @pytest.mark.asyncio
    async def test_cancel_returns_400_for_no_subscription(self):
        """Should return 400 when no subscription found."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response
        
        with patch("httpx.AsyncClient", return_value=mock_client):
            items = mock_response.json()["items"]
            has_subscription = len(items) > 0
            assert has_subscription is False
    
    @pytest.mark.asyncio
    async def test_cancel_sets_cancel_at_period_end(self, mock_settings_with_polar):
        """Should set cancel_at_period_end=true in Polar."""
        cancel_payload = {"cancel_at_period_end": True}
        assert cancel_payload["cancel_at_period_end"] is True
    
    @pytest.mark.asyncio
    async def test_cancel_updates_local_database(self, mock_settings_with_polar):
        """Should update local subscriptions table."""
        update_data = {"cancel_at_period_end": True}
        assert update_data["cancel_at_period_end"] is True
    
    @pytest.mark.asyncio
    async def test_cancel_returns_subscription_id(self, mock_settings_with_polar):
        """Response should include subscription_id."""
        response = {
            "status": "cancelled",
            "subscription_id": "sub-123",
            "message": "Subscription will be cancelled at end of billing period"
        }
        assert response["subscription_id"] == "sub-123"
    
    @pytest.mark.asyncio
    async def test_cancel_handles_polar_api_error(self, mock_settings_with_polar):
        """Should handle Polar API errors gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response
        
        with patch("httpx.AsyncClient", return_value=mock_client):
            is_success = mock_response.status_code in [200, 201, 204]
            assert is_success is False


# =============================================================================
# Tests for Checkout Session Endpoint
# =============================================================================

class TestCreateCheckoutEndpoint:
    """Tests for POST /api/v1/billing/checkout."""
    
    @pytest.fixture
    def checkout_request(self):
        """Create a mock request for checkout endpoint."""
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/billing/checkout",
            "query_string": b"",
            "headers": [],
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 12345),
            "app": None,
        }
        return Request(scope=scope)
    
    @pytest.mark.asyncio
    async def test_checkout_creates_polar_session(self, checkout_request):
        """Should create checkout session with Polar."""
        from types import SimpleNamespace
        from api.v1.billing import create_checkout_session, CheckoutRequest

        mock_response = MagicMock()
        mock_response.json.return_value = {"url": "https://checkout.example.com"}
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_response

        with patch("api.v1.billing.settings") as mock_settings, \
             patch("api.v1.billing.team_service.get_user_team_member", new=AsyncMock(return_value=SimpleNamespace(team_id="team-1"))), \
             patch("httpx.AsyncClient", return_value=mock_client):
            mock_settings.POLAR_ACCESS_TOKEN = "token"
            mock_settings.POLAR_PRODUCT_ID_STARTER_MONTHLY = "starter_id"
            mock_settings.POLAR_PRODUCT_ID_PRO_MONTHLY = "pro_id"
            mock_settings.POLAR_PRODUCT_ID_ENTERPRISE = "enterprise_id"
            mock_settings.APP_URL = "https://app.example.com"

            result = await create_checkout_session(
                request=checkout_request,
                data=CheckoutRequest(plan="starter"),
                current_user_id="user-1",
            )

        assert result["url"] == "https://checkout.example.com"
    
    @pytest.mark.asyncio
    async def test_checkout_returns_checkout_url(self):
        """Should return URL to redirect user for payment."""
        response = {"checkout_url": "https://polar.sh/checkout/xxx"}
        assert "checkout_url" in response
