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


async def require_admin(user_id: str = Depends(get_current_user)) -> str:
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
        member_result = supabase.table("team_members").select("role").eq("user_id", user_id).eq("role", "admin").execute()
        
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


# Re-export get_current_user for convenience
__all__ = [
    'get_current_user',
    'validate_team_access',
    'get_effective_plan',
    'require_plan',
    'require_admin',
]
