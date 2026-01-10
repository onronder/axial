from unittest.mock import MagicMock

import httpx
import pytest
from fastapi import FastAPI
from starlette.requests import Request

from core.tracing import RequestTracingMiddleware, get_request_logger


@pytest.mark.asyncio
async def test_request_tracing_adds_headers():
    app = FastAPI()
    app.add_middleware(RequestTracingMiddleware)

    @app.get("/ok")
    async def ok():
        return {"status": "ok"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ok")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert "X-Response-Time" in response.headers


@pytest.mark.asyncio
async def test_request_tracing_logs_user_hint_with_bearer():
    app = FastAPI()
    app.add_middleware(RequestTracingMiddleware)

    @app.get("/ok")
    async def ok():
        return {"status": "ok"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ok", headers={"Authorization": "Bearer abcdef123456"})

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_request_tracing_handles_exceptions():
    app = FastAPI()
    app.add_middleware(RequestTracingMiddleware)

    @app.get("/boom")
    async def boom():
        raise RuntimeError("boom")

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/boom")

    assert response.status_code == 500


def test_request_logger_formats_message(monkeypatch):
    fake_logger = MagicMock()
    monkeypatch.setattr("core.tracing.logger", fake_logger)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "client": ("127.0.0.1", 1234),
    }
    request = Request(scope)
    request.state.request_id = "abcd1234"

    logger = get_request_logger(request)
    logger.info("hello")

    fake_logger.info.assert_called_once_with("[abcd1234] hello")


def test_request_logger_level_helpers(monkeypatch):
    fake_logger = MagicMock()
    monkeypatch.setattr("core.tracing.logger", fake_logger)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "client": ("127.0.0.1", 1234),
    }
    request = Request(scope)
    request.state.request_id = "req-9999"

    logger = get_request_logger(request)
    logger.debug("debug")
    logger.warning("warn")
    logger.error("err")
    logger.exception("boom")

    fake_logger.debug.assert_called_once_with("[req-9999] debug")
    fake_logger.warning.assert_called_once_with("[req-9999] warn")
    fake_logger.error.assert_called_once_with("[req-9999] err")
    fake_logger.exception.assert_called_once_with("[req-9999] boom")
