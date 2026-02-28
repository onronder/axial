"""
Team Management API Router

Endpoints for managing teams and team members.

Note: Most endpoints require paid access via require_paid_access dependency.
      The /team/effective-plan endpoint is exempt (defined separately) to allow
      the frontend to check plan status before showing the paywall.
"""

import logging
from datetime import datetime, timezone
from enum import Enum

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from pydantic import BaseModel, EmailStr, Field

from api.v1.dependencies import require_paid_access, validate_team_access
from api.v1.error_utils import (
    ApiErrorCode,
    api_error,
    api_error_400,
    api_error_403,
    api_error_404,
)
from core.db import get_supabase
from core.rate_limit import limiter
from core.security import get_current_user
from services.audit import audit_logger
from services.team_service import team_service

logger = logging.getLogger(__name__)


class TeamRole(str, Enum):
    """Valid team member roles."""
    admin = "admin"
    editor = "editor"
    viewer = "viewer"

# Main router with paid access requirement for team management operations
router = APIRouter()

# ============================================================
# MODELS
# ============================================================

class TeamResponse(BaseModel):
    """Team details response."""
    id: str
    name: str
    slug: str | None = None
    owner_id: str
    created_at: str
    user_role: str | None = None
    is_owner: bool = False

class TeamMemberResponse(BaseModel):
    id: str
    email: str
    name: str | None = None
    role: str
    status: str
    last_active: str | None = None
    created_at: str
    invited_at: str | None = None
    expires_at: str | None = None

class TeamMemberCreate(BaseModel):
    email: EmailStr
    name: str | None = Field(None, max_length=100)
    role: TeamRole = TeamRole.viewer

class TeamMemberUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    role: TeamRole | None = None
    status: str | None = Field(None, max_length=30)

class TeamMemberListResponse(BaseModel):
    """Paginated team member list response."""
    items: list[TeamMemberResponse]
    total: int
    has_more: bool

class TeamStatsResponse(BaseModel):
    total_seats: int = 20
    active_members: int
    pending_invites: int
    suspended_members: int = 0

class EffectivePlanResponse(BaseModel):
    """Response for effective plan lookup."""
    plan: str
    inherited: bool
    team_id: str | None = None
    team_name: str | None = None


class TeamUpdate(BaseModel):
    """Request model for updating team details."""
    name: str | None = Field(None, max_length=100)
    slug: str | None = Field(None, max_length=50)


class InviteRequest(BaseModel):
    """Request to invite a team member."""
    email: EmailStr
    role: TeamRole = TeamRole.viewer
    name: str | None = Field(None, max_length=100)


class InviteResponse(BaseModel):
    """Response from invite operation."""
    success: bool
    member: dict | None = None
    error: str | None = None
    code: str | None = None


class BulkInviteResponse(BaseModel):
    """Response from bulk invite operation."""
    success: bool
    total: int = 0
    invited: int = 0
    failed: int = 0
    errors: list[dict] = []
    error: str | None = None
    code: str | None = None


class DeclineInviteRequest(BaseModel):
    """Request to decline a team invitation."""
    token: str


class AcceptInviteRequest(BaseModel):
    """Request to accept a team invitation."""
    token: str  # The invite token (member_id from the URL)


class AcceptInviteResponse(BaseModel):
    """Response from accept invite operation."""
    success: bool
    team_name: str | None = None
    team_id: str | None = None
    error: str | None = None


class PendingInvite(BaseModel):
    """A pending team invite for the current user."""
    id: str
    team_id: str
    team_name: str
    role: str
    invited_at: str
    expires_at: str | None = None


class PendingInvitesResponse(BaseModel):
    """Response containing user's pending invites."""
    invites: list[PendingInvite]
    count: int


# ============================================================
# TEAM ENDPOINTS
# ============================================================

# Shared dependency for paid-only team operations
_paid_team_deps = [Depends(validate_team_access), Depends(require_paid_access)]


@router.get("/team", response_model=TeamResponse, dependencies=_paid_team_deps)
@limiter.limit("60/minute")
async def get_current_team(request: Request, user_id: str = Depends(get_current_user)):
    """Get the current user's team."""
    team = await team_service.get_user_team(user_id)

    if not team:
        raise api_error_404("team")

    return team


