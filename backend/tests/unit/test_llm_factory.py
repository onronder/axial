from unittest.mock import MagicMock, patch

import pytest

from core.config import settings
from services.llm_factory import LLMFactory


def test_get_model_downgrades_viewer_to_fast(monkeypatch):
    monkeypatch.setattr(settings, "SECONDARY_MODEL_PROVIDER", "groq")
    monkeypatch.setattr(settings, "SECONDARY_MODEL_NAME", "fast-model")
    monkeypatch.setattr(settings, "PRIMARY_MODEL_PROVIDER", "openai")
    monkeypatch.setattr(settings, "PRIMARY_MODEL_NAME", "smart-model")

    sentinel = object()
    with patch.object(LLMFactory, "_create_groq", return_value=sentinel) as mock_groq:
        llm, metadata = LLMFactory.get_model(
            requested_tier=settings.MODEL_ALIAS_SMART,
            user_plan="pro",
            user_role="viewer",
        )

    assert llm is sentinel
    assert metadata["actual_tier"] == "fast"
    assert metadata["upsell"] is False
    mock_groq.assert_called_once()


def test_get_model_downgrades_free_plan_with_upsell(monkeypatch):
    monkeypatch.setattr(settings, "SECONDARY_MODEL_PROVIDER", "groq")
    monkeypatch.setattr(settings, "SECONDARY_MODEL_NAME", "fast-model")
    monkeypatch.setattr(settings, "PRIMARY_MODEL_PROVIDER", "openai")
    monkeypatch.setattr(settings, "PRIMARY_MODEL_NAME", "smart-model")

    sentinel = object()
    with patch.object(LLMFactory, "_create_groq", return_value=sentinel):
        _, metadata = LLMFactory.get_model(
            requested_tier=settings.MODEL_ALIAS_SMART,
            user_plan="free",
            user_role="member",
        )

    assert metadata["actual_tier"] == "fast"
    assert metadata["upsell"] is True


def test_get_model_unsupported_provider_raises():
    with pytest.raises(ValueError):
        LLMFactory.get_model(
            provider="unknown",
            model_name="custom",
            requested_tier="custom",
            user_plan="pro",
        )


def test_create_groq_requires_api_key(monkeypatch):
    monkeypatch.setattr(settings, "GROQ_API_KEY", None)
    module = MagicMock()
    module.ChatGroq = MagicMock()
    monkeypatch.setitem(__import__("sys").modules, "langchain_groq", module)

    with pytest.raises(ValueError):
        LLMFactory._create_groq("model", 0, False, None)


def test_get_model_uses_primary_on_smart_tier(monkeypatch):
    monkeypatch.setattr(settings, "PRIMARY_MODEL_PROVIDER", "openai")
    monkeypatch.setattr(settings, "PRIMARY_MODEL_NAME", "smart-model")
    monkeypatch.setattr(settings, "SECONDARY_MODEL_PROVIDER", "groq")
    monkeypatch.setattr(settings, "SECONDARY_MODEL_NAME", "fast-model")

    sentinel = object()
    with patch.object(LLMFactory, "_create_openai", return_value=sentinel) as mock_openai:
        llm, metadata = LLMFactory.get_model(
            requested_tier=settings.MODEL_ALIAS_SMART,
            user_plan="pro",
            user_role="member",
        )

    assert llm is sentinel
    assert metadata["actual_tier"] == "smart"
    mock_openai.assert_called_once_with("smart-model", 0, False, None)


def test_get_model_fallbacks_to_secondary_for_unknown_tier(monkeypatch):
    monkeypatch.setattr(settings, "SECONDARY_MODEL_PROVIDER", "groq")
    monkeypatch.setattr(settings, "SECONDARY_MODEL_NAME", "fast-model")
    monkeypatch.setattr(settings, "PRIMARY_MODEL_PROVIDER", "openai")
    monkeypatch.setattr(settings, "PRIMARY_MODEL_NAME", "smart-model")

    sentinel = object()
    with patch.object(LLMFactory, "_create_groq", return_value=sentinel) as mock_groq:
        llm, metadata = LLMFactory.get_model(
            requested_tier="unknown",
            user_plan="pro",
            user_role="member",
        )

    assert llm is sentinel
    assert metadata["actual_tier"] == "unknown"
    mock_groq.assert_called_once_with("fast-model", 0, False, None)


