"""
FastAPI Dependencies for Access Control

Provides reusable dependencies for protecting endpoints with
subscription status and team access validation.
"""

import logging
from fastapi import Depends, HTTPException, status
from core.security import get_current_user
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