@router.get("/team/my-invites", response_model=PendingInvitesResponse)
@limiter.limit("30/minute")
async def get_pending_invites(
    request: Request,
    user_id: str = Depends(get_current_user)
):
    """
    Get pending team invites for the current user.

    Matches invites by the user's email address. This endpoint is not
    gated by paid access so users can see invites before joining a team.
    """
    supabase = get_supabase()

    try:
        # Get current user's email
        user_response = supabase.table("user_profiles").select("email").eq("user_id", user_id).single().execute()

        if not user_response.data or not user_response.data.get("email"):
            return PendingInvitesResponse(invites=[], count=0)

        user_email = user_response.data["email"]

        # Find pending invites for this email (exclude expired)
        invites_response = supabase.table("team_members").select(
            "id, team_id, role, created_at, expires_at, teams(id, name)"
        ).eq("email", user_email).eq("status", "pending").execute()

        now = datetime.now(timezone.utc)
        invites = []
        for invite in (invites_response.data or []):
            # Skip expired invites
            expires_at_str = invite.get("expires_at")
            if expires_at_str:
                try:
                    expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
                    if now > expires_at:
                        continue
                except (ValueError, TypeError):
                    continue  # Fail-closed: skip unparseable expiry

            team_info = invite.get("teams", {})
            if team_info:
                invites.append(PendingInvite(
                    id=invite["id"],
                    team_id=invite["team_id"],
                    team_name=team_info.get("name", "Unknown Team"),
                    role=invite.get("role", "viewer"),
                    invited_at=invite.get("created_at", ""),
                    expires_at=invite.get("expires_at"),
                ))

        return PendingInvitesResponse(invites=invites, count=len(invites))

    except Exception as e:
        logger.error(f"Failed to fetch pending invites: {e}")
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "get_pending_invites")


@router.patch("/team", response_model=TeamResponse, dependencies=_paid_team_deps)
@limiter.limit("30/minute")
async def update_team(
    request: Request,
    payload: TeamUpdate,
    user_id: str = Depends(get_current_user)
):
    """
    Update team name or slug.

    Only team owners can update team details.
    """
    supabase = get_supabase()

    try:
        # Get user's team and verify ownership
        team = await team_service.get_user_team(user_id)

        if not team:
            raise api_error_404("team")

        if not team.get("is_owner"):
            raise api_error_403("Only team owners can update team details")

        # Build update payload
        update_data = {}
        if payload.name is not None:
            update_data["name"] = payload.name
        if payload.slug is not None:
            # Validate slug format (lowercase, alphanumeric with dashes)
            import re
            if not re.match(r'^[a-z0-9-]+$', payload.slug):
                raise api_error_400("Slug must be lowercase alphanumeric with dashes only")
            update_data["slug"] = payload.slug

        if not update_data:
            raise api_error_400("No update fields provided")

        # Perform update
        result = supabase.table("teams")\
            .update(update_data)\
            .eq("id", team["id"])\
            .execute()

        if not result.data:
            raise api_error(ApiErrorCode.DATABASE_ERROR, None, "update_team")

        # Return updated team (with user context)
        return await team_service.get_user_team(user_id)

    except HTTPException:
        raise
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "update_team")


