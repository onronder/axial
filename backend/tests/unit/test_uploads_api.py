"""
Unit tests for uploads API endpoints and helpers.

Focuses on:
- Input sanitization
- Idempotency
- Presigned upload flow
- Crawl config deletion
"""

import itertools
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch, AsyncMock

import pytest
from fastapi import HTTPException
from starlette.requests import Request

import api.v1.uploads as uploads_module
import api.v1.integrations as integrations_module


TEST_USER_ID = "00000000-0000-0000-0000-000000000001"
_REQUEST_COUNTER = itertools.count(1)


def make_request(headers=None):
    headers = headers or {}
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    client_ip = f"127.0.0.{next(_REQUEST_COUNTER)}"
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/uploads/file/reference",
        "headers": raw_headers,
        "client": (client_ip, 1234),
    }
    return Request(scope)


class TestHelpers:
    def test_sanitize_filename_blocks_path_traversal(self):
        name = "../../etc/passwd"
        assert uploads_module.sanitize_filename(name) == "passwd"

    def test_sanitize_filename_handles_empty(self):
        assert uploads_module.sanitize_filename("") == "unnamed_file"

    def test_sanitize_filename_preserves_extension(self):
        assert uploads_module.sanitize_filename("report.pdf") == "report.pdf"

    def test_sanitize_filename_handles_unquote_failure(self):
        with patch("urllib.parse.unquote", side_effect=Exception("boom")):
            assert uploads_module.sanitize_filename("%%") == "__"

    def test_sanitize_filename_handles_dot_only(self):
        assert uploads_module.sanitize_filename("....") == "unnamed_file"

    def test_get_idempotency_key_accepts_header(self):
        request = make_request({"Idempotency-Key": "  key-123 "})
        assert uploads_module.get_idempotency_key(request) == "key-123"

    def test_find_existing_ingestion_job_returns_latest(self):
        supabase = MagicMock()
        table = supabase.table.return_value
        table.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = Mock(
            data=[{"id": "job-1", "status": "pending"}]
        )

        result = uploads_module.find_existing_ingestion_job(
            supabase, TEST_USER_ID, "file_upload", "key-123"
        )
        assert result["id"] == "job-1"

    def test_find_existing_ingestion_job_returns_none_without_key(self):
        supabase = MagicMock()
        assert uploads_module.find_existing_ingestion_job(supabase, TEST_USER_ID, "file_upload", None) is None


