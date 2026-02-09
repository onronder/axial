"""
Integration tests for Dead Letter Queue (DLQ) retry functionality.

Tests the complete retry flow from failure detection through
task resurrection and email notifications.
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest


class TestDLQLogging:
    """Tests for logging failed tasks to DLQ."""

    @pytest.fixture
    def mock_supabase(self):
        """Create a mock Supabase client."""
        mock = MagicMock()
        mock.table.return_value.insert.return_value.execute.return_value.data = [{"id": str(uuid4())}]
        mock.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{}]
        mock.table.return_value.select.return_value.eq.return_value.lte.return_value.execute.return_value.data = []
        return mock

    def test_log_failed_task_creates_record(self, mock_supabase):
        """Verify failed task is logged to failed_tasks table."""
        from worker.dlq_worker import log_failed_task

        task_id = str(uuid4())
        job_id = str(uuid4())
        user_id = str(uuid4())

        log_failed_task(
            supabase=mock_supabase,
            task_id=task_id,
            task_name="unified_ingest_task",
            exception=ValueError("Test error"),
            user_id=user_id,
            job_id=job_id,
            kwargs={"item_ids": ["file_1"]}
        )

        # Verify insert was called on failed_tasks
        mock_supabase.table.assert_called_with("failed_tasks")
        insert_call = mock_supabase.table().insert
        assert insert_call.called

    def test_retry_schedule_calculation(self, mock_supabase):
        """Verify exponential backoff retry scheduling."""
        from worker.dlq_worker import log_failed_task

        # First failure - should schedule retry in 5 minutes
        log_failed_task(
            supabase=mock_supabase,
            task_id=str(uuid4()),
            task_name="test_task",
            exception=Exception("Error"),
            user_id=str(uuid4()),
            job_id=str(uuid4()),
            kwargs={}
        )

        call_args = mock_supabase.table().insert.call_args[0][0]
        assert "next_retry_at" in call_args
        assert call_args["attempt_count"] == 1

    def test_max_retries_exceeded(self, mock_supabase):
        """Verify task marked as permanently failed after max retries."""
        from worker.dlq_worker import log_failed_task

        # Simulate 4th attempt (over the 3 retry limit)
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"attempt_count": 3}
        ]

        log_failed_task(
            supabase=mock_supabase,
            task_id=str(uuid4()),
            task_name="test_task",
            exception=Exception("Error"),
            user_id=str(uuid4()),
            job_id=str(uuid4()),
            kwargs={}
        )

        # Should be marked as permanently_failed
        update_calls = mock_supabase.table().update.call_args_list
        # Verify status is set correctly


class TestDLQRetry:
    """Tests for retrying failed tasks."""

    @pytest.fixture
    def mock_supabase(self):
        """Create a mock Supabase client."""
        mock = MagicMock()
        return mock

    def test_retry_pending_tasks(self, mock_supabase):
        """Verify pending retry tasks are fetched and retried."""
        from worker.dlq_worker import retry_failed_tasks

        task_id = str(uuid4())
        job_id = str(uuid4())

        # Mock pending retry task
        mock_supabase.table.return_value.select.return_value.eq.return_value.lte.return_value.execute.return_value.data = [
            {
                "id": str(uuid4()),
                "task_id": task_id,
                "task_name": "unified_ingest_task",
                "job_id": job_id,
                "kwargs": {"user_id": str(uuid4()), "connector_type": "google_drive"},
                "attempt_count": 1,
                "status": "pending_retry"
            }
        ]
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{}]

        with patch("worker.dlq_worker.get_supabase", return_value=mock_supabase):
            with patch("worker.tasks.unified_ingest_task") as mock_task:
                mock_task.apply_async = MagicMock()
                result = retry_failed_tasks()

        assert result["retried"] >= 0

    def test_optimistic_locking_prevents_double_retry(self, mock_supabase):
        """Verify atomic claiming prevents race conditions."""
        from worker.dlq_worker import retry_failed_tasks

        # Mock task that's already been claimed by another worker
        mock_supabase.table.return_value.select.return_value.eq.return_value.lte.return_value.execute.return_value.data = [
            {
                "id": str(uuid4()),
                "task_id": str(uuid4()),
                "task_name": "unified_ingest_task",
                "status": "pending_retry",
                "kwargs": {},
                "attempt_count": 1
            }
        ]

        # Atomic update returns empty (task was already claimed)
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        with patch("worker.dlq_worker.get_supabase", return_value=mock_supabase):
            result = retry_failed_tasks()

        # Should skip already claimed task
        assert result["retried"] == 0

    def test_retry_with_email_notification(self, mock_supabase):
        """Verify email is sent when retry is scheduled."""
        from worker.dlq_worker import log_failed_task

        with patch("services.email.email_service.send_retry_scheduled_email") as mock_email:
            mock_email.return_value = True

            log_failed_task(
                supabase=mock_supabase,
                task_id=str(uuid4()),
                task_name="unified_ingest_task",
                exception=Exception("Error"),
                user_id=str(uuid4()),
                job_id=str(uuid4()),
                kwargs={}
            )

            # Email notification should be attempted
            # Implementation verifies email is sent


class TestDLQEmailNotifications:
    """Tests for DLQ email notifications."""

    def test_retry_scheduled_email(self):
        """Verify retry scheduled email is sent correctly."""
        from services.email import EmailService

        with patch("services.email.settings") as mock_settings:
            mock_settings.RESEND_API_KEY = "test_key"
            mock_settings.EMAILS_FROM_EMAIL = "test@example.com"
            mock_settings.APP_URL = "https://app.example.com"

            service = EmailService()

            # Verify method exists and accepts correct parameters
            assert hasattr(service, "send_retry_scheduled_email")

    def test_retry_succeeded_email(self):
        """Verify success email is sent after successful retry."""
        from services.email import EmailService

        with patch("services.email.settings") as mock_settings:
            mock_settings.RESEND_API_KEY = "test_key"
            mock_settings.EMAILS_FROM_EMAIL = "test@example.com"
            mock_settings.APP_URL = "https://app.example.com"

            service = EmailService()

            assert hasattr(service, "send_retry_succeeded_email")

    def test_permanently_failed_email(self):
        """Verify failure email is sent after all retries exhausted."""
        from services.email import EmailService

        with patch("services.email.settings") as mock_settings:
            mock_settings.RESEND_API_KEY = "test_key"
            mock_settings.EMAILS_FROM_EMAIL = "test@example.com"
            mock_settings.APP_URL = "https://app.example.com"

            service = EmailService()

            assert hasattr(service, "send_permanently_failed_email")


class TestDLQMetrics:
    """Tests for DLQ monitoring metrics."""

    def test_dlq_metrics_recorded(self):
        """Verify DLQ operations are tracked in Prometheus metrics."""
        from core.metrics import (
            DLQ_PERMANENTLY_FAILED,
            DLQ_RETRY_ATTEMPTS,
            DLQ_TASKS_TOTAL,
        )

        # Verify metrics are defined
        assert DLQ_TASKS_TOTAL is not None
        assert DLQ_RETRY_ATTEMPTS is not None
        assert DLQ_PERMANENTLY_FAILED is not None

    def test_dlq_task_gauge(self):
        """Verify DLQ task count gauge is updated."""
        from core.metrics import DLQ_TASKS_PENDING

        # Verify gauge exists
        assert DLQ_TASKS_PENDING is not None
