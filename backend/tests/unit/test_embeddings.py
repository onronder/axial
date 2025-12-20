"""
Unit Tests for Embedding Factory

Tests the multi-model embedding tier selection and factory functionality.
"""

import pytest
from unittest.mock import patch, Mock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.embeddings import EmbeddingFactory, EmbeddingTier


class TestEmbeddingTierSelection:
    """Test the auto_select tier selection logic."""
    
    def test_high_priority_returns_premium(self):
        """High priority should always return premium tier."""
        tier = EmbeddingFactory.auto_select(doc_count=1, priority="high")
        assert tier == EmbeddingTier.PREMIUM
    
    def test_large_batch_returns_local(self):
        """Large batches (>1000) should use local tier for cost savings."""
        tier = EmbeddingFactory.auto_select(doc_count=1500, priority="normal")
        assert tier == EmbeddingTier.LOCAL
    
    def test_medium_batch_returns_standard(self):
        """Medium batches (100-1000) should use standard tier."""
        tier = EmbeddingFactory.auto_select(doc_count=500, priority="normal")
        assert tier == EmbeddingTier.STANDARD
    
    def test_small_batch_returns_premium(self):
        """Small batches (<100) should use premium tier for quality."""
        tier = EmbeddingFactory.auto_select(doc_count=50, priority="normal")
        assert tier == EmbeddingTier.PREMIUM
    
    def test_force_local_overrides_all(self):
        """force_local=True should override all other logic."""
        tier = EmbeddingFactory.auto_select(doc_count=1, priority="high", force_local=True)
        assert tier == EmbeddingTier.LOCAL


class TestEmbeddingDimensions:
    """Test embedding dimension reporting."""
    
    def test_local_dimension(self):
        """Local model should report 384 dimensions."""
        dim = EmbeddingFactory.get_embedding_dimension(EmbeddingTier.LOCAL)
        assert dim == 384
    
    def test_standard_dimension(self):
        """Standard model should report 1024 dimensions."""
        dim = EmbeddingFactory.get_embedding_dimension(EmbeddingTier.STANDARD)
        assert dim == 1024
    
    def test_premium_dimension(self):
        """Premium model should report 1536 dimensions."""
        dim = EmbeddingFactory.get_embedding_dimension(EmbeddingTier.PREMIUM)
        assert dim == 1536


class TestEmbeddingFactory:
    """Test the EmbeddingFactory.get_embeddings method."""
    
    @patch('core.embeddings.OpenAIEmbeddings')
    def test_premium_returns_openai(self, mock_openai):
        """Premium tier should return OpenAI embeddings."""
        mock_openai.return_value = Mock()
        
        embeddings = EmbeddingFactory.get_embeddings(EmbeddingTier.PREMIUM)
        
        mock_openai.assert_called_once()
        assert embeddings is not None
    
    @patch('core.embeddings.settings')
    def test_standard_without_mistral_falls_back(self, mock_settings):
        """Standard tier without Mistral API key should fall back to premium."""
        mock_settings.MISTRAL_API_KEY = None
        mock_settings.OPENAI_API_KEY = "test-key"
        
        with patch('core.embeddings.OpenAIEmbeddings') as mock_openai:
            mock_openai.return_value = Mock()
            embeddings = EmbeddingFactory.get_embeddings(EmbeddingTier.STANDARD)
            # Should fall back to OpenAI
            mock_openai.assert_called()
