import pytest

from connectors.enhanced import EnhancedConnector, SourceDocument, SourceType


class DummyConnector(EnhancedConnector):
    @property
    def connector_type(self) -> SourceType:
        return SourceType.FILE_UPLOAD

    def fetch_documents_sync(self, item_ids, credentials=None, **kwargs):
        yield SourceDocument(
            content=b"hello",
            metadata={"title": "Doc"},
            source_type=SourceType.FILE_UPLOAD,
            source_id="item-1",
            filename="Doc.txt",
            mime_type="text/plain",
            size_bytes=5,
        )

    async def fetch_documents(self, item_ids, credentials=None, **kwargs):
        for doc in self.fetch_documents_sync(item_ids, credentials, **kwargs):
            yield doc

    async def authorize(self, user_id: str) -> bool:
        return True

    async def list_items(self, user_id: str, parent_id=None):
        return []


@pytest.mark.asyncio
async def test_fetch_documents_returns_source_document():
    connector = DummyConnector()
    docs = []
    async for doc in connector.fetch_documents(["item-1"], user_id="user-1"):
        docs.append(doc)
    assert docs[0].source_type == SourceType.FILE_UPLOAD
    assert docs[0].filename == "Doc.txt"


def test_fetch_documents_sync_returns_source_document():
    connector = DummyConnector()
    docs = list(connector.fetch_documents_sync(["item-1"], user_id="user-1"))
    assert docs[0].source_id == "item-1"


def test_connector_type_not_implemented():
    class MissingConnector(EnhancedConnector):
        async def authorize(self, user_id: str) -> bool:
            return True

        async def list_items(self, user_id: str, parent_id=None):
            return []

        async def fetch_documents(self, item_ids, credentials=None, **kwargs):
            return
            yield

        def fetch_documents_sync(self, item_ids, credentials=None, **kwargs):
            return iter(())

    with pytest.raises(NotImplementedError):
        _ = MissingConnector().connector_type


@pytest.mark.asyncio
async def test_fetch_documents_not_implemented_raises():
    class MissingFetchConnector(EnhancedConnector):
        @property
        def connector_type(self) -> SourceType:
            return SourceType.FILE_UPLOAD

        async def authorize(self, user_id: str) -> bool:
            return True

        async def list_items(self, user_id: str, parent_id=None):
            return []

        async def fetch_documents(self, item_ids, credentials=None, **kwargs):
            return await super().fetch_documents(item_ids, credentials, **kwargs)

        def fetch_documents_sync(self, item_ids, credentials=None, **kwargs):
            return super().fetch_documents_sync(item_ids, credentials, **kwargs)

    connector = MissingFetchConnector()
    with pytest.raises(NotImplementedError):
        await connector.fetch_documents(["item-1"])

    with pytest.raises(NotImplementedError):
        list(connector.fetch_documents_sync(["item-1"]))


def test_supports_flags_default_false():
    connector = DummyConnector()
    assert connector.supports_batch_fetch is False
    assert connector.supports_incremental_sync is False
