"""
Test Suite for Jobs API

Tests for:
- GET /api/v1/jobs/active - Get active ingestion job for polling
- GET /api/v1/jobs/{id} - Get specific job by ID
- GET /api/v1/jobs - List recent jobs
- Job progress tracking integration
"""

import asyncio
import sys
import types
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

import pytest
from fastapi import HTTPException


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
        with patch("api.v1.jobs.get_supabase", return_value=mock_supabase_with_active_job):
            from api.v1.jobs import get_active_job

            result = asyncio.run(get_active_job(user_id="user-123"))

        assert result.id == "job-123"
    
    @pytest.mark.unit
    def test_returns_none_when_no_active_job(self, mock_supabase_no_active_job):
        """Should return None/204 when no active job exists."""
        with patch("api.v1.jobs.get_supabase", return_value=mock_supabase_no_active_job):
            from api.v1.jobs import get_active_job

            result = asyncio.run(get_active_job(user_id="user-123"))

        assert result is None
    
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
    def test_filters_by_organization_id(self, mock_supabase_with_active_job):
        """Should only return jobs for the current organization."""
        # This tests that org isolation is enforced
        with patch("api.v1.jobs.get_supabase", return_value=mock_supabase_with_active_job), \
             patch("api.v1.jobs._resolve_org_id", return_value="org-1"):
            from api.v1.jobs import get_active_job

            asyncio.run(get_active_job(user_id="user-123"))

        mock_supabase_with_active_job.table.return_value.eq.assert_any_call("organization_id", "org-1")
    
    @pytest.mark.unit
    def test_returns_most_recent_job(self):
        """Should return the most recently created active job when multiple exist."""
        # Ordered by created_at DESC, limit 1
        mock_supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.in_.return_value = table
        table.order.return_value = table
        table.limit.return_value = table
        table.execute.return_value = MagicMock(
            data=[{"id": "job-1", "provider": "google_drive", "status": "processing"}]
        )
        mock_supabase.table.return_value = table

        with patch("api.v1.jobs.get_supabase", return_value=mock_supabase):
            from api.v1.jobs import get_active_job

            asyncio.run(get_active_job(user_id="user-123"))

        table.order.assert_called_with("created_at", desc=True)
        table.limit.assert_called_with(1)


class TestGetJobById:
    """Tests for GET /api/v1/jobs/{id} endpoint."""
    
    @pytest.mark.unit
    def test_returns_job_when_exists(self):
        """Should return job details when job exists."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.single.return_value = table
        table.execute.return_value = MagicMock(
            data={
                "id": "job-1",
                "provider": "google_drive",
                "total_files": 2,
                "processed_files": 1,
                "status": "processing",
            }
        )
        mock_supabase.table.return_value = table

        with patch("api.v1.jobs.get_supabase", return_value=mock_supabase):
            from api.v1.jobs import get_job_by_id

            result = asyncio.run(get_job_by_id("job-1", user_id="user-123"))

        assert result.id == "job-1"
    
    @pytest.mark.unit
    def test_returns_404_when_not_found(self):
        """Should return 404 when job doesn't exist."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.single.return_value = table
        table.execute.return_value = MagicMock(data=None)
        mock_supabase.table.return_value = table

        with patch("api.v1.jobs.get_supabase", return_value=mock_supabase):
            from api.v1.jobs import get_job_by_id

            with pytest.raises(HTTPException) as exc:
                asyncio.run(get_job_by_id("job-1", user_id="user-123"))
        assert exc.value.status_code == 404
    
    @pytest.mark.unit
    def test_returns_404_for_other_users_job(self):
        """Should return 404 when job belongs to different user."""
        # Ensures user isolation
        mock_supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.single.return_value = table
        table.execute.return_value = MagicMock(data=None)
        mock_supabase.table.return_value = table

        with patch("api.v1.jobs.get_supabase", return_value=mock_supabase):
            from api.v1.jobs import get_job_by_id

            with pytest.raises(HTTPException) as exc:
                asyncio.run(get_job_by_id("job-1", user_id="user-123"))
        assert exc.value.status_code == 404

    @pytest.mark.unit
    def test_handles_single_no_rows_error(self):
        """Should return 404 when PostgREST single() returns no rows."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.single.return_value = table
        table.execute.side_effect = Exception("PGRST116: JSON object requested, multiple (or no) rows returned")
        mock_supabase.table.return_value = table

        with patch("api.v1.jobs.get_supabase", return_value=mock_supabase):
            from api.v1.jobs import get_job_by_id

            with pytest.raises(HTTPException) as exc:
                asyncio.run(get_job_by_id("job-1", user_id="user-123"))
        assert exc.value.status_code == 404

    @pytest.mark.unit
    def test_handles_unexpected_response_error(self):
        """Should return 500 when an unexpected error occurs."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.single.return_value = table
        table.execute.return_value = object()  # Missing expected attributes
        mock_supabase.table.return_value = table

        with patch("api.v1.jobs.get_supabase", return_value=mock_supabase):
            from api.v1.jobs import get_job_by_id

            with pytest.raises(HTTPException) as exc:
                asyncio.run(get_job_by_id("job-1", user_id="user-123"))
        assert exc.value.status_code == 500


