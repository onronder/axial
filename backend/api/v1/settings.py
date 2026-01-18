"""
Settings API Router

Endpoints for user profile and notification settings management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from typing import List, Optional
from api.v1.dependencies import validate_team_access, require_paid_access
from api.v1.error_utils import api_error, ApiErrorCode
from core.security import get_current_user
from core.db import get_supabase
from core.rate_limit import limiter
from datetime import datetime, timezone

router = APIRouter(dependencies=[Depends(validate_team_access)])

# ============================================================
# MODELS
# ============================================================

class ProfileResponse(BaseModel):
    id: str
    user_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    plan: str = "free"
    theme: str = "system"
    has_team: bool = False
    role: Optional[str] = None
    created_at: str
    updated_at: str

class ProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    theme: Optional[str] = None

class NotificationSettingResponse(BaseModel):
    id: str
    setting_key: str
    setting_label: str
    setting_description: Optional[str] = None
    category: str
    enabled: bool

class NotificationSettingUpdate(BaseModel):
    setting_key: str
    enabled: bool

# ============================================================
# PROFILE ENDPOINTS
# ============================================================
@router.get("/settings/profile", response_model=ProfileResponse)
@limiter.limit("60/minute")
async def get_profile(request: Request, user_id: str = Depends(get_current_user)):
    """Get user profile, creating one if it doesn't exist."""
    supabase = get_supabase()
    
    try:
        # Try to fetch existing profile
        response = supabase.table("user_profiles")\
            .select("*")\
            .eq("user_id", user_id)\
            .execute()
        
        profile_data = None
        
        if response.data and len(response.data) > 0:
            profile_data = response.data[0]
        else:
            # Profile doesn't exist - create one
            # Note: Trigger might have created it just now, so we could try select again or handle insert error.
            # But standard flow handles safe creation below.
            
            # Try to get user metadata from Supabase auth
            first_name = None
            last_name = None
            
            try:
                # Fetch user from Supabase auth.users to get metadata
                user_response = supabase.auth.admin.get_user_by_id(user_id)
                if user_response and user_response.user:
                    user_metadata = user_response.user.user_metadata or {}
                    
                    # Prefer direct first_name/last_name if available
                    first_name = user_metadata.get("first_name")
                    last_name = user_metadata.get("last_name")
                    
                    # Fallback: parse from full_name if separate fields not available
                    if not first_name and not last_name:
                        full_name = user_metadata.get("full_name", "")
                        if full_name:
                            name_parts = full_name.strip().split(" ", 1)
                            first_name = name_parts[0] if len(name_parts) > 0 else None
                            last_name = name_parts[1] if len(name_parts) > 1 else None
            except Exception as e:
                # Non-critical metadata fetch failure
                pass
            
            # Create default profile
            new_profile = {
                "user_id": user_id,
                "first_name": first_name,
                "last_name": last_name,
                "plan": "free",
                "theme": "system",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Handle potential race condition with trigger using upsert or ignoring error
            # Ideally we check again or use upsert. 
            # Given Task 1 adds a trigger, we should prefer fetching the trigger-created one if insert fails.
            try:
                insert_response = supabase.table("user_profiles")\
                    .insert(new_profile)\
                    .execute()
                if insert_response.data:
                    profile_data = insert_response.data[0]
            except Exception:
                # If insert fails, assume trigger created it and fetch again
                retry = supabase.table("user_profiles").select("*").eq("user_id", user_id).execute()
                if retry.data:
                    profile_data = retry.data[0]
                else:
                    raise HTTPException(status_code=500, detail="Failed to create or retrieve profile")

        if not profile_data:
             raise HTTPException(status_code=500, detail="Failed to retrieve profile")
             
        # TASK 3: Check if user is in any team
        # We assume if they are in a team, they completed onboarding or were invited.
        team_check = supabase.table("team_members")\
            .select("id, role")\
            .eq("member_user_id", user_id)\
            .limit(1)\
            .execute()
            
        if len(team_check.data) > 0:
            profile_data["has_team"] = True
            profile_data["role"] = team_check.data[0].get("role")
        else:
            profile_data["has_team"] = False
            profile_data["role"] = None
        
        return profile_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "fetch_profile")


@router.patch("/settings/profile", response_model=ProfileResponse)
@limiter.limit("30/minute")
async def update_profile(
    request: Request,
    payload: ProfileUpdate,
    user_id: str = Depends(get_current_user)
):
    """Update user profile."""
    supabase = get_supabase()
    
    try:
        # Build update data (only include non-None fields)
        update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
        
        if payload.first_name is not None:
            update_data["first_name"] = payload.first_name
        if payload.last_name is not None:
            update_data["last_name"] = payload.last_name
        if payload.theme is not None:
            if payload.theme not in ["light", "dark", "system"]:
                raise HTTPException(status_code=400, detail="Invalid theme value")
            update_data["theme"] = payload.theme
        
        # Upsert: update if exists, insert if not
        response = supabase.table("user_profiles")\
            .upsert({
                "user_id": user_id,
                **update_data
            }, on_conflict="user_id")\
            .execute()
        
        if response.data:
            return response.data[0]
        
        raise HTTPException(status_code=500, detail="Failed to update profile")
        
    except HTTPException:
        raise
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "update_profile")


