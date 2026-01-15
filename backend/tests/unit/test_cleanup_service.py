import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock

from services.cleanup import AccountCleanupService, ActiveIngestionError


@pytest.mark.asyncio
async def test_execute_org_deletion_blocks_active_ingestion():
    supabase = MagicMock()
    supabase.rpc.side_effect = Exception("active_ingestion_jobs")

    service = AccountCleanupService(supabase=supabase)
    with pytest.raises(ActiveIngestionError):
        await service.execute_org_deletion("org-1")


@pytest.mark.asyncio
async def test_execute_org_deletion_returns_counts():
    supabase = MagicMock()
    # The code calls supabase.rpc(...).execute(), so we need to mock the chain
    mock_response = SimpleNamespace(
        data={
            "deleted_chunks": 3,
            "deleted_documents": 2,
            "deleted_scopes": 1,
            "deleted_jobs": 4,
        }
    )
    supabase.rpc.return_value.execute.return_value = mock_response

    service = AccountCleanupService(supabase=supabase)
    result = await service.execute_org_deletion("org-1")

    assert result["vector_store"]["deleted"] == 3
    assert result["documents"]["deleted"] == 2
    assert result["scope_identities"]["deleted"] == 1
    assert result["ingestion_jobs"]["deleted"] == 4
    assert result["org_usage"]["status"] == "success"
