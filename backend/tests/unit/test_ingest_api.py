"""
Unit tests for ingest API endpoints and helpers.

Focuses on:
- Input sanitization
- Idempotency
- Web crawl and file upload dispatch
- Presigned upload flow
- Crawl config deletion
"""

import io
import sys
import itertools
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch, AsyncMock

import pytest
from fastapi import HTTPException, UploadFile
from starlette.requests import Request

if "magic" not in sys.modules:
    sys.modules["magic"] = SimpleNamespace(from_buffer=lambda *args, **kwargs: "text/plain")

import api.v1.ingest as ingest_module


TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


_REQUEST_COUNTER = itertools.count(1)


def make_request(headers=None):
    headers = headers or {}
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    client_ip = f"127.0.0.{next(_REQUEST_COUNTER)}"
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/ingest",
        "headers": raw_headers,
        "client": (client_ip, 1234),
    }
    return Request(scope)


class TestHelpers:
    def test_sanitize_filename_blocks_path_traversal(self):
        name = "../../etc/passwd"
        assert ingest_module.sanitize_filename(name) == "passwd"

    def test_sanitize_filename_handles_empty(self):
        assert ingest_module.sanitize_filename("") == "unnamed_file"

    def test_sanitize_filename_preserves_extension(self):
        assert ingest_module.sanitize_filename("report.pdf") == "report.pdf"

    def test_get_idempotency_key_accepts_header(self):
        request = make_request({"Idempotency-Key": "  key-123 "})
        assert ingest_module.get_idempotency_key(request) == "key-123"

    def test_find_existing_ingestion_job_returns_latest(self):
        supabase = MagicMock()
        table = supabase.table.return_value
        table.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = Mock(
            data=[{"id": "job-1", "status": "pending"}]
        )

        result = ingest_module.find_existing_ingestion_job(
            supabase, TEST_USER_ID, "file", "key-123"
        )
        assert result["id"] == "job-1"

    def test_sanitize_filename_handles_bad_unquote(self):
        with patch("urllib.parse.unquote", side_effect=Exception("boom")):
            assert ingest_module.sanitize_filename("file.txt") == "file.txt"

    def test_sanitize_filename_returns_unnamed_for_dots(self):
        assert ingest_module.sanitize_filename("...") == "unnamed_file"

    def test_find_existing_ingestion_job_returns_none_without_key(self):
        supabase = MagicMock()
        assert ingest_module.find_existing_ingestion_job(supabase, TEST_USER_ID, "file", None) is None


