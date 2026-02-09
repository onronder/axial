"""
Production-Grade Tests for SFTP Connector

Following best practices:
- Security validation (SSRF protection)
- Connection handling
- File operations
- Error mapping
- Authentication methods (password/key)

Coverage Target: 95%+
"""

import stat
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

from connectors.base import (
    ConnectorAuthError,
    ConnectorTransientError,
)
from connectors.enhanced import ItemNotFoundError, SourceType
from connectors.sftp import (
    SFTPConnector,
)

# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def connector():
    """Create a fresh SFTPConnector instance."""
    return SFTPConnector()


@pytest.fixture
def valid_config():
    """Valid SFTP configuration with password auth."""
    return {
        "host": "sftp.example.com",
        "port": 22,
        "username": "testuser",
        "password": "testpass123",
        "root_path": "/data",
        "_allow_private": True,  # Skip SSRF check in tests
    }


@pytest.fixture
def key_config():
    """Valid SFTP configuration with key auth."""
    return {
        "host": "sftp.example.com",
        "port": 22,
        "username": "testuser",
        "private_key": "-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----",
        "root_path": "/",
        "_allow_private": True,
    }


@pytest.fixture
def mock_sftp():
    """Create a mock SFTP client."""
    mock = MagicMock()
    mock.listdir_attr.return_value = []
    return mock


@pytest.fixture
def mock_transport():
    """Create a mock Transport."""
    return MagicMock()


# =============================================================================
# Test: Connector Properties
# =============================================================================

class TestConnectorProperties:
    """Test basic connector properties."""

    def test_connector_type_is_sftp(self, connector):
        """Connector type should be SFTP."""
        assert connector.connector_type == SourceType.SFTP


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

    def test_rejects_missing_host(self, connector):
        """Should reject config without host."""
        config = {
            "username": "user",
            "password": "pass",
            "_allow_private": True,
        }
        assert connector.validate_config(config) is False

    def test_rejects_missing_username(self, connector):
        """Should reject config without username."""
        config = {
            "host": "sftp.example.com",
            "password": "pass",
            "_allow_private": True,
        }
        assert connector.validate_config(config) is False

    def test_rejects_missing_credentials(self, connector):
        """Should reject config without password or private_key."""
        config = {
            "host": "sftp.example.com",
            "username": "user",
            "_allow_private": True,
        }
        assert connector.validate_config(config) is False

    def test_accepts_password_auth(self, connector, valid_config):
        """Should accept config with password."""
        assert connector.validate_config(valid_config) is True

    def test_accepts_key_auth(self, connector, key_config):
        """Should accept config with private_key."""
        assert connector.validate_config(key_config) is True

    def test_rejects_invalid_port_type(self, connector, valid_config):
        """Should reject non-integer port."""
        valid_config["port"] = "22"  # String instead of int
        assert connector.validate_config(valid_config) is False

    def test_rejects_invalid_root_path_type(self, connector, valid_config):
        """Should reject non-string root_path."""
        valid_config["root_path"] = 123
        assert connector.validate_config(valid_config) is False

    def test_default_port_is_22(self, connector, valid_config):
        """Should use default port 22 when not specified."""
        del valid_config["port"]
        assert connector.validate_config(valid_config) is True


# =============================================================================
# Test: SSRF Protection
# =============================================================================

class TestSSRFProtection:
    """Test SSRF protection mechanisms."""

    @patch('connectors.sftp.socket.gethostbyname')
    def test_blocks_private_ip_without_flag(self, mock_resolve, connector):
        """Should block private IPs without _allow_private flag."""
        mock_resolve.return_value = "192.168.1.1"
        config = {
            "host": "internal.example.com",
            "username": "user",
            "password": "pass",
        }
        # Should raise ValueError due to private IP
        with pytest.raises(ValueError, match="private network"):
            connector.validate_config(config)

    @patch('connectors.sftp.socket.gethostbyname')
    def test_blocks_localhost(self, mock_resolve, connector):
        """Should block localhost."""
        mock_resolve.return_value = "127.0.0.1"
        config = {
            "host": "localhost",
            "username": "user",
            "password": "pass",
        }
        with pytest.raises(ValueError, match="private network"):
            connector.validate_config(config)

    @patch('connectors.sftp.socket.gethostbyname')
    def test_blocks_loopback(self, mock_resolve, connector):
        """Should block loopback addresses."""
        mock_resolve.return_value = "127.0.0.1"
        config = {
            "host": "example.com",
            "username": "user",
            "password": "pass",
        }
        with pytest.raises(ValueError, match="private network"):
            connector.validate_config(config)

    def test_allows_private_with_flag(self, connector, valid_config):
        """Should allow private IPs with _allow_private flag."""
        valid_config["host"] = "192.168.1.1"
        assert connector.validate_config(valid_config) is True


# =============================================================================
# Test: File Listing
# =============================================================================

