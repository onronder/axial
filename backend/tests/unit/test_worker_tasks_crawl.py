from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch
import sys

import pytest

from worker import tasks


def _make_chain_table(result_data=None, count=None, execute_side_effect=None):
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.neq.return_value = table
    table.in_.return_value = table
    table.lt.return_value = table
    table.lte.return_value = table
    table.limit.return_value = table
    table.single.return_value = table
    table.order.return_value = table
    table.insert.return_value = table
    table.update.return_value = table
    table.delete.return_value = table
    if execute_side_effect is not None:
        table.execute.side_effect = execute_side_effect
    else:
        result = MagicMock(data=result_data)
        if count is not None:
            result.count = count
        table.execute.return_value = result
    return table


class TestCrawlStatusUpdates:
    @pytest.mark.unit
    def test_update_crawl_status_sets_completed_at(self):
        supabase = MagicMock()
        table = _make_chain_table(result_data=[])
        supabase.table.return_value = table

        metric = MagicMock()
        metric.labels.return_value.inc = MagicMock()

        with patch("worker.tasks.status_updates_total", metric), \
             patch("worker.tasks.record_crawl_job_update") as record_update:
            tasks.update_crawl_status(
                supabase,
                "crawl-1",
                status="completed",
                total_pages=3,
                pages_ingested=2,
                pages_failed=1,
                error_message="done",
            )

        payload = table.update.call_args[0][0]
        assert payload["status"] == "completed"
        assert "completed_at" in payload
        assert payload["total_pages_found"] == 3
        record_update.assert_called_once_with("crawl-1")

    @pytest.mark.unit
    def test_update_crawl_status_handles_errors(self):
        supabase = MagicMock()
        table = _make_chain_table()
        table.execute.side_effect = Exception("db error")
        supabase.table.return_value = table

        tasks.update_crawl_status(supabase, "crawl-1", status="processing")


class TestRateLimiting:
    @pytest.mark.unit
    def test_check_rate_limit_allows_first_request(self, monkeypatch):
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        fake_module = SimpleNamespace(from_url=MagicMock(return_value=mock_redis))
        monkeypatch.setitem(sys.modules, "redis", fake_module)

        allowed = tasks.check_rate_limit(MagicMock(), "https://example.com/path")

        assert allowed is True
        mock_redis.setex.assert_called_once()

    @pytest.mark.unit
    def test_check_rate_limit_blocks_when_over_limit(self, monkeypatch):
        mock_redis = MagicMock()
        mock_redis.get.return_value = b"5"
        fake_module = SimpleNamespace(from_url=MagicMock(return_value=mock_redis))
        monkeypatch.setitem(sys.modules, "redis", fake_module)

        allowed = tasks.check_rate_limit(MagicMock(), "https://example.com/path")

        assert allowed is False

    @pytest.mark.unit
    def test_check_rate_limit_allows_on_error(self, monkeypatch):
        fake_module = SimpleNamespace(from_url=MagicMock(side_effect=Exception("boom")))
        monkeypatch.setitem(sys.modules, "redis", fake_module)

        assert tasks.check_rate_limit(MagicMock(), "https://example.com/path") is True

    @pytest.mark.unit
    def test_get_domain_rate_limit_key(self):
        assert tasks.get_domain_rate_limit_key("https://example.com/page") == "crawl_ratelimit:example.com"


