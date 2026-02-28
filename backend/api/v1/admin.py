"""
Admin API Router

Endpoints for administrative functions including audit logs.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from api.v1.dependencies import require_admin, require_paid_access, validate_team_access
from api.v1.error_utils import ApiErrorCode, api_error
from core.db import get_supabase
from core.rate_limit import limiter
from core.security import get_current_user
from services.team_service import team_service

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(validate_team_access), Depends(require_paid_access)])

# Separate router for user-accessible (non-admin) endpoints
user_router = APIRouter(dependencies=[Depends(validate_team_access), Depends(require_paid_access)])


# =============================================================================
# Response Models
# =============================================================================

class AuditLogEntry(BaseModel):
    """Response model for audit log entries."""
    id: str
    user_id: str | None = None
    user_email: str | None = None
    user_name: str | None = None
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    details: dict = {}
    ip_address: str | None = None
    created_at: str


class AuditLogListResponse(BaseModel):
    """Paginated audit log response."""
    items: list[AuditLogEntry]
    total: int
    has_more: bool


# =============================================================================
# Audit Log Endpoints
# =============================================================================

@router.get("/audit-logs", response_model=AuditLogListResponse)
@limiter.limit("30/minute")
async def get_audit_logs(
    request: Request,
    user_id: str = Depends(require_admin),
    limit: int = Query(default=50, le=10000),
    offset: int = Query(default=0, ge=0),
    action: str | None = None,
    resource_type: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    search: str | None = None,
):
    """
    Get audit logs for the user's team/account.

    Filters:
    - action: Filter by action type (e.g., 'document.delete')
    - resource_type: Filter by resource (e.g., 'document', 'chat')
    - from_date: ISO date string for start of range
    - to_date: ISO date string for end of range

    Only team owners/admins can view audit logs.
    Returns logs for ALL team members (organization-scoped).
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

        # Get all team member user_ids for organization-scoped audit logs
        team_member_ids = [user_id]  # Default to current user
        if team and team.get("id"):
            team_id = team["id"]
            members_response = supabase.table("team_members")\
                .select("member_user_id")\
                .eq("team_id", team_id)\
                .neq("status", "removed")\
                .execute()
            if members_response.data:
                team_member_ids = [m["member_user_id"] for m in members_response.data if m.get("member_user_id")]

        # Build query - filter by all organization members
        query = supabase.table("audit_logs")\
            .select("*", count="exact")\
            .in_("user_id", team_member_ids)

        # Apply filters
        if action:
            query = query.eq("action", action)
        if resource_type:
            query = query.eq("resource_type", resource_type)
        if from_date:
            query = query.gte("created_at", from_date)
        if to_date:
            query = query.lte("created_at", to_date)

        # Apply search filter at DB level (before pagination)
        if search:
            query = query.or_(
                f"action.ilike.%{search}%,"
                f"resource_type.ilike.%{search}%,"
                f"resource_id.ilike.%{search}%"
            )

        # Execute with pagination
        result = query\
            .order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()

        total = result.count if result.count is not None else 0

        # Fetch user profiles for display names
        user_ids = list(set(
            log.get("user_id") for log in (result.data or [])
            if log.get("user_id")
        ))

        user_profiles: dict = {}
        if user_ids:
            try:
                profiles_response = supabase.table("user_profiles")\
                    .select("user_id, email, first_name, last_name")\
                    .in_("user_id", user_ids)\
                    .execute()
                for profile in (profiles_response.data or []):
                    user_profiles[profile["user_id"]] = {
                        "email": profile.get("email"),
                        "name": " ".join(filter(None, [
                            profile.get("first_name"),
                            profile.get("last_name")
                        ])) or None
                    }
            except Exception as profile_error:
                logger.warning(f"Failed to fetch user profiles: {profile_error}")

        # Build response items with user info
        items = []
        for log in (result.data or []):
            user_info = user_profiles.get(log.get("user_id"), {})
            items.append(AuditLogEntry(
                id=log["id"],
                user_id=log.get("user_id"),
                user_email=user_info.get("email"),
                user_name=user_info.get("name"),
                action=log["action"],
                resource_type=log.get("resource_type"),
                resource_id=log.get("resource_id"),
                details=log.get("details", {}),
                ip_address=log.get("ip_address"),
                created_at=log["created_at"]
            ))

        return AuditLogListResponse(
            items=items,
            total=total,
            has_more=(offset + limit) < total
        )

    except HTTPException:
        raise
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "fetch_audit_logs")


