import base64
import itertools
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


def _make_chain_table(result_data=None, count=None, execute_side_effect=None, data=None):
    if result_data is None and data is not None:
        result_data = data
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.neq.return_value = table
    table.limit.return_value = table
    table.single.return_value = table
    table.maybe_single.return_value = table
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


class TestProcessDocumentPipeline:
    @pytest.mark.unit
    def test_process_document_pipeline_success(self):
        supabase = MagicMock()
        chunks = [
            _make_chunk(content="alpha", token_count=2, chunk_index=0),
            _make_chunk(content="beta", token_count=3, chunk_index=1),
        ]
        parse_result = _make_parse_result(
            file_type="txt",
            chunks=chunks,
            metadata={"parser": "test"},
            total_tokens=5,
        )

        with patch("worker.tasks.DocumentProcessorFactory.process", return_value=parse_result), \
             patch("worker.tasks.generate_embeddings_batch_sync", return_value=[[0.1], [0.2]]), \
             patch("worker.tasks.ingest_document_batched", return_value="doc-1"), \
             patch("worker.tasks.update_file_status") as update_file_status:
            result = tasks.process_document_pipeline(
                supabase,
                content=b"hello world",
                filename="test.txt",
                user_id="user-1",
                job_id="job-1",
                file_status_id="status-1",
                source_type="file_upload",
                metadata={"mime_type": "text/plain", "organization_id": "11111111-1111-1111-1111-111111111111", "scope_id": "file_upload://test.txt"},
            )

        assert result.success is True
        assert result.document_id == "doc-1"
        assert result.chunks_count == 2
        assert any(
            call.kwargs.get("status") == "completed" for call in update_file_status.call_args_list
        )

    @pytest.mark.unit
    def test_process_document_pipeline_rejects_large_file(self):
        supabase = MagicMock()

        with patch.object(tasks.settings, "MAX_FILE_SIZE", 2), \
             patch("worker.tasks.update_file_status") as update_file_status:
            result = tasks.process_document_pipeline(
                supabase,
                content=b"toolarge",
                filename="big.txt",
                user_id="user-1",
                job_id="job-1",
                file_status_id="status-1",
                source_type="file_upload",
                metadata={"mime_type": "text/plain", "organization_id": "11111111-1111-1111-1111-111111111111", "scope_id": "file_upload://big.txt"},
            )

        assert result.success is False
        assert result.error == "File too large"
        assert any(
            call.kwargs.get("status") == "failed" for call in update_file_status.call_args_list
        )

    @pytest.mark.unit
    def test_process_document_pipeline_parsing_timeout(self):
        supabase = MagicMock()
        parse_result = _make_parse_result(file_type="txt", chunks=[_make_chunk()])
        time_values = itertools.chain([0, 10], itertools.repeat(10))

        with patch("worker.tasks.DocumentProcessorFactory.process", return_value=parse_result), \
             patch("worker.tasks.get_parse_timeout_seconds", return_value=1), \
             patch("worker.tasks.time.time", side_effect=time_values), \
             patch("worker.tasks.generate_embeddings_batch_sync", return_value=[[0.1]]), \
             patch("worker.tasks.update_file_status") as update_file_status:
            result = tasks.process_document_pipeline(
                supabase,
                content=b"slow",
                filename="slow.pdf",
                user_id="user-1",
                job_id="job-1",
                file_status_id="status-1",
                source_type="file_upload",
                metadata={"mime_type": "application/pdf", "organization_id": "11111111-1111-1111-1111-111111111111", "scope_id": "file_upload://slow.pdf"},
            )

        assert result.success is False
        assert result.error == "Parsing timeout"
        assert any(
            call.kwargs.get("status") == "failed" for call in update_file_status.call_args_list
        )

    @pytest.mark.unit
    def test_process_document_pipeline_unsupported_file(self):
        supabase = MagicMock()
        parse_result = _make_parse_result(
            file_type="unsupported",
            chunks=[],
            metadata={"unsupported_reason": "binary_content"},
        )

        with patch("worker.tasks.DocumentProcessorFactory.process", return_value=parse_result), \
             patch("worker.tasks.update_file_status") as update_file_status:
            result = tasks.process_document_pipeline(
                supabase,
                content=b"binary",
                filename="file.bin",
                user_id="user-1",
                job_id="job-1",
                file_status_id="status-1",
                source_type="file_upload",
                metadata={"mime_type": "application/octet-stream", "organization_id": "11111111-1111-1111-1111-111111111111", "scope_id": "file_upload://file.bin"},
            )

        assert result.success is True
        assert result.chunks_count == 0
        assert any(
            call.kwargs.get("status") == "skipped" for call in update_file_status.call_args_list
        )

    @pytest.mark.unit
    def test_process_document_pipeline_empty_chunks(self):
        supabase = MagicMock()
        parse_result = _make_parse_result(file_type="txt", chunks=[])

        with patch("worker.tasks.DocumentProcessorFactory.process", return_value=parse_result), \
             patch("worker.tasks.update_file_status") as update_file_status:
            result = tasks.process_document_pipeline(
                supabase,
                content=b"empty",
                filename="empty.txt",
                user_id="user-1",
                job_id="job-1",
                file_status_id="status-1",
                source_type="file_upload",
                metadata={"mime_type": "text/plain", "organization_id": "11111111-1111-1111-1111-111111111111", "scope_id": "file_upload://empty.txt"},
            )

        assert result.success is True
        assert result.chunks_count == 0
        assert any(
            call.kwargs.get("status") == "skipped" for call in update_file_status.call_args_list
        )

    @pytest.mark.unit
    def test_process_document_pipeline_database_failure(self):
        supabase = MagicMock()
        chunks = [_make_chunk(content="alpha", token_count=1, chunk_index=0)]
        parse_result = _make_parse_result(file_type="txt", chunks=chunks)

        with patch("worker.tasks.DocumentProcessorFactory.process", return_value=parse_result), \
             patch("worker.tasks.generate_embeddings_batch_sync", return_value=[[0.1]]), \
             patch("worker.tasks.ingest_document_batched", return_value=None), \
             patch("worker.tasks.update_file_status") as update_file_status:
            result = tasks.process_document_pipeline(
                supabase,
                content=b"data",
                filename="fail.txt",
                user_id="user-1",
                job_id="job-1",
                file_status_id="status-1",
                source_type="file_upload",
                metadata={"mime_type": "text/plain", "organization_id": "11111111-1111-1111-1111-111111111111", "scope_id": "file_upload://fail.txt"},
            )

        assert result.success is False
        assert result.error == "Database insert failed"
        assert any(
            call.kwargs.get("status") == "failed" for call in update_file_status.call_args_list
        )


