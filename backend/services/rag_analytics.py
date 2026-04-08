"""
Request-level analytics for the chat RAG pipeline.

All writes are best-effort and keyed by `request_id`. This service must never
break the chat path if analytics insertion or feedback updates fail.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from services.faithfulness_guard import FaithfulnessResult

logger = logging.getLogger(__name__)


@dataclass
class RAGAnalyticsPayload:
    request_id: str | None
    organization_id: str
    conversation_id: str | None
    message_id: str | None
    user_id: str | None
    query_text: str
    search_query: str | None = None
    selected_scope_id: str | None = None
    allowed_scope_ids: list[str] | None = None
    guardrail_language: str | None = None
    guardrail_intent: str | None = None
    guardrail_complexity: str | None = None
    has_document_context: bool = False
    retrieval_docs: list[dict[str, Any]] = field(default_factory=list)
    high_quality_docs: list[dict[str, Any]] = field(default_factory=list)
    source_count: int = 0
    rerank_applied: bool = False
    scope_classification: str | None = None
    scope_dominance_ratio: float | None = None
    cached: bool = False
    no_answer: bool = False
    completion_status: str = "success"
    partial_response_length: int | None = None
    citations_stripped_count: int = 0
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_prompt_tokens: int | None = None
    llm_completion_tokens: int | None = None
    llm_total_tokens: int | None = None
    faithfulness_result: FaithfulnessResult | None = None


class RAGAnalyticsService:
    """Best-effort persistence for RAG request analytics."""

    @staticmethod
    def _extract_float(values: list[float]) -> float | None:
        return round(sum(values) / len(values), 4) if values else None

    @staticmethod
    def _retrieval_scores(docs: list[dict[str, Any]]) -> list[float]:
        scores: list[float] = []
        for doc in docs:
            score = doc.get("similarity")
            if score is None:
                score = doc.get("vector_score")
            try:
                if score is not None:
                    scores.append(float(score))
            except (TypeError, ValueError):
                continue
        return scores

    @staticmethod
    def _rerank_scores(docs: list[dict[str, Any]]) -> list[float]:
        scores: list[float] = []
        for doc in docs:
            try:
                score = doc.get("rerank_score")
                if score is not None:
                    scores.append(float(score))
            except (TypeError, ValueError):
                continue
        return scores

    async def record_request(self, supabase, payload: RAGAnalyticsPayload) -> bool:
        """Insert a request analytics row keyed by request_id."""
        if not payload.request_id:
            logger.warning("[RAGAnalytics] Skipping insert because request_id is missing")
            return False

        retrieval_scores = self._retrieval_scores(payload.retrieval_docs)
        rerank_scores = self._rerank_scores(payload.retrieval_docs)
        faithfulness = payload.faithfulness_result
        faithfulness_checked = bool(faithfulness and faithfulness.checked)

        record = {
            "request_id": payload.request_id,
            "organization_id": payload.organization_id,
            "conversation_id": payload.conversation_id,
            "message_id": payload.message_id,
            "user_id": payload.user_id,
            "query_text": payload.query_text,
            "search_query": payload.search_query,
            "selected_scope_id": payload.selected_scope_id,
            "allowed_scope_ids": payload.allowed_scope_ids,
            "guardrail_language": payload.guardrail_language,
            "guardrail_intent": payload.guardrail_intent,
            "guardrail_complexity": payload.guardrail_complexity,
            "has_document_context": payload.has_document_context,
            "retrieval_doc_count": len(payload.retrieval_docs),
            "high_quality_doc_count": len(payload.high_quality_docs),
            "source_count": payload.source_count,
            "top_similarity": max(retrieval_scores) if retrieval_scores else None,
            "avg_similarity": self._extract_float(retrieval_scores),
            "rerank_applied": payload.rerank_applied,
            "top_rerank_score": max(rerank_scores) if rerank_scores else None,
            "avg_rerank_score": self._extract_float(rerank_scores),
            "scope_classification": payload.scope_classification,
            "scope_dominance_ratio": payload.scope_dominance_ratio,
            "cached": payload.cached,
            "no_answer": payload.no_answer,
            "completion_status": payload.completion_status,
            "partial_response_length": payload.partial_response_length,
            "citations_stripped_count": payload.citations_stripped_count,
            "llm_provider": payload.llm_provider,
            "llm_model": payload.llm_model,
            "llm_prompt_tokens": payload.llm_prompt_tokens,
            "llm_completion_tokens": payload.llm_completion_tokens,
            "llm_total_tokens": payload.llm_total_tokens,
            "faithfulness_passed": faithfulness.faithful if faithfulness_checked else None,
            "faithfulness_score": faithfulness.score if faithfulness_checked else None,
            "faithfulness_warning": faithfulness.warning if faithfulness_checked else None,
        }

        try:
            supabase.table("rag_analytics").insert(record).execute()
            return True
        except Exception as e:
            logger.warning(
                "[RAGAnalytics] Insert failed for request=%s: %s",
                payload.request_id[:8],
                e,
            )
            return False

    async def update_feedback(self, supabase, *, message_id: str, rating: str) -> bool:
        """Best-effort feedback correlation by message_id."""
        try:
            result = (
                supabase.table("rag_analytics")
                .update(
                    {
                        "user_feedback": rating,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                .eq("message_id", message_id)
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            logger.warning("[RAGAnalytics] Feedback update failed for message=%s: %s", message_id[:8], e)
            return False


rag_analytics_service = RAGAnalyticsService()
