import pytest

from connectors.base import BaseConnector


class BaseConnectorHarness(BaseConnector):
    """Test harness implementing all abstract methods."""
    
    def list_files(self, config: dict, parent_id=None):
        return iter([])
    
    def fetch_file_content(self, file_id: str, config: dict) -> bytes:
        return b""
    
    def validate_config(self, config: dict) -> bool:
        return True


def test_base_connector_list_files_returns_iterator():
    """Test that list_files returns an iterator."""
    connector = BaseConnectorHarness()
    result = list(connector.list_files({}))
    assert result == []


def test_base_connector_fetch_file_content_returns_bytes():
    """Test that fetch_file_content returns bytes."""
    connector = BaseConnectorHarness()
    result = connector.fetch_file_content("file-1", {})
    assert result == b""


def test_base_connector_validate_config_returns_bool():
    """Test that validate_config returns a boolean."""
    connector = BaseConnectorHarness()
    assert connector.validate_config({}) is True
