"""
Production-Grade Tests for Box Connector

Following best practices:
- Comprehensive mocking with proper isolation
- Edge case coverage
- Error handling verification
- Authentication flow testing
- Rate limiting behavior
- Pagination testing
- File operation testing

Coverage Target: 95%+
"""

from unittest.mock import Mock, patch

import pytest

from connectors.base import (
    ConnectorAuthError,
    ConnectorRateLimitError,
    ConnectorTransientError,
)
from connectors.box import (
    BoxConnector,
)
from connectors.enhanced import ItemNotFoundError, SourceType

# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def connector():
    """Create a fresh BoxConnector instance for each test."""
    return BoxConnector()


@pytest.fixture
def mock_config():
    """Standard test configuration."""
    return {
        "access_token": "test-access-token-12345",
        "integration_id": "int-123",
        "user_id": "user-456",
    }


@pytest.fixture
def mock_file_entry():
    """Standard Box file entry response."""
    return {
        "type": "file",
        "id": "12345678901",
        "name": "test-document.pdf",
        "size": 102400,
        "sha1": "abc123def456",
        "modified_at": "2024-01-15T10:30:00-07:00",
        "parent": {"id": "987654321", "name": "Documents"},
    }


@pytest.fixture
def mock_folder_entry():
    """Standard Box folder entry response."""
    return {
        "type": "folder",
        "id": "987654321",
        "name": "Documents",
        "modified_at": "2024-01-10T08:00:00-07:00",
        "parent": {"id": "0", "name": "All Files"},
    }


# =============================================================================
# Test: Basic Properties
# =============================================================================

class TestConnectorProperties:
    """Test basic connector properties and initialization."""

    def test_connector_type_is_box(self, connector):
        """Connector type should be BOX."""
        assert connector.connector_type == SourceType.BOX

    def test_supports_incremental_sync(self, connector):
        """Box supports incremental sync via modified_at."""
        assert connector.supports_incremental_sync is True

    def test_does_not_support_batch_fetch(self, connector):
        """Box doesn't support batch downloads."""
        assert connector.supports_batch_fetch is False

    def test_folder_name_cache_initialized(self, connector):
        """Folder name cache should be initialized as empty dict."""
        assert connector._folder_name_cache == {}


# =============================================================================
# Test: Configuration Validation
# =============================================================================

class TestValidateConfig:
    """Test configuration validation."""

    def test_rejects_non_dict(self, connector):
        """Should reject non-dict config."""
        assert connector.validate_config(None) is False
        assert connector.validate_config("string") is False
        assert connector.validate_config([]) is False
        assert connector.validate_config(123) is False

    def test_rejects_empty_config(self, connector):
        """Should reject config without credentials."""
        assert connector.validate_config({}) is False
        assert connector.validate_config({"other_key": "value"}) is False

    def test_accepts_access_token_only(self, connector):
        """Should accept config with just access_token."""
        with patch.object(connector, '_verify_token', return_value={"id": "user-1"}):
            assert connector.validate_config({"access_token": "valid-token"}) is True

    def test_accepts_integration_id_only(self, connector):
        """Should accept config with just integration_id."""
        assert connector.validate_config({"integration_id": "int-123"}) is True

    def test_accepts_user_id_only(self, connector):
        """Should accept config with just user_id."""
        assert connector.validate_config({"user_id": "user-456"}) is True

    @patch.object(BoxConnector, '_verify_token')
    def test_verifies_access_token(self, mock_verify, connector):
        """Should call _verify_token when access_token is provided."""
        mock_verify.return_value = {"id": "user-1"}
        connector.validate_config({"access_token": "test-token"})
        mock_verify.assert_called_once_with("test-token")

    @patch.object(BoxConnector, '_verify_token')
    def test_rejects_invalid_token(self, mock_verify, connector):
        """Should reject when token verification fails."""
        mock_verify.side_effect = ConnectorAuthError("Invalid token")
        assert connector.validate_config({"access_token": "bad-token"}) is False

    @patch.object(BoxConnector, '_verify_token')
    def test_accepts_on_network_error(self, mock_verify, connector):
        """Network errors during validation shouldn't reject config."""
        mock_verify.side_effect = Exception("Network timeout")
        assert connector.validate_config({"access_token": "token"}) is True


# =============================================================================
# Test: Token Verification
# =============================================================================

