import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from connectors.enhanced import AuthenticationError, SourceDocument, SourceType
from connectors.notion import NotionConnector
from services.oauth_token_manager import TokenRefreshError


def _make_table(data=None):
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.execute.return_value = MagicMock(data=data)
    return table


def test_get_connector_definition_id_success():
    connector = NotionConnector()
    supabase = MagicMock()
    supabase.table.return_value = _make_table({"id": "def-1"})

    with patch("connectors.notion.get_supabase", return_value=supabase):
        assert connector._get_connector_definition_id() == "def-1"


def test_get_connector_definition_id_missing():
    connector = NotionConnector()
    supabase = MagicMock()
    supabase.table.return_value = _make_table(None)

    with patch("connectors.notion.get_supabase", return_value=supabase):
        with pytest.raises(ValueError):
            connector._get_connector_definition_id()


def test_authorize_implementation_true_false():
    connector = NotionConnector()
    supabase = MagicMock()
    table = _make_table([{"id": "int-1"}])
    supabase.table.return_value = table

    with patch("connectors.notion.get_supabase", return_value=supabase), \
         patch.object(connector, "_get_connector_definition_id", return_value="def-1"):
        assert connector._authorize_implementation("user-1") is True

    table.execute.return_value = MagicMock(data=[])
    with patch("connectors.notion.get_supabase", return_value=supabase), \
         patch.object(connector, "_get_connector_definition_id", return_value="def-1"):
        assert connector._authorize_implementation("user-1") is False


def test_get_access_token_missing_integration():
    connector = NotionConnector()
    supabase = MagicMock()
    supabase.table.return_value = _make_table([])

    with patch("connectors.notion.get_supabase", return_value=supabase), \
         patch.object(connector, "_get_connector_definition_id", return_value="def-1"):
        with pytest.raises(ValueError):
            connector._get_access_token("user-1")


def test_get_access_token_refresh_error():
    connector = NotionConnector()
    supabase = MagicMock()
    supabase.table.return_value = _make_table([{"id": "int-1"}])

    with patch("connectors.notion.get_supabase", return_value=supabase), \
         patch.object(connector, "_get_connector_definition_id", return_value="def-1"), \
         patch("connectors.notion.OAuthTokenManager.get_valid_credentials", side_effect=TokenRefreshError("boom")):
        with pytest.raises(ValueError):
            connector._get_access_token("user-1")


def test_get_access_token_success():
    connector = NotionConnector()
    supabase = MagicMock()
    supabase.table.return_value = _make_table([{"id": "int-1"}])

    with patch("connectors.notion.get_supabase", return_value=supabase), \
         patch.object(connector, "_get_connector_definition_id", return_value="def-1"), \
         patch(
             "connectors.notion.OAuthTokenManager.get_valid_credentials",
             return_value={"access_token": "token"},
         ):
        assert connector._get_access_token("user-1") == "token"


def test_get_headers_contains_auth_and_version():
    connector = NotionConnector()
    headers = connector._get_headers("token")
    assert headers["Authorization"] == "Bearer token"
    assert headers["Notion-Version"] == connector.NOTION_API_VERSION


def test_make_request_rate_limit_counts(monkeypatch):
    connector = NotionConnector()
    counter = MagicMock()
    metrics_module = SimpleNamespace(retry_total=MagicMock())
    metrics_module.retry_total.labels.return_value = counter
    monkeypatch.setitem(sys.modules, "core.metrics", metrics_module)

    response = MagicMock()
    response.status_code = 429
    response.json.return_value = {"ok": True}
    response.raise_for_status.return_value = None

    with patch("connectors.notion.requests.request", return_value=response):
        result = connector._make_request("GET", "search", "token")

    assert result == {"ok": True}
    assert counter.inc.called


def test_make_request_rate_limit_metrics_failure(monkeypatch):
    connector = NotionConnector()
    monkeypatch.setitem(sys.modules, "core.metrics", SimpleNamespace())

    response = MagicMock()
    response.status_code = 429
    response.json.return_value = {"ok": True}
    response.raise_for_status.return_value = None

    with patch("connectors.notion.requests.request", return_value=response):
        assert connector._make_request("GET", "search", "token") == {"ok": True}


