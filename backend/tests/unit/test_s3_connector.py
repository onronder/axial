"""
Unit Tests for Amazon S3 Connector

Tests production safeguards:
- Glacier/Deep Archive detection
- Resumable downloads (Range requests)
- Deterministic source IDs
- Cost protection (prefix requirement, object limits)
- Enterprise gate enforcement
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from connectors.base import (
    ConnectorAuthError,
    ConnectorRateLimitError,
)
from connectors.enhanced import ItemNotFoundError, SourceType
from connectors.s3 import (
    ARCHIVED_STORAGE_CLASSES,
    DEFAULT_REGION,
    LARGE_FILE_THRESHOLD,
    MAX_FILE_SIZE,
    MAX_OBJECTS_PER_SYNC,
    SUPPORTED_EXTENSIONS,
    S3Connector,
)


class TestS3ConnectorProperties:
    """Test connector property methods."""

    @pytest.mark.unit
    def test_connector_type_is_s3(self):
        connector = S3Connector()
        assert connector.connector_type == SourceType.S3

    @pytest.mark.unit
    def test_supports_incremental_sync(self):
        connector = S3Connector()
        assert connector.supports_incremental_sync is True

    @pytest.mark.unit
    def test_does_not_support_batch_fetch(self):
        connector = S3Connector()
        assert connector.supports_batch_fetch is False


class TestS3ConfigValidation:
    """Test configuration validation and cost protection."""

    @pytest.mark.unit
    def test_validate_config_requires_all_fields(self):
        connector = S3Connector()

        # Missing fields should fail
        assert connector.validate_config({}) is False
        assert connector.validate_config({"access_key_id": "test"}) is False

    @pytest.mark.unit
    def test_validate_config_requires_prefix(self):
        """CRITICAL: Prefix is mandatory for cost protection."""
        connector = S3Connector()

        config = {
            "access_key_id": "A" * 20,
            "secret_access_key": "B" * 40,
            "region": "us-east-1",
            "bucket_name": "test-bucket",
            "prefix": "",  # Empty prefix
        }

        with pytest.raises(ValueError, match="prefix is required"):
            connector.validate_config(config)

    @pytest.mark.unit
    def test_validate_config_accepts_valid_config(self):
        """Valid config with all required fields should pass (mocking S3)."""
        connector = S3Connector()

        config = {
            "access_key_id": "A" * 20,
            "secret_access_key": "B" * 40,
            "region": "us-east-1",
            "bucket_name": "test-bucket",
            "prefix": "documents/",
        }

        with patch.object(connector, "_verify_access", return_value={"status": "connected"}):
            assert connector.validate_config(config) is True


class TestGlacierTrapPrevention:
    """Test Glacier/Deep Archive detection (Bill Shock Prevention)."""

    @pytest.mark.unit
    def test_archived_storage_classes_defined(self):
        """Verify all archived storage classes are defined."""
        assert "GLACIER" in ARCHIVED_STORAGE_CLASSES
        assert "DEEP_ARCHIVE" in ARCHIVED_STORAGE_CLASSES
        assert "GLACIER_IR" in ARCHIVED_STORAGE_CLASSES

    @pytest.mark.unit
    def test_standard_storage_classes_not_archived(self):
        """Standard classes should NOT be in archived set."""
        assert "STANDARD" not in ARCHIVED_STORAGE_CLASSES
        assert "STANDARD_IA" not in ARCHIVED_STORAGE_CLASSES
        assert "INTELLIGENT_TIERING" not in ARCHIVED_STORAGE_CLASSES

    @pytest.mark.unit
    def test_list_files_skips_glacier_objects(self):
        """list_files should skip objects in GLACIER storage class."""
        connector = S3Connector()

        mock_client = MagicMock()
        mock_paginator = MagicMock()

        # Simulate S3 response with mixed storage classes
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {
                        "Key": "documents/standard.pdf",
                        "Size": 1000,
                        "LastModified": datetime.now(timezone.utc),
                        "StorageClass": "STANDARD",
                    },
                    {
                        "Key": "documents/archived.pdf",
                        "Size": 2000,
                        "LastModified": datetime.now(timezone.utc),
                        "StorageClass": "GLACIER",  # Should be skipped
                    },
                    {
                        "Key": "documents/deep_archive.pdf",
                        "Size": 3000,
                        "LastModified": datetime.now(timezone.utc),
                        "StorageClass": "DEEP_ARCHIVE",  # Should be skipped
                    },
                ]
            }
        ]
        mock_client.get_paginator.return_value = mock_paginator

        config = {
            "access_key_id": "test",
            "secret_access_key": "test",
            "region": "us-east-1",
            "bucket_name": "test-bucket",
            "prefix": "documents/",
        }

        with patch.object(connector, "_get_s3_client", return_value=mock_client), \
             patch.object(connector, "_resolve_config", return_value=config):
            files = list(connector.list_files(config))

        # Only STANDARD file should be returned
        assert len(files) == 1
        assert "standard.pdf" in files[0].name

    @pytest.mark.unit
    def test_fetch_documents_skips_archived_with_warning(self):
        """fetch_documents_sync should skip archived objects with warning."""
        connector = S3Connector()

        mock_client = MagicMock()

        # HEAD request returns GLACIER storage class
        mock_client.head_object.return_value = {
            "StorageClass": "GLACIER",
            "ContentLength": 1000,
        }

        config = {
            "access_key_id": "test",
            "secret_access_key": "test",
            "region": "us-east-1",
            "bucket_name": "test-bucket",
            "prefix": "documents/",
        }

        with patch.object(connector, "_get_s3_client", return_value=mock_client), \
             patch.object(connector, "_resolve_config", return_value=config), \
             patch.object(connector, "_build_config", return_value=config):
            docs = list(connector.fetch_documents_sync(
                ["documents/archived.pdf"],
                credentials=config
            ))

        # No documents should be returned (archived object skipped)
        assert len(docs) == 0


class TestResumableDownloads:
    """Test Range request support for large file resilience."""

    @pytest.mark.unit
    def test_large_file_threshold_defined(self):
        """Verify large file threshold is set correctly."""
        assert LARGE_FILE_THRESHOLD == 50 * 1024 * 1024  # 50 MB

    @pytest.mark.unit
    def test_small_file_uses_standard_download(self):
        """Files under threshold should use standard streaming."""
        connector = S3Connector()

        mock_client = MagicMock()
        mock_body = MagicMock()
        mock_body.iter_chunks.return_value = [b"small file content"]
        mock_body.close = MagicMock()

        mock_client.get_object.return_value = {"Body": mock_body}

        # File size under threshold
        content = connector._download_small_object(mock_client, "bucket", "key")

        assert content == b"small file content"
        mock_client.get_object.assert_called_once()

    @pytest.mark.unit
    def test_large_file_uses_range_requests(self):
        """Files over threshold should use Range requests."""
        connector = S3Connector()

        mock_client = MagicMock()
        content_length = 60 * 1024 * 1024  # 60 MB

        # Simulate chunked response
        chunk_size = 10 * 1024 * 1024  # 10 MB chunks
        chunks = [b"x" * chunk_size for _ in range(6)]

        call_count = [0]
        def mock_get_object(**kwargs):
            body = MagicMock()
            body.read.return_value = chunks[call_count[0]]
            body.close = MagicMock()
            call_count[0] += 1
            return {"Body": body}

        mock_client.get_object.side_effect = mock_get_object

        content = connector._download_large_object(
            mock_client, "bucket", "key", content_length
        )

        # Should make multiple GET requests with Range headers
        assert mock_client.get_object.call_count == 6

        # Verify Range header was used
        for call in mock_client.get_object.call_args_list:
            assert "Range" in call.kwargs


class TestDeterministicSourceIds:
    """Test deterministic ID generation for ghost file detection."""

    @pytest.mark.unit
    def test_canonical_source_id_format(self):
        """Source IDs should use s3://bucket/key format."""
        connector = S3Connector()

        source_id = connector._build_canonical_source_id("my-bucket", "path/to/file.pdf")

        assert source_id == "s3://my-bucket/path/to/file.pdf"

    @pytest.mark.unit
    def test_canonical_id_is_deterministic(self):
        """Same input should always produce same output."""
        connector = S3Connector()

        id1 = connector._build_canonical_source_id("bucket", "key")
        id2 = connector._build_canonical_source_id("bucket", "key")

        assert id1 == id2

    @pytest.mark.unit
    def test_extract_key_from_canonical_id(self):
        """Should correctly extract key from canonical ID."""
        connector = S3Connector()

        # Canonical format
        key = connector._extract_key_from_id("s3://my-bucket/path/to/file.pdf", "my-bucket")
        assert key == "path/to/file.pdf"

        # Raw key format
        key = connector._extract_key_from_id("path/to/file.pdf", "my-bucket")
        assert key == "path/to/file.pdf"