@router.delete("/team", dependencies=_paid_team_deps)
@limiter.limit("5/minute")
async def delete_team(
    request: Request,
    purge_data: bool = Query(default=True),
    user_id: str = Depends(get_current_user),
):
    """
    Delete the entire team.

    **WARNING**: This is a destructive operation that will:
    - Remove all team members
    - Revoke all member access

    Only team owners can delete teams.
    By default, org-scoped data is purged before deleting the team.
    """
    supabase = get_supabase()

    try:
        # Get user's team and verify ownership
        team = await team_service.get_user_team(user_id)

        if not team:
            raise api_error_404("team")

        if not team.get("is_owner"):
            raise api_error_403("Only team owners can delete a team")

        team_id = team["id"]

        if purge_data:
            from services.cleanup import ActiveIngestionError, cleanup_service
            try:
                await cleanup_service.execute_org_deletion(team_id, owner_id=user_id)
            except ActiveIngestionError as exc:
                raise api_error(
                    ApiErrorCode.CONFLICT, exc, "delete_team",
                    status_code=status.HTTP_409_CONFLICT,
                )

        # Delete all team members first (respects FK constraints)
        supabase.table("team_members")\
            .delete()\
            .eq("team_id", team_id)\
            .execute()

        # Delete the team itself
        supabase.table("teams")\
            .delete()\
            .eq("id", team_id)\
            .execute()

        # Invalidate plan cache for the owner
        team_service.invalidate_plan_cache(user_id)

        return {"status": "success", "message": "Team deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "delete_team")


@router.get(
    "/team/effective-plan",
    response_model=EffectivePlanResponse,
    dependencies=[Depends(validate_team_access)]  # No require_paid_access - needed for paywall check
)
@limiter.limit("60/minute")
async def get_effective_plan(request: Request, user_id: str = Depends(get_current_user)):
    """
    Get the effective plan for the current user.

    This returns the plan inherited from the team owner,
    which determines feature access.

    NOTE: This endpoint is intentionally NOT behind require_paid_access
    so the frontend can fetch the plan to determine if paywall should be shown.
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


@router.get("/team/members", response_model=TeamMemberListResponse, dependencies=_paid_team_deps)
@limiter.limit("60/minute")
async def list_team_members(
    request: Request,
    user_id: str = Depends(get_current_user),
    role: str | None = None,
    status: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0
):
    """List team members with optional filters and server-side pagination."""
    supabase = get_supabase()

    try:
        query = supabase.table("team_members")\
            .select("*", count="exact")\
            .eq("owner_user_id", user_id)\
            .neq("status", "removed")\
            .order("created_at", desc=True)

        # Apply filters
        if role and role != "all":
            query = query.eq("role", role)
        if status and status != "all":
            query = query.eq("status", status)

        # Server-side search via Supabase .or_() with ilike
        if search:
            query = query.or_(
                f"name.ilike.%{search}%,"
                f"email.ilike.%{search}%"
            )

        query = query.range(offset, offset + limit - 1)

        response = query.execute()

        total = response.count or 0
        items = response.data or []

        return TeamMemberListResponse(
            items=items,
            total=total,
            has_more=(offset + limit) < total,
        )

    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "fetch_team_members")


@router.get("/team/stats", response_model=TeamStatsResponse, dependencies=_paid_team_deps)
@limiter.limit("60/minute")
async def get_team_stats(request: Request, user_id: str = Depends(get_current_user)):
    """Get team statistics with dynamic seat limits based on plan."""
    from core.quotas import get_plan_limits

    supabase = get_supabase()

    try:
        # Get user's effective plan for dynamic seat limits
        effective_plan = await team_service.get_effective_plan(user_id)
        plan_limits = get_plan_limits(effective_plan)

        response = supabase.table("team_members")\
            .select("status")\
            .eq("owner_user_id", user_id)\
            .execute()

        members = response.data or []

        active = sum(1 for m in members if m.get("status") == "active")
        pending = sum(1 for m in members if m.get("status") == "pending")
        suspended = sum(1 for m in members if m.get("status") == "suspended")

        return TeamStatsResponse(
            total_seats=plan_limits.max_team_seats,
            active_members=active,
            pending_invites=pending,
            suspended_members=suspended,
        )

    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "fetch_team_stats")


@router.post("/team/invite", response_model=InviteResponse, status_code=status.HTTP_201_CREATED, dependencies=_paid_team_deps)
@limiter.limit("20/minute")
async def invite_team_member(
    request: Request,
    payload: InviteRequest,
    background_tasks: BackgroundTasks,
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
            raise api_error_403(result.get("error", "Upgrade required"), code=ApiErrorCode.SUBSCRIPTION_REQUIRED)
        elif error_code == "ALREADY_EXISTS":
            raise api_error(ApiErrorCode.CONFLICT, status_code=409, operation="invite_member")
        elif error_code == "SEAT_LIMIT":
            raise api_error(ApiErrorCode.QUOTA_EXCEEDED, status_code=402, operation="invite_member")
        else:
            raise api_error_400(result.get("error", "Invite failed"))

    member_data = result.get("member")
    audit_logger.log(
        background_tasks, user_id=user_id, action="team.member_invite",
        resource_type="team", resource_id=member_data.get("id") if member_data else None,
        details={"email": str(payload.email), "role": payload.role.value},
        request=request,
    )

    return InviteResponse(
        success=True,
        member=member_data,
    )


@router.post("/team/bulk-invite", response_model=BulkInviteResponse, dependencies=_paid_team_deps)
@limiter.limit("5/minute")
async def bulk_invite_team_members(
    request: Request,
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
    # Read CSV content with size limit
    try:
        MAX_CSV_SIZE = 1 * 1024 * 1024  # 1 MB
        if file.size and file.size > MAX_CSV_SIZE:
            raise api_error_400("CSV file too large. Maximum size is 1MB.")
        content = await file.read(MAX_CSV_SIZE + 1)
        if len(content) > MAX_CSV_SIZE:
            raise api_error_400("CSV file too large. Maximum size is 1MB.")
        csv_content = content.decode("utf-8")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to read CSV: {e}")
        raise api_error_400("Unable to read CSV file. Please check the file format.")

    result = await team_service.bulk_invite_csv(
        owner_id=user_id,
        csv_content=csv_content
    )

    if not result.get("success") and result.get("code") == "UPGRADE_REQUIRED":
        raise api_error_403(result.get("error", "Upgrade required"), code=ApiErrorCode.SUBSCRIPTION_REQUIRED)

    return BulkInviteResponse(**result)


# Legacy endpoint for backward compatibility
@router.post("/team/members", response_model=TeamMemberResponse, status_code=status.HTTP_201_CREATED, dependencies=_paid_team_deps)
@limiter.limit("20/minute")
async def invite_team_member_legacy(
    request: Request,
    payload: TeamMemberCreate,
    background_tasks: BackgroundTasks,
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
            raise api_error_403(
                result.get("error", "Upgrade to Enterprise to invite team members"),
                code=ApiErrorCode.SUBSCRIPTION_REQUIRED,
            )
        elif error_code == "ALREADY_EXISTS":
            raise api_error(
                ApiErrorCode.CONFLICT, None, "invite_member",
                status_code=status.HTTP_409_CONFLICT,
            )
        else:
            raise api_error_400(result.get("error", "Invite failed"))

    # Return the member data in legacy format
    if result.get("member"):
        audit_logger.log(
            background_tasks, user_id=user_id, action="team.member_invite",
            resource_type="team", resource_id=result["member"].get("id"),
            details={"email": str(payload.email), "role": payload.role.value},
            request=request,
        )
        return result["member"]

    raise api_error(ApiErrorCode.INTERNAL_ERROR, None, "invite_member")


@router.patch("/team/members/{member_id}", response_model=TeamMemberResponse, dependencies=_paid_team_deps)
@limiter.limit("30/minute")
async def update_team_member(
    request: Request,
    member_id: str,
    payload: TeamMemberUpdate,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    """Update a team member's role or status."""
    supabase = get_supabase()

    # Role hierarchy: owner > admin > editor > viewer
    # Only owner can assign admin. Admins can only assign editor/viewer.
    ROLE_HIERARCHY = {"owner": 3, "admin": 2, "editor": 1, "viewer": 0}

    try:
        # Determine requester's role in the team
        requester_member = supabase.table("team_members")\
            .select("role, member_user_id")\
            .eq("member_user_id", user_id)\
            .eq("owner_user_id", user_id)\
            .eq("status", "active")\
            .limit(1)\
            .execute()

        # Check if requester is the team owner
        team = await team_service.get_user_team(user_id)
        is_owner = team and team.get("is_owner", False)
        requester_role = "owner" if is_owner else (
            requester_member.data[0].get("role", "viewer") if requester_member.data else "viewer"
        )

        # Build update data
        update_data = {}

        if payload.name is not None:
            update_data["name"] = payload.name

        if payload.role is not None:
            # Role escalation prevention
            target_role_level = ROLE_HIERARCHY.get(payload.role, 0)
            requester_role_level = ROLE_HIERARCHY.get(requester_role, 0)

            if target_role_level >= requester_role_level:
                raise api_error_403(
                    f"Cannot assign '{payload.role}' role. "
                    f"Only users with a higher role can grant this level."
                )

            # Last-admin protection: prevent demoting the last admin
            if payload.role != "admin":
                # Check if this member is currently an admin
                member_check = supabase.table("team_members")\
                    .select("role")\
                    .eq("id", member_id)\
                    .eq("owner_user_id", user_id)\
                    .execute()

                if member_check.data and member_check.data[0].get("role") == "admin":
                    # Count remaining active admins for this team owner
                    admin_count_response = supabase.table("team_members")\
                        .select("id", count="exact")\
                        .eq("owner_user_id", user_id)\
                        .eq("role", "admin")\
                        .eq("status", "active")\
                        .execute()

                    admin_count = admin_count_response.count or 0
                    if admin_count <= 1:
                        raise api_error_400("Cannot demote the last admin. Promote another member to admin first.")

            update_data["role"] = payload.role

        if payload.status is not None:
            if payload.status not in ["active", "pending", "suspended"]:
                raise api_error_400("Invalid status. Must be active, pending, or suspended.")

            # Last-admin protection: prevent suspending the last admin
            if payload.status in ["suspended", "pending"]:
                member_check = supabase.table("team_members")\
                    .select("role, status")\
                    .eq("id", member_id)\
                    .eq("owner_user_id", user_id)\
                    .execute()

                if (member_check.data and
                    member_check.data[0].get("role") == "admin" and
                    member_check.data[0].get("status") == "active"):
                    # Count remaining active admins
                    admin_count_response = supabase.table("team_members")\
                        .select("id", count="exact")\
                        .eq("owner_user_id", user_id)\
                        .eq("role", "admin")\
                        .eq("status", "active")\
                        .execute()

                    admin_count = admin_count_response.count or 0
                    if admin_count <= 1:
                        raise api_error_400("Cannot suspend the last admin. Promote another member to admin first.")

            update_data["status"] = payload.status

        if not update_data:
            raise api_error_400("No update fields provided")

        response = supabase.table("team_members")\
            .update(update_data)\
            .eq("id", member_id)\
            .eq("owner_user_id", user_id)\
            .execute()

        if response.data and len(response.data) > 0:
            updated = response.data[0]
            action = "team.member_role_change" if payload.role is not None else "team.member_status_change"
            audit_logger.log(
                background_tasks, user_id=user_id, action=action,
                resource_type="team", resource_id=member_id,
                details={"member_id": member_id, "changes": update_data},
                request=request,
            )
            return updated

        raise api_error_404("member", member_id)

    except HTTPException:
        raise
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "update_member")


