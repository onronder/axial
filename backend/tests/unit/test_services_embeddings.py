"""
Unit Tests for Embeddings Service
Tests the resilient embedding generation logic, specifically handling of empty text.
"""
import builtins
import importlib
import sys
import types

import pytest
from unittest.mock import Mock, patch
from services.embeddings import generate_embedding, generate_embeddings_batch_sync

class TestEmbeddingsService:
    @pytest.mark.unit
    def test_generate_embedding_returns_none_for_empty_string(self):
        """Should return None when text is empty string."""
        assert generate_embedding("") is None
        assert generate_embedding("   ") is None
        assert generate_embedding(None) is None

    @pytest.mark.unit
    @patch('services.embeddings.get_embeddings_model')
    def test_generate_embedding_returns_vector_for_valid_text(self, mock_get_model):
        """Should return vector for valid text."""
        # Setup mock
        mock_model = Mock()
        mock_model.embed_query.return_value = [0.1, 0.2, 0.3]
        mock_get_model.return_value = mock_model

        # Execute
        result = generate_embedding("hello world")

        # Verify
        assert result == [0.1, 0.2, 0.3]
        mock_model.embed_query.assert_called_once_with("hello world")

    @pytest.mark.unit
    def test_generate_embeddings_batch_handles_mixed_content(self):
        """Should handle mix of valid and empty strings correctly."""
        texts = ["hello", "", "  ", "world"]
        
        # We need to mock the internal model call
        with patch('services.embeddings.get_embeddings_model') as mock_get_model:
            mock_model = Mock()
            # The service filters empty strings, so it only sends "hello" and "world" to OpenAI
            mock_model.embed_documents.return_value = [
                [1.0, 0.0], # hello
                [0.0, 1.0]  # world
            ]
            mock_get_model.return_value = mock_model

            results = generate_embeddings_batch_sync(texts)

            # verify results - should preserve order and insert Nones
            assert len(results) == 4
            assert results[0] == [1.0, 0.0]
            assert results[1] is None
            assert results[2] is None
            assert results[3] == [0.0, 1.0]

            # Verify specifically what was sent to the model (optimization check)
            mock_model.embed_documents.assert_called_once_with(["hello", "world"])

    @pytest.mark.unit
    def test_build_batches_respects_token_limits(self):
        from services.embeddings import _build_batches

        texts = ["short", "tiny", "big-text"]
        token_counts = [2, 2, 20]
        batches = _build_batches(texts, token_counts, batch_size=3, max_tokens_per_batch=5)

        assert batches == [["short", "tiny"], ["big-text"]]

    @pytest.mark.unit
    def test_generate_embeddings_batch_sync_uses_token_counts(self):
        texts = ["a" * 20, "b" * 4, "c" * 4]
        token_counts = [10, 1, 1]

        with patch("services.embeddings.get_embeddings_model") as mock_get_model:
            mock_model = Mock()
            mock_model.embed_documents.return_value = [[0.1], [0.2], [0.3]]
            mock_get_model.return_value = mock_model

            result = generate_embeddings_batch_sync(
                texts,
                token_counts=token_counts,
                max_tokens_per_batch=12,
            )

        assert result[0] == [0.1]
        assert result[1] == [0.2]
        assert result[2] == [0.3]

    @pytest.mark.unit
    def test_generate_embeddings_batch_sync_rate_limit_error(self):
        class RateLimit(Exception):
            status_code = 429

        with patch("services.embeddings.get_embeddings_model") as mock_get_model, \
             patch("services.embeddings.retry_failure") as retry_failure:
            mock_model = Mock()
            mock_model.embed_documents.side_effect = RateLimit("limit")
            mock_get_model.return_value = mock_model

            with pytest.raises(RateLimit):
                generate_embeddings_batch_sync(["hello"])

        retry_failure.labels.assert_called_once()

    @pytest.mark.unit
    def test_embedding_throttle_computes_sleep(self):
        from services.embeddings import _EmbeddingThrottle

        throttle = _EmbeddingThrottle()
        throttle.record_rate_limit()
        sleep_seconds = throttle.compute_sleep(0.1, 0.5)
        assert sleep_seconds >= 0.1

    @pytest.mark.unit
    def test_embedding_throttle_returns_zero_for_negative_sleep(self):
        from services.embeddings import _EmbeddingThrottle

        throttle = _EmbeddingThrottle()
        assert throttle.compute_sleep(-1.0, 0.0) == 0.0

    @pytest.mark.unit
    def test_generate_embeddings_batch_sync_empty_texts_returns_empty(self):
        assert generate_embeddings_batch_sync([]) == []

    @pytest.mark.unit
    def test_generate_embeddings_batch_sync_rate_limit_import_error(self, monkeypatch):
        class RateLimit(Exception):
            status_code = 429

        original_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "openai":
                raise ImportError("missing")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        with patch("services.embeddings.get_embeddings_model") as mock_get_model:
            mock_model = Mock()
            mock_model.embed_documents.side_effect = RateLimit("limit")
            mock_get_model.return_value = mock_model

            with pytest.raises(RateLimit):
                generate_embeddings_batch_sync(["hello"])


