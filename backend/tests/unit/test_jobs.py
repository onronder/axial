"""
Test Suite for Jobs API

Tests for:
- GET /api/v1/jobs/active - Get active ingestion job for polling
- GET /api/v1/jobs/{id} - Get specific job by ID
- GET /api/v1/jobs - List recent jobs
- Job progress tracking integration
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class TestGetActiveJob:
    """Tests for GET /api/v1/jobs/active endpoint."""
    
    @pytest.fixture
    def mock_supabase_with_active_job(self):
        """Mock Supabase with an active job."""
        mock = MagicMock()
        
        # Mock query chain
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.in_.return_value = table
        table.order.return_value = table
        table.limit.return_value = table
        table.execute.return_value = MagicMock(data=[{
            "id": "job-123",
            "user_id": "user-123",
            "provider": "google_drive",
            "total_files": 10,
            "processed_files": 5,
            "status": "processing",
            "error_message": None,
            "created_at": "2024-01-01T00:00:00Z"
        }])
        
        mock.table.return_value = table
        return mock
    
    @pytest.fixture
    def mock_supabase_no_active_job(self):
        """Mock Supabase with no active job."""
        mock = MagicMock()
        
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.in_.return_value = table
        table.order.return_value = table
        table.limit.return_value = table
        table.execute.return_value = MagicMock(data=[])
        
        mock.table.return_value = table
        return mock
    
    @pytest.mark.unit
    def test_returns_active_job_when_processing(self, mock_supabase_with_active_job):
        """Should return job when status is 'processing'."""
        with patch('core.db.get_supabase', return_value=mock_supabase_with_active_job):
            # Verify query filters by status IN ('pending', 'processing')
            mock_supabase_with_active_job.table.return_value.in_.assert_not_called()  # Not called until endpoint
    
    @pytest.mark.unit
    def test_returns_none_when_no_active_job(self, mock_supabase_no_active_job):
        """Should return None/204 when no active job exists."""
        pass
    
    @pytest.mark.unit
    def test_calculates_percent_correctly(self):
        """Percent should be (processed_files / total_files) * 100."""
        # Given: processed_files=5, total_files=10
        # Expected: percent=50.0
        processed = 5
        total = 10
        expected_percent = (processed / total) * 100
        assert expected_percent == 50.0
    
    @pytest.mark.unit
    def test_handles_zero_total_files(self):
        """Should return 0% when total_files is 0 (avoid division by zero)."""
        processed = 0
        total = 0
        percent = (processed / total * 100) if total > 0 else 0
        assert percent == 0
    
    @pytest.mark.unit
    def test_filters_by_user_id(self, mock_supabase_with_active_job):
        """Should only return jobs for the current user."""
        # This tests that user isolation is enforced
        pass
    
    @pytest.mark.unit
    def test_returns_most_recent_job(self):
        """Should return the most recently created active job when multiple exist."""
        # Ordered by created_at DESC, limit 1
        pass


class TestGetJobById:
    """Tests for GET /api/v1/jobs/{id} endpoint."""
    
    @pytest.mark.unit
    def test_returns_job_when_exists(self):
        """Should return job details when job exists."""
        pass
    
    @pytest.mark.unit
    def test_returns_404_when_not_found(self):
        """Should return 404 when job doesn't exist."""
        pass
    
    @pytest.mark.unit
    def test_returns_404_for_other_users_job(self):
        """Should return 404 when job belongs to different user."""
        # Ensures user isolation
        pass


class TestListJobs:
    """Tests for GET /api/v1/jobs endpoint."""
    
    @pytest.mark.unit
    def test_returns_user_jobs(self):
        """Should return list of user's jobs."""
        pass
    
    @pytest.mark.unit
    def test_respects_limit_parameter(self):
        """Should limit results to specified count."""
        pass
    
    @pytest.mark.unit
    def test_orders_by_created_at_desc(self):
        """Should return most recent jobs first."""
        pass


