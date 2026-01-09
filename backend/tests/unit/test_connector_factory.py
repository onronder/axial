import pytest

from connectors.factory import get_connector
from connectors.file_upload import FileUploadConnector
from connectors.web import WebConnector
from connectors.drive import DriveConnector
from connectors.notion import NotionConnector


def test_factory_returns_file_upload():
    assert isinstance(get_connector("file"), FileUploadConnector)
    assert isinstance(get_connector("file_upload"), FileUploadConnector)


def test_factory_returns_web():
    assert isinstance(get_connector("web"), WebConnector)


def test_factory_returns_drive_aliases():
    assert isinstance(get_connector("drive"), DriveConnector)
    assert isinstance(get_connector("google_drive"), DriveConnector)


def test_factory_returns_notion():
    assert isinstance(get_connector("notion"), NotionConnector)


def test_factory_rejects_unknown():
    with pytest.raises(ValueError):
        get_connector("unknown")