class TestPresignedUploadFlow:
    @pytest.mark.asyncio
    async def test_generate_upload_url_rejects_invalid_type(self):
        request = make_request()
        body = uploads_module.UploadUrlRequest(
            filename="file.exe",
            file_type="application/x-executable",
            file_size=10,
        )

        with patch("api.v1.uploads.get_supabase", return_value=MagicMock()), \
             patch("api.v1.uploads.check_can_upload", new=AsyncMock(return_value={"allowed": True})):
            with pytest.raises(HTTPException):
                await uploads_module.generate_upload_url(request, body, user_id=TEST_USER_ID)

    @pytest.mark.asyncio
    async def test_generate_upload_url_success(self):
        request = make_request()
        body = uploads_module.UploadUrlRequest(
            filename="file.pdf",
            file_type="application/pdf",
            file_size=10,
        )

        supabase = MagicMock()
        supabase.storage.from_.return_value.create_signed_upload_url.return_value = {
            "signed_url": "https://signed.example.com",
        }

        with patch("api.v1.uploads.get_supabase", return_value=supabase), \
             patch("api.v1.uploads.check_can_upload", new=AsyncMock(return_value={"allowed": True})):
            response = await uploads_module.generate_upload_url(request, body, user_id=TEST_USER_ID)

        assert response.upload_url == "https://signed.example.com"
        assert response.storage_path.startswith(f"uploads/{TEST_USER_ID}/")

    @pytest.mark.asyncio
    async def test_generate_upload_url_missing_signed_url(self):
        request = make_request()
        body = uploads_module.UploadUrlRequest(
            filename="file.pdf",
            file_type="application/pdf",
            file_size=10,
        )

        supabase = MagicMock()
        supabase.storage.from_.return_value.create_signed_upload_url.return_value = {"no_url": True}

        with patch("api.v1.uploads.get_supabase", return_value=supabase), \
             patch("api.v1.uploads.check_can_upload", new=AsyncMock(return_value={"allowed": True})):
            with pytest.raises(HTTPException):
                await uploads_module.generate_upload_url(request, body, user_id=TEST_USER_ID)

    @pytest.mark.asyncio
    async def test_generate_upload_url_quota_blocked(self):
        request = make_request()
        body = uploads_module.UploadUrlRequest(
            filename="file.pdf",
            file_type="application/pdf",
            file_size=10,
        )

        with patch("api.v1.uploads.get_supabase", return_value=MagicMock()), \
             patch("api.v1.uploads.check_can_upload", new=AsyncMock(return_value={"allowed": False, "reason": "limit"})):
            with pytest.raises(HTTPException):
                await uploads_module.generate_upload_url(request, body, user_id=TEST_USER_ID)

    @pytest.mark.asyncio
    async def test_generate_upload_url_none_response(self):
        request = make_request()
        body = uploads_module.UploadUrlRequest(
            filename="file.pdf",
            file_type="application/pdf",
            file_size=10,
        )

        supabase = MagicMock()
        supabase.storage.from_.return_value.create_signed_upload_url.return_value = None

        with patch("api.v1.uploads.get_supabase", return_value=supabase), \
             patch("api.v1.uploads.check_can_upload", new=AsyncMock(return_value={"allowed": True})):
            with pytest.raises(HTTPException):
                await uploads_module.generate_upload_url(request, body, user_id=TEST_USER_ID)

    @pytest.mark.asyncio
    async def test_generate_upload_url_exception(self):
        request = make_request()
        body = uploads_module.UploadUrlRequest(
            filename="file.pdf",
            file_type="application/pdf",
            file_size=10,
        )

        supabase = MagicMock()
        supabase.storage.from_.return_value.create_signed_upload_url.side_effect = RuntimeError("boom")

        with patch("api.v1.uploads.get_supabase", return_value=supabase), \
             patch("api.v1.uploads.check_can_upload", new=AsyncMock(return_value={"allowed": True})):
            with pytest.raises(HTTPException):
                await uploads_module.generate_upload_url(request, body, user_id=TEST_USER_ID)

    @pytest.mark.asyncio
    async def test_ingest_file_reference_dispatches_task(self):
        request = make_request()
        body = uploads_module.FileReferenceRequest(
            storage_path=f"uploads/{TEST_USER_ID}/uuid/file.txt",
            filename="file.txt",
            file_size=10,
            metadata={},
        )

        supabase = MagicMock()
        supabase.storage.from_.return_value.list.return_value = [{"name": "file.txt"}]
        table = MagicMock()
        table.insert.return_value.execute.return_value = Mock(data=[{"id": "job-2"}])
        supabase.table.return_value = table

        with patch("api.v1.uploads.get_supabase", return_value=supabase), \
             patch("api.v1.uploads.check_can_upload", new=AsyncMock(return_value={"allowed": True})), \
             patch("worker.tasks.unified_ingest_task") as mock_task:
            mock_task.delay.return_value = SimpleNamespace(id="task-2")

            response = await uploads_module.ingest_file_reference(request, body, user_id=TEST_USER_ID)

        assert response.status == "queued"
        assert response.doc_id == "job-2"

    @pytest.mark.asyncio
    async def test_ingest_file_reference_404_when_missing(self):
        request = make_request()
        body = uploads_module.FileReferenceRequest(
            storage_path=f"uploads/{TEST_USER_ID}/uuid/missing.txt",
            filename="missing.txt",
            file_size=10,
            metadata={},
        )

        supabase = MagicMock()
        supabase.storage.from_.return_value.list.return_value = [{"name": "other.txt"}]

        with patch("api.v1.uploads.get_supabase", return_value=supabase), \
             patch("api.v1.uploads.check_can_upload", new=AsyncMock(return_value={"allowed": True})):
            with pytest.raises(HTTPException):
                await uploads_module.ingest_file_reference(request, body, user_id=TEST_USER_ID)

    @pytest.mark.asyncio
    async def test_ingest_file_reference_cleans_up_on_quota_block(self):
        request = make_request()
        body = uploads_module.FileReferenceRequest(
            storage_path=f"uploads/{TEST_USER_ID}/uuid/file.txt",
            filename="file.txt",
            file_size=10,
            metadata={},
        )

        supabase = MagicMock()
        supabase.storage.from_.return_value.list.return_value = [{"name": "file.txt"}]
        supabase.storage.from_.return_value.remove.side_effect = Exception("boom")

        with patch("api.v1.uploads.get_supabase", return_value=supabase), \
             patch("api.v1.uploads.check_can_upload", new=AsyncMock(return_value={"allowed": False, "reason": "limit"})):
            with pytest.raises(HTTPException):
                await uploads_module.ingest_file_reference(request, body, user_id=TEST_USER_ID)

        supabase.storage.from_.return_value.remove.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_file_reference_continues_on_storage_list_error(self):
        request = make_request()
        body = uploads_module.FileReferenceRequest(
            storage_path=f"uploads/{TEST_USER_ID}/uuid/file.txt",
            filename="file.txt",
            file_size=10,
            metadata={},
        )

        supabase = MagicMock()
        supabase.storage.from_.return_value.list.side_effect = Exception("boom")
        supabase.table.return_value.insert.return_value.execute.return_value = Mock(data=[{"id": "job-2"}])

        with patch("api.v1.uploads.get_supabase", return_value=supabase), \
             patch("api.v1.uploads.check_can_upload", new=AsyncMock(return_value={"allowed": True})), \
             patch("worker.tasks.unified_ingest_task") as mock_task:
            mock_task.delay.return_value = SimpleNamespace(id="task-2")
            response = await uploads_module.ingest_file_reference(request, body, user_id=TEST_USER_ID)

        assert response.status == "queued"

    @pytest.mark.asyncio
    async def test_ingest_file_reference_job_creation_failure(self):
        request = make_request()
        body = uploads_module.FileReferenceRequest(
            storage_path=f"uploads/{TEST_USER_ID}/uuid/file.txt",
            filename="file.txt",
            file_size=10,
            metadata={},
        )

        supabase = MagicMock()
        supabase.storage.from_.return_value.list.return_value = [{"name": "file.txt"}]
        supabase.table.return_value.insert.return_value.execute.return_value = Mock(data=None)

        with patch("api.v1.uploads.get_supabase", return_value=supabase), \
             patch("api.v1.uploads.check_can_upload", new=AsyncMock(return_value={"allowed": True})):
            with pytest.raises(HTTPException) as exc:
                await uploads_module.ingest_file_reference(request, body, user_id=TEST_USER_ID)

        assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_ingest_file_reference_dispatch_failure_removes_storage(self):
        request = make_request()
        body = uploads_module.FileReferenceRequest(
            storage_path=f"uploads/{TEST_USER_ID}/uuid/file.txt",
            filename="file.txt",
            file_size=10,
            metadata={},
        )

        supabase = MagicMock()
        supabase.storage.from_.return_value.list.return_value = [{"name": "file.txt"}]
        supabase.storage.from_.return_value.remove.side_effect = Exception("boom")
        supabase.table.return_value.insert.return_value.execute.return_value = Mock(data=[{"id": "job-2"}])

        with patch("api.v1.uploads.get_supabase", return_value=supabase), \
             patch("api.v1.uploads.check_can_upload", new=AsyncMock(return_value={"allowed": True})), \
             patch("worker.tasks.unified_ingest_task") as mock_task:
            mock_task.delay.side_effect = Exception("boom")
            with pytest.raises(HTTPException) as exc:
                await uploads_module.ingest_file_reference(request, body, user_id=TEST_USER_ID)

        assert exc.value.status_code == 503
        supabase.storage.from_.return_value.remove.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_file_reference_includes_idempotency_key(self):
        request = make_request({"Idempotency-Key": "key-1"})
        body = uploads_module.FileReferenceRequest(
            storage_path=f"uploads/{TEST_USER_ID}/uuid/file.txt",
            filename="file.txt",
            file_size=10,
            metadata={},
        )

        supabase = MagicMock()
        supabase.storage.from_.return_value.list.return_value = [{"name": "file.txt"}]
        supabase.table.return_value.insert.return_value.execute.return_value = Mock(data=[{"id": "job-2"}])

        with patch("api.v1.uploads.get_supabase", return_value=supabase), \
             patch("api.v1.uploads.check_can_upload", new=AsyncMock(return_value={"allowed": True})), \
             patch("api.v1.uploads.find_existing_ingestion_job", return_value=None), \
             patch("worker.tasks.unified_ingest_task") as mock_task:
            mock_task.delay.return_value = SimpleNamespace(id="task-2")
            await uploads_module.ingest_file_reference(request, body, user_id=TEST_USER_ID)

        payload = supabase.table.return_value.insert.call_args[0][0]
        assert payload["idempotency_key"] == "key-1"

    @pytest.mark.asyncio
    async def test_ingest_file_reference_idempotency_returns_existing(self):
        request = make_request({"Idempotency-Key": "key-1"})
        body = uploads_module.FileReferenceRequest(
            storage_path=f"uploads/{TEST_USER_ID}/uuid/file.txt",
            filename="file.txt",
            file_size=10,
            metadata={},
        )

        supabase = MagicMock()
        supabase.storage.from_.return_value.list.return_value = [{"name": "file.txt"}]
        supabase.table.return_value.insert.return_value.execute.return_value = Mock(data=[{"id": "job-2"}])

        with patch("api.v1.uploads.get_supabase", return_value=supabase), \
             patch("api.v1.uploads.check_can_upload", new=AsyncMock(return_value={"allowed": True})), \
             patch("api.v1.uploads.find_existing_ingestion_job", return_value={"id": "job-2", "status": "queued"}):
            response = await uploads_module.ingest_file_reference(request, body, user_id=TEST_USER_ID)

        assert response.doc_id == "job-2"