def test_list_items_parent_returns_children():
    connector = NotionConnector()
    blocks_result = {
        "results": [
            {"id": "page-1", "type": "child_page", "child_page": {"title": "Page A"}},
            {"id": "db-1", "type": "child_database", "child_database": {"title": "DB A"}},
        ],
        "has_more": False,
    }

    with patch.object(connector, "_get_access_token", return_value="token"), \
         patch.object(connector, "_make_request", return_value=blocks_result):
        items = connector._list_items_implementation("user-1", parent_id="parent-1")

    assert len(items) == 2
    assert items[0].parent_id == "parent-1"


def test_list_items_parent_error_returns_empty():
    connector = NotionConnector()
    with patch.object(connector, "_get_access_token", return_value="token"), \
         patch.object(connector, "_make_request", side_effect=Exception("boom")):
        items = connector._list_items_implementation("user-1", parent_id="parent-1")

    assert items == []


def test_list_items_root_includes_pages_and_databases():
    connector = NotionConnector()
    pages_result = {
        "results": [
            {
                "id": "page-1",
                "parent": {"type": "workspace"},
                "properties": {
                    "title": {"type": "title", "title": [{"plain_text": "Page One"}]},
                },
                "icon": {"type": "emoji", "emoji": "E"},
            },
            {
                "id": "page-2",
                "parent": {"type": "page"},
                "properties": {
                    "title": {"type": "title", "title": [{"plain_text": "Skip"}]},
                },
            },
        ]
    }
    db_result = {
        "results": [
            {
                "id": "db-1",
                "parent": {"type": "workspace"},
                "title": [{"plain_text": "DB One"}],
                "icon": {"type": "emoji", "emoji": "D"},
            },
            {
                "id": "db-2",
                "parent": {"type": "page"},
                "title": [{"plain_text": "Skip DB"}],
            }
        ]
    }

    with patch.object(connector, "_get_access_token", return_value="token"), \
         patch.object(connector, "_make_request", side_effect=[pages_result, db_result]):
        items = connector._list_items_implementation("user-1", parent_id=None)

    names = [item.name for item in items]
    assert "Page One" in names
    assert "DB One" in names
    assert "Skip" not in names


def test_extract_text_from_blocks_formats():
    connector = NotionConnector()
    blocks = [
        {"type": "heading_1", "heading_1": {"rich_text": [{"plain_text": "Title"}]}},
        {"type": "heading_2", "heading_2": {"rich_text": [{"plain_text": "Subtitle"}]}},
        {"type": "heading_3", "heading_3": {"rich_text": [{"plain_text": "Section"}]}},
        {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Para"}]}},
        {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"plain_text": "Item"}]}},
        {"type": "quote", "quote": {"rich_text": [{"plain_text": "Quote"}]}},
        {"type": "code", "code": {"rich_text": [{"plain_text": "print(1)"}], "language": "python"}},
        {"type": "divider"},
    ]

    text = connector._extract_text_from_blocks(blocks)
    assert "# Title" in text
    assert "## Subtitle" in text
    assert "### Section" in text
    assert "Para" in text
    assert "\u2022 Item" in text
    assert "> Quote" in text
    assert "```python" in text
    assert "---" in text


@pytest.mark.asyncio
async def test_fetch_documents_async_wrapper():
    connector = NotionConnector()
    doc = SourceDocument(
        content="Hello",
        metadata={"title": "Doc"},
        source_type=SourceType.NOTION,
        source_id="page-1",
        filename="Doc.md",
        mime_type="text/markdown",
        size_bytes=5,
    )

    with patch.object(connector, "fetch_documents_sync", return_value=iter([doc])):
        docs = []
        async for item in connector.fetch_documents(["page-1"], user_id="user-1"):
            docs.append(item)

    assert docs == [doc]


