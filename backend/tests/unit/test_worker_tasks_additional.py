import base64
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from worker import tasks


def _make_chunk(content="chunk", token_count=1, chunk_index=0, metadata=None):
    return SimpleNamespace(
        content=content,
        token_count=token_count,
        chunk_index=chunk_index,
        metadata=metadata or {},
    )


def _make_parse_result(file_type="txt", chunks=None, metadata=None, total_tokens=0):
    return SimpleNamespace(
        file_type=file_type,
        chunks=chunks or [],
        metadata=metadata or {},
        total_tokens=total_tokens,
    )


def _make_chain_table(execute_data=None):
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.in_.return_value = table
    table.limit.return_value = table
    table.single.return_value = table
    table.update.return_value = table
    table.insert.return_value = table
    table.execute.return_value = SimpleNamespace(data=execute_data)
    return table


def test_process_document_pipeline_handles_exception():
    supabase = MagicMock()

    with patch("worker.tasks.DocumentProcessorFactory.process", side_effect=RuntimeError("boom")), \
         patch("worker.tasks.update_file_status") as update_file_status:
        result = tasks.process_document_pipeline(
            supabase,
            content=b"data",
            filename="file.txt",
            user_id="user-1",
            job_id="job-1",
            file_status_id="status-1",
            source_type="file_upload",
            metadata={
                "mime_type": "text/plain",
                "organization_id": "11111111-1111-1111-1111-111111111111",
                "scope_id": "file_upload://file.txt",
            },
        )

    assert result.success is False
    assert result.error == "boom"
    update_file_status.assert_called()


def test_handle_task_failure_logs_to_dlq():
    fake_task = SimpleNamespace(name="test-task")
    with patch("worker.dlq_worker.log_task_failure") as log_task_failure:
        tasks.handle_task_failure(
            fake_task,
            Exception("fail"),
            "task-1",
            (),
            {"user_id": "user-1", "job_id": "job-1"},
            "traceback",
        )

    log_task_failure.assert_called_once()


def test_handle_task_failure_handles_errors():
    fake_task = SimpleNamespace(name="test-task")
    with patch("worker.dlq_worker.log_task_failure", side_effect=RuntimeError("boom")):
        tasks.handle_task_failure(
            fake_task,
            Exception("fail"),
            "task-1",
            (),
            {"user_id": "user-1", "job_id": "job-1"},
            "traceback",
        )


