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
import os
from types import SimpleNamespace
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4

from services.ingestion_pipeline import IngestionPipeline, MAX_FILE_SIZE, _sanitize_text, get_embeddings
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
    
    assert result["status"] == "failed"
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
    assert job_updates[-1]["status"] == "completed"


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
    
    assert result["status"] == "completed"
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


def test_sanitize_text_handles_nulls():
    assert _sanitize_text(None) is None
    assert _sanitize_text("") == ""
    assert _sanitize_text("a\x00b") == "ab"
    assert _sanitize_text("clean") == "clean"


@pytest.mark.asyncio
async def test_get_embeddings_delegates():
    with patch("services.ingestion_pipeline.generate_embeddings_batch", new=AsyncMock(return_value=[[0.1]])) as gen:
        result = await get_embeddings(["hi"], token_counts=[1])

    assert result == [[0.1]]
    gen.assert_awaited_once_with(["hi"], token_counts=[1])


@pytest.mark.asyncio
async def test_process_stream_fetch_error(ingestion_pipeline):
    async def failing_stream():
        raise RuntimeError("fetch failed")
        yield

    ingestion_pipeline._update_job_status = Mock()
    ingestion_pipeline._create_notification = Mock()

    with pytest.raises(RuntimeError, match="fetch failed"):
        await ingestion_pipeline.process_stream(failing_stream(), "file_upload")

    assert ingestion_pipeline._update_job_status.call_args_list[-1].args[0] == "failed"


@pytest.mark.asyncio
async def test_process_single_document_skips_unsupported_binary(mock_supabase, sample_source_document):
    pipeline = IngestionPipeline(
        user_id=str(uuid4()),
        job_id=str(uuid4()),
        supabase_client=mock_supabase
    )
    pipeline._create_file_status = Mock(return_value="file-status-id")
    pipeline._update_file_status = Mock()
    pipeline._update_chunk_progress = Mock()
    pipeline._validate_document = AsyncMock()
    pipeline._write_to_temp = Mock(return_value="/tmp/file")
    pipeline._parse_and_chunk = AsyncMock(return_value=SimpleNamespace(
        file_type="unsupported",
        metadata={"unsupported_reason": "binary_content"},
        chunks=[]
    ))

    with patch("services.ingestion_pipeline.os.path.exists", return_value=False):
        result = await pipeline._process_single_document(sample_source_document, 1)

    assert result["status"] == "skipped"
    assert result["reason"] == "binary_content"
    assert any(
        call.args[1] == "skipped" for call in pipeline._update_file_status.call_args_list
    )


@pytest.mark.asyncio
async def test_process_single_document_skips_empty_chunks(mock_supabase, sample_source_document):
    pipeline = IngestionPipeline(
        user_id=str(uuid4()),
        job_id=str(uuid4()),
        supabase_client=mock_supabase
    )
    pipeline._create_file_status = Mock(return_value="file-status-id")
    pipeline._update_file_status = Mock()
    pipeline._update_chunk_progress = Mock()
    pipeline._validate_document = AsyncMock()
    pipeline._write_to_temp = Mock(return_value="/tmp/file")
    pipeline._parse_and_chunk = AsyncMock(return_value=SimpleNamespace(
        file_type="txt",
        metadata={},
        chunks=[]
    ))

    with patch("services.ingestion_pipeline.os.path.exists", return_value=False):
        result = await pipeline._process_single_document(sample_source_document, 1)

    assert result["status"] == "skipped"
    assert result["reason"] == "empty"


@pytest.mark.asyncio
async def test_process_single_document_cleanup_warns_on_unlink_error(mock_supabase, sample_source_document):
    pipeline = IngestionPipeline(
        user_id=str(uuid4()),
        job_id=str(uuid4()),
        supabase_client=mock_supabase
    )
    pipeline._create_file_status = Mock(return_value="file-status-id")
    pipeline._update_file_status = Mock()
    pipeline._validate_document = AsyncMock()
    pipeline._write_to_temp = Mock(return_value="/tmp/file")
    pipeline._parse_and_chunk = AsyncMock(side_effect=RuntimeError("parse failed"))

    with patch("services.ingestion_pipeline.os.path.exists", return_value=True), \
         patch("services.ingestion_pipeline.os.unlink", side_effect=OSError("nope")):
        with pytest.raises(RuntimeError, match="parse failed"):
            await pipeline._process_single_document(sample_source_document, 1)