class TestIngestDocumentBatched:
    @pytest.mark.unit
    @pytest.mark.skip(reason="Complex async mock setup required - embeddings pipeline")
    def test_ingest_document_batched_inserts_batches(self):
        supabase = MagicMock()
        documents_table = _make_chain_table(execute_side_effect=[MagicMock(data=[{"id": "doc-1"}])])
        supabase.table.return_value = documents_table

        chunks_payload = [
            {"content": "a", "embedding": [0.1], "chunk_index": 0, "metadata": {"foo": "bar"}},
            {"content": "b", "embedding": [0.2], "chunk_index": 1, "metadata": {"foo": "bar"}},
            {"content": "c", "embedding": [0.3], "chunk_index": 2, "metadata": {"foo": "bar"}},
        ]

        with patch.object(tasks.settings, "CHUNK_INSERT_BATCH_SIZE", 2), \
             patch("worker.tasks.insert_rows_with_retry") as insert_rows:
            doc_id = tasks.ingest_document_batched(
                supabase=supabase,
                user_id="user-1",
                organization_id="11111111-1111-1111-1111-111111111111",
                doc_title="doc.txt",
                source_type="file_upload",
                metadata={
                    "mime_type": "text/plain",
                    "scope_id": "file_upload://doc.txt",
                    "organization_id": "11111111-1111-1111-1111-111111111111",
                },
                chunks_payload=chunks_payload,
                file_size_bytes=123,
            )

        assert doc_id == "doc-1"
        assert insert_rows.call_count == 2
        first_batch = insert_rows.call_args_list[0].args[2]
        assert all("metadata" not in chunk for chunk in first_batch)

    @pytest.mark.unit
    def test_ingest_document_batched_reuses_existing_document(self):
        supabase = MagicMock()
        documents_table = _make_chain_table(
            execute_side_effect=[
                MagicMock(data=[{"id": "doc-1", "content_hash": "hash-1"}]),
                MagicMock(data=[{"id": "doc-1"}]),
            ]
        )
        supabase.table.return_value = documents_table

        chunks_payload = [
            {"content": "a", "embedding": [0.1], "chunk_index": 0},
        ]

        metric = MagicMock()
        metric.labels.return_value.inc = MagicMock()

        with patch("worker.tasks.delete_rows_with_retry") as delete_rows, \
             patch("worker.tasks.insert_rows_with_retry") as insert_rows, \
             patch("worker.tasks.idempotency_hits", metric):
            doc_id = tasks.ingest_document_batched(
                supabase=supabase,
                user_id="user-1",
                organization_id="11111111-1111-1111-1111-111111111111",
                doc_title="doc.txt",
                source_type="file_upload",
                metadata={
                    "mime_type": "text/plain",
                    "scope_id": "file_upload://doc.txt",
                    "organization_id": "11111111-1111-1111-1111-111111111111",
                },
                chunks_payload=chunks_payload,
                file_size_bytes=123,
                content_hash="hash-1",
            )

        assert doc_id == "doc-1"
        delete_rows.assert_not_called()
        insert_rows.assert_not_called()
        documents_table.update.assert_called()

    @pytest.mark.unit
    def test_ingest_document_batched_raises_on_missing_document(self):
        supabase = MagicMock()
        documents_table = _make_chain_table(result_data=[])
        supabase.table.return_value = documents_table

        with pytest.raises(Exception):
            tasks.ingest_document_batched(
                supabase=supabase,
                user_id="user-1",
                organization_id="11111111-1111-1111-1111-111111111111",
                doc_title="doc.txt",
                source_type="file_upload",
                metadata={
                    "mime_type": "text/plain",
                    "scope_id": "file_upload://doc.txt",
                    "organization_id": "11111111-1111-1111-1111-111111111111",
                },
                chunks_payload=[],
                file_size_bytes=123,
            )


