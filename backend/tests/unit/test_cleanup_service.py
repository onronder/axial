from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from services.cleanup import AccountCleanupService, ActiveIngestionError


@pytest.mark.asyncio
async def test_execute_org_deletion_blocks_active_ingestion():
    supabase = MagicMock()
    supabase.rpc.side_effect = Exception("active_ingestion_jobs")

    service = AccountCleanupService(supabase=supabase)
    with pytest.raises(ActiveIngestionError):
        await service.execute_org_deletion("org-1", owner_id="user-1")


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
    result = await service.execute_org_deletion("org-1", owner_id="user-1")

    assert result["vector_store"]["deleted"] == 3
    assert result["documents"]["deleted"] == 2
    assert result["scope_identities"]["deleted"] == 1
    assert result["ingestion_jobs"]["deleted"] == 4
    assert result["org_usage"]["status"] == "success"


@pytest.mark.asyncio
async def test_delete_single_document_skips_storage_for_identity():
    supabase = MagicMock()
    documents_table = MagicMock()
    documents_table.select.return_value = documents_table
    documents_table.eq.return_value = documents_table
    documents_table.single.return_value = documents_table
    documents_table.delete.return_value = documents_table
    documents_table.execute.side_effect = [
        SimpleNamespace(data={"id": "doc-1", "source_type": "identity", "metadata": {}}),
        SimpleNamespace(data=[]),
    ]

    chunks_table = MagicMock()
    chunks_table.delete.return_value = chunks_table
    chunks_table.eq.return_value = chunks_table
    chunks_table.execute.return_value = SimpleNamespace(data=[])

    supabase.table.side_effect = lambda name: {
        "documents": documents_table,
        "document_chunks": chunks_table,
    }[name]
    supabase.storage = MagicMock()

    service = AccountCleanupService(supabase=supabase)
    result = await service.delete_single_document("doc-1", user_id="user-1", organization_id="org-1")

    assert result["status"] == "success"
    supabase.storage.from_.assert_not_called()
