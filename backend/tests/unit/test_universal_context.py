import json
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import BackgroundTasks
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse

sys.modules.setdefault("boto3", MagicMock())
sys.modules.setdefault("botocore", MagicMock())
sys.modules.setdefault("botocore.config", MagicMock())
sys.modules.setdefault("botocore.exceptions", MagicMock())

from api.v1.chat import ChatRequest, chat_endpoint
from core.scopes import build_scope_uri
from services.scope_analysis import ScopeAnalysisResult, ScopeClassification, ScopeStats
from services.scope_identity import synthesize_and_save_identity


def _make_request() -> Request:
    scope = {"type": "http", "method": "POST", "path": "/chat", "headers": []}
    return Request(scope)


def _make_chain_table(data=None):
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.in_.return_value = table
    table.limit.return_value = table
    table.single.return_value = table
    table.update.return_value = table
    table.upsert.return_value = table
    table.insert.return_value = table
    table.execute.return_value = SimpleNamespace(data=data)
    return table


class DummyRpcResponse:
    def __init__(self, data):
        self.data = data

    def execute(self):
        return self


def test_build_scope_uri_github_valid():
    assert (
        build_scope_uri("github", {"repository": "acme/project", "branch": "dev"})
        == "github://acme/project@dev"
    )


def test_build_scope_uri_github_missing_repo():
    with pytest.raises(ValueError):
        build_scope_uri("github", {"branch": "main"})


def test_build_scope_uri_s3_normalizes_prefix():
    assert (
        build_scope_uri("s3", {"bucket_name": "docs-bucket", "prefix": "manuals/2024/"})
        == "s3://docs-bucket/manuals/2024"
    )


def test_build_scope_uri_s3_empty_prefix():
    assert build_scope_uri("s3", {"bucket": "docs-bucket", "prefix": ""}) == "s3://docs-bucket/"


def test_build_scope_uri_s3_missing_bucket():
    with pytest.raises(ValueError):
        build_scope_uri("s3", {"prefix": "x"})


def test_build_scope_uri_box_valid():
    assert (
        build_scope_uri("box", {"folder_id": "123", "folder_name": "Marketing"})
        == "box://folder/123:Marketing"
    )


def test_build_scope_uri_box_missing_folder_name():
    with pytest.raises(ValueError):
        build_scope_uri("box", {"folder_id": "123"})


@pytest.mark.asyncio
async def test_synthesize_and_save_identity_stats_and_tree():
    documents = [
        SimpleNamespace(
            filename="src/app.py",
            size_bytes=120,
            metadata={"path": "src/app.py"},
        ),
        SimpleNamespace(
            filename="docs/readme.md",
            size_bytes=80,
            metadata={"path": "docs/readme.md"},
        ),
    ]

    scope_table = _make_chain_table(data={"user_id": "user-1"})
    docs_table = _make_chain_table(data=[])
    docs_table.insert.return_value.execute.return_value = SimpleNamespace(data=[{"id": "doc-1"}])

    def table_side_effect(name):
        return {"scope_identities": scope_table, "documents": docs_table}.get(name, _make_chain_table())

    supabase = MagicMock()
    supabase.table.side_effect = table_side_effect
    supabase.rpc.return_value.execute.return_value = SimpleNamespace(data="doc-1")

    with patch("services.scope_identity.get_supabase", return_value=supabase), \
         patch("services.scope_identity.generate_embeddings_batch_sync", return_value=[[0.1]]), \
         patch("services.scope_identity.team_service.get_effective_plan", new_callable=AsyncMock, return_value="pro"):
        await synthesize_and_save_identity(
            "github://org/repo@main",
            documents,
            organization_id="org-1",
            user_id="user-1",
        )

    rpc_args = supabase.rpc.call_args[0]
    assert rpc_args[0] == "upsert_scope_identity_document"
    payload = rpc_args[1]
    assert payload["p_attributes"]["file_count"] == 2
    assert payload["p_attributes"]["size"] == 200
    assert ".py" in payload["p_attributes"]["languages"]
    assert ".md" in payload["p_attributes"]["languages"]
    assert "SCOPE IDENTITY DOCUMENT" in payload["p_summary"]
    assert "src" in payload["p_file_tree"]
    assert "docs" in payload["p_file_tree"]


