import pytest
from unittest.mock import AsyncMock, patch

from connectors.web_enhanced import WebConnectorEnhanced
from connectors.enhanced import SourceDocument, SourceType
from connectors.base import ConnectorDocument


@pytest.mark.asyncio
async def test_fetch_documents_maps_source_document():
    connector = WebConnectorEnhanced()

    def fake_ingest(_config):
        async def fake_iter():
            yield ConnectorDocument(
                page_content="hello",
                metadata={"source_url": "https://example.com", "title": "Example"},
            )
        return fake_iter()

    with patch.object(connector.legacy, "ingest", new=fake_ingest):
        docs = []
        async for doc in connector.fetch_documents(
            ["https://example.com"], user_id="user-1", respect_robots=False
        ):
            docs.append(doc)

    assert isinstance(docs[0], SourceDocument)
    assert docs[0].source_type == SourceType.WEB
    assert docs[0].source_id == "https://example.com"
    assert docs[0].filename.endswith(".html")


@pytest.mark.asyncio
async def test_authorize_and_list_items():
    connector = WebConnectorEnhanced()
    assert await connector.authorize("user-1") is True
    assert await connector.list_items("user-1") == []


@pytest.mark.asyncio
async def test_ingest_delegates():
    connector = WebConnectorEnhanced()
    def fake_ingest(_config):
        async def fake_iter():
            if False:
                yield None
        return fake_iter()

    with patch.object(connector.legacy, "ingest", new=fake_ingest):
        result = await connector.ingest({"item_ids": []})
    assert result is not None


def test_validate_credentials_always_true():
    connector = WebConnectorEnhanced()
    assert connector.validate_credentials({}) is True


def test_connector_type_property():
    connector = WebConnectorEnhanced()
    assert connector.connector_type == SourceType.WEB