class TestListFiles:
    """Test file listing functionality."""

    @patch.object(SFTPConnector, '_sftp_connection')
    @patch.object(SFTPConnector, '_resolve_config')
    def test_list_files_non_recursive(self, mock_resolve, mock_conn, connector, valid_config):
        """Should list files non-recursively when parent_id is 'root'."""
        mock_resolve.return_value = valid_config

        # Create mock file attributes
        file_attr = MagicMock()
        file_attr.filename = "test.txt"
        file_attr.st_size = 1024
        file_attr.st_mtime = 1704067200  # 2024-01-01
        file_attr.st_mode = stat.S_IFREG

        mock_sftp = MagicMock()
        mock_sftp.listdir_attr.return_value = [file_attr]
        mock_conn.return_value.__enter__ = Mock(return_value=mock_sftp)
        mock_conn.return_value.__exit__ = Mock(return_value=False)

        files = list(connector.list_files({**valid_config, "parent_id": "root"}))

        assert len(files) == 1
        assert files[0].name == "test.txt"
        assert files[0].size == 1024

    @patch.object(SFTPConnector, '_sftp_connection')
    @patch.object(SFTPConnector, '_resolve_config')
    def test_list_files_includes_directories(self, mock_resolve, mock_conn, connector, valid_config):
        """Should include directories in listing."""
        mock_resolve.return_value = valid_config

        dir_attr = MagicMock()
        dir_attr.filename = "subdir"
        dir_attr.st_mtime = 1704067200
        dir_attr.st_mode = stat.S_IFDIR

        mock_sftp = MagicMock()
        mock_sftp.listdir_attr.return_value = [dir_attr]
        mock_conn.return_value.__enter__ = Mock(return_value=mock_sftp)
        mock_conn.return_value.__exit__ = Mock(return_value=False)

        files = list(connector.list_files({**valid_config, "parent_id": "root"}))

        assert len(files) == 1
        assert files[0].name == "subdir"
        assert files[0].mime_type == "inode/directory"

    @patch.object(SFTPConnector, '_sftp_connection')
    @patch.object(SFTPConnector, '_resolve_config')
    def test_list_files_skips_dot_entries(self, mock_resolve, mock_conn, connector, valid_config):
        """Should skip . and .. entries."""
        mock_resolve.return_value = valid_config

        dot_attr = MagicMock()
        dot_attr.filename = "."

        dotdot_attr = MagicMock()
        dotdot_attr.filename = ".."

        mock_sftp = MagicMock()
        mock_sftp.listdir_attr.return_value = [dot_attr, dotdot_attr]
        mock_conn.return_value.__enter__ = Mock(return_value=mock_sftp)
        mock_conn.return_value.__exit__ = Mock(return_value=False)

        files = list(connector.list_files({**valid_config, "parent_id": "root"}))

        assert len(files) == 0

    @patch.object(SFTPConnector, '_sftp_connection')
    @patch.object(SFTPConnector, '_resolve_config')
    def test_list_files_since_filter(self, mock_resolve, mock_conn, connector, valid_config):
        """Should filter files by modification time."""
        mock_resolve.return_value = valid_config

        old_file = MagicMock()
        old_file.filename = "old.txt"
        old_file.st_size = 100
        old_file.st_mtime = 1640995200  # 2022-01-01
        old_file.st_mode = stat.S_IFREG

        new_file = MagicMock()
        new_file.filename = "new.txt"
        new_file.st_size = 200
        new_file.st_mtime = 1704067200  # 2024-01-01
        new_file.st_mode = stat.S_IFREG

        mock_sftp = MagicMock()
        mock_sftp.listdir_attr.return_value = [old_file, new_file]
        mock_conn.return_value.__enter__ = Mock(return_value=mock_sftp)
        mock_conn.return_value.__exit__ = Mock(return_value=False)

        since = datetime(2023, 1, 1, tzinfo=timezone.utc)
        files = list(connector.list_files({**valid_config, "parent_id": "root"}, since=since))

        assert len(files) == 1
        assert files[0].name == "new.txt"


# =============================================================================
# Test: File Content Fetching
# =============================================================================

class TestFetchFileContent:
    """Test file content fetching."""

    @patch.object(SFTPConnector, '_sftp_connection')
    @patch.object(SFTPConnector, '_resolve_config')
    def test_fetch_file_content_success(self, mock_resolve, mock_conn, connector, valid_config):
        """Should fetch file content successfully."""
        mock_resolve.return_value = valid_config

        mock_sftp = MagicMock()
        mock_file = MagicMock()
        mock_file.read.return_value = b"file content here"
        mock_sftp.open.return_value.__enter__ = Mock(return_value=mock_file)
        mock_sftp.open.return_value.__exit__ = Mock(return_value=False)

        mock_conn.return_value.__enter__ = Mock(return_value=mock_sftp)
        mock_conn.return_value.__exit__ = Mock(return_value=False)

        result = connector.fetch_file_content("/data/test.txt", valid_config)

        assert result == b"file content here"

    @patch.object(SFTPConnector, '_sftp_connection')
    @patch.object(SFTPConnector, '_resolve_config')
    def test_fetch_file_not_found(self, mock_resolve, mock_conn, connector, valid_config):
        """Should raise ItemNotFoundError when file doesn't exist."""
        mock_resolve.return_value = valid_config

        mock_sftp = MagicMock()
        mock_sftp.open.side_effect = OSError("No such file")

        mock_conn.return_value.__enter__ = Mock(return_value=mock_sftp)
        mock_conn.return_value.__exit__ = Mock(return_value=False)

        with pytest.raises(ItemNotFoundError):
            connector.fetch_file_content("/data/missing.txt", valid_config)


