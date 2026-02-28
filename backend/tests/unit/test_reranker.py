"""
Unit Tests for Reranker (H4)

Tests reranking, fallback behavior, and skip-when-few-docs logic.
"""

from unittest.mock import AsyncMock, patch

import pytest

from services.reranker import Reranker


class TestReranker:
    @pytest.fixture
    def reranker(self):
        return Reranker(provider="cohere")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rerank_returns_top_k(self, reranker):
        docs = [{"content": f"doc {i}", "similarity": 0.9 - i * 0.05} for i in range(15)]
        with patch.object(
            reranker, "_rerank_cohere", new_callable=AsyncMock, return_value=docs[:8]
        ):
            result = await reranker.rerank("query", docs, top_k=8)
        assert len(result) == 8
        assert result[0]["content"] == "doc 0"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rerank_fallback_on_error(self, reranker):
        """If reranking fails, return original docs truncated."""
        docs = [{"content": f"doc {i}"} for i in range(15)]
        with patch.object(
            reranker, "_rerank_cohere", new_callable=AsyncMock, side_effect=Exception("API error")
        ):
            result = await reranker.rerank("query", docs, top_k=8)
        assert len(result) == 8
        # Verify it's the original order (not reranked)
        assert result[0]["content"] == "doc 0"
        assert result[7]["content"] == "doc 7"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rerank_skips_when_few_docs(self, reranker):
        """No reranking needed if docs <= top_k."""
        docs = [{"content": "only doc"}]
        result = await reranker.rerank("query", docs, top_k=8)
        assert len(result) == 1
        assert result is docs  # Same list reference — no processing done

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rerank_empty_docs(self, reranker):
        result = await reranker.rerank("query", [], top_k=8)
        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rerank_exactly_top_k_docs(self, reranker):
        """Docs == top_k should be returned as-is."""
        docs = [{"content": f"doc {i}"} for i in range(8)]
        result = await reranker.rerank("query", docs, top_k=8)
        assert len(result) == 8
        assert result is docs  # Same reference — no processing

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rerank_does_not_mutate_input(self, reranker):
        """Reranking should not mutate the original documents."""
        docs = [{"content": f"doc {i}", "nested": {"key": "val"}} for i in range(15)]
        original_first = docs[0].copy()
        with patch.object(
            reranker, "_rerank_cohere", new_callable=AsyncMock, return_value=docs[:8]
        ):
            await reranker.rerank("query", docs, top_k=8)
        # Original docs should be unchanged
        assert docs[0] == original_first

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cohere_no_api_key_returns_truncated(self, reranker):
        """Without COHERE_API_KEY, fallback to truncated original."""
        docs = [{"content": f"doc {i}"} for i in range(15)]
        with patch("services.reranker.settings") as mock_settings:
            mock_settings.COHERE_API_KEY = None
            result = await reranker._rerank_cohere("query", docs, top_k=8)
        assert len(result) == 8
