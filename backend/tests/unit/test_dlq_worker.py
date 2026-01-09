from unittest.mock import MagicMock, Mock, patch

import pytest

from worker import dlq_worker


def _make_table(result_data=None, execute_side_effect=None):
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.lte.return_value = table
    table.update.return_value = table
    table.insert.return_value = table
    if execute_side_effect is not None:
        table.execute.side_effect = execute_side_effect
    else:
        table.execute.return_value = Mock(data=result_data)
    return table


class TestRedaction:
    def test_redact_payload_masks_sensitive_keys(self):
        payload = {
            "token": "secret",
            "nested": {"password": "pw", "ok": True},
            "items": [{"authorization": "auth", "value": 1}],
        }

        redacted = dlq_worker.redact_payload(payload)

        assert redacted["token"] == "<redacted>"
        assert redacted["nested"]["password"] == "<redacted>"
        assert redacted["items"][0]["authorization"] == "<redacted>"

    def test_redact_value_bytes_and_str(self):
        assert dlq_worker._redact_value(b"secret") == "<redacted:6 bytes>"
        assert dlq_worker._redact_value("secret") == "<redacted>"

    def test_redact_value_other_types(self):
        assert dlq_worker._redact_value(123) == "<redacted>"

    def test_redact_payload_tuple(self):
        payload = ({"token": "secret"},)
        redacted = dlq_worker.redact_payload(payload)
        assert isinstance(redacted, list)
        assert redacted[0]["token"] == "<redacted>"


class TestLogTaskFailure:
    def test_log_task_failure_inserts_new_record(self):
        supabase = MagicMock()
        table = _make_table(result_data=[])
        supabase.table.return_value = table

        dlq_worker.log_task_failure(
            task_id="task-1",
            task_name="unified_ingest_task",
            args=(),
            kwargs={"token": "secret"},
            exc=Exception("boom"),
            traceback_str="trace",
            user_id="user-1",
            job_id="job-1",
            supabase_client=supabase,
        )

        table.insert.assert_called_once()
        insert_payload = table.insert.call_args[0][0]
        assert insert_payload["status"] == "pending_retry"

    def test_log_task_failure_updates_existing_record(self):
        supabase = MagicMock()
        existing = [{"attempt_count": 3}]
        table = _make_table(result_data=existing)
        supabase.table.return_value = table

        dlq_worker.log_task_failure(
            task_id="task-1",
            task_name="unified_ingest_task",
            args=(),
            kwargs={},
            exc=Exception("boom"),
            traceback_str="trace",
            supabase_client=supabase,
        )

        table.update.assert_called_once()
        update_payload = table.update.call_args[0][0]
        assert update_payload["status"] == "permanently_failed"

    def test_log_task_failure_schedules_retry(self):
        supabase = MagicMock()
        existing = [{"attempt_count": 1}]
        table = _make_table(result_data=existing)
        supabase.table.return_value = table

        dlq_worker.log_task_failure(
            task_id="task-1",
            task_name="unified_ingest_task",
            args=(),
            kwargs={},
            exc=Exception("boom"),
            traceback_str="trace",
            supabase_client=supabase,
        )

        update_payload = table.update.call_args[0][0]
        assert update_payload["status"] == "pending_retry"

    def test_log_task_failure_handles_exception(self):
        supabase = MagicMock()
        table = _make_table(execute_side_effect=Exception("boom"))
        supabase.table.return_value = table

        dlq_worker.log_task_failure(
            task_id="task-1",
            task_name="unified_ingest_task",
            args=(),
            kwargs={},
            exc=Exception("boom"),
            traceback_str="trace",
            supabase_client=supabase,
        )

    def test_log_failed_task_wrapper(self):
        supabase = MagicMock()
        with patch("worker.dlq_worker.log_task_failure") as log_mock:
            dlq_worker.log_failed_task(
                supabase,
                task_id="task-1",
                task_name="unified_ingest_task",
                exception=Exception("boom"),
            )

        log_mock.assert_called_once()


class TestRetryFailedTasks:
    def test_retry_failed_tasks_empty(self):
        supabase = MagicMock()
        table = _make_table(result_data=[])
        supabase.table.return_value = table

        with patch("worker.dlq_worker.get_supabase", return_value=supabase):
            result = dlq_worker.retry_failed_tasks()

        assert result["retried"] == 0
        assert result["failed"] == 0

    def test_retry_failed_tasks_dispatches(self):
        tasks = [
            {
                "id": "row-1",
                "task_id": "task-1",
                "task_name": "unified_ingest_task",
                "attempt_count": 1,
                "kwargs": {"user_id": "user-1", "job_id": "job-1"},
            }
        ]
        table = _make_table(
            execute_side_effect=[
                Mock(data=tasks),
                Mock(data=[{"id": "row-1"}]),
            ]
        )
        supabase = MagicMock()
        supabase.table.return_value = table

        with patch("worker.dlq_worker.get_supabase", return_value=supabase), \
             patch("worker.tasks.unified_ingest_task") as task_mock:
            result = dlq_worker.retry_failed_tasks()

        task_mock.apply_async.assert_called_once()
        assert result["retried"] == 1

    def test_retry_failed_tasks_claimed_by_other_worker(self):
        tasks = [
            {"id": "row-1", "task_id": "task-1", "task_name": "unified_ingest_task", "attempt_count": 1, "kwargs": {}}
        ]
        table = _make_table(
            execute_side_effect=[
                Mock(data=tasks),
                Mock(data=[]),
            ]
        )
        supabase = MagicMock()
        supabase.table.return_value = table

        with patch("worker.dlq_worker.get_supabase", return_value=supabase):
            result = dlq_worker.retry_failed_tasks()

        assert result["retried"] == 0

    def test_retry_failed_tasks_unknown_task_type(self):
        tasks = [
            {"id": "row-1", "task_id": "task-1", "task_name": "other_task", "attempt_count": 1, "kwargs": {}}
        ]
        table = _make_table(
            execute_side_effect=[
                Mock(data=tasks),
                Mock(data=[{"id": "row-1"}]),
            ]
        )
        supabase = MagicMock()
        supabase.table.return_value = table

        with patch("worker.dlq_worker.get_supabase", return_value=supabase):
            result = dlq_worker.retry_failed_tasks()

        assert result["failed"] == 1

    def test_retry_failed_tasks_handles_task_error(self):
        tasks = [
            {"id": "row-1", "task_id": "task-1", "task_name": "unified_ingest_task", "attempt_count": 1, "kwargs": {}}
        ]
        table = _make_table(
            execute_side_effect=[
                Mock(data=tasks),
                Mock(data=[{"id": "row-1"}]),
                Mock(data=[{"id": "row-1"}]),
            ]
        )
        supabase = MagicMock()
        supabase.table.return_value = table

        with patch("worker.dlq_worker.get_supabase", return_value=supabase), \
             patch("worker.tasks.unified_ingest_task.apply_async", side_effect=Exception("boom")):
            result = dlq_worker.retry_failed_tasks()

        assert result["failed"] == 1

    def test_retry_failed_tasks_handles_error(self):
        with patch("worker.dlq_worker.get_supabase", side_effect=Exception("boom")):
            result = dlq_worker.retry_failed_tasks()

        assert result["failed"] == 0