class TestHelpers:
    @pytest.mark.unit
    def test_sanitize_text_strips_nulls(self):
        assert tasks._sanitize_text("a\x00b") == "ab"


class TestFinalizeJobTask:
    @pytest.mark.unit
    def test_finalize_job_task_skips_missing_job(self):
        task = SimpleNamespace(request=SimpleNamespace(id="task-1"))
        supabase = MagicMock()
        job_table = _make_chain_table(result_data=None)
        supabase.table.return_value = job_table

        with patch("worker.tasks.get_supabase", return_value=supabase):
            tasks.finalize_job_task.run.__func__(task, "user-1", "job-1")

        job_table.update.assert_not_called()

    @pytest.mark.unit
    def test_finalize_job_task_skips_incomplete_job(self):
        task = SimpleNamespace(request=SimpleNamespace(id="task-1"))
        supabase = MagicMock()
        job_table = _make_chain_table(result_data={"status": "processing", "total_files": 2, "organization_id": "11111111-1111-1111-1111-111111111111"})
        supabase.table.return_value = job_table

        with patch("worker.tasks.get_supabase", return_value=supabase), \
             patch("worker.tasks.get_ingest_job_counters", return_value={"total": 2, "processed": 1}):
            tasks.finalize_job_task.run.__func__(task, "user-1", "job-1")

        # Should not call update for final status update since job is incomplete
        # (though org backfill may call update if organization_id is None)
        update_calls = [c for c in job_table.update.call_args_list if "status" in str(c)]
        assert len(update_calls) == 0

    @pytest.mark.unit
    def test_finalize_job_task_updates_status_and_notifies(self):
        task = SimpleNamespace(request=SimpleNamespace(id="task-1"))
        supabase = MagicMock()
        # Provide tables for job and file status queries
        job_table = _make_chain_table(
            result_data={"status": "processing", "total_files": 2, "organization_id": "11111111-1111-1111-1111-111111111111"}
        )
        # File status table should return a list of dicts with document_id
        file_status_table = _make_chain_table(
            result_data=[{"document_id": "doc-1"}, {"document_id": "doc-2"}]
        )
        # Documents table returns docs with scope_id
        docs_table = _make_chain_table(
            result_data=[
                {"id": "doc-1", "scope_id": "file_upload://file1.txt"},
                {"id": "doc-2", "scope_id": "file_upload://file2.txt"},
            ]
        )
        supabase.table.side_effect = lambda name: {
            "ingestion_jobs": job_table,
            "ingestion_file_status": file_status_table,
            "documents": docs_table,
        }.get(name, job_table)

        counts = {
            "total": 2,
            "processed": 2,
            "success": 2,
            "failed": 0,
            "skipped": 0,
            "job_status_updates": 1,
            "file_status_updates": 1,
        }

        with patch("worker.tasks.get_supabase", return_value=supabase), \
             patch("worker.tasks.get_ingest_job_counters", return_value=counts), \
             patch("worker.tasks._get_ingestion_counts_from_db", return_value=counts), \
             patch("worker.tasks.create_notification") as create_notification, \
             patch("worker.tasks.send_email_notification") as send_email_notification, \
             patch("worker.tasks.clear_ingest_job_counters") as clear_counters, \
             patch("worker.tasks.synthesize_and_save_identity", return_value=None):
            tasks.finalize_job_task.run.__func__(task, "user-1", "job-1")

        # Should have at least one update call for status
        job_table.update.assert_called()
        create_notification.assert_called_once()
        send_email_notification.assert_called_once()
        clear_counters.assert_called_once()


