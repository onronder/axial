"""
Tests for Connector Architecture Refactoring

Verifies that:
1. DriveConnector uses passed credentials (no DB call) when provided
2. DriveConnector falls back to DB lookup when only user_id is provided
3. WebConnector uses trafilatura and returns correct ConnectorDocument format
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestDriveConnectorRefactoring:
    """Tests for Drive connector with hybrid credential logic."""

    @patch('connectors.drive.build')
    @patch('connectors.drive.get_supabase')
    def test_drive_ingest_uses_passed_credentials(self, mock_supabase, mock_build):
        """When credentials are passed in config, DriveConnector should use them directly without DB lookup."""
        from connectors.drive import DriveConnector
        from connectors.base import ConnectorDocument
        
        # Setup mocks
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        # Mock files().get() response
        mock_file_meta = {
            'id': 'test_file_id',
            'name': 'test.txt',
            'mimeType': 'text/plain',
            'webViewLink': 'https://drive.google.com/file/test'
        }
        mock_service.files.return_value.get.return_value.execute.return_value = mock_file_meta
        mock_service.files.return_value.get_media.return_value.execute.return_value = b'Test file content'
        
        connector = DriveConnector()
        
        # Config with explicit credentials (worker case)
        config = {
            "user_id": "test_user_123",
            "item_ids": ["test_file_id"],
            "credentials": {
                "access_token": "test_access_token",
                "refresh_token": "test_refresh_token"
            },
            "provider": "google_drive"
        }
        
        # Execute
        docs = connector.ingest(config)
        
        # Verify: build() was called (service created)
        mock_build.assert_called_once()
        
        # Verify: get_supabase was NOT called (no DB lookup)
        mock_supabase.assert_not_called()
        
        # Verify: credentials were passed to build
        call_args = mock_build.call_args
        assert call_args[0][0] == 'drive'
        assert call_args[0][1] == 'v3'
        # The credentials argument should be present
        assert 'credentials' in call_args[1]

    @patch('connectors.drive.build')
    @patch('connectors.drive.get_supabase')
    def test_drive_ingest_falls_back_to_db_when_no_credentials(self, mock_supabase, mock_build):
        """When no credentials are passed, DriveConnector should lookup from DB using user_id."""
        from connectors.drive import DriveConnector
        
        # Setup mock for DB lookup
        mock_client = MagicMock()
        mock_supabase.return_value = mock_client
        
        # Mock connector definition lookup
        mock_def_response = MagicMock()
        mock_def_response.data = {"id": "connector_def_123"}
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_def_response
        
        # Mock user integration lookup
        mock_integration_response = MagicMock()
        mock_integration_response.data = [{
            "id": "integration_123",
            "access_token": "encrypted_access_token",
            "refresh_token": "encrypted_refresh_token"
        }]
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_integration_response
        
        # Mock service
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_file_meta = {
            'id': 'test_file_id',
            'name': 'test.txt',
            'mimeType': 'text/plain',
            'webViewLink': 'https://drive.google.com/file/test'
        }
        mock_service.files.return_value.get.return_value.execute.return_value = mock_file_meta
        mock_service.files.return_value.get_media.return_value.execute.return_value = b'Test content'
        
        connector = DriveConnector()
        
        # Config WITHOUT credentials (API case - should trigger DB lookup)
        config = {
            "user_id": "test_user_123",
            "item_ids": ["test_file_id"],
            "provider": "google_drive"
            # No "credentials" key
        }
        
        with patch('connectors.drive.decrypt_token', side_effect=lambda x: x):
            # Execute
            docs = connector.ingest(config)
        
        # Verify: get_supabase WAS called (DB lookup happened)
        mock_supabase.assert_called()

    def test_drive_ingest_raises_when_no_credentials_or_user_id(self):
        """When neither credentials nor user_id are provided, should raise ValueError."""
        from connectors.drive import DriveConnector
        
        connector = DriveConnector()
        
        # Empty config
        config = {
            "item_ids": ["test_file_id"],
            "provider": "google_drive"
        }
        
        with pytest.raises(ValueError, match="No credentials or user_id provided"):
            connector.ingest(config)


class TestWebConnectorRefactoring:
    """Tests for Web connector with trafilatura."""

    @patch('connectors.web.trafilatura')
    def test_web_ingest_uses_trafilatura(self, mock_trafilatura):
        """WebConnector should use trafilatura for extraction."""
        from connectors.web import WebConnector
        from connectors.base import ConnectorDocument
        
        # Setup mocks
        mock_trafilatura.fetch_url.return_value = "<html><body>Test content</body></html>"
        mock_trafilatura.extract.return_value = "Extracted article text"
        
        mock_metadata = MagicMock()
        mock_metadata.title = "Test Article Title"
        mock_trafilatura.extract_metadata.return_value = mock_metadata
        
        connector = WebConnector()
        
        config = {
            "item_ids": ["https://example.com/article"],
            "user_id": "test_user"
        }
        
        # Execute
        docs = connector.ingest(config)
        
        # Verify: trafilatura was called
        mock_trafilatura.fetch_url.assert_called_once_with("https://example.com/article")
        mock_trafilatura.extract.assert_called_once()
        
        # Verify: Returns correct format
        assert len(docs) == 1
        assert isinstance(docs[0], ConnectorDocument)
        assert docs[0].page_content == "Extracted article text"
        assert docs[0].metadata["source"] == "web"
        assert docs[0].metadata["title"] == "Test Article Title"
        assert docs[0].metadata["source_url"] == "https://example.com/article"

    @patch('connectors.web.trafilatura')
    def test_web_ingest_handles_failed_downloads(self, mock_trafilatura):
        """WebConnector should gracefully handle failed downloads."""
        from connectors.web import WebConnector
        
        # Simulate download failure
        mock_trafilatura.fetch_url.return_value = None
        
        connector = WebConnector()
        
        config = {
            "item_ids": ["https://example.com/broken"],
            "user_id": "test_user"
        }
        
        # Should not raise, just return empty list
        docs = connector.ingest(config)
        
        assert len(docs) == 0

    @patch('connectors.web.trafilatura')
    def test_web_ingest_handles_extraction_failure(self, mock_trafilatura):
        """WebConnector should gracefully handle extraction failures."""
        from connectors.web import WebConnector
        
        # Download succeeds but extraction returns None
        mock_trafilatura.fetch_url.return_value = "<html></html>"
        mock_trafilatura.extract.return_value = None
        mock_trafilatura.extract_metadata.return_value = None
        
        connector = WebConnector()
        
        config = {
            "item_ids": ["https://example.com/empty"],
            "user_id": "test_user"
        }
        
        docs = connector.ingest(config)
        
        assert len(docs) == 0

    @patch('connectors.web.trafilatura')
    def test_web_ingest_uses_url_as_title_when_no_metadata(self, mock_trafilatura):
        """When metadata extraction fails, use URL as title."""
        from connectors.web import WebConnector
        
        mock_trafilatura.fetch_url.return_value = "<html><body>Content</body></html>"
        mock_trafilatura.extract.return_value = "Some content"
        mock_trafilatura.extract_metadata.return_value = None  # No metadata
        
        connector = WebConnector()
        
        url = "https://example.com/no-title"
        config = {
            "item_ids": [url],
            "user_id": "test_user"
        }
        
        docs = connector.ingest(config)
        
        assert len(docs) == 1
        assert docs[0].metadata["title"] == url  # Falls back to URL


class TestWorkerIntegration:
    """Tests that worker calls connector.ingest with correct config."""

    def test_worker_calls_ingest_with_config(self):
        """Worker should call connector.ingest(config) with proper structure."""
        # This is a structural test - verify the worker code uses the right pattern
        import inspect
        from worker import tasks
        source = inspect.getsource(tasks.ingest_file_task)
        
        # Verify the config structure is used
        assert 'ingest_config' in source or 'config' in source, "Worker should prepare a config dict"
        assert 'connector.ingest(ingest_config)' in source, "Worker should call connector.ingest(config)"
        assert 'ingest_sync' not in source, "Old method ingest_sync should NOT be present"
        
        # Verify all expected config keys are populated
        assert '"user_id"' in source, "Config should contain user_id"
        assert '"item_ids"' in source, "Config should contain item_ids"
        assert '"credentials"' in source, "Config should contain credentials"
        assert '"provider"' in source, "Config should contain provider"
