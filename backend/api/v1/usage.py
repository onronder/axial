"""
Usage API Endpoint

Provides usage statistics for the frontend to display progress bars
and quota information.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

from core.security import get_current_user
from services.usage import get_user_usage_with_limits
from core.quotas import get_plan_display_info, PLANS

import logging

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================
# RESPONSE MODELS
# ============================================================

class UsageCount(BaseModel):
    """Usage count with limit."""
    used: int
    limit: int
    percent: float  # 0-100


class StorageUsage(BaseModel):
    """Storage usage with limit."""
    used_bytes: int
    used_display: str  # e.g., "48 MB"
    limit_bytes: int
    limit_display: str  # e.g., "50 MB"
    percent: float  # 0-100


class FeatureAccess(BaseModel):
    """Feature access flags based on plan."""
    web_crawl: bool
    team: bool
    premium_models: bool


class UsageResponse(BaseModel):
    """
    Complete usage response for frontend display.
    
    Example:
    {
        "plan": "free",
        "files": {"used": 4, "limit": 5, "percent": 80.0},
        "storage": {
            "used_bytes": 45000000,
            "used_display": "45 MB",
            "limit_bytes": 52428800,
            "limit_display": "50 MB",
            "percent": 85.8
        },
        "features": {
            "web_crawl": false,
            "team": false,
            "premium_models": false
        },
        "model_tier": "basic"
    }
    """
    plan: str
    files: UsageCount
    storage: StorageUsage
    features: FeatureAccess
    model_tier: str
    subscription_status: str


class PlansResponse(BaseModel):
    """List of available plans with limits."""
    plans: dict


# ============================================================
# ENDPOINTS
# ============================================================

@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    user_id: str = Depends(get_current_user)
):
    """
    Get current usage statistics for the authenticated user.
    
    Returns file count, storage usage, and feature access
    based on the user's current plan.
    """
    try:
        usage_with_limits = await get_user_usage_with_limits(UUID(user_id))
        usage = usage_with_limits.usage
        limits = usage_with_limits.limits
        
        # Calculate percentages (capped at 100)
        files_percent = min(100.0, (usage.files / limits.max_files * 100)) if limits.max_files > 0 else 0.0
        storage_percent = min(100.0, (usage.storage_bytes / limits.max_storage_bytes * 100)) if limits.max_storage_bytes > 0 else 0.0
        
        return UsageResponse(
            plan=usage.plan,
            files=UsageCount(
                used=usage.files,
                limit=limits.max_files,
                percent=round(files_percent, 1)
            ),
            storage=StorageUsage(
                used_bytes=usage.storage_bytes,
                used_display=usage.storage_display,
                limit_bytes=limits.max_storage_bytes,
                limit_display=_format_bytes(limits.max_storage_bytes),
                percent=round(storage_percent, 1)
            ),
            features=FeatureAccess(
                web_crawl=limits.allow_web_crawl,
                team=limits.max_team_seats > 1,
                premium_models=limits.model_tier.value in ["hybrid", "premium"]
            ),
            model_tier=limits.model_tier.value,
            subscription_status=usage.subscription_status
        )
        
    except Exception as e:
        logger.error(f"Failed to get usage: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch usage: {str(e)}")


@router.get("/plans", response_model=PlansResponse)
async def get_plans():
    """
    Get available plans and their limits (public endpoint).
    
    Returns all plan definitions for pricing page display.
    """
    plans_info = {}
    for plan_name in PLANS.keys():
        plans_info[plan_name] = get_plan_display_info(plan_name)
    
    return PlansResponse(plans=plans_info)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _format_bytes(size_bytes: int) -> str:
    """Format bytes into human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.0f} {unit}" if size_bytes == int(size_bytes) else f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"