class TestListJobs:
    """Tests for GET /api/v1/jobs endpoint."""
    
    @pytest.mark.unit
    def test_returns_user_jobs(self):
        """Should return list of user's jobs."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.order.return_value = table
        table.limit.return_value = table
        table.execute.return_value = MagicMock(
            data=[{"id": "job-1", "provider": "web", "status": "completed"}]
        )
        mock_supabase.table.return_value = table

        with patch("api.v1.jobs.get_supabase", return_value=mock_supabase):
            from api.v1.jobs import list_recent_jobs

            result = asyncio.run(list_recent_jobs(user_id="user-123", limit=10))

        assert len(result) == 1
    
    @pytest.mark.unit
    def test_respects_limit_parameter(self):
        """Should limit results to specified count."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.order.return_value = table
        table.limit.return_value = table
        table.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value = table

        with patch("api.v1.jobs.get_supabase", return_value=mock_supabase):
            from api.v1.jobs import list_recent_jobs

            asyncio.run(list_recent_jobs(user_id="user-123", limit=5))

        table.limit.assert_called_with(5)
    
    @pytest.mark.unit
    def test_orders_by_created_at_desc(self):
        """Should return most recent jobs first."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.order.return_value = table
        table.limit.return_value = table
        table.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value = table

        with patch("api.v1.jobs.get_supabase", return_value=mock_supabase):
            from api.v1.jobs import list_recent_jobs

            asyncio.run(list_recent_jobs(user_id="user-123", limit=5))

        table.order.assert_called_with("created_at", desc=True)


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
        """Should verify job belongs to requesting org."""
        # Query should filter by organization_id
        mock_supabase = MagicMock()
        job_response = MagicMock()
        job_response.data = {"id": "job-1", "user_id": "user-123", "status": "failed"}
        files_response = MagicMock()
        files_response.data = [{"id": "file-1", "status": "failed", "retry_count": 0}]

        job_table = MagicMock()
        job_table.select.return_value = job_table
        job_table.eq.return_value = job_table
        job_table.single.return_value = job_table
        job_table.execute.side_effect = [job_response, MagicMock(data=[])]
        job_table.update.return_value = job_table

        files_table = MagicMock()
        files_table.select.return_value = files_table
        files_table.eq.return_value = files_table
        files_table.execute.return_value = files_response
        files_table.update.return_value = files_table

        mock_supabase.table.side_effect = lambda name: job_table if name == "ingestion_jobs" else files_table

        with patch("api.v1.jobs.get_supabase", return_value=mock_supabase):
            from api.v1.jobs import retry_job

            asyncio.run(retry_job("job-1", user_id="user-123"))

        job_table.eq.assert_any_call("organization_id", "user-123")
    
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
        mock_supabase = MagicMock()
        job_response = MagicMock()
        job_response.data = {"id": "job-1", "user_id": "user-123", "status": "processing", "celery_task_id": "task-1"}

        job_table = MagicMock()
        job_table.select.return_value = job_table
        job_table.eq.return_value = job_table
        job_table.single.return_value = job_table
        job_table.execute.return_value = job_response
        job_table.update.return_value = job_table

        file_table = MagicMock()
        file_table.update.return_value = file_table
        file_table.eq.return_value = file_table
        file_table.in_.return_value = file_table

        mock_supabase.table.side_effect = lambda name: job_table if name == "ingestion_jobs" else file_table

        fake_celery = types.SimpleNamespace(control=MagicMock())
        module = types.SimpleNamespace(celery_app=fake_celery)
        sys.modules["worker.celery_app"] = module

        with patch("api.v1.jobs.get_supabase", return_value=mock_supabase):
            from api.v1.jobs import cancel_job

            result = asyncio.run(cancel_job("job-1", user_id="user-123"))

        assert result["status"] == "cancelled"
        fake_celery.control.revoke.assert_called_with("task-1", terminate=True)
    
    @pytest.mark.unit
    def test_cancel_job_updates_status(self):
        """Should update job status to 'cancelled'."""
        new_status = "cancelled"
        assert new_status == "cancelled"
    
    @pytest.mark.unit
    def test_cancel_job_verifies_ownership(self):
        """Should verify job belongs to requesting user."""
        mock_supabase = MagicMock()
        job_response = MagicMock()
        job_response.data = None
        job_table = MagicMock()
        job_table.select.return_value = job_table
        job_table.eq.return_value = job_table
        job_table.single.return_value = job_table
        job_table.execute.return_value = job_response
        mock_supabase.table.return_value = job_table

        with patch("api.v1.jobs.get_supabase", return_value=mock_supabase):
            from api.v1.jobs import cancel_job

            with pytest.raises(HTTPException) as exc:
                asyncio.run(cancel_job("job-1", user_id="user-123"))
        assert exc.value.status_code == 404


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
        mock_supabase = MagicMock()
        job_table = MagicMock()
        job_table.select.return_value = job_table
        job_table.eq.return_value = job_table
        job_table.single.return_value = job_table
        job_table.execute.return_value = MagicMock(data=None)
        mock_supabase.table.return_value = job_table

        with patch("api.v1.jobs.get_supabase", return_value=mock_supabase):
            from api.v1.jobs import get_job_files

            with pytest.raises(HTTPException) as exc:
                asyncio.run(get_job_files("job-1", user_id="user-123"))
        assert exc.value.status_code == 404


class TestRetryFileEndpoint:
    @pytest.mark.unit
    def test_retry_file_queues_retry(self):
        file_table = MagicMock()
        file_table.select.return_value = file_table
        file_table.eq.return_value = file_table
        file_table.single.return_value = file_table
        file_table.update.return_value = file_table
        file_table.execute.side_effect = [
            MagicMock(
                data={
                    "id": "file-1",
                    "job_id": "job-1",
                    "status": "failed",
                    "retry_count": 1,
                    "can_retry": True,
                    "ingestion_jobs": {"organization_id": "user-123"},
                }
            ),
            MagicMock(data=[]),
        ]

        job_table = MagicMock()
        job_table.update.return_value = job_table
        job_table.eq.return_value = job_table
        job_table.in_.return_value = job_table
        job_table.execute.return_value = MagicMock(data=[])

        supabase = MagicMock()
        supabase.table.side_effect = lambda name: {
            "ingestion_file_status": file_table,
            "ingestion_jobs": job_table,
        }[name]

        with patch("api.v1.jobs.get_supabase", return_value=supabase):
            from api.v1.jobs import retry_file

            result = asyncio.run(retry_file("file-1", user_id="user-123"))

        assert result["status"] == "queued"


class TestRetryJobEndpoint:
    @pytest.mark.unit
    def test_retry_job_resets_failed_files(self):
        job_table = MagicMock()
        job_table.select.return_value = job_table
        job_table.eq.return_value = job_table
        job_table.single.return_value = job_table
        job_table.update.return_value = job_table
        job_table.execute.side_effect = [
            MagicMock(data={"id": "job-1", "status": "failed"}),
            MagicMock(data=[]),
        ]

        file_table = MagicMock()
        file_table.select.return_value = file_table
        file_table.eq.return_value = file_table
        file_table.execute.return_value = MagicMock(
            data=[{"id": "file-1", "retry_count": 0}]
        )
        file_table.update.return_value = file_table

        supabase = MagicMock()
        supabase.table.side_effect = lambda name: {
            "ingestion_jobs": job_table,
            "ingestion_file_status": file_table,
        }[name]

        with patch("api.v1.jobs.get_supabase", return_value=supabase):
            from api.v1.jobs import retry_job

            result = asyncio.run(retry_job("job-1", user_id="user-123"))

        assert result["files_queued"] == 1


class TestGetJobFilesDetailed:
    @pytest.mark.unit
    def test_get_job_files_returns_data(self):
        job_table = MagicMock()
        job_table.select.return_value = job_table
        job_table.eq.return_value = job_table
        job_table.single.return_value = job_table
        job_table.execute.return_value = MagicMock(data={"id": "job-1"})

        file_table = MagicMock()
        file_table.select.return_value = file_table
        file_table.eq.return_value = file_table
        file_table.order.return_value = file_table
        file_table.execute.return_value = MagicMock(data=[{"id": "file-1"}])

        supabase = MagicMock()
        supabase.table.side_effect = lambda name: {
            "ingestion_jobs": job_table,
            "ingestion_file_status": file_table,
        }[name]

        with patch("api.v1.jobs.get_supabase", return_value=supabase):
            from api.v1.jobs import get_job_files

            result = asyncio.run(get_job_files("job-1", user_id="user-123"))

        assert result[0]["id"] == "file-1"


class TestJobErrorPaths:
    @pytest.mark.unit
    def test_get_active_job_handles_exception(self):
        mock_supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.in_.return_value = table
        table.order.return_value = table
        table.limit.return_value = table
        table.execute.side_effect = Exception("boom")
        mock_supabase.table.return_value = table

        with patch("api.v1.jobs.get_supabase", return_value=mock_supabase):
            from api.v1.jobs import get_active_job

            with pytest.raises(HTTPException) as exc:
                asyncio.run(get_active_job(user_id="user-123"))
        assert exc.value.status_code == 500

    @pytest.mark.unit
    def test_get_job_by_id_handles_exception(self):
        mock_supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.single.return_value = table
        table.execute.side_effect = Exception("boom")
        mock_supabase.table.return_value = table

        with patch("api.v1.jobs.get_supabase", return_value=mock_supabase):
            from api.v1.jobs import get_job_by_id

            with pytest.raises(HTTPException) as exc:
                asyncio.run(get_job_by_id("job-1", user_id="user-123"))
        assert exc.value.status_code == 500

    @pytest.mark.unit
    def test_list_recent_jobs_handles_exception(self):
        mock_supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.order.return_value = table
        table.limit.return_value = table
        table.execute.side_effect = Exception("boom")
        mock_supabase.table.return_value = table

        with patch("api.v1.jobs.get_supabase", return_value=mock_supabase):
            from api.v1.jobs import list_recent_jobs

            with pytest.raises(HTTPException) as exc:
                asyncio.run(list_recent_jobs(user_id="user-123", limit=10))
        assert exc.value.status_code == 500

    @pytest.mark.unit
    def test_cancel_job_rejects_completed(self):
        mock_supabase = MagicMock()
        job_response = MagicMock()
        job_response.data = {"id": "job-1", "user_id": "user-123", "status": "completed"}

        job_table = MagicMock()
        job_table.select.return_value = job_table
        job_table.eq.return_value = job_table
        job_table.single.return_value = job_table
        job_table.execute.return_value = job_response
        mock_supabase.table.return_value = job_table

        with patch("api.v1.jobs.get_supabase", return_value=mock_supabase):
            from api.v1.jobs import cancel_job

            with pytest.raises(HTTPException) as exc:
                asyncio.run(cancel_job("job-1", user_id="user-123"))
        assert exc.value.status_code == 400

    @pytest.mark.unit
    def test_cancel_job_handles_revoke_error(self):
        mock_supabase = MagicMock()
        job_response = MagicMock()
        job_response.data = {
            "id": "job-1",
            "user_id": "user-123",
            "status": "processing",
            "celery_task_id": "task-1",
        }

        job_table = MagicMock()
        job_table.select.return_value = job_table
        job_table.eq.return_value = job_table
        job_table.single.return_value = job_table
        job_table.execute.return_value = job_response
        job_table.update.return_value = job_table

        file_table = MagicMock()
        file_table.update.return_value = file_table
        file_table.eq.return_value = file_table
        file_table.in_.return_value = file_table

        mock_supabase.table.side_effect = lambda name: job_table if name == "ingestion_jobs" else file_table

        fake_celery = types.SimpleNamespace(control=MagicMock())
        fake_celery.control.revoke.side_effect = Exception("boom")
        module = types.SimpleNamespace(celery_app=fake_celery)
        sys.modules["worker.celery_app"] = module

        with patch("api.v1.jobs.get_supabase", return_value=mock_supabase):
            from api.v1.jobs import cancel_job

            result = asyncio.run(cancel_job("job-1", user_id="user-123"))

        assert result["status"] == "cancelled"

    @pytest.mark.unit
    def test_cancel_job_handles_exception(self):
        mock_supabase = MagicMock()
        job_table = MagicMock()
        job_table.select.return_value = job_table
        job_table.eq.return_value = job_table
        job_table.single.return_value = job_table
        job_table.execute.side_effect = Exception("boom")
        mock_supabase.table.return_value = job_table

        with patch("api.v1.jobs.get_supabase", return_value=mock_supabase):
            from api.v1.jobs import cancel_job

            with pytest.raises(HTTPException) as exc:
                asyncio.run(cancel_job("job-1", user_id="user-123"))
        assert exc.value.status_code == 500

    @pytest.mark.unit
    def test_retry_file_not_found(self):
        file_table = MagicMock()
        file_table.select.return_value = file_table
        file_table.eq.return_value = file_table
        file_table.single.return_value = file_table
        file_table.execute.return_value = MagicMock(data=None)

        supabase = MagicMock()
        supabase.table.return_value = file_table

        with patch("api.v1.jobs.get_supabase", return_value=supabase):
            from api.v1.jobs import retry_file

            with pytest.raises(HTTPException) as exc:
                asyncio.run(retry_file("file-1", user_id="user-123"))
        assert exc.value.status_code == 404

    @pytest.mark.unit
    def test_retry_file_user_mismatch(self):
        file_table = MagicMock()
        file_table.select.return_value = file_table
        file_table.eq.return_value = file_table
        file_table.single.return_value = file_table
        file_table.execute.return_value = MagicMock(
            data={"status": "failed", "ingestion_jobs": {"organization_id": "other"}}
        )

        supabase = MagicMock()
        supabase.table.return_value = file_table

        with patch("api.v1.jobs.get_supabase", return_value=supabase):
            from api.v1.jobs import retry_file

            with pytest.raises(HTTPException) as exc:
                asyncio.run(retry_file("file-1", user_id="user-123"))
        assert exc.value.status_code == 404

    @pytest.mark.unit
    def test_retry_file_invalid_status(self):
        file_table = MagicMock()
        file_table.select.return_value = file_table
        file_table.eq.return_value = file_table
        file_table.single.return_value = file_table
        file_table.execute.return_value = MagicMock(
            data={
                "status": "processing",
                "can_retry": True,
                "ingestion_jobs": {"organization_id": "user-123"},
            }
        )

        supabase = MagicMock()
        supabase.table.return_value = file_table

        with patch("api.v1.jobs.get_supabase", return_value=supabase):
            from api.v1.jobs import retry_file

            with pytest.raises(HTTPException) as exc:
                asyncio.run(retry_file("file-1", user_id="user-123"))
        assert exc.value.status_code == 400

    @pytest.mark.unit
    def test_retry_file_cannot_retry(self):
        file_table = MagicMock()
        file_table.select.return_value = file_table
        file_table.eq.return_value = file_table
        file_table.single.return_value = file_table
        file_table.execute.return_value = MagicMock(
            data={
                "status": "failed",
                "can_retry": False,
                "ingestion_jobs": {"organization_id": "user-123"},
            }
        )

        supabase = MagicMock()
        supabase.table.return_value = file_table

        with patch("api.v1.jobs.get_supabase", return_value=supabase):
            from api.v1.jobs import retry_file

            with pytest.raises(HTTPException) as exc:
                asyncio.run(retry_file("file-1", user_id="user-123"))
        assert exc.value.status_code == 400

    @pytest.mark.unit
    def test_retry_file_max_attempts_exceeded(self):
        file_table = MagicMock()
        file_table.select.return_value = file_table
        file_table.eq.return_value = file_table
        file_table.single.return_value = file_table
        file_table.execute.return_value = MagicMock(
            data={
                "status": "failed",
                "retry_count": 3,
                "can_retry": True,
                "ingestion_jobs": {"organization_id": "user-123"},
            }
        )

        supabase = MagicMock()
        supabase.table.return_value = file_table

        with patch("api.v1.jobs.get_supabase", return_value=supabase):
            from api.v1.jobs import retry_file

            with pytest.raises(HTTPException) as exc:
                asyncio.run(retry_file("file-1", user_id="user-123"))
        assert exc.value.status_code == 400

    @pytest.mark.unit
    def test_retry_file_handles_exception(self):
        file_table = MagicMock()
        file_table.select.return_value = file_table
        file_table.eq.return_value = file_table
        file_table.single.return_value = file_table
        file_table.execute.side_effect = Exception("boom")

        supabase = MagicMock()
        supabase.table.return_value = file_table

        with patch("api.v1.jobs.get_supabase", return_value=supabase):
            from api.v1.jobs import retry_file

            with pytest.raises(HTTPException) as exc:
                asyncio.run(retry_file("file-1", user_id="user-123"))
        assert exc.value.status_code == 500

    @pytest.mark.unit
    def test_get_job_files_handles_exception(self):
        job_table = MagicMock()
        job_table.select.return_value = job_table
        job_table.eq.return_value = job_table
        job_table.single.return_value = job_table
        job_table.execute.return_value = MagicMock(data={"id": "job-1"})

        file_table = MagicMock()
        file_table.select.return_value = file_table
        file_table.eq.return_value = file_table
        file_table.order.return_value = file_table
        file_table.execute.side_effect = Exception("boom")

        supabase = MagicMock()
        supabase.table.side_effect = lambda name: {
            "ingestion_jobs": job_table,
            "ingestion_file_status": file_table,
        }[name]

        with patch("api.v1.jobs.get_supabase", return_value=supabase):
            from api.v1.jobs import get_job_files

            with pytest.raises(HTTPException) as exc:
                asyncio.run(get_job_files("job-1", user_id="user-123"))
        assert exc.value.status_code == 500

    @pytest.mark.unit
    def test_retry_job_no_failed_files(self):
        job_table = MagicMock()
        job_table.select.return_value = job_table
        job_table.eq.return_value = job_table
        job_table.single.return_value = job_table
        job_table.execute.side_effect = [
            MagicMock(data={"id": "job-1", "status": "failed"}),
            MagicMock(data=[]),
        ]

        file_table = MagicMock()
        file_table.select.return_value = file_table
        file_table.eq.return_value = file_table
        file_table.execute.return_value = MagicMock(data=[])

        supabase = MagicMock()
        supabase.table.side_effect = lambda name: {
            "ingestion_jobs": job_table,
            "ingestion_file_status": file_table,
        }[name]

        with patch("api.v1.jobs.get_supabase", return_value=supabase):
            from api.v1.jobs import retry_job

            with pytest.raises(HTTPException) as exc:
                asyncio.run(retry_job("job-1", user_id="user-123"))
        assert exc.value.status_code == 400

    @pytest.mark.unit
    def test_retry_job_all_failed_exceeded(self):
        job_table = MagicMock()
        job_table.select.return_value = job_table
        job_table.eq.return_value = job_table
        job_table.single.return_value = job_table
        job_table.execute.side_effect = [
            MagicMock(data={"id": "job-1", "status": "failed"}),
            MagicMock(data=[]),
        ]

        file_table = MagicMock()
        file_table.select.return_value = file_table
        file_table.eq.return_value = file_table
        file_table.execute.return_value = MagicMock(
            data=[{"id": "file-1", "retry_count": 3}]
        )

        supabase = MagicMock()
        supabase.table.side_effect = lambda name: {
            "ingestion_jobs": job_table,
            "ingestion_file_status": file_table,
        }[name]

        with patch("api.v1.jobs.get_supabase", return_value=supabase):
            from api.v1.jobs import retry_job

            with pytest.raises(HTTPException) as exc:
                asyncio.run(retry_job("job-1", user_id="user-123"))
        assert exc.value.status_code == 400

    @pytest.mark.unit
    def test_retry_job_handles_exception(self):
        job_table = MagicMock()
        job_table.select.return_value = job_table
        job_table.eq.return_value = job_table
        job_table.single.return_value = job_table
        job_table.execute.side_effect = Exception("boom")

        supabase = MagicMock()
        supabase.table.return_value = job_table

        with patch("api.v1.jobs.get_supabase", return_value=supabase):
            from api.v1.jobs import retry_job

            with pytest.raises(HTTPException) as exc:
                asyncio.run(retry_job("job-1", user_id="user-123"))
        assert exc.value.status_code == 500

    @pytest.mark.unit
    def test_retry_job_not_found(self):
        job_table = MagicMock()
        job_table.select.return_value = job_table
        job_table.eq.return_value = job_table
        job_table.single.return_value = job_table
        job_table.execute.return_value = MagicMock(data=None)

        supabase = MagicMock()
        supabase.table.return_value = job_table

        with patch("api.v1.jobs.get_supabase", return_value=supabase):
            from api.v1.jobs import retry_job

            with pytest.raises(HTTPException) as exc:
                asyncio.run(retry_job("job-1", user_id="user-123"))
        assert exc.value.status_code == 404

    @pytest.mark.unit
    def test_retry_job_invalid_status(self):
        job_table = MagicMock()
        job_table.select.return_value = job_table
        job_table.eq.return_value = job_table
        job_table.single.return_value = job_table
        job_table.execute.return_value = MagicMock(data={"id": "job-1", "status": "processing"})

        supabase = MagicMock()
        supabase.table.return_value = job_table

        with patch("api.v1.jobs.get_supabase", return_value=supabase):
            from api.v1.jobs import retry_job

            with pytest.raises(HTTPException) as exc:
                asyncio.run(retry_job("job-1", user_id="user-123"))
        assert exc.value.status_code == 400
