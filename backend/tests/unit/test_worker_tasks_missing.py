import base64
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest

import worker.tasks as tasks


class DummyTask:
    def __init__(self, task_id="task-1"):
        self.request = SimpleNamespace(id=task_id)
        self.name = "dummy"


def _make_table(data=None):
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.neq.return_value = table
    table.single.return_value = table
    table.order.return_value = table
    table.limit.return_value = table
    table.update.return_value = table
    table.insert.return_value = table
    table.delete.return_value = table
    table.execute.return_value = Mock(data=data)
    return table


def test_collect_documents_sync_requires_sync_fetch():
    connector = SimpleNamespace()
    with pytest.raises(RuntimeError):
        tasks._collect_documents_sync(connector, ["item"], None, "user-1")


def test_collect_documents_sync_rejects_coroutine_function():
    async def fetch_documents_sync(_item_ids, _credentials, user_id=None):
        return []

    connector = SimpleNamespace(fetch_documents_sync=fetch_documents_sync)
    with pytest.raises(RuntimeError):
        tasks._collect_documents_sync(connector, ["item"], None, "user-1")


def test_collect_documents_sync_rejects_async_results():
    async def _gen():
        yield "doc"

    def fetch_documents_sync(_item_ids, _credentials, user_id=None):
        return _gen()

    connector = SimpleNamespace(fetch_documents_sync=fetch_documents_sync)
    with pytest.raises(RuntimeError):
        tasks._collect_documents_sync(connector, ["item"], None, "user-1")


def test_update_job_status_sets_failed_files():
    supabase = MagicMock()
    table = _make_table([])
    supabase.table.return_value = table

    tasks.update_job_status(supabase, "job-1", "processing", failed_files=2)

    payload = table.update.call_args[0][0]
    assert payload["failed_files"] == 2


def test_update_job_status_handles_error():
    supabase = MagicMock()
    table = _make_table([])
    table.execute.side_effect = Exception("boom")
    supabase.table.return_value = table

    tasks.update_job_status(supabase, "job-1", "processing")


def test_update_job_progress_handles_error():
    supabase = MagicMock()
    table = _make_table([])
    table.execute.side_effect = Exception("boom")
    supabase.table.return_value = table

    tasks.update_job_progress(supabase, "job-1", 50)


def test_should_emit_job_progress_update_branches(monkeypatch):
    assert tasks._should_emit_job_progress_update("job-1", 0, 0) is False
    assert tasks._should_emit_job_progress_update("job-1", 5, 5) is True
    assert tasks._should_emit_job_progress_update("job-1", 1, 10) is True

    with patch("redis.from_url") as from_url, \
         patch("worker.tasks.settings.REDIS_JOB_PROGRESS_UPDATE_BATCH", 5):
        from_url.return_value.set.return_value = True
        assert tasks._should_emit_job_progress_update("job-1", 2, 10) is True

    with patch("redis.from_url", side_effect=Exception("boom")), \
         patch("worker.tasks.settings.REDIS_JOB_PROGRESS_UPDATE_BATCH", 5):
        assert tasks._should_emit_job_progress_update("job-1", 2, 10) is False


def test_update_job_progress_from_counters_returns_early(monkeypatch):
    supabase = MagicMock()

    tasks._update_job_progress_from_counters(supabase, "job-1", {})
    tasks._update_job_progress_from_counters(supabase, "job-1", {"total": 0, "processed": 1})

    with patch("worker.tasks._should_emit_job_progress_update", return_value=False):
        tasks._update_job_progress_from_counters(supabase, "job-1", {"total": 10, "processed": 2})


def test_record_ingest_outcome_early_returns(monkeypatch):
    supabase = MagicMock()
    tasks._record_ingest_outcome_and_maybe_finalize(supabase, "user-1", None, None, "success")

    with patch("worker.tasks.record_ingest_outcome", return_value=None), \
         patch("worker.tasks.job_counters_missing") as missing:
        missing.labels.return_value = missing
        tasks._record_ingest_outcome_and_maybe_finalize(supabase, "user-1", "job-1", "file-1", "success")
        missing.inc.assert_called_once()


def test_record_ingest_outcome_handles_total_lookup_failure(monkeypatch):
    supabase = MagicMock()
    table = _make_table([])
    table.execute.side_effect = Exception("boom")
    supabase.table.return_value = table

    with patch("worker.tasks.record_ingest_outcome", return_value={"total": 0, "processed": 1, "failed": 0, "skipped": 0}):
        tasks._record_ingest_outcome_and_maybe_finalize(supabase, "user-1", "job-1", "file-1", "success")


