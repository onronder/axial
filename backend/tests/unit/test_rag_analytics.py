from unittest.mock import MagicMock, Mock

import pytest

from services.faithfulness_guard import FaithfulnessResult
from services.rag_analytics import RAGAnalyticsPayload, rag_analytics_service


@pytest.mark.asyncio
async def test_record_request_skips_when_request_id_missing():
    supabase = MagicMock()
    payload = RAGAnalyticsPayload(
        request_id=None,
        organization_id="org-1",
        conversation_id="conv-1",
        message_id=None,
        user_id="user-1",
        query_text="What is the policy?",
    )

    result = await rag_analytics_service.record_request(supabase, payload)

    assert result is False
    supabase.table.assert_not_called()


@pytest.mark.asyncio
async def test_record_request_inserts_denormalized_metrics():
    supabase = MagicMock()
    supabase.table.return_value.insert.return_value.execute.return_value = Mock(data=[{"id": "1"}])
    payload = RAGAnalyticsPayload(
        request_id="req-1",
        organization_id="org-1",
        conversation_id="conv-1",
        message_id="msg-1",
        user_id="user-1",
        query_text="What is the policy?",
        search_query="policy",
        retrieval_docs=[
            {"similarity": 0.8, "rerank_score": 0.7},
            {"vector_score": 0.6, "rerank_score": 0.5},
        ],
        high_quality_docs=[{"similarity": 0.8}],
        source_count=2,
        faithfulness_result=FaithfulnessResult(
            checked=True,
            faithful=False,
            score=0.3,
            warning="Needs review",
        ),
    )

    result = await rag_analytics_service.record_request(supabase, payload)

    assert result is True
    insert_payload = supabase.table.return_value.insert.call_args[0][0]
    assert insert_payload["request_id"] == "req-1"
    assert insert_payload["message_id"] == "msg-1"
    assert insert_payload["retrieval_doc_count"] == 2
    assert insert_payload["avg_similarity"] == 0.7
    assert insert_payload["avg_rerank_score"] == 0.6
    assert insert_payload["faithfulness_warning"] == "Needs review"


@pytest.mark.asyncio
async def test_record_request_allows_null_message_id_with_request_id():
    supabase = MagicMock()
    supabase.table.return_value.insert.return_value.execute.return_value = Mock(data=[{"id": "1"}])
    payload = RAGAnalyticsPayload(
        request_id="req-2",
        organization_id="org-1",
        conversation_id="conv-1",
        message_id=None,
        user_id="user-1",
        query_text="What happened?",
        completion_status="partial_stream_failure",
        partial_response_length=42,
        citations_stripped_count=0,
    )

    result = await rag_analytics_service.record_request(supabase, payload)

    assert result is True
    insert_payload = supabase.table.return_value.insert.call_args[0][0]
    assert insert_payload["request_id"] == "req-2"
    assert insert_payload["message_id"] is None
    assert insert_payload["completion_status"] == "partial_stream_failure"
    assert insert_payload["partial_response_length"] == 42
