"""
Test Suite for Ghost Protocol Chat/Search Decryption

Tests for search result decryption in chat and search endpoints.
"""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from typing import List, Dict


class TestDecryptSearchResultsChat:
    """Tests for _decrypt_search_results in chat.py."""
    
    def test_function_exists_in_chat(self):
        """Decryption helper should exist in chat module."""
        from api.v1.chat import _decrypt_search_results
        assert callable(_decrypt_search_results)
    
    def test_returns_empty_list_for_empty_input(self):
        """Should return empty list for empty input."""
        from api.v1.chat import _decrypt_search_results
        
        result = _decrypt_search_results([])
        assert result == []
    
    def test_returns_same_list_when_no_encryption(self, monkeypatch):
        """When encryption is disabled, should return docs unchanged."""
        import core.security as security
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", False)
        
        from api.v1.chat import _decrypt_search_results
        
        docs = [{"content": "plain text", "document_id": str(uuid4())}]
        result = _decrypt_search_results(docs)
        
        assert result[0]["content"] == "plain text"
    
    def test_decrypts_content_when_encryption_enabled(self, monkeypatch):
        """Should decrypt content when encryption is enabled."""
        import core.security as security
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)
        monkeypatch.setattr(security, "decrypt_text", lambda x: f"DECRYPTED:{x}")
        
        from api.v1.chat import _decrypt_search_results
        
        docs = [{"content": "encrypted_content", "document_id": str(uuid4())}]
        result = _decrypt_search_results(docs)
        
        assert result[0]["content"] == "DECRYPTED:encrypted_content"
    
    def test_handles_unencrypted_content_error(self, monkeypatch):
        """Should handle UnencryptedContentError gracefully."""
        import core.security as security
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)
        
        from core.security import UnencryptedContentError
        monkeypatch.setattr(security, "decrypt_text", MagicMock(side_effect=UnencryptedContentError("test")))
        
        from api.v1.chat import _decrypt_search_results
        
        docs = [{"content": "plaintext", "document_id": str(uuid4())}]
        result = _decrypt_search_results(docs)
        
        assert "encryption policy violation" in result[0]["content"].lower()
    
    def test_handles_encryption_error(self, monkeypatch):
        """Should handle EncryptionError gracefully."""
        import core.security as security
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)
        
        from core.security import EncryptionError
        monkeypatch.setattr(security, "decrypt_text", MagicMock(side_effect=EncryptionError("test")))
        
        from api.v1.chat import _decrypt_search_results
        
        docs = [{"content": "bad_data", "document_id": str(uuid4())}]
        result = _decrypt_search_results(docs)
        
        assert "decryption error" in result[0]["content"].lower()
    
    def test_handles_multiple_docs(self, monkeypatch):
        """Should decrypt all docs in the list."""
        import core.security as security
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)
        monkeypatch.setattr(security, "decrypt_text", lambda x: f"DEC:{x}")
        
        from api.v1.chat import _decrypt_search_results
        
        docs = [
            {"content": "content1", "document_id": str(uuid4())},
            {"content": "content2", "document_id": str(uuid4())},
            {"content": "content3", "document_id": str(uuid4())},
        ]
        result = _decrypt_search_results(docs)
        
        assert result[0]["content"] == "DEC:content1"
        assert result[1]["content"] == "DEC:content2"
        assert result[2]["content"] == "DEC:content3"


class TestDecryptSearchResultsSearch:
    """Tests for _decrypt_search_results in search.py."""
    
    def test_function_exists_in_search(self):
        """Decryption helper should exist in search module."""
        from api.v1.search import _decrypt_search_results
        assert callable(_decrypt_search_results)
    
    def test_returns_empty_list_for_empty_input(self):
        """Should return empty list for empty input."""
        from api.v1.search import _decrypt_search_results
        
        result = _decrypt_search_results([])
        assert result == []
    
    def test_decrypts_content_when_encryption_enabled(self, monkeypatch):
        """Should decrypt content when encryption is enabled."""
        import core.security as security
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)
        monkeypatch.setattr(security, "decrypt_text", lambda x: f"DECRYPTED:{x}")
        
        from api.v1.search import _decrypt_search_results
        
        results = [{"content": "encrypted", "id": str(uuid4())}]
        decrypted = _decrypt_search_results(results)
        
        assert decrypted[0]["content"] == "DECRYPTED:encrypted"


class TestDecryptionIntegration:
    """Tests for decryption integration with search flow."""
    
    def test_format_context_receives_decrypted_content(self, monkeypatch):
        """format_context_with_citations should receive already decrypted content."""
        from api.v1.chat import format_context_with_citations
        
        # Docs with "decrypted" content (simulating after _decrypt_search_results)
        docs = [
            {
                "content": "This is the decrypted document content",
                "title": "Test Doc",
                "source_type": "file_upload",
                "metadata": {}
            }
        ]
        
        context, sources = format_context_with_citations(docs)
        
        # The content should be in the formatted context
        assert "This is the decrypted document content" in context
    
    def test_empty_content_handled_gracefully(self):
        """Should handle docs with empty content."""
        from api.v1.chat import _decrypt_search_results
        
        docs = [
            {"content": "", "document_id": str(uuid4())},
            {"content": None, "document_id": str(uuid4())},
            {"document_id": str(uuid4())},  # No content key
        ]
        
        # Should not raise
        result = _decrypt_search_results(docs)
        
        assert len(result) == 3


class TestDecryptionPreservesOtherFields:
    """Tests that decryption preserves other document fields."""
    
    def test_preserves_document_metadata(self, monkeypatch):
        """Should preserve all non-content fields."""
        import core.security as security
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)
        monkeypatch.setattr(security, "decrypt_text", lambda x: "decrypted")
        
        from api.v1.chat import _decrypt_search_results
        
        doc_id = str(uuid4())
        docs = [
            {
                "content": "encrypted",
                "document_id": doc_id,
                "title": "Test Title",
                "source_type": "file_upload",
                "chunk_index": 5,
                "vector_score": 0.95,
                "keyword_score": 0.8,
                "metadata": {"page_number": 1}
            }
        ]
        
        result = _decrypt_search_results(docs)
        
        assert result[0]["document_id"] == doc_id
        assert result[0]["title"] == "Test Title"
        assert result[0]["source_type"] == "file_upload"
        assert result[0]["chunk_index"] == 5
        assert result[0]["vector_score"] == 0.95
        assert result[0]["keyword_score"] == 0.8
        assert result[0]["metadata"]["page_number"] == 1


class TestErrorRecovery:
    """Tests for error recovery during decryption."""
    
    def test_continues_on_single_doc_error(self, monkeypatch):
        """Should continue processing other docs if one fails."""
        import core.security as security
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)
        
        # First call fails, second succeeds
        call_count = [0]
        
        def mock_decrypt(x):
            call_count[0] += 1
            if call_count[0] == 1:
                from core.security import EncryptionError
                raise EncryptionError("first failed")
            return f"decrypted:{x}"
        
        monkeypatch.setattr(security, "decrypt_text", mock_decrypt)
        
        from api.v1.chat import _decrypt_search_results
        
        docs = [
            {"content": "first_content", "document_id": str(uuid4())},
            {"content": "second_content", "document_id": str(uuid4())},
        ]
        
        result = _decrypt_search_results(docs)
        
        # First doc should have error message
        assert "decryption error" in result[0]["content"].lower()
        # Second doc should be decrypted
        assert result[1]["content"] == "decrypted:second_content"
