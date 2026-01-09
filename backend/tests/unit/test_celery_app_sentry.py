import builtins
import sys
import types
from unittest.mock import MagicMock

import core.celery_app as celery_app


def test_init_celery_sentry_success(monkeypatch):
    fake_sentry = types.ModuleType("sentry_sdk")
    fake_sentry.init = MagicMock()

    celery_mod = types.ModuleType("sentry_sdk.integrations.celery")
    logging_mod = types.ModuleType("sentry_sdk.integrations.logging")

    class DummyIntegration:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    celery_mod.CeleryIntegration = DummyIntegration
    logging_mod.LoggingIntegration = DummyIntegration

    monkeypatch.setitem(sys.modules, "sentry_sdk", fake_sentry)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.celery", celery_mod)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.logging", logging_mod)
    monkeypatch.setattr(celery_app.settings, "SENTRY_DSN", "https://example")
    monkeypatch.setattr(celery_app.settings, "ENVIRONMENT", "production")

    celery_app.init_celery_sentry()
    fake_sentry.init.assert_called_once()


def test_init_celery_sentry_import_error(monkeypatch):
    monkeypatch.setattr(celery_app.settings, "SENTRY_DSN", "https://example")
    monkeypatch.setattr(celery_app.settings, "ENVIRONMENT", "production")

    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "sentry_sdk":
            raise ImportError("missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    celery_app.init_celery_sentry()


def test_init_celery_sentry_handles_exception(monkeypatch):
    fake_sentry = types.ModuleType("sentry_sdk")

    def raise_init(*args, **kwargs):
        raise RuntimeError("boom")

    fake_sentry.init = raise_init

    celery_mod = types.ModuleType("sentry_sdk.integrations.celery")
    logging_mod = types.ModuleType("sentry_sdk.integrations.logging")

    class DummyIntegration:
        def __init__(self, *args, **kwargs):
            pass

    celery_mod.CeleryIntegration = DummyIntegration
    logging_mod.LoggingIntegration = DummyIntegration

    monkeypatch.setitem(sys.modules, "sentry_sdk", fake_sentry)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.celery", celery_mod)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.logging", logging_mod)
    monkeypatch.setattr(celery_app.settings, "SENTRY_DSN", "https://example")
    monkeypatch.setattr(celery_app.settings, "ENVIRONMENT", "production")

    celery_app.init_celery_sentry()