@router.delete("/settings/profile/me", status_code=200)
@limiter.limit("3/minute")
async def delete_account(request: Request, user_id: str = Depends(get_current_user)):
    """
    Permanently delete user account and all associated data.
    
    GDPR Article 17 "Right to Erasure" / CCPA Deletion Request
    
    This is a hard delete that removes:
    - All vector embeddings (AI memory)
    - All uploaded files (storage)
    - All database records (cascading)
    - Auth account (Supabase Auth)
    
    WARNING: This action is irreversible.
    """
    from services.cleanup import cleanup_service
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info(f"🗑️ [DeleteAccount] Request received for user: {user_id}")
    
    try:
        # Execute complete account deletion
        results = await cleanup_service.execute_account_deletion(user_id)
        
        logger.info(f"✅ [DeleteAccount] Account deleted successfully: {user_id}")
        
        return {
            "message": "Account and all data permanently deleted",
            "details": results
        }
        
    except Exception as e:
        raise api_error(ApiErrorCode.INTERNAL_ERROR, e, "delete_account")


@router.post("/settings/profile/me/anonymize", status_code=200)
@limiter.limit("3/minute")
async def anonymize_account(request: Request, user_id: str = Depends(get_current_user)):
    """
    Anonymize user data without hard deletion.
    
    GDPR/KVKK compliant alternative to full account deletion.
    """
    from services.cleanup import cleanup_service
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"🧹 [AnonymizeAccount] Request received for user: {user_id}")

    try:
        results = await cleanup_service.anonymize_user_data(user_id)
        return {
            "message": "Account data anonymized",
            "details": results,
        }
    except Exception as e:
        raise api_error(ApiErrorCode.INTERNAL_ERROR, e, "anonymize_account")


# ============================================================
# NOTIFICATION SETTINGS ENDPOINTS
# ============================================================

# Default notification settings to seed for new users
DEFAULT_NOTIFICATION_SETTINGS = [
    {
        "setting_key": "email_on_ingestion_complete",
        "setting_label": "Ingestion Complete Emails",
        "setting_description": "Receive an email when document processing finishes",
        "category": "email",
        "enabled": True
    },
    {
        "setting_key": "weekly-digest",
        "setting_label": "Weekly Digest",
        "setting_description": "Receive a weekly summary of activity",
        "category": "email",
        "enabled": True
    },
    {
        "setting_key": "new-features",
        "setting_label": "New Feature Announcements",
        "setting_description": "Get notified about new product updates",
        "category": "email",
        "enabled": False
    },
    {
        "setting_key": "inapp_on_ingestion_complete",
        "setting_label": "Ingestion Completed",
        "setting_description": "Show in-app notification when files finish processing",
        "category": "system",
        "enabled": True
    },
    {
        "setting_key": "inapp_on_ingestion_failed",
        "setting_label": "Ingestion Failed",
        "setting_description": "Show in-app notification if processing fails",
        "category": "system",
        "enabled": True
    }
]


@router.get(
    "/settings/notifications",
    response_model=List[NotificationSettingResponse],
    dependencies=[Depends(require_paid_access)],
)
@limiter.limit("60/minute")
async def get_notification_settings(request: Request, user_id: str = Depends(get_current_user)):
    """Get notification settings, creating defaults if they don't exist."""
    supabase = get_supabase()
    
    try:
        response = supabase.table("user_notification_settings")\
            .select("*")\
            .eq("user_id", user_id)\
            .execute()
        
        # If no settings exist, create defaults
        if not response.data or len(response.data) == 0:
            settings_to_insert = [
                {
                    "user_id": user_id,
                    **setting,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                for setting in DEFAULT_NOTIFICATION_SETTINGS
            ]
            
            insert_response = supabase.table("user_notification_settings")\
                .insert(settings_to_insert)\
                .execute()
            
            return insert_response.data if insert_response.data else []
        
        return response.data
        
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "fetch_notification_settings")


@router.patch(
    "/settings/notifications",
    response_model=NotificationSettingResponse,
    dependencies=[Depends(require_paid_access)],
)
@limiter.limit("30/minute")
async def update_notification_setting(
    request: Request,
    payload: NotificationSettingUpdate,
    user_id: str = Depends(get_current_user),
):
    """Toggle a specific notification setting."""
    supabase = get_supabase()
    
    try:
        response = supabase.table("user_notification_settings")\
            .update({
                "enabled": payload.enabled,
                "updated_at": datetime.now(timezone.utc).isoformat()
            })\
            .eq("user_id", user_id)\
            .eq("setting_key", payload.setting_key)\
            .execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        
        raise HTTPException(status_code=404, detail="Setting not found")
        
    except HTTPException:
        raise
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "update_notification_settings")


@router.delete(
    "/settings/notifications",
    dependencies=[Depends(require_paid_access)],
)
@limiter.limit("5/minute")
async def reset_notification_settings(request: Request, user_id: str = Depends(get_current_user)):
    """
    Reset all notification settings to defaults.
    
    Deletes all existing settings - they will be recreated with defaults
    on the next GET /settings/notifications call.
    """
    supabase = get_supabase()
    
    try:
        # Delete all user's notification settings
        result = supabase.table("user_notification_settings")\
            .delete()\
            .eq("user_id", user_id)\
            .execute()
        
        deleted_count = len(result.data) if result.data else 0
        
        return {
            "status": "success",
            "message": "Notification settings reset to defaults",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "update_notification_settings")
