import asyncio
import requests
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from connectors.notion import NotionConnector
from connectors.base import ConnectorDocument, ConnectorItem
from services.oauth_token_manager import TokenRefreshError
from core.config import settings


def test_get_connector_definition_id_success():
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"id": "def-1"}
    )

    with patch("connectors.notion.get_supabase", return_value=supabase):
        connector = NotionConnector()
        assert connector._get_connector_definition_id() == "def-1"


def test_get_connector_definition_id_missing():
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data=None
    )

    with patch("connectors.notion.get_supabase", return_value=supabase):
        connector = NotionConnector()
        with pytest.raises(ValueError):
            connector._get_connector_definition_id()


def test_authorize_returns_true_when_connected():
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": "int-1"}]
    )

    with patch("connectors.notion.get_supabase", return_value=supabase), \
         patch.object(NotionConnector, "_get_connector_definition_id", return_value="def-1"):
        connector = NotionConnector()
        assert connector._authorize_implementation("user-1") is True


def test_authorize_async_wrapper_uses_threadpool():
    connector = NotionConnector()
    with patch("connectors.notion.run_in_threadpool", new_callable=AsyncMock) as run_in_threadpool:
        run_in_threadpool.return_value = True
        result = asyncio.run(connector.authorize("user-1"))

    assert result is True
    run_in_threadpool.assert_awaited_once_with(connector._authorize_implementation, "user-1")


def test_get_access_token_raises_when_missing():
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[]
    )

    with patch("connectors.notion.get_supabase", return_value=supabase), \
         patch.object(NotionConnector, "_get_connector_definition_id", return_value="def-1"):
        connector = NotionConnector()
        with pytest.raises(ValueError):
            connector._get_access_token("user-1")


def test_get_access_token_refresh_error():
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": "int-1"}]
    )

    with patch("connectors.notion.get_supabase", return_value=supabase), \
         patch.object(NotionConnector, "_get_connector_definition_id", return_value="def-1"), \
         patch("services.oauth_token_manager.OAuthTokenManager.get_valid_credentials", side_effect=TokenRefreshError("refresh")):
        connector = NotionConnector()
        with pytest.raises(ValueError):
            connector._get_access_token("user-1")


def test_list_items_top_level_pages_and_databases():
    connector = NotionConnector()

    page_result = {
        "results": [
            {
                "id": "page-1",
                "parent": {"type": "workspace"},
                "properties": {
                    "title": {"type": "title", "title": [{"plain_text": "Page"}]}
                },
                "icon": {"type": "emoji", "emoji": "📄"},
            },
            {"id": "page-2", "parent": {"type": "database"}},
        ]
    }
    db_result = {
        "results": [
            {
                "id": "db-1",
                "parent": {"type": "workspace"},
                "title": [{"plain_text": "Database"}],
            }
        ]
    }

    with patch.object(connector, "_get_access_token", return_value="token"), \
         patch.object(connector, "_make_request", side_effect=[page_result, db_result]):
        items = connector._list_items_implementation("user-1", parent_id=None)

    assert len(items) == 2
    assert items[0].name == "Page"
    assert items[1].name == "Database"


def test_list_items_root_aliases_to_none():
    connector = NotionConnector()
    search_result = {"results": []}

    with patch.object(connector, "_get_access_token", return_value="token"), \
         patch.object(connector, "_make_request", side_effect=[search_result, search_result]) as mock_request:
        items = connector._list_items_implementation("user-1", parent_id="root")

    assert items == []
    assert mock_request.call_count == 2


def test_list_items_children():
    connector = NotionConnector()
    child_result = {
        "results": [
            {"id": "child-1", "type": "child_page", "child_page": {"title": "Child"}},
            {"id": "db-1", "type": "child_database", "child_database": {"title": "DB"}},
        ]
    }

    with patch.object(connector, "_get_access_token", return_value="token"), \
         patch.object(connector, "_make_request", return_value=child_result):
        items = connector._list_items_implementation("user-1", parent_id="page-1")

    assert len(items) == 2
    assert items[0].name == "Child"


