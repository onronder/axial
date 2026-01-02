"""
Unit Tests for Embeddings Service
Tests the resilient embedding generation logic, specifically handling of empty text.
"""
import pytest
from unittest.mock import Mock, patch
from services.embeddings import generate_embedding, generate_embeddings_batch

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

            results = generate_embeddings_batch(texts)

            # verify results - should preserve order and insert Nones
            assert len(results) == 4
            assert results[0] == [1.0, 0.0]
            assert results[1] is None
            assert results[2] is None
            assert results[3] == [0.0, 1.0]

            # Verify specifically what was sent to the model (optimization check)
            mock_model.embed_documents.assert_called_once_with(["hello", "world"])
