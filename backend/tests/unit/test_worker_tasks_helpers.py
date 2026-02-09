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

    result = tasks.create_file_status(supabase, "job-1", "user-1", "org-1", "file.txt", 10)
    assert result == "status-1"


def test_update_file_status_caps_progress():
    """Test that progress is capped at 100."""
    supabase = MagicMock()

    # Mock RPC to return True (update successful) but also verify the capped progress is passed
    rpc_mock = MagicMock()
    rpc_mock.execute.return_value = MagicMock(data=True)
    supabase.rpc.return_value = rpc_mock

    tasks.update_file_status(supabase, "status-1", progress=150)

    # Verify RPC was called
    supabase.rpc.assert_called_once()

    # Verify the progress was capped to 100 when passed to RPC
    call_args = supabase.rpc.call_args
    assert call_args[0][0] == "update_file_status_if_changed"
    params = call_args[0][1]
    assert params["p_progress"] == 100  # Capped from 150 to 100


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


# ============================================================
# Tests for org/scope validation
# ============================================================

class TestOrgScopeValidation:
    """Tests for _validate_org_scope_consistency function."""

    def test_validate_org_scope_valid(self):
        """Valid UUIDs pass validation without error."""
        org_id = "11111111-1111-1111-1111-111111111111"
        scope_id = "github://owner/repo"

        # Should not raise
        tasks._validate_org_scope_consistency(org_id, scope_id, "test_context")

    def test_validate_org_scope_missing_org_id(self):
        """Missing org_id raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            tasks._validate_org_scope_consistency(None, "github://owner/repo", "test_context")

        assert "organization_id is required" in str(exc_info.value)
        assert "test_context" in str(exc_info.value)

    def test_validate_org_scope_empty_org_id(self):
        """Empty org_id raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            tasks._validate_org_scope_consistency("", "github://owner/repo", "test_context")

        assert "organization_id is required" in str(exc_info.value)

    def test_validate_org_scope_missing_scope_id(self):
        """Missing scope_id raises ValueError."""
        org_id = "11111111-1111-1111-1111-111111111111"

        with pytest.raises(ValueError) as exc_info:
            tasks._validate_org_scope_consistency(org_id, None, "test_context")

        assert "scope_id is required" in str(exc_info.value)
        assert "test_context" in str(exc_info.value)

    def test_validate_org_scope_empty_scope_id(self):
        """Empty scope_id raises ValueError."""
        org_id = "11111111-1111-1111-1111-111111111111"

        with pytest.raises(ValueError) as exc_info:
            tasks._validate_org_scope_consistency(org_id, "", "test_context")

        assert "scope_id is required" in str(exc_info.value)

    def test_validate_org_scope_invalid_uuid(self):
        """Invalid org_id UUID format raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            tasks._validate_org_scope_consistency("not-a-uuid", "github://owner/repo", "test_context")

        assert "Invalid organization_id format" in str(exc_info.value)

    def test_validate_org_scope_context_in_error(self):
        """Context string is included in error messages."""
        context = "unified_ingest_task:abc123"

        with pytest.raises(ValueError) as exc_info:
            tasks._validate_org_scope_consistency(None, "github://owner/repo", context)

        assert context in str(exc_info.value)


class TestEnsureScopeIdentityPlaceholder:
    """Tests for _ensure_scope_identity_placeholder function."""

    def test_ensure_placeholder_empty_scope_returns_false(self):
        """Empty scope_id raises ValueError without DB call."""
        supabase = MagicMock()
        with pytest.raises(ValueError):
            tasks._ensure_scope_identity_placeholder(
                supabase=supabase,
                organization_id="11111111-1111-1111-1111-111111111111",
                user_id="22222222-2222-2222-2222-222222222222",
                scope_id="",
            )
        supabase.table.assert_not_called()

    def test_ensure_placeholder_none_scope_returns_false(self):
        """None scope_id raises ValueError without DB call."""
        supabase = MagicMock()
        with pytest.raises(ValueError):
            tasks._ensure_scope_identity_placeholder(
                supabase=supabase,
                organization_id="11111111-1111-1111-1111-111111111111",
                user_id="22222222-2222-2222-2222-222222222222",
                scope_id=None,
            )
        supabase.table.assert_not_called()

    def test_ensure_placeholder_creates_record(self):
        """Valid inputs create scope identity placeholder."""
        supabase = MagicMock()
        supabase.rpc.return_value.execute.return_value = MagicMock(data="created")

        result = tasks._ensure_scope_identity_placeholder(
            supabase=supabase,
            organization_id="11111111-1111-1111-1111-111111111111",
            user_id="22222222-2222-2222-2222-222222222222",
            scope_id="github://owner/repo",
            source_type="github",
        )

        assert result == "created"
        supabase.rpc.assert_called_once()

    def test_ensure_placeholder_handles_upsert_error_with_existing_check(self):
        """On upsert error, checks if placeholder exists (race condition)."""
        supabase = MagicMock()

        # RPC fails, fallback upsert fails, select finds existing
        supabase.rpc.return_value.execute.side_effect = Exception("rpc down")
        supabase.table.return_value.upsert.return_value.execute.side_effect = Exception("conflict")
        supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": "github://owner/repo"}]
        )

        result = tasks._ensure_scope_identity_placeholder(
            supabase=supabase,
            organization_id="11111111-1111-1111-1111-111111111111",
            user_id="22222222-2222-2222-2222-222222222222",
            scope_id="github://owner/repo",
        )

        # Should return exists because placeholder was found via select
        assert result == "exists"

    def test_ensure_placeholder_invalid_org_id_raises(self):
        """Invalid org_id raises ValueError."""
        supabase = MagicMock()

        with pytest.raises(ValueError) as exc_info:
            tasks._ensure_scope_identity_placeholder(
                supabase=supabase,
                organization_id="not-a-uuid",
                user_id="22222222-2222-2222-2222-222222222222",
                scope_id="github://owner/repo",
            )

        assert "Invalid organization_id format" in str(exc_info.value)
