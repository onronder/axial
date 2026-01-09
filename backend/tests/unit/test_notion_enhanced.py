import pytest
from unittest.mock import AsyncMock, patch

from connectors.notion_enhanced import NotionConnectorEnhanced
from connectors.enhanced import SourceDocument, SourceType
from connectors.base import ConnectorDocument


@pytest.mark.asyncio
async def test_fetch_documents_maps_source_document():
    connector = NotionConnectorEnhanced()

    async def fake_iter():
        yield ConnectorDocument(
            page_content="hello",
            metadata={"page_id": "page-1", "title": "Title", "parent_id": "parent-1"},
        )

    with patch.object(connector.legacy, "ingest", new=AsyncMock(return_value=fake_iter())):
        docs = []
        async for doc in connector.fetch_documents(["page-1"], credentials={"integration_id": "int-1"}, user_id="user-1"):
            docs.append(doc)

    assert isinstance(docs[0], SourceDocument)
    assert docs[0].source_type == SourceType.NOTION
    assert docs[0].source_id == "page-1"
    assert docs[0].filename == "Title"


@pytest.mark.asyncio
async def test_authorize_delegates():
    connector = NotionConnectorEnhanced()
    with patch.object(connector.legacy, "authorize", new=AsyncMock(return_value=True)):
        assert await connector.authorize("user-1") is True


@pytest.mark.asyncio
async def test_list_items_delegates():
    connector = NotionConnectorEnhanced()
    with patch.object(connector.legacy, "list_items", new=AsyncMock(return_value=[])):
        assert await connector.list_items("user-1") == []


@pytest.mark.asyncio
async def test_sync_delegates():
    connector = NotionConnectorEnhanced()
    with patch.object(connector.legacy, "sync", new=AsyncMock(return_value={"status": "ok"})):
        result = await connector.sync("user-1", "int-1")
    assert result["status"] == "ok"


def test_validate_credentials():
    connector = NotionConnectorEnhanced()
    assert connector.validate_credentials({"integration_id": "int-1"}) is True
    assert connector.validate_credentials({"access_token": "token"}) is True
    assert connector.validate_credentials({}) is False
