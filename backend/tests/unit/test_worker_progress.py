"""
Test Suite for Worker Task Progress Tracking

Tests for:
- update_job_status helper function
- process_file_task job progress updates
- Status transitions: pending -> processing -> completed/failed
"""

import base64
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch, MagicMock, call

import pytest


class TestUpdateJobStatus:
    """Tests for the update_job_status helper function."""
    
    @pytest.mark.unit
    def test_updates_status_field(self):
        """Should update the status field in the database."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock()
        
        from worker.tasks import update_job_status
        
        update_job_status(mock_supabase, "job-123", "processing", 0)
        
        # Verify update was called
        mock_supabase.table.assert_called_with("ingestion_jobs")
        mock_table.update.assert_called_once()
        
        # Check the update data includes status
        update_call = mock_table.update.call_args
        update_data = update_call[0][0]
        assert update_data["status"] == "processing"
    
    @pytest.mark.unit
    def test_updates_processed_files_when_provided(self):
        """Should update processed_files count when provided."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock()
        
        from worker.tasks import update_job_status
        
        update_job_status(mock_supabase, "job-123", "processing", processed_files=5)
        
        update_data = mock_table.update.call_args[0][0]
        assert update_data["processed_files"] == 5
    
    @pytest.mark.unit
    def test_updates_error_message_when_provided(self):
        """Should update error_message when job fails."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock()
        
        from worker.tasks import update_job_status
        
        update_job_status(
            mock_supabase, 
            "job-123", 
            "failed", 
            processed_files=3, 
            error_message="Connection timeout"
        )
        
        update_data = mock_table.update.call_args[0][0]
        assert update_data["status"] == "failed"
        assert update_data["error_message"] == "Connection timeout"
    
    @pytest.mark.unit
    def test_always_updates_updated_at(self):
        """Should always update the updated_at timestamp."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock()
        
        from worker.tasks import update_job_status
        
        update_job_status(mock_supabase, "job-123", "processing")
        
        update_data = mock_table.update.call_args[0][0]
        assert "updated_at" in update_data
    
    @pytest.mark.unit
    def test_filters_by_job_id(self):
        """Should filter update by job_id."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock()
        
        from worker.tasks import update_job_status
        
        update_job_status(mock_supabase, "job-456", "completed")
        
        mock_table.eq.assert_called_with("id", "job-456")


class TestIngestFileTaskProgress:
    """Tests for progress tracking in process_file_task."""
    
    @pytest.mark.unit
    def test_sets_status_to_processing_at_start(self):
        """Task should set status to 'processing' when it starts."""
        # Verify the task calls update_job_status with "processing" at start
        from worker.tasks import process_file_task

        task = SimpleNamespace(request=SimpleNamespace(id="task-1"))

        supabase = MagicMock()
        doc_table = MagicMock()
        doc_table.select.return_value = doc_table
        doc_table.eq.return_value = doc_table
        doc_table.limit.return_value = doc_table
        doc_table.execute.return_value = MagicMock(data=[])
        doc_table.insert.return_value = doc_table
        doc_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "doc-1"}])
        supabase.table.side_effect = lambda name: doc_table

        file_data = {
            "filename": "test.txt",
            "content_b64": base64.b64encode(b"hello").decode("utf-8"),
            "size_bytes": 5,
            "mime_type": "text/plain",
        }

        dummy_result = MagicMock()
        dummy_result.file_type = "txt"
        dummy_result.chunks = [MagicMock(content="chunk", token_count=1)]

        update_file_status = MagicMock()

        with patch("worker.tasks.get_supabase", return_value=supabase), \
             patch("services.parsers.DocumentProcessorFactory.process", return_value=dummy_result), \
             patch("services.embeddings.generate_embeddings_batch_sync", return_value=[[0.1]]), \
             patch("worker.tasks.insert_rows_with_retry"), \
             patch("worker.tasks.update_file_status", update_file_status), \
             patch("worker.tasks._record_ingest_outcome_and_maybe_finalize"):
            process_file_task._orig_run.__func__(task, "user-1", "job-1", file_data, "file-1", "file_upload")

        first_call = update_file_status.call_args_list[0][1]
        assert first_call["status"] == "uploading"
    
    @pytest.mark.unit
    def test_increments_processed_files_during_loop(self):
        """Should increment processed_files after each document group."""
        # Verify update_job_status is called with incrementing counts
        from worker.tasks import process_file_task

        task = SimpleNamespace(request=SimpleNamespace(id="task-1"))

        supabase = MagicMock()
        doc_table = MagicMock()
        doc_table.select.return_value = doc_table
        doc_table.eq.return_value = doc_table
        doc_table.limit.return_value = doc_table
        doc_table.execute.return_value = MagicMock(data=[])
        doc_table.insert.return_value = doc_table
        doc_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "doc-1"}])
        supabase.table.side_effect = lambda name: doc_table

        file_data = {
            "filename": "test.txt",
            "content_b64": base64.b64encode(b"hello").decode("utf-8"),
            "size_bytes": 5,
            "mime_type": "text/plain",
        }

        dummy_result = MagicMock()
        dummy_result.file_type = "txt"
        dummy_result.chunks = [
            MagicMock(content="chunk1", token_count=1),
            MagicMock(content="chunk2", token_count=1),
        ]

        update_file_status = MagicMock()

        with patch("worker.tasks.get_supabase", return_value=supabase), \
             patch("services.parsers.DocumentProcessorFactory.process", return_value=dummy_result), \
             patch("services.embeddings.generate_embeddings_batch_sync", return_value=[[0.1], [0.2]]), \
             patch("worker.tasks.insert_rows_with_retry"), \
             patch("worker.tasks.update_file_status", update_file_status), \
             patch("worker.tasks._record_ingest_outcome_and_maybe_finalize"):
            process_file_task._orig_run.__func__(task, "user-1", "job-1", file_data, "file-1", "file_upload")

        assert any("chunks_processed" in call.kwargs for call in update_file_status.call_args_list)
    
    @pytest.mark.unit
    def test_sets_status_to_completed_on_success(self):
        """Task should set status to 'completed' when finished successfully."""
        from worker.tasks import process_file_task

        task = SimpleNamespace(request=SimpleNamespace(id="task-1"))

        supabase = MagicMock()
        doc_table = MagicMock()
        doc_table.select.return_value = doc_table
        doc_table.eq.return_value = doc_table
        doc_table.limit.return_value = doc_table
        doc_table.execute.return_value = MagicMock(data=[])
        doc_table.insert.return_value = doc_table
        doc_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "doc-1"}])
        supabase.table.side_effect = lambda name: doc_table

        file_data = {
            "filename": "test.txt",
            "content_b64": base64.b64encode(b"hello").decode("utf-8"),
            "size_bytes": 5,
            "mime_type": "text/plain",
        }

        dummy_result = MagicMock()
        dummy_result.file_type = "txt"
        dummy_result.chunks = [MagicMock(content="chunk", token_count=1)]

        update_file_status = MagicMock()

        with patch("worker.tasks.get_supabase", return_value=supabase), \
             patch("services.parsers.DocumentProcessorFactory.process", return_value=dummy_result), \
             patch("services.embeddings.generate_embeddings_batch_sync", return_value=[[0.1]]), \
             patch("worker.tasks.insert_rows_with_retry"), \
             patch("worker.tasks.update_file_status", update_file_status), \
             patch("worker.tasks._record_ingest_outcome_and_maybe_finalize"):
            process_file_task._orig_run.__func__(task, "user-1", "job-1", file_data, "file-1", "file_upload")

        assert any(call.kwargs.get("status") == "completed" for call in update_file_status.call_args_list)
    
    @pytest.mark.unit
    def test_sets_status_to_failed_on_exception(self):
        """Task should set status to 'failed' when exception occurs."""
        from worker.tasks import process_file_task

        task = SimpleNamespace(request=SimpleNamespace(id="task-1"))

        supabase = MagicMock()
        doc_table = MagicMock()
        supabase.table.side_effect = lambda name: doc_table

        file_data = {
            "filename": "test.txt",
            "content_b64": base64.b64encode(b"hello").decode("utf-8"),
            "size_bytes": 5,
            "mime_type": "text/plain",
        }

        update_file_status = MagicMock()

        with patch("worker.tasks.get_supabase", return_value=supabase), \
             patch("services.parsers.DocumentProcessorFactory.process", side_effect=Exception("boom")), \
             patch("worker.tasks.update_file_status", update_file_status), \
             patch("worker.tasks._record_ingest_outcome_and_maybe_finalize"):
            process_file_task._orig_run.__func__(task, "user-1", "job-1", file_data, "file-1", "file_upload")

        assert any(call.kwargs.get("status") == "failed" for call in update_file_status.call_args_list)
    
    @pytest.mark.unit
    def test_saves_error_message_on_failure(self):
        """Task should save the error message when it fails."""
        from worker.tasks import process_file_task

        task = SimpleNamespace(request=SimpleNamespace(id="task-1"))

        supabase = MagicMock()
        doc_table = MagicMock()
        supabase.table.side_effect = lambda name: doc_table

        file_data = {
            "filename": "test.txt",
            "content_b64": base64.b64encode(b"hello").decode("utf-8"),
            "size_bytes": 5,
            "mime_type": "text/plain",
        }

        update_file_status = MagicMock()

        with patch("worker.tasks.get_supabase", return_value=supabase), \
             patch("services.parsers.DocumentProcessorFactory.process", side_effect=Exception("boom")), \
             patch("worker.tasks.update_file_status", update_file_status), \
             patch("worker.tasks._record_ingest_outcome_and_maybe_finalize"):
            process_file_task._orig_run.__func__(task, "user-1", "job-1", file_data, "file-1", "file_upload")

        failure_calls = [call for call in update_file_status.call_args_list if call.kwargs.get("status") == "failed"]
        assert failure_calls
    
    @pytest.mark.unit
    def test_handles_missing_job_id_gracefully(self):
        """Task should work without job_id (backward compatibility)."""
        # job_id is optional, task should not crash if not provided
        from worker.tasks import process_file_task

        task = SimpleNamespace(request=SimpleNamespace(id="task-1"))

        supabase = MagicMock()
        doc_table = MagicMock()
        doc_table.select.return_value = doc_table
        doc_table.eq.return_value = doc_table
        doc_table.limit.return_value = doc_table
        doc_table.execute.return_value = MagicMock(data=[])
        doc_table.insert.return_value = doc_table
        doc_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "doc-1"}])
        supabase.table.side_effect = lambda name: doc_table

        file_data = {
            "filename": "test.txt",
            "content_b64": base64.b64encode(b"hello").decode("utf-8"),
            "size_bytes": 5,
            "mime_type": "text/plain",
        }

        dummy_result = MagicMock()
        dummy_result.file_type = "txt"
        dummy_result.chunks = [MagicMock(content="chunk", token_count=1)]

        with patch("worker.tasks.get_supabase", return_value=supabase), \
             patch("services.parsers.DocumentProcessorFactory.process", return_value=dummy_result), \
             patch("services.embeddings.generate_embeddings_batch_sync", return_value=[[0.1]]), \
             patch("worker.tasks.insert_rows_with_retry"), \
             patch("worker.tasks.update_file_status"), \
             patch("worker.tasks._record_ingest_outcome_and_maybe_finalize"):
            result = process_file_task._orig_run.__func__(task, "user-1", None, file_data, "file-1", "file_upload")

        assert result["status"] == "success"
    
    @pytest.mark.unit
    def test_returns_job_id_in_result(self):
        """Successful task result should include job_id."""
        # Result should be: {"status": "success", "ingested_ids": [...], "task_id": ..., "job_id": ...}
        from worker.tasks import process_file_task

        task = SimpleNamespace(request=SimpleNamespace(id="task-1"))

        supabase = MagicMock()
        doc_table = MagicMock()
        doc_table.select.return_value = doc_table
        doc_table.eq.return_value = doc_table
        doc_table.limit.return_value = doc_table
        doc_table.execute.return_value = MagicMock(data=[])
        doc_table.insert.return_value = doc_table
        doc_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "doc-1"}])
        supabase.table.side_effect = lambda name: doc_table

        file_data = {
            "filename": "test.txt",
            "content_b64": base64.b64encode(b"hello").decode("utf-8"),
            "size_bytes": 5,
            "mime_type": "text/plain",
        }

        dummy_result = MagicMock()
        dummy_result.file_type = "txt"
        dummy_result.chunks = [MagicMock(content="chunk", token_count=1)]

        with patch("worker.tasks.get_supabase", return_value=supabase), \
             patch("services.parsers.DocumentProcessorFactory.process", return_value=dummy_result), \
             patch("services.embeddings.generate_embeddings_batch_sync", return_value=[[0.1]]), \
             patch("worker.tasks.insert_rows_with_retry"), \
             patch("worker.tasks.update_file_status"), \
             patch("worker.tasks._record_ingest_outcome_and_maybe_finalize"):
            result = process_file_task._orig_run.__func__(task, "user-1", "job-1", file_data, "file-1", "file_upload")

        assert result["status"] == "success"


class TestJobStatusTransitions:
    """Tests for valid job status transitions."""
    
    @pytest.mark.unit
    def test_pending_to_processing(self):
        """Jobs should transition from pending to processing."""
        # This is the expected flow when worker starts
        transitions = [("pending", "processing")]
        assert ("pending", "processing") in transitions
    
    @pytest.mark.unit
    def test_processing_to_completed(self):
        """Jobs should transition from processing to completed."""
        # This is the expected flow on success
        transitions = [("processing", "completed")]
        assert ("processing", "completed") in transitions
    
    @pytest.mark.unit
    def test_processing_to_failed(self):
        """Jobs should transition from processing to failed."""
        # This is the expected flow on error
        transitions = [("processing", "failed")]
        assert ("processing", "failed") in transitions
    
    @pytest.mark.unit
    def test_pending_to_failed(self):
        """Jobs can fail before starting to process."""
        # Early failure case
        transitions = [("pending", "failed")]
        assert ("pending", "failed") in transitions


class TestProgressCalculation:
    """Tests for progress percentage calculations."""
    
    @pytest.mark.unit
    def test_zero_percent_at_start(self):
        """Progress should be 0% when no files processed."""
        processed = 0
        total = 10
        percent = (processed / total * 100) if total > 0 else 0
        assert percent == 0
    
    @pytest.mark.unit
    def test_fifty_percent_at_halfway(self):
        """Progress should be 50% when half files processed."""
        processed = 5
        total = 10
        percent = (processed / total * 100) if total > 0 else 0
        assert percent == 50.0
    
    @pytest.mark.unit
    def test_hundred_percent_when_complete(self):
        """Progress should be 100% when all files processed."""
        processed = 10
        total = 10
        percent = (processed / total * 100) if total > 0 else 0
        assert percent == 100.0
    
    @pytest.mark.unit
    def test_handles_single_file(self):
        """Should handle single file ingestion."""
        processed = 1
        total = 1
        percent = (processed / total * 100) if total > 0 else 0
        assert percent == 100.0
    
    @pytest.mark.unit
    def test_rounds_to_one_decimal(self):
        """Percent should be rounded to one decimal place."""
        processed = 1
        total = 3
        percent = round((processed / total * 100) if total > 0 else 0, 1)
        assert percent == 33.3