@router.get("/audit-logs/actions")
@limiter.limit("30/minute")
async def get_audit_log_actions(
    request: Request,
    user_id: str = Depends(require_admin)
):
    """
    Get list of distinct action types in audit logs.

    Useful for populating filter dropdowns in the UI.
    Returns actions actually present in the database plus known action types.
    """
    supabase = get_supabase()

    # Known actions (superset) — always included so filters show even before first event
    KNOWN_ACTIONS = [
        "document.create", "document.update", "document.delete", "document.wipe",
        "chat.create", "chat.delete",
        "connector.create", "connector.update", "connector.delete",
        "connector.connect", "connector.disconnect",
        "connector.sync_start", "connector.sync_success", "connector.sync_fail",
        "scope.create", "scope.update", "scope.delete", "scope.wipe",
        "ingestion.queued", "ingestion.started", "ingestion.completed",
        "ingestion.failed", "ingestion.skipped", "ingestion.timeout",
        "chunk.purge", "organization.purge",
        "security.document_wiped", "security.scope_deleted",
        "security.chunk_purged", "security.organization_purged",
        "security.ghost_protocol_activated", "security.ghost_protocol_completed",
        "settings.update", "settings.configure",
        "team.create", "team.update", "team.member_invite", "team.member_remove",
        "team.member_role_change", "team.member_status_change", "team.member_resend_invite",
        "team.member_decline_invite",
        "approval.request", "approval.approve", "approval.reject",
        "approval.execute", "approval.approval_requested",
        "consent.granted", "consent.revoked", "consent.updated",
        "gdpr.anonymization_requested", "gdpr.anonymization_completed",
        "gdpr.data_export_requested", "gdpr.data_export_completed",
        "gdpr.deletion_requested", "gdpr.deletion_completed",
        "compliance.audit_requested", "compliance.audit_completed",
        "mcp.api_key_created", "mcp.api_key_rotated", "mcp.api_key_revoked",
        "safety.content_flagged", "safety.content_blocked",
    ]

    try:
        # Merge known actions with any new ones from DB
        result = supabase.rpc("get_distinct_audit_actions", {}).execute()
        db_actions = result.data if result.data else []
        all_actions = sorted(set(KNOWN_ACTIONS) | set(db_actions))
    except Exception:
        # Fallback to known actions if RPC doesn't exist
        all_actions = sorted(KNOWN_ACTIONS)

    return {"actions": all_actions}


# =============================================================================
# Security Log Endpoints (Ghost Protocol)
# =============================================================================

class SecurityEventEntry(BaseModel):
    """Response model for security/wipe events."""
    id: str
    event_type: str
    resource_type: str
    resource_name: str
    resource_id: str
    wipe_pattern: str | None = None
    wipe_verified: bool = False
    performed_by: str
    performed_at: str
    duration_ms: int = 0


class SecurityLogResponse(BaseModel):
    """Paginated security log response."""
    items: list[SecurityEventEntry]
    total: int
    has_more: bool


# SYNC WARNING: This list must be manually updated when new security-related
# audit actions are added. For dynamic list, query: SELECT DISTINCT action FROM audit_logs
# WHERE action LIKE '%.wipe' OR action LIKE '%.delete' OR action LIKE '%.purge'
SECURITY_ACTIONS = [
    # Initiation events (logged when user triggers wipe)
    "document.wipe",
    "scope.wipe",
    # Completion events (logged by Ghost Protocol after wipe finishes)
    "security.document_wiped",
    "security.scope_deleted",
    "security.chunk_purged",
    "security.organization_purged",
    # Legacy action names
    "scope.delete",
    "chunk.purge",
    "organization.purge",
]