class TestCrawlDiscoveryTask:
    @pytest.mark.unit
    def test_crawl_discovery_dispatches_page_tasks(self):
        task = SimpleNamespace(request=SimpleNamespace(id="task-1"))
        supabase = MagicMock()
        supabase.table.return_value = _make_chain_table(result_data=[])

        connector = MagicMock()
        connector.normalize_url.return_value = "https://example.com"
        connector.is_safe_url.return_value = True
        connector.check_robots_txt.return_value = True

        mock_group = MagicMock()
        mock_group.apply_async.return_value = SimpleNamespace(id="group-1")

        with patch("worker.tasks.get_supabase", return_value=supabase), \
             patch("connectors.web.WebConnector", return_value=connector), \
             patch("worker.tasks.create_notification"), \
             patch("worker.tasks.update_crawl_status"), \
             patch("worker.tasks.init_crawl_counters", return_value=True), \
             patch("celery.group", return_value=mock_group):
            result = tasks.crawl_discovery_task._orig_run.__func__(
                task,
                "user-1",
                "https://example.com",
                {"crawl_id": "crawl-1", "crawl_type": "single"},
            )

        assert result["status"] == "dispatched"
        assert result["total_pages"] == 1

    @pytest.mark.unit
    def test_crawl_discovery_rejects_invalid_url(self):
        task = SimpleNamespace(request=SimpleNamespace(id="task-1"))
        supabase = MagicMock()

        connector = MagicMock()
        connector.normalize_url.return_value = None

        with patch("worker.tasks.get_supabase", return_value=supabase), \
             patch("connectors.web.WebConnector", return_value=connector), \
             patch("worker.tasks.create_notification"), \
             patch("worker.tasks.update_crawl_status"):
            with pytest.raises(ValueError):
                tasks.crawl_discovery_task._orig_run.__func__(
                    task,
                    "user-1",
                    "bad-url",
                    {"crawl_id": "crawl-1", "crawl_type": "single"},
                )

    @pytest.mark.unit
    def test_crawl_discovery_dedup_adds_raw_url_when_normalize_none(self):
        task = SimpleNamespace(request=SimpleNamespace(id="task-1"))
        supabase = MagicMock()
        doc_table = _make_chain_table(result_data=[{"source_url": "https://example.com/existing"}])
        supabase.table.return_value = doc_table

        connector = MagicMock()
        connector.normalize_url.side_effect = lambda url: None if url == "https://example.com/existing" else url
        connector.is_safe_url.return_value = True
        connector.check_robots_txt.return_value = True

        mock_group = MagicMock()
        mock_group.apply_async.return_value = SimpleNamespace(id="group-1")

        with patch("worker.tasks.get_supabase", return_value=supabase), \
             patch("connectors.web.WebConnector", return_value=connector), \
             patch("worker.tasks.create_notification"), \
             patch("worker.tasks.update_crawl_status"), \
             patch("worker.tasks.init_crawl_counters", return_value=True), \
             patch("celery.group", return_value=mock_group):
            result = tasks.crawl_discovery_task._orig_run.__func__(
                task,
                "user-1",
                "https://example.com/root",
                {"crawl_id": "crawl-1", "crawl_type": "single"},
            )

        assert result["status"] == "dispatched"

    @pytest.mark.unit
    def test_crawl_discovery_dedup_query_failure(self):
        task = SimpleNamespace(request=SimpleNamespace(id="task-1"))
        supabase = MagicMock()
        doc_table = _make_chain_table(result_data=[])
        doc_table.execute.side_effect = Exception("boom")
        supabase.table.return_value = doc_table

        connector = MagicMock()
        connector.normalize_url.return_value = "https://example.com/root"
        connector.is_safe_url.return_value = True
        connector.check_robots_txt.return_value = True

        mock_group = MagicMock()
        mock_group.apply_async.return_value = SimpleNamespace(id="group-1")

        with patch("worker.tasks.get_supabase", return_value=supabase), \
             patch("connectors.web.WebConnector", return_value=connector), \
             patch("worker.tasks.create_notification"), \
             patch("worker.tasks.update_crawl_status"), \
             patch("worker.tasks.init_crawl_counters", return_value=True), \
             patch("celery.group", return_value=mock_group):
            result = tasks.crawl_discovery_task._orig_run.__func__(
                task,
                "user-1",
                "https://example.com/root",
                {"crawl_id": "crawl-1", "crawl_type": "single"},
            )

        assert result["status"] == "dispatched"