def test_record_ingest_outcome_loads_total_from_db(monkeypatch):
    supabase = MagicMock()
    table = _make_table({"total_files": 3})
    supabase.table.return_value = table

    with patch("worker.tasks.record_ingest_outcome", return_value={"total": 0, "processed": 1, "failed": 0, "skipped": 0}):
        tasks._record_ingest_outcome_and_maybe_finalize(supabase, "user-1", "job-1", "file-1", "success")


def test_record_crawl_outcome_early_returns(monkeypatch):
    supabase = MagicMock()
    tasks._record_crawl_outcome_and_maybe_finalize(supabase, "user-1", None, "url", "success")

    with patch("worker.tasks.record_crawl_outcome", return_value=None), \
         patch("worker.tasks.job_counters_missing") as missing:
        missing.labels.return_value = missing
        tasks._record_crawl_outcome_and_maybe_finalize(supabase, "user-1", "crawl-1", "url", "success")
        missing.inc.assert_called_once()


def test_record_crawl_outcome_handles_total_lookup_failure(monkeypatch):
    supabase = MagicMock()
    table = _make_table([])
    table.execute.side_effect = Exception("boom")
    supabase.table.return_value = table

    with patch("worker.tasks.record_crawl_outcome", return_value={"total": 0, "processed": 1}):
        tasks._record_crawl_outcome_and_maybe_finalize(supabase, "user-1", "crawl-1", "url", "success")


def test_record_crawl_outcome_loads_total_from_db(monkeypatch):
    supabase = MagicMock()
    table = _make_table({"total_pages_found": 2})
    supabase.table.return_value = table

    with patch("worker.tasks.record_crawl_outcome", return_value={"total": 0, "processed": 1}):
        tasks._record_crawl_outcome_and_maybe_finalize(supabase, "user-1", "crawl-1", "url", "success")


def test_ingest_document_batched_no_chunks():
    supabase = MagicMock()
    table = _make_table([{"id": "doc-1"}])
    supabase.table.return_value = table

    doc_id = tasks.ingest_document_batched(
        supabase=supabase,
        user_id="user-1",
        organization_id="org-1",
        doc_title="Doc",
        source_type="file_upload",
        metadata={},
        chunks_payload=[],
        file_size_bytes=1,
    )

    assert doc_id == "doc-1"


def test_ingest_document_batched_insert_error(monkeypatch):
    supabase = MagicMock()
    table = _make_table([{"id": "doc-1"}])
    supabase.table.return_value = table

    monkeypatch.setattr(tasks, "insert_rows_with_retry", lambda *_args, **_kwargs: (_ for _ in ()).throw(Exception("boom")))

    doc_id = tasks.ingest_document_batched(
        supabase=supabase,
        user_id="user-1",
        organization_id="org-1",
        doc_title="Doc",
        source_type="file_upload",
        metadata={},
        chunks_payload=[{"content": "x", "embedding": [0.1], "chunk_index": 0, "metadata": {}}],
        file_size_bytes=1,
    )

    assert doc_id == "doc-1"


def test_create_file_status_returns_none_on_empty():
    supabase = MagicMock()
    table = _make_table([])
    supabase.table.return_value = table
    assert tasks.create_file_status(supabase, "job-1", "user-1", "file.txt") is None


def test_create_file_status_handles_exception():
    supabase = MagicMock()
    table = _make_table([])
    table.execute.side_effect = Exception("boom")
    supabase.table.return_value = table
    assert tasks.create_file_status(supabase, "job-1", "user-1", "file.txt") is None


def test_update_file_status_no_id():
    tasks.update_file_status(MagicMock(), None)


def test_update_file_status_handles_error():
    supabase = MagicMock()
    table = _make_table([])
    table.execute.side_effect = Exception("boom")
    supabase.table.return_value = table

    tasks.update_file_status(supabase, "status-1", error="fail")


def test_check_job_cancelled_handles_none():
    assert tasks.check_job_cancelled(MagicMock(), None) is False


def test_check_job_cancelled_handles_exception():
    supabase = MagicMock()
    table = _make_table([])
    table.execute.side_effect = Exception("boom")
    supabase.table.return_value = table
    assert tasks.check_job_cancelled(supabase, "job-1") is False


def test_store_celery_task_id_handles_error():
    supabase = MagicMock()
    table = _make_table([])
    table.execute.side_effect = Exception("boom")
    supabase.table.return_value = table
    tasks.store_celery_task_id(supabase, "job-1", "task-1")


