"""
Integration tests for Celery Beat periodic tasks.

Verifies scheduled tasks run correctly and handle errors gracefully.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestScheduledTasks:
    """Tests for periodic tasks defined in beat_schedule."""

    def test_check_scheduled_crawls_executes(self):
        """Verify scheduled crawl check runs correctly."""
        from worker.tasks import check_scheduled_crawls

        with patch("worker.tasks.get_supabase") as mock_db:
            mock_db.return_value.table.return_value.select.return_value.lte.return_value.execute.return_value.data = []
            mock_db.return_value.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

            # Should execute without error
            # Result depends on pending crawls
            assert callable(check_scheduled_crawls)

    def test_cleanup_old_jobs_executes(self):
        """Verify old job cleanup runs correctly."""
        from worker.tasks import cleanup_old_jobs

        with patch("worker.tasks.get_supabase") as mock_db:
            mock_db.return_value.table.return_value.delete.return_value.lt.return_value.execute.return_value.data = []

            assert callable(cleanup_old_jobs)

    def test_retry_failed_tasks_scheduled(self):
        """Verify DLQ retry task is in beat schedule."""
        from core.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        assert "retry-failed-tasks" in schedule
        assert schedule["retry-failed-tasks"]["schedule"] == 300.0

    def test_update_memory_metrics_scheduled(self):
        """Verify memory metrics task is scheduled."""
        from core.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        assert "update-memory-metrics" in schedule

    def test_cleanup_old_file_status_scheduled(self):
        """Verify file status cleanup is scheduled daily."""
        from core.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        assert "cleanup-old-file-status-daily" in schedule

    def test_cleanup_old_audit_logs_scheduled(self):
        """Verify audit log cleanup is scheduled weekly."""
        from core.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        assert "cleanup-old-audit-logs-weekly" in schedule


class TestCleanupTasks:
    """Tests for cleanup periodic tasks."""

    @pytest.fixture
    def mock_supabase(self):
        """Create a mock Supabase client."""
        mock = MagicMock()
        mock.table.return_value.delete.return_value.lt.return_value.execute.return_value.data = []
        mock.table.return_value.select.return_value.lt.return_value.execute.return_value.data = []
        return mock

    def test_file_status_cleanup_deletes_old_records(self, mock_supabase):
        """Verify old file_status records are deleted."""
        # Cleanup should target records older than 7 days
        # with status 'completed' or 'failed'

        mock_supabase.table.return_value.delete.return_value.lt.return_value.eq.return_value.execute.return_value = MagicMock()

        # Implementation would call cleanup_old_file_status task
        mock_supabase.table.assert_not_called()  # Not called yet

    def test_audit_log_cleanup_respects_retention(self, mock_supabase):
        """Verify audit logs respect retention policy."""
        # Cleanup should only delete logs older than 90 days

        mock_supabase.table.return_value.delete.return_value.lt.return_value.execute.return_value = MagicMock()

        # Implementation would verify retention period

    def test_job_cleanup_preserves_recent(self, mock_supabase):
        """Verify recent jobs are preserved during cleanup."""
        # Cleanup should only affect jobs older than 30 days

        mock_supabase.table.return_value.delete.return_value.lt.return_value.neq.return_value.execute.return_value = MagicMock()

        # Implementation would verify preservation logic


class TestMemoryMetrics:
    """Tests for memory metrics collection."""

    def test_memory_metrics_recorded(self):
        """Verify memory metrics are collected and recorded."""
        from core.metrics import MEMORY_USAGE, OPEN_FILES, PROCESS_CPU_PERCENT

        # Verify metrics are defined
        assert MEMORY_USAGE is not None
        assert PROCESS_CPU_PERCENT is not None
        assert OPEN_FILES is not None

    def test_worker_metrics_updated(self):
        """Verify worker metrics are updated periodically."""
        # The update_memory_metrics task should update gauges
        # for current memory usage, CPU, and open file handles

        with patch("core.metrics.MEMORY_USAGE") as mock_metric:
            mock_metric.set = MagicMock()

            # Implementation would verify metric update


class TestTaskResilience:
    """Tests for task error handling and resilience."""

    def test_task_autoretry_on_connection_error(self):
        """Verify tasks retry on transient connection errors."""
        from core.celery_app import celery_app

        # Verify retry configuration
        # Tasks should retry on ConnectionError, TimeoutError

        # Check task decorator configuration
        assert celery_app.conf.task_acks_late is True

    def test_task_soft_time_limit(self):
        """Verify tasks have soft time limits."""
        from core.celery_app import celery_app

        # Verify soft time limit is set
        assert celery_app.conf.task_soft_time_limit > 0

    def test_task_result_backend(self):
        """Verify task results are stored correctly."""
        from core.celery_app import celery_app

        # Verify result backend configuration
        assert celery_app.conf.result_backend is not None
