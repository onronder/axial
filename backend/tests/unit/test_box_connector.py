"""
Unit Tests for Box Connector

Tests production safeguards:
- Deterministic source IDs (ghost file detection)
- Robust pagination (BFS traversal)
- Large file chunked downloads
- Error resilience (continues on individual file errors)
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch
import requests

from connectors.box import (
    BoxConnector,
    BOX_API_BASE,
    ROOT_FOLDER_ID,
    PAGE_SIZE,
    LARGE_FILE_THRESHOLD,
    CHUNK_SIZE,
    MAX_RETRIES,
)
from connectors.base import (
    ConnectorAuthError,
    ConnectorTransientError,
    ConnectorRateLimitError,
    RemoteFile,
)
from connectors.enhanced import SourceType, ItemNotFoundError, FileTooLargeError


class TestBoxConnectorProperties:
    """Test connector property methods."""

    @pytest.mark.unit
    def test_connector_type_is_box(self):
        connector = BoxConnector()
        assert connector.connector_type == SourceType.BOX

    @pytest.mark.unit
    def test_supports_incremental_sync(self):
        connector = BoxConnector()
        assert connector.supports_incremental_sync is True

    @pytest.mark.unit
    def test_does_not_support_batch_fetch(self):
        connector = BoxConnector()
        assert connector.supports_batch_fetch is False


class TestDeterministicSourceIds:
    """Test deterministic ID generation for ghost file detection."""

    @pytest.mark.unit
    def test_canonical_source_id_format_file(self):
        """File source IDs should use box://file/{id} format."""
        connector = BoxConnector()
        
        source_id = connector._build_canonical_source_id("123456789", is_folder=False)
        
        assert source_id == "box://file/123456789"

    @pytest.mark.unit
    def test_canonical_source_id_format_folder(self):
        """Folder source IDs should use box://folder/{id} format."""
        connector = BoxConnector()
        
        source_id = connector._build_canonical_source_id("987654321", is_folder=True)
        
        assert source_id == "box://folder/987654321"

    @pytest.mark.unit
    def test_canonical_id_is_deterministic(self):
        """Same input should always produce same output."""
        connector = BoxConnector()
        
        id1 = connector._build_canonical_source_id("123", is_folder=False)
        id2 = connector._build_canonical_source_id("123", is_folder=False)
        
        assert id1 == id2

    @pytest.mark.unit
    def test_extract_box_id_from_canonical_format(self):
        """Should correctly extract Box ID from canonical format."""
        connector = BoxConnector()
        
        # Canonical format
        box_id = connector._extract_box_id_from_source_id("box://file/123456789")
        assert box_id == "123456789"
        
        box_id = connector._extract_box_id_from_source_id("box://folder/987654321")
        assert box_id == "987654321"

    @pytest.mark.unit
    def test_extract_box_id_from_raw_format(self):
        """Should handle raw Box IDs."""
        connector = BoxConnector()
        
        # Raw format
        box_id = connector._extract_box_id_from_source_id("123456789")
        assert box_id == "123456789"

    @pytest.mark.unit
    def test_item_to_remote_file_uses_canonical_id(self):
        """RemoteFile IDs should use canonical format."""
        connector = BoxConnector()
        
        item = {
            "id": "123456789",
            "name": "test.pdf",
            "type": "file",
            "size": 1000,
            "modified_at": "2026-01-15T10:00:00Z",
            "parent": {"id": "0"},
        }
        
        remote_file = connector._item_to_remote_file(item, since=None, is_folder=False)
        
        assert remote_file.id == "box://file/123456789"
        assert remote_file.name == "test.pdf"