def test_create_notification_handles_pref_error():
    supabase = MagicMock()
    settings_table = _make_table([])
    settings_table.execute.side_effect = Exception("boom")
    settings_table.maybe_single.return_value = settings_table
    supabase.table.return_value = settings_table

    tasks.create_notification(
        supabase,
        "user-1",
        "Title",
        check_setting_key="email_on_ingestion_complete",
    )


def test_send_email_notification_handles_profile_variants():
    supabase = MagicMock()
    table = _make_table(SimpleNamespace(data={"display_name": "User", "email": "u@example.com"}))
    supabase.table.return_value = table

    with patch("worker.tasks.email_service.send_ingestion_complete"):
        tasks.send_email_notification(supabase, "user-1", 1)


def test_send_email_notification_handles_auth_error():
    supabase = MagicMock()
    profile_table = _make_table({"display_name": "User"})
    settings_table = _make_table([])
    supabase.table.side_effect = lambda name: profile_table if name == "user_profiles" else settings_table
    supabase.auth.admin.get_user_by_id.side_effect = Exception("boom")

    tasks.send_email_notification(supabase, "user-1", 1)


def test_send_email_notification_settings_error():
    supabase = MagicMock()
    profile_table = _make_table({"display_name": "User", "email": "u@example.com"})
    settings_table = _make_table([])
    settings_table.execute.side_effect = Exception("boom")
    settings_table.maybe_single.return_value = settings_table
    supabase.table.side_effect = lambda name: profile_table if name == "user_profiles" else settings_table

    with patch("worker.tasks.email_service.send_ingestion_complete"):
        tasks.send_email_notification(supabase, "user-1", 1)


def test_send_failure_email_notification_paths():
    supabase = MagicMock()
    profile_table = _make_table([])
    profile_table.execute.side_effect = Exception("boom")
    settings_table = _make_table([])
    supabase.table.side_effect = lambda name: profile_table if name == "user_profiles" else settings_table
    supabase.auth.admin.get_user_by_id.side_effect = Exception("boom")

    tasks.send_failure_email_notification(supabase, "user-1", "file.txt", "error")


def test_send_failure_email_notification_settings_error():
    supabase = MagicMock()
    profile_table = _make_table({"display_name": "User", "full_name": "User"})
    settings_table = _make_table([])
    settings_table.execute.side_effect = Exception("boom")
    settings_table.maybe_single.return_value = settings_table
    supabase.table.side_effect = lambda name: profile_table if name == "user_profiles" else settings_table
    supabase.auth.admin.get_user_by_id.return_value = SimpleNamespace(user=SimpleNamespace(email="u@example.com"))

    with patch("worker.tasks.email_service.send_ingestion_failed"):
        tasks.send_failure_email_notification(supabase, "user-1", "file.txt", "error")


def test_send_failure_email_notification_disabled():
    supabase = MagicMock()
    profile_table = _make_table({"display_name": "User", "full_name": "User"})
    settings_table = _make_table({"enabled": False})
    settings_table.maybe_single.return_value = settings_table
    supabase.table.side_effect = lambda name: profile_table if name == "user_profiles" else settings_table
    supabase.auth.admin.get_user_by_id.return_value = SimpleNamespace(user=SimpleNamespace(email="u@example.com"))

    tasks.send_failure_email_notification(supabase, "user-1", "file.txt", "error")


def test_send_failure_email_notification_handles_exception():
    supabase = MagicMock()
    profile_table = _make_table({"display_name": "User", "full_name": "User"})
    settings_table = _make_table({"enabled": True})
    settings_table.maybe_single.return_value = settings_table
    supabase.table.side_effect = lambda name: profile_table if name == "user_profiles" else settings_table
    supabase.auth.admin.get_user_by_id.return_value = SimpleNamespace(user=SimpleNamespace(email="u@example.com"))

    with patch("worker.tasks.email_service.send_ingestion_failed", side_effect=Exception("boom")):
        tasks.send_failure_email_notification(supabase, "user-1", "file.txt", "error")


def test_sanitize_text_returns_value():
    assert tasks._sanitize_text("hello") == "hello"


def test_sanitize_text_returns_empty_value():
    assert tasks._sanitize_text("") == ""


def test_process_document_pipeline_handles_string_content(monkeypatch):
    supabase = MagicMock()

    result = SimpleNamespace(
        file_type="unsupported",
        chunks=[],
        metadata={"unsupported_reason": "binary_content"},
        total_tokens=0,
    )

    monkeypatch.setattr(tasks, "DocumentProcessorFactory", SimpleNamespace(process=lambda **_kwargs: result))
    monkeypatch.setattr(tasks, "update_file_status", lambda *_args, **_kwargs: None)

    outcome = tasks.process_document_pipeline(
        supabase,
        content="text",
        filename="file.bin",
        user_id="user-1",
        job_id="job-1",
        file_status_id="status-1",
        source_type="file_upload",
        metadata={"organization_id": "org-1", "scope_id": "file_upload://file.bin"},
    )

    assert outcome.success is True


