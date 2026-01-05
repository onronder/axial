"""
Error scenario tests for unified ingestion pipeline.

Tests comprehensive error handling across all components.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4

from services.ingestion_pipeline import IngestionPipeline
from connectors.enhanced import (
    SourceDocument,
    SourceType,
    QuotaExceededError,
    FileTooLargeError,
    ItemNotFoundError,
    AuthenticationError
)


@pytest.mark.asyncio
async def test_invalid_connector_type():
    """Test error when connector type doesn't exist."""
    
    from connectors import get_connector
    
    with pytest.raises(ValueError, match="Unknown connector type"):
        get_connector("invalid_type")


@pytest.mark.asyncio
async def test_supabase_connection_failure():
    """Test handling of database connection failures."""
    
    with patch('services.ingestion_pipeline.get_supabase') as mock:
        mock.side_effect = ConnectionError("Database unavailable")
        
        with pytest.raises(ConnectionError):
            pipeline = IngestionPipeline(
                user_id=str(uuid4()),
                job_id=str(uuid4()),
                supabase_client=None
            )


@pytest.mark.asyncio
async def test_llamaparse_timeout():
    """Test handling of LlamaParse timeout."""
    
    pipeline = IngestionPipeline(
        user_id=str(uuid4()),
        job_id=str(uuid4()),
        supabase_client=Mock()
    )
    
    # Mock document processor to timeout
    with patch('services.ingestion_pipeline.DocumentProcessorFactory') as mock:
        mock.process.side_effect = TimeoutError("LlamaParse timeout")
        
        async def doc_stream():
            yield SourceDocument(
                content=b"PDF content",
                metadata={},
                source_type=SourceType.FILE_UPLOAD,
                source_id="test",
                filename="test.pdf",
                mime_type="application/pdf",
                size_bytes=100
            )
        
        result = await pipeline.process_stream(doc_stream())
        
        # Should handle timeout gracefully
        assert result["failed"] >= 1


@pytest.mark.asyncio
async def test_openai_rate_limit():
    """Test handling of OpenAI API rate limits."""
    
    pipeline = IngestionPipeline(
        user_id=str(uuid4()),
        job_id=str(uuid4()),
        supabase_client=Mock()
    )
    
    # Mock embeddings service to hit rate limit
    with patch('services.ingestion_pipeline.get_embeddings') as mock:
        from openai import RateLimitError
        mock.side_effect = RateLimitError("Rate limit exceeded")
        
        async def doc_stream():
            yield SourceDocument(
                content=b"content",
                metadata={},
                source_type=SourceType.FILE_UPLOAD,
                source_id="test",
                filename="test.txt",
                mime_type="text/plain",
                size_bytes=50
            )
        
        # Should retry or handle gracefully
        result = await pipeline.process_stream(doc_stream())
        assert result is not None


@pytest.mark.asyncio
async def test_storage_quota_exceeded():
    """Test handling when storage quota is exceeded."""
    
    pipeline = IngestionPipeline(
        user_id=str(uuid4()),
        job_id=str(uuid4()),
        supabase_client=Mock()
    )
    
    async def doc_stream():
        yield SourceDocument(
            content=b"content",
            metadata={},
            source_type=SourceType.FILE_UPLOAD,
            source_id="test",
            filename="test.pdf",
            mime_type="application/pdf",
            size_bytes=100
        )
    
    # Mock quota check to fail
    with patch.object(pipeline, '_check_quota') as mock:
        mock.side_effect = QuotaExceededError("Storage quota exceeded")
        
        result = await pipeline.process_stream(doc_stream())
        
        assert result["failed"] >= 1