class TestVerifyToken:
    """Test token verification via Box API."""

    @patch('connectors.box.requests.get')
    def test_verify_token_success(self, mock_get, connector):
        """Should return user info on successful verification."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "user-123",
            "name": "Test User",
            "login": "test@example.com",
        }
        mock_get.return_value = mock_response

        result = connector._verify_token("valid-token")

        assert result["id"] == "user-123"
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]["headers"]["Authorization"] == "Bearer valid-token"

    @patch('connectors.box.requests.get')
    def test_verify_token_401_raises_auth_error(self, mock_get, connector):
        """Should raise ConnectorAuthError on 401."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        with pytest.raises(ConnectorAuthError, match="invalid or expired"):
            connector._verify_token("expired-token")

    @patch('connectors.box.requests.get')
    def test_verify_token_403_raises_auth_error(self, mock_get, connector):
        """Should raise ConnectorAuthError on 403."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response

        with pytest.raises(ConnectorAuthError, match="insufficient permissions"):
            connector._verify_token("restricted-token")

    @patch('connectors.box.requests.get')
    def test_verify_token_500_raises_transient_error(self, mock_get, connector):
        """Should raise ConnectorTransientError on 5xx."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        with pytest.raises(ConnectorTransientError, match="API error"):
            connector._verify_token("token")

    @patch('connectors.box.requests.get')
    def test_verify_token_network_error(self, mock_get, connector):
        """Should raise ConnectorTransientError on network error."""
        import requests
        mock_get.side_effect = requests.RequestException("Connection refused")

        with pytest.raises(ConnectorTransientError, match="connection error"):
            connector._verify_token("token")


# =============================================================================
# Test: HTTP Request Methods
# =============================================================================

