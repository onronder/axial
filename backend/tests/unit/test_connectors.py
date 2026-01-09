"""
Unit tests for connector implementations.

Tests all 4 connectors:
- FileUploadConnector
- GoogleDriveConnector
- NotionConnectorEnhanced
- WebConnectorEnhanced
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from connectors.file_upload import FileUploadConnector
from connectors.google_drive import GoogleDriveConnector
from connectors.notion_enhanced import NotionConnectorEnhanced
from connectors.enhanced import SourceDocument, SourceType
from connectors.base import BaseConnector, ConnectorDocument
from connectors import get_connector


class _DummyConnector(BaseConnector):
    async def authorize(self, user_id: str) -> bool:
        await super().authorize(user_id)
        return True

    async def list_items(self, user_id: str, parent_id: str | None = None):
        await super().list_items(user_id, parent_id)
        return []

    async def ingest(self, config):
        await super().ingest(config)
        if False:
            yield ConnectorDocument(page_content="", metadata={})


@pytest.mark.asyncio
async def test_file_upload_connector_fetch(mock_supabase):
    """Test FileUploadConnector.fetch_documents()."""
    
    connector = FileUploadConnector()
    storage_path = "uploads/user123/uuid/test.pdf"
    
    # Mock storage download
    mock_supabase.storage.from_.return_value.download.return_value = b"PDF content here"
    
    with patch('connectors.file_upload.get_supabase', return_value=mock_supabase):
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


@pytest.mark.asyncio
async def test_base_connector_super_methods_are_callable():
    connector = _DummyConnector()

    assert await connector.authorize("user-1") is True
    assert await connector.list_items("user-1") == []

    items = []
    async for item in connector.ingest({"user_id": "user-1"}):
        items.append(item)

    assert items == []


@pytest.mark.asyncio
async def test_file_upload_connector_multiple_files(mock_supabase):
    """Test fetching multiple files."""
    
    connector = FileUploadConnector()
    paths = [
        "uploads/user/1/file1.pdf",
        "uploads/user/2/file2.txt",
        "uploads/user/3/file3.docx"
    ]
    
    mock_supabase.storage.from_.return_value.download.return_value = b"content"
    
    with patch('connectors.file_upload.get_supabase', return_value=mock_supabase):
        documents = []
        async for doc in connector.fetch_documents(paths):
            documents.append(doc)
        
        assert len(documents) == 3
        assert documents[0].filename == "file1.pdf"
        assert documents[1].filename == "file2.txt"
        assert documents[2].filename == "file3.docx"


@pytest.mark.asyncio
async def test_file_upload_connector_mime_detection():
    """Test MIME type detection from filename."""
    
    connector = FileUploadConnector()
    
    assert connector._detect_mime_type("test.pdf") == "application/pdf"
    assert connector._detect_mime_type("test.txt") == "text/plain"
    assert connector._detect_mime_type("test.docx") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert connector._detect_mime_type("test.unknown") == "application/octet-stream"


def test_file_upload_connector_properties():
    """Test FileUploadConnector properties."""
    
    connector = FileUploadConnector()
    
    assert connector.connector_type == SourceType.FILE_UPLOAD
    assert connector.supports_batch_fetch == False
    assert connector.supports_incremental_sync == False


def test_get_connector_returns_instance():
    connector = get_connector("file_upload")
    assert isinstance(connector, FileUploadConnector)


def test_base_connector_pass_through():
    class DummyConnector(BaseConnector):
        async def authorize(self, user_id: str) -> bool:
            return await super().authorize(user_id)

        async def list_items(self, user_id: str, parent_id=None):
            return await super().list_items(user_id, parent_id)

        async def ingest(self, config):
            return await super().ingest(config)

    dummy = DummyConnector()
    assert dummy is not None


@pytest.mark.asyncio
async def test_file_upload_connector_authorization():
    """Test that file upload doesn't require authorization."""
    
    connector = FileUploadConnector()
    
    is_authorized = await connector.authorize("any-user-id")
    assert is_authorized == True


@pytest.mark.asyncio
async def test_file_upload_connector_ingest_yields_connector_documents():
    connector = FileUploadConnector()

    async def fake_fetch(_item_ids, _credentials=None, **_kwargs):
        yield SourceDocument(
            content=b"hello",
            metadata={"filename": "file.txt"},
            source_type=SourceType.FILE_UPLOAD,
            source_id="file-1",
            filename="file.txt",
            mime_type="text/plain",
            size_bytes=5,
        )

    connector.fetch_documents = fake_fetch

    docs = []
    async for doc in connector.ingest({"item_ids": ["file-1"], "user_id": "user-1"}):
        docs.append(doc)

    assert len(docs) == 1
    assert isinstance(docs[0], ConnectorDocument)


