import pytest

from connectors.enhanced import EnhancedConnector, SourceDocument, SourceType
from connectors.base import ConnectorDocument


class DummyConnector(EnhancedConnector):
    @property
    def connector_type(self) -> SourceType:
        return SourceType.FILE_UPLOAD

    def ingest(self, config):
        async def _iter():
            yield ConnectorDocument(page_content="hello", metadata={"title": "Doc"})
        return _iter()

    async def authorize(self, user_id: str) -> bool:
        return True

    async def list_items(self, user_id: str, parent_id=None):
        return []


@pytest.mark.asyncio
async def test_fetch_documents_falls_back_to_ingest():
    connector = DummyConnector()
    docs = []
    async for doc in connector.fetch_documents(["item-1"], user_id="user-1"):
        docs.append(doc)
    assert docs[0].source_type == SourceType.FILE_UPLOAD
    assert docs[0].filename == "Doc"


def test_source_document_to_connector_document():
    src = SourceDocument(
        content=b"hello",
        metadata={"source_id": "id"},
        source_type=SourceType.WEB,
        source_id="id",
        filename="file.txt",
        mime_type="text/plain",
        size_bytes=5,
    )
    doc = src.to_connector_document()
    assert doc.page_content == "hello"


def test_connector_type_not_implemented():
    class MissingConnector(EnhancedConnector):
        def ingest(self, config):
            async def _iter():
                if False:
                    yield None
            return _iter()

        async def authorize(self, user_id: str) -> bool:
            return True

        async def list_items(self, user_id: str, parent_id=None):
            return []

    with pytest.raises(NotImplementedError):
        _ = MissingConnector().connector_type
