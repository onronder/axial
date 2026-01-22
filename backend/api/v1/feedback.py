"""
Feedback API Router

Endpoints for collecting and analyzing user feedback on AI chat responses.

Endpoints:
- POST /chat/feedback - Submit feedback on a message
- GET /chat/feedback/conversation/{id} - Get user's feedback for a conversation
- GET /analytics/feedback - Team feedback analytics (admin only)
- GET /analytics/feedback/sources - Source quality metrics (admin only)
- GET /admin/feedback/platform - Platform-wide analytics (platform admin only)

Related Files:
- backend/services/feedback_service.py (business logic)
- supabase/migrations/20260122000000_message_feedback.sql (schema)
- frontend-new/components/chat/FeedbackButtons.tsx (UI)
"""

import logging
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, field_validator
from api.v1.dependencies import (
    get_current_user,
    validate_team_access,
    require_admin,
    get_user_organization_id,
)
from api.v1.error_utils import api_error, ApiErrorCode
from core.db import get_supabase
from core.rate_limit import limiter
from services.feedback_service import feedback_service
from services.team_service import team_service

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class SourceSnapshot(BaseModel):
    """Source metadata snapshot for feedback."""
    index: Optional[int] = None
    type: Optional[str] = None
    label: Optional[str] = None
    url: Optional[str] = None
    page: Optional[int] = None
    section: Optional[str] = None


class SubmitFeedbackRequest(BaseModel):
    """Request body for submitting feedback."""
    message_id: str = Field(..., description="UUID of the message being rated")
    rating: str = Field(..., description="Rating: 'positive' or 'negative'")
    feedback_text: Optional[str] = Field(
        None, 
        max_length=100,
        description="Optional comment (max 100 characters)"
    )
    # Context for analytics (sent by frontend)
    query_text: str = Field(..., description="The user's original question")
    answer_preview: str = Field(..., description="First 500 chars of AI response")
    sources: List[SourceSnapshot] = Field(
        default_factory=list,
        description="Sources cited in the response"
    )
    
    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v):
        if v not in ('positive', 'negative'):
            raise ValueError("rating must be 'positive' or 'negative'")
        return v
    
    @field_validator('feedback_text')
    @classmethod
    def validate_feedback_text(cls, v):
        if v is not None and len(v) > 100:
            raise ValueError("feedback_text must be 100 characters or less")
        return v


class FeedbackResponse(BaseModel):
    """Response after submitting feedback."""
    id: str
    message_id: str
    rating: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    is_update: bool = False


class FeedbackItem(BaseModel):
    """Individual feedback item in analytics."""
    id: str
    rating: str
    feedback_text: Optional[str] = None
    query_text: str
    answer_preview: str
    sources: List[dict] = []
    user_email: str
    created_at: str


class FeedbackSummary(BaseModel):
    """Summary statistics for feedback."""
    positive_count: int
    negative_count: int
    total_count: int
    negative_rate_pct: float


class TeamFeedbackResponse(BaseModel):
    """Response for team feedback analytics."""
    items: List[FeedbackItem]
    total: int
    has_more: bool
    summary: FeedbackSummary


class SourceMetricItem(BaseModel):
    """Source quality metric item."""
    source_label: str
    source_type: Optional[str] = None
    source_url: Optional[str] = None
    positive_count: int
    negative_count: int
    total_feedback: int
    negative_rate_pct: float
    last_feedback_at: Optional[str] = None


class SourceMetricsResponse(BaseModel):
    """Response for source quality metrics."""
    items: List[SourceMetricItem]
    total: int


class ConversationFeedbackResponse(BaseModel):
    """Response for user's feedback in a conversation."""
    feedback: dict  # message_id -> rating mapping


# =============================================================================
# Platform Admin Dependency
# =============================================================================

async def require_platform_admin(user_id: str = Depends(get_current_user)) -> str:
    """
    Verify user is a platform admin.
    
    Platform admins are identified by:
    - Email ending with @axiohub.io
    - Or is_platform_admin flag in user_profiles
    """
    supabase = get_supabase()
    
    try:
        # Check user email via auth admin API
        user_result = supabase.auth.admin.get_user_by_id(user_id)
        if user_result and user_result.user:
            email = user_result.user.email or ""
            if email.endswith("@axiohub.io"):
                return user_id
        
        # Check is_platform_admin flag in user_profiles
        profile = supabase.table("user_profiles")\
            .select("is_platform_admin")\
            .eq("user_id", user_id)\
            .maybeSingle()\
            .execute()
        
        if profile.data and profile.data.get("is_platform_admin"):
            return user_id
        
    except Exception as e:
        logger.error(f"[require_platform_admin] Error checking admin status: {e}")
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": "PLATFORM_ADMIN_REQUIRED",
            "message": "This endpoint requires platform admin access"
        }
    )