def test_list_items_children_handles_error():
    connector = NotionConnector()
    with patch.object(connector, "_get_access_token", return_value="token"), \
         patch.object(connector, "_make_request", side_effect=RuntimeError("boom")):
        items = connector._list_items_implementation("user-1", parent_id="page-1")

    assert items == []


def test_list_items_async_wrapper_uses_threadpool():
    connector = NotionConnector()
    with patch("connectors.notion.run_in_threadpool", new_callable=AsyncMock) as run_in_threadpool:
        run_in_threadpool.return_value = []
        result = asyncio.run(connector.list_items("user-1", parent_id="root"))

    assert result == []
    run_in_threadpool.assert_awaited_once_with(connector._list_items_implementation, "user-1", "root")


def test_extract_text_from_blocks_formats_output():
    connector = NotionConnector()
    blocks = [
        {"type": "heading_1", "heading_1": {"rich_text": [{"plain_text": "Title"}]}},
        {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Hello"}]}},
        {"type": "code", "code": {"language": "python", "rich_text": [{"plain_text": "print('hi')"}]}},
    ]

    content = connector._extract_text_from_blocks(blocks)
    assert "# Title" in content
    assert "Hello" in content
    assert "```python" in content


def test_extract_text_from_blocks_includes_divider_and_lists():
    connector = NotionConnector()
    blocks = [
        {"type": "divider"},
        {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"plain_text": "Item"}]}},
    ]

    content = connector._extract_text_from_blocks(blocks)
    assert "---" in content
    assert "• Item" in content


def test_ingest_implementation_yields_document():
    connector = NotionConnector()

    def make_request_side_effect(method, endpoint, access_token, json_data=None):
        if endpoint.startswith("pages/"):
            return {
                "properties": {
                    "title": {"type": "title", "title": [{"plain_text": "Page"}]}
                },
                "url": "https://notion.so/page",
            }
        if endpoint.startswith("blocks/") and "children" in endpoint:
            return {
                "results": [
                    {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Hello"}]}}
                ],
                "has_more": False,
            }
        return {}

    config = {
        "item_ids": ["page-1"],
        "credentials": {"access_token": "token"},
    }

    with patch.object(connector, "_make_request", side_effect=make_request_side_effect):
        docs = list(connector._ingest_implementation(config))

    assert len(docs) == 1
    assert docs[0].metadata["page_id"] == "page-1"


def test_ingest_implementation_recurses_children_and_databases():
    connector = NotionConnector()

    def make_request_side_effect(method, endpoint, access_token, json_data=None):
        if endpoint.startswith("pages/"):
            page_id = endpoint.split("/")[-1]
            return {
                "properties": {
                    "title": {"type": "title", "title": [{"plain_text": f"Page-{page_id}"}]}
                },
                "url": f"https://notion.so/{page_id}",
            }
        if endpoint.startswith("blocks/page-1/children"):
            return {
                "results": [
                    {"type": "child_page", "id": "child-1"},
                    {"type": "child_database", "id": "db-1"},
                    {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Hello"}]}},
                ],
                "has_more": False,
            }
        if endpoint.startswith("databases/db-1/query"):
            return {"results": [{"id": "db-page-1"}]}
        if endpoint.startswith("blocks/child-1/children"):
            return {
                "results": [
                    {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Child"}]}}
                ],
                "has_more": False,
            }
        if endpoint.startswith("blocks/db-page-1/children"):
            return {
                "results": [
                    {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "DB"}]}}
                ],
                "has_more": False,
            }
        return {"results": [], "has_more": False}

    config = {
        "item_ids": ["page-1"],
        "credentials": {"access_token": "token"},
    }

    with patch.object(connector, "_make_request", side_effect=make_request_side_effect):
        docs = list(connector._ingest_implementation(config))

    assert len(docs) == 3
    assert {doc.metadata["page_id"] for doc in docs} == {"page-1", "child-1", "db-page-1"}


def test_ingest_implementation_missing_integration_id_raises():
    connector = NotionConnector()
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data=None
    )

    with patch("connectors.notion.get_supabase", return_value=supabase):
        with pytest.raises(ValueError):
            list(connector._ingest_implementation({
                "credentials": {"integration_id": "int-1"},
                "item_ids": ["page-1"],
            }))


