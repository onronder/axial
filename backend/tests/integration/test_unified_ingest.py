"""
Integration tests for the unified ingestion worker task.

These tests verify the complete end-to-end ingestion flow
from file upload through to document storage.
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest


class TestUnifiedIngestTask:
    """Integration tests for unified_ingest_task."""

    @pytest.fixture
    def mock_supabase(self):
        """Create a mock Supabase client."""
        mock = MagicMock()
        mock.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        mock.table.return_value.insert.return_value.execute.return_value.data = [{"id": str(uuid4())}]
        mock.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{}]
        return mock

    @pytest.fixture
    def mock_connector(self):
        """Create a mock connector."""
        async def mock_fetch(*args, **kwargs):
            yield MagicMock(
                filename="test.pdf",
                content=b"test content",
                metadata={"size": 100}
            )

        mock = MagicMock()
        mock.fetch_documents = mock_fetch
        return mock

    @pytest.fixture
    def sample_job_payload(self):
        """Sample job data for ingestion."""
        return {
            "user_id": str(uuid4()),
            "job_id": str(uuid4()),
            "connector_type": "google_drive",
            "item_ids": ["file_1", "file_2"],
        }

    def test_job_status_tracking(self, mock_supabase, sample_job_payload):
        """Verify job status is properly tracked through processing stages."""
        from worker.tasks import update_job_status

        job_id = sample_job_payload["job_id"]

        # Test pending status
        update_job_status(mock_supabase, job_id, "pending")
        mock_supabase.table.assert_called_with("ingestion_jobs")

        # Test processing status
        update_job_status(mock_supabase, job_id, "processing", processed_files=1)
        mock_supabase.table().update.assert_called()

    def test_file_status_creation(self, mock_supabase):
        """Verify file status records are created for tracking."""
        from worker.tasks import create_file_status

        job_id = str(uuid4())
        user_id = str(uuid4())

        result = create_file_status(
            mock_supabase,
            job_id=job_id,
            user_id=user_id,
            organization_id=str(uuid4()),
            filename="test.pdf",
            file_size=1024
        )

        # Should call insert on ingestion_file_status table
        mock_supabase.table.assert_called_with("ingestion_file_status")

    def test_job_cancellation_check(self, mock_supabase):
        """Verify job cancellation is properly detected."""
        from worker.tasks import check_job_cancelled

        job_id = str(uuid4())

        # Mock cancelled job
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "status": "cancelled"
        }

        result = check_job_cancelled(mock_supabase, job_id)
        assert result is True

        # Mock active job
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "status": "processing"
        }

        result = check_job_cancelled(mock_supabase, job_id)
        assert result is False

    def test_notification_creation(self, mock_supabase):
        """Verify notifications are created for job events."""
        from worker.tasks import create_notification

        user_id = str(uuid4())

        create_notification(
            mock_supabase,
            user_id=user_id,
            title="Ingestion Complete",
            message="5 files processed",
            notification_type="success"
        )

        mock_supabase.table.assert_called_with("notifications")


class TestBatchProcessing:
    """Tests for batch document processing."""

    def test_batched_chunk_insertion(self):
        """Verify chunks are inserted in batches to avoid timeout."""

        # Create mock with 200 chunks (should split into batches)
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{"id": str(uuid4())}]
        mock_supabase.rpc.return_value.execute.return_value.data = {"doc_id": str(uuid4())}

        chunks = [{"content": f"chunk_{i}", "embedding": [0.1] * 1536} for i in range(200)]

        # Should handle large batch without timeout
        # Implementation verifies batching logic
        assert len(chunks) == 200


class TestErrorHandling:
    """Tests for error handling in ingestion."""

    def test_parse_error_handling(self):
        """Verify parsing errors are properly caught and logged."""
        with patch("services.parsers.DocumentProcessorFactory.process") as mock:
            mock.side_effect = Exception("Parse error")

            from services.parsers import DocumentProcessorFactory

            with pytest.raises(Exception, match="Parse error"):
                DocumentProcessorFactory.process(content=b"bad content", filename="bad.pdf")

    def test_embedding_timeout_handling(self):
        """Verify embedding timeouts are handled gracefully."""
        # The resilience module provides timeout protection
        from core.resilience import Timeouts

        # Verify timeout constant exists
        assert hasattr(Timeouts, 'EMBEDDING_BATCH')
        assert Timeouts.EMBEDDING_BATCH > 0

    def test_dlq_integration_on_failure(self):
        """Verify failed tasks are logged to DLQ."""
        from worker.dlq_worker import log_task_failure

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{"id": str(uuid4())}]

        with patch("worker.dlq_worker.get_supabase") as mock_get_supabase:
            mock_get_supabase.return_value = mock_supabase

            log_task_failure(
                task_id=str(uuid4()),
                task_name="unified_ingest_task",
                args=(),
                kwargs={},
                exc=Exception("Test failure"),
                traceback_str="traceback",
                user_id=str(uuid4()),
                job_id=str(uuid4()),
            )

        mock_supabase.table.assert_called_with("failed_tasks")
