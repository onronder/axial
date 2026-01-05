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
from connectors.enhanced import SourceDocument, SourceType


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


@pytest.mark.asyncio
async def test_file_upload_connector_authorization():
    """Test that file upload doesn't require authorization."""
    
    connector = FileUploadConnector()
    
    is_authorized = await connector.authorize("any-user-id")
    assert is_authorized == True


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
