"""
Settings API Router

Endpoints for user profile and notification settings management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from core.security import get_current_user
from core.db import get_supabase
from datetime import datetime

router = APIRouter()

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
async def get_profile(user_id: str = Depends(get_current_user)):
    """Get user profile, creating one if it doesn't exist."""
    supabase = get_supabase()
    
    try:
        # Try to fetch existing profile
        response = supabase.table("user_profiles")\
            .select("*")\
            .eq("user_id", user_id)\
            .execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        
        # Create default profile if not exists
        new_profile = {
            "user_id": user_id,
            "first_name": None,
            "last_name": None,
            "plan": "free",
            "theme": "system",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        insert_response = supabase.table("user_profiles")\
            .insert(new_profile)\
            .execute()
        
        if insert_response.data:
            return insert_response.data[0]
        
        raise HTTPException(status_code=500, detail="Failed to create profile")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch profile: {str(e)}")


@router.patch("/settings/profile", response_model=ProfileResponse)
async def update_profile(
    payload: ProfileUpdate,
    user_id: str = Depends(get_current_user)
):
    """Update user profile."""
    supabase = get_supabase()
    
    try:
        # Build update data (only include non-None fields)
        update_data = {"updated_at": datetime.utcnow().isoformat()}
        
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
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")


# ============================================================
# NOTIFICATION SETTINGS ENDPOINTS
# ============================================================

# Default notification settings to seed for new users
DEFAULT_NOTIFICATION_SETTINGS = [
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
        "setting_key": "ingestion-completed",
        "setting_label": "Ingestion Completed",
        "setting_description": "Get notified when a file finishes processing",
        "category": "system",
        "enabled": True
    },
    {
        "setting_key": "ingestion-failed",
        "setting_label": "Ingestion Failed",
        "setting_description": "Get notified if a connector fails",
        "category": "system",
        "enabled": True
    }
]


@router.get("/settings/notifications", response_model=List[NotificationSettingResponse])
async def get_notification_settings(user_id: str = Depends(get_current_user)):
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
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                for setting in DEFAULT_NOTIFICATION_SETTINGS
            ]
            
            insert_response = supabase.table("user_notification_settings")\
                .insert(settings_to_insert)\
                .execute()
            
            return insert_response.data if insert_response.data else []
        
        return response.data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch settings: {str(e)}")


@router.patch("/settings/notifications", response_model=NotificationSettingResponse)
async def update_notification_setting(
    payload: NotificationSettingUpdate,
    user_id: str = Depends(get_current_user)
):
    """Toggle a specific notification setting."""
    supabase = get_supabase()
    
    try:
        response = supabase.table("user_notification_settings")\
            .update({
                "enabled": payload.enabled,
                "updated_at": datetime.utcnow().isoformat()
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
        raise HTTPException(status_code=500, detail=f"Failed to update setting: {str(e)}")