class TestIngestWebUrl:
    @pytest.mark.asyncio
    async def test_ingest_url_queues_web_crawl(self):
        request = make_request()
        with patch("api.v1.ingest.get_supabase", return_value=MagicMock()), \
             patch("api.v1.ingest.team_service.get_user_team", new=AsyncMock(return_value=None)), \
             patch("api.v1.ingest.check_quota", new=AsyncMock()), \
             patch("api.v1.ingest.check_feature_access", new=AsyncMock(return_value={"allowed": True})), \
             patch("api.v1.ingest.queue_web_crawl", return_value={"task_id": "task-1", "crawl_id": "crawl-1"}), \
             patch("api.v1.ingest.WebConnector") as mock_connector:
            connector = mock_connector.return_value
            connector.normalize_url.return_value = "https://example.com"
            connector.is_safe_url.return_value = True

            response = await ingest_module.ingest_document(
                request,
                url="https://example.com",
                metadata="{}",
                user_id=TEST_USER_ID,
            )

        assert response.status == "queued"
        assert response.doc_id == "crawl-1"

    @pytest.mark.asyncio
    async def test_ingest_url_safe_parsing_defaults(self):
        request = make_request()
        with patch("api.v1.ingest.get_supabase", return_value=MagicMock()), \
             patch("api.v1.ingest.team_service.get_user_team", new=AsyncMock(return_value=None)), \
             patch("api.v1.ingest.check_quota", new=AsyncMock()), \
             patch("api.v1.ingest.check_feature_access", new=AsyncMock(return_value={"allowed": True})), \
             patch("api.v1.ingest.queue_web_crawl", return_value={"task_id": "task-1", "crawl_id": "crawl-1"}) as queue_crawl, \
             patch("api.v1.ingest.WebConnector") as mock_connector:
            connector = mock_connector.return_value
            connector.normalize_url.return_value = "https://example.com"
            connector.is_safe_url.return_value = True

            response = await ingest_module.ingest_document(
                request,
                url="https://example.com",
                metadata='{"crawl_type": "recursive", "depth": "bad", "max_pages": "bad", '
                         '"allow_subdomains": true, "respect_robots": "yes"}',
                user_id=TEST_USER_ID,
            )

        assert response.status == "queued"
        _, kwargs = queue_crawl.call_args
        assert kwargs["max_depth"] == 1
        assert kwargs["max_pages"] == 500
        assert kwargs["allow_subdomains"] is True
        assert kwargs["respect_robots"] is True

    @pytest.mark.asyncio
    async def test_ingest_url_rejects_invalid_crawl_type(self):
        request = make_request()
        with patch("api.v1.ingest.get_supabase", return_value=MagicMock()), \
             patch("api.v1.ingest.team_service.get_user_team", new=AsyncMock(return_value=None)), \
             patch("api.v1.ingest.check_quota", new=AsyncMock()), \
             patch("api.v1.ingest.check_feature_access", new=AsyncMock(return_value={"allowed": True})), \
             patch("api.v1.ingest.WebConnector") as mock_connector:
            connector = mock_connector.return_value
            connector.normalize_url.return_value = "https://example.com"
            connector.is_safe_url.return_value = True

            with pytest.raises(HTTPException):
                await ingest_module.ingest_document(
                    request,
                    url="https://example.com",
                    metadata='{"crawl_type": "bad"}',
                    user_id=TEST_USER_ID,
                )

    @pytest.mark.asyncio
    async def test_ingest_blocks_viewer_role(self):
        request = make_request()
        with patch("api.v1.ingest.get_supabase", return_value=MagicMock()), \
             patch("api.v1.ingest.team_service.get_user_team", new=AsyncMock(return_value={"user_role": "viewer"})), \
             patch("api.v1.ingest.check_quota", new=AsyncMock()):
            with pytest.raises(HTTPException):
                await ingest_module.ingest_document(
                    request,
                    url="https://example.com",
                    metadata="{}",
                    user_id=TEST_USER_ID,
                )

    @pytest.mark.asyncio
    async def test_ingest_url_blocks_feature(self):
        request = make_request()
        with patch("api.v1.ingest.get_supabase", return_value=MagicMock()), \
             patch("api.v1.ingest.team_service.get_user_team", new=AsyncMock(return_value=None)), \
             patch("api.v1.ingest.check_quota", new=AsyncMock()), \
             patch("api.v1.ingest.check_feature_access", new=AsyncMock(return_value={"allowed": False, "reason": "no"})):
            with pytest.raises(HTTPException):
                await ingest_module.ingest_document(
                    request,
                    url="https://example.com",
                    metadata="{}",
                    user_id=TEST_USER_ID,
                )

    @pytest.mark.asyncio
    async def test_ingest_url_invalid_url(self):
        request = make_request()
        with patch("api.v1.ingest.get_supabase", return_value=MagicMock()), \
             patch("api.v1.ingest.team_service.get_user_team", new=AsyncMock(return_value=None)), \
             patch("api.v1.ingest.check_quota", new=AsyncMock()), \
             patch("api.v1.ingest.check_feature_access", new=AsyncMock(return_value={"allowed": True})), \
             patch("api.v1.ingest.WebConnector") as mock_connector:
            connector = mock_connector.return_value
            connector.normalize_url.return_value = None

            with pytest.raises(HTTPException):
                await ingest_module.ingest_document(
                    request,
                    url="bad",
                    metadata="{}",
                    user_id=TEST_USER_ID,
                )

    @pytest.mark.asyncio
    async def test_ingest_url_queue_failure(self):
        request = make_request()
        with patch("api.v1.ingest.get_supabase", return_value=MagicMock()), \
             patch("api.v1.ingest.team_service.get_user_team", new=AsyncMock(return_value=None)), \
             patch("api.v1.ingest.check_quota", new=AsyncMock()), \
             patch("api.v1.ingest.check_feature_access", new=AsyncMock(return_value={"allowed": True})), \
             patch("api.v1.ingest.queue_web_crawl", side_effect=Exception("down")), \
             patch("api.v1.ingest.WebConnector") as mock_connector:
            connector = mock_connector.return_value
            connector.normalize_url.return_value = "https://example.com"
            connector.is_safe_url.return_value = True

            with pytest.raises(HTTPException):
                await ingest_module.ingest_document(
                    request,
                    url="https://example.com",
                    metadata="{}",
                    user_id=TEST_USER_ID,
                )

    @pytest.mark.asyncio
    async def test_ingest_url_unsafe_rejected(self):
        request = make_request()
        with patch("api.v1.ingest.get_supabase", return_value=MagicMock()), \
             patch("api.v1.ingest.team_service.get_user_team", new=AsyncMock(return_value=None)), \
             patch("api.v1.ingest.check_quota", new=AsyncMock()), \
             patch("api.v1.ingest.check_feature_access", new=AsyncMock(return_value={"allowed": True})), \
             patch("api.v1.ingest.WebConnector") as mock_connector:
            connector = mock_connector.return_value
            connector.normalize_url.return_value = "https://example.com"
            connector.is_safe_url.return_value = False

            with pytest.raises(HTTPException):
                await ingest_module.ingest_document(
                    request,
                    url="https://example.com",
                    metadata="{}",
                    user_id=TEST_USER_ID,
                )

    @pytest.mark.asyncio
    async def test_ingest_url_metadata_parse_failure(self):
        request = make_request()
        with patch("api.v1.ingest.get_supabase", return_value=MagicMock()), \
             patch("api.v1.ingest.team_service.get_user_team", new=AsyncMock(return_value=None)), \
             patch("api.v1.ingest.check_quota", new=AsyncMock()), \
             patch("api.v1.ingest.check_feature_access", new=AsyncMock(return_value={"allowed": True})), \
             patch("api.v1.ingest.queue_web_crawl", return_value={"task_id": "task-1", "crawl_id": "crawl-1"}), \
             patch("api.v1.ingest.WebConnector") as mock_connector:
            connector = mock_connector.return_value
            connector.normalize_url.return_value = "https://example.com"
            connector.is_safe_url.return_value = True

            response = await ingest_module.ingest_document(
                request,
                url="https://example.com",
                metadata="not-json",
                user_id=TEST_USER_ID,
            )

        assert response.status == "queued"


