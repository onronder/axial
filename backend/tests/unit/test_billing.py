import pytest
from unittest.mock import patch, Mock, AsyncMock
from api.v1.billing import list_plans
from core.config import settings

@pytest.fixture
def mock_settings():
    with patch("api.v1.billing.settings") as mock:
        mock.POLAR_ACCESS_TOKEN = "test_token"
        mock.POLAR_PRODUCT_ID_STARTER_MONTHLY = "starter_id"
        mock.POLAR_PRODUCT_ID_PRO_MONTHLY = "pro_id"
        yield mock

@pytest.mark.asyncio
async def test_list_plans_success(mock_settings):
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
        plans = await list_plans()

    assert len(plans) == 2
    assert plans[0].type == "starter"
    assert plans[1].type == "pro"
    assert plans[0].price_amount == 1000
    assert plans[1].price_amount == 2000

@pytest.mark.asyncio
async def test_list_plans_no_token():
    with patch("api.v1.billing.settings") as mock_settings:
        mock_settings.POLAR_ACCESS_TOKEN = None
        plans = await list_plans()
        assert plans == []

@pytest.mark.asyncio
async def test_list_plans_api_error(mock_settings):
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.side_effect = Exception("API Error")

    with patch("httpx.AsyncClient", return_value=mock_client):
        plans = await list_plans()
        assert plans == []
