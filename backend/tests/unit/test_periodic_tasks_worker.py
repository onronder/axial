from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from worker import periodic_tasks


def _mock_supabase_with_delete(table_name: str, count: int):
    supabase = MagicMock()
    table_mock = MagicMock()
    table_mock.delete.return_value.eq.return_value.lt.return_value.execute.return_value.data = [1] * count
    table_mock.delete.return_value.in_.return_value.lt.return_value.execute.return_value.data = [1] * count
    table_mock.delete.return_value.lt.return_value.execute.return_value.data = [1] * count
    supabase.table.return_value = table_mock
    return supabase


def test_cleanup_old_jobs_returns_deleted_count():
    supabase = _mock_supabase_with_delete("ingestion_jobs", 3)
    with patch("worker.periodic_tasks.get_supabase", return_value=supabase):
        result = periodic_tasks.cleanup_old_jobs()
    assert result["deleted"] == 3


def test_cleanup_old_jobs_handles_error():
    with patch("worker.periodic_tasks.get_supabase", side_effect=RuntimeError("db")):
        result = periodic_tasks.cleanup_old_jobs()
    assert "error" in result


def test_cleanup_old_file_status_returns_deleted_count():
    supabase = _mock_supabase_with_delete("ingestion_file_status", 2)
    with patch("worker.periodic_tasks.get_supabase", return_value=supabase):
        result = periodic_tasks.cleanup_old_file_status()
    assert result["deleted"] == 2


def test_cleanup_old_file_status_handles_error():
    with patch("worker.periodic_tasks.get_supabase", side_effect=RuntimeError("db")):
        result = periodic_tasks.cleanup_old_file_status()
    assert "error" in result


def test_cleanup_old_audit_logs_returns_deleted_count():
    supabase = _mock_supabase_with_delete("audit_logs", 5)
    with patch("worker.periodic_tasks.get_supabase", return_value=supabase):
        result = periodic_tasks.cleanup_old_audit_logs()
    assert result["deleted"] == 5


def test_cleanup_old_audit_logs_handles_error():
    with patch("worker.periodic_tasks.get_supabase", side_effect=RuntimeError("db")):
        result = periodic_tasks.cleanup_old_audit_logs()
    assert "error" in result


def test_update_memory_metrics_updates_gauges():
    with patch("worker.periodic_tasks.check_memory_usage") as mock_check:
        mock_check.return_value = {"percent": 50.0, "available_mb": 2048, "warning": False, "critical": False}
        with patch("worker.periodic_tasks.psutil.Process") as mock_proc:
            mock_proc.return_value.cpu_percent.return_value = 12.5
            mock_proc.return_value.open_files.return_value = []
            with patch("worker.periodic_tasks.MEMORY_USAGE") as mem_usage, \
                 patch("worker.periodic_tasks.MEMORY_AVAILABLE_MB") as mem_avail, \
                 patch("worker.periodic_tasks.MEMORY_WARNINGS") as mem_warn, \
                 patch("worker.periodic_tasks.MEMORY_CRITICAL") as mem_crit, \
                 patch("worker.periodic_tasks.PROCESS_CPU_PERCENT") as cpu_pct, \
                 patch("worker.periodic_tasks.OPEN_FILES") as open_files:
                result = periodic_tasks.update_memory_metrics()

    mem_usage.set.assert_called_with(50.0)
    mem_avail.set.assert_called_with(2048)
    cpu_pct.set.assert_called_with(12.5)
    open_files.set.assert_called_with(0)
    assert result["percent"] == 50.0


def test_update_memory_metrics_handles_warning_and_critical():
    with patch("worker.periodic_tasks.check_memory_usage") as mock_check:
        mock_check.return_value = {"percent": 95.0, "available_mb": 10, "warning": True, "critical": True}
        with patch("worker.periodic_tasks.psutil.Process") as mock_proc:
            mock_proc.return_value.cpu_percent.return_value = 0.0
            mock_proc.return_value.open_files.return_value = []
            with patch("worker.periodic_tasks.MEMORY_USAGE"), \
                 patch("worker.periodic_tasks.MEMORY_AVAILABLE_MB"), \
                 patch("worker.periodic_tasks.MEMORY_WARNINGS") as mem_warn, \
                 patch("worker.periodic_tasks.MEMORY_CRITICAL") as mem_crit, \
                 patch("worker.periodic_tasks.PROCESS_CPU_PERCENT"), \
                 patch("worker.periodic_tasks.OPEN_FILES"):
                periodic_tasks.update_memory_metrics()

    mem_warn.inc.assert_called_once()
    mem_crit.inc.assert_called_once()


def test_update_memory_metrics_handles_error():
    with patch("worker.periodic_tasks.check_memory_usage", side_effect=RuntimeError("boom")):
        result = periodic_tasks.update_memory_metrics()
    assert "error" in result


def test_retry_failed_tasks_task_invokes_worker():
    with patch("worker.dlq_worker.retry_failed_tasks", return_value={"retried": 1}) as mock_retry:
        result = periodic_tasks.retry_failed_tasks_task()
    assert result["retried"] == 1
    mock_retry.assert_called_once()


def test_reconcile_ingestion_jobs_no_jobs():
    supabase = MagicMock()
    table = MagicMock()
    table.select.return_value.eq.return_value.execute.return_value.data = []
    supabase.table.return_value = table

    with patch("worker.periodic_tasks.get_supabase", return_value=supabase):
        result = periodic_tasks.reconcile_ingestion_jobs()

    assert result["jobs_checked"] == 0
    assert result["jobs_finalized"] == 0


def test_reconcile_ingestion_jobs_skips_invalid_jobs():
    supabase = MagicMock()

    def table_side_effect(name):
        table = MagicMock()
        if name == "ingestion_jobs":
            table.select.return_value.eq.return_value.execute.return_value.data = [
                {"id": None, "user_id": "user-1", "total_files": 1, "status": "processing"},
                {"id": "job-1", "user_id": "user-1", "total_files": 0, "status": "processing"},
            ]
        return table

    supabase.table.side_effect = table_side_effect

    with patch("worker.periodic_tasks.get_supabase", return_value=supabase):
        result = periodic_tasks.reconcile_ingestion_jobs()

    assert result["jobs_checked"] == 2
    assert result["jobs_finalized"] == 0


def test_reconcile_ingestion_jobs_finalizes():
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "job-1", "user_id": "user-1", "total_files": 2, "status": "processing"}
    ]
    supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"status": "completed"},
        {"status": "completed"},
    ]

    def table_side_effect(name):
        table_mock = MagicMock()
        if name == "ingestion_jobs":
            table_mock.select.return_value.eq.return_value.execute.return_value.data = [
                {"id": "job-1", "user_id": "user-1", "total_files": 2, "status": "processing"}
            ]
            return table_mock
        if name == "ingestion_file_status":
            table_mock.select.return_value.eq.return_value.execute.return_value.data = [
                {"status": "completed"},
                {"status": "completed"},
            ]
            return table_mock
        return table_mock

    supabase.table.side_effect = table_side_effect

    with patch("worker.periodic_tasks.get_supabase", return_value=supabase):
        with patch("worker.tasks.finalize_job_task.apply_async") as mock_finalize:
            result = periodic_tasks.reconcile_ingestion_jobs()

    mock_finalize.assert_called_once()
    assert result["jobs_finalized"] == 1


def test_reconcile_ingestion_jobs_handles_error():
    with patch("worker.periodic_tasks.get_supabase", side_effect=RuntimeError("db")):
        result = periodic_tasks.reconcile_ingestion_jobs()
    assert "error" in result
