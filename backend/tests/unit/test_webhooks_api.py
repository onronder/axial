from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request

from api.v1.webhooks import polar_webhook, webhook_health
from api.v1.webhooks import HTTPException


def _make_request(body: bytes, headers: dict):
    async def receive():
        return {"type": "http.request", "body": body}

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/webhooks/polar",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
    }
    return Request(scope, receive)


@pytest.mark.asyncio
async def test_polar_webhook_missing_signature():
    request = _make_request(b"{}", {})
    with pytest.raises(HTTPException) as exc:
        await polar_webhook(request)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_polar_webhook_invalid_signature():
    request = _make_request(b"{}", {
        "webhook-signature": "sig",
        "webhook-id": "id",
        "webhook-timestamp": "ts",
    })

    with patch("api.v1.webhooks.subscription_service.verify_signature", return_value=False), \
         patch("api.v1.webhooks.redis.from_url") as mock_redis:
        mock_client = AsyncMock()
        mock_client.get.return_value = None
        mock_redis.return_value = mock_client

        with pytest.raises(HTTPException) as exc:
            await polar_webhook(request)
        assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_polar_webhook_idempotent_returns_early():
    request = _make_request(b"{}", {
        "webhook-signature": "sig",
        "webhook-id": "id",
        "webhook-timestamp": "ts",
    })

    with patch("api.v1.webhooks.redis.from_url") as mock_redis:
        mock_client = AsyncMock()
        mock_client.get.return_value = "processed"
        mock_redis.return_value = mock_client

        result = await polar_webhook(request)

    assert result["idempotent"] is True


@pytest.mark.asyncio
async def test_polar_webhook_valid_signature_processes():
    request = _make_request(b"{\"type\": \"event\"}", {
        "webhook-signature": "sig",
        "webhook-id": "id",
        "webhook-timestamp": "ts",
    })

    with patch("api.v1.webhooks.subscription_service.verify_signature", return_value=True), \
         patch("api.v1.webhooks.subscription_service.handle_webhook", new=AsyncMock()) as mock_handle, \
         patch("api.v1.webhooks.redis.from_url") as mock_redis:
        mock_client = AsyncMock()
        mock_client.get.return_value = None
        mock_redis.return_value = mock_client

        result = await polar_webhook(request)

    assert result["status"] == "received"
    mock_handle.assert_awaited_once()


@pytest.mark.asyncio
async def test_polar_webhook_redis_error_falls_back():
    request = _make_request(b"{\"type\": \"event\"}", {
        "webhook-signature": "sig",
        "webhook-id": "id",
        "webhook-timestamp": "ts",
    })

    with patch("api.v1.webhooks.redis.from_url", side_effect=RuntimeError("redis down")), \
         patch("api.v1.webhooks.subscription_service.verify_signature", return_value=True), \
         patch("api.v1.webhooks.subscription_service.handle_webhook", new=AsyncMock()):
        result = await polar_webhook(request)

    assert result["status"] == "received"


@pytest.mark.asyncio
async def test_polar_webhook_idempotency_set_failure_is_non_blocking():
    request = _make_request(b"{\"type\": \"event\"}", {
        "webhook-signature": "sig",
        "webhook-id": "id",
        "webhook-timestamp": "ts",
    })

    with patch("api.v1.webhooks.subscription_service.verify_signature", return_value=True), \
         patch("api.v1.webhooks.subscription_service.handle_webhook", new=AsyncMock()), \
         patch("api.v1.webhooks.redis.from_url") as mock_redis:
        mock_client = AsyncMock()
        mock_client.get.return_value = None
        mock_client.set.side_effect = RuntimeError("set failed")
        mock_redis.return_value = mock_client

        result = await polar_webhook(request)

    assert result["status"] == "received"


@pytest.mark.asyncio
async def test_polar_webhook_processing_error_returns_500():
    request = _make_request(b"{\"type\": \"event\"}", {
        "webhook-signature": "sig",
        "webhook-id": "id",
        "webhook-timestamp": "ts",
    })

    with patch("api.v1.webhooks.subscription_service.verify_signature", return_value=True), \
         patch("api.v1.webhooks.subscription_service.handle_webhook", side_effect=RuntimeError("boom")), \
         patch("api.v1.webhooks.redis.from_url") as mock_redis:
        mock_client = AsyncMock()
        mock_client.get.return_value = None
        mock_redis.return_value = mock_client

        with pytest.raises(HTTPException) as exc:
            await polar_webhook(request)

    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_webhook_health_returns_status():
    result = await webhook_health()
    assert result["status"] == "healthy"
