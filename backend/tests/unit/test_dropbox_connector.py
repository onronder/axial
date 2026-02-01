"""
Comprehensive tests for Dropbox connector.

Tests cover:
- Configuration validation
- Token verification
- File listing with pagination
- Content download
- Team/Business account support
- Error handling (auth, rate limit, transient)
- Helper methods
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
import json

from connectors.dropbox import (
    DropboxConnector,
    get_dropbox_connector,
    DROPBOX_API_BASE,
    DROPBOX_CONTENT_BASE,
)
from connectors.base import (
    ConnectorAuthError,
    ConnectorRateLimitError,
    ConnectorTransientError,
    RemoteFile,
)
from connectors.enhanced import SourceType, ItemNotFoundError


class TestDropboxConnectorBasics:
    """Test basic connector properties and instantiation."""

    def test_connector_type_is_dropbox(self):
        connector = DropboxConnector()
        assert connector.connector_type == SourceType.DROPBOX

    def test_supports_incremental_sync(self):
        connector = DropboxConnector()
        assert connector.supports_incremental_sync is True

    def test_get_dropbox_connector_factory(self):
        connector = get_dropbox_connector()
        assert isinstance(connector, DropboxConnector)


class TestValidateConfig:
    """Test configuration validation."""

    def test_validate_config_rejects_non_dict(self):
        connector = DropboxConnector()
        assert connector.validate_config(None) is False
        assert connector.validate_config("string") is False
        assert connector.validate_config([]) is False

    def test_validate_config_requires_credential_source(self):
        connector = DropboxConnector()
        assert connector.validate_config({}) is False
        assert connector.validate_config({"other_key": "value"}) is False

    def test_validate_config_accepts_integration_id(self):
        connector = DropboxConnector()
        assert connector.validate_config({"integration_id": "int-123"}) is True

    def test_validate_config_accepts_user_id(self):
        connector = DropboxConnector()
        assert connector.validate_config({"user_id": "user-123"}) is True

    @patch.object(DropboxConnector, '_verify_token')
    def test_validate_config_verifies_access_token(self, mock_verify):
        mock_verify.return_value = {"account_id": "acc-123"}
        connector = DropboxConnector()
        result = connector.validate_config({"access_token": "test-token"})
        assert result is True
        mock_verify.assert_called_once_with("test-token")

    @patch.object(DropboxConnector, '_verify_token')
    def test_validate_config_rejects_invalid_token(self, mock_verify):
        mock_verify.side_effect = ConnectorAuthError("Invalid token")
        connector = DropboxConnector()
        result = connector.validate_config({"access_token": "invalid-token"})
        assert result is False

    @patch.object(DropboxConnector, '_verify_token')
    def test_validate_config_accepts_on_network_error(self, mock_verify):
        """Network errors during validation shouldn't reject config."""
        mock_verify.side_effect = Exception("Network timeout")
        connector = DropboxConnector()
        result = connector.validate_config({"access_token": "test-token"})
        assert result is True


