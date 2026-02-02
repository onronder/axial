"""
FastAPI Dependencies for Access Control

Provides reusable dependencies for protecting endpoints with
subscription status and team access validation.
"""

import logging
from fastapi import Depends, HTTPException, status
from core.security import get_current_user
from core.db import get_supabase
from services.team_service import team_service

logger = logging.getLogger(__name__)


async def validate_team_access(user_id: str = Depends(get_current_user)) -> str:
    """
    Dependency to validate team access before allowing endpoint access.
    
    Checks:
    1. User's team membership status
    2. Owner's subscription status
    3. Owner's plan allows team members
    
    If user is blocked (owner downgraded or subscription inactive),
    raises 403 Forbidden.
    
    Usage:
        @router.post("/endpoint")
        async def endpoint(user_id: str = Depends(validate_team_access)):
            ...
    
    Returns:
        user_id if access is allowed
        
    Raises:
        HTTPException(403): If team access is blocked
    """
    access = await team_service.verify_team_access(user_id)
    
    if not access.get("allowed", False):
        reason = access.get("reason", "unknown")
        message = access.get("message", "Access denied")
        
        logger.warning(
            f"[Dependencies] Access denied for user {user_id[:8]}...: {reason}"
        )
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "TEAM_ACCESS_DENIED",
                "reason": reason,
                "message": message
            }
        )
    
    return user_id


async def get_effective_plan(user_id: str = Depends(get_current_user)) -> str:
    """
    Dependency to get user's effective plan.
    
    Returns the plan inherited from team owner, with
    subscription status enforcement.
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(plan: str = Depends(get_effective_plan)):
            ...
    """
    return await team_service.get_effective_plan(user_id)


async def require_plan(required_plans: list[str]):
    """
    Factory for creating plan requirement dependencies.
    
    Usage:
        @router.post("/endpoint", dependencies=[Depends(require_plan(["pro", "enterprise"]))])
        async def endpoint():
            ...
    """
    async def checker(plan: str = Depends(get_effective_plan)):
        if plan not in required_plans:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "PLAN_REQUIRED",
                    "current_plan": plan,
                    "required_plans": required_plans,
                    "message": f"This feature requires one of: {', '.join(required_plans)}"
                }
            )
        return plan
    return checker


async def require_paid_access(user_id: str = Depends(validate_team_access)) -> str:
    """
    Require an active paid plan.

    Blocks users with 'none' or 'free' plans from core application endpoints.
    These users should see the paywall and subscribe via Polar.
    
    Plan hierarchy:
    - 'none': New users who haven't selected a plan yet (shows paywall)
    - 'free': Users after trial ends or subscription cancellation (shows paywall)
    - 'starter', 'pro', 'enterprise': Paid plans with full access
    
    Allowed endpoints for free/none users:
    - /billing/* (to subscribe)
    - /usage (to see current status)
    - /team/effective-plan (for frontend paywall logic)
    - /settings (profile management)
    """
    try:
        plan = await team_service.get_effective_plan(user_id)
    except Exception as exc:
        logger.warning("[Dependencies] Failed to resolve plan for %s: %s", user_id[:8], exc)
        plan = "none"

    plan_lower = plan.lower() if plan else "none"
    
    # Block both 'none' (new users) and 'free' (post-trial/canceled users)
    if plan_lower in ("none", "free"):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "SUBSCRIPTION_REQUIRED",
                "message": "An active subscription is required to access this resource.",
                "current_plan": plan_lower,
            },
        )
    return user_id


async def require_admin(user_id: str = Depends(validate_team_access)) -> str:
    """
    Dependency to require admin privileges.
    
    Checks if the user has admin role in their team or is a system admin.
    
    Usage:
        @router.post("/admin-only")
        async def admin_endpoint(user_id: str = Depends(require_admin)):
            ...
    
    Returns:
        user_id if admin access is granted
        
    Raises:
        HTTPException(403): If user is not an admin
    """
    try:
        supabase = get_supabase()
        
        # Check if user is a team owner (owners are admins of their team)
        result = supabase.table("teams").select("id, owner_id").eq("owner_id", user_id).execute()
        
        if result.data and len(result.data) > 0:
            return user_id  # User is a team owner, grant admin access
        
        # Check if user has admin role in team_members
        member_result = (
            supabase.table("team_members")
            .select("role")
            .eq("member_user_id", user_id)
            .eq("role", "admin")
            .execute()
        )
        
        if member_result.data and len(member_result.data) > 0:
            return user_id  # User has admin role
        
        # If neither, deny access
        logger.warning(f"[require_admin] Admin access denied for user {user_id[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "ADMIN_REQUIRED",
                "message": "This endpoint requires admin privileges"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[require_admin] Error checking admin status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify admin status"
        )


async def require_editor(user_id: str = Depends(validate_team_access)) -> str:
    """
    Require an editor or admin role (team owner counts as admin).
    
    Blocks viewers from performing write actions while allowing
    solo users and team owners/admins.
    """
    try:
        team = await team_service.get_user_team(user_id)

        # Solo users (no team) are allowed
        if not team:
            return user_id

        if team.get("is_owner"):
            return user_id

        role = team.get("user_role", "viewer")
        if role not in ["admin", "editor"]:
            logger.warning(
                f"[require_editor] Write access denied for user {user_id[:8]}... (role={role})"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "EDITOR_REQUIRED",
                    "message": "You need editor or admin access to perform this action.",
                },
            )

        return user_id

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[require_editor] Error checking role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify permissions",
        )


async def get_user_organization_id(user_id: str = Depends(validate_team_access)) -> str:
    """
    Get the user's organization_id (team_id).
    
    This is the canonical way to get the organization context for org-scoped
    queries. Falls back to user_id if user has no team (solo user).
    
    Usage:
        @router.get("/documents")
        async def list_docs(org_id: str = Depends(get_user_organization_id)):
            # Query by org_id instead of user_id
            ...
    
    Returns:
        organization_id (team_id) if user has a team, otherwise user_id
    """
    try:
        team = await team_service.get_user_team(user_id)
        if team and team.get("id"):
            return str(team["id"])
        
        # For solo users (no team), use user_id as organization_id
        # This maintains compatibility for users before team feature
        return user_id
        
    except Exception as e:
        logger.warning(f"[get_user_organization_id] Failed for {user_id[:8]}...: {e}")
        # Fail open - use user_id
        return user_id


# Re-export get_current_user for convenience
__all__ = [
    'get_current_user',
    'validate_team_access',
    'get_effective_plan',
    'require_plan',
    'require_paid_access',
    'require_admin',
    'require_editor',
    'get_user_organization_id',
]