class TestCostProtection:
    """Test cost protection features."""

    @pytest.mark.unit
    def test_object_limit_constant(self):
        """Verify object limit is defined."""
        assert MAX_OBJECTS_PER_SYNC == 10_000

    @pytest.mark.unit
    def test_file_size_limit_constant(self):
        """Verify file size limit is defined."""
        assert MAX_FILE_SIZE == 100 * 1024 * 1024  # 100 MB

    @pytest.mark.unit
    def test_supported_extensions_defined(self):
        """Verify supported extensions are defined."""
        assert ".pdf" in SUPPORTED_EXTENSIONS
        assert ".docx" in SUPPORTED_EXTENSIONS
        assert ".txt" in SUPPORTED_EXTENSIONS
        assert ".md" in SUPPORTED_EXTENSIONS

        # Log files should NOT be supported
        assert ".log" not in SUPPORTED_EXTENSIONS

    @pytest.mark.unit
    def test_should_process_object_filters_extensions(self):
        """Only supported extensions should be processed."""
        connector = S3Connector()

        # Supported
        assert connector._should_process_object("docs/file.pdf") is True
        assert connector._should_process_object("docs/file.docx") is True
        assert connector._should_process_object("docs/file.md") is True

        # Not supported
        assert connector._should_process_object("logs/access.log") is False
        assert connector._should_process_object("backup/data.gz") is False
        assert connector._should_process_object("archive.zip") is False

    @pytest.mark.unit
    def test_should_process_skips_hidden_files(self):
        """Hidden files and directories should be skipped."""
        connector = S3Connector()

        assert connector._should_process_object(".hidden/file.pdf") is False
        assert connector._should_process_object("docs/.gitignore") is False
        assert connector._should_process_object(".env") is False

    @pytest.mark.unit
    def test_list_files_respects_object_limit(self):
        """list_files should stop at MAX_OBJECTS_PER_SYNC."""
        connector = S3Connector()

        mock_client = MagicMock()
        mock_paginator = MagicMock()

        # Generate more objects than limit
        objects = [
            {
                "Key": f"documents/file_{i}.pdf",
                "Size": 100,
                "LastModified": datetime.now(timezone.utc),
                "StorageClass": "STANDARD",
            }
            for i in range(MAX_OBJECTS_PER_SYNC + 100)
        ]

        # Split into pages of 1000
        pages = [{"Contents": objects[i:i+1000]} for i in range(0, len(objects), 1000)]
        mock_paginator.paginate.return_value = pages
        mock_client.get_paginator.return_value = mock_paginator

        config = {
            "access_key_id": "test",
            "secret_access_key": "test",
            "region": "us-east-1",
            "bucket_name": "test-bucket",
            "prefix": "documents/",
        }

        with patch.object(connector, "_get_s3_client", return_value=mock_client), \
             patch.object(connector, "_resolve_config", return_value=config):
            files = list(connector.list_files(config))

        # Should stop at limit
        assert len(files) <= MAX_OBJECTS_PER_SYNC