class TestIngestFileUpload:
    @pytest.mark.asyncio
    async def test_ingest_file_upload_queues_task(self):
        request = make_request()
        file = UploadFile(filename="test.txt", file=io.BytesIO(b"hello"))

        supabase = MagicMock()
        storage_bucket = MagicMock()
        supabase.storage.from_.return_value = storage_bucket
        table = MagicMock()
        table.insert.return_value.execute.return_value = Mock(data=[{"id": "job-1"}])
        supabase.table.return_value = table

        with patch("api.v1.ingest.get_supabase", return_value=supabase), \
             patch("api.v1.ingest.team_service.get_user_team", new=AsyncMock(return_value=None)), \
             patch("api.v1.ingest.check_quota", new=AsyncMock()), \
             patch("api.v1.ingest.check_can_upload", new=AsyncMock(return_value={"allowed": True})), \
             patch("api.v1.ingest.magic.from_buffer", return_value="text/plain"), \
             patch("worker.tasks.unified_ingest_task") as mock_task:
            mock_task.delay.return_value = SimpleNamespace(id="task-1")

            response = await ingest_module.ingest_document(
                request,
                file=file,
                url=None,
                drive_id=None,
                notion_page_id=None,
                metadata="{}",
                user_id=TEST_USER_ID,
            )

        assert response.status == "queued"
        assert response.doc_id == "job-1"
        storage_bucket.upload.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_file_upload_blocks_dangerous_mime(self):
        request = make_request()
        file = UploadFile(filename="bad.exe", file=io.BytesIO(b"MZ"))

        with patch("api.v1.ingest.get_supabase", return_value=MagicMock()), \
             patch("api.v1.ingest.team_service.get_user_team", new=AsyncMock(return_value=None)), \
             patch("api.v1.ingest.check_quota", new=AsyncMock()), \
             patch("api.v1.ingest.check_can_upload", new=AsyncMock(return_value={"allowed": True})), \
             patch("api.v1.ingest.magic.from_buffer", return_value="application/x-executable"):
            with pytest.raises(HTTPException):
                await ingest_module.ingest_document(
                    request,
                    file=file,
                    url=None,
                    drive_id=None,
                    notion_page_id=None,
                    metadata="{}",
                    user_id=TEST_USER_ID,
                )

    @pytest.mark.asyncio
    async def test_ingest_file_upload_extension_mismatch(self):
        request = make_request()
        file = UploadFile(filename="bad.pdf", file=io.BytesIO(b"data"))

        with patch("api.v1.ingest.get_supabase", return_value=MagicMock()), \
             patch("api.v1.ingest.team_service.get_user_team", new=AsyncMock(return_value=None)), \
             patch("api.v1.ingest.check_quota", new=AsyncMock()), \
             patch("api.v1.ingest.check_can_upload", new=AsyncMock(return_value={"allowed": True})), \
             patch("api.v1.ingest.magic.from_buffer", return_value="text/plain"):
            with pytest.raises(HTTPException):
                await ingest_module.ingest_document(
                    request,
                    file=file,
                    url=None,
                    drive_id=None,
                    notion_page_id=None,
                    metadata="{}",
                    user_id=TEST_USER_ID,
                )

    @pytest.mark.asyncio
    async def test_ingest_file_upload_dispatch_failure_cleans_up(self):
        request = make_request()
        file = UploadFile(filename="test.txt", file=io.BytesIO(b"hello"))

        supabase = MagicMock()
        storage_bucket = MagicMock()
        supabase.storage.from_.return_value = storage_bucket
        table = MagicMock()
        table.insert.return_value.execute.return_value = Mock(data=[{"id": "job-1"}])
        supabase.table.return_value = table

        with patch("api.v1.ingest.get_supabase", return_value=supabase), \
             patch("api.v1.ingest.team_service.get_user_team", new=AsyncMock(return_value=None)), \
             patch("api.v1.ingest.check_quota", new=AsyncMock()), \
             patch("api.v1.ingest.check_can_upload", new=AsyncMock(return_value={"allowed": True})), \
             patch("api.v1.ingest.magic.from_buffer", return_value="text/plain"), \
             patch("worker.tasks.unified_ingest_task.delay", side_effect=Exception("boom")):
            with pytest.raises(HTTPException):
                await ingest_module.ingest_document(
                    request,
                    file=file,
                    url=None,
                    drive_id=None,
                    notion_page_id=None,
                    metadata="{}",
                    user_id=TEST_USER_ID,
                )

        storage_bucket.remove.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_file_upload_includes_idempotency_key(self):
        request = make_request({"Idempotency-Key": "key-1"})
        file = UploadFile(filename="test.txt", file=io.BytesIO(b"hello"))

        supabase = MagicMock()
        storage_bucket = MagicMock()
        supabase.storage.from_.return_value = storage_bucket
        table = MagicMock()
        table.insert.return_value.execute.return_value = Mock(data=[{"id": "job-1"}])
        supabase.table.return_value = table

        with patch("api.v1.ingest.get_supabase", return_value=supabase), \
             patch("api.v1.ingest.team_service.get_user_team", new=AsyncMock(return_value=None)), \
             patch("api.v1.ingest.check_quota", new=AsyncMock()), \
             patch("api.v1.ingest.check_can_upload", new=AsyncMock(return_value={"allowed": True})), \
             patch("api.v1.ingest.magic.from_buffer", return_value="text/plain"), \
             patch("api.v1.ingest.find_existing_ingestion_job", return_value=None), \
             patch("worker.tasks.unified_ingest_task") as mock_task:
            mock_task.delay.return_value = SimpleNamespace(id="task-1")

            await ingest_module.ingest_document(
                request,
                file=file,
                url=None,
                drive_id=None,
                notion_page_id=None,
                metadata="{}",
                user_id=TEST_USER_ID,
            )

        payload = table.insert.call_args[0][0]
        assert payload["idempotency_key"] == "key-1"

    @pytest.mark.asyncio
    async def test_ingest_file_upload_dispatch_failure_cleanup_error(self):
        request = make_request()
        file = UploadFile(filename="test.txt", file=io.BytesIO(b"hello"))

        supabase = MagicMock()
        storage_bucket = MagicMock()
        storage_bucket.remove.side_effect = Exception("cleanup failed")
        supabase.storage.from_.return_value = storage_bucket
        table = MagicMock()
        table.insert.return_value.execute.return_value = Mock(data=[{"id": "job-1"}])
        supabase.table.return_value = table

        with patch("api.v1.ingest.get_supabase", return_value=supabase), \
             patch("api.v1.ingest.team_service.get_user_team", new=AsyncMock(return_value=None)), \
             patch("api.v1.ingest.check_quota", new=AsyncMock()), \
             patch("api.v1.ingest.check_can_upload", new=AsyncMock(return_value={"allowed": True})), \
             patch("api.v1.ingest.magic.from_buffer", return_value="text/plain"), \
             patch("worker.tasks.unified_ingest_task.delay", side_effect=Exception("boom")):
            with pytest.raises(HTTPException):
                await ingest_module.ingest_document(
                    request,
                    file=file,
                    url=None,
                    drive_id=None,
                    notion_page_id=None,
                    metadata="{}",
                    user_id=TEST_USER_ID,
                )

        storage_bucket.remove.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_file_upload_quota_blocked(self):
        request = make_request()
        file = UploadFile(filename="test.txt", file=io.BytesIO(b"hello"))

        with patch("api.v1.ingest.get_supabase", return_value=MagicMock()), \
             patch("api.v1.ingest.team_service.get_user_team", new=AsyncMock(return_value=None)), \
             patch("api.v1.ingest.check_quota", new=AsyncMock()), \
             patch("api.v1.ingest.check_can_upload", new=AsyncMock(return_value={"allowed": False, "reason": "limit"})):
            with pytest.raises(HTTPException):
                await ingest_module.ingest_document(
                    request,
                    file=file,
                    url=None,
                    drive_id=None,
                    notion_page_id=None,
                    metadata="{}",
                    user_id=TEST_USER_ID,
                )

    @pytest.mark.asyncio
    async def test_ingest_file_upload_magic_error_logs(self):
        request = make_request()
        file = UploadFile(filename="test.txt", file=io.BytesIO(b"hello"))

        supabase = MagicMock()
        storage_bucket = MagicMock()
        supabase.storage.from_.return_value = storage_bucket
        table = MagicMock()
        table.insert.return_value.execute.return_value = Mock(data=[{"id": "job-1"}])
        supabase.table.return_value = table

        with patch("api.v1.ingest.get_supabase", return_value=supabase), \
             patch("api.v1.ingest.team_service.get_user_team", new=AsyncMock(return_value=None)), \
             patch("api.v1.ingest.check_quota", new=AsyncMock()), \
             patch("api.v1.ingest.check_can_upload", new=AsyncMock(return_value={"allowed": True})), \
             patch("api.v1.ingest.magic.from_buffer", side_effect=Exception("boom")), \
             patch("worker.tasks.unified_ingest_task") as mock_task:
            mock_task.delay.return_value = SimpleNamespace(id="task-1")

            response = await ingest_module.ingest_document(
                request,
                file=file,
                url=None,
                drive_id=None,
                notion_page_id=None,
                metadata="{}",
                user_id=TEST_USER_ID,
            )

        assert response.status == "queued"

    @pytest.mark.asyncio
    async def test_ingest_file_upload_storage_failure(self):
        request = make_request()
        file = UploadFile(filename="test.txt", file=io.BytesIO(b"hello"))

        supabase = MagicMock()
        storage_bucket = MagicMock()
        storage_bucket.upload.side_effect = Exception("boom")
        supabase.storage.from_.return_value = storage_bucket

        with patch("api.v1.ingest.get_supabase", return_value=supabase), \
             patch("api.v1.ingest.team_service.get_user_team", new=AsyncMock(return_value=None)), \
             patch("api.v1.ingest.check_quota", new=AsyncMock()), \
             patch("api.v1.ingest.check_can_upload", new=AsyncMock(return_value={"allowed": True})), \
             patch("api.v1.ingest.magic.from_buffer", return_value="text/plain"):
            with pytest.raises(HTTPException):
                await ingest_module.ingest_document(
                    request,
                    file=file,
                    url=None,
                    drive_id=None,
                    notion_page_id=None,
                    metadata="{}",
                    user_id=TEST_USER_ID,
                )