@router.get("/security-log", response_model=SecurityLogResponse)
@limiter.limit("30/minute")
async def get_security_log(
    request: Request,
    user_id: str = Depends(require_admin),
    limit: int = Query(default=50, le=10000),
    offset: int = Query(default=0, ge=0),
    event_type: str | None = None,
    search: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None
):
    """
    Get security-related audit logs (wipes, deletions, purges).

    Filters by Ghost Protocol actions:
    - document_wiped: DoD 5220.22-M compliant document wipe
    - scope_deleted: Entire scope deletion with cascade wipe
    - chunk_purged: Vector chunk purge
    - organization_purged: Full organization data purge

    Only team admins can view security logs.
    Returns logs for ALL team members (organization-scoped).
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
                    detail="Only team owners and admins can view security logs"
                )

        # Get all team member user_ids for organization-scoped security logs
        team_member_ids = [user_id]  # Default to current user
        if team and team.get("id"):
            team_id = team["id"]
            members_response = supabase.table("team_members")\
                .select("member_user_id")\
                .eq("team_id", team_id)\
                .neq("status", "removed")\
                .execute()
            if members_response.data:
                team_member_ids = [m["member_user_id"] for m in members_response.data if m.get("member_user_id")]

        # Build query - filter to security actions for all organization members
        query = supabase.table("audit_logs")\
            .select("*", count="exact")\
            .in_("user_id", team_member_ids)\
            .in_("action", SECURITY_ACTIONS)

        # Apply event type filter
        if event_type:
            # Map frontend event types to ALL matching audit action names
            action_map = {
                "document_wiped": ["document.wipe", "security.document_wiped"],
                "scope_deleted": ["scope.delete", "scope.wipe", "security.scope_deleted"],
                "chunk_purged": ["chunk.purge", "security.chunk_purged"],
                "organization_purged": ["organization.purge", "security.organization_purged"],
            }
            mapped_actions = action_map.get(event_type)
            if mapped_actions:
                query = query.in_("action", mapped_actions)
            else:
                query = query.eq("action", event_type)

        # Apply date filters
        if from_date:
            query = query.gte("created_at", from_date)
        if to_date:
            query = query.lte("created_at", to_date)

        # Apply search filter at DB level (Bug 2 fix: before pagination)
        if search:
            query = query.or_(
                f"details->>resource_name.ilike.%{search}%,"
                f"resource_id.ilike.%{search}%"
            )

        # Execute with pagination
        result = query\
            .order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()

        total = result.count if result.count is not None else 0

        # Transform to security event format
        event_type_map = {
            "document.wipe": "document_wiped",
            "security.document_wiped": "document_wiped",
            "scope.delete": "scope_deleted",
            "scope.wipe": "scope_deleted",
            "security.scope_deleted": "scope_deleted",
            "chunk.purge": "chunk_purged",
            "security.chunk_purged": "chunk_purged",
            "organization.purge": "organization_purged",
            "security.organization_purged": "organization_purged",
        }

        items = []
        for log in (result.data or []):
            details = log.get("details", {})
            resource_name = details.get("resource_name", log.get("resource_id", "Unknown"))

            items.append(SecurityEventEntry(
                id=log["id"],
                event_type=event_type_map.get(log["action"], log["action"]),
                resource_type=log.get("resource_type", "document"),
                resource_name=resource_name,
                resource_id=log.get("resource_id", ""),
                wipe_pattern=details.get("wipe_pattern"),
                wipe_verified=details.get("wipe_verified", False),
                performed_by=log.get("user_id", "system"),
                performed_at=log["created_at"],
                duration_ms=details.get("duration_ms", 0),
            ))

        return SecurityLogResponse(
            items=items,
            total=total,
            has_more=(offset + limit) < total
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin] Security log fetch error: {e}")
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "fetch_security_log")


# =============================================================================
# User Audit Trail (Non-Admin)
# =============================================================================

@user_router.get("/audit-logs/me", response_model=AuditLogListResponse)
@limiter.limit("30/minute")
async def get_my_audit_logs(
    request: Request,
    user_id: str = Depends(get_current_user),
    limit: int = Query(default=50, le=1000),
    offset: int = Query(default=0, ge=0),
    action: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
):
    """
    Get the requesting user's own audit trail.

    Unlike /audit-logs (admin-only), this endpoint returns only actions
    performed BY or ON the requesting user. Supports GDPR transparency
    requirements by allowing users to see who accessed their data.
    """
    supabase = get_supabase()

    try:
        query = supabase.table("audit_logs")\
            .select("*", count="exact")\
            .eq("user_id", user_id)

        if action:
            query = query.eq("action", action)
        if from_date:
            query = query.gte("created_at", from_date)
        if to_date:
            query = query.lte("created_at", to_date)

        result = query\
            .order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()

        total = result.count if result.count is not None else 0

        items = []
        for log in (result.data or []):
            items.append(AuditLogEntry(
                id=log["id"],
                user_id=log.get("user_id"),
                user_email=None,
                user_name=None,
                action=log["action"],
                resource_type=log.get("resource_type"),
                resource_id=log.get("resource_id"),
                details=log.get("details", {}),
                ip_address=log.get("ip_address"),
                created_at=log["created_at"]
            ))

        return AuditLogListResponse(
            items=items,
            total=total,
            has_more=(offset + limit) < total
        )

    except HTTPException:
        raise
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "fetch_my_audit_logs")