def test_ingest_implementation_requires_credentials():
    connector = NotionConnector()
    with pytest.raises(ValueError):
        list(connector._ingest_implementation({"item_ids": ["page-1"]}))


def test_make_request_records_rate_limit(monkeypatch):
    connector = NotionConnector()
    response = MagicMock()
    response.status_code = 429
    response.raise_for_status = MagicMock()
    response.json.return_value = {"ok": True}

    counter = MagicMock()
    counter.labels.return_value = counter

    monkeypatch.setattr("connectors.notion.requests.request", lambda **kwargs: response)
    monkeypatch.setattr("core.metrics.retry_total", counter)

    result = connector._make_request("GET", "pages/x", "token")

    assert result == {"ok": True}
    counter.labels.assert_called_with("notion", "rate_limit")


def test_make_request_rate_limit_metrics_error_is_ignored(monkeypatch):
    connector = NotionConnector()
    response = MagicMock()
    response.status_code = 429
    response.raise_for_status = MagicMock()
    response.json.return_value = {"ok": True}

    class Counter:
        def labels(self, *_args, **_kwargs):
            raise RuntimeError("metrics down")

    monkeypatch.setattr("connectors.notion.requests.request", lambda **kwargs: response)
    monkeypatch.setattr("core.metrics.retry_total", Counter())

    result = connector._make_request("GET", "pages/x", "token")

    assert result == {"ok": True}


def test_ingest_async_wrapper_uses_iterate_in_threadpool():
    connector = NotionConnector()
    config = {"item_ids": ["page-1"], "credentials": {"access_token": "token"}}

    with patch.object(connector, "_ingest_implementation", return_value="gen"), \
         patch("starlette.concurrency.iterate_in_threadpool", return_value="stream") as iterate_in_threadpool:
        result = asyncio.run(connector.ingest(config))

    assert result == "stream"
    iterate_in_threadpool.assert_called_once_with("gen")


def test_sync_implementation_processes_documents(monkeypatch):
    connector = NotionConnector()
    doc = ConnectorDocument(page_content="hello", metadata={"title": "Doc", "page_id": "page-1", "source_url": "url"})

    monkeypatch.setattr(connector, "_list_items_implementation", lambda user_id, parent_id=None: [ConnectorItem(id="page-1", name="Doc", type="folder")])
    monkeypatch.setattr(connector, "_ingest_implementation", lambda config: [doc])

    supabase = MagicMock()

    def make_table(responses):
        table = MagicMock()
        table.select.return_value = table
        table.insert.return_value = table
        table.update.return_value = table
        table.eq.return_value = table
        table.limit.return_value = table
        table.execute.side_effect = [SimpleNamespace(data=resp) for resp in responses]
        return table

    tables = {
        "ingestion_jobs": make_table([[{"id": "job-1"}], [{"id": "job-1"}], [{"id": "job-1"}]]),
        "documents": make_table([[], [{"id": "doc-1"}]]),
        "user_integrations": make_table([[{"id": "int-1"}]]),
    }
    supabase.table.side_effect = lambda name: tables[name]

    monkeypatch.setattr("core.db.get_supabase", lambda: supabase)
    monkeypatch.setattr("services.embeddings.generate_embeddings_batch_sync", lambda chunks: [[0.1] * 3 for _ in chunks])
    monkeypatch.setattr("connectors.notion.insert_rows_with_retry", lambda *args, **kwargs: None)
    monkeypatch.setattr("connectors.notion.compute_content_hash", lambda *_: "hash")
    monkeypatch.setattr("worker.tasks.create_file_status", lambda *args, **kwargs: "status-1")
    monkeypatch.setattr("worker.tasks.update_file_status", lambda *args, **kwargs: None)
    monkeypatch.setattr("connectors.notion.settings", settings)
    monkeypatch.setattr(settings, "MAX_FILE_SIZE", 10 * 1024 * 1024)
    monkeypatch.setattr(settings, "CHUNK_INSERT_BATCH_SIZE", 10)

    result = connector._sync_implementation("user-1", "int-1")

    assert result["status"] == "success"
    assert result["files_processed"] == 1


