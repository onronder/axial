from unittest.mock import AsyncMock, MagicMock, Mock, patch

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

def _make_mock_request(method="GET", path="/api/v1"):
    """Create a mock Starlette Request for testing endpoints with rate limiters."""
    from starlette.requests import Request
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": [],
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 12345),
        "app": None,
    }
    return Request(scope=scope)



class TestSearchDocuments:
    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("detected_language", "expected_regconfig"),
        [("tr", "turkish"), (None, "simple")],
    )
    async def test_search_documents_passes_language_aware_regconfig(
        self,
        detected_language,
        expected_regconfig,
    ):
        captured_params = {}
        supabase = MagicMock()

        def fake_rpc(name, params):
            captured_params["name"] = name
            captured_params["params"] = params
            rpc_result = MagicMock()
            rpc_result.execute.return_value = Mock(data=[{"id": "doc-1"}])
            return rpc_result

        supabase.rpc.side_effect = fake_rpc

        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.return_value = [0.1, 0.2]

        with patch("api.v1.search.get_supabase", return_value=supabase), \
             patch("services.embeddings.get_embeddings_model", return_value=mock_embeddings), \
             patch("api.v1.search.language_detector.detect", return_value=detected_language), \
             patch(
                 "api.v1.search.compliance_switch.filter_tombstoned_docs",
                 new=AsyncMock(return_value=[{"id": "doc-1"}]),
             ):
            result = await search_documents(
                request=_make_mock_request(),
                payload=SearchRequest(query="hello", limit=5, threshold=0.2),
                user_id="user-1",
            )

        assert result.results == [{"id": "doc-1"}]
        assert captured_params["name"] in {"hybrid_search", "hybrid_search_scoped"}
        assert captured_params["params"]["search_language"] == expected_regconfig

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_documents_success(self):
        supabase = MagicMock()
        supabase.rpc.return_value.execute.return_value = Mock(data=[{"id": "doc-1"}])

        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.return_value = [0.1, 0.2]

        with patch("api.v1.search.get_supabase", return_value=supabase), \
             patch("services.embeddings.get_embeddings_model", return_value=mock_embeddings), \
             patch(
                 "api.v1.search.compliance_switch.filter_tombstoned_docs",
                 new=AsyncMock(return_value=[{"id": "doc-1"}]),
             ):
            result = await search_documents(
                request=_make_mock_request(),
                payload=SearchRequest(query="hello", limit=5, threshold=0.2),
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
             patch("services.embeddings.get_embeddings_model", return_value=mock_embeddings):
            with pytest.raises(HTTPException) as excinfo:
                await search_documents(
                    request=_make_mock_request(),
                    payload=SearchRequest(query="hello"),
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
             patch("services.embeddings.get_embeddings_model", return_value=mock_embeddings):
            with pytest.raises(HTTPException) as excinfo:
                await search_documents(
                    request=_make_mock_request(),
                    payload=SearchRequest(query="hello"),
                    user_id="user-1",
                )

        assert excinfo.value.status_code == 500
