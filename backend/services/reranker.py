"""
Cross-Encoder Reranker (H4)

Reranks retrieved documents by relevance to improve retrieval precision.
Supports Cohere reranking with graceful fallback to original ordering.

Usage:
    from services.reranker import reranker

    docs = await reranker.rerank("query text", docs, top_k=8)
"""

import logging
from copy import deepcopy
from typing import Any

from core.config import settings
from core.metrics import rerank_score, rerank_skipped_total

logger = logging.getLogger(__name__)


class Reranker:
    """Cross-encoder reranker for improving retrieval precision."""

    def __init__(self, provider: str = "cohere"):
        self.provider = provider

    async def rerank(
        self, query: str, documents: list[dict[str, Any]], top_k: int = 8
    ) -> list[dict[str, Any]]:
        """Rerank documents by relevance to query.

        Returns top_k most relevant documents in order.
        Falls back to original order truncated on any error.
        """
        if not documents or len(documents) <= top_k:
            self._record_skip("too_few_docs")
            return documents

        try:
            if self.provider == "cohere":
                return await self._rerank_cohere(query, documents, top_k)
        except Exception as e:
            self._record_skip("api_error")
            logger.warning(
                "[Reranker] Reranking failed (%s), returning original order: %s",
                self.provider,
                e,
            )

        # Fallback: return original order truncated
        return documents[:top_k]

    async def _rerank_cohere(
        self,
        query: str,
        documents: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Rerank using Cohere's rerank API."""
        cohere_api_key = getattr(settings, "COHERE_API_KEY", None)
        if not cohere_api_key:
            self._record_skip("no_api_key")
            logger.debug("[Reranker] No COHERE_API_KEY configured, skipping rerank")
            return documents[:top_k]

        try:
            import cohere

            client = cohere.AsyncClientV2(api_key=cohere_api_key)

            # Extract text content for reranking
            doc_texts = [
                doc.get("content", "") or doc.get("text", "") for doc in documents
            ]

            model_name = getattr(settings, "COHERE_RERANK_MODEL", "rerank-v3.5")
            response = await client.rerank(
                model=model_name,
                query=query,
                documents=doc_texts,
                top_n=top_k,
            )

            # Reorder documents based on reranking results — use deepcopy to avoid mutating input
            reranked: list[dict[str, Any]] = []
            for result in response.results:
                idx = result.index
                if 0 <= idx < len(documents):
                    doc = deepcopy(documents[idx])
                    doc["rerank_score"] = result.relevance_score
                    reranked.append(doc)

            logger.info(
                "[Reranker] Reranked %d -> %d docs (top score: %.3f)",
                len(documents),
                len(reranked),
                reranked[0]["rerank_score"] if reranked else 0,
            )
            self._record_scores(reranked)
            return reranked

        except ImportError:
            self._record_skip("import_error")
            logger.warning("[Reranker] cohere package not installed, skipping rerank")
            return documents[:top_k]

    def _record_skip(self, reason: str) -> None:
        """Metrics must never break fail-open reranking behavior."""
        try:
            rerank_skipped_total.labels(provider=self.provider, reason=reason).inc()
        except Exception:
            pass

    def _record_scores(self, documents: list[dict[str, Any]]) -> None:
        """Observe returned rerank scores for successful responses."""
        try:
            histogram = rerank_score.labels(provider=self.provider)
            for doc in documents:
                score = doc.get("rerank_score")
                if score is not None:
                    histogram.observe(float(score))
        except Exception:
            pass


# Singleton
reranker = Reranker()