class TestVerifyToken:
    """Test token verification."""

    @patch('connectors.dropbox.requests.post')
    def test_verify_token_success(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "account_id": "acc-123",
            "email": "test@example.com",
            "root_info": {"root_namespace_id": "ns-123"}
        }
        mock_post.return_value = mock_response

        connector = DropboxConnector()
        result = connector._verify_token("test-token")

        assert result["account_id"] == "acc-123"
        assert result["root_info"]["root_namespace_id"] == "ns-123"

    @patch('connectors.dropbox.requests.post')
    def test_verify_token_unauthorized(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        connector = DropboxConnector()
        with pytest.raises(ConnectorAuthError, match="invalid or expired"):
            connector._verify_token("bad-token")

    @patch('connectors.dropbox.requests.post')
    def test_verify_token_server_error(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        connector = DropboxConnector()
        with pytest.raises(ConnectorTransientError, match="API error"):
            connector._verify_token("test-token")

    @patch('connectors.dropbox.requests.post')
    def test_verify_token_network_error(self, mock_post):
        import requests
        mock_post.side_effect = requests.RequestException("Connection refused")

        connector = DropboxConnector()
        with pytest.raises(ConnectorTransientError, match="connection error"):
            connector._verify_token("test-token")


class TestGetHeaders:
    """Test header building with Team account support."""

    def test_get_headers_basic(self):
        connector = DropboxConnector()
        headers = connector._get_headers({"access_token": "test-token"})

        assert headers["Authorization"] == "Bearer test-token"
        assert headers["Content-Type"] == "application/json"

    def test_get_headers_no_content_type(self):
        connector = DropboxConnector()
        headers = connector._get_headers(
            {"access_token": "test-token"},
            content_type=None
        )

        assert headers["Authorization"] == "Bearer test-token"
        assert "Content-Type" not in headers

    def test_get_headers_with_namespace_id(self):
        """Team accounts should include Path Root header."""
        connector = DropboxConnector()
        headers = connector._get_headers({
            "access_token": "test-token",
            "namespace_id": "ns-123"
        })

        assert "Dropbox-API-Path-Root" in headers
        path_root = json.loads(headers["Dropbox-API-Path-Root"])
        assert path_root[".tag"] == "root"
        assert path_root["root"] == "ns-123"


class TestRequestWithRetry:
    """Test HTTP request handling with retries."""

    @patch('connectors.dropbox.requests.request')
    def test_successful_request(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        connector = DropboxConnector()
        result = connector._request_with_retry("GET", "http://test.com")

        assert result == mock_response

    @patch('connectors.dropbox.requests.request')
    def test_auth_error_401(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.close = Mock()
        mock_request.return_value = mock_response

        connector = DropboxConnector()
        with pytest.raises(ConnectorAuthError, match="auth failed"):
            connector._request_with_retry("GET", "http://test.com")

    @patch('connectors.dropbox.requests.request')
    def test_auth_error_403(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_response.close = Mock()
        mock_request.return_value = mock_response

        connector = DropboxConnector()
        with pytest.raises(ConnectorAuthError):
            connector._request_with_retry("GET", "http://test.com")

    @patch('connectors.dropbox.requests.request')
    def test_server_error_500(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Server Error"
        mock_response.close = Mock()
        mock_request.return_value = mock_response

        connector = DropboxConnector()
        with pytest.raises(ConnectorTransientError, match="server error"):
            connector._request_with_retry("GET", "http://test.com")

    @patch('connectors.dropbox.requests.request')
    def test_network_error(self, mock_request):
        import requests
        mock_request.side_effect = requests.RequestException("Network error")

        connector = DropboxConnector()
        with pytest.raises(ConnectorTransientError, match="network error"):
            connector._request_with_retry("GET", "http://test.com")

    @patch('connectors.dropbox.time.sleep')
    @patch('connectors.dropbox.requests.request')
    def test_rate_limit_with_retry(self, mock_request, mock_sleep):
        """Should retry on 429 with Retry-After header."""
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {"Retry-After": "2"}
        rate_limit_response.close = Mock()

        success_response = Mock()
        success_response.status_code = 200

        mock_request.side_effect = [rate_limit_response, success_response]

        connector = DropboxConnector()
        result = connector._request_with_retry("GET", "http://test.com")

        assert result == success_response
        mock_sleep.assert_called_once_with(2)

    @patch('connectors.dropbox.time.sleep')
    @patch('connectors.dropbox.requests.request')
    def test_rate_limit_exceeded_after_max_retries(self, mock_request, mock_sleep):
        """Should raise after MAX_RETRIES rate limit errors."""
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {}
        rate_limit_response.close = Mock()

        mock_request.return_value = rate_limit_response

        connector = DropboxConnector()
        with pytest.raises(ConnectorRateLimitError, match="exceeded after retries"):
            connector._request_with_retry("GET", "http://test.com")


class TestParseRetryAfter:
    """Test Retry-After header parsing."""

    def test_parse_valid_integer(self):
        connector = DropboxConnector()
        assert connector._parse_retry_after("5", default=1) == 5
        assert connector._parse_retry_after("10", default=1) == 10

    def test_parse_none_returns_default(self):
        connector = DropboxConnector()
        assert connector._parse_retry_after(None, default=3) == 3

    def test_parse_invalid_returns_default(self):
        connector = DropboxConnector()
        assert connector._parse_retry_after("invalid", default=2) == 2

    def test_parse_zero_returns_one(self):
        """Should return at least 1 second."""
        connector = DropboxConnector()
        assert connector._parse_retry_after("0", default=1) == 1


class TestRPCRequest:
    """Test RPC-style API requests."""

    @patch.object(DropboxConnector, '_request_with_retry')
    @patch.object(DropboxConnector, '_get_headers')
    @patch('connectors.dropbox.connector_fetch_limit')
    def test_rpc_request_success(self, mock_limit, mock_headers, mock_request):
        mock_headers.return_value = {"Authorization": "Bearer test"}
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_request.return_value = mock_response
        mock_limit.return_value.__enter__ = Mock()
        mock_limit.return_value.__exit__ = Mock()

        connector = DropboxConnector()
        result = connector._rpc_request(
            {"access_token": "test"},
            "/files/list_folder",
            {"path": ""}
        )

        assert result == {"result": "success"}

    @patch.object(DropboxConnector, '_request_with_retry')
    @patch.object(DropboxConnector, '_get_headers')
    @patch('connectors.dropbox.connector_fetch_limit')
    def test_rpc_request_path_not_found(self, mock_limit, mock_headers, mock_request):
        mock_headers.return_value = {"Authorization": "Bearer test"}
        mock_response = Mock()
        mock_response.status_code = 409
        mock_response.content = b'{"error": {".tag": "path"}, "error_summary": "path/not_found"}'
        mock_response.json.return_value = {
            "error": {".tag": "path"},
            "error_summary": "path/not_found"
        }
        mock_request.return_value = mock_response
        mock_limit.return_value.__enter__ = Mock()
        mock_limit.return_value.__exit__ = Mock()

        connector = DropboxConnector()
        with pytest.raises(ItemNotFoundError, match="not found"):
            connector._rpc_request(
                {"access_token": "test"},
                "/files/get_metadata",
                {"path": "/nonexistent"}
            )


class TestContentDownload:
    """Test file content download."""

    @patch.object(DropboxConnector, '_request_with_retry')
    @patch.object(DropboxConnector, '_get_headers')
    @patch('connectors.dropbox.connector_fetch_limit')
    def test_download_success(self, mock_limit, mock_headers, mock_request):
        mock_headers.return_value = {"Authorization": "Bearer test"}
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b"file", b"content"]
        mock_response.close = Mock()
        mock_request.return_value = mock_response
        mock_limit.return_value.__enter__ = Mock()
        mock_limit.return_value.__exit__ = Mock()

        connector = DropboxConnector()
        result = connector._content_download({"access_token": "test"}, "/file.txt")

        assert result == b"filecontent"

    @patch.object(DropboxConnector, '_request_with_retry')
    @patch.object(DropboxConnector, '_get_headers')
    @patch('connectors.dropbox.connector_fetch_limit')
    def test_download_not_found(self, mock_limit, mock_headers, mock_request):
        mock_headers.return_value = {"Authorization": "Bearer test"}
        mock_response = Mock()
        mock_response.status_code = 409
        mock_response.headers = {"Dropbox-API-Result": "not found"}
        mock_response.close = Mock()
        mock_request.return_value = mock_response
        mock_limit.return_value.__enter__ = Mock()
        mock_limit.return_value.__exit__ = Mock()

        connector = DropboxConnector()
        with pytest.raises(ItemNotFoundError, match="file not found"):
            connector._content_download({"access_token": "test"}, "/nonexistent.txt")


class TestListFiles:
    """Test file listing with pagination."""

    @patch.object(DropboxConnector, '_resolve_config')
    @patch.object(DropboxConnector, '_rpc_request')
    def test_list_files_single_page(self, mock_rpc, mock_resolve):
        mock_resolve.return_value = {"access_token": "test"}
        mock_rpc.return_value = {
            "entries": [
                {".tag": "file", "id": "id:1", "name": "file1.txt", "size": 100},
                {".tag": "file", "id": "id:2", "name": "file2.pdf", "size": 200},
            ],
            "has_more": False
        }

        connector = DropboxConnector()
        files = list(connector.list_files({}))

        assert len(files) == 2
        assert files[0].name == "file1.txt"
        assert files[1].name == "file2.pdf"

    @patch.object(DropboxConnector, '_resolve_config')
    @patch.object(DropboxConnector, '_rpc_request')
    def test_list_files_with_pagination(self, mock_rpc, mock_resolve):
        mock_resolve.return_value = {"access_token": "test"}
        mock_rpc.side_effect = [
            {
                "entries": [{".tag": "file", "id": "id:1", "name": "file1.txt"}],
                "has_more": True,
                "cursor": "cursor-123"
            },
            {
                "entries": [{".tag": "file", "id": "id:2", "name": "file2.txt"}],
                "has_more": False
            }
        ]

        connector = DropboxConnector()
        files = list(connector.list_files({}))

        assert len(files) == 2
        assert mock_rpc.call_count == 2

    @patch.object(DropboxConnector, '_resolve_config')
    @patch.object(DropboxConnector, '_rpc_request')
    def test_list_files_includes_folders(self, mock_rpc, mock_resolve):
        mock_resolve.return_value = {"access_token": "test"}
        mock_rpc.return_value = {
            "entries": [
                {".tag": "folder", "id": "id:folder", "name": "Documents", "path_display": "/Documents"},
                {".tag": "file", "id": "id:file", "name": "readme.txt"},
            ],
            "has_more": False
        }

        connector = DropboxConnector()
        files = list(connector.list_files({}))

        assert len(files) == 2
        folder = next(f for f in files if f.name == "Documents")
        assert folder.mime_type == "inode/directory"

    @patch.object(DropboxConnector, '_resolve_config')
    @patch.object(DropboxConnector, '_rpc_request')
    def test_list_files_handles_not_found(self, mock_rpc, mock_resolve):
        mock_resolve.return_value = {"access_token": "test"}
        mock_rpc.side_effect = ItemNotFoundError("Path not found")

        connector = DropboxConnector()
        files = list(connector.list_files({}))

        assert files == []


class TestEntryToRemoteFile:
    """Test metadata conversion to RemoteFile."""

    def test_file_entry(self):
        connector = DropboxConnector()
        entry = {
            ".tag": "file",
            "id": "id:abc123",
            "name": "document.pdf",
            "size": 12345,
            "server_modified": "2024-01-15T10:30:00Z",
            "path_display": "/Folder/document.pdf"
        }

        result = connector._entry_to_remote_file(entry)

        assert result.id == "id:abc123"
        assert result.name == "document.pdf"
        assert result.size == 12345
        assert result.mime_type == "application/pdf"
        assert result.parent_id == "/Folder"

    def test_folder_entry(self):
        connector = DropboxConnector()
        entry = {
            ".tag": "folder",
            "id": "id:folder123",
            "name": "My Folder",
            "path_display": "/My Folder"
        }

        result = connector._entry_to_remote_file(entry)

        assert result.id == "id:folder123"
        assert result.name == "My Folder"
        assert result.mime_type == "inode/directory"
        assert result.size is None

    def test_folder_entry_excluded(self):
        connector = DropboxConnector()
        entry = {".tag": "folder", "name": "Folder"}

        result = connector._entry_to_remote_file(entry, include_folders=False)

        assert result is None

    def test_since_filter_excludes_old_files(self):
        connector = DropboxConnector()
        since = datetime(2024, 2, 1, tzinfo=timezone.utc)
        entry = {
            ".tag": "file",
            "id": "id:old",
            "name": "old.txt",
            "server_modified": "2024-01-15T10:30:00Z"
        }

        result = connector._entry_to_remote_file(entry, since=since)

        assert result is None

    def test_since_filter_includes_new_files(self):
        connector = DropboxConnector()
        since = datetime(2024, 1, 1, tzinfo=timezone.utc)
        entry = {
            ".tag": "file",
            "id": "id:new",
            "name": "new.txt",
            "server_modified": "2024-01-15T10:30:00Z"
        }

        result = connector._entry_to_remote_file(entry, since=since)

        assert result is not None
        assert result.name == "new.txt"

    def test_non_file_entry_excluded(self):
        connector = DropboxConnector()
        entry = {".tag": "deleted", "name": "deleted.txt"}

        result = connector._entry_to_remote_file(entry)

        assert result is None


class TestHelperMethods:
    """Test utility methods."""

    def test_normalize_path_id_with_dropbox_id(self):
        connector = DropboxConnector()
        assert connector._normalize_path_id("id:abc123") == "id:abc123"
        assert connector._normalize_path_id("dbid:xyz") == "dbid:xyz"

    def test_normalize_path_id_with_path(self):
        connector = DropboxConnector()
        assert connector._normalize_path_id("/folder/file.txt") == "/folder/file.txt"

    def test_normalize_path_id_adds_leading_slash(self):
        connector = DropboxConnector()
        assert connector._normalize_path_id("folder/file.txt") == "/folder/file.txt"

    def test_normalize_path_id_empty_string(self):
        connector = DropboxConnector()
        assert connector._normalize_path_id("") == ""

    def test_get_parent_path(self):
        connector = DropboxConnector()
        assert connector._get_parent_path("/Folder/file.txt") == "/Folder"
        assert connector._get_parent_path("/file.txt") == "/"  # Root-level file
        assert connector._get_parent_path("/a/b/c/file.txt") == "/a/b/c"

    def test_get_parent_path_none(self):
        connector = DropboxConnector()
        assert connector._get_parent_path(None) is None

    def test_parse_datetime_valid(self):
        result = DropboxConnector._parse_datetime("2024-01-15T10:30:00Z")
        assert result == datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    def test_parse_datetime_none(self):
        assert DropboxConnector._parse_datetime(None) is None

    def test_parse_datetime_invalid(self):
        assert DropboxConnector._parse_datetime("not-a-date") is None

    def test_guess_mime_type(self):
        assert DropboxConnector._guess_mime_type("document.pdf") == "application/pdf"
        assert DropboxConnector._guess_mime_type("image.png") == "image/png"
        assert DropboxConnector._guess_mime_type("file.txt") == "text/plain"

    def test_guess_mime_type_unknown(self):
        # .xyz is actually a known chemical format, use truly unknown extension
        assert DropboxConnector._guess_mime_type("unknown.zzzzz") == "application/octet-stream"

    def test_guess_mime_type_none(self):
        assert DropboxConnector._guess_mime_type(None) == "application/octet-stream"


class TestResolveConfig:
    """Test configuration resolution."""

    @patch.object(DropboxConnector, '_verify_token')
    def test_resolve_with_access_token(self, mock_verify):
        mock_verify.return_value = {
            "account_id": "acc-123",
            "root_info": {"root_namespace_id": "ns-456"}
        }

        connector = DropboxConnector()
        result = connector._resolve_config({"access_token": "test-token"})

        assert result["access_token"] == "test-token"
        assert result["namespace_id"] == "ns-456"

    @patch.object(DropboxConnector, '_verify_token')
    def test_resolve_preserves_existing_namespace(self, mock_verify):
        """Should not overwrite existing namespace_id."""
        connector = DropboxConnector()
        result = connector._resolve_config({
            "access_token": "test-token",
            "namespace_id": "existing-ns"
        })

        assert result["namespace_id"] == "existing-ns"
        mock_verify.assert_not_called()

    @patch.object(DropboxConnector, '_load_integration')
    @patch('connectors.dropbox.OAuthTokenManager.get_valid_credentials')
    def test_resolve_loads_integration(self, mock_creds, mock_load):
        mock_load.return_value = {
            "id": "int-123",
            "credentials": {"namespace_id": "ns-789", "root_path": "/Team"}
        }
        mock_creds.return_value = {
            "access_token": "refreshed-token",
            "refresh_token": "refresh",
            "expires_at": "2024-12-31"
        }

        connector = DropboxConnector()
        result = connector._resolve_config({"integration_id": "int-123"})

        assert result["access_token"] == "refreshed-token"
        assert result["namespace_id"] == "ns-789"
        assert result["root_path"] == "/Team"


class TestFetchFileContent:
    """Test file content fetching."""

    @patch.object(DropboxConnector, '_resolve_config')
    @patch.object(DropboxConnector, '_content_download')
    def test_fetch_file_content(self, mock_download, mock_resolve):
        mock_resolve.return_value = {"access_token": "test"}
        mock_download.return_value = b"file content here"

        connector = DropboxConnector()
        result = connector.fetch_file_content("id:abc123", {})

        assert result == b"file content here"
        mock_download.assert_called_once()


@pytest.mark.asyncio
class TestFetchDocuments:
    """Test async document fetching."""

    async def test_fetch_documents_empty_list(self):
        connector = DropboxConnector()
        docs = [doc async for doc in connector.fetch_documents([], {})]
        assert docs == []

    @patch.object(DropboxConnector, '_resolve_config')
    @patch.object(DropboxConnector, '_rpc_request')
    @patch.object(DropboxConnector, '_build_source_document')
    async def test_fetch_documents_single_file(self, mock_build, mock_rpc, mock_resolve):
        mock_resolve.return_value = {"access_token": "test"}
        mock_rpc.return_value = {
            ".tag": "file",
            "id": "id:file123",
            "name": "test.pdf",
            "path_lower": "/test.pdf"
        }
        mock_doc = Mock()
        mock_build.return_value = mock_doc

        connector = DropboxConnector()
        docs = [doc async for doc in connector.fetch_documents(["id:file123"], {})]

        assert len(docs) == 1
        assert docs[0] == mock_doc

    @patch.object(DropboxConnector, '_resolve_config')
    @patch.object(DropboxConnector, '_rpc_request')
    async def test_fetch_documents_handles_not_found(self, mock_rpc, mock_resolve):
        mock_resolve.return_value = {"access_token": "test"}
        mock_rpc.side_effect = ItemNotFoundError("Not found")

        connector = DropboxConnector()
        docs = [doc async for doc in connector.fetch_documents(["id:missing"], {})]

        assert docs == []


class TestFetchDocumentsSync:
    """Test synchronous document fetching."""

    @patch.object(DropboxConnector, '_resolve_config')
    def test_fetch_documents_sync_empty(self, mock_resolve):
        connector = DropboxConnector()
        result = list(connector.fetch_documents_sync([], {}))
        assert result == []
        mock_resolve.assert_not_called()