@pytest.mark.asyncio
async def test_validate_document_file_too_large(mock_supabase):
    pipeline = IngestionPipeline(
        user_id=str(uuid4()),
        job_id=str(uuid4()),
        supabase_client=mock_supabase
    )
    large_doc = SourceDocument(
        content=b"x" * (MAX_FILE_SIZE + 1),
        metadata={},
        source_type=SourceType.FILE_UPLOAD,
        source_id="large",
        filename="large.pdf",
        mime_type="application/pdf",
        size_bytes=MAX_FILE_SIZE + 1
    )

    with pytest.raises(FileTooLargeError):
        await pipeline._validate_document(large_doc)


@pytest.mark.asyncio
async def test_validate_document_quota_exceeded(mock_supabase, sample_source_document):
    pipeline = IngestionPipeline(
        user_id=str(uuid4()),
        job_id=str(uuid4()),
        supabase_client=mock_supabase
    )
    pipeline._check_quota = AsyncMock(return_value={"allowed": False, "reason": "quota"})

    with pytest.raises(QuotaExceededError):
        await pipeline._validate_document(sample_source_document)


@pytest.mark.asyncio
async def test_check_quota_delegates_to_usage(mock_supabase, sample_source_document, monkeypatch):
    pipeline = IngestionPipeline(
        user_id=str(uuid4()),
        job_id=str(uuid4()),
        supabase_client=mock_supabase
    )
    called = {}

    async def fake_check_can_upload(user_id, size_bytes, file_count=1):
        called["args"] = (user_id, size_bytes, file_count)
        return {"allowed": True, "reason": ""}

    monkeypatch.setattr("services.ingestion_pipeline.check_can_upload", fake_check_can_upload)
    result = await pipeline._check_quota(sample_source_document)

    assert result["allowed"] is True
    assert called["args"][1] == sample_source_document.size_bytes


def test_write_to_temp_handles_string_content(mock_supabase, tmp_path):
    pipeline = IngestionPipeline(
        user_id=str(uuid4()),
        job_id=str(uuid4()),
        supabase_client=mock_supabase
    )
    doc = SourceDocument(
        content="text content",
        metadata={},
        source_type=SourceType.FILE_UPLOAD,
        source_id="text-1",
        filename="note.txt",
        mime_type="text/plain",
        size_bytes=12
    )

    path = pipeline._write_to_temp(doc)
    try:
        with open(path, "rb") as handle:
            assert handle.read() == b"text content"
    finally:
        if path and os.path.exists(path):
            os.unlink(path)


@pytest.mark.asyncio
async def test_generate_embeddings_sanitizes_and_delegates(mock_supabase):
    pipeline = IngestionPipeline(
        user_id=str(uuid4()),
        job_id=str(uuid4()),
        supabase_client=mock_supabase
    )
    chunks = [
        SimpleNamespace(content="a\x00b", token_count=1, metadata={}),
        SimpleNamespace(content="c", token_count=2, metadata={}),
    ]

    async def fake_with_timeout(awaitable, _timeout, _label):
        return await awaitable

    with patch("services.ingestion_pipeline.get_embeddings", new=AsyncMock(return_value=[[0.1], [0.2]])) as get_emb, \
         patch("core.resilience.with_timeout", new=fake_with_timeout):
        embeddings, texts = await pipeline._generate_embeddings(chunks)

    assert embeddings == [[0.1], [0.2]]
    assert texts == ["ab", "c"]
    get_emb.assert_awaited_once_with(["ab", "c"], token_counts=[1, 2])


@pytest.mark.asyncio
async def test_store_document_raises_when_insert_fails(mock_supabase, sample_source_document):
    pipeline = IngestionPipeline(
        user_id=str(uuid4()),
        job_id=str(uuid4()),
        supabase_client=mock_supabase
    )
    chunks = [SimpleNamespace(content="chunk", token_count=1, metadata={"foo": "bar"})]
    embeddings = [None]
    texts = ["chunk"]

    with patch("worker.tasks.ingest_document_batched", return_value=None):
        with pytest.raises(Exception, match="Failed to store document"):
            await pipeline._store_document(sample_source_document, chunks, embeddings, texts)


def test_update_job_status_and_total_handle_errors(mock_supabase):
    pipeline = IngestionPipeline(
        user_id=str(uuid4()),
        job_id=str(uuid4()),
        supabase_client=mock_supabase
    )
    table = Mock()
    table.update.return_value = table
    table.eq.return_value = table
    table.execute.side_effect = RuntimeError("db down")
    mock_supabase.table.return_value = table

    pipeline._update_job_status("processing", 10, "msg")
    pipeline._update_job_total(5)


