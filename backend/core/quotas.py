"""
Quota Configuration for Plan Limits

Defines the limits for each subscription plan tier.
Used by the usage service to enforce quotas.
"""

from enum import Enum
from pydantic import BaseModel
from typing import Dict


class ModelTier(str, Enum):
    """
    AI model tier access levels.
    
    BASIC: Access to cost-effective models only (e.g., Llama-3)
    HYBRID: Smart router decides between models (Llama + GPT-4o)
    PREMIUM: Priority access to premium models (GPT-4o first)
    """
    BASIC = "basic"
    HYBRID = "hybrid"
    PREMIUM = "premium"


class PlanLimits(BaseModel):
    """
    Defines the resource limits for a subscription plan.
    
    Attributes:
        max_files: Maximum number of documents/files allowed
        max_storage_bytes: Maximum total storage in bytes
        max_team_seats: Maximum team members (1 = solo plan)
        allow_web_crawl: Whether web crawling feature is enabled
        model_tier: AI model access tier
    """
    max_files: int
    max_storage_bytes: int
    max_team_seats: int
    allow_web_crawl: bool
    model_tier: ModelTier


# ==============================================================================
# PLAN DEFINITIONS
# ==============================================================================
# These are the canonical limits for each subscription tier.
# Changes here affect quota enforcement across the entire application.

PLANS: Dict[str, PlanLimits] = {
    "free": PlanLimits(
        max_files=5,
        max_storage_bytes=50 * 1024 * 1024,  # 50 MB
        max_team_seats=1,
        allow_web_crawl=False,
        model_tier=ModelTier.BASIC
    ),
    "starter": PlanLimits(
        max_files=20,
        max_storage_bytes=200 * 1024 * 1024,  # 200 MB
        max_team_seats=1,
        allow_web_crawl=False,
        model_tier=ModelTier.BASIC
    ),
    "pro": PlanLimits(
        max_files=500,
        max_storage_bytes=2 * 1024 * 1024 * 1024,  # 2 GB
        max_team_seats=1,
        allow_web_crawl=True,
        model_tier=ModelTier.HYBRID
    ),
    "enterprise": PlanLimits(
        max_files=100000,
        max_storage_bytes=100 * 1024 * 1024 * 1024,  # 100 GB
        max_team_seats=9999,
        allow_web_crawl=True,
        model_tier=ModelTier.PREMIUM
    )
}


def get_plan_limits(plan_name: str) -> PlanLimits:
    """
    Get the limits for a specific plan.
    
    Args:
        plan_name: The plan identifier (free, starter, pro, enterprise)
        
    Returns:
        PlanLimits for the specified plan
        
    Raises:
        ValueError: If the plan name is not recognized
    """
    if plan_name not in PLANS:
        raise ValueError(f"Unknown plan: {plan_name}. Valid plans: {list(PLANS.keys())}")
    return PLANS[plan_name]


def format_bytes(size_bytes: int) -> str:
    """
    Format bytes into human-readable string.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Human-readable string (e.g., "50 MB", "2 GB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.0f} {unit}" if size_bytes == int(size_bytes) else f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def get_plan_display_info(plan_name: str) -> dict:
    """
    Get display-friendly information about a plan's limits.
    
    Args:
        plan_name: The plan identifier
        
    Returns:
        Dictionary with human-readable limit descriptions
    """
    limits = get_plan_limits(plan_name)
    return {
        "plan": plan_name,
        "max_files": limits.max_files,
        "max_storage": format_bytes(limits.max_storage_bytes),
        "max_storage_bytes": limits.max_storage_bytes,
        "max_team_seats": limits.max_team_seats,
        "web_crawl_enabled": limits.allow_web_crawl,
        "model_tier": limits.model_tier.value
    }
