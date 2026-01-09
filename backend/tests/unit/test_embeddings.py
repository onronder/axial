"""
Unit Tests for Embedding Factory

Tests the multi-model embedding tier selection and factory functionality.
"""

import pytest
from types import SimpleNamespace
from unittest.mock import patch, Mock, MagicMock
import sys
import os

# Set environment variables BEFORE importing modules that use settings
os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("ENVIRONMENT", "test")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

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
    
    @patch('langchain_openai.OpenAIEmbeddings')
    def test_premium_returns_openai(self, mock_openai):
        """Premium tier should return OpenAI embeddings."""
        mock_openai.return_value = Mock()
        
        embeddings = EmbeddingFactory.get_embeddings(EmbeddingTier.PREMIUM)
        
        mock_openai.assert_called_once()
        assert embeddings is not None

    def test_local_embeddings_falls_back_on_import_error(self, monkeypatch):
        sentinel = Mock()
        monkeypatch.setattr(EmbeddingFactory, "_get_premium_embeddings", Mock(return_value=sentinel))

        original_import = __import__

        def guarded_import(name, *args, **kwargs):
            if name.startswith("langchain_community"):
                raise ImportError("missing")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", guarded_import)

        EmbeddingFactory._cached_local_model = None
        result = EmbeddingFactory._get_local_embeddings()

        assert result is sentinel

    def test_standard_embeddings_falls_back_on_import_error(self, monkeypatch):
        sentinel = Mock()
        monkeypatch.setattr(EmbeddingFactory, "_get_premium_embeddings", Mock(return_value=sentinel))
        import core.embeddings as embeddings_module
        dummy_settings = SimpleNamespace(MISTRAL_API_KEY="key", OPENAI_API_KEY="test")
        monkeypatch.setattr(embeddings_module, "settings", dummy_settings)

        original_import = __import__

        def guarded_import(name, *args, **kwargs):
            if name.startswith("langchain_mistralai"):
                raise ImportError("missing")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", guarded_import)

        result = EmbeddingFactory._get_standard_embeddings()

        assert result is sentinel

    def test_local_embeddings_returns_huggingface(self):
        import types

        EmbeddingFactory._cached_local_model = None
        sentinel = Mock()

        fake_pkg = types.ModuleType("langchain_community")
        fake_module = types.ModuleType("langchain_community.embeddings")

        class DummyHF:
            def __init__(self, *args, **kwargs):
                pass

        def fake_init(*_args, **_kwargs):
            return sentinel

        DummyHF.__call__ = staticmethod(fake_init)
        fake_module.HuggingFaceEmbeddings = Mock(return_value=sentinel)
        fake_pkg.embeddings = fake_module

        sys.modules["langchain_community"] = fake_pkg
        sys.modules["langchain_community.embeddings"] = fake_module

        try:
            result = EmbeddingFactory._get_local_embeddings()
        finally:
            sys.modules.pop("langchain_community.embeddings", None)
            sys.modules.pop("langchain_community", None)

        assert result is sentinel
        assert EmbeddingFactory._cached_local_model is sentinel
        EmbeddingFactory._cached_local_model = None

    def test_standard_embeddings_uses_mistral(self, monkeypatch):
        import types
        import core.embeddings as embeddings_module

        dummy_settings = SimpleNamespace(MISTRAL_API_KEY="key", OPENAI_API_KEY="test")
        monkeypatch.setattr(embeddings_module, "settings", dummy_settings)
        sentinel = Mock()

        fake_module = types.ModuleType("langchain_mistralai")
        fake_module.MistralAIEmbeddings = Mock(return_value=sentinel)
        sys.modules["langchain_mistralai"] = fake_module

        try:
            result = EmbeddingFactory._get_standard_embeddings()
        finally:
            sys.modules.pop("langchain_mistralai", None)

        assert result is sentinel

    def test_get_embeddings_local_and_standard(self, monkeypatch):
        sentinel_local = Mock()
        sentinel_standard = Mock()
        monkeypatch.setattr(EmbeddingFactory, "_get_local_embeddings", Mock(return_value=sentinel_local))
        monkeypatch.setattr(EmbeddingFactory, "_get_standard_embeddings", Mock(return_value=sentinel_standard))

        assert EmbeddingFactory.get_embeddings(EmbeddingTier.LOCAL) is sentinel_local
        assert EmbeddingFactory.get_embeddings(EmbeddingTier.STANDARD) is sentinel_standard
