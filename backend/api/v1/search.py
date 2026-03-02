"""
Search API Endpoints

Provides document search with scope-aware distribution analysis.

GHOST PROTOCOL: Search results have encrypted content that is
decrypted before being returned to the client.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from api.v1.dependencies import (
    get_user_allowed_scopes,
    require_paid_access,
    validate_team_access,
)
from api.v1.error_utils import ApiErrorCode, api_error
from core.db import get_supabase
from core.rate_limit import limiter
from core.security import get_current_user
from services.scope_analysis import (
    analyze_scope_distribution,
)
from services.team_service import team_service

logger = logging.getLogger(__name__)


def _decrypt_search_results(results: list[dict]) -> list[dict]:
    """
    GHOST PROTOCOL: Decrypt content in search results.

    Handles encrypted content from Ghost Protocol storage.
    Errors are handled gracefully to ensure search functionality.
    """
    from core.security import (
        HAS_CHUNK_ENCRYPTION,
        EncryptionError,
        UnencryptedContentError,
        decrypt_text,
    )

    if not results or not HAS_CHUNK_ENCRYPTION:
        return results

    for result in results:
        if result.get('content'):
            try:
                result['content'] = decrypt_text(result['content'])
            except UnencryptedContentError:
                logger.warning(
                    "[GhostProtocol] Unencrypted content in search result"
                )
                result['content'] = "[Content unavailable - encryption policy violation]"
            except EncryptionError as e:
                logger.error(f"[GhostProtocol] Decryption failed: {e}")
                result['content'] = "[Content unavailable - decryption error]"
            except Exception:
                # Don't modify - might be plaintext (legacy data)
                pass

    return results

router = APIRouter(dependencies=[Depends(validate_team_access), Depends(require_paid_access)])


class SearchRequest(BaseModel):
    """Search request with optional scope filtering."""
    query: str = Field(..., min_length=1, max_length=10000)
    limit: int = Field(default=10, ge=1, le=50)
    threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    scope_ids: list[str] | None = Field(
        default=None,
        description="Optional: restrict search to specific scope URIs"
    )
    include_scope_analysis: bool = Field(
        default=False,
        description="Include scope distribution analysis in response"
    )


class ScopeDistribution(BaseModel):
    """Scope distribution statistics for a single scope."""
    scope_id: str
    count: int
    score_sum: float
    avg_score: float


class ScopeAnalysis(BaseModel):
    """Scope analysis result for retrieval results."""
    classification: str  # dominant, contested, fragmented, empty
    primary_scope_id: str | None = None
    dominance_ratio: float = 0.0
    total_docs: int = 0
    scoped_docs: int = 0
    distribution: list[ScopeDistribution] = []


class SearchResponse(BaseModel):
    """Search response with optional scope analysis."""
    results: list[dict[str, Any]]
    scope_analysis: ScopeAnalysis | None = None


@router.post("/search", response_model=SearchResponse)
@limiter.limit("60/minute")
async def search_documents(
    request: Request,
    payload: SearchRequest,
    user_id: str = Depends(get_current_user),
    allowed_scopes: list[str] | None = Depends(get_user_allowed_scopes),
):
    """
    Search documents with optional scope filtering and distribution analysis.

    Features:
    - Hybrid search (vector + keyword)
    - Optional scope filtering via scope_ids
    - Scope-level access control via consent system
    - Scope distribution analysis for Dominance Guard
    """
    supabase = get_supabase()

    # 1. Embed Query
    from services.embeddings import get_embeddings_model
    embeddings_model = get_embeddings_model()

    try:
        query_vector = embeddings_model.embed_query(payload.query)
    except Exception as e:
        raise api_error(ApiErrorCode.PROCESSING_ERROR, e, "search")

    # 2. Execute Hybrid Search (scope-aware)
    organization_id = await team_service.get_organization_id(user_id)

    # Apply scope-level access control: intersect requested scopes with allowed scopes
    effective_scope_ids = payload.scope_ids
    if allowed_scopes is not None:
        if effective_scope_ids:
            # Intersect: only allow scopes user has access to
            effective_scope_ids = [s for s in effective_scope_ids if s in allowed_scopes]
        else:
            # No explicit filter — restrict to allowed scopes
            effective_scope_ids = allowed_scopes

        # All scopes revoked or no intersection — return empty results
        if not effective_scope_ids:
            return SearchResponse(results=[], scope_analysis=None)

    try:
        if effective_scope_ids:
            # Use scoped search (explicit filter or access-controlled)
            response = supabase.rpc("hybrid_search_scoped", {
                "query_text": payload.query,
                "query_embedding": query_vector,
                "match_count": payload.limit,
                "filter_org_id": organization_id,
                "filter_scope_ids": effective_scope_ids,
                "similarity_threshold": payload.threshold,
            }).execute()
        else:
            # Standard hybrid search (now includes scope_id)
            response = supabase.rpc("hybrid_search", {
                "query_text": payload.query,
                "query_embedding": query_vector,
                "match_count": payload.limit,
                "filter_org_id": organization_id,
                "similarity_threshold": payload.threshold,
            }).execute()

        matches = response.data or []
        logger.info(f"📚 [Search] Found {len(matches)} results for query: {payload.query[:50]}...")

        # GHOST PROTOCOL: Decrypt content before returning
        matches = _decrypt_search_results(matches)

    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "search")

    # 3. Analyze scope distribution (optional)
    scope_analysis_response = None
    if payload.include_scope_analysis and matches:
        analysis = analyze_scope_distribution(matches)

        # Convert to response model
        distribution_list = []
        for scope_stats in sorted(
            analysis.distribution.values(),
            key=lambda s: s.count,
            reverse=True
        )[:10]:  # Top 10 scopes
            distribution_list.append(ScopeDistribution(
                scope_id=scope_stats.scope_id,
                count=scope_stats.count,
                score_sum=round(scope_stats.score_sum, 3),
                avg_score=round(scope_stats.avg_score, 3),
            ))

        scope_analysis_response = ScopeAnalysis(
            classification=analysis.classification.value,
            primary_scope_id=analysis.primary_scope_id,
            dominance_ratio=round(analysis.dominance_ratio, 3),
            total_docs=analysis.total_docs,
            scoped_docs=analysis.scoped_docs,
            distribution=distribution_list,
        )

    return SearchResponse(
        results=matches,
        scope_analysis=scope_analysis_response
    )
