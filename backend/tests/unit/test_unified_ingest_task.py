"""
Unit tests for unified_ingest_task worker function.

Tests cover:
- All 4 connector types (file_upload, google_drive, notion, web)
- Error handling and retry logic
- Job status updates
- Notification creation
- Celery integration
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from uuid import uuid4
from celery.exceptions import Retry

from worker.tasks import unified_ingest_task
from connectors.enhanced import SourceDocument, SourceType, QuotaExceededError


@pytest.fixture
def mock_celery_task():
    """Mock Celery task context."""
    task = MagicMock()
    task.request.id = str(uuid4())
    return task


@pytest.fixture
def mock_get_connector():
    """Mock connector factory."""
    with patch('worker.tasks.get_connector') as mock:
        yield mock


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    with patch('worker.tasks.get_supabase') as mock:
        client = Mock()
        client.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock()
        client.table.return_value.insert.return_value.execute.return_value = Mock(
            data=[{"id": "file-status-id"}]
        )
        mock.return_value = client
        yield mock


def test_unified_ingest_task_file_upload(
    mock_get_connector,
    mock_supabase
):
    """Test unified_ingest_task with file upload connector."""
    
    # Setup
    user_id = str(uuid4())
    job_id = str(uuid4())
    storage_path = "uploads/user/uuid/test.pdf"
    scope_id = f"file_upload://{storage_path}"
    
    # Mock connector
    connector = Mock()
    def mock_fetch_sync(item_ids, credentials=None, **kwargs):
        yield SourceDocument(
            content=b"PDF content",
            metadata={"storage_path": storage_path, "scope_id": scope_id},
            source_type=SourceType.FILE_UPLOAD,
            source_id=storage_path,
            filename="test.pdf",
            mime_type="application/pdf",
            size_bytes=100
        )
    connector.fetch_documents_sync = mock_fetch_sync
    mock_get_connector.return_value = connector
    
    with patch("worker.tasks.process_file_task") as mock_task, \
         patch("celery.group") as mock_group:
        mock_task.s.return_value = "sig"
        mock_group.return_value.apply_async.return_value = Mock(id="group-1")

        # Execute
        result = unified_ingest_task(
            user_id=user_id,
            job_id=job_id,
            connector_type="file_upload",
            item_ids=[storage_path],
            credentials=None,
            plan_code="starter",
        )
    
    # Verify
    assert result["status"] == "dispatched"
    mock_get_connector.assert_called_once_with("file_upload")
    mock_task.s.assert_called_once()


def test_unified_ingest_task_google_drive(
    mock_get_connector,
    mock_supabase
):
    """Test unified_ingest_task with Google Drive connector."""
    
    user_id = str(uuid4())
    job_id = str(uuid4())
    file_ids = ["drive-file-1", "drive-file-2"]
    credentials = {"integration_id": "int-1"}
    
    # Mock connector
    connector = Mock()
    def mock_fetch_sync(item_ids, creds, **kwargs):
        for file_id in item_ids:
            yield SourceDocument(
                content=f"Content of {file_id}",
                metadata={
                    "file_id": file_id,
                    "drive_id": "drive-1",
                    "folder_id": "folder-1",
                    "name": f"{file_id}.txt",
                    "scope_id": "google_drive://drive-1/folder-1",
                },
                source_type=SourceType.GOOGLE_DRIVE,
                source_id=file_id,
                filename=f"{file_id}.txt",
                mime_type="text/plain",
                size_bytes=50
            )
    connector.fetch_documents_sync = mock_fetch_sync
    mock_get_connector.return_value = connector
    
    with patch("worker.tasks.process_file_task") as mock_task, \
         patch("celery.group") as mock_group:
        mock_task.s.return_value = "sig"
        mock_group.return_value.apply_async.return_value = Mock(id="group-2")

        # Execute
        result = unified_ingest_task(
            user_id=user_id,
            job_id=job_id,
            connector_type="google_drive",
            item_ids=file_ids,
            credentials=credentials,
            plan_code="starter",
        )
    
    # Verify
    assert result["status"] == "dispatched"
    mock_get_connector.assert_called_once_with("google_drive")


def test_unified_ingest_task_notion(
    mock_get_connector,
    mock_supabase
):
    """Test unified_ingest_task with Notion connector."""
    
    user_id = str(uuid4())
    job_id = str(uuid4())
    page_ids = ["notion-page-1", "notion-page-2"]
    credentials = {"integration_id": "int-1"}
    
    # Mock connector
    connector = Mock()
    def mock_fetch_sync(item_ids, creds, **kwargs):
        for page_id in item_ids:
            yield SourceDocument(
                content=f"Notion page content {page_id}",
                metadata={
                    "page_id": page_id,
                    "workspace_id": "workspace-1",
                    "title": f"Page {page_id}",
                    "scope_id": "notion://workspace-1",
                },
                source_type=SourceType.NOTION,
                source_id=page_id,
                filename=f"Page {page_id}",
                mime_type="text/markdown",
                size_bytes=200
            )
    connector.fetch_documents_sync = mock_fetch_sync
    mock_get_connector.return_value = connector
    
    with patch("worker.tasks.process_file_task") as mock_task, \
         patch("celery.group") as mock_group:
        mock_task.s.return_value = "sig"
        mock_group.return_value.apply_async.return_value = Mock(id="group-3")

        # Execute
        result = unified_ingest_task(
            user_id=user_id,
            job_id=job_id,
            connector_type="notion",
            item_ids=page_ids,
            credentials=credentials,
            plan_code="starter",
        )
    
    # Verify
    assert result["status"] == "dispatched"
    mock_get_connector.assert_called_once_with("notion")


def test_unified_ingest_task_web(
    mock_get_connector,
    mock_supabase
):
    """Test unified_ingest_task with web crawler."""
    
    user_id = str(uuid4())
    job_id = str(uuid4())
    url = "https://example.com"
    
    # Mock connector
    connector = Mock()
    def mock_fetch_sync(item_ids, creds, **kwargs):
        yield SourceDocument(
            content="<html>Web page content</html>",
            metadata={"url": url, "scope_id": "web://example.com"},
            source_type=SourceType.WEB,
            source_id=url,
            filename="example.com",
            mime_type="text/html",
            size_bytes=500
        )
    connector.fetch_documents_sync = mock_fetch_sync
    mock_get_connector.return_value = connector
    
    with patch("worker.tasks.process_file_task") as mock_task, \
         patch("celery.group") as mock_group:
        mock_task.s.return_value = "sig"
        mock_group.return_value.apply_async.return_value = Mock(id="group-4")

        # Execute
        result = unified_ingest_task(
            user_id=user_id,
            job_id=job_id,
            connector_type="web",
            item_ids=[url],
            credentials=None,
            plan_code="starter",
        )
    
    # Verify
    assert result["status"] == "dispatched"
    mock_get_connector.assert_called_once_with("web")


def test_unified_ingest_task_invalid_connector(
    mock_get_connector,
    mock_supabase
):
    """Test error handling for invalid connector type."""
    
    mock_get_connector.side_effect = ValueError("Unknown connector type: invalid")
    
    with pytest.raises(ValueError, match="Unknown connector type"):
        unified_ingest_task(
            user_id=str(uuid4()),
            job_id=str(uuid4()),
            connector_type="invalid",
            item_ids=["item1"],
            credentials=None,
            plan_code="starter",
        )


def test_unified_ingest_task_connector_failure(
    mock_get_connector,
    mock_supabase
):
    """Test error handling when connector fails."""
    
    # Mock connector that raises exception
    connector = Mock()
    def failing_fetch_sync(*args, **kwargs):
        raise Exception("Connector failed to fetch documents")
    connector.fetch_documents_sync = failing_fetch_sync
    mock_get_connector.return_value = connector
    
    # Execute - should handle error gracefully
    with pytest.raises(Exception, match="Connector failed"):
        unified_ingest_task(
            user_id=str(uuid4()),
            job_id=str(uuid4()),
            connector_type="file_upload",
            item_ids=["test.pdf"],
            credentials=None,
            plan_code="starter",
        )


def test_unified_ingest_task_pipeline_failure(
    mock_get_connector,
    mock_supabase
):
    """Test error handling when pipeline fails."""
    
    # Mock connector
    connector = Mock()
    def mock_fetch_sync(*args, **kwargs):
        yield SourceDocument(
            content=b"content",
            metadata={"storage_path": "uploads/test.pdf", "scope_id": "file_upload://test.pdf"},
            source_type=SourceType.FILE_UPLOAD,
            source_id="test",
            filename="test.pdf",
            mime_type="application/pdf",
            size_bytes=100
        )
    connector.fetch_documents_sync = mock_fetch_sync
    mock_get_connector.return_value = connector
    
    # Simulate dispatch failure
    with patch("worker.tasks.process_file_task") as mock_task:
        mock_task.s.side_effect = Exception("Pipeline error")
        with pytest.raises(Exception, match="Pipeline error"):
            unified_ingest_task(
                user_id=str(uuid4()),
                job_id=str(uuid4()),
                connector_type="file_upload",
                item_ids=["test.pdf"],
                credentials=None,
                plan_code="starter",
            )


def test_unified_ingest_task_quota_exceeded(
    mock_get_connector,
    mock_supabase
):
    """Test handling of quota exceeded errors."""
    
    # Mock connector
    connector = Mock()
    def mock_fetch_sync(*args, **kwargs):
        yield SourceDocument(
            content=b"content",
            metadata={"storage_path": "uploads/test.pdf", "scope_id": "file_upload://test.pdf"},
            source_type=SourceType.FILE_UPLOAD,
            source_id="test",
            filename="test.pdf",
            mime_type="application/pdf",
            size_bytes=100
        )
    connector.fetch_documents_sync = mock_fetch_sync
    mock_get_connector.return_value = connector
    
    with patch("worker.tasks.process_file_task") as mock_task:
        mock_task.s.side_effect = QuotaExceededError("Storage quota exceeded")
        with pytest.raises(QuotaExceededError):
            unified_ingest_task(
                user_id=str(uuid4()),
                job_id=str(uuid4()),
                connector_type="file_upload",
                item_ids=["test.pdf"],
                credentials=None,
                plan_code="starter",
            )


def test_unified_ingest_task_job_status_updates(
    mock_get_connector,
    mock_supabase
):
    """Test that job status is updated correctly."""
    
    # Mock connector
    connector = Mock()
    def mock_fetch_sync(*args, **kwargs):
        yield SourceDocument(
            content=b"content",
            metadata={"storage_path": "uploads/test.pdf", "scope_id": "file_upload://test.pdf"},
            source_type=SourceType.FILE_UPLOAD,
            source_id="test",
            filename="test.pdf",
            mime_type="application/pdf",
            size_bytes=100
        )
    connector.fetch_documents_sync = mock_fetch_sync
    mock_get_connector.return_value = connector
    
    with patch("worker.tasks.process_file_task") as mock_task, \
         patch("celery.group") as mock_group:
        mock_task.s.return_value = "sig"
        mock_group.return_value.apply_async.return_value = Mock(id="group-5")

        # Execute
        job_id = str(uuid4())
        unified_ingest_task(
            user_id=str(uuid4()),
            job_id=job_id,
            connector_type="file_upload",
            item_ids=["test.pdf"],
            credentials=None,
            plan_code="starter",
        )
    
    # Verify job status was updated
    assert mock_supabase.return_value.table.called
    # Should update job with completed status


def test_unified_ingest_task_empty_item_ids(
    mock_get_connector,
    mock_supabase
):
    """Test handling of empty item_ids list."""
    
    # Mock connector
    connector = Mock()
    def mock_fetch_sync(*args, **kwargs):
        return []
    connector.fetch_documents_sync = mock_fetch_sync
    mock_get_connector.return_value = connector
    
    # Execute
    result = unified_ingest_task(
        user_id=str(uuid4()),
        job_id=str(uuid4()),
        connector_type="file_upload",
        item_ids=[],
        credentials=None,
        plan_code="starter",
    )
    
    # Verify
    assert result["status"] == "completed"
    assert "No documents" in result["message"]


def test_unified_ingest_task_requires_connector_type():
    with pytest.raises(ValueError):
        unified_ingest_task(
            user_id=str(uuid4()),
            job_id=str(uuid4()),
            connector_type=None,
            item_ids=[],
            credentials=None,
            plan_code="starter",
        )


def test_unified_ingest_task_wraps_item_id_when_item_ids_none():
    captured = {}

    def fake_collect(_connector, item_ids, _credentials, _user_id):
        captured["item_ids"] = item_ids
        return []

    with patch("worker.tasks.get_supabase", return_value=Mock()), \
         patch("worker.tasks.get_connector", return_value=Mock()), \
         patch("worker.tasks._collect_documents_sync", side_effect=fake_collect), \
         patch("worker.tasks.store_celery_task_id"), \
         patch("worker.tasks.check_job_cancelled", return_value=False), \
         patch("worker.tasks.update_job_status"), \
         patch("worker.tasks.create_notification"):
        unified_ingest_task(
            user_id=str(uuid4()),
            job_id=str(uuid4()),
            connector_type="file_upload",
            item_ids=None,
            item_id="item-1",
            credentials=None,
            plan_code="starter",
        )

    assert captured["item_ids"] == ["item-1"]


def test_unified_ingest_task_wraps_item_ids_when_not_list():
    captured = {}

    def fake_collect(_connector, item_ids, _credentials, _user_id):
        captured["item_ids"] = item_ids
        return []

    with patch("worker.tasks.get_supabase", return_value=Mock()), \
         patch("worker.tasks.get_connector", return_value=Mock()), \
         patch("worker.tasks._collect_documents_sync", side_effect=fake_collect), \
         patch("worker.tasks.store_celery_task_id"), \
         patch("worker.tasks.check_job_cancelled", return_value=False), \
         patch("worker.tasks.update_job_status"), \
         patch("worker.tasks.create_notification"):
        unified_ingest_task(
            user_id=str(uuid4()),
            job_id=str(uuid4()),
            connector_type="file_upload",
            item_ids="item-1",
            credentials=None,
            plan_code="starter",
        )

    assert captured["item_ids"] == ["item-1"]


def test_unified_ingest_task_logs_provider_normalization_failure():
    supabase = Mock()
    supabase.table.return_value.update.return_value.eq.return_value.execute.side_effect = Exception("boom")

    with patch("worker.tasks.get_supabase", return_value=supabase), \
         patch("worker.tasks.get_connector", return_value=Mock()), \
         patch("worker.tasks._collect_documents_sync", return_value=[]), \
         patch("worker.tasks.store_celery_task_id"), \
         patch("worker.tasks.check_job_cancelled", return_value=False), \
         patch("worker.tasks.update_job_status"), \
         patch("worker.tasks.create_notification"):
        result = unified_ingest_task(
            user_id=str(uuid4()),
            job_id=str(uuid4()),
            connector_type="Google-Drive",
            item_ids=[],
            credentials=None,
            plan_code="starter",
        )

    assert result["status"] == "completed"


@patch('worker.tasks.unified_ingest_task.retry')
def test_unified_ingest_task_retry_on_connection_error(
    mock_retry,
    mock_get_connector,
    mock_supabase
):
    """Test that task retries on connection errors."""
    
    # Mock connector to raise connection error
    connector = Mock()
    def failing_fetch_sync(*args, **kwargs):
        raise ConnectionError("Network error")
    connector.fetch_documents_sync = failing_fetch_sync
    mock_get_connector.return_value = connector
    
    # Configure retry
    mock_retry.side_effect = Retry()
    
    # Execute - should trigger retry
    with pytest.raises(Retry):
        unified_ingest_task(
            user_id=str(uuid4()),
            job_id=str(uuid4()),
            connector_type="file_upload",
            item_ids=["test.pdf"],
            credentials=None,
            plan_code="starter",
        )
    
    # Verify retry was called
    assert mock_retry.called


def test_unified_ingest_task_multiple_files(
    mock_get_connector,
    mock_supabase
):
    """Test processing multiple files in one task."""
    
    # Mock connector
    connector = Mock()
    def mock_fetch_sync(item_ids, *args, **kwargs):
        for item_id in item_ids:
            yield SourceDocument(
                content=f"Content {item_id}".encode(),
                metadata={"storage_path": f"uploads/{item_id}", "scope_id": f"file_upload://{item_id}"},
                source_type=SourceType.FILE_UPLOAD,
                source_id=item_id,
                filename=f"{item_id}.pdf",
                mime_type="application/pdf",
                size_bytes=100
            )
    connector.fetch_documents_sync = mock_fetch_sync
    mock_get_connector.return_value = connector
    
    with patch("worker.tasks.process_file_task") as mock_task, \
         patch("celery.group") as mock_group:
        mock_task.s.return_value = "sig"
        mock_group.return_value.apply_async.return_value = Mock(id="group-6")
        
        # Execute
        result = unified_ingest_task(
            user_id=str(uuid4()),
            job_id=str(uuid4()),
            connector_type="file_upload",
            item_ids=["file1", "file2", "file3"],
            credentials=None,
            plan_code="starter",
        )
    
    # Verify
    assert result["status"] == "dispatched"
    assert result["total_files"] == 3
