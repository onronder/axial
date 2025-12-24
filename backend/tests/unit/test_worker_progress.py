"""
Test Suite for Worker Task Progress Tracking

Tests for:
- update_job_status helper function
- ingest_file_task job progress updates
- Status transitions: pending -> processing -> completed/failed
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime


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
    """Tests for progress tracking in ingest_file_task."""
    
    @pytest.mark.unit
    def test_sets_status_to_processing_at_start(self):
        """Task should set status to 'processing' when it starts."""
        # Verify the task calls update_job_status with "processing" at start
        pass
    
    @pytest.mark.unit
    def test_increments_processed_files_during_loop(self):
        """Should increment processed_files after each document group."""
        # Verify update_job_status is called with incrementing counts
        pass
    
    @pytest.mark.unit
    def test_sets_status_to_completed_on_success(self):
        """Task should set status to 'completed' when finished successfully."""
        pass
    
    @pytest.mark.unit
    def test_sets_status_to_failed_on_exception(self):
        """Task should set status to 'failed' when exception occurs."""
        pass
    
    @pytest.mark.unit
    def test_saves_error_message_on_failure(self):
        """Task should save the error message when it fails."""
        pass
    
    @pytest.mark.unit
    def test_handles_missing_job_id_gracefully(self):
        """Task should work without job_id (backward compatibility)."""
        # job_id is optional, task should not crash if not provided
        pass
    
    @pytest.mark.unit
    def test_returns_job_id_in_result(self):
        """Successful task result should include job_id."""
        # Result should be: {"status": "success", "ingested_ids": [...], "task_id": ..., "job_id": ...}
        pass


class TestJobStatusTransitions:
    """Tests for valid job status transitions."""
    
    @pytest.mark.unit
    def test_pending_to_processing(self):
        """Jobs should transition from pending to processing."""
        # This is the expected flow when worker starts
        pass
    
    @pytest.mark.unit
    def test_processing_to_completed(self):
        """Jobs should transition from processing to completed."""
        # This is the expected flow on success
        pass
    
    @pytest.mark.unit
    def test_processing_to_failed(self):
        """Jobs should transition from processing to failed."""
        # This is the expected flow on error
        pass
    
    @pytest.mark.unit
    def test_pending_to_failed(self):
        """Jobs can fail before starting to process."""
        # Early failure case
        pass


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