def test_sync_async_wrapper_uses_threadpool():
    connector = NotionConnector()
    with patch("connectors.notion.run_in_threadpool", new_callable=AsyncMock) as run_in_threadpool:
        run_in_threadpool.return_value = {"status": "success"}
        result = asyncio.run(connector.sync("user-1", "int-1"))

    assert result == {"status": "success"}
    run_in_threadpool.assert_awaited_once_with(connector._sync_implementation, "user-1", "int-1")


def test_get_access_token_success():
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": "int-1"}]
    )

    with patch("connectors.notion.get_supabase", return_value=supabase), \
         patch.object(NotionConnector, "_get_connector_definition_id", return_value="def-1"), \
         patch("services.oauth_token_manager.OAuthTokenManager.get_valid_credentials", return_value={"access_token": "token"}):
        connector = NotionConnector()
        assert connector._get_access_token("user-1") == "token"


def test_list_items_skips_non_workspace_database_and_sets_icon():
    connector = NotionConnector()

    page_result = {"results": []}
    db_result = {
        "results": [
            {"id": "db-1", "parent": {"type": "database"}, "title": [{"plain_text": "Skip"}]},
            {"id": "db-2", "parent": {"type": "workspace"}, "title": [{"plain_text": "DB"}], "icon": {"type": "emoji", "emoji": "🧠"}},
        ]
    }

    with patch.object(connector, "_get_access_token", return_value="token"), \
         patch.object(connector, "_make_request", side_effect=[page_result, db_result]):
        items = connector._list_items_implementation("user-1", parent_id=None)

    assert len(items) == 1
    assert items[0].icon == "🧠"


def test_extract_text_from_blocks_heading_and_quote():
    connector = NotionConnector()
    blocks = [
        {"type": "heading_2", "heading_2": {"rich_text": [{"plain_text": "H2"}]}},
        {"type": "heading_3", "heading_3": {"rich_text": [{"plain_text": "H3"}]}},
        {"type": "quote", "quote": {"rich_text": [{"plain_text": "Quoted"}]}},
    ]

    content = connector._extract_text_from_blocks(blocks)
    assert "## H2" in content
    assert "### H3" in content
    assert "> Quoted" in content


def test_ingest_implementation_uses_integration_id_credentials():
    connector = NotionConnector()
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"id": "int-1"}
    )

    with patch("connectors.notion.get_supabase", return_value=supabase), \
         patch("services.oauth_token_manager.OAuthTokenManager.get_valid_credentials", return_value={"access_token": "token"}):
        list(
            connector._ingest_implementation(
                {"item_ids": [], "credentials": {"integration_id": "int-1"}}
            )
        )


def test_ingest_implementation_fallback_user_id():
    connector = NotionConnector()
    with patch.object(connector, "_get_access_token", return_value="token"):
        list(connector._ingest_implementation({"item_ids": [], "user_id": "user-1"}))


def test_ingest_implementation_recursion_guard_and_cursor(monkeypatch):
    connector = NotionConnector()

    def make_request(method, endpoint, access_token, json_data=None):
        if endpoint.startswith("pages/"):
            return {"properties": {"title": {"type": "title", "title": [{"plain_text": "Title"}]}}}
        if endpoint.startswith("blocks/") and "start_cursor" not in endpoint:
            return {
                "results": [
                    {"type": "child_page", "id": "page-1"},
                    {"type": "child_database", "id": "db-1"},
                ],
                "has_more": True,
                "next_cursor": "next",
            }
        if endpoint.startswith("blocks/") and "start_cursor=next" in endpoint:
            return {"results": [], "has_more": False}
        if endpoint.startswith("databases/"):
            raise RuntimeError("db fail")
        return {}

    monkeypatch.setattr(connector, "_make_request", make_request)
    monkeypatch.setattr(connector, "_extract_text_from_blocks", lambda _blocks: "content")

    docs = list(
        connector._ingest_implementation(
            {"item_ids": ["page-1"], "credentials": {"access_token": "token"}}
        )
    )

    assert len(docs) == 1


