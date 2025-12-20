"""
Team Management API Router

Endpoints for managing team members and invitations.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from core.security import get_current_user
from core.db import get_supabase
from datetime import datetime

router = APIRouter()

# ============================================================
# MODELS
# ============================================================

class TeamMemberResponse(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    role: str
    status: str
    last_active: Optional[str] = None
    created_at: str
    invited_at: Optional[str] = None

class TeamMemberCreate(BaseModel):
    email: str
    name: Optional[str] = None
    role: str = "viewer"

class TeamMemberUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None

class TeamStatsResponse(BaseModel):
    total_seats: int = 20
    active_members: int
    pending_invites: int

# ============================================================
# TEAM ENDPOINTS
# ============================================================

@router.get("/team/members", response_model=List[TeamMemberResponse])
async def list_team_members(
    user_id: str = Depends(get_current_user),
    role: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List team members with optional filters."""
    supabase = get_supabase()
    
    try:
        query = supabase.table("team_members")\
            .select("*")\
            .eq("owner_user_id", user_id)\
            .order("created_at", desc=True)
        
        # Apply filters
        if role and role != "all":
            query = query.eq("role", role)
        if status and status != "all":
            query = query.eq("status", status)
        
        # Note: Supabase doesn't support ILIKE easily through client, 
        # so search would need to be done client-side or via RPC
        
        query = query.range(offset, offset + limit - 1)
        
        response = query.execute()
        
        # Client-side search filter if provided
        results = response.data or []
        if search:
            search_lower = search.lower()
            results = [
                m for m in results 
                if search_lower in (m.get("name", "") or "").lower() 
                or search_lower in (m.get("email", "") or "").lower()
            ]
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch team: {str(e)}")


@router.get("/team/stats", response_model=TeamStatsResponse)
async def get_team_stats(user_id: str = Depends(get_current_user)):
    """Get team statistics."""
    supabase = get_supabase()
    
    try:
        response = supabase.table("team_members")\
            .select("status")\
            .eq("owner_user_id", user_id)\
            .execute()
        
        members = response.data or []
        
        active = sum(1 for m in members if m.get("status") == "active")
        pending = sum(1 for m in members if m.get("status") == "pending")
        
        return TeamStatsResponse(
            total_seats=20,
            active_members=active,
            pending_invites=pending
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")


@router.post("/team/members", response_model=TeamMemberResponse, status_code=status.HTTP_201_CREATED)
async def invite_team_member(
    payload: TeamMemberCreate,
    user_id: str = Depends(get_current_user)
):
    """Invite a new team member."""
    supabase = get_supabase()
    
    try:
        # Validate role
        if payload.role not in ["admin", "editor", "viewer"]:
            raise HTTPException(status_code=400, detail="Invalid role")
        
        # Check if already invited
        existing = supabase.table("team_members")\
            .select("id")\
            .eq("owner_user_id", user_id)\
            .eq("email", payload.email)\
            .execute()
        
        if existing.data and len(existing.data) > 0:
            raise HTTPException(status_code=409, detail="Member already invited")
        
        # Create invitation
        now = datetime.utcnow().isoformat()
        new_member = {
            "owner_user_id": user_id,
            "email": payload.email,
            "name": payload.name or payload.email.split("@")[0],
            "role": payload.role,
            "status": "pending",
            "created_at": now,
            "invited_at": now
        }
        
        response = supabase.table("team_members")\
            .insert(new_member)\
            .execute()
        
        if response.data:
            return response.data[0]
        
        raise HTTPException(status_code=500, detail="Failed to create invitation")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to invite member: {str(e)}")


@router.patch("/team/members/{member_id}", response_model=TeamMemberResponse)
async def update_team_member(
    member_id: str,
    payload: TeamMemberUpdate,
    user_id: str = Depends(get_current_user)
):
    """Update a team member's role or status."""
    supabase = get_supabase()
    
    try:
        # Build update data
        update_data = {}
        
        if payload.name is not None:
            update_data["name"] = payload.name
        if payload.role is not None:
            if payload.role not in ["admin", "editor", "viewer"]:
                raise HTTPException(status_code=400, detail="Invalid role")
            update_data["role"] = payload.role
        if payload.status is not None:
            if payload.status not in ["active", "pending", "suspended"]:
                raise HTTPException(status_code=400, detail="Invalid status")
            update_data["status"] = payload.status
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No update fields provided")
        
        response = supabase.table("team_members")\
            .update(update_data)\
            .eq("id", member_id)\
            .eq("owner_user_id", user_id)\
            .execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        
        raise HTTPException(status_code=404, detail="Member not found")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update member: {str(e)}")


@router.delete("/team/members/{member_id}")
async def remove_team_member(
    member_id: str,
    user_id: str = Depends(get_current_user)
):
    """Remove a team member."""
    supabase = get_supabase()
    
    try:
        response = supabase.table("team_members")\
            .delete()\
            .eq("id", member_id)\
            .eq("owner_user_id", user_id)\
            .execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Member not found")
        
        return {"status": "success", "id": member_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove member: {str(e)}")


@router.post("/team/members/{member_id}/resend")
async def resend_invitation(
    member_id: str,
    user_id: str = Depends(get_current_user)
):
    """Resend invitation to a pending member."""
    supabase = get_supabase()
    
    try:
        # Verify member exists and belongs to user
        response = supabase.table("team_members")\
            .select("*")\
            .eq("id", member_id)\
            .eq("owner_user_id", user_id)\
            .eq("status", "pending")\
            .execute()
        
        if not response.data or len(response.data) == 0:
            raise HTTPException(status_code=404, detail="Pending member not found")
        
        # Update invited_at timestamp
        supabase.table("team_members")\
            .update({"invited_at": datetime.utcnow().isoformat()})\
            .eq("id", member_id)\
            .execute()
        
        # In a real implementation, send email here
        
        return {"status": "success", "message": "Invitation resent"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resend: {str(e)}")
