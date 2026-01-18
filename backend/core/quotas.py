"""
Plan Limits and Quota Definitions

This module defines plan limits and provides utilities for checking plans.
Actual quota enforcement is handled by services/quotas.py (check_admission).
"""

from core.config import settings
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

class PlanLimits(BaseModel):
    plan_name: str
    max_files: int
    max_storage_bytes: int
    max_scopes: int
    max_llm_tokens: int
    max_team_seats: int = 1
    allow_web_crawl: bool = False
    model_tier: str = "standard" # standard, hybrid, premium
    
    # Silence Pydantic warning about "model_" prefix
    model_config = {"protected_namespaces": ()}

    @property
    def max_storage_mb(self):
        return self.max_storage_bytes / (1024 * 1024)

# Define Plans using Settings
QUOTA_LIMITS = {
    "free": PlanLimits(
        plan_name="free",
        max_files=0,
        max_storage_bytes=0,
        max_scopes=0,
        max_llm_tokens=0,
        max_team_seats=1,
        allow_web_crawl=False,
        model_tier="standard",
    ),
    "starter": PlanLimits(
        plan_name="starter",
        max_files=settings.LIMITS_STARTER_FILES,
        max_storage_bytes=settings.LIMITS_STARTER_MB * 1024 * 1024,
        max_scopes=settings.LIMITS_STARTER_SCOPES,
        max_llm_tokens=settings.LIMITS_STARTER_LLM_TOKENS,
        max_team_seats=1,
        allow_web_crawl=True,
        model_tier="standard"
    ),
    "pro": PlanLimits(
        plan_name="pro",
        max_files=settings.LIMITS_PRO_FILES,
        max_storage_bytes=settings.LIMITS_PRO_MB * 1024 * 1024,
        max_scopes=settings.LIMITS_PRO_SCOPES,
        max_llm_tokens=settings.LIMITS_PRO_LLM_TOKENS,
        max_team_seats=5,
        allow_web_crawl=True,
        model_tier="premium"
    ),
    "enterprise": PlanLimits(
        plan_name="enterprise",
        max_files=100000,
        max_storage_bytes=1024 * 1024 * 1024 * 1024, # 1TB
        max_scopes=settings.LIMITS_ENTERPRISE_SCOPES,
        max_llm_tokens=settings.LIMITS_ENTERPRISE_LLM_TOKENS,
        max_team_seats=100,
        allow_web_crawl=True,
        model_tier="premium"
    )
}

def get_plan_limits(plan_name: str) -> PlanLimits:
    return QUOTA_LIMITS.get(plan_name, QUOTA_LIMITS["free"])

def format_bytes(size: int) -> str:
    power = 2**10
    n = 0
    power_labels = {0 : '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return f"{size:.1f} {power_labels[n]}B"


# NOTE: Quota enforcement is handled by services/quotas.py using check_admission()
# which provides organization-based admission control with the org_usage table.