class TestRobustPagination:
    """Test pagination and traversal robustness."""

    @pytest.mark.unit
    def test_root_folder_id_constant(self):
        """Root folder ID should be "0"."""
        assert ROOT_FOLDER_ID == "0"

    @pytest.mark.unit
    def test_page_size_constant(self):
        """Page size should be Box maximum (1000)."""
        assert PAGE_SIZE == 1000

    @pytest.mark.unit
    def test_normalize_folder_id_handles_root(self):
        """Various root indicators should normalize to "0"."""
        connector = BoxConnector()
        
        assert connector._normalize_folder_id(None) == "0"
        assert connector._normalize_folder_id("") == "0"
        assert connector._normalize_folder_id("root") == "0"
        assert connector._normalize_folder_id("ROOT") == "0"

    @pytest.mark.unit
    def test_normalize_folder_id_preserves_real_ids(self):
        """Real folder IDs should be preserved."""
        connector = BoxConnector()
        
        assert connector._normalize_folder_id("123456789") == "123456789"

    @pytest.mark.unit
    def test_traverse_uses_visited_set(self):
        """Traversal should track visited folders to prevent loops."""
        connector = BoxConnector()
        
        # Mock the list_folder_items to return items
        items_call_count = [0]
        
        def mock_list_folder_items(config, folder_id):
            items_call_count[0] += 1
            if folder_id == "0":
                return iter([
                    {"id": "folder1", "name": "Folder 1", "type": "folder"},
                    {"id": "file1", "name": "file1.pdf", "type": "file", "size": 100, "modified_at": None},
                ])
            elif folder_id == "folder1":
                return iter([
                    {"id": "file2", "name": "file2.pdf", "type": "file", "size": 200, "modified_at": None},
                ])
            return iter([])
        
        config = {"access_token": "test"}
        
        with patch.object(connector, "_list_folder_items", side_effect=mock_list_folder_items), \
             patch.object(connector, "_resolve_config", return_value=config):
            files = list(connector._traverse_recursive(config, "0", include_folders=False))
        
        # Should have visited root and folder1, yielded 2 files
        assert len(files) == 2


class TestLargeFileDownloads:
    """Test chunked download support for large files."""

    @pytest.mark.unit
    def test_large_file_threshold_defined(self):
        """Verify large file threshold is set."""
        assert LARGE_FILE_THRESHOLD == 50 * 1024 * 1024  # 50 MB

    @pytest.mark.unit
    def test_chunk_size_defined(self):
        """Verify chunk size is set."""
        assert CHUNK_SIZE == 10 * 1024 * 1024  # 10 MB

    @pytest.mark.unit
    def test_small_file_uses_standard_download(self):
        """Files under threshold should use standard streaming."""
        connector = BoxConnector()
        
        config = {"access_token": "test"}
        
        mock_response = Mock()
        mock_response.iter_content.return_value = [b"small content"]
        mock_response.raise_for_status = Mock()
        mock_response.close = Mock()
        
        with patch.object(connector, "_request_with_retry", return_value=mock_response), \
             patch("connectors.box.connector_fetch_limit"):
            content = connector._download_file_content(config, "123", file_size=1000)
        
        assert content == b"small content"

    @pytest.mark.unit
    def test_large_file_uses_chunked_download(self):
        """Files over threshold should use Range requests."""
        connector = BoxConnector()
        
        config = {"access_token": "test"}
        large_size = 60 * 1024 * 1024  # 60 MB
        
        # Mock response for each chunk
        chunk_responses = []
        num_chunks = 6
        for i in range(num_chunks):
            mock_response = Mock()
            mock_response.content = b"x" * CHUNK_SIZE
            mock_response.close = Mock()
            chunk_responses.append(mock_response)
        
        call_idx = [0]
        def mock_request_with_retry(*args, **kwargs):
            resp = chunk_responses[call_idx[0]]
            call_idx[0] += 1
            return resp
        
        with patch.object(connector, "_request_with_retry", side_effect=mock_request_with_retry), \
             patch.object(connector, "_get_headers", return_value={"Authorization": "Bearer test"}), \
             patch("connectors.box.connector_fetch_limit"):
            content = connector._download_large_file_chunked(config, "123", large_size)
        
        # Should have made multiple requests
        assert call_idx[0] == num_chunks