@pytest.mark.asyncio
async def test_ingest_requires_payload():
    request = make_request()
    with patch("api.v1.ingest.get_supabase", return_value=MagicMock()), \
         patch("api.v1.ingest.team_service.get_user_team", new=AsyncMock(return_value=None)), \
         patch("api.v1.ingest.check_quota", new=AsyncMock()):
        with pytest.raises(HTTPException) as exc:
            await ingest_module.ingest_document(
                request,
                file=None,
                url=None,
                drive_id=None,
                notion_page_id=None,
                metadata="{}",
                user_id=TEST_USER_ID,
            )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_ingest_file_upload_idempotency_returns_existing():
    request = make_request({"Idempotency-Key": "key-1"})
    file = UploadFile(filename="test.txt", file=io.BytesIO(b"hello"))

    supabase = MagicMock()
    storage_bucket = MagicMock()
    supabase.storage.from_.return_value = storage_bucket
    supabase.table.return_value.insert.return_value.execute.return_value = Mock(data=[{"id": "job-1"}])

    with patch("api.v1.ingest.get_supabase", return_value=supabase), \
         patch("api.v1.ingest.team_service.get_user_team", new=AsyncMock(return_value=None)), \
         patch("api.v1.ingest.check_quota", new=AsyncMock()), \
         patch("api.v1.ingest.check_can_upload", new=AsyncMock(return_value={"allowed": True})), \
         patch("api.v1.ingest.magic.from_buffer", return_value="text/plain"), \
         patch("api.v1.ingest.find_existing_ingestion_job", return_value={"id": "job-1", "status": "queued"}):
        response = await ingest_module.ingest_document(
            request,
            file=file,
            url=None,
            drive_id=None,
            notion_page_id=None,
            metadata="{}",
            user_id=TEST_USER_ID,
        )

    assert response.doc_id == "job-1"