class TestDeleteCrawlConfig:
    @pytest.mark.asyncio
    async def test_delete_crawl_config_not_found(self):
        supabase = MagicMock()
        table = MagicMock()
        table.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data=None
        )
        supabase.table.return_value = table

        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException):
                await integrations_module.delete_crawl_config("cfg-1", user_id="user-1")

    @pytest.mark.asyncio
    async def test_delete_crawl_config_revokes_task(self):
        supabase = MagicMock()
        table = MagicMock()
        table.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data={"id": "cfg-1", "celery_task_id": "task-1", "status": "processing"}
        )
        table.delete.return_value.eq.return_value.eq.return_value.execute.return_value = Mock(data=[])
        supabase.table.return_value = table

        mock_result = MagicMock()
        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("celery.result.AsyncResult", return_value=mock_result):
            response = await integrations_module.delete_crawl_config("cfg-1", user_id="user-1")

        assert response["status"] == "success"
        mock_result.revoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_crawl_config_revoke_failure(self):
        supabase = MagicMock()
        table = MagicMock()
        table.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data={"id": "cfg-1", "celery_task_id": "task-1", "status": "processing"}
        )
        table.delete.return_value.eq.return_value.eq.return_value.execute.return_value = Mock(data=[])
        supabase.table.return_value = table

        mock_result = MagicMock()
        mock_result.revoke.side_effect = Exception("boom")
        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("celery.result.AsyncResult", return_value=mock_result):
            response = await integrations_module.delete_crawl_config("cfg-1", user_id="user-1")

        assert response["status"] == "success"

    @pytest.mark.asyncio
    async def test_delete_crawl_config_delete_failure(self):
        supabase = MagicMock()
        table = MagicMock()
        table.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data={"id": "cfg-1", "celery_task_id": None, "status": "completed"}
        )
        table.delete.return_value.eq.return_value.eq.return_value.execute.side_effect = Exception("boom")
        supabase.table.return_value = table

        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException):
                await integrations_module.delete_crawl_config("cfg-1", user_id="user-1")
