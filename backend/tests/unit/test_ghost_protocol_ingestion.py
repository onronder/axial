"""
Test Suite for Ghost Protocol Ingestion Utilities

Tests for encrypted content preparation and insertion including:
- prepare_chunks_for_ghost_protocol
- insert_chunks_with_ghost_protocol
- Encryption/plaintext handling
- RPC fallback behavior
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from core.ingestion_utils import (
    _insert_chunks_direct,
    insert_chunks_with_ghost_protocol,
    prepare_chunks_for_ghost_protocol,
)


class TestPrepareChunksForGhostProtocol:
    """Tests for prepare_chunks_for_ghost_protocol function."""

    def test_returns_prepared_chunks(self):
        """Function should return list of prepared chunk dicts."""
        chunks = [
            {"content": "Hello world", "embedding": [0.1] * 1536, "chunk_index": 0},
            {"content": "Goodbye world", "embedding": [0.2] * 1536, "chunk_index": 1},
        ]
        doc_id = str(uuid4())

        prepared, encrypted = prepare_chunks_for_ghost_protocol(chunks, doc_id)

        assert len(prepared) == 2
        assert all("content_encrypted" in c for c in prepared)
        assert all("content_plaintext" in c for c in prepared)
        assert all("document_id" in c for c in prepared)

    def test_preserves_plaintext_for_search(self):
        """content_plaintext should contain original text for TSVECTOR."""
        chunks = [{"content": "searchable text here", "embedding": [0.1] * 1536, "chunk_index": 0}]
        doc_id = str(uuid4())

        prepared, _ = prepare_chunks_for_ghost_protocol(chunks, doc_id)

        assert prepared[0]["content_plaintext"] == "searchable text here"

    def test_sets_document_id_on_all_chunks(self):
        """All prepared chunks should have the document_id set."""
        chunks = [
            {"content": "chunk 1", "embedding": [0.1] * 1536, "chunk_index": 0},
            {"content": "chunk 2", "embedding": [0.1] * 1536, "chunk_index": 1},
        ]
        doc_id = str(uuid4())

        prepared, _ = prepare_chunks_for_ghost_protocol(chunks, doc_id)

        assert all(c["document_id"] == doc_id for c in prepared)

    def test_generates_unique_ids_for_chunks(self):
        """Each chunk should get a unique UUID."""
        chunks = [
            {"content": "chunk 1", "embedding": [0.1] * 1536, "chunk_index": 0},
            {"content": "chunk 2", "embedding": [0.1] * 1536, "chunk_index": 1},
        ]
        doc_id = str(uuid4())

        prepared, _ = prepare_chunks_for_ghost_protocol(chunks, doc_id)

        ids = [c["id"] for c in prepared]
        assert len(set(ids)) == 2  # All unique

    def test_preserves_chunk_index(self):
        """chunk_index should be preserved in prepared chunks."""
        chunks = [
            {"content": "first", "embedding": [0.1] * 1536, "chunk_index": 5},
            {"content": "second", "embedding": [0.2] * 1536, "chunk_index": 10},
        ]
        doc_id = str(uuid4())

        prepared, _ = prepare_chunks_for_ghost_protocol(chunks, doc_id)

        assert prepared[0]["chunk_index"] == 5
        assert prepared[1]["chunk_index"] == 10

    def test_preserves_embedding(self):
        """embedding should be preserved in prepared chunks."""
        embedding = [0.5] * 1536
        chunks = [{"content": "text", "embedding": embedding, "chunk_index": 0}]
        doc_id = str(uuid4())

        prepared, _ = prepare_chunks_for_ghost_protocol(chunks, doc_id)

        assert prepared[0]["embedding"] == embedding

    def test_handles_empty_content(self):
        """Should handle chunks with empty or missing content."""
        chunks = [
            {"content": "", "embedding": [0.1] * 1536, "chunk_index": 0},
            {"embedding": [0.2] * 1536, "chunk_index": 1},  # Missing content
        ]
        doc_id = str(uuid4())

        prepared, _ = prepare_chunks_for_ghost_protocol(chunks, doc_id)

        assert prepared[0]["content_encrypted"] == ""
        assert prepared[0]["content_plaintext"] == ""
        assert prepared[1]["content_encrypted"] == ""
        assert prepared[1]["content_plaintext"] == ""

    def test_returns_encryption_flag(self, monkeypatch):
        """Should return whether encryption was applied."""
        # Test with encryption enabled
        import core.security as security
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)

        chunks = [{"content": "text", "embedding": [0.1] * 1536, "chunk_index": 0}]
        doc_id = str(uuid4())

        _, encrypted = prepare_chunks_for_ghost_protocol(chunks, doc_id)

        assert encrypted is True

    def test_includes_detected_language_in_prepared_chunks(self, monkeypatch):
        """Prepared chunk payload should include detected ISO language code."""
        import core.security as security
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", False)

        chunks = [{"content": "Merhaba dunya bu metin yeterince uzundur.", "embedding": [0.1] * 1536, "chunk_index": 0}]
        doc_id = str(uuid4())

        with patch("core.ingestion_utils._detect_chunk_language", return_value="tr"):
            prepared, _ = prepare_chunks_for_ghost_protocol(chunks, doc_id)

        assert prepared[0]["language"] == "tr"

    def test_encryption_disabled_returns_plaintext(self, monkeypatch):
        """With encryption disabled, content_encrypted should equal plaintext."""
        import core.security as security
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", False)

        chunks = [{"content": "plain text", "embedding": [0.1] * 1536, "chunk_index": 0}]
        doc_id = str(uuid4())

        prepared, encrypted = prepare_chunks_for_ghost_protocol(chunks, doc_id)

        assert encrypted is False
        assert prepared[0]["content_encrypted"] == "plain text"
        assert prepared[0]["content_plaintext"] == "plain text"


class TestInsertChunksWithGhostProtocol:
    """Tests for insert_chunks_with_ghost_protocol function."""

    def test_calls_rpc_with_prepared_chunks(self, monkeypatch):
        """Should call ingest_document_chunks_batch RPC."""
        import core.security as security
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", False)

        mock_supabase = MagicMock()
        mock_rpc_result = MagicMock()
        mock_rpc_result.data = [{"inserted_id": "id-1", "chunk_index": 0}]
        mock_supabase.rpc.return_value.execute.return_value = mock_rpc_result

        chunks = [{"content": "text", "embedding": [0.1] * 1536, "chunk_index": 0}]
        doc_id = str(uuid4())

        count = insert_chunks_with_ghost_protocol(
            supabase=mock_supabase,
            document_id=doc_id,
            chunks_payload=chunks,
        )

        assert count == 1
        mock_supabase.rpc.assert_called_once()
        call_args = mock_supabase.rpc.call_args
        assert call_args[0][0] == "ingest_document_chunks_batch"

    def test_batches_chunks(self, monkeypatch):
        """Should process chunks in batches."""
        import core.security as security
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", False)

        mock_supabase = MagicMock()
        mock_rpc_result = MagicMock()
        mock_rpc_result.data = [{"inserted_id": "id", "chunk_index": i} for i in range(50)]
        mock_supabase.rpc.return_value.execute.return_value = mock_rpc_result

        # 150 chunks with batch_size of 50 = 3 batches
        chunks = [{"content": f"chunk {i}", "embedding": [0.1] * 1536, "chunk_index": i} for i in range(150)]
        doc_id = str(uuid4())

        count = insert_chunks_with_ghost_protocol(
            supabase=mock_supabase,
            document_id=doc_id,
            chunks_payload=chunks,
            batch_size=50,
        )

        # Should have made 3 RPC calls
        assert mock_supabase.rpc.call_count == 3

    def test_returns_total_inserted_count(self, monkeypatch):
        """Should return total number of inserted chunks."""
        import core.security as security
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", False)

        mock_supabase = MagicMock()

        # Simulate varying batch results
        mock_result1 = MagicMock()
        mock_result1.data = [{"inserted_id": f"id-{i}"} for i in range(100)]
        mock_result2 = MagicMock()
        mock_result2.data = [{"inserted_id": f"id-{i}"} for i in range(50)]

        mock_supabase.rpc.return_value.execute.side_effect = [mock_result1, mock_result2]

        chunks = [{"content": f"chunk {i}", "embedding": [0.1] * 1536, "chunk_index": i} for i in range(150)]
        doc_id = str(uuid4())

        count = insert_chunks_with_ghost_protocol(
            supabase=mock_supabase,
            document_id=doc_id,
            chunks_payload=chunks,
            batch_size=100,
        )

        assert count == 150

    def test_handles_empty_chunks(self, monkeypatch):
        """Should handle empty chunks list."""
        mock_supabase = MagicMock()
        doc_id = str(uuid4())

        count = insert_chunks_with_ghost_protocol(
            supabase=mock_supabase,
            document_id=doc_id,
            chunks_payload=[],
        )

        assert count == 0
        mock_supabase.rpc.assert_not_called()

    def test_fallback_to_direct_insert_on_rpc_not_found(self, monkeypatch):
        """Should fallback to direct insert if RPC doesn't exist."""
        import core.security as security
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", False)

        mock_supabase = MagicMock()
        # Simulate RPC not found error
        mock_supabase.rpc.return_value.execute.side_effect = Exception(
            "function ingest_document_chunks_batch does not exist"
        )

        # Mock direct insert
        with patch('core.ingestion_utils._insert_chunks_direct') as mock_direct:
            mock_direct.return_value = 5

            chunks = [{"content": "text", "embedding": [0.1] * 1536, "chunk_index": 0}]
            doc_id = str(uuid4())

            count = insert_chunks_with_ghost_protocol(
                supabase=mock_supabase,
                document_id=doc_id,
                chunks_payload=chunks,
            )

            assert count == 5
            mock_direct.assert_called_once()

    def test_raises_on_other_rpc_errors(self, monkeypatch):
        """Should raise exception on non-recoverable RPC errors."""
        import core.security as security
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", False)

        mock_supabase = MagicMock()
        mock_supabase.rpc.return_value.execute.side_effect = Exception("Database connection failed")

        chunks = [{"content": "text", "embedding": [0.1] * 1536, "chunk_index": 0}]
        doc_id = str(uuid4())

        with pytest.raises(Exception) as exc:
            insert_chunks_with_ghost_protocol(
                supabase=mock_supabase,
                document_id=doc_id,
                chunks_payload=chunks,
            )

        assert "Database connection failed" in str(exc.value)