def test_create_openai_passes_max_tokens(monkeypatch):
    sentinel = object()
    with patch("services.llm_factory.ChatOpenAI", return_value=sentinel) as chat_openai:
        llm = LLMFactory._create_openai("gpt-test", 0.2, True, 512)

    assert llm is sentinel
    chat_openai.assert_called_once_with(model="gpt-test", temperature=0.2, streaming=True, api_key=settings.OPENAI_API_KEY, max_tokens=512)


def test_create_groq_import_error(monkeypatch):
    original_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "langchain_groq":
            raise ImportError("missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)

    with pytest.raises(ImportError):
        LLMFactory._create_groq("model", 0, False, None)


def test_create_groq_success(monkeypatch):
    class DummyGroq:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    module = MagicMock()
    module.ChatGroq = DummyGroq
    monkeypatch.setitem(__import__("sys").modules, "langchain_groq", module)
    monkeypatch.setattr(settings, "GROQ_API_KEY", "groq-key")

    llm = LLMFactory._create_groq("model-x", 0.1, True, 99)
    assert isinstance(llm, DummyGroq)
    assert llm.kwargs["model_name"] == "model-x"
    assert llm.kwargs["max_tokens"] == 99


def test_create_grok_requires_api_key(monkeypatch):
    monkeypatch.setattr(settings, "GROK_API_KEY", None)
    with pytest.raises(ValueError):
        LLMFactory._create_grok("grok-test", 0, False, None)


def test_create_grok_passes_base_url(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(settings, "GROK_API_KEY", "grok-key")
    monkeypatch.setattr(settings, "GROK_BASE_URL", "https://api.x.ai/v1")

    with patch("services.llm_factory.ChatOpenAI", return_value=sentinel) as chat_openai:
        llm = LLMFactory._create_grok("grok-test", 0.2, True, 256)

    assert llm is sentinel
    chat_openai.assert_called_once_with(
        model="grok-test",
        temperature=0.2,
        streaming=True,
        api_key=settings.GROK_API_KEY,
        base_url=settings.GROK_BASE_URL,
        max_tokens=256,
    )


def test_get_model_allow_override_uses_explicit_provider(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(settings, "GROK_API_KEY", "grok-key")

    with patch.object(LLMFactory, "_create_grok", return_value=sentinel) as create_grok:
        llm, metadata = LLMFactory.get_model(
            provider="grok",
            model_name="grok-test",
            user_plan="pro",
            requested_tier=settings.MODEL_ALIAS_FAST,
            allow_override=True,
        )

    assert llm is sentinel
    assert metadata["provider"] == "grok"
    assert metadata["model"] == "grok-test"
    create_grok.assert_called_once_with("grok-test", 0, False, None)


def test_get_primary_and_secondary_models(monkeypatch):
    sentinel_primary = object()
    sentinel_secondary = object()

    with patch.object(LLMFactory, "get_model", return_value=(sentinel_primary, {})) as get_model:
        assert LLMFactory.get_primary_model(streaming=True) is sentinel_primary
        get_model.assert_called_once()

    with patch.object(LLMFactory, "get_model", return_value=(sentinel_secondary, {})) as get_model:
        assert LLMFactory.get_secondary_model(streaming=False) is sentinel_secondary
        get_model.assert_called_once()


def test_get_guardrail_model_uses_groq(monkeypatch):
    sentinel = object()
    with patch.object(LLMFactory, "_create_groq", return_value=sentinel) as create_groq:
        assert LLMFactory.get_guardrail_model(streaming=False, temperature=0.1) is sentinel
        create_groq.assert_called_once_with(settings.GUARDRAIL_MODEL_NAME, 0.1, False, None)