class TestProcessPageTask:
    @pytest.mark.unit
    def test_process_page_task_blocks_unsafe_url(self):
        task = SimpleNamespace(request=SimpleNamespace(id="task-1"))
        supabase = MagicMock()
        supabase.rpc.return_value.execute.return_value = MagicMock(data=[])

        connector = MagicMock()
        connector.is_safe_url.return_value = False

        with patch("worker.tasks.get_supabase", return_value=supabase), \
             patch("connectors.web.WebConnector", return_value=connector), \
             patch("worker.tasks._record_crawl_outcome_and_maybe_finalize") as record_outcome:
            result = tasks.process_page_task._orig_run.__func__(
                task,
                "user-1",
                "https://unsafe.example.com",
                crawl_id="crawl-1",
                respect_robots=True,
            )

        assert result["status"] == "failed"
        record_outcome.assert_called_once()

    @pytest.mark.unit
    def test_process_page_task_handles_empty_docs(self):
        task = SimpleNamespace(request=SimpleNamespace(id="task-1"))
        supabase = MagicMock()
        supabase.rpc.return_value.execute.return_value = MagicMock(data=[])

        connector = MagicMock()
        connector.is_safe_url.return_value = True
        connector.get_crawl_delay.return_value = None
        connector.fetch_documents_sync.return_value = []

        with patch("worker.tasks.get_supabase", return_value=supabase), \
             patch("connectors.web.WebConnector", return_value=connector), \
             patch("worker.tasks.check_rate_limit", return_value=True), \
             patch("worker.tasks._record_crawl_outcome_and_maybe_finalize") as record_outcome:
            result = tasks.process_page_task._orig_run.__func__(
                task,
                "user-1",
                "https://example.com",
                crawl_id="crawl-1",
                respect_robots=True,
            )

        assert result["status"] == "skipped"
        record_outcome.assert_called_once()

    @pytest.mark.unit
    def test_process_page_task_success(self):
        task = SimpleNamespace(request=SimpleNamespace(id="task-1"))
        supabase = MagicMock()
        supabase.rpc.return_value.execute.return_value = MagicMock(data=[])

        doc = SimpleNamespace(content="hello world", metadata={"title": "Home", "source_url": "https://example.com"})
        connector = MagicMock()
        connector.is_safe_url.return_value = True
        connector.get_crawl_delay.return_value = None
        connector.fetch_documents_sync.return_value = [doc]

        chunk = SimpleNamespace(content="chunk", token_count=2, chunk_index=0, metadata={})
        parse_result = SimpleNamespace(chunks=[chunk], total_tokens=2)

        with patch("worker.tasks.get_supabase", return_value=supabase), \
             patch("connectors.web.WebConnector", return_value=connector), \
             patch("worker.tasks.check_rate_limit", return_value=True), \
             patch("worker.tasks._is_duplicate_document", return_value=False), \
             patch("services.parsers.DocumentProcessorFactory.process_web_content", return_value=parse_result), \
             patch("services.embeddings.generate_embeddings_batch_sync", return_value=[[0.1]]), \
             patch("worker.tasks.ingest_document_batched", return_value="doc-1"), \
             patch("worker.tasks._record_crawl_outcome_and_maybe_finalize") as record_outcome:
            result = tasks.process_page_task._orig_run.__func__(
                task,
                "user-1",
                "https://example.com",
                crawl_id="crawl-1",
                respect_robots=True,
            )

        assert result["status"] == "success"
        record_outcome.assert_called_once()

    @pytest.mark.unit
    def test_process_page_task_decodes_bytes_content(self):
        task = SimpleNamespace(request=SimpleNamespace(id="task-1"))
        supabase = MagicMock()
        supabase.rpc.return_value.execute.return_value = MagicMock(data=[])

        doc = SimpleNamespace(content=b"hello world", metadata={"title": "Home", "source_url": "https://example.com"})
        connector = MagicMock()
        connector.is_safe_url.return_value = True
        connector.get_crawl_delay.return_value = None
        connector.fetch_documents_sync.return_value = [doc]

        chunk = SimpleNamespace(content="chunk", token_count=2, chunk_index=0, metadata={})
        parse_result = SimpleNamespace(chunks=[chunk], total_tokens=2)

        with patch("worker.tasks.get_supabase", return_value=supabase), \
             patch("connectors.web.WebConnector", return_value=connector), \
             patch("worker.tasks.check_rate_limit", return_value=True), \
             patch("worker.tasks._is_duplicate_document", return_value=False), \
             patch("services.parsers.DocumentProcessorFactory.process_web_content", return_value=parse_result) as process_web, \
             patch("services.embeddings.generate_embeddings_batch_sync", return_value=[[0.1]]), \
             patch("worker.tasks.ingest_document_batched", return_value="doc-1"), \
             patch("worker.tasks._record_crawl_outcome_and_maybe_finalize"):
            result = tasks.process_page_task._orig_run.__func__(
                task,
                "user-1",
                "https://example.com",
                crawl_id="crawl-1",
                respect_robots=True,
            )

        assert result["status"] == "success"
        assert process_web.call_args[0][0] == "hello world"


