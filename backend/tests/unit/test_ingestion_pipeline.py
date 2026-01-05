"""
Unit tests for unified ingestion pipeline.

Tests cover:
- IngestionPipeline.process_stream()
- Quota validation
- File size validation
- Error handling
- Progress tracking
- Notification creation
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4

from services.ingestion_pipeline import IngestionPipeline, MAX_FILE_SIZE
from connectors.enhanced import SourceDocument, SourceType, QuotaExceededError, FileTooLargeError


@pytest.mark.asyncio
async def test_process_single_document_success(
    ingestion_pipeline,
    sample_source_document,
    mock_document_processor,
    mock_embeddings,
    mock_quota_check
):
    """Test successful processing of a single document."""
    
    async def mock_stream():
        yield sample_source_document
    
    result = await ingestion_pipeline.process_stream(mock_stream(), "file_upload")
    
    assert result["status"] == "completed"
    assert result["total"] == 1
    assert result["processed"] == 1
    assert result["failed"] == 0
    assert result["chunks"] == 3  # From mock_document_processor


@pytest.mark.asyncio
async def test_process_multiple_documents(
    ingestion_pipeline,
    sample_source_document,
    sample_text_document,
    mock_document_processor,
    mock_embeddings,
    mock_quota_check
):
    """Test processing multiple documents in a stream."""
    
    async def mock_stream():
        yield sample_source_document
        yield sample_text_document
    
    result = await ingestion_pipeline.process_stream(mock_stream(), "file_upload")
    
    assert result["status"] == "completed"
    assert result["total"] == 2
    assert result["processed"] == 2
    assert result["failed"] == 0
    assert result["chunks"] == 6  # 3 chunks per document


@pytest.mark.asyncio
async def test_quota_exceeded(
    ingestion_pipeline,
    sample_source_document,
    mock_quota_exceeded
):
    """Test that quota exceeded errors are handled correctly."""
    
    async def mock_stream():
        yield sample_source_document
    
    result = await ingestion_pipeline.process_stream(mock_stream(), "file_upload")
    
    assert result["status"] in ["completed", "partial"]
    assert result["failed"] >= 1


@pytest.mark.asyncio
async def test_file_too_large(
    ingestion_pipeline,
    mock_quota_check,
    mock_document_processor,
    mock_embeddings
):
    """Test that oversized files are rejected."""
    
    large_doc = SourceDocument(
        content=b"x" * (MAX_FILE_SIZE + 1),
        metadata={},
        source_type=SourceType.FILE_UPLOAD,
        source_id="large-file",
        filename="large.pdf",
        mime_type="application/pdf",
        size_bytes=MAX_FILE_SIZE + 1
    )
    
    async def mock_stream():
        yield large_doc
    
    result = await ingestion_pipeline.process_stream(mock_stream(), "file_upload")
    
    assert result["failed"] == 1
    assert result["processed"] == 0


@pytest.mark.asyncio
async def test_empty_document_stream(ingestion_pipeline):
    """Test handling of empty document stream."""
    
    async def mock_stream():
        return
        yield  # Never reached
    
    result = await ingestion_pipeline.process_stream(mock_stream(), "file_upload")
    
    assert result["status"] == "completed"
    assert result["total"] == 0
    assert result["processed"] == 0


@pytest.mark.asyncio
async def test_document_with_no_content(
    ingestion_pipeline,
    mock_quota_check
):
    """Test handling of documents that produce no chunks."""
    
    empty_doc = SourceDocument(
        content=b"",
        metadata={},
        source_type=SourceType.FILE_UPLOAD,
        source_id="empty",
        filename="empty.txt",
        mime_type="text/plain",
        size_bytes=0
    )
    
    # Mock processor to return no chunks
    with patch('services.ingestion_pipeline.DocumentProcessorFactory') as mock:
        mock.process.return_value.chunks = []
        
        async def mock_stream():
            yield empty_doc
        
        result = await ingestion_pipeline.process_stream(mock_stream(), "file_upload")
        
        assert result["total"] == 1
        assert result["chunks"] == 0


@pytest.mark.asyncio
async def test_progress_tracking(
    ingestion_pipeline,
    sample_source_document,
    mock_document_processor,
    mock_embeddings,
    mock_quota_check
):
    """Test that progress is tracked correctly."""
    
    async def mock_stream():
        yield sample_source_document
    
    # Track update_job_status calls
    job_updates = []
    original_update = ingestion_pipeline._update_job_status
    
    def track_update(status, progress, message=""):
        job_updates.append({"status": status, "progress": progress})
        original_update(status, progress, message)
    
    ingestion_pipeline._update_job_status = track_update
    
    await ingestion_pipeline.process_stream(mock_stream(), "file_upload")
    
    # Should have multiple progress updates
    assert len(job_updates) >= 2
    assert job_updates[-1]["progress"] == 100
    assert job_updates[-1]["status"] in ["completed", "partial"]


@pytest.mark.asyncio
async def test_notification_creation(
    ingestion_pipeline,
    sample_source_document,
    mock_document_processor,
    mock_embeddings,
    mock_quota_check
):
    """Test that notifications are created."""
    
    notifications = []
    
    def track_notification(title, message, type):
        notifications.append({"title": title, "type": type})
    
    ingestion_pipeline._create_notification = track_notification
    
    async def mock_stream():
        yield sample_source_document
    
    await ingestion_pipeline.process_stream(mock_stream(), "file_upload")
    
    # Should have start and completion notifications
    assert len(notifications) >= 2
    assert any("Started" in n["title"] for n in notifications)
    assert any("Complete" in n["title"] for n in notifications)


@pytest.mark.asyncio
async def test_partial_failure(
    ingestion_pipeline,
    sample_source_document,
    sample_text_document,
    mock_document_processor,
    mock_embeddings,
    mock_quota_check
):
    """Test handling when some documents fail."""
    
    # Make second document fail
    call_count = [0]
    
    async def failing_stream():
        yield sample_source_document  # Success
        call_count[0] += 1
        if call_count[0] > 1:
            raise Exception("Simulated failure")
        yield sample_text_document  # Will fail
    
    # Patch process_single_document to fail on second call
    original_process = ingestion_pipeline._process_single_document
    call_num = [0]
    
    async def failing_process(doc, num):
        call_num[0] += 1
        if call_num[0] == 2:
            raise Exception("Processing failed")
        return await original_process(doc, num)
    
    ingestion_pipeline._process_single_document = failing_process
    
    async def mock_stream():
        yield sample_source_document
        yield sample_text_document
    
    result = await ingestion_pipeline.process_stream(mock_stream(), "file_upload")
    
    assert result["status"] == "partial"
    assert result["processed"] == 1
    assert result["failed"] == 1


def test_pipeline_initialization(mock_supabase):
    """Test IngestionPipeline initialization."""
    user_id = str(uuid4())
    job_id = str(uuid4())
    
    pipeline = IngestionPipeline(
        user_id=user_id,
        job_id=job_id,
        supabase_client=mock_supabase
    )
    
    assert pipeline.user_id == user_id
    assert pipeline.job_id == job_id
    assert pipeline.total_docs == 0
    assert pipeline.processed_docs == 0
    assert pipeline.failed_docs == 0
    assert pipeline.total_chunks == 0
