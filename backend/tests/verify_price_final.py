import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from api.v1.billing import list_plans
from core.config import settings

async def verify_price_logic():
    print("🔎 Starting Final Price Logic Verification...")
    
    TEST_PRO_ID = "test_pro_id"

    # Mock Response mimicking Polar API
    mock_data = {
        "items": [
            {
                "id": TEST_PRO_ID,
                "name": "Pro Plan",
                "prices": [
                    {"price_amount": 499, "price_currency": "usd", "recurring_interval": "month"}
                ]
            }
        ]
    }

    # Patch httpx to avoid real network call during this logic check
    # We use AsyncMock for the client instance, which supports __aenter__ automatically
    mock_response = AsyncMock()
    # But json() and status_code are sync properties/methods usually on the result
    # Actually, httpx.Response attributes are sync.
    # However, if we use AsyncMock for response, we need to be careful. 
    # Let's use MagicMock for the response object itself (the thing awaited)
    # BUT wait, AsyncMock method returns a coroutine. The result of that coroutine is return_value.
    
    # Explicitly build the client mock structure
    real_response = MagicMock(name="RealResponse")
    real_response.status_code = 200
    real_response.json.return_value = mock_data
    # Ensure text is a string to avoid logging errors if it IS accessed
    real_response.text = "Mock Response Text"

    mock_client = MagicMock(name="MockClient")
    # __aenter__ must be awaitable (returns coroutine) and return the client
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    # __aexit__ must be awaitable
    mock_client.__aexit__ = AsyncMock(return_value=None)
    
    # client.get must be awaitable and return real_response
    mock_client.get = AsyncMock(return_value=real_response)
    
    # Patch the CLASS to return our mock_client when instantiated
    with patch("httpx.AsyncClient", return_value=mock_client):
        
        # Inject a dummy key if missing, just to pass the 'if not token' check in logic
        with patch.object(settings, 'POLAR_ACCESS_TOKEN', 'mock_token'):
             # Also ensure ID matches if it was None in config
            with patch.object(settings, 'POLAR_PRODUCT_ID_PRO_MONTHLY', TEST_PRO_ID):
                plans = await list_plans()

    # Assertions
    if not plans:
        print("❌ FAILED: Returned empty plan list.")
        exit(1)
    
    pro = next((p for p in plans if p['type'] == 'pro'), None)
    if not pro:
        print("❌ FAILED: Pro plan not found in processed list.")
        exit(1)

    if pro['price_amount'] == 499:
        print("✅ SUCCESS: Price parsed correctly as 499.")
    else:
        print(f"❌ FAILED: Expected 499, got {pro['price_amount']}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(verify_price_logic())