def test_fetch_documents_sync_empty_item_ids_returns_empty():
    connector = NotionConnector()
    assert list(connector.fetch_documents_sync([])) == []


def test_fetch_documents_sync_integration_not_found():
    connector = NotionConnector()
    supabase = MagicMock()
    supabase.table.return_value = _make_table(None)

    with patch("connectors.notion.get_supabase", return_value=supabase):
        with pytest.raises(AuthenticationError):
            list(
                connector.fetch_documents_sync(
                    ["page-1"],
                    credentials={"integration_id": "int-1"},
                )
            )


def test_fetch_documents_sync_recurses_child_pages_and_databases():
    connector = NotionConnector()

    def fake_request(method, endpoint, access_token, json_data=None):
        if endpoint.startswith("pages/"):
            page_id = endpoint.split("/")[1]
            return {
                "properties": {
                    "title": {"type": "title", "title": [{"plain_text": f"Title {page_id}"}]},
                },
                "url": f"https://notion.so/{page_id}",
                "parent": {"page_id": "parent-1"},
            }
        if endpoint.startswith("blocks/root/children?start_cursor=cursor-1"):
            return {"results": [], "has_more": False}
        if endpoint.startswith("blocks/root/children"):
            return {
                "results": [
                    {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Root"}]}},
                    {"id": "child-1", "type": "child_page", "child_page": {"title": "Child"}},
                    {"id": "db-1", "type": "child_database", "child_database": {"title": "DB"}},
                ],
                "has_more": True,
                "next_cursor": "cursor-1",
            }
        if endpoint.startswith("blocks/child-1/children"):
            return {
                "results": [
                    {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Child"}]}},
                ],
                "has_more": False,
            }
        if endpoint.startswith("blocks/db-page-1/children"):
            return {
                "results": [
                    {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "DB"}]}},
                ],
                "has_more": False,
            }
        if endpoint.startswith("databases/"):
            return {"results": [{"id": "db-page-1"}]}
        return {"results": [], "has_more": False}

    with patch.object(connector, "_get_access_token", return_value="token"), \
         patch.object(connector, "_make_request", side_effect=fake_request):
        docs = list(connector.fetch_documents_sync(["root"], user_id="user-1"))

    assert len(docs) == 3
    titles = [doc.metadata["title"] for doc in docs]
    assert "Title root" in titles
    assert "Title child-1" in titles
    assert "Title db-page-1" in titles


