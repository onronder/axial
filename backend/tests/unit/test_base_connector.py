import pytest

from connectors.base import BaseConnector


class BaseConnectorHarness(BaseConnector):
    async def authorize(self, user_id: str) -> bool:
        return await super().authorize(user_id)

    async def list_items(self, user_id: str, parent_id=None):
        return await super().list_items(user_id, parent_id)


@pytest.mark.asyncio
async def test_base_connector_authorize_pass_through():
    connector = BaseConnectorHarness()
    assert await connector.authorize("user-1") is None


@pytest.mark.asyncio
async def test_base_connector_list_items_pass_through():
    connector = BaseConnectorHarness()
    assert await connector.list_items("user-1") is None