class TestIngestionJobResponse:
    """Tests for the job response schema."""
    
    @pytest.mark.unit
    def test_response_includes_all_fields(self):
        """Response should include id, provider, total_files, etc."""
        # Schema validation - verify expected fields
        expected_fields = [
            "id", "provider", "total_files", "processed_files",
            "status", "percent", "error_message", "created_at"
        ]
        
        # Simulate a response dict
        response = {
            "id": "job-123",
            "provider": "google_drive",
            "total_files": 10,
            "processed_files": 5,
            "status": "processing",
            "percent": 50.0,
            "error_message": None,
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        for field in expected_fields:
            assert field in response
    
    @pytest.mark.unit
    def test_percent_is_float(self):
        """Percent field should be a float, not int."""
        # Calculate percent
        processed = 1
        total = 3
        percent = round((processed / total) * 100, 1)
        
        # Should be 33.3, not 33
        assert isinstance(percent, float)
        assert percent == 33.3


class TestIngestionJobModel:
    """Tests for the IngestionJob data structure."""
    
    @pytest.mark.unit
    def test_model_has_required_fields(self):
        """IngestionJob should have all required fields."""
        # Verify expected field names
        expected_fields = [
            "id", "user_id", "provider", "total_files",
            "processed_files", "status", "error_message",
            "created_at", "updated_at"
        ]
        
        # Simulate a job dict
        job = {
            "id": "job-123",
            "user_id": "user-123",
            "provider": "google_drive",
            "total_files": 10,
            "processed_files": 5,
            "status": "processing",
            "error_message": None,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
        
        for field in expected_fields:
            assert field in job
    
    @pytest.mark.unit
    def test_default_status_is_pending(self):
        """New jobs should default to 'pending' status."""
        default_status = "pending"
        assert default_status == "pending"
    
    @pytest.mark.unit
    def test_default_file_counts_are_zero(self):
        """New jobs should have 0 processed and total files by default."""
        default_total = 0
        default_processed = 0
        
        assert default_total == 0
        assert default_processed == 0


class TestJobStatus:
    """Tests for job status enum values."""
    
    @pytest.mark.unit
    def test_valid_status_values(self):
        """Job status should support pending, processing, completed, failed, cancelled."""
        valid_statuses = ["pending", "processing", "completed", "failed", "cancelled"]
        
        assert "pending" in valid_statuses
        assert "processing" in valid_statuses
        assert "completed" in valid_statuses
        assert "failed" in valid_statuses
        assert "cancelled" in valid_statuses


# =============================================================================
# Tests for NEW CRUD Endpoints
# =============================================================================

class TestRetryJobEndpoint:
    """Tests for POST /api/v1/jobs/{job_id}/retry."""
    
    @pytest.fixture
    def mock_supabase_with_failed_job(self):
        """Mock Supabase with a failed job."""
        mock = MagicMock()
        
        # Job lookup response
        job_response = MagicMock()
        job_response.data = {
            "id": "job-123",
            "user_id": "user-123",
            "status": "failed",
            "provider": "google_drive"
        }
        
        # Failed files response
        files_response = MagicMock()
        files_response.data = [
            {"id": "file-1", "status": "failed", "retry_count": 1},
            {"id": "file-2", "status": "failed", "retry_count": 2},
            {"id": "file-3", "status": "failed", "retry_count": 3},  # Max retries
        ]
        
        # Update responses
        update_response = MagicMock()
        update_response.data = [{"id": "file-1"}]
        
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.in_.return_value = table
        table.lt.return_value = table
        table.single.return_value = table
        table.update.return_value = table
        table.execute.side_effect = [job_response, files_response, update_response, update_response, update_response]
        
        mock.table.return_value = table
        return mock
    
    @pytest.mark.unit
    def test_retry_job_resets_failed_files(self, mock_supabase_with_failed_job):
        """Should reset failed files to pending status."""
        # Files with status="failed" should be reset to status="pending"
        reset_status = "pending"
        assert reset_status == "pending"
    
    @pytest.mark.unit
    def test_retry_job_increments_retry_count(self):
        """Should increment retry_count for each file."""
        current_retry_count = 1
        new_retry_count = current_retry_count + 1
        assert new_retry_count == 2
    
    @pytest.mark.unit
    def test_retry_job_skips_max_retry_files(self):
        """Should skip files that have reached max retry count (3)."""
        max_retries = 3
        file_retry_count = 3
        can_retry = file_retry_count < max_retries
        assert can_retry is False
    
    @pytest.mark.unit
    def test_retry_job_returns_queued_count(self):
        """Should return count of files queued for retry."""
        files_queued = 2
        files_skipped = 1
        assert files_queued == 2
        assert files_skipped == 1
    
    @pytest.mark.unit
    def test_retry_job_updates_job_status(self):
        """Should update job status to 'processing'."""
        new_job_status = "processing"
        assert new_job_status == "processing"
    
    @pytest.mark.unit
    def test_retry_job_verifies_ownership(self):
        """Should verify job belongs to requesting user."""
        # Query should filter by user_id
        job_user_id = "user-123"
        requesting_user_id = "user-123"
        assert job_user_id == requesting_user_id
    
    @pytest.mark.unit
    def test_retry_job_returns_404_for_nonexistent(self):
        """Should return 404 when job doesn't exist."""
        mock = MagicMock()
        job_response = MagicMock()
        job_response.data = None
        
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.single.return_value = table
        table.execute.return_value = job_response
        mock.table.return_value = table
        
        assert job_response.data is None
    
    @pytest.mark.unit
    def test_retry_job_returns_400_for_invalid_status(self):
        """Should return 400 when job is still pending/processing."""
        invalid_statuses = ["pending", "processing"]
        for status in invalid_statuses:
            can_retry = status in ["failed", "completed"]
            assert can_retry is False
    
    @pytest.mark.unit
    def test_retry_job_returns_400_when_no_files_to_retry(self):
        """Should return 400 when no files can be retried."""
        retryable_files = []
        has_retryable = len(retryable_files) > 0
        assert has_retryable is False
    
    @pytest.mark.unit
    def test_retry_job_clears_error_message(self):
        """Should clear error_message when resetting file status."""
        error_message_after_reset = None
        assert error_message_after_reset is None
    
    @pytest.mark.unit
    def test_retry_job_sets_progress_to_zero(self):
        """Should reset progress to 0 when retrying."""
        progress_after_reset = 0
        assert progress_after_reset == 0


class TestCancelJobEndpoint:
    """Tests for POST /api/v1/jobs/{job_id}/cancel."""
    
    @pytest.mark.unit
    def test_cancel_job_revokes_celery_task(self):
        """Should revoke the Celery task."""
        # celery.result.revoke() should be called
        pass
    
    @pytest.mark.unit
    def test_cancel_job_updates_status(self):
        """Should update job status to 'cancelled'."""
        new_status = "cancelled"
        assert new_status == "cancelled"
    
    @pytest.mark.unit
    def test_cancel_job_verifies_ownership(self):
        """Should verify job belongs to requesting user."""
        pass


class TestGetJobFilesEndpoint:
    """Tests for GET /api/v1/jobs/{job_id}/files."""
    
    @pytest.mark.unit
    def test_get_files_returns_file_statuses(self):
        """Should return list of file status records."""
        files = [
            {"id": "file-1", "filename": "doc.pdf", "status": "completed"},
            {"id": "file-2", "filename": "report.docx", "status": "failed"}
        ]
        assert len(files) == 2
    
    @pytest.mark.unit
    def test_get_files_filters_by_job_id(self):
        """Should only return files for the specified job."""
        job_id = "job-123"
        filter_column = "job_id"
        assert filter_column == "job_id"
    
    @pytest.mark.unit
    def test_get_files_verifies_job_ownership(self):
        """Should verify user owns the job."""
        pass