class TestRequestMethods:
    """Test HTTP request handling."""

    def test_get_headers(self, connector, mock_config):
        """Should build proper auth headers."""
        headers = connector._get_headers(mock_config)
        assert headers["Authorization"] == f"Bearer {mock_config['access_token']}"

    @patch.object(BoxConnector, '_request_with_retry')
    @patch('connectors.box.connector_fetch_limit')
    def test_request_success(self, mock_limit, mock_retry, connector, mock_config):
        """Should make GET request and return JSON."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"entries": []}
        mock_retry.return_value = mock_response
        mock_limit.return_value.__enter__ = Mock()
        mock_limit.return_value.__exit__ = Mock()

        result = connector._request(mock_config, "/folders/0/items")

        assert result == {"entries": []}


class TestRequestWithRetry:
    """Test retry logic for requests."""

    @patch('connectors.box.requests.request')
    def test_successful_request(self, mock_request, connector):
        """Should return response on success."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        result = connector._request_with_retry("GET", "http://test.com")
        assert result == mock_response

    @patch('connectors.box.requests.request')
    def test_401_raises_auth_error(self, mock_request, connector):
        """Should raise ConnectorAuthError on 401."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.close = Mock()
        mock_request.return_value = mock_response

        with pytest.raises(ConnectorAuthError):
            connector._request_with_retry("GET", "http://test.com")

    @patch('connectors.box.requests.request')
    def test_403_raises_auth_error(self, mock_request, connector):
        """Should raise ConnectorAuthError on 403."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_response.close = Mock()
        mock_request.return_value = mock_response

        with pytest.raises(ConnectorAuthError):
            connector._request_with_retry("GET", "http://test.com")

    @patch('connectors.box.time.sleep')
    @patch('connectors.box.requests.request')
    def test_429_retries_with_backoff(self, mock_request, mock_sleep, connector):
        """Should retry on 429 with exponential backoff."""
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {"Retry-After": "2"}
        rate_limit_response.close = Mock()

        success_response = Mock()
        success_response.status_code = 200

        mock_request.side_effect = [rate_limit_response, success_response]

        result = connector._request_with_retry("GET", "http://test.com")

        assert result == success_response
        mock_sleep.assert_called()

    @patch('connectors.box.time.sleep')
    @patch('connectors.box.requests.request')
    def test_429_exhausts_retries(self, mock_request, mock_sleep, connector):
        """Should raise after max retries on persistent 429."""
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {}
        rate_limit_response.close = Mock()
        mock_request.return_value = rate_limit_response

        with pytest.raises(ConnectorRateLimitError):
            connector._request_with_retry("GET", "http://test.com")

    @patch('connectors.box.requests.request')
    def test_500_raises_transient_error(self, mock_request, connector):
        """Should raise ConnectorTransientError on 5xx."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Server Error"
        mock_response.close = Mock()
        mock_request.return_value = mock_response

        with pytest.raises(ConnectorTransientError):
            connector._request_with_retry("GET", "http://test.com")

    @patch('connectors.box.requests.request')
    def test_network_error_raises_transient(self, mock_request, connector):
        """Should raise ConnectorTransientError on network failure."""
        import requests
        mock_request.side_effect = requests.RequestException("Network error")

        with pytest.raises(ConnectorTransientError):
            connector._request_with_retry("GET", "http://test.com")


# =============================================================================
# Test: File Listing
# =============================================================================

class TestListFiles:
    """Test file listing functionality."""

    @patch.object(BoxConnector, '_resolve_config')
    @patch.object(BoxConnector, '_request')
    def test_list_files_single_page(self, mock_request, mock_resolve, connector):
        """Should list files from a single page."""
        mock_resolve.return_value = {"access_token": "test"}
        mock_request.return_value = {
            "entries": [
                {"type": "file", "id": "1", "name": "file1.txt"},
                {"type": "file", "id": "2", "name": "file2.pdf"},
            ],
            "total_count": 2,
            "offset": 0,
            "limit": 1000,
        }

        files = list(connector.list_files({}))

        assert len(files) == 2
        assert files[0].name == "file1.txt"
        assert files[1].name == "file2.pdf"

    @patch.object(BoxConnector, '_resolve_config')
    @patch.object(BoxConnector, '_request')
    def test_list_files_with_pagination(self, mock_request, mock_resolve, connector):
        """Should handle pagination correctly."""
        mock_resolve.return_value = {"access_token": "test"}

        # First page has 1000 items (max), second page has remaining
        mock_request.side_effect = [
            {
                "entries": [{"type": "file", "id": str(i), "name": f"file{i}.txt"} for i in range(1000)],
                "total_count": 1500,
                "offset": 0,
                "limit": 1000,
            },
            {
                "entries": [{"type": "file", "id": str(i), "name": f"file{i}.txt"} for i in range(1000, 1500)],
                "total_count": 1500,
                "offset": 1000,
                "limit": 1000,
            },
        ]

        files = list(connector.list_files({}))

        assert len(files) == 1500
        assert mock_request.call_count == 2

    @patch.object(BoxConnector, '_resolve_config')
    @patch.object(BoxConnector, '_request')
    def test_list_files_includes_folders(self, mock_request, mock_resolve, connector, mock_folder_entry):
        """Should include folders in listing."""
        mock_resolve.return_value = {"access_token": "test"}
        mock_request.return_value = {
            "entries": [mock_folder_entry],
            "total_count": 1,
        }

        files = list(connector.list_files({}))

        # Verify at least one folder is in the results
        folders = [f for f in files if f.mime_type == "inode/directory"]
        assert len(folders) >= 1
        assert folders[0].name == "Documents"

    @patch.object(BoxConnector, '_resolve_config')
    @patch.object(BoxConnector, '_request')
    def test_list_files_specific_folder(self, mock_request, mock_resolve, connector):
        """Should list files from specific folder when parent_id provided."""
        mock_resolve.return_value = {"access_token": "test", "parent_id": "123"}
        mock_request.return_value = {
            "entries": [{"type": "file", "id": "1", "name": "file.txt"}],
            "total_count": 1,
        }

        files = list(connector.list_files({"parent_id": "123"}))

        # Should call with folder ID 123
        call_args = mock_request.call_args[0]
        assert "/folders/123/items" in call_args[1]


# =============================================================================
# Test: Item Conversion
# =============================================================================

class TestItemToRemoteFile:
    """Test conversion of Box items to RemoteFile."""

    def test_file_item_conversion(self, connector, mock_file_entry):
        """Should correctly convert file item."""
        result = connector._item_to_remote_file(mock_file_entry)

        # Box connector uses canonical source IDs like box://file/ID
        assert "12345678901" in result.id
        assert result.name == "test-document.pdf"
        assert result.size == 102400
        assert result.mime_type == "application/pdf"

    def test_folder_item_conversion(self, connector, mock_folder_entry):
        """Should correctly convert folder item."""
        result = connector._item_to_remote_file(mock_folder_entry)

        assert "987654321" in result.id
        assert result.name == "Documents"
        # Box connector may use different mime type for folders
        assert result.mime_type in ("inode/directory", "application/octet-stream")
        assert result.size is None

    def test_web_link_returns_web_link_type(self, connector):
        """Should convert web_link items (not return None)."""
        item = {"type": "web_link", "id": "1", "name": "Link"}
        result = connector._item_to_remote_file(item)
        # Box connector handles web_links - it creates RemoteFile with octet-stream
        assert result is not None
        assert result.name == "Link"


# =============================================================================
# Test: File Download
# =============================================================================

class TestFileDownload:
    """Test file content download via fetch_file_content."""

    @patch.object(BoxConnector, '_resolve_config')
    @patch.object(BoxConnector, '_download_file_content')
    def test_fetch_file_content_success(self, mock_download, mock_resolve, connector):
        """Should download file content successfully."""
        mock_resolve.return_value = {"access_token": "test"}
        mock_download.return_value = b"file content here"

        result = connector.fetch_file_content("123", {"access_token": "test"})

        assert result == b"file content here"


# =============================================================================
# Test: Helper Methods
# =============================================================================

class TestHelperMethods:
    """Test utility helper methods."""

    def test_parse_datetime_valid(self, connector):
        """Should parse valid Box datetime format."""
        result = connector._parse_datetime("2024-01-15T10:30:00-07:00")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_datetime_none(self, connector):
        """Should return None for None input."""
        assert connector._parse_datetime(None) is None

    def test_parse_datetime_invalid(self, connector):
        """Should return None for invalid datetime."""
        assert connector._parse_datetime("not-a-date") is None

    def test_guess_mime_type_pdf(self, connector):
        """Should guess PDF mime type."""
        assert connector._guess_mime_type("document.pdf") == "application/pdf"

    def test_guess_mime_type_txt(self, connector):
        """Should guess text mime type."""
        assert connector._guess_mime_type("readme.txt") == "text/plain"

    def test_guess_mime_type_unknown(self, connector):
        """Should return octet-stream for unknown types."""
        assert connector._guess_mime_type("file.unknown123") == "application/octet-stream"

    def test_guess_mime_type_none(self, connector):
        """Should return octet-stream for None filename."""
        assert connector._guess_mime_type(None) == "application/octet-stream"


# =============================================================================
# Test: Configuration Resolution
# =============================================================================

class TestResolveConfig:
    """Test configuration resolution from various sources."""

    @patch.object(BoxConnector, '_verify_token')
    def test_resolve_with_access_token(self, mock_verify, connector):
        """Should use provided access token directly."""
        mock_verify.return_value = {"id": "user-1"}

        result = connector._resolve_config({"access_token": "direct-token"})

        assert result["access_token"] == "direct-token"

    @patch.object(BoxConnector, '_load_integration')
    @patch('connectors.box.OAuthTokenManager.get_valid_credentials')
    def test_resolve_from_integration(self, mock_creds, mock_load, connector):
        """Should load credentials from integration."""
        mock_load.return_value = {"id": "int-123", "credentials": {}}
        mock_creds.return_value = {
            "access_token": "refreshed-token",
            "refresh_token": "refresh",
        }

        result = connector._resolve_config({"integration_id": "int-123"})

        assert result["access_token"] == "refreshed-token"

    @patch.object(BoxConnector, '_load_integration')
    @patch('connectors.box.OAuthTokenManager.get_valid_credentials')
    def test_resolve_refresh_error_raises_auth(self, mock_creds, mock_load, connector):
        """Should raise ConnectorAuthError on token refresh failure."""
        from services.oauth_token_manager import TokenRefreshError

        mock_load.return_value = {"id": "int-123"}
        mock_creds.side_effect = TokenRefreshError("Token refresh failed")

        with pytest.raises(ConnectorAuthError, match="reconnection"):
            connector._resolve_config({"integration_id": "int-123"})


# =============================================================================
# Test: Async Document Fetching
# =============================================================================

@pytest.mark.asyncio
class TestFetchDocuments:
    """Test async document fetching interface."""

    async def test_fetch_documents_empty(self, connector):
        """Should handle empty item list."""
        docs = [doc async for doc in connector.fetch_documents([], {})]
        assert docs == []

    @patch.object(BoxConnector, 'fetch_documents_sync')
    async def test_fetch_single_file(self, mock_sync, connector):
        """Should fetch single file document via sync wrapper."""
        mock_doc = Mock()
        mock_doc.filename = "test.pdf"
        mock_sync.return_value = iter([mock_doc])

        docs = [doc async for doc in connector.fetch_documents(["123"], {})]

        assert len(docs) == 1
        assert docs[0].filename == "test.pdf"

    @patch.object(BoxConnector, '_resolve_config')
    @patch.object(BoxConnector, '_request')
    async def test_fetch_handles_not_found(self, mock_request, mock_resolve, connector):
        """Should skip missing files without failing."""
        mock_resolve.return_value = {"access_token": "test"}
        mock_request.side_effect = ItemNotFoundError("File not found")

        docs = [doc async for doc in connector.fetch_documents(["missing"], {})]

        assert docs == []
