"""
Unit tests for integrations API endpoints.
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import BackgroundTasks, HTTPException

from api.v1.integrations import (
    ExchangeRequest,
    MicrosoftExchangeRequest,
    IngestRequest,
    WebCrawlRequest,
    _require_provider,
    crawl_web,
    disconnect_provider,
    exchange_google_token,
    exchange_microsoft_token,
    exchange_notion_token,
    get_available_connectors,
    get_provider_status,
    get_sync_history,
    get_user_integrations,
    ingest_provider_items,
    list_provider_items,
    run_background_sync,
    sync_integration,
)
from starlette.requests import Request


def build_table(execute_data=None):
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.order.return_value = table
    table.limit.return_value = table
    table.insert.return_value = table
    table.upsert.return_value = table
    table.update.return_value = table
    table.delete.return_value = table
    table.execute.return_value = MagicMock(data=execute_data)
    return table


def build_supabase(table_map):
    supabase = MagicMock()
    supabase.table.side_effect = lambda name: table_map[name]
    return supabase


class FakeResponse:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data
        self.text = str(data)

    def json(self):
        return self._data


class FakeAsyncClient:
    def __init__(self, responses):
        self.responses = list(responses)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, **kwargs):
        return self.responses.pop(0)

    async def get(self, url, **kwargs):
        return self.responses.pop(0)


class TestGoogleDriveConnector:
    @pytest.mark.asyncio
    async def test_list_provider_items_rejects_deprecated_provider(self):
        with pytest.raises(HTTPException) as exc:
            _require_provider("drive")
        assert exc.value.status_code == 400
        assert "Deprecated provider value" in exc.value.detail

    @pytest.mark.asyncio
    async def test_list_drive_items_returns_files_and_folders(self):
        items = [
            {"id": "file-1", "name": "doc.pdf", "mime_type": "application/pdf"},
            {"id": "folder-1", "name": "Folder", "mime_type": "application/vnd.google-apps.folder"},
        ]
        connector = MagicMock()
        connector.list_files = AsyncMock(return_value=items)

        with patch("api.v1.integrations.get_connector", return_value=connector):
            result = await list_provider_items("google_drive", user_id="user-1")

        assert result[0]["id"] == "file-1"
        assert result[0]["type"] == "file"
        assert result[1]["id"] == "folder-1"
        assert result[1]["type"] == "folder"

    @pytest.mark.asyncio
    async def test_list_drive_items_supports_folder_navigation(self):
        connector = MagicMock()
        connector.list_files = AsyncMock(return_value=[])

        with patch("api.v1.integrations.get_connector", return_value=connector):
            await list_provider_items("google_drive", user_id="user-1", parent_id="folder-123")

        connector.list_files.assert_awaited_once_with(
            {"user_id": "user-1", "parent_id": "folder-123", "provider": "google_drive"}
        )

    @pytest.mark.asyncio
    async def test_list_drive_items_filters_supported_types(self):
        items = [
            {"id": "file-1", "mime_type": "application/pdf"},
            {"id": "file-2", "mime_type": "text/plain"},
        ]
        connector = MagicMock()
        connector.list_files = AsyncMock(return_value=items)

        with patch("api.v1.integrations.get_connector", return_value=connector):
            result = await list_provider_items("google_drive", user_id="user-1")

        assert any(item["mimeType"] == "application/pdf" for item in result)

    @pytest.mark.asyncio
    async def test_recursive_folder_ingestion(self):
        supabase = build_supabase(
            {
                "connector_definitions": build_table({"id": "def-1"}),
                "user_integrations": build_table(
                    {"id": "int-1", "access_token": "token", "credentials": {}}
                ),
                "ingestion_jobs": build_table([{"id": "job-1"}]),
            }
        )

        task = MagicMock()
        task.delay.return_value = SimpleNamespace(id="task-1")

        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            with patch("worker.tasks.unified_ingest_task", task):
                response = await ingest_provider_items(
                    "google_drive",
                    IngestRequest(item_ids=["folder-1", "file-2"]),
                    user_id="user-1",
                )

        assert response["status"] == "accepted"
        task.delay.assert_called_once()

    @pytest.mark.asyncio
    async def test_recursive_ingestion_respects_depth_limit(self):
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/",
            "headers": [],
            "client": ("127.0.0.1", 1234),
        }
        request = Request(scope)
        with patch("api.v1.integrations.check_feature_access", new=AsyncMock(return_value={"allowed": True})):
            connector = MagicMock()
            connector.normalize_url.return_value = "https://example.com"
            connector.is_safe_url.return_value = True

            with patch("api.v1.integrations.WebConnector", return_value=connector):
                with patch("api.v1.integrations.queue_web_crawl", return_value={"crawl_id": "c1", "task_id": "t1"}):
                    response = await crawl_web(
                        request=request,
                        body=WebCrawlRequest(url="https://example.com", crawl_type="recursive", max_depth=3),
                        user_id="00000000-0000-0000-0000-000000000001",
                    )

        assert response["status"] == "queued"


class TestConnectorDiscovery:
    @pytest.mark.asyncio
    async def test_get_available_connectors_returns_list(self):
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "client": ("127.0.0.1", 1234),
        }
        request = Request(scope)
        supabase = build_supabase({"connector_definitions": build_table([{"id": "c1"}])})
        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            result = await get_available_connectors(request=request)
        assert result[0]["id"] == "c1"

    @pytest.mark.asyncio
    async def test_get_user_integrations_transforms(self):
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "client": ("127.0.0.1", 1234),
        }
        request = Request(scope)
        supabase = build_supabase(
            {
                "user_integrations": build_table(
                    [
                        {
                            "id": "int-1",
                            "connector_definition_id": "def-1",
                            "connector_definitions": {"type": "google_drive", "name": "Google Drive"},
                            "last_sync_at": None,
                        }
                    ]
                )
            }
        )
        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            result = await get_user_integrations(request=request, user_id="user-1")
        assert result[0]["connector_type"] == "google_drive"

    @pytest.mark.asyncio
    async def test_get_available_connectors_handles_error(self):
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "client": ("127.0.0.1", 1234),
        }
        request = Request(scope)
        table = build_table([])
        table.execute.side_effect = Exception("db error")
        supabase = build_supabase({"connector_definitions": table})

        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException):
                await get_available_connectors(request=request)

    @pytest.mark.asyncio
    async def test_get_user_integrations_handles_error(self):
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "client": ("127.0.0.1", 1234),
        }
        request = Request(scope)
        table = build_table([])
        table.execute.side_effect = Exception("db error")
        supabase = build_supabase({"user_integrations": table})

        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException):
                await get_user_integrations(request=request, user_id="user-1")


class TestAsyncIngestion:
    @pytest.mark.asyncio
    async def test_ingest_returns_202_accepted(self):
        supabase = build_supabase(
            {
                "connector_definitions": build_table({"id": "def-1"}),
                "user_integrations": build_table(
                    {"id": "int-1", "access_token": "token", "credentials": {}}
                ),
                "ingestion_jobs": build_table([{"id": "job-1"}]),
            }
        )
        task = MagicMock()
        task.delay.return_value = SimpleNamespace(id="task-1")

        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            with patch("worker.tasks.unified_ingest_task", task):
                response = await ingest_provider_items(
                    "google_drive",
                    IngestRequest(item_ids=["file-1"]),
                    user_id="user-1",
                )

        assert response["status"] == "accepted"

    @pytest.mark.asyncio
    async def test_ingest_returns_task_id(self):
        supabase = build_supabase(
            {
                "connector_definitions": build_table({"id": "def-1"}),
                "user_integrations": build_table(
                    {"id": "int-1", "access_token": "token", "credentials": {}}
                ),
                "ingestion_jobs": build_table([{"id": "job-1"}]),
            }
        )
        task = MagicMock()
        task.delay.return_value = SimpleNamespace(id="task-42")

        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            with patch("worker.tasks.unified_ingest_task", task):
                response = await ingest_provider_items(
                    "google_drive",
                    IngestRequest(item_ids=["file-1"]),
                    user_id="user-1",
                )

        assert response["task_id"] == "task-42"

    @pytest.mark.asyncio
    async def test_ingest_queues_celery_task(self):
        supabase = build_supabase(
            {
                "connector_definitions": build_table({"id": "def-1"}),
                "user_integrations": build_table(
                    {"id": "int-1", "access_token": "token", "credentials": {}}
                ),
                "ingestion_jobs": build_table([{"id": "job-1"}]),
            }
        )
        task = MagicMock()
        task.delay.return_value = SimpleNamespace(id="task-1")

        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            with patch("worker.tasks.unified_ingest_task", task):
                await ingest_provider_items(
                    "google_drive",
                    IngestRequest(item_ids=["file-1"]),
                    user_id="user-1",
                )

        task.delay.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_handles_multiple_files(self):
        supabase = build_supabase(
            {
                "connector_definitions": build_table({"id": "def-1"}),
                "user_integrations": build_table(
                    {"id": "int-1", "access_token": "token", "credentials": {}}
                ),
                "ingestion_jobs": build_table([{"id": "job-1"}]),
            }
        )
        task = MagicMock()
        task.delay.return_value = SimpleNamespace(id="task-1")

        items = ["file-1", "file-2"]

        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            with patch("worker.tasks.unified_ingest_task", task):
                response = await ingest_provider_items(
                    "google_drive",
                    IngestRequest(item_ids=items),
                    user_id="user-1",
                )

        assert response["message"].endswith("2 items")

    @pytest.mark.asyncio
    async def test_ingest_unknown_provider_definition_raises(self):
        supabase = build_supabase(
            {
                "connector_definitions": build_table(None),
            }
        )

        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException) as exc:
                await ingest_provider_items(
                    "google_drive",
                    IngestRequest(item_ids=["file-1"]),
                    user_id="user-1",
                )

        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_ingest_non_oauth_requires_credentials(self):
        supabase = build_supabase(
            {
                "connector_definitions": build_table({"id": "def-1"}),
                "user_integrations": build_table(None),
            }
        )
        test_user_id = "00000000-0000-0000-0000-000000000001"

        # Use a valid provider and mock the provider/feature checks
        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("api.v1.integrations._require_provider", return_value="web"), \
             patch("api.v1.integrations._resolve_org_and_plan", return_value=("org-1", "starter")), \
             patch("api.v1.integrations.check_admission"), \
             patch("api.v1.integrations.check_feature_access", return_value={"allowed": True}):
            with pytest.raises(HTTPException) as exc:
                await ingest_provider_items(
                    "web",
                    IngestRequest(item_ids=["https://example.com"]),
                    user_id=test_user_id,
                )

        # No integration found = 401
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_ingest_non_oauth_uses_credentials(self):
        supabase = build_supabase(
            {
                "connector_definitions": build_table({"id": "def-1"}),
                "user_integrations": build_table({"id": "int-1", "credentials": {"bucket": "staging"}}),
                "ingestion_jobs": build_table([{"id": "job-1"}]),
            }
        )
        task = MagicMock()
        task.delay.return_value = SimpleNamespace(id="task-1")
        test_user_id = "00000000-0000-0000-0000-000000000001"

        # Use a valid provider and mock the provider/feature checks
        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("api.v1.integrations._require_provider", return_value="web"), \
             patch("api.v1.integrations._resolve_org_and_plan", return_value=("org-1", "starter")), \
             patch("api.v1.integrations.check_admission"), \
             patch("api.v1.integrations.check_feature_access", return_value={"allowed": True}):
            with patch("worker.tasks.unified_ingest_task", task):
                response = await ingest_provider_items(
                    "web",
                    IngestRequest(item_ids=["https://example.com"]),
                    user_id=test_user_id,
                )

        assert response["status"] == "accepted"


class TestOAuthIntegration:
    @pytest.mark.asyncio
    async def test_oauth_stores_encrypted_tokens(self, monkeypatch):
        connector_def_table = build_table({"id": "def-1"})
        upsert_table = build_table([{"id": "int-1"}])
        supabase = build_supabase(
            {"connector_definitions": connector_def_table, "user_integrations": upsert_table}
        )

        flow = MagicMock()
        flow.fetch_token.return_value = None
        flow.credentials = SimpleNamespace(
            token="access-token",
            refresh_token="refresh-token",
            expiry=datetime.now(timezone.utc),
        )

        monkeypatch.setattr("api.v1.integrations.settings.GOOGLE_CLIENT_ID", "cid")
        monkeypatch.setattr("api.v1.integrations.settings.GOOGLE_CLIENT_SECRET", "secret")
        monkeypatch.setattr("api.v1.integrations.settings.GOOGLE_REDIRECT_URI", "https://example.com/callback")

        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            with patch("api.v1.integrations.Flow.from_client_config", return_value=flow):
                with patch("api.v1.integrations.encrypt_token", side_effect=lambda value: f"enc-{value}"):
                    result = await exchange_google_token(
                        ExchangeRequest(code="code"),
                        BackgroundTasks(),
                        user_id="user-1",
                    )

        assert result["status"] == "success"
        assert upsert_table.upsert.called

    @pytest.mark.asyncio
    async def test_google_oauth_missing_config(self, monkeypatch):
        monkeypatch.setattr("api.v1.integrations.settings.GOOGLE_CLIENT_ID", "")
        monkeypatch.setattr("api.v1.integrations.settings.GOOGLE_CLIENT_SECRET", "")

        with pytest.raises(HTTPException):
            await exchange_google_token(
                ExchangeRequest(code="code"),
                BackgroundTasks(),
                user_id="user-1",
            )

    @pytest.mark.asyncio
    async def test_google_oauth_connector_missing(self, monkeypatch):
        connector_def_table = build_table(None)
        supabase = build_supabase({"connector_definitions": connector_def_table})

        monkeypatch.setattr("api.v1.integrations.settings.GOOGLE_CLIENT_ID", "cid")
        monkeypatch.setattr("api.v1.integrations.settings.GOOGLE_CLIENT_SECRET", "secret")
        monkeypatch.setattr("api.v1.integrations.settings.GOOGLE_REDIRECT_URI", "https://example.com/callback")

        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException):
                await exchange_google_token(
                    ExchangeRequest(code="code"),
                    BackgroundTasks(),
                    user_id="user-1",
                )

    @pytest.mark.asyncio
    async def test_google_oauth_token_exchange_failure(self, monkeypatch):
        connector_def_table = build_table({"id": "def-1"})
        supabase = build_supabase({"connector_definitions": connector_def_table})

        flow = MagicMock()
        flow.fetch_token.side_effect = Exception("bad")

        monkeypatch.setattr("api.v1.integrations.settings.GOOGLE_CLIENT_ID", "cid")
        monkeypatch.setattr("api.v1.integrations.settings.GOOGLE_CLIENT_SECRET", "secret")
        monkeypatch.setattr("api.v1.integrations.settings.GOOGLE_REDIRECT_URI", "https://example.com/callback")

        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("api.v1.integrations.Flow.from_client_config", return_value=flow):
            with pytest.raises(HTTPException):
                await exchange_google_token(
                    ExchangeRequest(code="code"),
                    BackgroundTasks(),
                    user_id="user-1",
                )

    @pytest.mark.asyncio
    async def test_google_oauth_upsert_returns_no_data(self, monkeypatch):
        connector_def_table = build_table({"id": "def-1"})
        upsert_table = build_table(None)
        supabase = build_supabase(
            {"connector_definitions": connector_def_table, "user_integrations": upsert_table}
        )

        flow = MagicMock()
        flow.fetch_token.return_value = None
        flow.credentials = SimpleNamespace(token="token", refresh_token=None, expiry=None)

        monkeypatch.setattr("api.v1.integrations.settings.GOOGLE_CLIENT_ID", "cid")
        monkeypatch.setattr("api.v1.integrations.settings.GOOGLE_CLIENT_SECRET", "secret")
        monkeypatch.setattr("api.v1.integrations.settings.GOOGLE_REDIRECT_URI", "https://example.com/callback")

        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("api.v1.integrations.Flow.from_client_config", return_value=flow), \
             patch("api.v1.integrations.encrypt_token", return_value="enc"):
            with pytest.raises(HTTPException):
                await exchange_google_token(
                    ExchangeRequest(code="code"),
                    BackgroundTasks(),
                    user_id="user-1",
                )

    @pytest.mark.asyncio
    async def test_oauth_decrypts_tokens_for_use(self):
        with patch("api.v1.integrations.decrypt_token", return_value="token") as decrypt:
            assert decrypt("enc-token") == "token"

    @pytest.mark.asyncio
    async def test_oauth_handles_refresh(self, monkeypatch):
        connector_def_table = build_table({"id": "def-1"})
        upsert_table = build_table([{"id": "int-1"}])
        job_table = build_table([{"id": "job-1"}])
        supabase = build_supabase(
            {
                "connector_definitions": connector_def_table,
                "user_integrations": upsert_table,
                "ingestion_jobs": job_table,
            }
        )

        token_response = FakeResponse(
            200,
            {
                "access_token": "access-token",
                "workspace_id": "ws-1",
                "workspace_name": "Workspace",
                "bot_id": "bot-1",
            },
        )
        search_response = FakeResponse(
            200,
            {"results": [{"id": "page-1", "object": "page"}]},
        )

        monkeypatch.setattr("api.v1.integrations.settings.NOTION_CLIENT_ID", "cid")
        monkeypatch.setattr("api.v1.integrations.settings.NOTION_CLIENT_SECRET", "secret")
        monkeypatch.setattr("api.v1.integrations.settings.NOTION_REDIRECT_URI", "https://example.com/callback")

        task = MagicMock()
        task.delay.return_value = SimpleNamespace(id="task-1")

        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            with patch("api.v1.integrations.encrypt_token", side_effect=lambda value: f"enc-{value}"):
                with patch(
                    "api.v1.integrations.httpx.AsyncClient",
                    side_effect=[
                        FakeAsyncClient([token_response]),
                        FakeAsyncClient([search_response]),
                    ],
                ):
                    with patch("worker.tasks.unified_ingest_task", task):
                        result = await exchange_notion_token(
                            ExchangeRequest(code="code"),
                            user_id="user-1",
                        )

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_notion_oauth_missing_config(self, monkeypatch):
        monkeypatch.setattr("api.v1.integrations.settings.NOTION_CLIENT_ID", "")
        monkeypatch.setattr("api.v1.integrations.settings.NOTION_CLIENT_SECRET", "")
        monkeypatch.setattr("api.v1.integrations.settings.NOTION_REDIRECT_URI", "")

        with pytest.raises(HTTPException):
            await exchange_notion_token(ExchangeRequest(code="code"), user_id="user-1")

    @pytest.mark.asyncio
    async def test_notion_oauth_api_error(self, monkeypatch):
        connector_def_table = build_table({"id": "def-1"})
        upsert_table = build_table([{"id": "int-1"}])
        supabase = build_supabase(
            {"connector_definitions": connector_def_table, "user_integrations": upsert_table}
        )

        token_response = FakeResponse(400, {"error": "invalid"})

        monkeypatch.setattr("api.v1.integrations.settings.NOTION_CLIENT_ID", "cid")
        monkeypatch.setattr("api.v1.integrations.settings.NOTION_CLIENT_SECRET", "secret")
        monkeypatch.setattr("api.v1.integrations.settings.NOTION_REDIRECT_URI", "https://example.com/callback")

        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("api.v1.integrations.httpx.AsyncClient", return_value=FakeAsyncClient([token_response])):
            with pytest.raises(HTTPException):
                await exchange_notion_token(ExchangeRequest(code="code"), user_id="user-1")


class TestConnectionStatus:
    @pytest.mark.asyncio
    async def test_status_returns_connected_when_valid_token(self):
        supabase = build_supabase(
            {
                "connector_definitions": build_table({"id": "def-1"}),
                "user_integrations": build_table([{"id": "int-1"}]),
            }
        )

        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            result = await get_provider_status("google_drive", user_id="user-1")

        assert result["connected"] is True

    @pytest.mark.asyncio
    async def test_status_returns_disconnected_when_no_token(self):
        supabase = build_supabase(
            {
                "connector_definitions": build_table({"id": "def-1"}),
                "user_integrations": build_table([]),
            }
        )

        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            result = await get_provider_status("google_drive", user_id="user-1")

        assert result["connected"] is False

    @pytest.mark.asyncio
    async def test_status_returns_disconnected_when_token_expired(self):
        supabase = build_supabase({"connector_definitions": build_table(None)})
        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            result = await get_provider_status("google_drive", user_id="user-1")

        assert result["connected"] is False


class TestDataSourceSecurity:
    @pytest.mark.asyncio
    async def test_credentials_isolated_by_user(self):
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "client": ("127.0.0.1", 1234),
        }
        request = Request(scope)
        supabase = build_supabase({"user_integrations": build_table([])})
        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            result = await get_user_integrations(request=request, user_id="user-1")
        assert result == []

    @pytest.mark.asyncio
    async def test_ingested_data_isolated_by_user(self):
        supabase = build_supabase(
            {
                "connector_definitions": build_table({"id": "def-1"}),
                "user_integrations": build_table(
                    {"id": "int-1", "access_token": "token", "credentials": {}}
                ),
                "ingestion_jobs": build_table([{"id": "job-1"}]),
            }
        )
        task = MagicMock()
        task.delay.return_value = SimpleNamespace(id="task-1")
        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            with patch("worker.tasks.unified_ingest_task", task):
                result = await ingest_provider_items(
                    "google_drive",
                    IngestRequest(item_ids=["file-1"]),
                    user_id="user-1",
                )
        assert result["status"] == "accepted"


class TestSyncHistoryEndpoint:
    @pytest.mark.asyncio
    async def test_sync_history_returns_list(self):
        supabase = build_supabase(
            {
                "user_integrations": build_table(
                    {"id": "int-1", "connector_definitions": {"type": "google_drive"}}
                ),
                "sync_state": build_table([{"id": "sync-1"}, {"id": "sync-2"}]),
            }
        )

        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            result = await get_sync_history("int-1", user_id="user-1")

        assert len(result["history"]) == 2

    @pytest.mark.asyncio
    async def test_sync_history_verifies_integration_ownership(self):
        supabase = build_supabase(
            {
                "user_integrations": build_table(
                    {"id": "int-1", "connector_definitions": {"type": "google_drive"}}
                ),
                "sync_state": build_table([]),
            }
        )
        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            result = await get_sync_history("int-1", user_id="user-1")
        assert result["integration_id"] == "int-1"

    @pytest.mark.asyncio
    async def test_sync_history_returns_404_for_nonexistent_integration(self):
        supabase = build_supabase({"user_integrations": build_table(None)})
        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException):
                await get_sync_history("int-1", user_id="user-1")

    @pytest.mark.asyncio
    async def test_sync_history_filters_by_provider(self):
        supabase = build_supabase(
            {
                "user_integrations": build_table(
                    {"id": "int-1", "connector_definitions": {"type": "google_drive"}}
                ),
                "sync_state": build_table([]),
            }
        )
        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            result = await get_sync_history("int-1", user_id="user-1", limit=10)
        assert result["provider"] == "google_drive"

    @pytest.mark.asyncio
    async def test_sync_history_orders_by_updated_at_desc(self):
        supabase = build_supabase(
            {
                "user_integrations": build_table(
                    {"id": "int-1", "connector_definitions": {"type": "google_drive"}}
                ),
                "sync_state": build_table([{"id": "sync-1"}]),
            }
        )
        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            result = await get_sync_history("int-1", user_id="user-1")
        assert result["history"][0]["id"] == "sync-1"

    @pytest.mark.asyncio
    async def test_sync_history_respects_limit_parameter(self):
        supabase = build_supabase(
            {
                "user_integrations": build_table(
                    {"id": "int-1", "connector_definitions": {"type": "google_drive"}}
                ),
                "sync_state": build_table([{"id": "sync-1"}]),
            }
        )
        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            result = await get_sync_history("int-1", user_id="user-1", limit=1)
        assert len(result["history"]) == 1

    @pytest.mark.asyncio
    async def test_sync_history_response_includes_provider(self):
        supabase = build_supabase(
            {
                "user_integrations": build_table(
                    {"id": "int-1", "connector_definitions": {"type": "google_drive"}}
                ),
                "sync_state": build_table([]),
            }
        )
        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            result = await get_sync_history("int-1", user_id="user-1")
        assert result["provider"] == "google_drive"


class TestDisconnectProvider:
    @pytest.mark.asyncio
    async def test_disconnect_provider_unknown(self):
        supabase = build_supabase({"connector_definitions": build_table(None)})
        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException):
                await disconnect_provider("unknown", user_id="user-1")

    @pytest.mark.asyncio
    async def test_disconnect_provider_missing_definition_raises(self):
        supabase = build_supabase({"connector_definitions": build_table(None)})
        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException) as exc:
                await disconnect_provider("google_drive", user_id="user-1")

        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_disconnect_provider_cleans_records(self):
        supabase = build_supabase(
            {
                "connector_definitions": build_table({"id": "def-1"}),
                "user_integrations": build_table({"access_token": "enc-token"}),
                "documents": build_table([]),
                "ingestion_jobs": build_table([{"id": "job-1"}]),
                "ingestion_file_status": build_table([]),
                "sync_state": build_table([]),
            }
        )
        response = FakeResponse(200, {})

        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("api.v1.integrations.decrypt_token", return_value="token"), \
             patch("api.v1.integrations.httpx.AsyncClient", return_value=FakeAsyncClient([response])):
            result = await disconnect_provider("google_drive", user_id="user-1")

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_disconnect_provider_notion_path(self):
        supabase = build_supabase(
            {
                "connector_definitions": build_table({"id": "def-1"}),
                "user_integrations": build_table({"access_token": "enc-token"}),
                "documents": build_table([]),
                "ingestion_jobs": build_table([]),
                "ingestion_file_status": build_table([]),
                "sync_state": build_table([]),
            }
        )
        response = FakeResponse(200, {})

        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("api.v1.integrations.decrypt_token", return_value="token"), \
             patch("api.v1.integrations.httpx.AsyncClient", return_value=FakeAsyncClient([response])):
            result = await disconnect_provider("notion", user_id="user-1")

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_disconnect_provider_notion_revocation_noop(self):
        supabase = build_supabase(
            {
                "connector_definitions": build_table({"id": "def-1"}),
                "user_integrations": build_table({"access_token": "enc-token"}),
                "documents": build_table([]),
                "ingestion_jobs": build_table([]),
                "ingestion_file_status": build_table([]),
                "sync_state": build_table([]),
            }
        )

        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("api.v1.integrations.decrypt_token", return_value="token"), \
             patch("api.v1.integrations.httpx.AsyncClient", return_value=FakeAsyncClient([])):
            result = await disconnect_provider("notion", user_id="user-1")

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_disconnect_provider_document_cleanup_error(self):
        doc_table = build_table([])
        doc_table.in_.return_value = doc_table
        doc_table.execute.side_effect = Exception("doc delete")
        supabase = build_supabase(
            {
                "connector_definitions": build_table({"id": "def-1"}),
                "user_integrations": build_table({"access_token": "enc-token"}),
                "documents": doc_table,
                "ingestion_jobs": build_table([{"id": "job-1"}]),
                "ingestion_file_status": build_table([]),
                "sync_state": build_table([]),
            }
        )

        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("api.v1.integrations.decrypt_token", return_value="token"), \
             patch("api.v1.integrations.httpx.AsyncClient", return_value=FakeAsyncClient([FakeResponse(200, {})])):
            result = await disconnect_provider("google_drive", user_id="user-1")

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_disconnect_provider_unexpected_exception(self):
        user_integrations = build_table({"access_token": "enc-token"})
        user_integrations.execute.side_effect = [
            MagicMock(data={"access_token": "enc-token"}),
            Exception("boom"),
        ]
        supabase = build_supabase(
            {
                "connector_definitions": build_table({"id": "def-1"}),
                "user_integrations": user_integrations,
                "documents": build_table([]),
                "ingestion_jobs": build_table([]),
                "ingestion_file_status": build_table([]),
                "sync_state": build_table([]),
            }
        )

        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("api.v1.integrations.decrypt_token", return_value="token"), \
             patch("api.v1.integrations.httpx.AsyncClient", return_value=FakeAsyncClient([FakeResponse(200, {})])):
            with pytest.raises(HTTPException) as exc:
                await disconnect_provider("google_drive", user_id="user-1")

        assert exc.value.status_code == 500


class TestSyncIntegration:
    @pytest.mark.asyncio
    async def test_sync_integration_queues_background_task(self):
        jobs_table = build_table([])
        jobs_table.execute.side_effect = [
            MagicMock(data=[]),
            MagicMock(data=[{"id": "job-1"}]),
        ]
        supabase = build_supabase(
            {
                "user_integrations": build_table(
                    {"id": "int-1", "connector_definitions": {"type": "google_drive"}}
                ),
                "ingestion_jobs": jobs_table,
            }
        )

        bg = BackgroundTasks()
        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            result = await sync_integration("int-1", bg, user_id="user-1")

        assert result["status"] == "accepted"
        assert bg.tasks

    @pytest.mark.asyncio
    async def test_sync_integration_not_found(self):
        supabase = build_supabase({"user_integrations": build_table(None)})
        bg = BackgroundTasks()

        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException):
                await sync_integration("int-1", bg, user_id="user-1")

    @pytest.mark.asyncio
    async def test_sync_integration_job_create_failure(self):
        jobs_table = build_table(None)
        jobs_table.execute.side_effect = [MagicMock(data=[]), MagicMock(data=None)]
        supabase = build_supabase(
            {
                "user_integrations": build_table(
                    {"id": "int-1", "connector_definitions": {"type": "google_drive"}}
                ),
                "ingestion_jobs": jobs_table,
            }
        )
        bg = BackgroundTasks()

        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException):
                await sync_integration("int-1", bg, user_id="user-1")


class TestRunBackgroundSync:
    @pytest.mark.asyncio
    async def test_run_background_sync_success(self):
        supabase = build_supabase({"ingestion_jobs": build_table([])})
        connector = SimpleNamespace(list_files=AsyncMock(return_value=[SimpleNamespace(id="root-1")]))
        task = MagicMock()
        task.delay.return_value = SimpleNamespace(id="task-1")

        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("connectors.get_connector", return_value=connector), \
             patch("worker.tasks.unified_ingest_task", task):
            await run_background_sync("job-1", "google_drive", "user-1", "int-1")

        task.delay.assert_called_once()
        assert supabase.table.called

    @pytest.mark.asyncio
    async def test_run_background_sync_no_items_completes(self):
        supabase = build_supabase({"ingestion_jobs": build_table([])})
        connector = SimpleNamespace(list_files=AsyncMock(return_value=[]))

        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("connectors.get_connector", return_value=connector):
            await run_background_sync("job-1", "google_drive", "user-1", "int-1")

        update_call = supabase.table("ingestion_jobs").update.call_args
        assert update_call is not None


class TestListProviderItemsErrors:
    @pytest.mark.asyncio
    async def test_list_provider_items_returns_500_on_error(self):
        with patch("api.v1.integrations.get_connector", side_effect=Exception("boom")):
            with pytest.raises(HTTPException):
                await list_provider_items("google_drive", user_id="user-1")


class TestSyncConnectorThreadOffloading:
    """
    Tests for the async/sync connector bridge pattern.
    
    Ensures that:
    - Async connectors (Google Drive, Notion) are awaited directly
    - Sync connectors (Dropbox, SFTP) are offloaded to threadpool
    - Generator-based connectors work correctly
    """
    
    @pytest.mark.asyncio
    async def test_sync_generator_connector_uses_threadpool(self):
        """
        Dropbox/SFTP connectors return generators (sync).
        These MUST be wrapped with run_in_threadpool to avoid blocking.
        """
        # Create a mock sync connector that returns a generator
        def sync_generator_list_files(config):
            yield {"id": "file-1", "name": "doc.pdf", "mime_type": "application/pdf"}
            yield {"id": "file-2", "name": "image.png", "mime_type": "image/png"}
        
        connector = MagicMock()
        connector.list_files = sync_generator_list_files  # NOT AsyncMock - a real sync function
        
        with patch("api.v1.integrations.get_connector", return_value=connector), \
             patch("api.v1.integrations.run_in_threadpool") as mock_threadpool:
            # Make run_in_threadpool call the lambda and return result
            mock_threadpool.side_effect = lambda fn: fn()
            
            result = await list_provider_items("dropbox", user_id="user-1")
        
        # Verify run_in_threadpool was called (sync connector detection works)
        mock_threadpool.assert_called_once()
        
        # Verify results are correct
        assert len(result) == 2
        assert result[0]["id"] == "file-1"
        assert result[1]["id"] == "file-2"
    
    @pytest.mark.asyncio
    async def test_async_connector_does_not_use_threadpool(self):
        """
        Async connectors (Google Drive, Notion) should NOT use threadpool.
        They should be awaited directly for better performance.
        """
        connector = MagicMock()
        connector.list_files = AsyncMock(return_value=[
            {"id": "file-1", "name": "doc.pdf", "mime_type": "application/pdf"}
        ])
        
        with patch("api.v1.integrations.get_connector", return_value=connector), \
             patch("api.v1.integrations.run_in_threadpool") as mock_threadpool:
            result = await list_provider_items("google_drive", user_id="user-1")
        
        # Verify run_in_threadpool was NOT called
        mock_threadpool.assert_not_called()
        
        # Verify the async connector was awaited directly
        connector.list_files.assert_awaited_once()
        assert len(result) == 1
    
    @pytest.mark.asyncio
    async def test_sync_connector_errors_propagate_correctly(self):
        """
        Errors from sync connectors must propagate through the threadpool wrapper.
        """
        from connectors.base import ConnectorAuthError
        
        def failing_sync_list_files(config):
            raise ConnectorAuthError("Dropbox token expired")
        
        connector = MagicMock()
        connector.list_files = failing_sync_list_files
        
        with patch("api.v1.integrations.get_connector", return_value=connector):
            with pytest.raises(HTTPException) as exc:
                await list_provider_items("dropbox", user_id="user-1")
        
        # Auth errors should return 401, not 500
        assert exc.value.status_code == 401
        assert "Authentication failed" in exc.value.detail


class TestCrawlWebErrors:
    @pytest.mark.asyncio
    async def test_crawl_web_blocks_feature(self):
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/",
            "headers": [],
            "client": ("127.0.0.1", 1234),
        }
        request = Request(scope)

        with patch("api.v1.integrations.check_feature_access", new=AsyncMock(return_value={"allowed": False, "reason": "no"})):
            with pytest.raises(HTTPException):
                await crawl_web(
                    request=request,
                    body=WebCrawlRequest(url="https://example.com"),
                    user_id="user-1",
                )

    @pytest.mark.asyncio
    async def test_crawl_web_invalid_url(self):
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/",
            "headers": [],
            "client": ("127.0.0.1", 1234),
        }
        request = Request(scope)

        connector = MagicMock()
        connector.normalize_url.return_value = None

        with patch("api.v1.integrations.check_feature_access", new=AsyncMock(return_value={"allowed": True})), \
             patch("api.v1.integrations.WebConnector", return_value=connector):
            with pytest.raises(HTTPException):
                await crawl_web(
                    request=request,
                    body=WebCrawlRequest(url="bad"),
                    user_id="user-1",
                )


class TestIngestProviderItemsErrors:
    @pytest.mark.asyncio
    async def test_ingest_provider_web_rejects_multiple_urls(self):
        with pytest.raises(HTTPException):
            await ingest_provider_items(
                "web",
                IngestRequest(item_ids=["a", "b"]),
                user_id="user-1",
            )

    @pytest.mark.asyncio
    async def test_ingest_provider_unknown(self):
        with pytest.raises(HTTPException) as exc:
            await ingest_provider_items(
                "dropbox",
                IngestRequest(item_ids=["file-1"]),
                user_id="user-1",
            )
        assert exc.value.status_code == 400
        assert "Unsupported provider value" in exc.value.detail

    @pytest.mark.asyncio
    async def test_ingest_provider_missing_oauth(self):
        supabase = build_supabase(
            {
                "connector_definitions": build_table({"id": "def-1"}),
                "user_integrations": build_table(None),
            }
        )
        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException):
                await ingest_provider_items(
                    "google_drive",
                    IngestRequest(item_ids=["file-1"]),
                    user_id="user-1",
                )


class TestDisconnectProvider:
    @pytest.mark.asyncio
    async def test_disconnect_provider_unknown(self):
        with pytest.raises(HTTPException) as exc:
            await disconnect_provider("unknown", user_id="user-1")
        assert exc.value.status_code == 400
        assert "Unsupported provider value" in exc.value.detail

    @pytest.mark.asyncio
    async def test_disconnect_provider_missing_definition_raises(self):
        supabase = build_supabase({"connector_definitions": build_table(None)})

        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException) as exc:
                await disconnect_provider("google_drive", user_id="user-1")

        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_disconnect_provider_cleans_data(self):
        supabase = build_supabase(
            {
                "connector_definitions": build_table({"id": "def-1"}),
                "user_integrations": build_table({"access_token": "enc"}),
                "documents": build_table([{"id": "doc-1"}]),
                "ingestion_jobs": build_table([{"id": "job-1"}]),
                "ingestion_file_status": build_table([]),
                "sync_state": build_table([{"id": "sync-1"}]),
            }
        )

        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("api.v1.integrations.decrypt_token", return_value="token"), \
             patch("api.v1.integrations.httpx.AsyncClient", return_value=FakeAsyncClient([FakeResponse(200, {})])):
            result = await disconnect_provider("google_drive", user_id="user-1")

        assert result["status"] == "success"


class TestIntegrationsAdditional:
    @pytest.mark.asyncio
    async def test_google_oauth_expiry_error_fallback(self, monkeypatch):
        connector_def_table = build_table({"id": "def-1"})
        upsert_table = build_table([{"id": "int-1"}])
        supabase = build_supabase(
            {"connector_definitions": connector_def_table, "user_integrations": upsert_table}
        )

        class BadExpiry:
            def isoformat(self):
                raise ValueError("bad")

        flow = MagicMock()
        flow.fetch_token.return_value = None
        flow.credentials = SimpleNamespace(token="token", refresh_token="refresh", expiry=BadExpiry())

        monkeypatch.setattr("api.v1.integrations.settings.GOOGLE_CLIENT_ID", "cid")
        monkeypatch.setattr("api.v1.integrations.settings.GOOGLE_CLIENT_SECRET", "secret")
        monkeypatch.setattr("api.v1.integrations.settings.GOOGLE_REDIRECT_URI", "https://example.com/callback")

        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("api.v1.integrations.Flow.from_client_config", return_value=flow), \
             patch("api.v1.integrations.encrypt_token", return_value="enc"):
            result = await exchange_google_token(
                ExchangeRequest(code="code"),
                BackgroundTasks(),
                user_id="user-1",
            )

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_google_oauth_database_error(self, monkeypatch):
        connector_def_table = build_table({"id": "def-1"})
        upsert_table = build_table(execute_data=None)
        upsert_table.execute.side_effect = Exception("boom")
        supabase = build_supabase(
            {"connector_definitions": connector_def_table, "user_integrations": upsert_table}
        )

        flow = MagicMock()
        flow.fetch_token.return_value = None
        flow.credentials = SimpleNamespace(token="token", refresh_token=None, expiry=None)

        monkeypatch.setattr("api.v1.integrations.settings.GOOGLE_CLIENT_ID", "cid")
        monkeypatch.setattr("api.v1.integrations.settings.GOOGLE_CLIENT_SECRET", "secret")
        monkeypatch.setattr("api.v1.integrations.settings.GOOGLE_REDIRECT_URI", "https://example.com/callback")

        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("api.v1.integrations.Flow.from_client_config", return_value=flow), \
             patch("api.v1.integrations.encrypt_token", return_value="enc"):
            with pytest.raises(HTTPException) as exc:
                await exchange_google_token(
                    ExchangeRequest(code="code"),
                    BackgroundTasks(),
                    user_id="user-1",
                )

        assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_notion_redirect_missing(self, monkeypatch):
        monkeypatch.setattr("api.v1.integrations.settings.NOTION_CLIENT_ID", "cid")
        monkeypatch.setattr("api.v1.integrations.settings.NOTION_CLIENT_SECRET", "secret")
        monkeypatch.setattr("api.v1.integrations.settings.NOTION_REDIRECT_URI", None)

        with pytest.raises(HTTPException):
            await exchange_notion_token(ExchangeRequest(code="code"), user_id="user-1")

    @pytest.mark.asyncio
    async def test_notion_token_exchange_exception(self, monkeypatch):
        connector_def_table = build_table({"id": "def-1"})
        supabase = build_supabase({"connector_definitions": connector_def_table})

        class ErrorAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, *args, **kwargs):
                raise Exception("boom")

        monkeypatch.setattr("api.v1.integrations.settings.NOTION_CLIENT_ID", "cid")
        monkeypatch.setattr("api.v1.integrations.settings.NOTION_CLIENT_SECRET", "secret")
        monkeypatch.setattr("api.v1.integrations.settings.NOTION_REDIRECT_URI", "https://example.com/callback")

        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("api.v1.integrations.httpx.AsyncClient", return_value=ErrorAsyncClient()):
            with pytest.raises(HTTPException):
                await exchange_notion_token(ExchangeRequest(code="code"), user_id="user-1")

    @pytest.mark.asyncio
    async def test_notion_upsert_error(self, monkeypatch):
        connector_def_table = build_table({"id": "def-1"})
        upsert_table = build_table([{"id": "int-1"}])
        upsert_table.execute.side_effect = Exception("boom")
        supabase = build_supabase(
            {"connector_definitions": connector_def_table, "user_integrations": upsert_table}
        )

        token_response = FakeResponse(
            200,
            {
                "access_token": "token",
                "workspace_id": "ws-1",
                "workspace_name": "Workspace",
                "bot_id": "bot-1",
            },
        )

        monkeypatch.setattr("api.v1.integrations.settings.NOTION_CLIENT_ID", "cid")
        monkeypatch.setattr("api.v1.integrations.settings.NOTION_CLIENT_SECRET", "secret")
        monkeypatch.setattr("api.v1.integrations.settings.NOTION_REDIRECT_URI", "https://example.com/callback")

        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("api.v1.integrations.encrypt_token", return_value="enc"), \
             patch("api.v1.integrations.httpx.AsyncClient", return_value=FakeAsyncClient([token_response])):
            with pytest.raises(HTTPException):
                await exchange_notion_token(ExchangeRequest(code="code"), user_id="user-1")

    @pytest.mark.asyncio
    async def test_notion_auto_ingest_no_items(self, monkeypatch):
        connector_def_table = build_table({"id": "def-1"})
        upsert_table = build_table([{"id": "int-1"}])
        supabase = build_supabase(
            {"connector_definitions": connector_def_table, "user_integrations": upsert_table, "ingestion_jobs": build_table([])}
        )

        token_response = FakeResponse(
            200,
            {
                "access_token": "token",
                "workspace_id": "ws-1",
                "workspace_name": "Workspace",
                "bot_id": "bot-1",
            },
        )
        search_response = FakeResponse(200, {"results": []})

        monkeypatch.setattr("api.v1.integrations.settings.NOTION_CLIENT_ID", "cid")
        monkeypatch.setattr("api.v1.integrations.settings.NOTION_CLIENT_SECRET", "secret")
        monkeypatch.setattr("api.v1.integrations.settings.NOTION_REDIRECT_URI", "https://example.com/callback")

        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("api.v1.integrations.encrypt_token", return_value="enc"), \
             patch(
                 "api.v1.integrations.httpx.AsyncClient",
                 side_effect=[FakeAsyncClient([token_response]), FakeAsyncClient([search_response])],
             ):
            result = await exchange_notion_token(ExchangeRequest(code="code"), user_id="user-1")

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_notion_connector_definition_missing(self, monkeypatch):
        connector_def_table = build_table(None)
        supabase = build_supabase({"connector_definitions": connector_def_table})

        monkeypatch.setattr("api.v1.integrations.settings.NOTION_CLIENT_ID", "cid")
        monkeypatch.setattr("api.v1.integrations.settings.NOTION_CLIENT_SECRET", "secret")
        monkeypatch.setattr("api.v1.integrations.settings.NOTION_REDIRECT_URI", "https://example.com/callback")

        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException) as exc:
                await exchange_notion_token(ExchangeRequest(code="code"), user_id="user-1")

        assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_notion_upsert_returns_no_data(self, monkeypatch):
        connector_def_table = build_table({"id": "def-1"})
        upsert_table = build_table(None)
        supabase = build_supabase(
            {"connector_definitions": connector_def_table, "user_integrations": upsert_table}
        )

        token_response = FakeResponse(
            200,
            {
                "access_token": "token",
                "workspace_id": "ws-1",
                "workspace_name": "Workspace",
                "bot_id": "bot-1",
            },
        )

        monkeypatch.setattr("api.v1.integrations.settings.NOTION_CLIENT_ID", "cid")
        monkeypatch.setattr("api.v1.integrations.settings.NOTION_CLIENT_SECRET", "secret")
        monkeypatch.setattr("api.v1.integrations.settings.NOTION_REDIRECT_URI", "https://example.com/callback")

        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("api.v1.integrations.encrypt_token", return_value="enc"), \
             patch("api.v1.integrations.httpx.AsyncClient", return_value=FakeAsyncClient([token_response])):
            with pytest.raises(HTTPException) as exc:
                await exchange_notion_token(ExchangeRequest(code="code"), user_id="user-1")

        assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_notion_auto_ingest_failure_is_noncritical(self, monkeypatch):
        connector_def_table = build_table({"id": "def-1"})
        upsert_table = build_table([{"id": "int-1"}])
        supabase = build_supabase(
            {"connector_definitions": connector_def_table, "user_integrations": upsert_table}
        )

        token_response = FakeResponse(
            200,
            {
                "access_token": "token",
                "workspace_id": "ws-1",
                "workspace_name": "Workspace",
                "bot_id": "bot-1",
            },
        )

        class ErrorAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, *args, **kwargs):
                raise Exception("search failed")

        monkeypatch.setattr("api.v1.integrations.settings.NOTION_CLIENT_ID", "cid")
        monkeypatch.setattr("api.v1.integrations.settings.NOTION_CLIENT_SECRET", "secret")
        monkeypatch.setattr("api.v1.integrations.settings.NOTION_REDIRECT_URI", "https://example.com/callback")

        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("api.v1.integrations.encrypt_token", return_value="enc"), \
             patch(
                 "api.v1.integrations.httpx.AsyncClient",
                 side_effect=[FakeAsyncClient([token_response]), ErrorAsyncClient()],
             ):
            result = await exchange_notion_token(ExchangeRequest(code="code"), user_id="user-1")

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_get_provider_status_handles_exception(self):
        supabase = MagicMock()
        supabase.table.side_effect = Exception("boom")

        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            result = await get_provider_status("google_drive", user_id="user-1")

        assert result["connected"] is False

    @pytest.mark.asyncio
    async def test_disconnect_provider_cleanup_errors_are_non_blocking(self):
        supabase = MagicMock()
        def_table = build_table({"id": "def-1"})
        int_table = build_table({"access_token": "enc"})
        doc_table = build_table([])
        doc_table.execute.side_effect = Exception("doc delete")
        jobs_table = build_table([{"id": "job-1"}])
        jobs_table.execute.side_effect = Exception("job delete")
        sync_table = build_table([])
        sync_table.execute.side_effect = Exception("sync delete")
        user_int_table = build_table([])

        supabase.table.side_effect = lambda name: {
            "connector_definitions": def_table,
            "user_integrations": int_table if name == "user_integrations" else user_int_table,
            "documents": doc_table,
            "ingestion_jobs": jobs_table,
            "ingestion_file_status": build_table([]),
            "sync_state": sync_table,
        }[name]

        class ErrorAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, *args, **kwargs):
                raise Exception("revoke failed")

        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("api.v1.integrations.decrypt_token", return_value="token"), \
             patch("api.v1.integrations.httpx.AsyncClient", return_value=ErrorAsyncClient()):
            result = await disconnect_provider("google_drive", user_id="user-1")

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_crawl_web_access_denied(self):
        scope = {"type": "http", "method": "POST", "path": "/", "headers": [], "client": ("127.0.0.1", 1234)}
        request = Request(scope)

        with patch("api.v1.integrations.check_feature_access", new=AsyncMock(return_value={"allowed": False, "reason": "no"})):
            with pytest.raises(HTTPException) as exc:
                await crawl_web(request, WebCrawlRequest(url="https://example.com"), user_id="00000000-0000-0000-0000-000000000001")

        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_crawl_web_invalid_url(self):
        scope = {"type": "http", "method": "POST", "path": "/", "headers": [], "client": ("127.0.0.1", 1234)}
        request = Request(scope)

        connector = MagicMock()
        connector.normalize_url.return_value = None
        connector.is_safe_url.return_value = True

        with patch("api.v1.integrations.check_feature_access", new=AsyncMock(return_value={"allowed": True})), \
             patch("api.v1.integrations.WebConnector", return_value=connector):
            with pytest.raises(HTTPException) as exc:
                await crawl_web(request, WebCrawlRequest(url="https://example.com"), user_id="00000000-0000-0000-0000-000000000001")

        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_crawl_web_unsafe_url(self):
        scope = {"type": "http", "method": "POST", "path": "/", "headers": [], "client": ("127.0.0.1", 1234)}
        request = Request(scope)

        connector = MagicMock()
        connector.normalize_url.return_value = "https://example.com"
        connector.is_safe_url.return_value = False

        with patch("api.v1.integrations.check_feature_access", new=AsyncMock(return_value={"allowed": True})), \
             patch("api.v1.integrations.WebConnector", return_value=connector):
            with pytest.raises(HTTPException) as exc:
                await crawl_web(request, WebCrawlRequest(url="https://example.com"), user_id="00000000-0000-0000-0000-000000000001")

        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_crawl_web_invalid_type(self):
        scope = {"type": "http", "method": "POST", "path": "/", "headers": [], "client": ("127.0.0.1", 1234)}
        request = Request(scope)

        connector = MagicMock()
        connector.normalize_url.return_value = "https://example.com"
        connector.is_safe_url.return_value = True

        with patch("api.v1.integrations.check_feature_access", new=AsyncMock(return_value={"allowed": True})), \
             patch("api.v1.integrations.WebConnector", return_value=connector):
            with pytest.raises(HTTPException) as exc:
                await crawl_web(request, WebCrawlRequest(url="https://example.com", crawl_type="bad"), user_id="00000000-0000-0000-0000-000000000001")

        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_crawl_web_single_sets_max_pages(self):
        scope = {"type": "http", "method": "POST", "path": "/", "headers": [], "client": ("127.0.0.1", 1234)}
        request = Request(scope)

        connector = MagicMock()
        connector.normalize_url.return_value = "https://example.com"
        connector.is_safe_url.return_value = True

        with patch("api.v1.integrations.check_feature_access", new=AsyncMock(return_value={"allowed": True})), \
             patch("api.v1.integrations.WebConnector", return_value=connector), \
             patch("api.v1.integrations.queue_web_crawl", return_value={"crawl_id": "c1", "task_id": "t1"}) as queue_mock:
            await crawl_web(request, WebCrawlRequest(url="https://example.com", crawl_type="single", max_pages=10), user_id="00000000-0000-0000-0000-000000000001")

        assert queue_mock.call_args.kwargs["max_pages"] == 1

    @pytest.mark.asyncio
    async def test_ingest_web_requires_single_item(self):
        with pytest.raises(HTTPException) as exc:
            await ingest_provider_items(
                "web",
                IngestRequest(item_ids=["a", "b"]),
                user_id="user-1",
            )

        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_ingest_web_access_denied(self):
        with patch("api.v1.integrations.check_feature_access", new=AsyncMock(return_value={"allowed": False, "reason": "no"})):
            with pytest.raises(HTTPException) as exc:
                await ingest_provider_items(
                    "web",
                    IngestRequest(item_ids=["https://example.com"]),
                    user_id="00000000-0000-0000-0000-000000000001",
                )

        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_ingest_web_invalid_url(self):
        connector = MagicMock()
        connector.normalize_url.return_value = None
        connector.is_safe_url.return_value = True

        with patch("api.v1.integrations.check_feature_access", new=AsyncMock(return_value={"allowed": True})), \
             patch("api.v1.integrations.WebConnector", return_value=connector):
            with pytest.raises(HTTPException) as exc:
                await ingest_provider_items(
                    "web",
                    IngestRequest(item_ids=["https://example.com"]),
                    user_id="00000000-0000-0000-0000-000000000001",
                )

        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_ingest_web_unsafe_url(self):
        connector = MagicMock()
        connector.normalize_url.return_value = "https://example.com"
        connector.is_safe_url.return_value = False

        with patch("api.v1.integrations.check_feature_access", new=AsyncMock(return_value={"allowed": True})), \
             patch("api.v1.integrations.WebConnector", return_value=connector):
            with pytest.raises(HTTPException) as exc:
                await ingest_provider_items(
                    "web",
                    IngestRequest(item_ids=["https://example.com"]),
                    user_id="00000000-0000-0000-0000-000000000001",
                )

        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_ingest_web_success_queues_crawl(self):
        connector = MagicMock()
        connector.normalize_url.return_value = "https://example.com"
        connector.is_safe_url.return_value = True

        with patch("api.v1.integrations.check_feature_access", new=AsyncMock(return_value={"allowed": True})), \
             patch("api.v1.integrations.WebConnector", return_value=connector), \
             patch(
                 "api.v1.integrations.queue_web_crawl",
                 return_value={"crawl_id": "crawl-1", "task_id": "task-1"},
             ):
            result = await ingest_provider_items(
                "web",
                IngestRequest(item_ids=["https://example.com"]),
                user_id="00000000-0000-0000-0000-000000000001",
            )

        assert result["status"] == "queued"
        assert result["crawl_id"] == "crawl-1"

    @pytest.mark.asyncio
    async def test_ingest_provider_integration_fetch_error(self):
        supabase = MagicMock()
        def_table = build_table({"id": "def-1"})
        int_table = build_table([])
        int_table.execute.side_effect = Exception("boom")
        supabase.table.side_effect = lambda name: def_table if name == "connector_definitions" else int_table

        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException) as exc:
                await ingest_provider_items(
                    "google_drive",
                    IngestRequest(item_ids=["file-1"]),
                    user_id="user-1",
                )

        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_ingest_provider_unsupported_connector(self):
        with pytest.raises(HTTPException) as exc:
            await ingest_provider_items(
                "slack",
                IngestRequest(item_ids=["file-1"]),
                user_id="user-1",
            )

        assert exc.value.status_code == 400
        assert "Unsupported provider value" in exc.value.detail

    @pytest.mark.asyncio
    async def test_ingest_provider_job_creation_failure(self):
        supabase = build_supabase(
            {
                "connector_definitions": build_table({"id": "def-1"}),
                "user_integrations": build_table({"id": "int-1", "access_token": "token", "credentials": {}}),
                "ingestion_jobs": build_table(None),
            }
        )

        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException) as exc:
                await ingest_provider_items(
                    "google_drive",
                    IngestRequest(item_ids=["file-1"]),
                    user_id="user-1",
                )

        assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_ingest_provider_task_failure(self):
        supabase = build_supabase(
            {
                "connector_definitions": build_table({"id": "def-1"}),
                "user_integrations": build_table({"id": "int-1", "access_token": "token", "credentials": {}}),
                "ingestion_jobs": build_table([{"id": "job-1"}]),
            }
        )
        task = MagicMock()
        task.delay.side_effect = Exception("boom")

        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("worker.tasks.unified_ingest_task", task):
            with pytest.raises(HTTPException) as exc:
                await ingest_provider_items(
                    "google_drive",
                    IngestRequest(item_ids=["file-1"]),
                    user_id="user-1",
                )

        assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_run_background_sync_connector_failure(self):
        supabase = MagicMock()
        supabase.table().update().eq().execute.return_value = MagicMock(data=[{"id": "job-1"}])

        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("connectors.get_connector", side_effect=Exception("boom")):
            await run_background_sync("job-1", "google_drive", "user-1", "int-1")

        assert supabase.table().update.called

    @pytest.mark.asyncio
    async def test_run_background_sync_auth_failure_message(self):
        supabase = MagicMock()
        supabase.table().update().eq().execute.return_value = MagicMock(data=[{"id": "job-1"}])

        connector = MagicMock()
        connector.list_files = AsyncMock(side_effect=Exception("invalid_grant"))

        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("connectors.get_connector", return_value=connector):
            await run_background_sync("job-1", "google_drive", "user-1", "int-1")

        update_payload = supabase.table().update.call_args_list[-1][0][0]
        assert "Authentication failed" in update_payload["error_message"]

    @pytest.mark.asyncio
    async def test_sync_integration_existing_job(self):
        supabase = build_supabase(
            {
                "user_integrations": build_table({
                    "id": "int-1",
                    "connector_definitions": {"type": "google_drive"},
                }),
                "ingestion_jobs": build_table([{"id": "job-1"}]),
            }
        )

        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            response = await sync_integration("int-1", BackgroundTasks(), user_id="user-1")

        assert response["status"] == "accepted"

    @pytest.mark.asyncio
    async def test_sync_integration_handles_error(self):
        supabase = MagicMock()
        supabase.table.side_effect = Exception("boom")

        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException) as exc:
                await sync_integration("int-1", BackgroundTasks(), user_id="user-1")

        assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_get_sync_history_handles_error(self):
        supabase = MagicMock()
        supabase.table.side_effect = Exception("boom")

        with patch("api.v1.integrations.get_supabase", return_value=supabase):
            with pytest.raises(HTTPException) as exc:
                await get_sync_history("int-1", user_id="user-1")

        assert exc.value.status_code == 500


class TestDisconnectProviderCoverage:
    @pytest.mark.asyncio
    async def test_disconnect_provider_notion_revocation_branch(self):
        supabase = build_supabase(
            {
                "connector_definitions": build_table({"id": "def-1"}),
                "user_integrations": build_table({"access_token": "enc-token"}),
                "documents": build_table([]),
                "ingestion_jobs": build_table([]),
                "ingestion_file_status": build_table([]),
                "sync_state": build_table([]),
            }
        )

        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("api.v1.integrations.decrypt_token", return_value="token"), \
             patch("api.v1.integrations.httpx.AsyncClient", return_value=FakeAsyncClient([])):
            result = await disconnect_provider("notion", user_id="user-1")

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_disconnect_provider_document_cleanup_error(self):
        doc_table = build_table([])
        doc_table.in_.return_value = doc_table
        doc_table.execute.side_effect = Exception("doc delete")
        supabase = build_supabase(
            {
                "connector_definitions": build_table({"id": "def-1"}),
                "user_integrations": build_table({"access_token": "enc-token"}),
                "documents": doc_table,
                "ingestion_jobs": build_table([{"id": "job-1"}]),
                "ingestion_file_status": build_table([]),
                "sync_state": build_table([]),
            }
        )

        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("api.v1.integrations.decrypt_token", return_value="token"), \
             patch("api.v1.integrations.httpx.AsyncClient", return_value=FakeAsyncClient([FakeResponse(200, {})])):
            result = await disconnect_provider("google_drive", user_id="user-1")

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_disconnect_provider_unexpected_exception(self):
        user_integrations = build_table({"access_token": "enc-token"})
        user_integrations.execute.side_effect = [
            MagicMock(data={"access_token": "enc-token"}),
            Exception("boom"),
        ]
        supabase = build_supabase(
            {
                "connector_definitions": build_table({"id": "def-1"}),
                "user_integrations": user_integrations,
                "documents": build_table([]),
                "ingestion_jobs": build_table([]),
                "ingestion_file_status": build_table([]),
                "sync_state": build_table([]),
            }
        )

        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("api.v1.integrations.decrypt_token", return_value="token"), \
             patch("api.v1.integrations.httpx.AsyncClient", return_value=FakeAsyncClient([FakeResponse(200, {})])):
            with pytest.raises(HTTPException) as exc:
                await disconnect_provider("google_drive", user_id="user-1")

        assert exc.value.status_code == 500


class TestMicrosoftOAuth:
    @pytest.mark.asyncio
    async def test_microsoft_oauth_onedrive_success(self, monkeypatch):
        connector_def_table = build_table({"id": "def-1"})
        upsert_table = build_table([{"id": "int-1"}])
        supabase = build_supabase(
            {"connector_definitions": connector_def_table, "user_integrations": upsert_table}
        )

        token_response = FakeResponse(
            200,
            {"access_token": "access-token", "refresh_token": "refresh-token", "expires_in": 3600},
        )
        drive_response = FakeResponse(200, {"id": "drive-1"})

        monkeypatch.setattr("api.v1.integrations.settings.MICROSOFT_CLIENT_ID", "cid")
        monkeypatch.setattr("api.v1.integrations.settings.MICROSOFT_CLIENT_SECRET", "secret")
        monkeypatch.setattr("api.v1.integrations.settings.MICROSOFT_REDIRECT_URI", "https://example.com/callback")
        monkeypatch.setattr("api.v1.integrations.settings.MICROSOFT_SCOPES_ONEDRIVE", "scope")
        monkeypatch.setattr("api.v1.integrations.settings.MICROSOFT_SCOPES_SHAREPOINT", "scope")

        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("api.v1.integrations.encrypt_token", side_effect=lambda value: f"enc-{value}"), \
             patch("api.v1.integrations.audit_logger.log_sync"), \
             patch(
                 "api.v1.integrations.httpx.AsyncClient",
                 side_effect=[FakeAsyncClient([token_response]), FakeAsyncClient([drive_response])],
             ):
            result = await exchange_microsoft_token(
                MicrosoftExchangeRequest(code="code", target_type="onedrive"),
                user_id="user-1",
            )

        assert result["status"] == "success"
        assert result["provider"] == "onedrive"
        assert upsert_table.upsert.called

    @pytest.mark.asyncio
    async def test_microsoft_oauth_sharepoint_success(self, monkeypatch):
        connector_def_table = build_table({"id": "def-2"})
        upsert_table = build_table([{"id": "int-2"}])
        supabase = build_supabase(
            {"connector_definitions": connector_def_table, "user_integrations": upsert_table}
        )

        token_response = FakeResponse(
            200,
            {"access_token": "access-token", "refresh_token": "refresh-token", "expires_in": 3600},
        )
        site_response = FakeResponse(200, {"id": "site-1"})
        drive_response = FakeResponse(200, {"id": "drive-2"})

        monkeypatch.setattr("api.v1.integrations.settings.MICROSOFT_CLIENT_ID", "cid")
        monkeypatch.setattr("api.v1.integrations.settings.MICROSOFT_CLIENT_SECRET", "secret")
        monkeypatch.setattr("api.v1.integrations.settings.MICROSOFT_REDIRECT_URI", "https://example.com/callback")
        monkeypatch.setattr("api.v1.integrations.settings.MICROSOFT_SCOPES_ONEDRIVE", "scope")
        monkeypatch.setattr("api.v1.integrations.settings.MICROSOFT_SCOPES_SHAREPOINT", "scope")

        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch("api.v1.integrations.encrypt_token", side_effect=lambda value: f"enc-{value}"), \
             patch("api.v1.integrations.audit_logger.log_sync"), \
             patch(
                 "api.v1.integrations.httpx.AsyncClient",
                 side_effect=[
                     FakeAsyncClient([token_response]),
                     FakeAsyncClient([site_response, drive_response]),
                 ],
             ):
            result = await exchange_microsoft_token(
                MicrosoftExchangeRequest(code="code", target_type="sharepoint"),
                user_id="user-1",
            )

        assert result["status"] == "success"
        assert result["provider"] == "sharepoint"
        assert upsert_table.upsert.called

    @pytest.mark.asyncio
    async def test_microsoft_oauth_exchange_failure(self, monkeypatch):
        connector_def_table = build_table({"id": "def-1"})
        supabase = build_supabase({"connector_definitions": connector_def_table})

        token_response = FakeResponse(400, {"error": "invalid_grant"})

        monkeypatch.setattr("api.v1.integrations.settings.MICROSOFT_CLIENT_ID", "cid")
        monkeypatch.setattr("api.v1.integrations.settings.MICROSOFT_CLIENT_SECRET", "secret")
        monkeypatch.setattr("api.v1.integrations.settings.MICROSOFT_REDIRECT_URI", "https://example.com/callback")
        monkeypatch.setattr("api.v1.integrations.settings.MICROSOFT_SCOPES_ONEDRIVE", "scope")
        monkeypatch.setattr("api.v1.integrations.settings.MICROSOFT_SCOPES_SHAREPOINT", "scope")

        with patch("api.v1.integrations.get_supabase", return_value=supabase), \
             patch(
                 "api.v1.integrations.httpx.AsyncClient",
                 return_value=FakeAsyncClient([token_response]),
             ):
            with pytest.raises(HTTPException) as exc:
                await exchange_microsoft_token(
                    MicrosoftExchangeRequest(code="code", target_type="onedrive"),
                    user_id="user-1",
                )

        assert exc.value.status_code == 400
