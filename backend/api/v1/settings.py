"""
Settings API Router

Endpoints for user profile and notification settings management.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from api.v1.dependencies import require_paid_access, validate_team_access
from api.v1.error_utils import ApiErrorCode, api_error
from core.db import get_supabase
from core.rate_limit import limiter
from core.security import get_current_user

router = APIRouter(dependencies=[Depends(validate_team_access)])

# ============================================================
# MODELS
# ============================================================

class ProfileResponse(BaseModel):
    id: str
    user_id: str
    first_name: str | None = None
    last_name: str | None = None
    plan: str = "free"
    theme: str = "system"
    organization_id: str
    team_id: str | None = None
    has_team: bool = False
    role: str | None = None
    created_at: str
    updated_at: str

class ProfileUpdate(BaseModel):
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    theme: str | None = Field(None, max_length=20)

class NotificationSettingResponse(BaseModel):
    id: str
    setting_key: str
    setting_label: str
    setting_description: str | None = None
    category: str
    enabled: bool

class NotificationSettingUpdate(BaseModel):
    setting_key: str
    enabled: bool


def _resolve_team_identity(supabase, user_id: str) -> tuple[str, str | None, str | None]:
    team_check = (
        supabase.table("team_members")
        .select("team_id, role")
        .eq("member_user_id", user_id)
        .neq("status", "removed")
        .limit(1)
        .execute()
    )

    if team_check.data:
        membership = team_check.data[0]
        team_id = membership.get("team_id")
        return (team_id or user_id, team_id, membership.get("role"))

    return (user_id, None, None)


def _serialize_profile_response(profile_data: dict, organization_id: str, team_id: str | None, role: str | None) -> dict:
    profile_data["organization_id"] = organization_id
    profile_data["team_id"] = team_id
    profile_data["has_team"] = team_id is not None
    profile_data["role"] = role
    return profile_data

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
            except Exception:
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

        organization_id, team_id, role = _resolve_team_identity(supabase, user_id)
        return _serialize_profile_response(profile_data, organization_id, team_id, role)

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
            organization_id, team_id, role = _resolve_team_identity(supabase, user_id)
            return _serialize_profile_response(response.data[0], organization_id, team_id, role)

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
    import logging

    from services.cleanup import cleanup_service

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


class AnonymizeRequest(BaseModel):
    """Request body for GDPR anonymization."""
    reason: str = "user_request"
    confirmation: str  # User must type "ANONYMIZE" to confirm


class AnonymizeResponse(BaseModel):
    """Response model for GDPR anonymization."""
    message: str
    request_id: str
    anonymized_at: str
    details: dict


@router.post("/settings/profile/me/anonymize", status_code=200, response_model=AnonymizeResponse)
@limiter.limit("3/minute")
async def anonymize_account(
    request: Request,
    body: AnonymizeRequest,
    user_id: str = Depends(get_current_user)
):
    """
    GDPR-compliant data anonymization.

    This endpoint anonymizes user data without full deletion, preserving
    system integrity while removing personally identifiable information.

    **GDPR Articles Implemented:**
    - Article 17: Right to Erasure (alternative implementation)
    - Article 20: Right to Data Portability (data remains but anonymized)

    **What gets anonymized:**
    - Profile: Names set to "Deleted User", avatar removed
    - Team Records: Email anonymized, name set to "Deleted User"
    - Integrations: OAuth connections deleted (contain tokens)
    - Feedback: User association removed but feedback preserved
    - Auth: Email anonymized, metadata cleared

    **What is preserved:**
    - Documents and embeddings (for enterprise compliance)
    - Chat history (anonymized attribution)
    - Billing records (legal requirement)

    **Confirmation Required:**
    User must send `confirmation: "ANONYMIZE"` in the request body.
    """
    import logging
    from datetime import datetime, timezone

    from services.cleanup import cleanup_service

    logger = logging.getLogger(__name__)

    # Require explicit confirmation
    if body.confirmation != "ANONYMIZE":
        raise HTTPException(
            status_code=400,
            detail="Confirmation required. Send 'confirmation': 'ANONYMIZE' to proceed."
        )

    logger.info(f"🔒 [GDPR] Anonymization request received for user: {user_id}, reason: {body.reason}")

    try:
        request_id = str(uuid.uuid4())
        results = await cleanup_service.anonymize_user_data(user_id, reason=body.reason)

        return AnonymizeResponse(
            message="Your data has been anonymized. Your account remains active but personal information has been removed.",
            request_id=request_id,
            anonymized_at=datetime.now(timezone.utc).isoformat(),
            details=results,
        )
    except Exception as e:
        logger.error(f"❌ [GDPR] Anonymization failed: {e}")
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
    response_model=list[NotificationSettingResponse],
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