def test_unified_ingest_task_dispatches_group_for_docs(monkeypatch):
    task = SimpleNamespace(request=SimpleNamespace(id="task-1"))

    class DummyConnector:
        def __init__(self, docs):
            self.docs = docs

        def fetch_documents_sync(self, item_ids, credentials, user_id=None):
            for doc in self.docs:
                yield doc

    docs = [
        SimpleNamespace(
            filename="a.txt",
            content="hello",
            size_bytes=5,
            mime_type="text/plain",
            metadata={"storage_path": "uploads/a.txt", "scope_id": "file_upload://uploads/a.txt"},
            source_type="file_upload",
            source_id="src-a",
            parent_id=None,
        ),
        SimpleNamespace(
            filename="b.bin",
            content=base64.b64encode(b"bin").decode("utf-8"),
            size_bytes=3,
            mime_type="application/octet-stream",
            metadata={"storage_path": "uploads/b.bin", "scope_id": "file_upload://uploads/b.bin"},
            source_type="file_upload",
            source_id="src-b",
            parent_id=None,
        ),
    ]

    ingestion_jobs = _make_chain_table(execute_data=[{"id": "job-1"}])
    ingestion_jobs.execute.side_effect = [
        SimpleNamespace(data=[]),
        SimpleNamespace(data=[]),
    ]

    file_status = _make_chain_table(execute_data=[{"id": "status-1"}])
    file_status.execute.side_effect = [
        SimpleNamespace(data=[{"id": "status-1"}]),
        SimpleNamespace(data=[{"id": "status-2"}]),
    ]
    scope_identities = _make_chain_table(execute_data=[])

    supabase = MagicMock()
    supabase.table.side_effect = lambda name: {
        "ingestion_jobs": ingestion_jobs,
        "ingestion_file_status": file_status,
        "scope_identities": scope_identities,
    }[name]

    @contextmanager
    def no_limit(_connector_type):
        yield

    class FakeGroup:
        def __init__(self, _tasks):
            self.id = "group-1"

        def apply_async(self):
            return SimpleNamespace(id=self.id)

    monkeypatch.setattr(tasks, "get_supabase", lambda: supabase)
    monkeypatch.setattr(tasks, "get_connector", lambda _connector_type: DummyConnector(docs))
    monkeypatch.setattr(tasks, "connector_fetch_limit", no_limit)
    monkeypatch.setattr(tasks, "store_celery_task_id", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(tasks, "check_job_cancelled", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(tasks, "update_job_status", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(tasks, "create_notification", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(tasks, "init_ingest_job_counters", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(tasks, "process_file_task", SimpleNamespace(s=lambda **_kwargs: "sig"))
    monkeypatch.setattr("celery.group", lambda _tasks: FakeGroup(_tasks))

    result = tasks.unified_ingest_task._orig_run.__func__(
        task,
        "11111111-1111-1111-1111-111111111111",
        "job-1",
        "file_upload",
        ["a", "b"],
        {},
        plan_code="starter",
    )

    assert result["status"] == "dispatched"
    assert result["total_files"] == 2


def test_unified_ingest_task_handles_invalid_content(monkeypatch):
    task = SimpleNamespace(request=SimpleNamespace(id="task-1"))

    class DummyConnector:
        def fetch_documents_sync(self, item_ids, credentials, user_id=None):
            yield SimpleNamespace(
                filename="bad.bin",
                content=["not", "bytes"],
                size_bytes=2,
                mime_type="application/octet-stream",
                metadata={"storage_path": "uploads/bad.bin", "scope_id": "file_upload://uploads/bad.bin"},
                source_type="file_upload",
                source_id="src-bad",
                parent_id=None,
            )

    supabase = MagicMock()

    @contextmanager
    def no_limit(_connector_type):
        yield

    monkeypatch.setattr(tasks, "get_supabase", lambda: supabase)
    monkeypatch.setattr(tasks, "get_connector", lambda _connector_type: DummyConnector())
    monkeypatch.setattr(tasks, "connector_fetch_limit", no_limit)
    monkeypatch.setattr(tasks, "store_celery_task_id", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(tasks, "check_job_cancelled", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(tasks, "create_notification", lambda *_args, **_kwargs: None)

    called = {}

    def fake_update_job_status(*_args, **kwargs):
        called["status"] = kwargs.get("status") or (_args[2] if len(_args) > 2 else None)

    monkeypatch.setattr(tasks, "update_job_status", fake_update_job_status)

    with pytest.raises(ValueError, match="Unsupported document content type"):
        tasks.unified_ingest_task._orig_run.__func__(
            task,
            "11111111-1111-1111-1111-111111111111",
            "job-1",
            "file_upload",
            ["a"],
            {},
            plan_code="starter",
        )

    assert called["status"] == "failed"


def test_process_file_task_skips_empty_pdf(monkeypatch):
    task = SimpleNamespace(request=SimpleNamespace(id="task-1"))
    supabase = MagicMock()
    supabase.table.return_value = _make_chain_table(execute_data=[])

    file_data = {
        "filename": "empty.pdf",
        "organization_id": "11111111-1111-1111-1111-111111111111",
        "content_b64": base64.b64encode(b"content").decode("utf-8"),
        "size_bytes": 7,
        "mime_type": "application/pdf",
    }
    scope_id = "file_upload://empty.pdf"

    parse_result = _make_parse_result(file_type="pdf", chunks=[])

    with patch("worker.tasks.get_supabase", return_value=supabase), \
         patch("services.parsers.DocumentProcessorFactory.process", return_value=parse_result), \
         patch("worker.tasks.update_file_status") as update_file_status, \
         patch("worker.tasks._record_ingest_outcome_and_maybe_finalize") as record_outcome:
        result = tasks.process_file_task._orig_run.__func__(
            task,
            "user-1",
            "job-1",
            file_data,
            "status-1",
            "file_upload",
            scope_id,
        )

    assert result["status"] == "skipped"
    assert result["reason"] == "empty"
    assert any(
        "OCR required" in call.kwargs.get("message", "") for call in update_file_status.call_args_list
    )
    record_outcome.assert_called_once()


def test_process_file_task_reuses_existing_document(monkeypatch):
    """Test that process_file_task dispatches to embedding queue successfully."""
    task = SimpleNamespace(request=SimpleNamespace(id="task-1"))
    supabase = MagicMock()

    docs_table = _make_chain_table(execute_data=[{"id": "doc-1"}])
    docs_table.execute.side_effect = [
        SimpleNamespace(data=[{"id": "doc-1"}]),
        SimpleNamespace(data=[{"id": "doc-1"}]),
    ]
    chunks_table = _make_chain_table(execute_data=[])

    supabase.table.side_effect = lambda name: {
        "documents": docs_table,
        "document_chunks": chunks_table,
    }.get(name, _make_chain_table(execute_data=[]))

    file_data = {
        "filename": "file.txt",
        "organization_id": "11111111-1111-1111-1111-111111111111",
        "content_b64": base64.b64encode(b"content").decode("utf-8"),
        "size_bytes": 7,
        "mime_type": "text/plain",
    }
    scope_id = "file_upload://file.txt"

    parse_result = _make_parse_result(file_type="txt", chunks=[_make_chunk()], total_tokens=1)

    with patch("worker.tasks.get_supabase", return_value=supabase), \
         patch("services.parsers.DocumentProcessorFactory.process", return_value=parse_result), \
         patch("worker.tasks.generate_embeddings_task") as mock_embedding_task, \
         patch("worker.tasks.update_file_status"):
        result = tasks.process_file_task._orig_run.__func__(
            task,
            "user-1",
            "job-1",
            file_data,
            "status-1",
            "file_upload",
            scope_id,
        )

    # With async embedding pipeline, success returns "queued_embedding"
    assert result["status"] == "queued_embedding"
    mock_embedding_task.apply_async.assert_called_once()


def test_process_file_task_dispatches_embedding_task(monkeypatch):
    """Test that process_file_task dispatches to embedding queue on success."""
    task = SimpleNamespace(request=SimpleNamespace(id="task-1"))
    supabase = MagicMock()
    docs_table = _make_chain_table(execute_data=[])
    supabase.table.return_value = docs_table

    file_data = {
        "filename": "file.txt",
        "organization_id": "11111111-1111-1111-1111-111111111111",
        "content_b64": base64.b64encode(b"content").decode("utf-8"),
        "size_bytes": 7,
        "mime_type": "text/plain",
    }
    scope_id = "file_upload://file.txt"

    parse_result = _make_parse_result(file_type="txt", chunks=[_make_chunk()], total_tokens=1)

    with patch("worker.tasks.get_supabase", return_value=supabase), \
         patch("services.parsers.DocumentProcessorFactory.process", return_value=parse_result), \
         patch("worker.tasks.generate_embeddings_task") as mock_embedding_task, \
         patch("worker.tasks.update_file_status"):
        result = tasks.process_file_task._orig_run.__func__(
            task,
            "user-1",
            "job-1",
            file_data,
            "status-1",
            "file_upload",
            scope_id,
        )

    # With async embedding pipeline, returns "queued_embedding"
    assert result["status"] == "queued_embedding"
    mock_embedding_task.apply_async.assert_called_once()

def test_process_file_task_handles_exception():
    """Test that process_file_task handles exceptions and returns failed."""
    task = SimpleNamespace(request=SimpleNamespace(id="task-1"))
    supabase = MagicMock()
    docs_table = _make_chain_table(execute_data=[])
    supabase.table.return_value = docs_table

    file_data = {
        "filename": "file.txt",
        "organization_id": "11111111-1111-1111-1111-111111111111",
        "content_b64": base64.b64encode(b"content").decode("utf-8"),
        "size_bytes": 7,
        "mime_type": "text/plain",
    }
    scope_id = "file_upload://file.txt"

    # Simulate parsing failure
    with patch("worker.tasks.get_supabase", return_value=supabase), \
         patch("services.parsers.DocumentProcessorFactory.process", side_effect=Exception("parse fail")), \
         patch("worker.tasks.update_file_status") as update_file_status, \
         patch("worker.tasks._record_ingest_outcome_and_maybe_finalize") as record_outcome:
        result = tasks.process_file_task._orig_run.__func__(
            task,
            "user-1",
            "job-1",
            file_data,
            "status-1",
            "file_upload",
            scope_id,
        )

    assert result["status"] == "failed"
    assert update_file_status.called
    record_outcome.assert_called()


def test_crawl_discovery_task_sitemap_dispatches(monkeypatch):
    task = SimpleNamespace(request=SimpleNamespace(id="task-1"))
    supabase = MagicMock()
    docs_table = _make_chain_table(execute_data=[{"source_url": "https://example.com/a"}])
    supabase.table.return_value = docs_table

    class DummyConnector:
        USER_AGENT = "test-agent"

        def normalize_url(self, url):
            return url

        def is_safe_url(self, _url):
            return True

        def parse_sitemap(self, _url):
            return ["https://example.com/a", "https://example.com/b"]

        def is_allowed_domain(self, _host, _base, _allow_subdomains):
            return True

        def check_robots_txt(self, _url, _ua):
            return True

    class FakeGroup:
        def __init__(self, _tasks):
            self.id = "group-1"

        def apply_async(self):
            return SimpleNamespace(id=self.id)

    monkeypatch.setattr(tasks, "get_supabase", lambda: supabase)
    monkeypatch.setattr(tasks, "update_crawl_status", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(tasks, "create_notification", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(tasks, "init_crawl_counters", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(tasks, "process_page_task", SimpleNamespace(s=lambda **_kwargs: "sig"))
    monkeypatch.setattr("celery.group", lambda _tasks: FakeGroup(_tasks))
    monkeypatch.setattr("connectors.web.WebConnector", lambda: DummyConnector())

    result = tasks.crawl_discovery_task._orig_run.__func__(
        task,
        "user-1",
        "https://example.com/sitemap.xml",
        {"crawl_id": "crawl-1", "crawl_type": "sitemap", "max_pages": 2},
    )

    assert result["status"] == "dispatched"
    assert result["total_pages"] == 1


def test_crawl_discovery_task_no_pages(monkeypatch):
    task = SimpleNamespace(request=SimpleNamespace(id="task-1"))
    supabase = MagicMock()
    supabase.table.return_value = _make_chain_table(execute_data=[])

    class DummyConnector:
        USER_AGENT = "test-agent"

        def normalize_url(self, url):
            return url

        def is_safe_url(self, _url):
            return True

        def parse_sitemap(self, _url):
            return []

        def is_allowed_domain(self, *_args, **_kwargs):
            return True

        def check_robots_txt(self, _url, _ua):
            return True

    monkeypatch.setattr(tasks, "get_supabase", lambda: supabase)
    monkeypatch.setattr(tasks, "update_crawl_status", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(tasks, "create_notification", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("connectors.web.WebConnector", lambda: DummyConnector())

    result = tasks.crawl_discovery_task._orig_run.__func__(
        task,
        "user-1",
        "https://example.com/sitemap.xml",
        {"crawl_id": "crawl-1", "crawl_type": "sitemap", "max_pages": 2},
    )

    assert result["status"] == "completed"


def test_crawl_discovery_task_recursive_dedup(monkeypatch):
    task = SimpleNamespace(request=SimpleNamespace(id="task-1"))
    supabase = MagicMock()
    docs_table = _make_chain_table(execute_data=[{"source_url": "https://example.com"}])
    supabase.table.return_value = docs_table

    class DummyConnector:
        USER_AGENT = "test-agent"

        def normalize_url(self, url):
            return url

        def is_safe_url(self, _url):
            return True

        def fetch_html(self, _url):
            return "<a href='https://example.com/next'>Next</a>"

        def extract_links(self, *_args, **_kwargs):
            return ["https://example.com/next"]

        def is_allowed_domain(self, *_args, **_kwargs):
            return True

        def check_robots_txt(self, _url, _ua):
            return True

    class FakeGroup:
        def __init__(self, _tasks):
            self.id = "group-1"

        def apply_async(self):
            return SimpleNamespace(id=self.id)

    monkeypatch.setattr(tasks, "get_supabase", lambda: supabase)
    monkeypatch.setattr(tasks, "update_crawl_status", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(tasks, "create_notification", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(tasks, "init_crawl_counters", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(tasks, "process_page_task", SimpleNamespace(s=lambda **_kwargs: "sig"))
    monkeypatch.setattr("celery.group", lambda _tasks: FakeGroup(_tasks))
    monkeypatch.setattr("connectors.web.WebConnector", lambda: DummyConnector())
    monkeypatch.setattr("worker.tasks.time.sleep", lambda *_args, **_kwargs: None)

    result = tasks.crawl_discovery_task._orig_run.__func__(
        task,
        "user-1",
        "https://example.com",
        {"crawl_id": "crawl-1", "crawl_type": "recursive", "max_depth": 1, "max_pages": 1},
    )

    assert result["status"] == "completed"
