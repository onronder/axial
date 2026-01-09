from types import SimpleNamespace

import pytest

from services.guardrails import GuardrailService, GuardrailResult
from services import guardrails as guardrails_module


class FakeModel:
    def __init__(self, content):
        self._content = content

    async def ainvoke(self, prompt):
        return SimpleNamespace(content=self._content)


def test_parse_json_response_handles_code_block():
    service = GuardrailService()
    raw = "```json\n{\"language\":\"tr\",\"is_safe\":false}\n```"
    result = service._parse_json_response(raw)
    assert result.language == "tr"
    assert result.is_safe is False


def test_parse_json_response_handles_wrapped_json():
    service = GuardrailService()
    raw = "prefix {\"intent\":\"OFF_TOPIC\"} suffix"
    result = service._parse_json_response(raw)
    assert result.intent == "OFF_TOPIC"


def test_parse_json_response_handles_non_dict():
    service = GuardrailService()
    raw = "```json\n[1, 2, 3]\n```"
    result = service._parse_json_response(raw)
    assert result.intent == "RAG_QUERY"


def test_parse_json_response_handles_invalid_json():
    service = GuardrailService()
    raw = "not-json"
    result = service._parse_json_response(raw)
    assert result.intent == "RAG_QUERY"


@pytest.mark.asyncio
async def test_analyze_query_returns_result_from_model():
    service = GuardrailService()
    service._get_model = lambda: FakeModel("{\"language\":\"en\",\"is_safe\":true,\"intent\":\"RAG_QUERY\",\"complexity\":\"SIMPLE\"}")

    result = await service.analyze_query("hello")
    assert result.language == "en"
    assert result.intent == "RAG_QUERY"


@pytest.mark.asyncio
async def test_analyze_query_fallback_on_error():
    service = GuardrailService()

    async def raise_error(prompt):
        raise RuntimeError("boom")

    service._get_model = lambda: SimpleNamespace(ainvoke=raise_error)

    result = await service.analyze_query("hello")
    assert isinstance(result, GuardrailResult)
    assert result.intent == "RAG_QUERY"


def test_get_model_falls_back_to_openai(monkeypatch):
    service = GuardrailService()
    sentinel = FakeModel("{\"language\":\"en\"}")

    monkeypatch.setattr(guardrails_module.LLMFactory, "get_guardrail_model", lambda: (_ for _ in ()).throw(Exception("no groq")))
    monkeypatch.setattr(guardrails_module.LLMFactory, "get_model", lambda **kwargs: (sentinel, {"actual_tier": "fast"}))

    model = service._get_model()
    assert model is sentinel


def test_get_model_initializes_guardrail_model(monkeypatch):
    service = GuardrailService()
    sentinel = FakeModel("{\"language\":\"en\"}")

    monkeypatch.setattr(guardrails_module.LLMFactory, "get_guardrail_model", lambda: sentinel)
    model = service._get_model()
    assert model is sentinel


def test_guardrail_result_to_dict():
    result = GuardrailResult(language="tr", is_safe=False, intent="OFF_TOPIC", complexity="SIMPLE", reply="no")
    assert result.to_dict()["language"] == "tr"
