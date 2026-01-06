"""
Admin API Router

Endpoints for administrative functions including audit logs.
"""

import logging
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from core.security import get_current_user
from core.db import get_supabase
from services.team_service import team_service

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================

class AuditLogEntry(BaseModel):
    """Response model for audit log entries."""
    id: str
    user_id: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: dict = {}
    ip_address: Optional[str] = None
    created_at: str


class AuditLogListResponse(BaseModel):
    """Paginated audit log response."""
    items: List[AuditLogEntry]
    total: int
    has_more: bool


# =============================================================================
# Audit Log Endpoints
# =============================================================================

@router.get("/audit-logs", response_model=AuditLogListResponse)
async def get_audit_logs(
    user_id: str = Depends(get_current_user),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
):
    """
    Get audit logs for the user's team/account.
    
    Filters:
    - action: Filter by action type (e.g., 'document.delete')
    - resource_type: Filter by resource (e.g., 'document', 'chat')
    - from_date: ISO date string for start of range
    - to_date: ISO date string for end of range
    
    Only team owners/admins can view audit logs.
    """
    supabase = get_supabase()
    
    try:
        # Check if user is team owner or admin
        team = await team_service.get_user_team(user_id)
        if team:
            role = team.get("user_role", "viewer")
            if role not in ["owner", "admin"]:
                raise HTTPException(
                    status_code=403,
                    detail="Only team owners and admins can view audit logs"
                )
        
        # Build query
        query = supabase.table("audit_logs")\
            .select("*", count="exact")\
            .eq("user_id", user_id)
        
        # Apply filters
        if action:
            query = query.eq("action", action)
        if resource_type:
            query = query.eq("resource_type", resource_type)
        if from_date:
            query = query.gte("created_at", from_date)
        if to_date:
            query = query.lte("created_at", to_date)
        
        # Execute with pagination
        result = query\
            .order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        total = result.count if result.count is not None else 0
        items = [AuditLogEntry(**log) for log in (result.data or [])]
        
        return AuditLogListResponse(
            items=items,
            total=total,
            has_more=(offset + limit) < total
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch audit logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch audit logs")


@router.get("/audit-logs/actions")
async def get_audit_log_actions(
    user_id: str = Depends(get_current_user)
):
    """
    Get list of distinct action types in audit logs.
    
    Useful for populating filter dropdowns in the UI.
    """
    # Return static list of known actions for efficiency
    return {
        "actions": [
            "document.delete",
            "document.update", 
            "chat.delete",
            "connector.sync_start",
            "connector.sync_success",
            "connector.sync_fail",
            "settings.update",
            "team.member_invite",
            "team.member_remove"
        ]
    }