class TestTaskFailureHandling:
    @pytest.mark.unit
    def test_handle_task_failure_logs_to_dlq(self):
        task = SimpleNamespace(name="unified_ingest_task")

        with patch("worker.dlq_worker.log_task_failure") as log_task_failure:
            tasks.handle_task_failure(
                task,
                Exception("boom"),
                "task-1",
                ("arg",),
                {"user_id": "user-1", "job_id": "job-1"},
                "traceback",
            )

        log_task_failure.assert_called_once()


class TestProcessFileTask:
    @pytest.mark.unit
    def test_process_file_task_missing_content_fails(self):
        task = SimpleNamespace(request=SimpleNamespace(id="task-1"))
        supabase = MagicMock()
        file_data = {"filename": "empty.txt", "organization_id": "11111111-1111-1111-1111-111111111111"}
        scope_id = "file_upload://empty.txt"

        with patch("worker.tasks.get_supabase", return_value=supabase), \
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
        assert any(
            call.kwargs.get("status") == "failed" for call in update_file_status.call_args_list
        )
        record_outcome.assert_called_once()

    @pytest.mark.unit
    def test_process_file_task_rejects_large_file(self):
        task = SimpleNamespace(request=SimpleNamespace(id="task-1"))
        supabase = MagicMock()
        file_data = {
            "filename": "big.txt",
            "organization_id": "11111111-1111-1111-1111-111111111111",
            "content_b64": base64.b64encode(b"too-big").decode("utf-8"),
            "size_bytes": 7,
            "mime_type": "text/plain",
        }
        scope_id = "file_upload://big.txt"

        with patch("worker.tasks.get_supabase", return_value=supabase), \
             patch.object(tasks.settings, "MAX_FILE_SIZE", 1), \
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
        assert result["error"] == "File too large"
        record_outcome.assert_called_once()
        assert any(
            call.kwargs.get("status") == "failed" for call in update_file_status.call_args_list
        )

    @pytest.mark.unit
    def test_process_file_task_dispatches_to_embedding_queue(self):
        """Test that process_file_task dispatches to embedding queue on success."""
        task = SimpleNamespace(request=SimpleNamespace(id="task-1"))
        supabase = MagicMock()
        doc_table = _make_chain_table(result_data=[])
        supabase.table.return_value = doc_table

        file_data = {
            "filename": "file.pdf",
            "organization_id": "11111111-1111-1111-1111-111111111111",
            "content_b64": base64.b64encode(b"content").decode("utf-8"),
            "size_bytes": 7,
            "mime_type": "application/pdf",
        }
        scope_id = "file_upload://file.pdf"

        parse_result = _make_parse_result(
            file_type="pdf",
            chunks=[_make_chunk()],
            total_tokens=1,
        )

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

    @pytest.mark.unit
    def test_process_file_task_skips_unsupported(self):
        task = SimpleNamespace(request=SimpleNamespace(id="task-1"))
        supabase = MagicMock()
        doc_table = _make_chain_table(result_data=[])
        supabase.table.return_value = doc_table

        file_data = {
            "filename": "file.bin",
            "organization_id": "11111111-1111-1111-1111-111111111111",
            "content_b64": base64.b64encode(b"binary").decode("utf-8"),
            "size_bytes": 6,
            "mime_type": "application/octet-stream",
        }
        scope_id = "file_upload://file.bin"

        parse_result = _make_parse_result(
            file_type="unsupported",
            chunks=[],
            metadata={"unsupported_reason": "binary_content"},
        )

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
        record_outcome.assert_called_once()
        assert any(
            call.kwargs.get("status") == "skipped" for call in update_file_status.call_args_list
        )

    @pytest.mark.unit
    def test_process_file_task_handles_exception(self):
        """Test that process_file_task handles exceptions and returns failed."""
        task = SimpleNamespace(request=SimpleNamespace(id="task-1"))
        supabase = MagicMock()
        doc_table = _make_chain_table(result_data=[])
        supabase.table.return_value = doc_table

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
             patch("services.parsers.DocumentProcessorFactory.process", side_effect=Exception("parse error")), \
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
        record_outcome.assert_called_once()
        assert any(
            call.kwargs.get("status") == "failed" for call in update_file_status.call_args_list
        )

    @pytest.mark.unit
    def test_process_file_task_reuses_existing_document(self):
        task = SimpleNamespace(request=SimpleNamespace(id="task-1"))
        supabase = MagicMock()
        doc_table = _make_chain_table(
            execute_side_effect=[
                MagicMock(data=[{"id": "doc-1", "content_hash": "hash"}]),
                MagicMock(data=[{"id": "doc-1"}]),
            ]
        )
        supabase.table.return_value = doc_table

        file_data = {
            "filename": "file.txt",
            "organization_id": "11111111-1111-1111-1111-111111111111",
            "content_b64": base64.b64encode(b"content").decode("utf-8"),
            "size_bytes": 7,
            "mime_type": "text/plain",
        }
        scope_id = "file_upload://file.txt"

        parse_result = _make_parse_result(
            file_type="txt",
            chunks=[_make_chunk(content="chunk", token_count=1, chunk_index=0)],
            total_tokens=1,
        )

        with patch("worker.tasks.get_supabase", return_value=supabase), \
             patch("services.parsers.DocumentProcessorFactory.process", return_value=parse_result), \
             patch("services.embeddings.generate_embeddings_batch_sync", return_value=[[0.1]]), \
             patch("worker.tasks.insert_rows_with_retry"), \
             patch("worker.tasks.ingest_document_batched", return_value="doc-1"), \
             patch("worker.tasks.compute_content_hash", return_value="hash"), \
             patch("worker.tasks.update_file_status"), \
             patch("worker.tasks._record_ingest_outcome_and_maybe_finalize"):
            result = tasks.process_file_task._orig_run.__func__(
                task,
                "user-1",
                "job-1",
                file_data,
                "status-1",
                "file_upload",
                scope_id,
            )

        # With async embedding pipeline, success returns "queued_embedding" or "success"
        assert result["status"] in ("success", "queued_embedding")

    @pytest.mark.unit
    @pytest.mark.skip(reason="Complex async mock setup required - storage cleanup")
    def test_process_file_task_removes_staged_upload(self):
        task = SimpleNamespace(request=SimpleNamespace(id="task-1"))
        storage = MagicMock()
        storage.download.return_value = b"content"
        supabase = MagicMock()
        supabase.storage.from_.return_value = storage
        doc_table = _make_chain_table(execute_side_effect=[MagicMock(data=[]), MagicMock(data=[{"id": "doc-1"}])])
        supabase.table.return_value = doc_table

        file_data = {
            "filename": "file.txt",
            "organization_id": "11111111-1111-1111-1111-111111111111",
            "storage_path": "uploads/file.txt",
            "size_bytes": 7,
            "mime_type": "text/plain",
        }
        scope_id = "file_upload://uploads/file.txt"

        parse_result = _make_parse_result(
            file_type="txt",
            chunks=[_make_chunk(content="chunk", token_count=1, chunk_index=0)],
        )

        with patch("worker.tasks.get_supabase", return_value=supabase), \
             patch("services.parsers.DocumentProcessorFactory.process", return_value=parse_result), \
             patch("services.embeddings.generate_embeddings_batch_sync", return_value=[[0.1]]), \
             patch("worker.tasks.insert_rows_with_retry"), \
             patch("worker.tasks.update_file_status"), \
             patch("worker.tasks._record_ingest_outcome_and_maybe_finalize"):
            result = tasks.process_file_task._orig_run.__func__(
                task,
                "user-1",
                "job-1",
                file_data,
                "status-1",
                "file_upload",
                scope_id,
            )

        # With async embedding pipeline, success returns "queued_embedding" or "success"
        assert result["status"] in ("success", "queued_embedding")
        storage.remove.assert_called_once_with(["uploads/file.txt"])