class TestEmbeddingsServiceEdgeCases:
    def test_metrics_import_failure_falls_back(self):
        import services.embeddings as embeddings_module

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "core.metrics":
                raise ImportError("missing")
            return real_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=fake_import):
            reloaded = importlib.reload(embeddings_module)
            assert reloaded.embeddings_generated is None

        importlib.reload(embeddings_module)

    def test_get_embeddings_model_initializes(self):
        import services.embeddings as embeddings_module

        embeddings_module._embeddings_model = None
        with patch("services.embeddings.OpenAIEmbeddings") as mock_model:
            sentinel = Mock()
            mock_model.return_value = sentinel
            result = embeddings_module.get_embeddings_model()

        assert result is sentinel

    def test_generate_embedding_raises_on_error(self):
        with patch("services.embeddings.get_embeddings_model") as mock_get_model:
            mock_model = Mock()
            mock_model.embed_query.side_effect = RuntimeError("boom")
            mock_get_model.return_value = mock_model

            with pytest.raises(RuntimeError):
                generate_embedding("hello")

    @pytest.mark.asyncio
    async def test_generate_embeddings_batch_delegates(self):
        import services.embeddings as embeddings_module

        with patch("services.embeddings.generate_embeddings_batch_sync", return_value=[["ok"]]) as sync:
            result = await embeddings_module.generate_embeddings_batch(["text"])

        assert result == [["ok"]]
        sync.assert_called_once()

    def test_estimate_token_count_empty(self):
        from services.embeddings import _estimate_token_count

        assert _estimate_token_count("") == 1

    def test_build_batches_empty_inputs(self):
        from services.embeddings import _build_batches

        assert _build_batches([], None, batch_size=2, max_tokens_per_batch=None) == []

    def test_build_batches_default_chunking(self):
        from services.embeddings import _build_batches

        texts = ["a", "b", "c"]
        batches = _build_batches(texts, None, batch_size=2, max_tokens_per_batch=None)

        assert batches == [["a", "b"], ["c"]]

    def test_build_batches_rolls_over_on_token_limit(self):
        from services.embeddings import _build_batches

        texts = ["a", "b", "c"]
        token_counts = [3, 3, 3]
        batches = _build_batches(texts, token_counts, batch_size=10, max_tokens_per_batch=4)

        assert batches == [["a"], ["b"], ["c"]]

    def test_generate_embeddings_batch_sync_accepts_generator(self):
        with patch("services.embeddings.get_embeddings_model") as mock_get_model:
            mock_model = Mock()
            mock_model.embed_documents.return_value = [[0.1]]
            mock_get_model.return_value = mock_model

            texts = (text for text in ["hello"])
            result = generate_embeddings_batch_sync(texts)

        assert result == [[0.1]]

    def test_generate_embeddings_batch_sync_returns_none_for_all_empty(self):
        with patch("services.embeddings.get_embeddings_model") as mock_get_model:
            mock_get_model.return_value = Mock()

            result = generate_embeddings_batch_sync([" ", ""])

        assert result == [None, None]

    def test_generate_embeddings_batch_sync_rate_limit_error_openai(self):
        import services.embeddings as embeddings_module

        class FakeRateLimitError(Exception):
            pass

        fake_openai = types.SimpleNamespace(RateLimitError=FakeRateLimitError)
        sys.modules["openai"] = fake_openai

        try:
            with patch("services.embeddings.get_embeddings_model") as mock_get_model:
                mock_model = Mock()
                mock_model.embed_documents.side_effect = FakeRateLimitError("limit")
                mock_get_model.return_value = mock_model

                with pytest.raises(FakeRateLimitError):
                    embeddings_module.generate_embeddings_batch_sync(["hello"])
        finally:
            sys.modules.pop("openai", None)

    def test_generate_embeddings_batch_sync_rate_limit_response(self):
        import services.embeddings as embeddings_module

        class Response:
            status_code = 429

        class DummyError(Exception):
            def __init__(self):
                self.response = Response()

        with patch("services.embeddings.get_embeddings_model") as mock_get_model:
            mock_model = Mock()
            mock_model.embed_documents.side_effect = DummyError()
            mock_get_model.return_value = mock_model

            with pytest.raises(DummyError):
                embeddings_module.generate_embeddings_batch_sync(["hello"])

    def test_generate_embeddings_batch_sync_sleeps_between_batches(self):
        import services.embeddings as embeddings_module

        with patch.object(embeddings_module.settings, "EMBEDDING_BATCH_SIZE", 1), \
             patch.object(embeddings_module.settings, "EMBEDDING_SLEEP_INTERVAL", 0.1), \
             patch.object(embeddings_module.settings, "EMBEDDING_MAX_TOKENS_PER_REQUEST", 1000), \
             patch("services.embeddings.get_embeddings_model") as mock_get_model, \
             patch("services.embeddings._EMBEDDING_THROTTLE.compute_sleep", return_value=0.1), \
             patch("services.embeddings.time.sleep") as sleeper:
            mock_model = Mock()
            mock_model.embed_documents.return_value = [[0.1]]
            mock_get_model.return_value = mock_model

            result = embeddings_module.generate_embeddings_batch_sync(["a", "b"])

        assert result == [[0.1], [0.1]]
        sleeper.assert_called_once()
