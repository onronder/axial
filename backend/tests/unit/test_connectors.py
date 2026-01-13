"""
Unit tests for connector implementations (unified ingestion interface).
"""

import pytest
from unittest.mock import Mock, patch

from connectors.file_upload import FileUploadConnector
from connectors.drive import DriveConnector
from connectors.notion import NotionConnector
from connectors.microsoft import MicrosoftGraphConnector
from connectors.sftp import SFTPConnector
from connectors.web import WebConnector
from connectors.enhanced import ItemNotFoundError, SourceDocument, SourceType
from connectors import get_connector


@pytest.mark.asyncio
async def test_file_upload_connector_fetch(mock_supabase):
    connector = FileUploadConnector()
    storage_path = "uploads/user123/uuid/test.pdf"

    mock_supabase.storage.from_.return_value.download.return_value = b"PDF content here"

    with patch("connectors.file_upload.get_supabase", return_value=mock_supabase):
        documents = []
        async for doc in connector.fetch_documents([storage_path]):
            documents.append(doc)

    assert len(documents) == 1
    doc = documents[0]
    assert isinstance(doc, SourceDocument)
    assert doc.source_type == SourceType.FILE_UPLOAD
    assert doc.filename == "test.pdf"
    assert doc.mime_type == "application/pdf"
    assert doc.size_bytes == len(b"PDF content here")


def test_file_upload_connector_missing_file_raises():
    connector = FileUploadConnector()
    supabase = Mock()
    supabase.storage.from_.return_value.download.return_value = None

    with patch("connectors.file_upload.get_supabase", return_value=supabase):
        with pytest.raises(ItemNotFoundError):
            list(connector.fetch_documents_sync(["uploads/user/missing.pdf"]))


@pytest.mark.asyncio
async def test_file_upload_connector_multiple_files(mock_supabase):
    connector = FileUploadConnector()
    paths = [
        "uploads/user/1/file1.pdf",
        "uploads/user/2/file2.txt",
        "uploads/user/3/file3.docx",
    ]

    mock_supabase.storage.from_.return_value.download.return_value = b"content"

    with patch("connectors.file_upload.get_supabase", return_value=mock_supabase):
        documents = []
        async for doc in connector.fetch_documents(paths):
            documents.append(doc)

    assert [doc.filename for doc in documents] == ["file1.pdf", "file2.txt", "file3.docx"]


def test_file_upload_connector_mime_detection():
    connector = FileUploadConnector()
    assert connector._detect_mime_type("test.pdf") == "application/pdf"
    assert connector._detect_mime_type("test.txt") == "text/plain"
    assert (
        connector._detect_mime_type("test.docx")
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert connector._detect_mime_type("test.unknown") == "application/octet-stream"


def test_get_connector_returns_instances():
    assert isinstance(get_connector("file_upload"), FileUploadConnector)
    assert isinstance(get_connector("google_drive"), DriveConnector)
    assert isinstance(get_connector("notion"), NotionConnector)
    assert isinstance(get_connector("sftp"), SFTPConnector)
    assert isinstance(get_connector("onedrive"), MicrosoftGraphConnector)
    assert isinstance(get_connector("sharepoint"), MicrosoftGraphConnector)
    assert isinstance(get_connector("web"), WebConnector)


def test_get_connector_unknown_type_raises():
    with pytest.raises(ValueError):
        get_connector("unknown")


@pytest.mark.asyncio
async def test_file_upload_connector_flags_and_auth():
    connector = FileUploadConnector()
    assert connector.connector_type == SourceType.FILE_UPLOAD
    assert await connector.authorize("user-1") is True
    assert list(connector.list_files({}, None)) == []
    assert connector.validate_credentials({"any": "value"}) is True