@pytest.mark.asyncio
async def test_chat_dominant_scope_proceeds_with_generation():
    docs = [
        {"content": "A", "metadata": {"scope_id": "github://org/repo@main"}, "vector_score": 0.9}
    ]
    supabase = MagicMock()
    supabase.rpc.return_value = DummyRpcResponse(docs)

    from services.guardrails import GuardrailResult
    guardrail = GuardrailResult(is_safe=True, intent="RAG_QUERY", complexity="SIMPLE", language="en", reply=None)
    analysis = ScopeAnalysisResult(
        classification=ScopeClassification.DOMINANT,
        primary_scope_id="github://org/repo@main",
        dominance_ratio=0.9,
        primary_scope_stats=ScopeStats(scope_id="github://org/repo@main", count=1, score_sum=0.9),
        total_docs=1,
        scoped_docs=1,
        distribution={},
    )

    async def fake_stream(*_args, **_kwargs):
        if False:
            yield ""  # pragma: no cover
        return

    with patch("api.v1.chat.get_supabase", return_value=supabase), \
         patch("api.v1.chat.team_service.get_organization_id", new_callable=AsyncMock, return_value="org-1"), \
         patch("api.v1.chat.team_service.get_effective_plan", new_callable=AsyncMock, return_value="pro"), \
         patch("api.v1.chat.check_llm_quota", new_callable=AsyncMock, return_value={"balance": 100}), \
         patch("api.v1.chat.record_llm_usage", new_callable=AsyncMock, return_value=None), \
         patch("api.v1.chat.guardrail_service.analyze_query_with_context", return_value=guardrail), \
         patch("api.v1.chat.llm_router.select_model", return_value=SimpleNamespace(provider="openai", model="gpt-4o")), \
         patch("api.v1.chat.OpenAIEmbeddings.embed_query", return_value=[0.1, 0.2]), \
         patch("api.v1.chat.analyze_scope_distribution", return_value=analysis), \
         patch("api.v1.chat.fetch_scope_identity", return_value={"type": "github_repo"}), \
         patch("api.v1.chat.filter_docs_by_scope", return_value=docs), \
         patch("api.v1.chat.stream_chat_response", side_effect=fake_stream), \
         patch("api.v1.chat.LLMFactory.get_model", return_value=(object(), {})):
        response = await chat_endpoint(
            request=_make_request(),
            payload=ChatRequest(query="test", stream=True, history=[]),
            background_tasks=BackgroundTasks(),
            user_id="user-1",
        )

    assert isinstance(response, StreamingResponse)


@pytest.mark.asyncio
async def test_chat_fragmented_scope_returns_300():
    docs = [
        {"content": "A", "metadata": {"scope_id": "github://org/repo@main"}, "vector_score": 0.9},
        {"content": "B", "metadata": {"scope_id": "s3://bucket/docs"}, "vector_score": 0.8},
    ]
    supabase = MagicMock()
    supabase.rpc.return_value = DummyRpcResponse(docs)

    from services.guardrails import GuardrailResult
    guardrail = GuardrailResult(is_safe=True, intent="RAG_QUERY", complexity="SIMPLE", language="en", reply=None)
    analysis = ScopeAnalysisResult(
        classification=ScopeClassification.FRAGMENTED,
        primary_scope_id="github://org/repo@main",
        dominance_ratio=0.5,
        primary_scope_stats=ScopeStats(scope_id="github://org/repo@main", count=1, score_sum=0.9),
        secondary_scopes=[ScopeStats(scope_id="s3://bucket/docs", count=1, score_sum=0.8)],
        total_docs=2,
        scoped_docs=2,
        distribution={},
    )

    scope_infos = [
        {"id": "github://org/repo@main", "type": "github_repo", "summary": "Backend"},
        {"id": "s3://bucket/docs", "type": "s3_bucket", "summary": "Manuals"},
    ]

    with patch("api.v1.chat.get_supabase", return_value=supabase), \
         patch("api.v1.chat.team_service.get_organization_id", new_callable=AsyncMock, return_value="org-1"), \
         patch("api.v1.chat.team_service.get_effective_plan", new_callable=AsyncMock, return_value="pro"), \
         patch("api.v1.chat.check_llm_quota", new_callable=AsyncMock, return_value={"balance": 100}), \
         patch("api.v1.chat.guardrail_service.analyze_query_with_context", return_value=guardrail), \
         patch("api.v1.chat.llm_router.select_model", return_value=SimpleNamespace(provider="openai", model="gpt-4o")), \
         patch("api.v1.chat.OpenAIEmbeddings.embed_query", return_value=[0.1, 0.2]), \
         patch("api.v1.chat.analyze_scope_distribution", return_value=analysis), \
         patch("api.v1.chat.fetch_scope_candidates_with_summaries", return_value=scope_infos), \
         patch("api.v1.chat.LLMFactory.get_model", return_value=(object(), {})) as get_model:
        response = await chat_endpoint(
            request=_make_request(),
            payload=ChatRequest(query="test", stream=False, history=[]),
            background_tasks=BackgroundTasks(),
            user_id="user-1",
        )

    assert isinstance(response, JSONResponse)
    assert response.status_code == 300
    body = json.loads(response.body.decode("utf-8"))
    assert body["action"] == "clarify_scope"
    candidate_ids = [c["id"] for c in body["candidates"]]
    assert "github://org/repo@main" in candidate_ids
    assert "s3://bucket/docs" in candidate_ids
    assert get_model.call_count == 0