def test_create_file_status_handles_error(mock_supabase, sample_source_document):
    pipeline = IngestionPipeline(
        user_id=str(uuid4()),
        job_id=str(uuid4()),
        supabase_client=mock_supabase
    )
    table = Mock()
    table.insert.return_value = table
    table.execute.side_effect = RuntimeError("db down")
    mock_supabase.table.return_value = table

    assert pipeline._create_file_status(sample_source_document) == ""


def test_update_file_status_no_file_id_noop(mock_supabase):
    pipeline = IngestionPipeline(
        user_id=str(uuid4()),
        job_id=str(uuid4()),
        supabase_client=mock_supabase
    )
    pipeline._update_file_status("", "processing", 10, "msg")


def test_update_file_status_handles_error(mock_supabase):
    pipeline = IngestionPipeline(
        user_id=str(uuid4()),
        job_id=str(uuid4()),
        supabase_client=mock_supabase
    )
    table = Mock()
    table.update.return_value = table
    table.eq.return_value = table
    table.execute.side_effect = RuntimeError("db down")
    mock_supabase.table.return_value = table

    pipeline._update_file_status("file-1", "processing", 10, "msg")


def test_update_chunk_progress_handles_errors(mock_supabase):
    pipeline = IngestionPipeline(
        user_id=str(uuid4()),
        job_id=str(uuid4()),
        supabase_client=mock_supabase
    )
    table = Mock()
    table.update.return_value = table
    table.eq.return_value = table
    table.execute.side_effect = RuntimeError("db down")
    mock_supabase.table.return_value = table

    pipeline._update_chunk_progress("file-1", 1, 2, current_stage="embedding")


def test_update_chunk_progress_no_file_id_noop(mock_supabase):
    pipeline = IngestionPipeline(
        user_id=str(uuid4()),
        job_id=str(uuid4()),
        supabase_client=mock_supabase
    )
    pipeline._update_chunk_progress("", 1, 2, current_stage="embedding")


def test_create_notification_handles_error(mock_supabase):
    pipeline = IngestionPipeline(
        user_id=str(uuid4()),
        job_id=str(uuid4()),
        supabase_client=mock_supabase
    )
    table = Mock()
    table.insert.return_value = table
    table.execute.side_effect = RuntimeError("db down")
    mock_supabase.table.return_value = table

    pipeline._create_notification("Title", "Message", "info")


@pytest.mark.asyncio
async def test_store_document_success_with_string_content(mock_supabase):
    pipeline = IngestionPipeline(
        user_id=str(uuid4()),
        job_id=str(uuid4()),
        supabase_client=mock_supabase
    )
    doc = SourceDocument(
        content="text content",
        metadata={"source_url": "https://example.com"},
        source_type=SourceType.FILE_UPLOAD,
        source_id="text-1",
        filename="note.txt",
        mime_type="text/plain",
        size_bytes=12
    )
    chunks = [SimpleNamespace(content="chunk", token_count=1, metadata={"foo": "bar"})]
    embeddings = [[0.1, 0.2]]
    texts = ["chunk"]

    with patch("worker.tasks.ingest_document_batched", return_value="doc-1") as ingest:
        result = await pipeline._store_document(doc, chunks, embeddings, texts)

    assert result == "doc-1"
    assert ingest.call_args.kwargs["chunks_payload"][0]["content"] == "chunk"


def test_update_file_status_success(mock_supabase):
    pipeline = IngestionPipeline(
        user_id=str(uuid4()),
        job_id=str(uuid4()),
        supabase_client=mock_supabase
    )
    table = Mock()
    table.update.return_value = table
    table.eq.return_value = table
    table.execute.return_value = Mock(data=[{"id": "file-1"}])
    mock_supabase.table.return_value = table

    pipeline._update_file_status("file-1", "processing", 10, "msg", chunks_total=1)
    table.update.assert_called_once()


def test_update_chunk_progress_success(mock_supabase):
    pipeline = IngestionPipeline(
        user_id=str(uuid4()),
        job_id=str(uuid4()),
        supabase_client=mock_supabase
    )
    table = Mock()
    table.update.return_value = table
    table.eq.return_value = table
    table.execute.return_value = Mock(data=[{"id": "file-1"}])
    mock_supabase.table.return_value = table

    pipeline._update_chunk_progress("file-1", 1, 2, current_stage="indexing")
    table.update.assert_called_once()