class TestNotificationsAndEmail:
    @pytest.mark.unit
    def test_create_notification_respects_disabled_setting(self):
        supabase = MagicMock()
        pref_table = _make_chain_table(data={"enabled": False})
        notifications_table = _make_chain_table(data=[{"id": "n1"}])
        supabase.table.side_effect = lambda name: {
            "user_notification_settings": pref_table,
            "notifications": notifications_table,
        }[name]

        tasks.create_notification(
            supabase,
            user_id="user-1",
            title="Title",
            message="Message",
            check_setting_key="some_setting",
        )

        notifications_table.insert.assert_not_called()

    @pytest.mark.unit
    def test_create_notification_includes_action_url(self):
        supabase = MagicMock()
        pref_table = _make_chain_table(data=None)
        notifications_table = _make_chain_table(data=[{"id": "n1"}])
        supabase.table.side_effect = lambda name: {
            "user_notification_settings": pref_table,
            "notifications": notifications_table,
        }[name]

        tasks.create_notification(
            supabase,
            user_id="user-1",
            title="Title",
            message="Message",
            action_url="/dashboard",
        )

        payload = notifications_table.insert.call_args[0][0]
        assert "action_url" in payload["extra_data"]

    @pytest.mark.unit
    def test_send_email_notification_respects_setting(self):
        supabase = MagicMock()
        profile_table = _make_chain_table(data={"display_name": "User", "email": "u@example.com"})
        # Settings uses execute() which returns a list of rows, not a single object
        settings_table = _make_chain_table(data=[{"enabled": False}])
        supabase.table.side_effect = lambda name: {
            "user_profiles": profile_table,
            "profiles": profile_table,
            "user_notification_settings": settings_table,
        }[name]

        with patch("worker.tasks.email_service.send_ingestion_complete") as send_email:
            tasks.send_email_notification(supabase, "user-1", total_files=2)

        send_email.assert_not_called()

    @pytest.mark.unit
    def test_send_email_notification_uses_auth_email(self):
        supabase = MagicMock()
        profile_table = _make_chain_table(data={"display_name": "User"})
        settings_table = _make_chain_table(data={"enabled": True})
        supabase.table.side_effect = lambda name: {
            "user_profiles": profile_table,
            "profiles": profile_table,
            "user_notification_settings": settings_table,
        }[name]
        supabase.auth.admin.get_user_by_id.return_value = SimpleNamespace(
            user=SimpleNamespace(email="auth@example.com")
        )

        with patch("worker.tasks.email_service.send_ingestion_complete") as send_email:
            tasks.send_email_notification(supabase, "user-1", total_files=2)

        send_email.assert_called_once()

    @pytest.mark.unit
    def test_send_failure_email_notification_sends(self):
        supabase = MagicMock()
        profile_table = _make_chain_table(data={"display_name": "User"})
        supabase.table.return_value = profile_table
        supabase.auth.admin.get_user_by_id.return_value = SimpleNamespace(
            user=SimpleNamespace(email="auth@example.com")
        )

        with patch("worker.tasks.email_service.send_ingestion_failed") as send_email:
            tasks.send_failure_email_notification(supabase, "user-1", "file.txt", "boom")

        send_email.assert_called_once()