def test_fetch_documents_sync_handles_database_query_error():
    connector = NotionConnector()

    def fake_request(method, endpoint, access_token, json_data=None):
        if endpoint.startswith("pages/"):
            return {
                "properties": {
                    "title": {"type": "title", "title": [{"plain_text": "Root"}]},
                },
                "url": "https://notion.so/root",
            }
        if endpoint.startswith("blocks/root/children"):
            return {
                "results": [
                    {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Root"}]}},
                    {"id": "db-1", "type": "child_database", "child_database": {"title": "DB"}},
                ],
                "has_more": False,
            }
        if endpoint.startswith("databases/"):
            raise RuntimeError("boom")
        return {"results": [], "has_more": False}

    with patch.object(connector, "_get_access_token", return_value="token"), \
         patch.object(connector, "_make_request", side_effect=fake_request):
        docs = list(connector.fetch_documents_sync(["root"], user_id="user-1"))

    assert len(docs) == 1


def test_fetch_documents_sync_skips_duplicate_pages():
    connector = NotionConnector()

    def fake_request(method, endpoint, access_token, json_data=None):
        if endpoint.startswith("pages/"):
            return {
                "properties": {
                    "title": {"type": "title", "title": [{"plain_text": "Root"}]},
                },
                "url": "https://notion.so/root",
            }
        if endpoint.startswith("blocks/root/children"):
            return {
                "results": [
                    {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Root"}]}},
                ],
                "has_more": False,
            }
        return {"results": [], "has_more": False}

    with patch.object(connector, "_get_access_token", return_value="token"), \
         patch.object(connector, "_make_request", side_effect=fake_request):
        docs = list(connector.fetch_documents_sync(["root", "root"], user_id="user-1"))

    assert len(docs) == 1


def test_fetch_documents_sync_handles_page_fetch_error():
    connector = NotionConnector()

    def fake_request(method, endpoint, access_token, json_data=None):
        if endpoint.startswith("pages/"):
            raise RuntimeError("boom")
        return {"results": [], "has_more": False}

    with patch.object(connector, "_get_access_token", return_value="token"), \
         patch.object(connector, "_make_request", side_effect=fake_request):
        docs = list(connector.fetch_documents_sync(["root"], user_id="user-1"))

    assert docs == []


def test_connector_type_notion():
    connector = NotionConnector()
    assert connector.connector_type == SourceType.NOTION


@pytest.mark.asyncio
async def test_authorize_async_wrapper():
    connector = NotionConnector()

    with patch("connectors.notion.run_in_threadpool", side_effect=lambda fn, *args: fn(*args)), \
         patch.object(connector, "_authorize_implementation", return_value=True):
        assert await connector.authorize("user-1") is True


@pytest.mark.asyncio
async def test_list_items_async_wrapper():
    connector = NotionConnector()

    with patch("connectors.notion.run_in_threadpool", side_effect=lambda fn, *args: fn(*args)), \
         patch.object(connector, "_list_items_implementation", return_value=["ok"]):
        items = await connector.list_items("user-1", parent_id="root")

    assert items == ["ok"]


def test_list_items_root_string_maps_to_none():
    connector = NotionConnector()
    pages_result = {"results": []}
    db_result = {"results": []}

    with patch.object(connector, "_get_access_token", return_value="token"), \
         patch.object(connector, "_make_request", side_effect=[pages_result, db_result]) as make_request:
        connector._list_items_implementation("user-1", parent_id="root")

    assert make_request.call_count == 2


def test_fetch_documents_sync_requires_credentials_or_user():
    connector = NotionConnector()
    with pytest.raises(AuthenticationError):
        list(connector.fetch_documents_sync(["page-1"]))


def test_fetch_documents_sync_integration_id_success():
    connector = NotionConnector()
    supabase = MagicMock()
    supabase.table.return_value = _make_table({"id": "int-1"})

    def fake_request(method, endpoint, access_token, json_data=None):
        if endpoint.startswith("pages/"):
            return {
                "properties": {
                    "title": {"type": "title", "title": [{"plain_text": "Page One"}]},
                },
                "url": "https://notion.so/page-1",
                "parent": {"page_id": "parent-1"},
            }
        if endpoint.startswith("blocks/") and endpoint.endswith("/children"):
            return {
                "results": [
                    {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Hello"}]}},
                ],
                "has_more": False,
            }
        return {}

    with patch("connectors.notion.get_supabase", return_value=supabase), \
         patch("connectors.notion.OAuthTokenManager.get_valid_credentials", return_value={"access_token": "token"}), \
         patch.object(connector, "_make_request", side_effect=fake_request):
        docs = list(connector.fetch_documents_sync(
            ["page-1"],
            credentials={"integration_id": "int-1"},
            user_id="user-1",
        ))

    assert len(docs) == 1
    assert isinstance(docs[0], SourceDocument)
    assert docs[0].filename == "Page One.md"
    assert docs[0].parent_id == "parent-1"


def test_fetch_documents_sync_skips_empty_content():
    connector = NotionConnector()

    def fake_request(method, endpoint, access_token, json_data=None):
        if endpoint.startswith("pages/"):
            return {
                "properties": {
                    "title": {"type": "title", "title": [{"plain_text": "Empty Page"}]},
                },
                "url": "https://notion.so/page-2",
            }
        if endpoint.startswith("blocks/") and endpoint.endswith("/children"):
            return {"results": [], "has_more": False}
        return {}

    with patch.object(connector, "_get_access_token", return_value="token"), \
         patch.object(connector, "_make_request", side_effect=fake_request):
        docs = list(connector.fetch_documents_sync(["page-2"], user_id="user-1"))

    assert docs == []