class TestFinalizeCrawlTask:
    @pytest.mark.unit
    def test_finalize_crawl_task_no_config(self):
        task = SimpleNamespace(request=SimpleNamespace(id="task-1"))
        supabase = MagicMock()
        table = _make_chain_table(result_data=None)
        supabase.table.return_value = table

        with patch("worker.tasks.get_supabase", return_value=supabase):
            tasks.finalize_crawl_task.run.__func__(task, "user-1", "crawl-1")

        table.select.assert_called_once()

    @pytest.mark.unit
    def test_finalize_crawl_task_completes_with_counters(self):
        task = SimpleNamespace(request=SimpleNamespace(id="task-1"))
        supabase = MagicMock()
        config_table = _make_chain_table(
            result_data={
                "status": "processing",
                "root_url": "https://example.com",
                "total_pages_found": 2,
                "pages_ingested": 1,
                "pages_failed": 0,
            }
        )
        supabase.table.return_value = config_table

        with patch("worker.tasks.get_supabase", return_value=supabase), \
             patch("worker.tasks.get_crawl_counters", return_value={"success": 1, "failed": 0, "skipped": 1, "total": 2}), \
             patch("worker.tasks.update_crawl_status") as update_status, \
             patch("worker.tasks.clear_crawl_counters") as clear_counters, \
             patch("worker.tasks.create_notification") as create_notification:
            tasks.finalize_crawl_task.run.__func__(task, "user-1", "crawl-1")

        update_status.assert_called_once()
        clear_counters.assert_called_once_with("crawl-1")
        create_notification.assert_called_once()


class TestScheduledCrawls:
    @pytest.mark.unit
    def test_check_scheduled_crawls_no_due(self):
        task = SimpleNamespace(request=SimpleNamespace(id="task-1"))
        supabase = MagicMock()
        table = _make_chain_table(result_data=[])
        supabase.table.return_value = table

        with patch("worker.tasks.get_supabase", return_value=supabase):
            result = tasks.check_scheduled_crawls.run.__func__(task)

        assert result["crawls_triggered"] == 0

    @pytest.mark.unit
    def test_check_scheduled_crawls_triggers(self):
        task = SimpleNamespace(request=SimpleNamespace(id="task-1"))
        supabase = MagicMock()
        table = _make_chain_table(
            execute_side_effect=[
                MagicMock(
                    data=[
                        {
                            "id": "crawl-1",
                            "user_id": "user-1",
                            "root_url": "https://example.com",
                            "crawl_type": "single",
                            "max_depth": 1,
                            "max_pages": 10,
                            "allow_subdomains": False,
                            "respect_robots_txt": True,
                            "refresh_interval": "daily",
                        }
                    ]
                ),
                MagicMock(data=[]),
                MagicMock(data=[]),
            ]
        )
        supabase.table.return_value = table

        mock_task = SimpleNamespace(id="task-123")

        with patch("worker.tasks.get_supabase", return_value=supabase), \
             patch("worker.tasks.crawl_discovery_task.delay", return_value=mock_task):
            result = tasks.check_scheduled_crawls.run.__func__(task)

        assert result["crawls_triggered"] == 1


class TestCleanupOldJobs:
    @pytest.mark.unit
    def test_cleanup_old_jobs_success(self):
        task = SimpleNamespace(request=SimpleNamespace(id="cleanup-1"))
        supabase = MagicMock()
        table = _make_chain_table(
            execute_side_effect=[
                MagicMock(data=[{"id": "job-1"}]),
                MagicMock(data=[{"id": "notif-1"}, {"id": "notif-2"}]),
            ]
        )
        supabase.table.return_value = table

        with patch("core.db.get_supabase", return_value=supabase):
            result = tasks.cleanup_old_jobs.run.__func__(task)

        assert result["status"] == "success"
        assert result["jobs_deleted"] == 1
        assert result["notifications_deleted"] == 2
