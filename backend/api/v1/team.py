"""
Team Management API Router

Endpoints for managing teams and team members.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from core.security import get_current_user
from core.db import get_supabase
from services.team_service import team_service
from datetime import datetime, timezone

router = APIRouter()

# ============================================================
# MODELS
# ============================================================

class TeamResponse(BaseModel):
    """Team details response."""
    id: str
    name: str
    slug: Optional[str] = None
    owner_id: str
    created_at: str
    user_role: Optional[str] = None
    is_owner: bool = False

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

class EffectivePlanResponse(BaseModel):
    """Response for effective plan lookup."""
    plan: str
    inherited: bool
    team_id: Optional[str] = None
    team_name: Optional[str] = None


class InviteRequest(BaseModel):
    """Request to invite a team member."""
    email: str
    role: str = "viewer"
    name: Optional[str] = None


class InviteResponse(BaseModel):
    """Response from invite operation."""
    success: bool
    member: Optional[dict] = None
    error: Optional[str] = None
    code: Optional[str] = None


class BulkInviteResponse(BaseModel):
    """Response from bulk invite operation."""
    success: bool
    total: int = 0
    invited: int = 0
    failed: int = 0
    errors: List[dict] = []
    error: Optional[str] = None
    code: Optional[str] = None


# ============================================================
# TEAM ENDPOINTS
# ============================================================

@router.get("/team", response_model=TeamResponse)
async def get_current_team(user_id: str = Depends(get_current_user)):
    """Get the current user's team."""
    team = await team_service.get_user_team(user_id)
    
    if not team:
        raise HTTPException(status_code=404, detail="No team found for user")
    
    return team


@router.get("/team/effective-plan", response_model=EffectivePlanResponse)
async def get_effective_plan(user_id: str = Depends(get_current_user)):
    """
    Get the effective plan for the current user.
    
    This returns the plan inherited from the team owner,
    which determines feature access.
    """
    plan = await team_service.get_effective_plan(user_id)
    team = await team_service.get_user_team(user_id)
    
    # Determine if inherited (team owner's plan != user's own plan only matters if not owner)
    inherited = False
    team_id = None
    team_name = None
    
    if team:
        team_id = team.get("id")
        team_name = team.get("name")
        inherited = not team.get("is_owner", True)
    
    return EffectivePlanResponse(
        plan=plan,
        inherited=inherited,
        team_id=team_id,
        team_name=team_name
    )


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


@router.post("/team/invite", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
async def invite_team_member(
    payload: InviteRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Invite a new team member.
    
    **Enterprise Only**: Requires a plan with team seats.
    Returns 403 if plan doesn't allow team management.
    """
    result = await team_service.invite_member(
        owner_id=user_id,
        email=payload.email,
        role=payload.role,
        name=payload.name
    )
    
    if not result.get("success"):
        error_code = result.get("code", "ERROR")
        
        if error_code == "UPGRADE_REQUIRED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=result.get("error", "Upgrade required")
            )
        elif error_code == "ALREADY_EXISTS":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=result.get("error", "Already invited")
            )
        elif error_code == "SEAT_LIMIT":
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=result.get("error", "Seat limit reached")
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Invite failed")
            )
    
    return InviteResponse(
        success=True,
        member=result.get("member")
    )


@router.post("/team/bulk-invite", response_model=BulkInviteResponse)
async def bulk_invite_team_members(
    file: UploadFile,
    user_id: str = Depends(get_current_user)
):
    """
    Bulk invite team members from CSV file.
    
    **Enterprise Only**: Requires a plan with team seats.
    
    Expected CSV format:
    ```csv
    email,role,name
    alice@example.com,editor,Alice
    bob@example.com,viewer,Bob
    ```
    """
    # Read CSV content
    try:
        content = await file.read()
        csv_content = content.decode("utf-8")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read CSV: {str(e)}"
        )
    
    result = await team_service.bulk_invite_csv(
        owner_id=user_id,
        csv_content=csv_content
    )
    
    if not result.get("success") and result.get("code") == "UPGRADE_REQUIRED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=result.get("error", "Upgrade required")
        )
    
    return BulkInviteResponse(**result)


# Legacy endpoint for backward compatibility
@router.post("/team/members", response_model=TeamMemberResponse, status_code=status.HTTP_201_CREATED)
async def invite_team_member_legacy(
    payload: TeamMemberCreate,
    user_id: str = Depends(get_current_user)
):
    """
    Legacy invite endpoint - redirects to new gated version.
    Kept for backward compatibility.
    """
    result = await team_service.invite_member(
        owner_id=user_id,
        email=payload.email,
        role=payload.role,
        name=payload.name
    )
    
    if not result.get("success"):
        error_code = result.get("code", "ERROR")
        
        if error_code == "UPGRADE_REQUIRED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=result.get("error", "Upgrade to Enterprise to invite team members")
            )
        elif error_code == "ALREADY_EXISTS":
            raise HTTPException(status_code=409, detail="Member already invited")
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Invite failed"))
    
    # Return the member data in legacy format
    if result.get("member"):
        return result["member"]
    
    raise HTTPException(status_code=500, detail="Failed to create invitation")


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
            .update({"invited_at": datetime.now(timezone.utc).isoformat()})\
            .eq("id", member_id)\
            .execute()
        
        # In a real implementation, send email here
        
        return {"status": "success", "message": "Invitation resent"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resend: {str(e)}")