@router.delete("/team/members/{member_id}", dependencies=_paid_team_deps)
@limiter.limit("20/minute")
async def remove_team_member(
    request: Request,
    member_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    """Remove a team member."""
    supabase = get_supabase()

    try:
        # Last-admin protection: check if we're removing the last admin
        member_check = supabase.table("team_members")\
            .select("role, status, member_user_id, email")\
            .eq("id", member_id)\
            .eq("owner_user_id", user_id)\
            .execute()

        if not member_check.data:
            raise api_error_404("member", member_id)

        member_data = member_check.data[0]

        # Prevent removing the team owner (themselves)
        if member_data.get("member_user_id") == user_id:
            raise api_error_400("Cannot remove yourself. Transfer ownership or delete the team instead.")

        # Prevent removing the last active admin
        if member_data.get("role") == "admin" and member_data.get("status") == "active":
            admin_count_response = supabase.table("team_members")\
                .select("id", count="exact")\
                .eq("owner_user_id", user_id)\
                .eq("role", "admin")\
                .eq("status", "active")\
                .execute()

            admin_count = admin_count_response.count or 0
            if admin_count <= 1:
                raise api_error_400("Cannot remove the last admin. Promote another member to admin first.")

        now = datetime.now(timezone.utc).isoformat()
        response = supabase.table("team_members")\
            .update({"status": "removed", "removed_at": now})\
            .eq("id", member_id)\
            .eq("owner_user_id", user_id)\
            .execute()

        if not response.data:
            raise api_error_404("member", member_id)

        audit_logger.log(
            background_tasks, user_id=user_id, action="team.member_remove",
            resource_type="team", resource_id=member_id,
            details={"email": member_data.get("email"), "role": member_data.get("role")},
            request=request,
        )

        # Invalidate removed member's plan cache
        removed_user_id = member_data.get("member_user_id")
        if removed_user_id:
            team_service.invalidate_plan_cache(removed_user_id)

        return {"status": "success", "id": member_id}

    except HTTPException:
        raise
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "remove_member")


