import importlib
import sys
import types
from unittest.mock import MagicMock


def _reload_config(monkeypatch, **env):
    for key, value in env.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    import core.config as config
    return importlib.reload(config)


def _drop_pytest_module():
    return sys.modules.pop("pytest", None)


def _restore_pytest_module(pytest_module):
    if pytest_module is not None:
        sys.modules["pytest"] = pytest_module


def test_get_polar_product_mapping_includes_enterprise(monkeypatch):
    config = _reload_config(
        monkeypatch,
        POLAR_PRODUCT_ID_ENTERPRISE="ent-prod",
        SENTRY_DSN="",
        ENVIRONMENT="test",
    )
    mapping = config.get_polar_product_mapping()
    assert mapping["ent-prod"] == config.settings.PLAN_ENTERPRISE


def test_settings_property_polar_product_mapping(monkeypatch):
    config = _reload_config(
        monkeypatch,
        POLAR_PRODUCT_ID_STARTER_MONTHLY="starter-prod",
        POLAR_PRODUCT_ID_PRO_MONTHLY="pro-prod",
        POLAR_PRODUCT_ID_ENTERPRISE="ent-prod",
        SENTRY_DSN="",
        ENVIRONMENT="test",
    )

    mapping = config.settings.POLAR_PRODUCT_MAPPING

    assert mapping["starter-prod"] == config.settings.PLAN_STARTER
    assert mapping["pro-prod"] == config.settings.PLAN_PRO
    assert mapping["ent-prod"] == config.settings.PLAN_ENTERPRISE


def test_sentry_init_success(monkeypatch):
    sentry_sdk = types.ModuleType("sentry_sdk")
    sentry_sdk.init = MagicMock()
    celery_mod = types.ModuleType("sentry_sdk.integrations.celery")
    logging_mod = types.ModuleType("sentry_sdk.integrations.logging")

    class DummyIntegration:
        def __init__(self, *args, **kwargs):
            pass

    celery_mod.CeleryIntegration = DummyIntegration
    logging_mod.LoggingIntegration = DummyIntegration

    monkeypatch.setitem(sys.modules, "sentry_sdk", sentry_sdk)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.celery", celery_mod)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.logging", logging_mod)

    pytest_module = _drop_pytest_module()
    try:
        _reload_config(
            monkeypatch,
            SENTRY_DSN="https://example.com/1",
            ENVIRONMENT="production",
            PYTEST_CURRENT_TEST=None,
        )
    finally:
        _restore_pytest_module(pytest_module)

    assert sentry_sdk.init.called


def test_sentry_import_error_logs_warning(monkeypatch):
    original_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "sentry_sdk":
            raise ImportError("no sentry")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)

    pytest_module = _drop_pytest_module()
    try:
        _reload_config(
            monkeypatch,
            SENTRY_DSN="https://example.com/1",
            ENVIRONMENT="production",
            PYTEST_CURRENT_TEST=None,
        )
    finally:
        _restore_pytest_module(pytest_module)


def test_sentry_init_exception_logs_error(monkeypatch):
    sentry_sdk = types.ModuleType("sentry_sdk")

    def boom(*args, **kwargs):
        raise RuntimeError("init failed")

    sentry_sdk.init = boom
    celery_mod = types.ModuleType("sentry_sdk.integrations.celery")
    logging_mod = types.ModuleType("sentry_sdk.integrations.logging")

    class DummyIntegration:
        def __init__(self, *args, **kwargs):
            pass

    celery_mod.CeleryIntegration = DummyIntegration
    logging_mod.LoggingIntegration = DummyIntegration

    monkeypatch.setitem(sys.modules, "sentry_sdk", sentry_sdk)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.celery", celery_mod)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.logging", logging_mod)

    pytest_module = _drop_pytest_module()
    try:
        _reload_config(
            monkeypatch,
            SENTRY_DSN="https://example.com/1",
            ENVIRONMENT="production",
            PYTEST_CURRENT_TEST=None,
        )
    finally:
        _restore_pytest_module(pytest_module)