def test_ingest_implementation_handles_errors():
    connector = NotionConnector()

    def boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    with patch.object(connector, "_make_request", side_effect=boom):
        docs = list(
            connector._ingest_implementation(
                {"item_ids": ["page-1"], "credentials": {"access_token": "token"}}
            )
        )

    assert docs == []


def test_sync_returns_when_no_root_items(monkeypatch):
    connector = NotionConnector()
    monkeypatch.setattr(connector, "_list_items_implementation", lambda *_args, **_kwargs: [])

    result = connector._sync_implementation("user-1", "int-1")

    assert result["files_processed"] == 0


def test_sync_returns_when_no_documents(monkeypatch):
    connector = NotionConnector()
    monkeypatch.setattr(connector, "_list_items_implementation", lambda *_args, **_kwargs: [ConnectorItem(id="page-1", name="Doc", type="folder")])
    monkeypatch.setattr(connector, "_ingest_implementation", lambda _config: [])

    result = connector._sync_implementation("user-1", "int-1")

    assert result["files_processed"] == 0


def test_sync_skips_large_document(monkeypatch):
    connector = NotionConnector()
    doc = ConnectorDocument(page_content="x" * 10, metadata={"title": "Doc", "page_id": "page-1", "source_url": "url"})

    monkeypatch.setattr(connector, "_list_items_implementation", lambda *_args, **_kwargs: [ConnectorItem(id="page-1", name="Doc", type="folder")])
    monkeypatch.setattr(connector, "_ingest_implementation", lambda _config: [doc])

    supabase = MagicMock()
    table = MagicMock()
    table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "job-1"}])
    supabase.table.return_value = table

    monkeypatch.setattr("core.db.get_supabase", lambda: supabase)
    monkeypatch.setattr("worker.tasks.create_file_status", lambda *args, **kwargs: "status-1")
    monkeypatch.setattr("worker.tasks.update_file_status", lambda *args, **kwargs: None)
    monkeypatch.setattr(settings, "MAX_FILE_SIZE", 1)

    result = connector._sync_implementation("user-1", "int-1")
    assert result["files_processed"] == 0