class TestEncryptionIntegration:
    """Tests for encryption integration in Ghost Protocol."""

    def test_content_encrypted_differs_from_plaintext_when_enabled(self, monkeypatch):
        """When encryption is enabled, content_encrypted should differ from plaintext."""
        import core.security as security

        # Ensure encryption is enabled and mock encrypt_text
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)
        monkeypatch.setattr(security, "encrypt_text", lambda x: f"ENCRYPTED:{x}")

        chunks = [{"content": "secret data", "embedding": [0.1] * 1536, "chunk_index": 0}]
        doc_id = str(uuid4())

        prepared, encrypted = prepare_chunks_for_ghost_protocol(chunks, doc_id)

        assert encrypted is True
        assert prepared[0]["content_encrypted"] == "ENCRYPTED:secret data"
        assert prepared[0]["content_plaintext"] == "secret data"

    def test_unicode_content_handled(self, monkeypatch):
        """Should handle Unicode content correctly."""
        import core.security as security
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", False)

        chunks = [{"content": "日本語 العربية 한국어 🔐", "embedding": [0.1] * 1536, "chunk_index": 0}]
        doc_id = str(uuid4())

        prepared, _ = prepare_chunks_for_ghost_protocol(chunks, doc_id)

        assert prepared[0]["content_plaintext"] == "日本語 العربية 한국어 🔐"