# =============================================================================
# Feedback Submission Endpoints
# =============================================================================

@router.post("/chat/feedback", response_model=FeedbackResponse, status_code=201)
@limiter.limit("30/minute")
async def submit_feedback(
    request: Request,
    payload: SubmitFeedbackRequest,
    user_id: str = Depends(validate_team_access),
    organization_id: str = Depends(get_user_organization_id)
):
    """
    Submit feedback on an AI chat response.
    
    Users can rate messages as positive (helpful) or negative (not helpful).
    One rating per user per message - submitting again updates the existing rating.
    
    The rating and context are stored for quality analytics:
    - Team admins can see which source documents produce poor answers
    - Platform admins can analyze feedback across all organizations
    """
    supabase = get_supabase()
    
    try:
        # Verify the message exists and user can access it
        message = supabase.table("messages")\
            .select("id, conversation_id, role")\
            .eq("id", payload.message_id)\
            .maybeSingle()\
            .execute()
        
        if not message.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )
        
        # Only allow feedback on assistant messages
        if message.data.get("role") != "assistant":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Feedback can only be submitted for assistant messages"
            )
        
        conversation_id = message.data["conversation_id"]
        
        # Verify user can access this conversation (org membership)
        conversation = supabase.table("conversations")\
            .select("id, organization_id")\
            .eq("id", conversation_id)\
            .maybeSingle()\
            .execute()
        
        if not conversation.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Org membership is implicitly verified by get_user_organization_id
        # but let's also check the conversation belongs to user's org
        conv_org_id = conversation.data.get("organization_id")
        if conv_org_id and conv_org_id != organization_id:
            logger.warning(
                f"[Feedback] Org mismatch: user_org={organization_id[:8]}... "
                f"conv_org={conv_org_id[:8]}..."
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this conversation"
            )
        
        # Convert sources to dict format
        sources_data = [
            s.model_dump(exclude_none=True) 
            for s in payload.sources
        ]
        
        # Submit feedback via service
        result = await feedback_service.submit_feedback(
            supabase=supabase,
            user_id=user_id,
            organization_id=organization_id,
            message_id=payload.message_id,
            conversation_id=conversation_id,
            rating=payload.rating,
            query_text=payload.query_text,
            answer_preview=payload.answer_preview,
            sources_snapshot=sources_data,
            feedback_text=payload.feedback_text,
        )
        
        return FeedbackResponse(**result)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"[Feedback] Submit failed: {e}")
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "submit_feedback")


@router.get("/chat/feedback/conversation/{conversation_id}", response_model=ConversationFeedbackResponse)
@limiter.limit("60/minute")
async def get_conversation_feedback(
    request: Request,
    conversation_id: str,
    user_id: str = Depends(validate_team_access)
):
    """
    Get the current user's feedback for all messages in a conversation.
    
    Returns a mapping of message_id -> rating for messages the user has rated.
    This is used by the frontend to show the current feedback state.
    """
    supabase = get_supabase()
    
    try:
        # Verify user can access this conversation
        conversation = supabase.table("conversations")\
            .select("id")\
            .eq("id", conversation_id)\
            .maybeSingle()\
            .execute()
        
        if not conversation.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        feedback_map = await feedback_service.get_user_feedback_for_conversation(
            supabase=supabase,
            user_id=user_id,
            conversation_id=conversation_id
        )
        
        return ConversationFeedbackResponse(feedback=feedback_map)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Feedback] Get conversation feedback failed: {e}")
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "get_conversation_feedback")


# =============================================================================
# Team Analytics Endpoints (Admin Only)
# =============================================================================