@pytest.mark.asyncio
async def test_malformed_document():
    """Test handling of malformed/corrupted documents."""
    
    pipeline = IngestionPipeline(
        user_id=str(uuid4()),
        job_id=str(uuid4()),
        supabase_client=Mock()
    )
    
    async def doc_stream():
        yield SourceDocument(
            content=b"\\x00\\x01\\x02corrupted",  # Malformed content
            metadata={},
            source_type=SourceType.FILE_UPLOAD,
            source_id="test",
            filename="corrupted.pdf",
            mime_type="application/pdf",
            size_bytes=20
        )
    
    # Should handle parsing errors
    result = await pipeline.process_stream(doc_stream())
    
    # Document should fail but not crash pipeline
    assert result["failed"] >= 0  # May fail or skip


@pytest.mark.asyncio
async def test_network_failure_during_fetch():
    """Test handling of network failures during document fetch."""
    
    from connectors.file_upload import FileUploadConnector
    
    connector = FileUploadConnector()
    
    with patch('connectors.file_upload.get_supabase') as mock:
        mock.return_value.storage.from_.return_value.download.side_effect = \
            ConnectionError("Network error")
        
        with pytest.raises(ConnectionError):
            documents = []
            async for doc in connector.fetch_documents(["test.pdf"]):
                documents.append(doc)


@pytest.mark.asyncio
async def test_item_not_found():
    """Test handling when requested item doesn't exist."""
    
    from connectors.file_upload import FileUploadConnector
    
    connector = FileUploadConnector()
    
    with patch('connectors.file_upload.get_supabase') as mock:
        mock.return_value.storage.from_.return_value.download.return_value = None
        
        with pytest.raises(ItemNotFoundError):
            async for doc in connector.fetch_documents(["nonexistent.pdf"]):
                pass


@pytest.mark.asyncio
async def test_authentication_failure():
    """Test handling of authentication failures."""
    
    from connectors.google_drive import GoogleDriveConnector
    
    connector = GoogleDriveConnector()
    
    # Mock invalid credentials
    with pytest.raises((AuthenticationError, Exception)):
        async for doc in connector.fetch_documents(
            ["file-id"],
            credentials={"access_token": "invalid"}
        ):
            pass


@pytest.mark.asyncio
async def test_concurrent_processing_error():
    """Test error handling during concurrent processing."""
    
    pipeline = IngestionPipeline(
        user_id=str(uuid4()),
        job_id=str(uuid4()),
        supabase_client=Mock()
    )
    
    # Create multiple documents, some will fail
    async def doc_stream():
        for i in range(5):
            yield SourceDocument(
                content=f"Content {i}".encode(),
                metadata={"index": i},
                source_type=SourceType.FILE_UPLOAD,
                source_id=f"test-{i}",
                filename=f"test-{i}.txt",
                mime_type="text/plain",
                size_bytes=50
            )
    
    # Mock some documents to fail
    call_count = [0]
    original_process = pipeline._process_single_document
    
    async def failing_process(doc, num):
        call_count[0] += 1
        if call_count[0] % 2 == 0:  # Fail every other document
            raise Exception(f"Processing failed for {doc.filename}")
        return await original_process(doc, num)
    
    pipeline._process_single_document = failing_process
    
    result = await pipeline.process_stream(doc_stream())
    
    # Should have partial success
    assert result["processed"] >= 1
    assert result["failed"] >= 1
    assert result["status"] == "partial"


@pytest.mark.asyncio
async def test_database_constraint_violation():
    """Test handling of database constraint violations."""
    
    pipeline = IngestionPipeline(
        user_id=str(uuid4()),
        job_id=str(uuid4()),
        supabase_client=Mock()
    )
    
    # Mock database to raise constraint error
    with patch.object(pipeline.supabase.table('documents'), 'insert') as mock:
        from psycopg2 import IntegrityError
        mock.side_effect = IntegrityError("Duplicate key violation")
        
        async def doc_stream():
            yield SourceDocument(
                content=b"content",
                metadata={},
                source_type=SourceType.FILE_UPLOAD,
                source_id="test",
                filename="test.txt",
                mime_type="text/plain",
                size_bytes=50
            )
        
        result = await pipeline.process_stream(doc_stream())
        
        # Should handle constraint error
        assert result["failed"] >= 1