class TestBatchSizeHandling:
    """Tests for batch size handling."""

    def test_custom_batch_size(self, monkeypatch):
        """Should respect custom batch_size parameter."""
        import core.security as security
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", False)

        mock_supabase = MagicMock()
        mock_rpc_result = MagicMock()
        mock_rpc_result.data = [{"inserted_id": f"id-{i}"} for i in range(10)]
        mock_supabase.rpc.return_value.execute.return_value = mock_rpc_result

        # 25 chunks with batch_size of 10 = 3 batches (10, 10, 5)
        chunks = [{"content": f"chunk {i}", "embedding": [0.1] * 1536, "chunk_index": i} for i in range(25)]
        doc_id = str(uuid4())

        insert_chunks_with_ghost_protocol(
            supabase=mock_supabase,
            document_id=doc_id,
            chunks_payload=chunks,
            batch_size=10,
        )

        assert mock_supabase.rpc.call_count == 3

    def test_batch_size_larger_than_chunk_count(self, monkeypatch):
        """Should handle batch_size larger than chunk count."""
        import core.security as security
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", False)

        mock_supabase = MagicMock()
        mock_rpc_result = MagicMock()
        mock_rpc_result.data = [{"inserted_id": "id-1"}]
        mock_supabase.rpc.return_value.execute.return_value = mock_rpc_result

        # 5 chunks with batch_size of 100 = 1 batch
        chunks = [{"content": f"chunk {i}", "embedding": [0.1] * 1536, "chunk_index": i} for i in range(5)]
        doc_id = str(uuid4())

        insert_chunks_with_ghost_protocol(
            supabase=mock_supabase,
            document_id=doc_id,
            chunks_payload=chunks,
            batch_size=100,
        )

        assert mock_supabase.rpc.call_count == 1