@router.get("/analytics/feedback", response_model=TeamFeedbackResponse)
@limiter.limit("30/minute")
async def get_team_feedback(
    request: Request,
    user_id: str = Depends(require_admin),
    organization_id: str = Depends(get_user_organization_id),
    limit: int = Query(default=50, le=100, ge=1),
    offset: int = Query(default=0, ge=0),
    rating: Optional[str] = Query(default=None, description="Filter: 'positive' or 'negative'"),
    from_date: Optional[str] = Query(default=None, description="ISO date for start of range"),
    to_date: Optional[str] = Query(default=None, description="ISO date for end of range"),
    source_label: Optional[str] = Query(default=None, description="Filter by source document")
):
    """
    Get feedback analytics for the team/organization.
    
    Only team owners and admins can access this endpoint.
    
    Use this to:
    - Review recent negative feedback
    - Identify problematic source documents
    - Track quality trends over time
    """
    supabase = get_supabase()
    
    try:
        # Validate rating filter
        if rating and rating not in ('positive', 'negative'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="rating must be 'positive' or 'negative'"
            )
        
        result = await feedback_service.get_team_feedback(
            supabase=supabase,
            organization_id=organization_id,
            limit=limit,
            offset=offset,
            rating=rating,
            from_date=from_date,
            to_date=to_date,
            source_label=source_label,
        )
        
        return TeamFeedbackResponse(
            items=[FeedbackItem(**item) for item in result["items"]],
            total=result["total"],
            has_more=result["has_more"],
            summary=FeedbackSummary(**result["summary"]),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Feedback] Get team feedback failed: {e}")
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "get_team_feedback")


@router.get("/analytics/feedback/sources", response_model=SourceMetricsResponse)
@limiter.limit("30/minute")
async def get_source_metrics(
    request: Request,
    user_id: str = Depends(require_admin),
    organization_id: str = Depends(get_user_organization_id),
    min_feedback_count: int = Query(default=5, ge=1, description="Min feedback to include"),
    sort_by: str = Query(default="negative_rate_pct", description="Sort column"),
    sort_order: str = Query(default="desc", description="'asc' or 'desc'"),
    limit: int = Query(default=20, le=50, ge=1)
):
    """
    Get aggregated quality metrics by source document.
    
    Shows which documents appear most frequently in negative feedback,
    helping identify content that needs improvement or removal.
    
    Only team owners and admins can access this endpoint.
    """
    supabase = get_supabase()
    
    try:
        # Validate sort_order
        if sort_order not in ('asc', 'desc'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="sort_order must be 'asc' or 'desc'"
            )
        
        result = await feedback_service.get_source_metrics(
            supabase=supabase,
            organization_id=organization_id,
            min_feedback_count=min_feedback_count,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
        )
        
        return SourceMetricsResponse(
            items=[SourceMetricItem(**item) for item in result["items"]],
            total=result["total"],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Feedback] Get source metrics failed: {e}")
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "get_source_metrics")


# =============================================================================
# Platform Admin Endpoints
# =============================================================================

@router.get("/admin/feedback/platform")
@limiter.limit("30/minute")
async def get_platform_feedback(
    request: Request,
    user_id: str = Depends(require_platform_admin),
    limit: int = Query(default=50, le=100, ge=1),
    offset: int = Query(default=0, ge=0),
    rating: Optional[str] = Query(default=None),
    from_date: Optional[str] = Query(default=None),
    to_date: Optional[str] = Query(default=None),
    organization_id: Optional[str] = Query(default=None, description="Filter by org")
):
    """
    Get feedback across all organizations (platform admin only).
    
    This endpoint is for Axio platform administrators to:
    - Monitor overall RAG quality
    - Identify systemic issues
    - Analyze feedback patterns across the platform
    
    Requires @axiohub.io email or is_platform_admin flag.
    """
    supabase = get_supabase()
    
    try:
        result = await feedback_service.get_platform_feedback(
            supabase=supabase,
            limit=limit,
            offset=offset,
            rating=rating,
            from_date=from_date,
            to_date=to_date,
            organization_id=organization_id,
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Feedback] Get platform feedback failed: {e}")
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "get_platform_feedback")


@router.post("/admin/feedback/refresh-metrics")
@limiter.limit("5/minute")
async def refresh_metrics(
    request: Request,
    user_id: str = Depends(require_platform_admin)
):
    """
    Manually refresh the source_feedback_metrics materialized view.
    
    Platform admin only. Use after bulk feedback operations or if
    metrics appear stale.
    """
    supabase = get_supabase()
    
    try:
        await feedback_service.refresh_metrics(supabase)
        return {"status": "success", "message": "Metrics refreshed"}
        
    except Exception as e:
        logger.error(f"[Feedback] Refresh metrics failed: {e}")
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "refresh_metrics")