def test_sync_existing_document_and_batch_insert_failure(monkeypatch):
    connector = NotionConnector()
    doc = ConnectorDocument(page_content="hello", metadata={"title": "Doc", "page_id": "page-1", "source_url": "url"})

    monkeypatch.setattr(connector, "_list_items_implementation", lambda *_args, **_kwargs: [ConnectorItem(id="page-1", name="Doc", type="folder")])
    monkeypatch.setattr(connector, "_ingest_implementation", lambda _config: [doc])

    supabase = MagicMock()

    def make_table(responses):
        table = MagicMock()
        table.select.return_value = table
        table.insert.return_value = table
        table.update.return_value = table
        table.eq.return_value = table
        table.limit.return_value = table
        table.execute.side_effect = [SimpleNamespace(data=resp) for resp in responses]
        return table

    tables = {
        "ingestion_jobs": make_table([[{"id": "job-1"}], [{"id": "job-1"}]]),
        "documents": make_table([[{"id": "doc-1"}], [{"id": "doc-1"}]]),
        "user_integrations": make_table([[{"id": "int-1"}]]),
    }
    supabase.table.side_effect = lambda name: tables.get(name, make_table([[]]))

    monkeypatch.setattr("core.db.get_supabase", lambda: supabase)
    monkeypatch.setattr("services.embeddings.generate_embeddings_batch_sync", lambda chunks: [None, [0.1]])
    monkeypatch.setattr("connectors.notion.insert_rows_with_retry", lambda *_args, **_kwargs: (_ for _ in ()).throw(Exception("db fail")))
    monkeypatch.setattr("connectors.notion.delete_rows_with_retry", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("connectors.notion.compute_content_hash", lambda *_: "hash")
    monkeypatch.setattr("worker.tasks.create_file_status", lambda *args, **kwargs: "status-1")
    monkeypatch.setattr("worker.tasks.update_file_status", lambda *args, **kwargs: None)
    monkeypatch.setattr(settings, "CHUNK_INSERT_BATCH_SIZE", 10)

    result = connector._sync_implementation("user-1", "int-1")
    assert result["status"] == "success"


def test_sync_document_insert_failure(monkeypatch):
    connector = NotionConnector()
    doc = ConnectorDocument(page_content="hello", metadata={"title": "Doc", "page_id": "page-1", "source_url": "url"})

    monkeypatch.setattr(connector, "_list_items_implementation", lambda *_args, **_kwargs: [ConnectorItem(id="page-1", name="Doc", type="folder")])
    monkeypatch.setattr(connector, "_ingest_implementation", lambda _config: [doc])

    supabase = MagicMock()

    def make_table(responses):
        table = MagicMock()
        table.select.return_value = table
        table.insert.return_value = table
        table.update.return_value = table
        table.eq.return_value = table
        table.limit.return_value = table
        table.execute.side_effect = [SimpleNamespace(data=resp) for resp in responses]
        return table

    tables = {
        "ingestion_jobs": make_table([[{"id": "job-1"}], [{"id": "job-1"}]]),
        "documents": make_table([[], None]),
        "user_integrations": make_table([[{"id": "int-1"}]]),
    }
    supabase.table.side_effect = lambda name: tables.get(name, make_table([[]]))

    monkeypatch.setattr("core.db.get_supabase", lambda: supabase)
    monkeypatch.setattr("worker.tasks.create_file_status", lambda *args, **kwargs: "status-1")
    monkeypatch.setattr("worker.tasks.update_file_status", lambda *args, **kwargs: None)

    result = connector._sync_implementation("user-1", "int-1")
    assert result["status"] == "success"


def test_sync_skips_when_no_chunks(monkeypatch):
    connector = NotionConnector()
    doc = ConnectorDocument(page_content="hello", metadata={"title": "Doc", "page_id": "page-1", "source_url": "url"})

    monkeypatch.setattr(connector, "_list_items_implementation", lambda *_args, **_kwargs: [ConnectorItem(id="page-1", name="Doc", type="folder")])
    monkeypatch.setattr(connector, "_ingest_implementation", lambda _config: [doc])

    supabase = MagicMock()

    def make_table(responses):
        table = MagicMock()
        table.select.return_value = table
        table.insert.return_value = table
        table.update.return_value = table
        table.eq.return_value = table
        table.limit.return_value = table
        table.execute.side_effect = [SimpleNamespace(data=resp) for resp in responses]
        return table

    tables = {
        "ingestion_jobs": make_table([[{"id": "job-1"}], [{"id": "job-1"}]]),
        "documents": make_table([[], [{"id": "doc-1"}]]),
        "user_integrations": make_table([[{"id": "int-1"}]]),
    }
    supabase.table.side_effect = lambda name: tables.get(name, make_table([[]]))

    monkeypatch.setattr("core.db.get_supabase", lambda: supabase)
    monkeypatch.setattr("services.embeddings.generate_embeddings_batch_sync", lambda chunks: [[0.1]])
    monkeypatch.setattr("connectors.notion.compute_content_hash", lambda *_: "hash")
    monkeypatch.setattr("worker.tasks.create_file_status", lambda *args, **kwargs: "status-1")
    monkeypatch.setattr("worker.tasks.update_file_status", lambda *args, **kwargs: None)

    class DummySplitter:
        def split_text(self, *_args, **_kwargs):
            return []

    monkeypatch.setitem(
        sys.modules,
        "langchain_text_splitters",
        SimpleNamespace(RecursiveCharacterTextSplitter=lambda *args, **kwargs: DummySplitter()),
    )

    result = connector._sync_implementation("user-1", "int-1")
    assert result["status"] == "success"


def test_sync_processing_exception_records_error(monkeypatch):
    connector = NotionConnector()
    doc = ConnectorDocument(page_content="hello", metadata={"title": "Doc", "page_id": "page-1", "source_url": "url"})

    monkeypatch.setattr(connector, "_list_items_implementation", lambda *_args, **_kwargs: [ConnectorItem(id="page-1", name="Doc", type="folder")])
    monkeypatch.setattr(connector, "_ingest_implementation", lambda _config: [doc])

    supabase = MagicMock()

    def make_table(responses):
        table = MagicMock()
        table.select.return_value = table
        table.insert.return_value = table
        table.update.return_value = table
        table.eq.return_value = table
        table.limit.return_value = table
        table.execute.side_effect = [SimpleNamespace(data=resp) for resp in responses]
        return table

    tables = {
        "ingestion_jobs": make_table([[{"id": "job-1"}], [{"id": "job-1"}]]),
        "documents": make_table([[], [{"id": "doc-1"}]]),
        "user_integrations": make_table([[{"id": "int-1"}]]),
    }
    supabase.table.side_effect = lambda name: tables.get(name, make_table([[]]))

    monkeypatch.setattr("core.db.get_supabase", lambda: supabase)
    monkeypatch.setattr("services.embeddings.generate_embeddings_batch_sync", lambda _chunks: (_ for _ in ()).throw(Exception("boom")))
    monkeypatch.setattr("connectors.notion.compute_content_hash", lambda *_: "hash")
    monkeypatch.setattr("worker.tasks.create_file_status", lambda *args, **kwargs: "status-1")
    monkeypatch.setattr("worker.tasks.update_file_status", lambda *args, **kwargs: None)

    result = connector._sync_implementation("user-1", "int-1")
    assert result["errors"]


def test_sync_http_error_401_raises(monkeypatch):
    connector = NotionConnector()
    response = MagicMock()
    response.status_code = 401
    error = requests.exceptions.HTTPError(response=response)

    monkeypatch.setattr(connector, "_list_items_implementation", lambda *_args, **_kwargs: (_ for _ in ()).throw(error))

    with pytest.raises(Exception, match="Integration requires reconnection"):
        connector._sync_implementation("user-1", "int-1")


def test_sync_http_error_non_401_raises(monkeypatch):
    connector = NotionConnector()
    response = MagicMock()
    response.status_code = 400
    error = requests.exceptions.HTTPError(response=response)

    monkeypatch.setattr(connector, "_list_items_implementation", lambda *_args, **_kwargs: (_ for _ in ()).throw(error))

    with pytest.raises(requests.exceptions.HTTPError):
        connector._sync_implementation("user-1", "int-1")


def test_sync_batch_insert_failure_marks_failed(monkeypatch):
    connector = NotionConnector()
    doc = ConnectorDocument(page_content="hello", metadata={"title": "Doc", "page_id": "page-1", "source_url": "url"})

    monkeypatch.setattr(connector, "_list_items_implementation", lambda *_args, **_kwargs: [ConnectorItem(id="page-1", name="Doc", type="folder")])
    monkeypatch.setattr(connector, "_ingest_implementation", lambda _config: [doc])

    supabase = MagicMock()

    def make_table(responses):
        table = MagicMock()
        table.select.return_value = table
        table.insert.return_value = table
        table.update.return_value = table
        table.eq.return_value = table
        table.limit.return_value = table
        table.execute.side_effect = [SimpleNamespace(data=resp) for resp in responses]
        return table

    tables = {
        "ingestion_jobs": make_table([[{"id": "job-1"}], [{"id": "job-1"}]]),
        "documents": make_table([[{"id": "doc-1"}], [{"id": "doc-1"}]]),
        "user_integrations": make_table([[{"id": "int-1"}]]),
    }
    supabase.table.side_effect = lambda name: tables.get(name, make_table([[]]))

    monkeypatch.setattr("core.db.get_supabase", lambda: supabase)
    monkeypatch.setattr("services.embeddings.generate_embeddings_batch_sync", lambda chunks: [[0.1] for _ in chunks])
    monkeypatch.setattr("connectors.notion.insert_rows_with_retry", lambda *_args, **_kwargs: (_ for _ in ()).throw(Exception("db fail")))
    monkeypatch.setattr("connectors.notion.delete_rows_with_retry", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("connectors.notion.compute_content_hash", lambda *_: "hash")
    monkeypatch.setattr("worker.tasks.create_file_status", lambda *args, **kwargs: "status-1")
    update_mock = MagicMock()
    monkeypatch.setattr("worker.tasks.update_file_status", update_mock)
    monkeypatch.setattr(settings, "CHUNK_INSERT_BATCH_SIZE", 10)

    connector._sync_implementation("user-1", "int-1")

    assert update_mock.called


def test_sync_exception_updates_job(monkeypatch):
    connector = NotionConnector()
    doc = ConnectorDocument(page_content="hello", metadata={"title": "Doc", "page_id": "page-1", "source_url": "url"})

    monkeypatch.setattr(connector, "_list_items_implementation", lambda *_args, **_kwargs: [ConnectorItem(id="page-1", name="Doc", type="folder")])
    monkeypatch.setattr(connector, "_ingest_implementation", lambda _config: (_ for _ in ()).throw(Exception("boom")))

    supabase = MagicMock()

    def make_table(responses):
        table = MagicMock()
        table.select.return_value = table
        table.insert.return_value = table
        table.update.return_value = table
        table.eq.return_value = table
        table.limit.return_value = table
        table.execute.side_effect = [SimpleNamespace(data=resp) for resp in responses]
        return table

    ingestion_jobs = make_table([[{"id": "job-1"}], [{"id": "job-1"}]])
    user_integrations = make_table([[{"id": "int-1"}]])
    documents = make_table([[]])

    def table_side_effect(name):
        if name == "ingestion_jobs":
            return ingestion_jobs
        if name == "user_integrations":
            return user_integrations
        if name == "documents":
            return documents
        return make_table([[]])

    supabase.table.side_effect = table_side_effect

    monkeypatch.setattr("core.db.get_supabase", lambda: supabase)

    with pytest.raises(Exception):
        connector._sync_implementation("user-1", "int-1")


def test_sync_global_exception_marks_job_failed(monkeypatch):
    connector = NotionConnector()
    doc = ConnectorDocument(page_content="hello", metadata={"title": "Doc", "page_id": "page-1", "source_url": "url"})

    monkeypatch.setattr(connector, "_list_items_implementation", lambda *_args, **_kwargs: [ConnectorItem(id="page-1", name="Doc", type="folder")])
    monkeypatch.setattr(connector, "_ingest_implementation", lambda _config: [doc])

    supabase = MagicMock()

    def make_table(responses):
        table = MagicMock()
        table.select.return_value = table
        table.insert.return_value = table
        table.update.return_value = table
        table.eq.return_value = table
        table.limit.return_value = table
        table.execute.side_effect = [SimpleNamespace(data=resp) for resp in responses]
        return table

    ingestion_jobs = make_table([[{"id": "job-1"}], [{"id": "job-1"}]])
    user_integrations = make_table([[{"id": "int-1"}]])
    user_integrations.update.return_value.eq.return_value.execute.side_effect = Exception("boom")
    documents = make_table([[], [{"id": "doc-1"}]])

    def table_side_effect(name):
        if name == "ingestion_jobs":
            return ingestion_jobs
        if name == "user_integrations":
            return user_integrations
        if name == "documents":
            return documents
        return make_table([[]])

    supabase.table.side_effect = table_side_effect

    monkeypatch.setattr("core.db.get_supabase", lambda: supabase)
    monkeypatch.setattr("services.embeddings.generate_embeddings_batch_sync", lambda chunks: [[0.1] * 3 for _ in chunks])
    monkeypatch.setattr("connectors.notion.insert_rows_with_retry", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("connectors.notion.compute_content_hash", lambda *_: "hash")
    monkeypatch.setattr("worker.tasks.create_file_status", lambda *args, **kwargs: "status-1")
    monkeypatch.setattr("worker.tasks.update_file_status", lambda *args, **kwargs: None)

    with pytest.raises(Exception):
        connector._sync_implementation("user-1", "int-1")

    assert ingestion_jobs.update.called