@pytest.mark.asyncio
async def test_ingest_file_upload_job_create_failure():
    request = make_request()
    file = UploadFile(filename="test.txt", file=io.BytesIO(b"hello"))

    supabase = MagicMock()
    storage_bucket = MagicMock()
    supabase.storage.from_.return_value = storage_bucket
    supabase.table.return_value.insert.return_value.execute.return_value = Mock(data=None)

    with patch("api.v1.ingest.get_supabase", return_value=supabase), \
         patch("api.v1.ingest.team_service.get_user_team", new=AsyncMock(return_value=None)), \
         patch("api.v1.ingest.check_quota", new=AsyncMock()), \
         patch("api.v1.ingest.check_can_upload", new=AsyncMock(return_value={"allowed": True})), \
         patch("api.v1.ingest.magic.from_buffer", return_value="text/plain"):
        with pytest.raises(HTTPException):
            await ingest_module.ingest_document(
                request,
                file=file,
                url=None,
                drive_id=None,
                notion_page_id=None,
                metadata="{}",
                user_id=TEST_USER_ID,
            )

    storage_bucket.remove.assert_called_once()


class TestIngestConnectors:
    @pytest.mark.asyncio
    async def test_ingest_connector_idempotency_returns_existing(self):
        request = make_request({"Idempotency-Key": "key-1"})
        supabase = MagicMock()
        table = MagicMock()
        table.insert.return_value.execute.return_value = Mock(data=[{"id": "job-1"}])
        supabase.table.return_value = table

        with patch("api.v1.ingest.get_supabase", return_value=supabase), \
             patch("api.v1.ingest.find_existing_ingestion_job", return_value={"id": "job-1", "status": "queued"}):
            response = await ingest_module.ingest_document(
                request,
                url=None,
                file=None,
                drive_id="drive-1",
                notion_page_id=None,
                metadata="{}",
                user_id=TEST_USER_ID,
            )

        assert response.doc_id == "job-1"

    @pytest.mark.asyncio
    async def test_ingest_connector_job_creation_failure(self):
        request = make_request()
        supabase = MagicMock()
        table = MagicMock()
        table.insert.return_value.execute.return_value = Mock(data=[])
        supabase.table.return_value = table

        with patch("api.v1.ingest.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException) as exc:
                await ingest_module.ingest_document(
                    request,
                    url=None,
                    file=None,
                    drive_id="drive-1",
                    notion_page_id=None,
                    metadata="{}",
                    user_id=TEST_USER_ID,
                )

        assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_ingest_connector_dispatch_failure(self):
        request = make_request()
        supabase = MagicMock()
        table = MagicMock()
        table.insert.return_value.execute.return_value = Mock(data=[{"id": "job-1"}])
        supabase.table.return_value = table

        with patch("api.v1.ingest.get_supabase", return_value=supabase), \
             patch("worker.tasks.unified_ingest_task.delay", side_effect=Exception("boom")):
            with pytest.raises(HTTPException) as exc:
                await ingest_module.ingest_document(
                    request,
                    url=None,
                    file=None,
                    drive_id="drive-1",
                    notion_page_id=None,
                    metadata="{}",
                    user_id=TEST_USER_ID,
                )

        assert exc.value.status_code == 503

    @pytest.mark.asyncio
    async def test_ingest_connector_includes_idempotency_key(self):
        request = make_request({"Idempotency-Key": "key-1"})
        supabase = MagicMock()
        table = MagicMock()
        table.insert.return_value.execute.return_value = Mock(data=[{"id": "job-1"}])
        supabase.table.return_value = table

        task = MagicMock()
        task.delay.return_value = SimpleNamespace(id="task-1")

        with patch("api.v1.ingest.get_supabase", return_value=supabase), \
             patch("api.v1.ingest.find_existing_ingestion_job", return_value=None), \
             patch("worker.tasks.unified_ingest_task", task):
            await ingest_module.ingest_document(
                request,
                url=None,
                file=None,
                drive_id="drive-1",
                notion_page_id=None,
                metadata="{}",
                user_id=TEST_USER_ID,
            )

        payload = table.insert.call_args[0][0]
        assert payload["idempotency_key"] == "key-1"


class TestPresignedUploadFlow:
    @pytest.mark.asyncio
    async def test_generate_upload_url_rejects_invalid_type(self):
        request = make_request()
        body = ingest_module.UploadUrlRequest(
            filename="file.exe",
            file_type="application/x-executable",
            file_size=10,
        )

        with patch("api.v1.ingest.get_supabase", return_value=MagicMock()), \
             patch("api.v1.ingest.check_can_upload", new=AsyncMock(return_value={"allowed": True})):
            with pytest.raises(HTTPException):
                await ingest_module.generate_upload_url(request, body, user_id=TEST_USER_ID)

    @pytest.mark.asyncio
    async def test_generate_upload_url_success(self):
        request = make_request()
        body = ingest_module.UploadUrlRequest(
            filename="file.pdf",
            file_type="application/pdf",
            file_size=10,
        )

        supabase = MagicMock()
        supabase.storage.from_.return_value.create_signed_upload_url.return_value = {
            "signed_url": "https://signed.example.com",
        }

        with patch("api.v1.ingest.get_supabase", return_value=supabase), \
             patch("api.v1.ingest.check_can_upload", new=AsyncMock(return_value={"allowed": True})):
            response = await ingest_module.generate_upload_url(request, body, user_id=TEST_USER_ID)

        assert response.upload_url == "https://signed.example.com"
        assert response.storage_path.startswith(f"uploads/{TEST_USER_ID}/")

    @pytest.mark.asyncio
    async def test_generate_upload_url_missing_signed_url(self):
        request = make_request()
        body = ingest_module.UploadUrlRequest(
            filename="file.pdf",
            file_type="application/pdf",
            file_size=10,
        )

        supabase = MagicMock()
        supabase.storage.from_.return_value.create_signed_upload_url.return_value = {"no_url": True}

        with patch("api.v1.ingest.get_supabase", return_value=supabase), \
             patch("api.v1.ingest.check_can_upload", new=AsyncMock(return_value={"allowed": True})):
            with pytest.raises(HTTPException):
                await ingest_module.generate_upload_url(request, body, user_id=TEST_USER_ID)

    @pytest.mark.asyncio
    async def test_generate_upload_url_quota_blocked(self):
        request = make_request()
        body = ingest_module.UploadUrlRequest(
            filename="file.pdf",
            file_type="application/pdf",
            file_size=10,
        )

        with patch("api.v1.ingest.get_supabase", return_value=MagicMock()), \
             patch("api.v1.ingest.check_can_upload", new=AsyncMock(return_value={"allowed": False, "reason": "limit"})):
            with pytest.raises(HTTPException):
                await ingest_module.generate_upload_url(request, body, user_id=TEST_USER_ID)

    @pytest.mark.asyncio
    async def test_generate_upload_url_none_response(self):
        request = make_request()
        body = ingest_module.UploadUrlRequest(
            filename="file.pdf",
            file_type="application/pdf",
            file_size=10,
        )

        supabase = MagicMock()
        supabase.storage.from_.return_value.create_signed_upload_url.return_value = None

        with patch("api.v1.ingest.get_supabase", return_value=supabase), \
             patch("api.v1.ingest.check_can_upload", new=AsyncMock(return_value={"allowed": True})):
            with pytest.raises(HTTPException):
                await ingest_module.generate_upload_url(request, body, user_id=TEST_USER_ID)

    @pytest.mark.asyncio
    async def test_generate_upload_url_exception(self):
        request = make_request()
        body = ingest_module.UploadUrlRequest(
            filename="file.pdf",
            file_type="application/pdf",
            file_size=10,
        )

        supabase = MagicMock()
        supabase.storage.from_.return_value.create_signed_upload_url.side_effect = RuntimeError("boom")

        with patch("api.v1.ingest.get_supabase", return_value=supabase), \
             patch("api.v1.ingest.check_can_upload", new=AsyncMock(return_value={"allowed": True})):
            with pytest.raises(HTTPException):
                await ingest_module.generate_upload_url(request, body, user_id=TEST_USER_ID)

    @pytest.mark.asyncio
    async def test_ingest_file_reference_dispatches_task(self):
        request = make_request()
        body = ingest_module.FileReferenceRequest(
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

        with patch("api.v1.ingest.get_supabase", return_value=supabase), \
             patch("api.v1.ingest.check_can_upload", new=AsyncMock(return_value={"allowed": True})), \
             patch("worker.tasks.unified_ingest_task") as mock_task:
            mock_task.delay.return_value = SimpleNamespace(id="task-2")

            response = await ingest_module.ingest_file_reference(request, body, user_id=TEST_USER_ID)

        assert response.status == "queued"
        assert response.doc_id == "job-2"

    @pytest.mark.asyncio
    async def test_ingest_file_reference_404_when_missing(self):
        request = make_request()
        body = ingest_module.FileReferenceRequest(
            storage_path=f"uploads/{TEST_USER_ID}/uuid/missing.txt",
            filename="missing.txt",
            file_size=10,
            metadata={},
        )

        supabase = MagicMock()
        supabase.storage.from_.return_value.list.return_value = [{"name": "other.txt"}]

        with patch("api.v1.ingest.get_supabase", return_value=supabase), \
             patch("api.v1.ingest.check_can_upload", new=AsyncMock(return_value={"allowed": True})):
            with pytest.raises(HTTPException):
                await ingest_module.ingest_file_reference(request, body, user_id=TEST_USER_ID)

    @pytest.mark.asyncio
    async def test_ingest_file_reference_cleans_up_on_quota_block(self):
        request = make_request()
        body = ingest_module.FileReferenceRequest(
            storage_path=f"uploads/{TEST_USER_ID}/uuid/file.txt",
            filename="file.txt",
            file_size=10,
            metadata={},
        )

        supabase = MagicMock()
        supabase.storage.from_.return_value.list.return_value = [{"name": "file.txt"}]

        with patch("api.v1.ingest.get_supabase", return_value=supabase), \
             patch("api.v1.ingest.check_can_upload", new=AsyncMock(return_value={"allowed": False, "reason": "limit"})):
            with pytest.raises(HTTPException):
                await ingest_module.ingest_file_reference(request, body, user_id=TEST_USER_ID)

        supabase.storage.from_.return_value.remove.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_file_reference_cleanup_error_on_quota_block(self):
        request = make_request()
        body = ingest_module.FileReferenceRequest(
            storage_path=f"uploads/{TEST_USER_ID}/uuid/file.txt",
            filename="file.txt",
            file_size=10,
            metadata={},
        )

        supabase = MagicMock()
        storage_bucket = MagicMock()
        storage_bucket.list.return_value = [{"name": "file.txt"}]
        storage_bucket.remove.side_effect = Exception("cleanup failed")
        supabase.storage.from_.return_value = storage_bucket

        with patch("api.v1.ingest.get_supabase", return_value=supabase), \
             patch("api.v1.ingest.check_can_upload", new=AsyncMock(return_value={"allowed": False, "reason": "limit"})):
            with pytest.raises(HTTPException):
                await ingest_module.ingest_file_reference(request, body, user_id=TEST_USER_ID)

    @pytest.mark.asyncio
    async def test_ingest_file_reference_includes_idempotency_key(self):
        request = make_request({"Idempotency-Key": "key-1"})
        body = ingest_module.FileReferenceRequest(
            storage_path=f"uploads/{TEST_USER_ID}/uuid/file.txt",
            filename="file.txt",
            file_size=10,
            metadata={},
        )

        supabase = MagicMock()
        supabase.storage.from_.return_value.list.return_value = [{"name": "file.txt"}]
        supabase.table.return_value.insert.return_value.execute.return_value = Mock(data=[{"id": "job-2"}])

        with patch("api.v1.ingest.get_supabase", return_value=supabase), \
             patch("api.v1.ingest.check_can_upload", new=AsyncMock(return_value={"allowed": True})), \
             patch("api.v1.ingest.find_existing_ingestion_job", return_value=None), \
             patch("worker.tasks.unified_ingest_task") as mock_task:
            mock_task.delay.return_value = SimpleNamespace(id="task-2")
            await ingest_module.ingest_file_reference(request, body, user_id=TEST_USER_ID)

        payload = supabase.table.return_value.insert.call_args[0][0]
        assert payload["idempotency_key"] == "key-1"

    @pytest.mark.asyncio
    async def test_ingest_file_reference_verification_error_continues(self):
        request = make_request()
        body = ingest_module.FileReferenceRequest(
            storage_path=f"uploads/{TEST_USER_ID}/uuid/file.txt",
            filename="file.txt",
            file_size=10,
            metadata={},
        )

        supabase = MagicMock()
        supabase.storage.from_.return_value.list.side_effect = Exception("boom")
        table = MagicMock()
        table.insert.return_value.execute.return_value = Mock(data=[{"id": "job-2"}])
        supabase.table.return_value = table

        with patch("api.v1.ingest.get_supabase", return_value=supabase), \
             patch("api.v1.ingest.check_can_upload", new=AsyncMock(return_value={"allowed": True})), \
             patch("worker.tasks.unified_ingest_task") as mock_task:
            mock_task.delay.return_value = SimpleNamespace(id="task-2")

            response = await ingest_module.ingest_file_reference(request, body, user_id=TEST_USER_ID)

        assert response.status == "queued"

    @pytest.mark.asyncio
    async def test_ingest_file_reference_idempotency_returns_existing(self):
        request = make_request({"Idempotency-Key": "key-1"})
        body = ingest_module.FileReferenceRequest(
            storage_path=f"uploads/{TEST_USER_ID}/uuid/file.txt",
            filename="file.txt",
            file_size=10,
            metadata={},
        )

        supabase = MagicMock()
        supabase.storage.from_.return_value.list.return_value = [{"name": "file.txt"}]
        supabase.table.return_value.insert.return_value.execute.return_value = Mock(data=[{"id": "job-2"}])

        with patch("api.v1.ingest.get_supabase", return_value=supabase), \
             patch("api.v1.ingest.check_can_upload", new=AsyncMock(return_value={"allowed": True})), \
             patch("api.v1.ingest.find_existing_ingestion_job", return_value={"id": "job-2", "status": "queued"}):
            response = await ingest_module.ingest_file_reference(request, body, user_id=TEST_USER_ID)

        assert response.doc_id == "job-2"

    @pytest.mark.asyncio
    async def test_ingest_file_reference_job_create_failure(self):
        request = make_request()
        body = ingest_module.FileReferenceRequest(
            storage_path=f"uploads/{TEST_USER_ID}/uuid/file.txt",
            filename="file.txt",
            file_size=10,
            metadata={},
        )

        supabase = MagicMock()
        supabase.storage.from_.return_value.list.return_value = [{"name": "file.txt"}]
        supabase.table.return_value.insert.return_value.execute.return_value = Mock(data=None)

        with patch("api.v1.ingest.get_supabase", return_value=supabase), \
             patch("api.v1.ingest.check_can_upload", new=AsyncMock(return_value={"allowed": True})):
            with pytest.raises(HTTPException):
                await ingest_module.ingest_file_reference(request, body, user_id=TEST_USER_ID)

    @pytest.mark.asyncio
    async def test_ingest_file_reference_dispatch_failure_remove_error(self):
        request = make_request()
        body = ingest_module.FileReferenceRequest(
            storage_path=f"uploads/{TEST_USER_ID}/uuid/file.txt",
            filename="file.txt",
            file_size=10,
            metadata={},
        )

        supabase = MagicMock()
        storage_bucket = MagicMock()
        storage_bucket.list.return_value = [{"name": "file.txt"}]
        storage_bucket.remove.side_effect = Exception("boom")
        supabase.storage.from_.return_value = storage_bucket
        supabase.table.return_value.insert.return_value.execute.return_value = Mock(data=[{"id": "job-2"}])

        with patch("api.v1.ingest.get_supabase", return_value=supabase), \
             patch("api.v1.ingest.check_can_upload", new=AsyncMock(return_value={"allowed": True})), \
             patch("worker.tasks.unified_ingest_task.delay", side_effect=Exception("boom")):
            with pytest.raises(HTTPException):
                await ingest_module.ingest_file_reference(request, body, user_id=TEST_USER_ID)


class TestDeleteCrawlConfig:
    @pytest.mark.asyncio
    async def test_delete_crawl_config_not_found(self):
        supabase = MagicMock()
        table = MagicMock()
        table.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data=None
        )
        supabase.table.return_value = table

        with patch("api.v1.ingest.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException):
                await ingest_module.delete_crawl_config("cfg-1", user_id="user-1")

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
        with patch("api.v1.ingest.get_supabase", return_value=supabase), \
             patch("celery.result.AsyncResult", return_value=mock_result):
            response = await ingest_module.delete_crawl_config("cfg-1", user_id="user-1")

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
        with patch("api.v1.ingest.get_supabase", return_value=supabase), \
             patch("celery.result.AsyncResult", return_value=mock_result):
            response = await ingest_module.delete_crawl_config("cfg-1", user_id="user-1")

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

        with patch("api.v1.ingest.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException):
                await ingest_module.delete_crawl_config("cfg-1", user_id="user-1")
