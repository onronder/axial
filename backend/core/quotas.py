from core.config import settings
from core.db import get_supabase
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

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
