import builtins
import importlib
import sys
import types
from unittest.mock import MagicMock, patch

import pytest


def load_main():
    sys.modules.setdefault("magic", types.ModuleType("magic"))
    if "main" in sys.modules:
        return importlib.reload(sys.modules["main"])
    return importlib.import_module("main")


def test_configure_cors_dev_defaults(monkeypatch):
    main = load_main()
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    origins = main.configure_cors()
    assert "http://localhost:3000" in origins


def test_configure_cors_prod_requires_origins(monkeypatch):
    main = load_main()
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    with pytest.raises(RuntimeError):
        main.configure_cors()


def test_configure_cors_prod_accepts_https(monkeypatch):
    main = load_main()
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://app.example.com,http://insecure.example.com")
    origins = main.configure_cors()
    assert "https://app.example.com" in origins
    assert "http://insecure.example.com" in origins


def test_configure_cors_rejects_wildcard(monkeypatch):
    main = load_main()
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://app.example.com,*")
    with pytest.raises(RuntimeError):
        main.configure_cors()


def test_build_cors_origins_fallback(monkeypatch):
    main = load_main()
    monkeypatch.setenv("ENVIRONMENT", "development")
    with patch("main.configure_cors", side_effect=RuntimeError("boom")):
        origins = main.build_cors_origins()
    assert origins == ["*"]


def test_build_cors_origins_raises_in_prod(monkeypatch):
    main = load_main()
    monkeypatch.setenv("ENVIRONMENT", "production")
    with patch("main.configure_cors", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            main.build_cors_origins()


def test_init_sentry_success_path(monkeypatch):
    main = load_main()
    fake_sentry = types.ModuleType("sentry_sdk")
    fake_sentry.init = MagicMock()

    fastapi_mod = types.ModuleType("sentry_sdk.integrations.fastapi")
    starlette_mod = types.ModuleType("sentry_sdk.integrations.starlette")
    logging_mod = types.ModuleType("sentry_sdk.integrations.logging")

    class DummyIntegration:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    fastapi_mod.FastApiIntegration = DummyIntegration
    starlette_mod.StarletteIntegration = DummyIntegration
    logging_mod.LoggingIntegration = DummyIntegration

    monkeypatch.setitem(sys.modules, "sentry_sdk", fake_sentry)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.fastapi", fastapi_mod)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.starlette", starlette_mod)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.logging", logging_mod)

    monkeypatch.setattr(main.settings, "SENTRY_DSN", "https://example")
    monkeypatch.setattr(main.settings, "ENVIRONMENT", "production")

    main.init_sentry()
    fake_sentry.init.assert_called_once()


def test_init_sentry_import_error(monkeypatch):
    main = load_main()
    monkeypatch.setattr(main.settings, "SENTRY_DSN", "https://example")
    monkeypatch.setattr(main.settings, "ENVIRONMENT", "production")

    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "sentry_sdk":
            raise ImportError("missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    main.init_sentry()


def test_init_sentry_handles_exception(monkeypatch):
    main = load_main()
    fake_sentry = types.ModuleType("sentry_sdk")

    def raise_init(*args, **kwargs):
        raise RuntimeError("boom")

    fake_sentry.init = raise_init

    fastapi_mod = types.ModuleType("sentry_sdk.integrations.fastapi")
    starlette_mod = types.ModuleType("sentry_sdk.integrations.starlette")
    logging_mod = types.ModuleType("sentry_sdk.integrations.logging")

    class DummyIntegration:
        def __init__(self, *args, **kwargs):
            pass

    fastapi_mod.FastApiIntegration = DummyIntegration
    starlette_mod.StarletteIntegration = DummyIntegration
    logging_mod.LoggingIntegration = DummyIntegration

    monkeypatch.setitem(sys.modules, "sentry_sdk", fake_sentry)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.fastapi", fastapi_mod)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.starlette", starlette_mod)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.logging", logging_mod)

    monkeypatch.setattr(main.settings, "SENTRY_DSN", "https://example")
    monkeypatch.setattr(main.settings, "ENVIRONMENT", "production")

    main.init_sentry()


def test_warn_optional_reranker_config_missing_key(monkeypatch):
    main = load_main()
    monkeypatch.setattr(main.settings, "COHERE_API_KEY", None)

    with patch.object(main.logger, "warning") as mock_warning:
        main.warn_optional_reranker_config()

    mock_warning.assert_called_once()
    assert "COHERE_API_KEY" in mock_warning.call_args[0][0]


def test_warn_optional_reranker_config_missing_package(monkeypatch):
    main = load_main()
    monkeypatch.setattr(main.settings, "COHERE_API_KEY", "key")
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "cohere":
            raise ImportError("missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with patch.object(main.logger, "warning") as mock_warning:
        main.warn_optional_reranker_config()

    mock_warning.assert_called_once()
    assert "cohere package" in mock_warning.call_args[0][0]


def test_configure_cors_adds_vercel_preview(monkeypatch):
    main = load_main()
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    monkeypatch.setenv("VERCEL_ENV", "preview")
    origins = main.configure_cors()
    assert "https://*.vercel.app" in origins


@pytest.mark.asyncio
async def test_health_check_healthy(monkeypatch):
    main = load_main()
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock(data=[{"id": 1}])

    monkeypatch.setenv("ENVIRONMENT", "development")
    with patch("main.get_supabase", return_value=supabase):
        with patch("redis.from_url") as mock_redis:
            mock_redis.return_value.ping.return_value = True
            result = await main.health_check()

    assert result["status"] == "healthy"
    assert result["services"]["database"] == "up"
    assert result["services"]["redis"] == "up"


@pytest.mark.asyncio
async def test_health_check_degraded(monkeypatch):
    main = load_main()
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock(data=[{"id": 1}])

    with patch("main.get_supabase", return_value=supabase):
        with patch("redis.from_url", side_effect=RuntimeError("redis down")):
            result = await main.health_check()

    assert result["status"] == "degraded"
    assert "redis_down" in result["issues"]


@pytest.mark.asyncio
async def test_health_check_unhealthy(monkeypatch):
    main = load_main()
    with patch("main.get_supabase", side_effect=RuntimeError("db down")):
        result = await main.health_check()

    assert result.status_code == 503


@pytest.mark.asyncio
async def test_read_root_returns_links():
    main = load_main()
    result = await main.read_root()
    assert result["health"] == "/health"


@pytest.mark.asyncio
async def test_lifespan_success(monkeypatch):
    main = load_main()
    with patch("main.check_connection", return_value=True):
        async with main.lifespan(main.app):
            pass


@pytest.mark.asyncio
async def test_lifespan_failure(monkeypatch):
    main = load_main()
    with patch("main.check_connection", side_effect=RuntimeError("db")):
        async with main.lifespan(main.app):
            pass