class TestErrorHandling:
    """Test error handling and exception mapping."""

    @pytest.mark.unit
    def test_access_denied_raises_auth_error(self):
        """AccessDenied should raise ConnectorAuthError."""
        connector = S3Connector()

        error = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "HeadBucket"
        )

        with pytest.raises(ConnectorAuthError):
            connector._handle_client_error(error, "test")

    @pytest.mark.unit
    def test_invalid_key_raises_auth_error(self):
        """InvalidAccessKeyId should raise ConnectorAuthError."""
        connector = S3Connector()

        error = ClientError(
            {"Error": {"Code": "InvalidAccessKeyId", "Message": "Invalid key"}},
            "HeadBucket"
        )

        with pytest.raises(ConnectorAuthError):
            connector._handle_client_error(error, "test")

    @pytest.mark.unit
    def test_no_such_key_raises_not_found(self):
        """NoSuchKey should raise ItemNotFoundError."""
        connector = S3Connector()

        error = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not found"}},
            "GetObject"
        )

        with pytest.raises(ItemNotFoundError):
            connector._handle_client_error(error, "test")

    @pytest.mark.unit
    def test_slow_down_raises_rate_limit(self):
        """SlowDown should raise ConnectorRateLimitError."""
        connector = S3Connector()

        error = ClientError(
            {"Error": {"Code": "SlowDown", "Message": "Slow down"}},
            "GetObject"
        )

        with pytest.raises(ConnectorRateLimitError):
            connector._handle_client_error(error, "test")


class TestS3ClientConfiguration:
    """Test S3 client configuration."""

    @pytest.mark.unit
    def test_default_region(self):
        """Verify default region is set."""
        assert DEFAULT_REGION == "us-east-1"

    @pytest.mark.unit
    def test_prefix_normalization(self):
        """Prefix should be normalized consistently."""
        connector = S3Connector()

        # Leading slash should be removed
        assert connector._normalize_prefix("/documents/") == "documents/"

        # Already normalized
        assert connector._normalize_prefix("documents/") == "documents/"

        # Whitespace should be stripped
        assert connector._normalize_prefix("  documents/  ") == "documents/"


class TestMimeTypeGuessing:
    """Test MIME type detection."""

    @pytest.mark.unit
    def test_guess_mime_type_from_filename(self):
        """Should guess MIME type from filename extension."""
        connector = S3Connector()

        assert connector._guess_mime_type("file.pdf") == "application/pdf"
        assert connector._guess_mime_type("file.docx") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert connector._guess_mime_type("file.txt") == "text/plain"

    @pytest.mark.unit
    def test_guess_mime_type_fallback(self):
        """Should fallback to content_type or octet-stream."""
        connector = S3Connector()

        # Unknown extension falls back to content_type
        assert connector._guess_mime_type("file.unknownext12345", "text/plain") == "text/plain"

        # No hints falls back to octet-stream
        assert connector._guess_mime_type("file.unknownext12345") == "application/octet-stream"