# =============================================================================
# Test: Connection Management
# =============================================================================

class TestConnectionManagement:
    """Test SFTP connection handling."""

    @patch('connectors.sftp.paramiko.Transport')
    @patch('connectors.sftp.paramiko.SFTPClient.from_transport')
    def test_connection_with_password(self, mock_sftp_client, mock_transport, connector, valid_config):
        """Should connect using password authentication."""
        mock_transport_instance = MagicMock()
        mock_transport.return_value = mock_transport_instance
        mock_sftp = MagicMock()
        mock_sftp_client.return_value = mock_sftp

        with connector._sftp_connection(valid_config) as sftp:
            assert sftp == mock_sftp

        mock_transport_instance.connect.assert_called_once()

    @patch('connectors.sftp.paramiko.Transport')
    @patch('connectors.sftp.paramiko.SFTPClient.from_transport')
    @patch('connectors.sftp.paramiko.RSAKey.from_private_key')
    def test_connection_with_private_key(self, mock_key, mock_sftp_client, mock_transport, connector, key_config):
        """Should connect using private key authentication."""
        mock_transport_instance = MagicMock()
        mock_transport.return_value = mock_transport_instance
        mock_sftp = MagicMock()
        mock_sftp_client.return_value = mock_sftp
        mock_key.return_value = MagicMock()

        with connector._sftp_connection(key_config) as sftp:
            assert sftp == mock_sftp

    @patch('connectors.sftp.paramiko.Transport')
    def test_connection_timeout(self, mock_transport, connector, valid_config):
        """Should raise error on connection timeout."""
        mock_transport.side_effect = TimeoutError("Connection timed out")

        with pytest.raises(ConnectorTransientError):
            with connector._sftp_connection(valid_config):
                pass

    @patch('connectors.sftp.paramiko.Transport')
    def test_connection_auth_failure(self, mock_transport, connector, valid_config):
        """Should raise ConnectorAuthError on auth failure."""
        import paramiko
        mock_transport_instance = MagicMock()
        mock_transport.return_value = mock_transport_instance
        mock_transport_instance.connect.side_effect = paramiko.AuthenticationException("Auth failed")

        with pytest.raises(ConnectorAuthError):
            with connector._sftp_connection(valid_config):
                pass


# =============================================================================
# Test: Path Handling
# =============================================================================

class TestPathHandling:
    """Test path normalization and handling."""

    def test_normalize_root_path(self, connector):
        """Should normalize root path."""
        assert connector._normalize_root("/") == "/"
        assert connector._normalize_root("/data") == "/data"
        assert connector._normalize_root("/data/") == "/data"

    def test_normalize_path_joining(self, connector):
        """Should correctly join paths."""
        assert connector._normalize_path("/root", "subdir") == "/root/subdir"
        assert connector._normalize_path("/root", "/absolute") == "/absolute"


# =============================================================================
# Test: Datetime Conversion
# =============================================================================

class TestDatetimeConversion:
    """Test timestamp to datetime conversion."""

    def test_to_datetime_valid_timestamp(self, connector):
        """Should convert valid timestamp."""
        result = connector._to_datetime(1704067200)  # 2024-01-01 00:00:00 UTC
        assert result is not None
        assert result.year == 2024

    def test_to_datetime_none(self, connector):
        """Should return None for None input."""
        assert connector._to_datetime(None) is None


# =============================================================================
# Test: Async Document Fetching
# =============================================================================

@pytest.mark.asyncio
class TestAsyncFetchDocuments:
    """Test async document fetching interface."""

    async def test_fetch_documents_empty(self, connector):
        """Should handle empty item list."""
        docs = [doc async for doc in connector.fetch_documents([], {})]
        assert docs == []

    @patch.object(SFTPConnector, '_resolve_config')
    @patch.object(SFTPConnector, '_sftp_connection')
    async def test_fetch_documents_single_file(self, mock_conn, mock_resolve, connector, valid_config):
        """Should fetch single file as document."""
        mock_resolve.return_value = valid_config

        mock_sftp = MagicMock()
        # Mock stat for file info
        file_stat = MagicMock()
        file_stat.st_size = 1024
        file_stat.st_mtime = 1704067200
        file_stat.st_mode = stat.S_IFREG
        mock_sftp.stat.return_value = file_stat

        # Mock file content
        mock_file = MagicMock()
        mock_file.read.return_value = b"content"
        mock_sftp.open.return_value.__enter__ = Mock(return_value=mock_file)
        mock_sftp.open.return_value.__exit__ = Mock(return_value=False)

        mock_conn.return_value.__enter__ = Mock(return_value=mock_sftp)
        mock_conn.return_value.__exit__ = Mock(return_value=False)

        docs = [doc async for doc in connector.fetch_documents(["/data/test.txt"], valid_config)]

        assert len(docs) == 1
