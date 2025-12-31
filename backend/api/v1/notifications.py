"""
Notifications API Router

Provides endpoints for managing user notifications.
Tracks operation lifecycle events (success, warning, error, info).
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime, timezone
import json
from core.security import get_current_user
from core.db import get_supabase
from models import NotificationResponse, NotificationListResponse, UnreadCountResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Helper Functions
# =============================================================================

def create_notification(
    supabase,
    user_id: str,
    title: str,
    message: str = None,
    notification_type: str = "info",
    metadata: dict = None
) -> dict:
    """
    Helper to create a notification in the database.
    
    Args:
        supabase: Supabase client instance
        user_id: User's ID
        title: Notification title
        message: Optional detailed message
        notification_type: One of 'info', 'success', 'warning', 'error'
        metadata: Optional extra data (e.g., job_id, file_names)
    
    Returns:
        Created notification dict
    """
    notification_data = {
        "user_id": user_id,
        "title": title,
        "message": message,
        "type": notification_type,
        "is_read": False,
        # Serialize dict to JSON string for extra_data column
        "extra_data": json.dumps(metadata) if metadata else None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        result = supabase.table("notifications").insert(notification_data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Failed to create notification: {e}")
        return None


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications(
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
        
        def parse_extra_data(data: Optional[str]) -> Optional[dict]:
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
        logger.error(f"Failed to list notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch notifications")


@router.get("/notifications/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(user_id: str = Depends(get_current_user)):
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
        logger.error(f"Failed to get unread count: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch unread count")


@router.patch("/notifications/{notification_id}/read", response_model=NotificationResponse)
async def mark_as_read(
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
        logger.error(f"Failed to mark notification as read: {e}")
        raise HTTPException(status_code=500, detail="Failed to update notification")


@router.patch("/notifications/read-all")
async def mark_all_as_read(user_id: str = Depends(get_current_user)):
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
        logger.error(f"Failed to mark all as read: {e}")
        raise HTTPException(status_code=500, detail="Failed to update notifications")


@router.delete("/notifications/all")
async def clear_all_notifications(user_id: str = Depends(get_current_user)):
    """Delete all notifications for the user."""
    supabase = get_supabase()
    
    try:
        supabase.table("notifications")\
            .delete()\
            .eq("user_id", user_id)\
            .execute()
        
        return {"status": "success", "message": "All notifications cleared"}
        
    except Exception as e:
        logger.error(f"Failed to clear notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear notifications")


@router.delete("/notifications/{notification_id}")
async def delete_notification(
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
        logger.error(f"Failed to delete notification: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete notification")