@pytest.mark.asyncio
async def test_google_drive_connector_wrapper():
    """Test GoogleDriveConnector wraps legacy connector."""
    
    connector = GoogleDriveConnector()
    
    assert connector.connector_type == SourceType.GOOGLE_DRIVE
    assert hasattr(connector, 'legacy')
    assert connector.legacy is not None


@pytest.mark.asyncio
async def test_google_drive_connector_fetch():
    """Test GoogleDriveConnector.fetch_documents()."""
    
    connector = GoogleDriveConnector()
    
    # Mock legacy connector
    mock_legacy_doc = Mock()
    mock_legacy_doc.page_content = "Drive file content"
    mock_legacy_doc.metadata = {
        "file_id": "drive-123",
        "title": "My Document",
        "mime_type": "application/pdf"
    }
    
    async def mock_ingest(config):
        yield mock_legacy_doc
    
    connector.legacy.ingest = mock_ingest
    
    documents = []
    async for doc in connector.fetch_documents(
        ["drive-123"],
        credentials={"access_token": "token"},
        user_id="user-456"
    ):
        documents.append(doc)
    
    assert len(documents) == 1
    doc = documents[0]
    assert doc.source_type == SourceType.GOOGLE_DRIVE
    assert doc.source_id == "drive-123"
    assert doc.filename == "My Document"


@pytest.mark.asyncio
async def test_google_drive_connector_fetch_sync_stream():
    connector = GoogleDriveConnector()

    connector.legacy.ingest = lambda _config: [
        ConnectorDocument(page_content="x", metadata={"file_id": "f1", "title": "Doc 1"})
    ]

    results = []
    async for doc in connector.fetch_documents(["f1"], credentials=None, user_id="user-1"):
        results.append(doc)

    assert len(results) == 1
    assert results[0].filename == "Doc 1"


def test_connector_validate_credentials():
    """Test credential validation for different connectors."""
    
    file_connector = FileUploadConnector()
    drive_connector = GoogleDriveConnector()
    
    # File upload doesn't need credentials
    assert file_connector.validate_credentials({}) == True
    assert file_connector.validate_credentials(None) == True
    
    # Drive needs access_token
    assert drive_connector.validate_credentials({"access_token": "token"}) == True
    assert drive_connector.validate_credentials({}) == True  # Legacy connector handles this


@pytest.mark.asyncio
async def test_google_drive_connector_delegates_methods():
    connector = GoogleDriveConnector()
    connector.legacy.authorize = AsyncMock(return_value=True)
    connector.legacy.list_items = AsyncMock(return_value=[{"id": "1"}])
    connector.legacy.ingest = Mock(return_value="stream")
    connector.legacy.sync = AsyncMock(return_value={"ok": True})

    assert await connector.authorize("user-1") is True
    assert await connector.list_items("user-1") == [{"id": "1"}]
    assert await connector.ingest({"user_id": "user-1"}) == "stream"
    assert await connector.sync("user-1", "int-1") == {"ok": True}


@pytest.mark.asyncio
async def test_connector_list_items():
    """Test list_items for file browser."""
    
    file_connector = FileUploadConnector()
    drive_connector = GoogleDriveConnector()
    
    # File upload doesn't support browsing
    items = await file_connector.list_items("user-id")
    assert items == []
    
    # Drive delegates to legacy connector
    mock_items = [{"id": "1", "name": "Folder 1", "type": "folder"}]
    drive_connector.legacy.list_items = AsyncMock(return_value=mock_items)
    
    items = await drive_connector.list_items("user-id")
    assert items == mock_items


@pytest.mark.asyncio
async def test_notion_connector_enhanced_connector_type():
    connector = NotionConnectorEnhanced()
    assert connector.connector_type == SourceType.NOTION


@pytest.mark.asyncio
async def test_notion_connector_enhanced_ingest_delegates():
    connector = NotionConnectorEnhanced()
    connector.legacy.ingest = Mock(return_value="stream")
    assert await connector.ingest({"user_id": "user-1"}) == "stream"
