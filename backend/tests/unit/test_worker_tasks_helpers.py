import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from worker import tasks


def test_get_parse_timeout_seconds_pdf_uses_ocr():
    with patch.object(tasks.settings, "LLAMA_CLOUD_API_KEY", "key"), \
         patch.object(tasks.settings, "PDF_PARSE_TIMEOUT_OCR", 600):
        assert tasks.get_parse_timeout_seconds("file.pdf", None) == 600


def test_get_parse_timeout_seconds_text():
    with patch.object(tasks.settings, "TEXT_PARSE_TIMEOUT", 60):
        assert tasks.get_parse_timeout_seconds("note.txt", "text/plain") == 60


def test_update_job_progress_updates_table_and_metrics():
    supabase = MagicMock()
    table = MagicMock()
    table.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])
    supabase.table.return_value = table

    metric = MagicMock()
    metric.labels.return_value.inc = MagicMock()

    with patch("worker.tasks.status_updates_total", metric), \
         patch("worker.tasks.record_ingest_job_update") as record_update:
        tasks.update_job_progress(supabase, "job-1", 50, message="Halfway")

    table.update.assert_called_once()
    record_update.assert_called_once_with("job-1")


def test_should_emit_job_progress_update_uses_redis_throttle():
    fake_client = SimpleNamespace(set=lambda *args, **kwargs: True)
    fake_redis = SimpleNamespace(from_url=lambda url: fake_client)

    with patch.dict(sys.modules, {"redis": fake_redis}), \
         patch.object(tasks.settings, "REDIS_URL", "redis://localhost"), \
         patch.object(tasks.settings, "REDIS_JOB_PROGRESS_UPDATE_INTERVAL", 10), \
         patch.object(tasks.settings, "REDIS_JOB_PROGRESS_UPDATE_BATCH", 5):
        assert tasks._should_emit_job_progress_update("job-1", processed=2, total=10) is True


def test_update_job_progress_from_counters_calls_update():
    supabase = MagicMock()
    with patch("worker.tasks._should_emit_job_progress_update", return_value=True), \
         patch("worker.tasks.update_job_status") as update_job_status:
        tasks._update_job_progress_from_counters(
            supabase,
            "job-1",
            {"total": 4, "processed": 2, "failed": 1, "skipped": 1},
        )
    update_job_status.assert_called_once()


def test_get_ingestion_counts_from_db():
    supabase = MagicMock()
    table = MagicMock()
    table.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[
            {"status": "completed"},
            {"status": "failed"},
            {"status": "skipped"},
        ]
    )
    supabase.table.return_value = table

    counts = tasks._get_ingestion_counts_from_db(supabase, "job-1")
    assert counts["success"] == 1
    assert counts["failed"] == 1
    assert counts["skipped"] == 1
    assert counts["processed"] == 3


def test_record_ingest_outcome_triggers_finalize():
    supabase = MagicMock()
    with patch("worker.tasks.record_ingest_outcome", return_value={"total": 1, "processed": 1}), \
         patch("worker.tasks._update_job_progress_from_counters") as update_progress, \
         patch("worker.tasks.mark_ingest_job_finalizing", return_value=True), \
         patch("worker.tasks.finalize_job_task.apply_async") as finalize_async:
        tasks._record_ingest_outcome_and_maybe_finalize(
            supabase,
            "user-1",
            "job-1",
            "file-1",
            "completed",
        )

    update_progress.assert_called_once()
    finalize_async.assert_called_once()


def test_record_crawl_outcome_triggers_finalize():
    supabase = MagicMock()
    with patch("worker.tasks.record_crawl_outcome", return_value={"total": 1, "processed": 1}), \
         patch("worker.tasks.mark_crawl_finalizing", return_value=True), \
         patch("worker.tasks.finalize_crawl_task.apply_async") as finalize_async:
        tasks._record_crawl_outcome_and_maybe_finalize(
            supabase,
            "user-1",
            "crawl-1",
            "https://example.com",
            "completed",
        )

    finalize_async.assert_called_once()


def test_create_file_status_returns_id():
    supabase = MagicMock()
    supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "status-1"}]
    )

    result = tasks.create_file_status(supabase, "job-1", "user-1", "file.txt", 10)
    assert result == "status-1"


def test_update_file_status_caps_progress():
    supabase = MagicMock()
    table = MagicMock()
    table.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])
    supabase.table.return_value = table

    tasks.update_file_status(supabase, "status-1", progress=150)
    update_data = table.update.call_args[0][0]
    assert update_data["progress"] == 100


def test_check_job_cancelled_true():
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"status": "cancelled"}
    )

    assert tasks.check_job_cancelled(supabase, "job-1") is True


def test_store_celery_task_id_updates_job():
    supabase = MagicMock()
    supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])

    tasks.store_celery_task_id(supabase, "job-1", "task-1")
    supabase.table.return_value.update.assert_called_once()
