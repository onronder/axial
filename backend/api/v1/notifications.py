"""
Notifications API Router

Provides endpoints for managing user notifications.
Tracks operation lifecycle events (success, warning, error, info).
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from api.v1.dependencies import require_paid_access, validate_team_access
from api.v1.error_utils import ApiErrorCode, api_error
from core.db import get_supabase
from core.rate_limit import limiter
from core.security import get_current_user
from models import NotificationListResponse, NotificationResponse, UnreadCountResponse

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(validate_team_access), Depends(require_paid_access)])


# =============================================================================
# Helper Functions (re-exported from centralized service)
# =============================================================================

# Import from centralized service to avoid duplication
from services.notification_service import create_notification  # noqa: F401

# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/notifications", response_model=NotificationListResponse)
@limiter.limit("60/minute")
async def list_notifications(
    request: Request,
    user_id: str = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
    unread_only: bool = False
):
    """
    List user's notifications with pagination.

    Returns notifications sorted by created_at desc.
    """
    supabase = get_supabase()

    try:
        # Build query
        query = supabase.table("notifications")\
            .select("*", count="exact")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .offset(offset)

        if unread_only:
            query = query.eq("is_read", False)

        response = query.execute()

        # Get unread count
        unread_response = supabase.table("notifications")\
            .select("id", count="exact")\
            .eq("user_id", user_id)\
            .eq("is_read", False)\
            .execute()

        def parse_extra_data(data: str | None) -> dict | None:
            if not data:
                return None
            try:
                return json.loads(data)
            except (json.JSONDecodeError, TypeError):
                return None

        notifications = [
            NotificationResponse(
                id=str(n["id"]),
                title=n["title"],
                message=n.get("message"),
                type=n["type"],
                is_read=n["is_read"],
                metadata=parse_extra_data(n.get("extra_data")),
                created_at=n.get("created_at")
            )
            for n in (response.data or [])
        ]

        return NotificationListResponse(
            notifications=notifications,
            total=response.count or len(notifications),
            unread_count=unread_response.count or 0
        )

    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "fetch_notifications")


@router.get("/notifications/unread-count", response_model=UnreadCountResponse)
@limiter.limit("120/minute")
async def get_unread_count(request: Request, user_id: str = Depends(get_current_user)):
    """
    Lightweight endpoint for unread notification count.

    Optimized for frequent polling (every 30s).
    """
    supabase = get_supabase()

    try:
        response = supabase.table("notifications")\
            .select("id", count="exact")\
            .eq("user_id", user_id)\
            .eq("is_read", False)\
            .execute()

        return UnreadCountResponse(count=response.count or 0)

    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "fetch_unread_count")


@router.patch("/notifications/{notification_id}/read", response_model=NotificationResponse)
@limiter.limit("60/minute")
async def mark_as_read(
    request: Request,
    notification_id: str,
    user_id: str = Depends(get_current_user)
):
    """Mark a specific notification as read."""
    supabase = get_supabase()

    try:
        # Update notification
        response = supabase.table("notifications")\
            .update({"is_read": True})\
            .eq("id", notification_id)\
            .eq("user_id", user_id)\
            .execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Notification not found")

        n = response.data[0]

        # Parse extra_data JSON
        extra_data_parsed = None
        if n.get("extra_data"):
            try:
                extra_data_parsed = json.loads(n["extra_data"])
            except (json.JSONDecodeError, TypeError):
                pass

        return NotificationResponse(
            id=str(n["id"]),
            title=n["title"],
            message=n.get("message"),
            type=n["type"],
            is_read=n["is_read"],
            metadata=extra_data_parsed,
            created_at=n.get("created_at")
        )

    except HTTPException:
        raise
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "mark_notification_read")


@router.patch("/notifications/read-all")
@limiter.limit("10/minute")
async def mark_all_as_read(request: Request, user_id: str = Depends(get_current_user)):
    """Mark all notifications as read."""
    supabase = get_supabase()

    try:
        supabase.table("notifications")\
            .update({"is_read": True})\
            .eq("user_id", user_id)\
            .eq("is_read", False)\
            .execute()

        return {"status": "success", "message": "All notifications marked as read"}

    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "mark_notification_read")


@router.delete("/notifications/all")
@limiter.limit("5/minute")
async def clear_all_notifications(request: Request, user_id: str = Depends(get_current_user)):
    """Delete all notifications for the user."""
    supabase = get_supabase()

    try:
        supabase.table("notifications")\
            .delete()\
            .eq("user_id", user_id)\
            .execute()

        return {"status": "success", "message": "All notifications cleared"}

    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "clear_notifications")


@router.delete("/notifications/{notification_id}")
@limiter.limit("30/minute")
async def delete_notification(
    request: Request,
    notification_id: str,
    user_id: str = Depends(get_current_user)
):
    """Delete a specific notification."""
    supabase = get_supabase()

    try:
        response = supabase.table("notifications")\
            .delete()\
            .eq("id", notification_id)\
            .eq("user_id", user_id)\
            .execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Notification not found")

        return {"status": "success", "message": "Notification deleted"}

    except HTTPException:
        raise
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "delete_notification")
