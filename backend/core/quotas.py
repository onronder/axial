from core.config import settings
from core.db import get_supabase
from fastapi import HTTPException
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

class PlanLimits(BaseModel):
    plan_name: str
    max_files: int
    max_storage_bytes: int
    max_team_seats: int = 1
    allow_web_crawl: bool = False
    model_tier: str = "standard" # standard, hybrid, premium

    @property
    def max_storage_mb(self):
        return self.max_storage_bytes / (1024 * 1024)

# Define Plans using Settings
QUOTA_LIMITS = {
    "free": PlanLimits(
        plan_name="free",
        max_files=settings.LIMITS_STARTER_FILES,
        max_storage_bytes=settings.LIMITS_STARTER_MB * 1024 * 1024,
        max_team_seats=1,
        allow_web_crawl=False,
        model_tier="standard"
    ),
    "starter": PlanLimits(
        plan_name="starter",
        max_files=settings.LIMITS_STARTER_FILES,
        max_storage_bytes=settings.LIMITS_STARTER_MB * 1024 * 1024,
        max_team_seats=1,
        allow_web_crawl=False,
        model_tier="standard"
    ),
    "pro": PlanLimits(
        plan_name="pro",
        max_files=settings.LIMITS_PRO_FILES,
        max_storage_bytes=settings.LIMITS_PRO_MB * 1024 * 1024,
        max_team_seats=5,
        allow_web_crawl=True,
        model_tier="premium"
    ),
    "enterprise": PlanLimits(
        plan_name="enterprise",
        max_files=100000,
        max_storage_bytes=1024 * 1024 * 1024 * 1024, # 1TB
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

async def check_quota(user_id: str, resource_type: str = "files"):
    """
    Check if user has exceeded their resource quota based on plan.
    Raises HTTPException(402) if quota exceeded.
    
    Args:
        user_id: User UUID
        resource_type: 'files' (count) or 'storage' (size - future impl)
    """
    supabase = get_supabase()
    
    # 1. Get User Plan
    try:
        profile = supabase.table("user_profiles").select("plan").eq("user_id", user_id).single().execute()
        user_plan = profile.data.get("plan", "free")
    except Exception as e:
        logger.warning(f"⚠️ [Quotas] Could not fetch plan for {user_id}, defaulting to 'free': {e}")
        user_plan = "free"
        
    # 2. Determine Limits
    limit = 0
    if user_plan == "free" or user_plan == "starter":
        limit = settings.LIMITS_STARTER_FILES
    elif user_plan == "pro":
        limit = settings.LIMITS_PRO_FILES
    elif user_plan == "enterprise":
        return  # Unlimited
        
    # 3. Check Usage
    if resource_type == "files":
        try:
            # Count user's files
            response = supabase.table("user_documents").select("id", count="exact").eq("user_id", user_id).execute()
            current_count = response.count
            
            logger.info(f"📊 [Quotas] User {user_id} ({user_plan}) Usage: {current_count}/{limit} files")
            
            if current_count >= limit:
                raise HTTPException(
                    status_code=402, 
                    detail=settings.MSG_UPSELL_FILES
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ [Quotas] Failed to check usage: {e}")
            # Fail open if DB error, don't block user
            return