@router.post("/team/members/{member_id}/resend", dependencies=_paid_team_deps)
@limiter.limit("10/minute")
async def resend_invitation(
    request: Request,
    member_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    """Resend invitation to a pending member."""
    # Delegate to service which handles logic and email
    result = await team_service.resend_invite(member_id, user_id)

    if not result.get("success"):
        # Map service errors to HTTP codes
        error = result.get("error", "Unknown error")
        if error == "Pending member not found":
            raise api_error_404("member", member_id)
        else:
            raise api_error(ApiErrorCode.INTERNAL_ERROR, None, "resend_invite")

    audit_logger.log(
        background_tasks, user_id=user_id, action="team.member_resend_invite",
        resource_type="team", resource_id=member_id,
        details={"member_id": member_id},
        request=request,
    )

    return {"status": "success", "message": "Invitation resent"}


@router.post("/team/decline")
@limiter.limit("10/minute")
async def decline_invite(
    request: Request,
    payload: DeclineInviteRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    """Decline a team invitation. The token is the member_id from the invite."""
    supabase = get_supabase()

    try:
        invite_response = supabase.table("team_members").select(
            "id, email, team_id, status"
        ).eq("id", payload.token).eq("status", "pending").execute()

        if not invite_response.data:
            raise api_error_404("invite")

        invite = invite_response.data[0]

        # Verify declining user's email matches the invite
        user_profile = supabase.table("user_profiles").select(
            "email"
        ).eq("user_id", user_id).single().execute()

        if not user_profile.data:
            raise api_error_403("Unable to verify your identity")

        declining_email = (user_profile.data.get("email") or "").lower().strip()
        invite_target = (invite.get("email") or "").lower().strip()

        if not declining_email or not invite_target or declining_email != invite_target:
            raise api_error_403(
                "This invitation was sent to a different email address."
            )

        now = datetime.now(timezone.utc).isoformat()
        supabase.table("team_members").update({
            "status": "removed",
            "removed_at": now
        }).eq("id", payload.token).execute()

        audit_logger.log(
            background_tasks, user_id=user_id, action="team.member_decline_invite",
            resource_type="team", resource_id=payload.token,
            details={"email": invite.get("email"), "team_id": invite.get("team_id")},
            request=request,
        )

        return {"status": "success", "message": "Invitation declined"}

    except HTTPException:
        raise
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "decline_invite")


@router.post("/team/accept", response_model=AcceptInviteResponse, dependencies=[Depends(validate_team_access)])
@limiter.limit("10/minute")
async def accept_invite(
    request: Request,
    payload: AcceptInviteRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Accept a team invitation.

    The token is the member_id from the invite URL.
    This endpoint:
    1. Validates the invite token (member_id)
    2. Updates the team_member record with the accepting user's ID
    3. Sets status to 'active' and records joined_at
    4. Invalidates plan cache for the user
    """
    supabase = get_supabase()

    try:
        # Step 1: Find the pending invite by token (which is the member_id)
        invite_response = supabase.table("team_members").select(
            "id, team_id, email, status, expires_at, teams(id, name)"
        ).eq("id", payload.token).eq("status", "pending").execute()

        if not invite_response.data or len(invite_response.data) == 0:
            raise api_error_404("invite")

        invite = invite_response.data[0]
        invite_email = invite.get("email")
        team_info = invite.get("teams", {})
        team_name = team_info.get("name", "Team")
        team_id = invite.get("team_id")

        # Step 2: Verify accepting user's email matches the invite
        user_profile = supabase.table("user_profiles").select(
            "email"
        ).eq("user_id", user_id).single().execute()

        if not user_profile.data:
            raise api_error_403("Unable to verify your identity")

        accepting_email = (user_profile.data.get("email") or "").lower().strip()
        invite_target = (invite_email or "").lower().strip()

        if not accepting_email or not invite_target or accepting_email != invite_target:
            logger.warning(
                f"[AcceptInvite] Email mismatch: user {user_id[:8]}... "
                f"tried to accept invite for {invite_target}"
            )
            raise api_error_403(
                "This invitation was sent to a different email address. "
                "Please sign in with the correct account."
            )

        # Step 3: Check invite expiry — fail-closed (reject if unparseable)
        expires_at_str = invite.get("expires_at")
        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) > expires_at:
                    raise HTTPException(
                        status_code=410,
                        detail="This invitation has expired. Please ask the team admin to resend it."
                    )
            except (ValueError, TypeError):
                logger.error(f"[AcceptInvite] Unparseable expires_at '{expires_at_str}' for invite {payload.token}")
                raise HTTPException(
                    status_code=410,
                    detail="This invitation has expired. Please ask the team admin to resend it."
                )

        # Step 4: Update the member record - link to accepting user
        now = datetime.now(timezone.utc).isoformat()

        update_response = supabase.table("team_members").update({
            "member_user_id": user_id,
            "status": "active",
            "joined_at": now
        }).eq("id", payload.token).execute()

        if not update_response.data:
            raise api_error(ApiErrorCode.DATABASE_ERROR, None, "accept_invite")

        # Step 3: Invalidate plan cache for the new member
        team_service.invalidate_plan_cache(user_id)

        return AcceptInviteResponse(
            success=True,
            team_name=team_name,
            team_id=team_id
        )

    except HTTPException:
        raise
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "accept_invite")