class TestDirectInsertLanguageHandling:
    """Tests for legacy direct-insert fallback language writes."""

    def test_direct_insert_includes_detected_language(self, monkeypatch):
        """Fallback insert path should write detected language explicitly."""
        import core.db_utils as db_utils
        import core.security as security

        captured_rows = {}

        def fake_insert_rows_with_retry(*args, **kwargs):
            captured_rows["rows"] = args[2]

        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", False)
        monkeypatch.setattr(db_utils, "insert_rows_with_retry", fake_insert_rows_with_retry)

        mock_supabase = MagicMock()
        chunks = [{"content": "Hallo welt dieser text ist lang genug.", "embedding": [0.1] * 1536, "chunk_index": 0}]
        doc_id = str(uuid4())

        with patch("core.ingestion_utils._detect_chunk_language", return_value="de"):
            inserted = _insert_chunks_direct(mock_supabase, doc_id, chunks, 100, "")

        assert inserted == 1
        assert captured_rows["rows"][0]["language"] == "de"

    def test_direct_insert_detects_language_before_encryption(self, monkeypatch):
        """Detection should run on plaintext content before encryption mutates it."""
        import core.db_utils as db_utils
        import core.security as security

        observed_content = []
        captured_rows = {}

        def fake_insert_rows_with_retry(*args, **kwargs):
            captured_rows["rows"] = args[2]

        def fake_detect(content):
            observed_content.append(content)
            return "tr"

        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)
        monkeypatch.setattr(security, "encrypt_text", lambda value: f"ENC:{value}")
        monkeypatch.setattr(db_utils, "insert_rows_with_retry", fake_insert_rows_with_retry)

        mock_supabase = MagicMock()
        chunks = [{"content": "Merhaba dunya bu metin yeterince uzundur.", "embedding": [0.1] * 1536, "chunk_index": 0}]
        doc_id = str(uuid4())

        with patch("core.ingestion_utils._detect_chunk_language", side_effect=fake_detect):
            inserted = _insert_chunks_direct(mock_supabase, doc_id, chunks, 100, "")

        assert inserted == 1
        assert observed_content == ["Merhaba dunya bu metin yeterince uzundur."]
        assert captured_rows["rows"][0]["content"] == "ENC:Merhaba dunya bu metin yeterince uzundur."
        assert captured_rows["rows"][0]["language"] == "tr"
