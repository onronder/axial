"""
Unit tests for Box Connector.

Tests cover:
- Token validation and refresh
- Folder traversal and pagination
- Rate limit handling
- File content streaming
- Error handling
"""

import io
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from requests import Response

from connectors.box import (
    BoxConnector,
    BOX_API_BASE,
    ROOT_FOLDER_ID,
    MAX_RETRIES,
    PAGE_SIZE,
)
from connectors.base import (
    ConnectorAuthError,
    ConnectorRateLimitError,
    ConnectorTransientError,
)
from connectors.enhanced import (
    SourceType,
    ItemNotFoundError,
    FileTooLargeError,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def connector():
    """Create a BoxConnector instance."""
    return BoxConnector()


@pytest.fixture
def mock_config():
    """Standard test configuration."""
    return {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    }


@pytest.fixture
def mock_user_response():
    """Mock Box /users/me response."""
    return {
        "id": "12345678",
        "type": "user",
        "name": "Test User",
        "login": "test@example.com",
        "enterprise": {
            "id": "98765432",
            "type": "enterprise",
            "name": "Test Enterprise",
        },
    }


@pytest.fixture
def mock_folder_items_response():
    """Mock Box /folders/{id}/items response."""
    return {
        "total_count": 3,
        "entries": [
            {
                "id": "file_001",
                "type": "file",
                "name": "document.pdf",
                "size": 1024,
                "sha1": "abc123",
                "modified_at": "2024-01-15T10:30:00Z",
                "parent": {"id": "0", "type": "folder"},
            },
            {
                "id": "file_002",
                "type": "file",
                "name": "spreadsheet.xlsx",
                "size": 2048,
                "sha1": "def456",
                "modified_at": "2024-01-16T11:00:00Z",
                "parent": {"id": "0", "type": "folder"},
            },
            {
                "id": "folder_001",
                "type": "folder",
                "name": "Subfolder",
                "parent": {"id": "0", "type": "folder"},
            },
        ],
        "offset": 0,
        "limit": 1000,
    }


@pytest.fixture
def mock_file_metadata():
    """Mock Box file metadata."""
    return {
        "id": "file_001",
        "type": "file",
        "name": "document.pdf",
        "size": 1024,
        "sha1": "abc123",
        "modified_at": "2024-01-15T10:30:00Z",
        "parent": {"id": "0", "type": "folder"},
    }


# =============================================================================
# Connector Properties Tests
# =============================================================================

class TestBoxConnectorProperties:
    """Test connector properties."""

    def test_connector_type(self, connector):
        """Test connector_type returns BOX."""
        assert connector.connector_type == SourceType.BOX

    def test_supports_incremental_sync(self, connector):
        """Test supports_incremental_sync returns True."""
        assert connector.supports_incremental_sync is True

    def test_supports_batch_fetch(self, connector):
        """Test supports_batch_fetch returns False."""
        assert connector.supports_batch_fetch is False


# =============================================================================
# Configuration Validation Tests
# =============================================================================

class TestValidateConfig:
    """Test configuration validation."""

    def test_validate_config_with_access_token(self, connector, mock_user_response):
        """Test validation with direct access token."""
        with patch.object(connector, "_verify_token", return_value=mock_user_response):
            result = connector.validate_config({"access_token": "test_token"})
            assert result is True

    def test_validate_config_with_invalid_token(self, connector):
        """Test validation with invalid token."""
        with patch.object(connector, "_verify_token", side_effect=ConnectorAuthError("Invalid")):
            result = connector.validate_config({"access_token": "bad_token"})
            assert result is False

    def test_validate_config_with_integration_id(self, connector):
        """Test validation with integration_id (deferred)."""
        result = connector.validate_config({"integration_id": "int_123"})
        assert result is True  # Deferred to operation time

    def test_validate_config_with_user_id(self, connector):
        """Test validation with user_id (deferred)."""
        result = connector.validate_config({"user_id": "user_123"})
        assert result is True  # Deferred to operation time

    def test_validate_config_empty(self, connector):
        """Test validation with empty config."""
        result = connector.validate_config({})
        assert result is False

    def test_validate_config_invalid_type(self, connector):
        """Test validation with non-dict config."""
        result = connector.validate_config("not a dict")
        assert result is False
        result = connector.validate_config(None)
        assert result is False


class TestVerifyToken:
    """Test token verification."""

    def test_verify_token_success(self, connector, mock_user_response):
        """Test successful token verification."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_user_response

        with patch("requests.get", return_value=mock_response):
            result = connector._verify_token("valid_token")
            assert result["id"] == "12345678"
            assert result["name"] == "Test User"

    def test_verify_token_unauthorized(self, connector):
        """Test token verification with 401 response."""
        mock_response = Mock()
        mock_response.status_code = 401

        with patch("requests.get", return_value=mock_response):
            with pytest.raises(ConnectorAuthError, match="invalid or expired"):
                connector._verify_token("bad_token")

    def test_verify_token_forbidden(self, connector):
        """Test token verification with 403 response."""
        mock_response = Mock()
        mock_response.status_code = 403

        with patch("requests.get", return_value=mock_response):
            with pytest.raises(ConnectorAuthError, match="access denied"):
                connector._verify_token("forbidden_token")


# =============================================================================
# Rate Limiting Tests
# =============================================================================

class TestRateLimiting:
    """Test rate limit handling."""

    def test_rate_limit_with_retry_after(self, connector, mock_config):
        """Test rate limiting respects Retry-After header."""
        # First call returns 429, second returns 200
        mock_429 = Mock()
        mock_429.status_code = 429
        mock_429.headers = {"Retry-After": "1"}
        mock_429.close = Mock()

        mock_200 = Mock()
        mock_200.status_code = 200
        mock_200.json.return_value = {"entries": [], "total_count": 0}

        with patch("requests.request", side_effect=[mock_429, mock_200]) as mock_req:
            with patch("time.sleep") as mock_sleep:
                response = connector._request_with_retry(
                    "GET",
                    f"{BOX_API_BASE}/folders/0/items",
                    headers={"Authorization": "Bearer test"},
                )
                assert response.status_code == 200
                mock_sleep.assert_called_once_with(1)

    def test_rate_limit_exponential_backoff(self, connector):
        """Test exponential backoff when no Retry-After header."""
        mock_429 = Mock()
        mock_429.status_code = 429
        mock_429.headers = {}  # No Retry-After
        mock_429.close = Mock()

        mock_200 = Mock()
        mock_200.status_code = 200

        with patch("requests.request", side_effect=[mock_429, mock_200]):
            with patch("time.sleep") as mock_sleep:
                connector._request_with_retry("GET", "http://test.com")
                # First retry: 1 * (2 ** 0) = 1
                mock_sleep.assert_called_once_with(1)

    def test_rate_limit_max_retries_exceeded(self, connector):
        """Test that max retries raises error."""
        mock_429 = Mock()
        mock_429.status_code = 429
        mock_429.headers = {"Retry-After": "1"}
        mock_429.close = Mock()

        with patch("requests.request", return_value=mock_429):
            with patch("time.sleep"):
                with pytest.raises(ConnectorRateLimitError, match="exceeded after retries"):
                    connector._request_with_retry("GET", "http://test.com")


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Test error handling in requests."""

    def test_auth_error_401(self, connector):
        """Test 401 raises ConnectorAuthError."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.close = Mock()

        with patch("requests.request", return_value=mock_response):
            with pytest.raises(ConnectorAuthError, match="invalid or expired"):
                connector._request_with_retry("GET", "http://test.com")

    def test_auth_error_403(self, connector):
        """Test 403 raises ConnectorAuthError."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.close = Mock()

        with patch("requests.request", return_value=mock_response):
            with pytest.raises(ConnectorAuthError, match="access denied"):
                connector._request_with_retry("GET", "http://test.com")

    def test_not_found_404(self, connector):
        """Test 404 raises ItemNotFoundError."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.close = Mock()

        with patch("requests.request", return_value=mock_response):
            with pytest.raises(ItemNotFoundError):
                connector._request_with_retry("GET", "http://test.com")

    def test_server_error_500(self, connector):
        """Test 500 raises ConnectorTransientError."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.close = Mock()

        with patch("requests.request", return_value=mock_response):
            with pytest.raises(ConnectorTransientError, match="server error"):
                connector._request_with_retry("GET", "http://test.com")


# =============================================================================
# Folder Listing Tests
# =============================================================================

class TestFolderListing:
    """Test folder listing functionality."""

    def test_list_folder_items_single_page(self, connector, mock_config, mock_folder_items_response):
        """Test listing folder items with single page."""
        with patch.object(connector, "_request", return_value=mock_folder_items_response):
            items = list(connector._list_folder_items(mock_config, "0"))
            assert len(items) == 3
            assert items[0]["name"] == "document.pdf"

    def test_list_folder_items_pagination(self, connector, mock_config):
        """Test listing folder items with pagination."""
        page1 = {
            "total_count": 2000,
            "entries": [{"id": f"file_{i}", "type": "file", "name": f"file_{i}.txt"} for i in range(1000)],
            "offset": 0,
            "limit": 1000,
        }
        page2 = {
            "total_count": 2000,
            "entries": [{"id": f"file_{i}", "type": "file", "name": f"file_{i}.txt"} for i in range(1000, 2000)],
            "offset": 1000,
            "limit": 1000,
        }

        with patch.object(connector, "_request", side_effect=[page1, page2]):
            items = list(connector._list_folder_items(mock_config, "0"))
            assert len(items) == 2000

    def test_list_folder_items_not_found(self, connector, mock_config):
        """Test listing folder that doesn't exist."""
        with patch.object(connector, "_request", side_effect=ItemNotFoundError("Not found")):
            items = list(connector._list_folder_items(mock_config, "nonexistent"))
            assert len(items) == 0


class TestRecursiveTraversal:
    """Test recursive folder traversal."""

    def test_traverse_recursive(self, connector, mock_config):
        """Test recursive folder traversal."""
        root_items = {
            "total_count": 2,
            "entries": [
                {"id": "file_001", "type": "file", "name": "doc.pdf", "size": 1024, "modified_at": None, "parent": {"id": "0"}},
                {"id": "folder_001", "type": "folder", "name": "Subfolder", "parent": {"id": "0"}},
            ],
        }
        subfolder_items = {
            "total_count": 1,
            "entries": [
                {"id": "file_002", "type": "file", "name": "nested.txt", "size": 512, "modified_at": None, "parent": {"id": "folder_001"}},
            ],
        }

        def mock_request(config, endpoint, params=None):
            if "0/items" in endpoint:
                return root_items
            elif "folder_001/items" in endpoint:
                return subfolder_items
            return {"total_count": 0, "entries": []}

        with patch.object(connector, "_request", side_effect=mock_request):
            files = list(connector._traverse_recursive(mock_config, "0", include_folders=False))
            # Should find 2 files (one at root, one in subfolder)
            assert len(files) == 2

    def test_traverse_recursive_handles_403(self, connector, mock_config):
        """Test recursive traversal gracefully handles 403 on subfolders."""
        root_items = {
            "total_count": 2,
            "entries": [
                {"id": "file_001", "type": "file", "name": "doc.pdf", "size": 1024, "modified_at": None, "parent": {"id": "0"}},
                {"id": "folder_001", "type": "folder", "name": "Restricted", "parent": {"id": "0"}},
            ],
        }

        call_count = [0]

        def mock_list_items(config, folder_id):
            call_count[0] += 1
            if folder_id == "0":
                return iter(root_items["entries"])
            elif folder_id == "folder_001":
                raise ConnectorAuthError("access denied to folder")
            return iter([])

        with patch.object(connector, "_list_folder_items", side_effect=mock_list_items):
            files = list(connector._traverse_recursive(mock_config, "0", include_folders=False))
            # Should only find the root file, skipping restricted folder
            assert len(files) == 1
            assert files[0].name == "doc.pdf"


# =============================================================================
# Content Fetching Tests
# =============================================================================

class TestContentFetching:
    """Test file content fetching."""

    def test_download_file_content_streaming(self, connector, mock_config):
        """Test streaming file download."""
        content = b"Test file content " * 100

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [content]
        mock_response.raise_for_status = Mock()
        mock_response.close = Mock()

        with patch.object(connector, "_request_with_retry", return_value=mock_response):
            with patch("connectors.limits.connector_fetch_limit"):
                result = connector._download_file_content(mock_config, "file_001")
                assert result == content

    def test_download_file_content_size_limit(self, connector, mock_config):
        """Test file size limit enforcement."""
        # Create content larger than MAX_FILE_SIZE
        large_chunk = b"x" * (50 * 1024 * 1024)  # 50MB chunks

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [large_chunk, large_chunk, large_chunk]  # 150MB
        mock_response.raise_for_status = Mock()
        mock_response.close = Mock()

        with patch.object(connector, "_request_with_retry", return_value=mock_response):
            with patch("connectors.limits.connector_fetch_limit"):
                with pytest.raises(FileTooLargeError, match="exceeds"):
                    connector._download_file_content(mock_config, "file_001")


class TestFetchDocuments:
    """Test fetch_documents_sync functionality."""

    def test_fetch_documents_single_file(self, connector, mock_config, mock_file_metadata):
        """Test fetching a single file."""
        content = b"Test content"

        with patch.object(connector, "_build_config", return_value=mock_config):
            with patch.object(connector, "_resolve_config", return_value=mock_config):
                with patch.object(connector, "_get_item_metadata", return_value=mock_file_metadata):
                    with patch.object(connector, "_download_file_content", return_value=content):
                        docs = list(connector.fetch_documents_sync(
                            ["file_001"],
                            mock_config,
                            user_id="test_user"
                        ))
                        assert len(docs) == 1
                        assert docs[0].filename == "document.pdf"
                        assert docs[0].source_type == SourceType.BOX

    def test_fetch_documents_folder_expansion(self, connector, mock_config, mock_file_metadata):
        """Test fetching a folder expands to all files."""
        folder_metadata = {"id": "folder_001", "type": "folder", "name": "Test Folder"}
        content = b"Test content"

        remote_file = Mock()
        remote_file.id = "file_001"
        remote_file.name = "document.pdf"

        with patch.object(connector, "_build_config", return_value=mock_config):
            with patch.object(connector, "_resolve_config", return_value=mock_config):
                with patch.object(connector, "_get_item_metadata", return_value=folder_metadata):
                    with patch.object(connector, "list_files", return_value=[remote_file]):
                        with patch.object(connector, "_request", return_value=mock_file_metadata):
                            with patch.object(connector, "_download_file_content", return_value=content):
                                docs = list(connector.fetch_documents_sync(
                                    ["folder_001"],
                                    mock_config,
                                ))
                                assert len(docs) == 1

    def test_fetch_documents_not_found(self, connector, mock_config):
        """Test fetching non-existent item."""
        with patch.object(connector, "_build_config", return_value=mock_config):
            with patch.object(connector, "_resolve_config", return_value=mock_config):
                with patch.object(connector, "_get_item_metadata", side_effect=ItemNotFoundError("Not found")):
                    docs = list(connector.fetch_documents_sync(
                        ["nonexistent"],
                        mock_config,
                    ))
                    assert len(docs) == 0


# =============================================================================
# Helper Method Tests
# =============================================================================

class TestHelperMethods:
    """Test helper methods."""

    def test_normalize_folder_id_root(self, connector):
        """Test normalize_folder_id handles root."""
        assert connector._normalize_folder_id(None) == ROOT_FOLDER_ID
        assert connector._normalize_folder_id("") == ROOT_FOLDER_ID
        assert connector._normalize_folder_id("root") == ROOT_FOLDER_ID
        assert connector._normalize_folder_id("ROOT") == ROOT_FOLDER_ID

    def test_normalize_folder_id_specific(self, connector):
        """Test normalize_folder_id preserves specific IDs."""
        assert connector._normalize_folder_id("12345") == "12345"
        assert connector._normalize_folder_id("folder_abc") == "folder_abc"

    def test_get_parent_id(self, connector):
        """Test _get_parent_id extracts parent."""
        item_with_parent = {"parent": {"id": "parent_123", "type": "folder"}}
        assert connector._get_parent_id(item_with_parent) == "parent_123"

        item_no_parent = {"name": "test"}
        assert connector._get_parent_id(item_no_parent) is None

    def test_parse_datetime(self, connector):
        """Test datetime parsing."""
        # Standard ISO format
        result = BoxConnector._parse_datetime("2024-01-15T10:30:00Z")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1

        # With timezone offset
        result = BoxConnector._parse_datetime("2024-01-15T10:30:00-08:00")
        assert result is not None

        # Invalid
        assert BoxConnector._parse_datetime(None) is None
        assert BoxConnector._parse_datetime("not a date") is None

    def test_guess_mime_type(self, connector):
        """Test MIME type guessing."""
        assert BoxConnector._guess_mime_type("document.pdf") == "application/pdf"
        assert BoxConnector._guess_mime_type("image.png") == "image/png"
        assert BoxConnector._guess_mime_type("script.py") == "text/x-python"
        assert BoxConnector._guess_mime_type("unknown.totally_fake_extension_12345") == "application/octet-stream"
        assert BoxConnector._guess_mime_type(None) == "application/octet-stream"


# =============================================================================
# Item to RemoteFile Conversion Tests
# =============================================================================

class TestItemToRemoteFile:
    """Test item to RemoteFile conversion."""

    def test_item_to_remote_file_file(self, connector):
        """Test converting file item."""
        item = {
            "id": "file_001",
            "name": "document.pdf",
            "type": "file",
            "size": 1024,
            "sha1": "abc123",
            "modified_at": "2024-01-15T10:30:00Z",
            "parent": {"id": "0"},
        }

        result = connector._item_to_remote_file(item, is_folder=False)

        assert result is not None
        assert result.id == "file_001"
        assert result.name == "document.pdf"
        assert result.size == 1024
        assert result.mime_type == "application/pdf"

    def test_item_to_remote_file_folder(self, connector):
        """Test converting folder item."""
        item = {
            "id": "folder_001",
            "name": "My Folder",
            "type": "folder",
            "parent": {"id": "0"},
        }

        result = connector._item_to_remote_file(item, is_folder=True)

        assert result is not None
        assert result.id == "folder_001"
        assert result.name == "My Folder"
        assert result.mime_type == "inode/directory"
        assert result.size is None

    def test_item_to_remote_file_since_filter(self, connector):
        """Test since filter excludes old files."""
        item = {
            "id": "file_001",
            "name": "old.txt",
            "type": "file",
            "size": 100,
            "modified_at": "2024-01-01T00:00:00Z",
            "parent": {"id": "0"},
        }

        # File is from January 1st, since is January 15th
        since = datetime(2024, 1, 15, tzinfo=timezone.utc)
        result = connector._item_to_remote_file(item, since=since, is_folder=False)

        assert result is None  # Should be filtered out


# =============================================================================
# Token Refresh Integration Tests
# =============================================================================

class TestTokenRefreshIntegration:
    """Test token refresh integration."""

    def test_resolve_config_with_access_token(self, connector, mock_config):
        """Test _resolve_config with direct access token."""
        result = connector._resolve_config(mock_config)
        assert result["access_token"] == "test_access_token"

    def test_resolve_config_triggers_refresh(self, connector):
        """Test _resolve_config loads from database when no token."""
        mock_integration = {
            "id": "int_123",
            "access_token": "encrypted_token",
            "refresh_token": "encrypted_refresh",
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        }

        mock_creds = {
            "access_token": "refreshed_token",
            "refresh_token": "refreshed_refresh",
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "integration_id": "int_123",
        }

        with patch.object(connector, "_load_integration", return_value=mock_integration):
            with patch("services.oauth_token_manager.OAuthTokenManager.get_valid_credentials", return_value=mock_creds):
                result = connector._resolve_config({"user_id": "user_123"})
                assert result["access_token"] == "refreshed_token"


# =============================================================================
# Build Config Tests
# =============================================================================

class TestBuildConfig:
    """Test _build_config method."""

    def test_build_config_merges_kwargs(self, connector):
        """Test _build_config merges credentials with kwargs."""
        credentials = {"access_token": "token123"}
        result = connector._build_config(
            credentials,
            user_id="user_abc",
            integration_id="int_xyz"
        )

        assert result["access_token"] == "token123"
        assert result["user_id"] == "user_abc"
        assert result["integration_id"] == "int_xyz"

    def test_build_config_empty(self, connector):
        """Test _build_config with empty inputs."""
        result = connector._build_config(None)
        assert result == {}

    def test_build_config_ignores_none_kwargs(self, connector):
        """Test _build_config ignores None kwargs."""
        result = connector._build_config(
            {"access_token": "token"},
            user_id=None,
            integration_id=None
        )
        assert "user_id" not in result
        assert "integration_id" not in result
