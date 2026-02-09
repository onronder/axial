"""
Notification Service - Centralized notification creation.

This module provides a single source of truth for creating notifications,
eliminating duplicate code across API and worker modules.
"""

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def create_notification(
    supabase,
    user_id: str,
    title: str,
    message: str = None,
    notification_type: str = "info",
    metadata: dict = None,
    action_url: str = None,
    check_setting_key: str = None
) -> dict | None:
    """
    Create a notification for the user.

    This is the CANONICAL notification creation function.
    All other code should import and use this function.

    Args:
        supabase: Supabase client instance
        user_id: User's ID
        title: Notification title
        message: Optional detailed message
        notification_type: One of 'info', 'success', 'warning', 'error'
        metadata: Optional extra data (e.g., job_id, file_names)
        action_url: Optional URL to navigate to when clicked (e.g., '/dashboard/chat')
        check_setting_key: Optional setting key to check. If user has this
                          setting disabled, notification will not be created.

    Returns:
        Created notification dict, or None if user has disabled this type or on error
    """
    try:
        # Check user preference if setting key provided
        if check_setting_key:
            try:
                pref = supabase.table("user_notification_settings")\
                    .select("enabled")\
                    .eq("user_id", user_id)\
                    .eq("setting_key", check_setting_key)\
                    .maybe_single()\
                    .execute()

                # If preference exists and is explicitly False, skip notification
                if pref.data and pref.data.get("enabled") is False:
                    logger.info(f"🔕 [Notification] Skipped for {user_id[:8]}...: {check_setting_key} is disabled")
                    return None
            except Exception as e:
                # Fail open - don't block notifications on preference check errors
                logger.warning(f"⚠️ [Notification] Failed to check preference: {e}")

        # Include action_url in metadata if provided
        meta = metadata.copy() if metadata else {}
        if action_url:
            meta["action_url"] = action_url

        notification_data = {
            "user_id": user_id,
            "title": title,
            "message": message,
            "type": notification_type,
            "is_read": False,
            # Serialize dict as JSON string for extra_data column
            "extra_data": json.dumps(meta) if meta else None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        result = supabase.table("notifications").insert(notification_data).execute()
        logger.info(f"🔔 [Notification] Created {notification_type}: {title}")
        return result.data[0] if result.data else None

    except Exception as e:
        logger.error(f"❌ [Notification] Failed to create: {e}")
        return None