def test_process_document_pipeline_skips_none_embeddings(monkeypatch):
    supabase = MagicMock()

    chunk = SimpleNamespace(content="hi", token_count=1, chunk_index=0, metadata={})
    result = SimpleNamespace(
        file_type="text",
        chunks=[chunk],
        metadata={},
        total_tokens=1,
    )

    monkeypatch.setattr(tasks, "DocumentProcessorFactory", SimpleNamespace(process=lambda **_kwargs: result))
    monkeypatch.setattr(tasks, "generate_embeddings_batch_sync", lambda *_args, **_kwargs: [None])
    monkeypatch.setattr(tasks, "ingest_document_batched", lambda **_kwargs: "doc-1")
    monkeypatch.setattr(tasks, "update_file_status", lambda *_args, **_kwargs: None)

    outcome = tasks.process_document_pipeline(
        supabase,
        content=b"hi",
        filename="file.txt",
        user_id="user-1",
        job_id="job-1",
        file_status_id="status-1",
        source_type="file_upload",
        metadata={"organization_id": "org-1", "scope_id": "file_upload://file.txt"},
    )

    assert outcome.success is True


def test_unified_ingest_task_cancelled(monkeypatch):
    supabase = MagicMock()

    monkeypatch.setattr(tasks, "get_supabase", lambda: supabase)
    monkeypatch.setattr(tasks, "store_celery_task_id", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(tasks, "check_job_cancelled", lambda *_args, **_kwargs: True)

    result = tasks.unified_ingest_task.run("user-1", "job-1", "file_upload", ["item"], {})

    assert result["status"] == "cancelled"


def test_unified_ingest_task_base64_fallback(monkeypatch):
    supabase = MagicMock()
    table = _make_table([{"id": "status-1"}])
    supabase.table.return_value = table

    def fetch_docs(*_args, **_kwargs):
        yield SimpleNamespace(
            filename="file.bin",
            content="notbase64",
            size_bytes=1,
            mime_type="application/octet-stream",
            metadata={"storage_path": "uploads/file.bin", "scope_id": "file_upload://uploads/file.bin"},
            source_type="file_upload",
            source_id="src-1",
            parent_id=None,
        )

    connector = SimpleNamespace(fetch_documents_sync=fetch_docs)

    class FakeGroup:
        def apply_async(self):
            return SimpleNamespace(id="group-1")

    class DummyContext:
        def __enter__(self):
            return None

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(tasks, "get_supabase", lambda: supabase)
    monkeypatch.setattr(tasks, "get_connector", lambda *_args, **_kwargs: connector)
    monkeypatch.setattr(tasks, "connector_fetch_limit", lambda *_args, **_kwargs: DummyContext())
    monkeypatch.setattr(tasks, "init_ingest_job_counters", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(tasks, "store_celery_task_id", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(tasks, "check_job_cancelled", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(tasks, "update_job_status", lambda *_args, **_kwargs: None)

    with patch("celery.group", return_value=FakeGroup()):
        result = tasks.unified_ingest_task.run("user-1", "job-1", "file_upload", ["item"], {})

    assert result["status"] == "dispatched"


def test_process_file_task_handles_string_content(monkeypatch):
    supabase = MagicMock()
    supabase.storage.from_.return_value.download.return_value = "text"
    supabase.storage.from_.return_value.remove.side_effect = Exception("boom")

    chunk = SimpleNamespace(content="hi", token_count=1, chunk_index=0, metadata={})
    result = SimpleNamespace(file_type="text", chunks=[chunk], metadata={})

    monkeypatch.setattr(tasks, "get_supabase", lambda: supabase)
    monkeypatch.setattr(tasks, "DocumentProcessorFactory", SimpleNamespace(process=lambda **_kwargs: result))
    monkeypatch.setattr(tasks, "generate_embeddings_batch_sync", lambda *_args, **_kwargs: [[0.1]])
    monkeypatch.setattr(tasks, "insert_rows_with_retry", lambda *_args, **_kwargs: (_ for _ in ()).throw(Exception("boom")))
    monkeypatch.setattr(tasks, "update_file_status", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(tasks, "_record_ingest_outcome_and_maybe_finalize", lambda *_args, **_kwargs: None)

    with patch("os.path.exists", return_value=True), \
         patch("os.unlink", side_effect=Exception("boom")):
        tasks.process_file_task.run(
            "user-1",
            "job-1",
            {
                "filename": "file.txt",
                "organization_id": "org-1",
                "storage_path": "uploads/x",
                "size_bytes": 1,
                "mime_type": "text/plain",
                "metadata": "oops",
            },
            "status-1",
            "file_upload",
            "file_upload://uploads/x",
        )


def test_finalize_job_task_already_completed():
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
        data={"status": "completed", "total_files": 1}
    )

    with patch("worker.tasks.get_supabase", return_value=supabase):
        tasks.finalize_job_task.run("user-1", "job-1")


def test_finalize_job_task_reconciles_counts(monkeypatch):
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
        data={"status": "processing", "total_files": 0}
    )

    monkeypatch.setattr(tasks, "get_supabase", lambda: supabase)
    monkeypatch.setattr(tasks, "get_ingest_job_counters", lambda _job: {"total": 0, "processed": 2, "success": 0, "failed": 1, "skipped": 1})
    monkeypatch.setattr(tasks, "_get_ingestion_counts_from_db", lambda *_args, **_kwargs: {"processed": 2, "success": 0, "failed": 1, "skipped": 1})
    reconciled = MagicMock()
    reconciled.labels.return_value = reconciled
    monkeypatch.setattr(tasks, "job_counters_reconciled", reconciled)
    monkeypatch.setattr(tasks, "job_counters_finalize", MagicMock())
    monkeypatch.setattr(tasks, "clear_ingest_job_counters", lambda *_args, **_kwargs: None)

    tasks.finalize_job_task.run("user-1", "job-1")


def test_finalize_job_task_reconciles_mismatch(monkeypatch):
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
        data={"status": "processing", "total_files": 2}
    )

    monkeypatch.setattr(tasks, "get_supabase", lambda: supabase)
    monkeypatch.setattr(
        tasks,
        "get_ingest_job_counters",
        lambda _job: {"total": 2, "processed": 1, "success": 1, "failed": 0, "skipped": 0},
    )
    monkeypatch.setattr(
        tasks,
        "_get_ingestion_counts_from_db",
        lambda *_args, **_kwargs: {"processed": 2, "success": 2, "failed": 0, "skipped": 0},
    )
    reconciled = MagicMock()
    reconciled.labels.return_value = reconciled
    monkeypatch.setattr(tasks, "job_counters_reconciled", reconciled)
    monkeypatch.setattr(tasks, "job_counters_finalize", MagicMock())
    monkeypatch.setattr(tasks, "clear_ingest_job_counters", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(tasks, "create_notification", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(tasks, "send_email_notification", lambda *_args, **_kwargs: None)

    tasks.finalize_job_task.run("user-1", "job-1")


def test_finalize_job_task_missing_counters_uses_db(monkeypatch):
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
        data={"status": "processing", "total_files": 0}
    )

    monkeypatch.setattr(tasks, "get_supabase", lambda: supabase)
    monkeypatch.setattr(tasks, "get_ingest_job_counters", lambda _job: None)
    missing = MagicMock()
    missing.labels.return_value = missing
    reconciled = MagicMock()
    reconciled.labels.return_value = reconciled
    monkeypatch.setattr(tasks, "job_counters_missing", missing)
    monkeypatch.setattr(tasks, "job_counters_reconciled", reconciled)
    monkeypatch.setattr(
        tasks,
        "_get_ingestion_counts_from_db",
        lambda *_args, **_kwargs: {"processed": 1, "success": 1, "failed": 0, "skipped": 0},
    )
    monkeypatch.setattr(tasks, "job_counters_finalize", MagicMock())
    monkeypatch.setattr(tasks, "clear_ingest_job_counters", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(tasks, "create_notification", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(tasks, "send_email_notification", lambda *_args, **_kwargs: None)

    tasks.finalize_job_task.run("user-1", "job-1")


def test_finalize_job_task_all_failed(monkeypatch):
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
        data={"status": "processing", "total_files": 2}
    )

    monkeypatch.setattr(tasks, "get_supabase", lambda: supabase)
    monkeypatch.setattr(tasks, "get_ingest_job_counters", lambda _job: {"total": 2, "processed": 2, "success": 0, "failed": 2, "skipped": 0})
    monkeypatch.setattr(tasks, "_get_ingestion_counts_from_db", lambda *_args, **_kwargs: {"processed": 2, "success": 0, "failed": 2, "skipped": 0})
    monkeypatch.setattr(tasks, "clear_ingest_job_counters", lambda *_args, **_kwargs: None)

    tasks.finalize_job_task.run("user-1", "job-1")


def test_crawl_discovery_task_unsafe_url(monkeypatch):
    supabase = MagicMock()
    connector = MagicMock()
    connector.normalize_url.return_value = "https://bad"
    connector.is_safe_url.return_value = False

    monkeypatch.setattr(tasks, "get_supabase", lambda: supabase)
    monkeypatch.setattr(tasks, "update_crawl_status", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(tasks, "create_notification", lambda *_args, **_kwargs: None)

    with patch("connectors.web.WebConnector", return_value=connector):
        with pytest.raises(Exception):
            tasks.crawl_discovery_task.run("user-1", "https://bad", {"crawl_type": "single"})


def test_crawl_discovery_task_sitemap_dedup(monkeypatch):
    supabase = MagicMock()
    connector = MagicMock()
    connector.normalize_url.side_effect = lambda url: None if url == "bad" else url
    connector.is_safe_url.return_value = True
    connector.parse_sitemap.return_value = ["bad", "https://example.com/page", "https://example.com/page"]
    connector.is_allowed_domain.return_value = True
    connector.check_robots_txt.return_value = True

    class FakeGroup:
        def apply_async(self):
            return SimpleNamespace(id="group-1")

    monkeypatch.setattr(tasks, "get_supabase", lambda: supabase)
    monkeypatch.setattr(tasks, "init_crawl_counters", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(tasks, "update_crawl_status", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(tasks, "create_notification", lambda *_args, **_kwargs: None)

    with patch("connectors.web.WebConnector", return_value=connector), \
         patch("celery.group", return_value=FakeGroup()):
        result = tasks.crawl_discovery_task.run("user-1", "https://example.com", {"crawl_type": "sitemap"})

    assert result["status"] == "dispatched"


def test_process_page_task_rate_limit_and_delay(monkeypatch):
    supabase = MagicMock()
    connector = MagicMock()
    connector.is_safe_url.return_value = True
    connector.get_crawl_delay.return_value = 1
    connector.fetch_documents_sync.return_value = []

    monkeypatch.setattr(tasks, "get_supabase", lambda: supabase)
    monkeypatch.setattr(tasks, "check_rate_limit", lambda *_args, **_kwargs: False)

    with patch("connectors.web.WebConnector", return_value=connector), \
         patch("time.sleep", return_value=None), \
         patch("worker.tasks._record_crawl_outcome_and_maybe_finalize") as record_outcome:
        result = tasks.process_page_task.run("user-1", "https://example.com", crawl_id="crawl-1")

    assert result["status"] == "skipped"
    record_outcome.assert_called()


def test_process_page_task_no_chunks(monkeypatch):
    supabase = MagicMock()
    supabase.rpc.return_value.execute.return_value = MagicMock()
    connector = MagicMock()
    connector.is_safe_url.return_value = True
    connector.get_crawl_delay.return_value = 0
    connector.fetch_documents_sync.return_value = [SimpleNamespace(content="hi", metadata={"title": "t"})]

    result_obj = SimpleNamespace(chunks=[], total_tokens=0)

    monkeypatch.setattr(tasks, "get_supabase", lambda: supabase)
    monkeypatch.setattr("services.parsers.DocumentProcessorFactory", SimpleNamespace(process_web_content=lambda *_args, **_kwargs: result_obj))
    monkeypatch.setattr(tasks, "check_rate_limit", lambda *_args, **_kwargs: True)

    with patch("connectors.web.WebConnector", return_value=connector), \
         patch("worker.tasks._record_crawl_outcome_and_maybe_finalize") as record_outcome:
        result = tasks.process_page_task.run("user-1", "https://example.com", crawl_id="crawl-1")

    assert result["status"] == "skipped"
    record_outcome.assert_called()


def test_process_page_task_no_embeddings(monkeypatch):
    supabase = MagicMock()
    supabase.rpc.return_value.execute.return_value = MagicMock()
    connector = MagicMock()
    connector.is_safe_url.return_value = True
    connector.get_crawl_delay.return_value = 0
    connector.fetch_documents_sync.return_value = [SimpleNamespace(content="hi", metadata={"title": "t"})]

    chunk = SimpleNamespace(content="hi", token_count=1, chunk_index=0, metadata={})
    result_obj = SimpleNamespace(chunks=[chunk], total_tokens=1)

    monkeypatch.setattr(tasks, "get_supabase", lambda: supabase)
    monkeypatch.setattr("services.parsers.DocumentProcessorFactory", SimpleNamespace(process_web_content=lambda *_args, **_kwargs: result_obj))
    monkeypatch.setattr("services.embeddings.generate_embeddings_batch_sync", lambda *_args, **_kwargs: [None])
    monkeypatch.setattr(tasks, "check_rate_limit", lambda *_args, **_kwargs: True)

    with patch("connectors.web.WebConnector", return_value=connector), \
         patch("worker.tasks._record_crawl_outcome_and_maybe_finalize") as record_outcome:
        result = tasks.process_page_task.run("user-1", "https://example.com", crawl_id="crawl-1")

    assert result["status"] == "failed"
    record_outcome.assert_called()


def test_process_page_task_doc_insert_failed(monkeypatch):
    supabase = MagicMock()
    supabase.rpc.return_value.execute.return_value = MagicMock()
    connector = MagicMock()
    connector.is_safe_url.return_value = True
    connector.get_crawl_delay.return_value = 0
    connector.fetch_documents_sync.return_value = [SimpleNamespace(content="hi", metadata={"title": "t"})]

    chunk = SimpleNamespace(content="hi", token_count=1, chunk_index=0, metadata={})
    result_obj = SimpleNamespace(chunks=[chunk], total_tokens=1)

    monkeypatch.setattr(tasks, "get_supabase", lambda: supabase)
    monkeypatch.setattr("services.parsers.DocumentProcessorFactory", SimpleNamespace(process_web_content=lambda *_args, **_kwargs: result_obj))
    monkeypatch.setattr("services.embeddings.generate_embeddings_batch_sync", lambda *_args, **_kwargs: [[0.1]])
    monkeypatch.setattr(tasks, "check_rate_limit", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(tasks, "ingest_document_batched", lambda **_kwargs: None)
    monkeypatch.setattr(tasks, "_is_duplicate_document", lambda *_args, **_kwargs: False)

    with patch("connectors.web.WebConnector", return_value=connector), \
         patch("worker.tasks._record_crawl_outcome_and_maybe_finalize") as record_outcome:
        result = tasks.process_page_task.run("user-1", "https://example.com", crawl_id="crawl-1")

    assert result["status"] == "failed"
    record_outcome.assert_called()


def test_process_page_task_increment_error(monkeypatch):
    supabase = MagicMock()
    supabase.rpc.side_effect = Exception("boom")
    connector = MagicMock()
    connector.is_safe_url.return_value = True
    connector.get_crawl_delay.return_value = 0
    connector.fetch_documents_sync.return_value = [SimpleNamespace(content="hi", metadata={"title": "t"})]

    chunk = SimpleNamespace(content="hi", token_count=1, chunk_index=0, metadata={})
    result_obj = SimpleNamespace(chunks=[chunk], total_tokens=1)

    monkeypatch.setattr(tasks, "get_supabase", lambda: supabase)
    monkeypatch.setattr("services.parsers.DocumentProcessorFactory", SimpleNamespace(process_web_content=lambda *_args, **_kwargs: result_obj))
    monkeypatch.setattr("services.embeddings.generate_embeddings_batch_sync", lambda *_args, **_kwargs: [[0.1]])
    monkeypatch.setattr(tasks, "check_rate_limit", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(tasks, "ingest_document_batched", lambda **_kwargs: "doc-1")
    monkeypatch.setattr(tasks, "_is_duplicate_document", lambda *_args, **_kwargs: False)

    with patch("connectors.web.WebConnector", return_value=connector), \
         patch("worker.tasks._record_crawl_outcome_and_maybe_finalize") as record_outcome:
        result = tasks.process_page_task.run("user-1", "https://example.com", crawl_id="crawl-1")

    assert result["status"] == "success"
    record_outcome.assert_called()


def test_process_page_task_exception_path(monkeypatch):
    supabase = MagicMock()
    supabase.rpc.return_value.execute.side_effect = Exception("boom")
    connector = MagicMock()
    connector.is_safe_url.return_value = True
    connector.get_crawl_delay.return_value = 0
    connector.fetch_documents_sync.return_value = [SimpleNamespace(content="hi", metadata={"title": "t"})]

    monkeypatch.setattr(tasks, "get_supabase", lambda: supabase)
    monkeypatch.setattr("services.parsers.DocumentProcessorFactory", SimpleNamespace(process_web_content=lambda *_args, **_kwargs: (_ for _ in ()).throw(Exception("boom"))))
    monkeypatch.setattr(tasks, "check_rate_limit", lambda *_args, **_kwargs: True)
    notify = MagicMock()
    monkeypatch.setattr(tasks, "send_failure_email_notification", notify)

    with patch("connectors.web.WebConnector", return_value=connector):
        with pytest.raises(Exception):
            tasks.process_page_task.run("user-1", "https://example.com", crawl_id="crawl-1")

    notify.assert_called_once()


def test_finalize_crawl_task_already_completed(monkeypatch):
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
        data={"status": "completed"}
    )
    monkeypatch.setattr(tasks, "get_supabase", lambda: supabase)

    tasks.finalize_crawl_task.run("user-1", "crawl-1")


def test_finalize_crawl_task_not_complete(monkeypatch):
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
        data={
            "status": "processing",
            "root_url": "https://example.com",
            "total_pages_found": 5,
            "pages_ingested": 2,
            "pages_failed": 1,
        }
    )
    monkeypatch.setattr(tasks, "get_supabase", lambda: supabase)
    monkeypatch.setattr(tasks, "get_crawl_counters", lambda _crawl: None)

    tasks.finalize_crawl_task.run("user-1", "crawl-1")


def test_finalize_crawl_task_reconciles(monkeypatch):
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
        data={
            "status": "processing",
            "root_url": "https://example.com",
            "total_pages_found": 0,
            "pages_ingested": 2,
            "pages_failed": 1,
        }
    )
    monkeypatch.setattr(tasks, "get_supabase", lambda: supabase)
    monkeypatch.setattr(tasks, "get_crawl_counters", lambda _crawl: {"total": 0, "success": 1, "failed": 0, "skipped": 0})
    reconciled = MagicMock()
    reconciled.labels.return_value = reconciled
    monkeypatch.setattr(tasks, "job_counters_reconciled", reconciled)
    monkeypatch.setattr(tasks, "update_crawl_status", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(tasks, "create_notification", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(tasks, "clear_crawl_counters", lambda *_args, **_kwargs: None)

    tasks.finalize_crawl_task.run("user-1", "crawl-1")


def test_check_scheduled_crawls_intervals(monkeypatch):
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.neq.return_value.lte.return_value.execute.return_value = Mock(
        data=[
            {"id": "c1", "user_id": "u1", "root_url": "https://a", "crawl_type": "single", "max_depth": 1, "refresh_interval": "weekly"},
            {"id": "c2", "user_id": "u2", "root_url": "https://b", "crawl_type": "single", "max_depth": 1, "refresh_interval": "monthly"},
            {"id": "c3", "user_id": "u3", "root_url": "https://c", "crawl_type": "single", "max_depth": 1, "refresh_interval": "other"},
        ]
    )
    monkeypatch.setattr(tasks, "get_supabase", lambda: supabase)
    monkeypatch.setattr(tasks, "crawl_discovery_task", SimpleNamespace(delay=lambda **_kwargs: SimpleNamespace(id="task-1")))

    result = tasks.check_scheduled_crawls.run()

    assert result["crawls_triggered"] == 3


def test_check_scheduled_crawls_handles_config_error(monkeypatch):
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.neq.return_value.lte.return_value.execute.return_value = Mock(
        data=[{"id": "c1", "user_id": "u1", "root_url": "https://a", "crawl_type": "single", "max_depth": 1, "refresh_interval": "daily"}]
    )
    supabase.table.return_value.update.return_value.eq.return_value.execute.side_effect = Exception("boom")
    monkeypatch.setattr(tasks, "get_supabase", lambda: supabase)
    monkeypatch.setattr(tasks, "crawl_discovery_task", SimpleNamespace(delay=lambda **_kwargs: SimpleNamespace(id="task-1")))

    result = tasks.check_scheduled_crawls.run()

    assert result["crawls_triggered"] == 0


def test_check_scheduled_crawls_handles_error(monkeypatch):
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.neq.return_value.lte.return_value.execute.side_effect = Exception("boom")
    monkeypatch.setattr(tasks, "get_supabase", lambda: supabase)

    result = tasks.check_scheduled_crawls.run()

    assert result["status"] == "error"


def test_check_rate_limit_increments(monkeypatch):
    client = MagicMock()
    client.get.return_value = b"1"
    monkeypatch.setattr("redis.from_url", lambda *_args, **_kwargs: client)

    assert tasks.check_rate_limit(MagicMock(), "https://example.com") is True
    client.incr.assert_called_once()


def test_health_check_task():
    result = tasks.health_check_task.run()
    assert result["status"] == "healthy"


def test_cleanup_old_jobs_handles_error(monkeypatch):
    monkeypatch.setattr(tasks, "get_supabase", lambda: (_ for _ in ()).throw(Exception("boom")))
    result = tasks.cleanup_old_jobs.run()
    assert result["status"] == "error"