class TestErrorResilience:
    """Test that connector continues on individual file errors."""

    @pytest.mark.unit
    def test_fetch_documents_continues_on_not_found(self):
        """Should continue processing when individual files are not found."""
        connector = BoxConnector()
        
        config = {"access_token": "test"}
        
        def mock_get_item_metadata(cfg, item_id):
            if item_id == "missing":
                raise ItemNotFoundError("Not found")
            return {"id": item_id, "type": "file", "name": f"{item_id}.pdf", "size": 100}
        
        with patch.object(connector, "_resolve_config", return_value=config), \
             patch.object(connector, "_build_config", return_value=config), \
             patch.object(connector, "_get_item_metadata", side_effect=mock_get_item_metadata), \
             patch.object(connector, "_build_source_document") as mock_build:
            mock_build.return_value = Mock()
            
            docs = list(connector.fetch_documents_sync(
                ["found1", "missing", "found2"],
                credentials=config
            ))
        
        # Should have processed 2 files (skipped missing)
        assert mock_build.call_count == 2

    @pytest.mark.unit
    def test_traverse_continues_on_403(self):
        """Should skip folders with 403 and continue traversal."""
        connector = BoxConnector()
        
        def mock_list_folder_items(config, folder_id):
            if folder_id == "restricted":
                raise ConnectorAuthError("Box access denied - insufficient permissions")
            elif folder_id == "0":
                return iter([
                    {"id": "restricted", "name": "Restricted", "type": "folder"},
                    {"id": "accessible", "name": "Accessible", "type": "folder"},
                ])
            elif folder_id == "accessible":
                return iter([
                    {"id": "file1", "name": "file1.pdf", "type": "file", "size": 100, "modified_at": None},
                ])
            return iter([])
        
        config = {"access_token": "test"}
        
        with patch.object(connector, "_list_folder_items", side_effect=mock_list_folder_items), \
             patch.object(connector, "_resolve_config", return_value=config):
            files = list(connector._traverse_recursive(config, "0", include_folders=False))
        
        # Should have gotten file from accessible folder
        assert len(files) == 1


class TestRateLimitHandling:
    """Test rate limit handling with Retry-After."""

    @pytest.mark.unit
    def test_max_retries_constant(self):
        """Verify max retries is set."""
        assert MAX_RETRIES == 3

    @pytest.mark.unit
    def test_request_with_retry_respects_retry_after(self):
        """Should respect Retry-After header on 429."""
        connector = BoxConnector()
        
        # First call returns 429 with Retry-After, second succeeds
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"Retry-After": "1"}
        mock_response_429.close = Mock()
        
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {}
        
        call_count = [0]
        def mock_request(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_response_429
            return mock_response_200
        
        with patch("connectors.box.requests.request", side_effect=mock_request), \
             patch("connectors.box.time.sleep"):
            response = connector._request_with_retry("GET", "http://test.com")
        
        assert call_count[0] == 2
        assert response == mock_response_200


class TestDateTimeParsing:
    """Test Box datetime parsing."""

    @pytest.mark.unit
    def test_parse_datetime_iso_format(self):
        """Should parse Box ISO 8601 format."""
        connector = BoxConnector()
        
        dt = connector._parse_datetime("2026-01-15T10:30:00-08:00")
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 1
        assert dt.day == 15

    @pytest.mark.unit
    def test_parse_datetime_utc_z_suffix(self):
        """Should handle Z suffix for UTC."""
        connector = BoxConnector()
        
        dt = connector._parse_datetime("2026-01-15T18:30:00Z")
        assert dt is not None
        assert dt.tzinfo is not None

    @pytest.mark.unit
    def test_parse_datetime_none(self):
        """Should handle None input."""
        connector = BoxConnector()
        
        assert connector._parse_datetime(None) is None
        assert connector._parse_datetime("") is None


class TestMimeTypeGuessing:
    """Test MIME type detection."""

    @pytest.mark.unit
    def test_guess_mime_type_from_extension(self):
        """Should guess MIME type from filename extension."""
        connector = BoxConnector()
        
        assert connector._guess_mime_type("file.pdf") == "application/pdf"
        assert connector._guess_mime_type("file.docx") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert connector._guess_mime_type("file.txt") == "text/plain"

    @pytest.mark.unit
    def test_guess_mime_type_fallback(self):
        """Should fallback to octet-stream for unknown."""
        connector = BoxConnector()
        
        assert connector._guess_mime_type("file.xyz") == "application/octet-stream"
        assert connector._guess_mime_type(None) == "application/octet-stream"


class TestConfigValidation:
    """Test configuration validation."""

    @pytest.mark.unit
    def test_validate_config_with_access_token(self):
        """Should accept config with access_token."""
        connector = BoxConnector()
        
        with patch.object(connector, "_verify_token", return_value={"id": "123"}):
            assert connector.validate_config({"access_token": "test"}) is True

    @pytest.mark.unit
    def test_validate_config_with_user_id(self):
        """Should accept config with user_id (deferred resolution)."""
        connector = BoxConnector()
        
        assert connector.validate_config({"user_id": "user-123"}) is True

    @pytest.mark.unit
    def test_validate_config_empty_fails(self):
        """Empty config should fail."""
        connector = BoxConnector()
        
        assert connector.validate_config({}) is False
        assert connector.validate_config(None) is False
