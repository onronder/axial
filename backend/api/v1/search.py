"""
Search API Endpoints

Provides document search with scope-aware distribution analysis.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from api.v1.dependencies import validate_team_access
from core.security import get_current_user
from core.db import get_supabase
from core.config import settings
from langchain_openai import OpenAIEmbeddings
from services.team_service import team_service
from services.scope_analysis import (
    analyze_scope_distribution,
    get_scope_candidates_for_clarification,
    ScopeClassification,
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(validate_team_access)])


class SearchRequest(BaseModel):
    """Search request with optional scope filtering."""
    query: str = Field(..., min_length=1, max_length=10000)
    limit: int = Field(default=10, ge=1, le=50)
    threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    scope_ids: Optional[List[str]] = Field(
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
    primary_scope_id: Optional[str] = None
    dominance_ratio: float = 0.0
    total_docs: int = 0
    scoped_docs: int = 0
    distribution: List[ScopeDistribution] = []


class SearchResponse(BaseModel):
    """Search response with optional scope analysis."""
    results: List[Dict[str, Any]]
    scope_analysis: Optional[ScopeAnalysis] = None


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    payload: SearchRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Search documents with optional scope filtering and distribution analysis.
    
    Features:
    - Hybrid search (vector + keyword)
    - Optional scope filtering via scope_ids
    - Scope distribution analysis for Dominance Guard
    """
    supabase = get_supabase()
    
    # 1. Embed Query
    embeddings_model = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=settings.OPENAI_API_KEY
    )
    
    try:
        query_vector = embeddings_model.embed_query(payload.query)
    except Exception as e:
        logger.error(f"❌ [Search] Embedding failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate query embedding: {str(e)}"
        )
    
    # 2. Execute Hybrid Search (scope-aware)
    organization_id = await team_service.get_organization_id(user_id)

    try:
        if payload.scope_ids:
            # Use scoped search when explicit scope filter provided
            response = supabase.rpc("hybrid_search_scoped", {
                "query_text": payload.query,
                "query_embedding": query_vector,
                "match_count": payload.limit,
                "filter_org_id": organization_id,
                "filter_scope_ids": payload.scope_ids,
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
        
    except Exception as e:
        logger.error(f"❌ [Search] Hybrid search failed: {e}")
        # Fallback to match_documents if hybrid_search unavailable
        try:
            response = supabase.rpc("match_documents", {
                "query_embedding": query_vector,
                "match_threshold": payload.threshold,
                "match_count": payload.limit,
                "filter_org_id": organization_id
            }).execute()
            matches = response.data or []
        except Exception as fallback_e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Search failed: {str(fallback_e)}"
            )
    
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
