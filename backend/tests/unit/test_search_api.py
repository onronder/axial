from unittest.mock import MagicMock, Mock, patch, AsyncMock

import pytest
from fastapi import HTTPException

from api.v1.search import SearchRequest, search_documents


@pytest.fixture(autouse=True)
def mock_org_id():
    with patch(
        "api.v1.search.team_service.get_organization_id",
        new_callable=AsyncMock,
        return_value="org-1",
    ):
        yield


class TestSearchDocuments:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_documents_success(self):
        supabase = MagicMock()
        supabase.rpc.return_value.execute.return_value = Mock(data=[{"id": "doc-1"}])

        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.return_value = [0.1, 0.2]

        with patch("api.v1.search.get_supabase", return_value=supabase), \
             patch("api.v1.search.OpenAIEmbeddings", return_value=mock_embeddings):
            result = await search_documents(
                SearchRequest(query="hello", limit=5, threshold=0.2),
                user_id="user-1",
            )

        assert result.results == [{"id": "doc-1"}]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_documents_embedding_failure(self):
        supabase = MagicMock()
        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.side_effect = Exception("embed failed")

        with patch("api.v1.search.get_supabase", return_value=supabase), \
             patch("api.v1.search.OpenAIEmbeddings", return_value=mock_embeddings):
            with pytest.raises(HTTPException) as excinfo:
                await search_documents(
                    SearchRequest(query="hello"),
                    user_id="user-1",
                )

        assert excinfo.value.status_code == 500

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_documents_rpc_failure(self):
        supabase = MagicMock()
        supabase.rpc.side_effect = Exception("rpc failed")
        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.return_value = [0.1, 0.2]

        with patch("api.v1.search.get_supabase", return_value=supabase), \
             patch("api.v1.search.OpenAIEmbeddings", return_value=mock_embeddings):
            with pytest.raises(HTTPException) as excinfo:
                await search_documents(
                    SearchRequest(query="hello"),
                    user_id="user-1",
                )

        assert excinfo.value.status_code == 500
