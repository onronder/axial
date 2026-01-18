"""
Production-Grade API Error Utilities

Provides:
1. Consistent error response structure
2. Sanitized error messages (no internal details exposed)
3. Error code constants for frontend handling
4. Logging integration for debugging

Usage:
    from api.v1.error_utils import api_error, ApiErrorCode
    
    try:
        ...
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "fetch_documents")
"""

import logging
from enum import Enum
from typing import Any, Dict, Optional, NoReturn

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


# =============================================================================
# ERROR CODES (Frontend-friendly identifiers)
# =============================================================================

class ApiErrorCode(str, Enum):
    """
    Standardized error codes for API responses.
    
    Frontend can use these to display appropriate messages or handle specific cases.
    """
    # Authentication & Authorization
    AUTH_REQUIRED = "AUTH_REQUIRED"
    AUTH_INVALID = "AUTH_INVALID"
    AUTH_EXPIRED = "AUTH_EXPIRED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    TEAM_ACCESS_DENIED = "TEAM_ACCESS_DENIED"
    ADMIN_REQUIRED = "ADMIN_REQUIRED"
    EDITOR_REQUIRED = "EDITOR_REQUIRED"
    SUBSCRIPTION_REQUIRED = "SUBSCRIPTION_REQUIRED"
    
    # Resource Errors
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    CONFLICT = "CONFLICT"
    
    # Validation Errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    INVALID_FORMAT = "INVALID_FORMAT"
    
    # Rate Limiting
    RATE_LIMITED = "RATE_LIMITED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    
    # Integration Errors
    OAUTH_ERROR = "OAUTH_ERROR"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    CONNECTOR_NOT_FOUND = "CONNECTOR_NOT_FOUND"
    CREDENTIALS_NOT_CONFIGURED = "CREDENTIALS_NOT_CONFIGURED"
    
    # Processing Errors
    PROCESSING_ERROR = "PROCESSING_ERROR"
    UPLOAD_ERROR = "UPLOAD_ERROR"
    INGESTION_ERROR = "INGESTION_ERROR"
    CRAWL_ERROR = "CRAWL_ERROR"
    
    # Database Errors
    DATABASE_ERROR = "DATABASE_ERROR"
    
    # External Service Errors
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    WEBHOOK_ERROR = "WEBHOOK_ERROR"
    EMAIL_ERROR = "EMAIL_ERROR"
    PAYMENT_ERROR = "PAYMENT_ERROR"
    
    # Generic
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


# =============================================================================
# USER-SAFE ERROR MESSAGES
# =============================================================================

# Maps operation contexts to user-friendly messages
# NEVER expose internal details like stack traces, SQL errors, or file paths
SANITIZED_MESSAGES: Dict[str, str] = {
    # Documents
    "fetch_documents": "Unable to retrieve documents. Please try again.",
    "fetch_document": "Unable to retrieve document. Please try again.",
    "fetch_stats": "Unable to retrieve statistics. Please try again.",
    "delete_document": "Unable to delete document. Please try again.",
    "update_document": "Unable to update document. Please try again.",
    "fetch_chunks": "Unable to retrieve document content. Please try again.",
    
    # Conversations & Chat
    "fetch_conversations": "Unable to retrieve conversations. Please try again.",
    "create_conversation": "Unable to create conversation. Please try again.",
    "fetch_conversation": "Unable to retrieve conversation. Please try again.",
    "update_conversation": "Unable to update conversation. Please try again.",
    "delete_conversation": "Unable to delete conversation. Please try again.",
    "fetch_messages": "Unable to retrieve messages. Please try again.",
    "send_message": "Unable to send message. Please try again.",
    "stream_chat": "Chat streaming failed. Please try again.",
    
    # Search
    "search": "Search failed. Please try again.",
    "hybrid_search": "Search failed. Please try again.",
    
    # Integrations
    "oauth_exchange": "Authentication failed. Please try connecting again.",
    "oauth_google": "Google authentication failed. Please try again.",
    "oauth_notion": "Notion authentication failed. Please try again.",
    "oauth_microsoft": "Microsoft authentication failed. Please try again.",
    "oauth_dropbox": "Dropbox authentication failed. Please try again.",
    "oauth_github": "GitHub authentication failed. Please try again.",
    "oauth_box": "Box authentication failed. Please try again.",
    "fetch_integrations": "Unable to retrieve integrations. Please try again.",
    "fetch_connectors": "Unable to retrieve available connectors. Please try again.",
    "disconnect": "Unable to disconnect integration. Please try again.",
    "fetch_items": "Unable to retrieve items from provider. Please try again.",
    "ingest_items": "Unable to start ingestion. Please try again.",
    "sync_integration": "Unable to sync integration. Please try again.",
    "sftp_connect": "Unable to connect to SFTP server. Please verify credentials.",
    "s3_connect": "Unable to connect to S3 bucket. Please verify credentials.",
    "github_repos": "Unable to retrieve GitHub repositories. Please try again.",
    
    # Crawling
    "queue_crawl": "Unable to start web crawl. Please try again.",
    "delete_crawl": "Unable to delete crawl configuration. Please try again.",
    
    # Jobs
    "fetch_job": "Unable to retrieve job status. Please try again.",
    "fetch_jobs": "Unable to retrieve jobs. Please try again.",
    "cancel_job": "Unable to cancel job. Please try again.",
    "retry_job": "Unable to retry job. Please try again.",
    "retry_file": "Unable to retry file. Please try again.",
    "fetch_job_files": "Unable to retrieve job files. Please try again.",
    
    # Notifications
    "fetch_notifications": "Unable to retrieve notifications. Please try again.",
    "fetch_unread_count": "Unable to retrieve notification count. Please try again.",
    "mark_notification_read": "Unable to update notification. Please try again.",
    "delete_notification": "Unable to delete notification. Please try again.",
    "clear_notifications": "Unable to clear notifications. Please try again.",
    
    # Team
    "fetch_team": "Unable to retrieve team information. Please try again.",
    "update_team": "Unable to update team. Please try again.",
    "delete_team": "Unable to delete team. Please try again.",
    "fetch_team_members": "Unable to retrieve team members. Please try again.",
    "invite_member": "Unable to send invitation. Please try again.",
    "update_member": "Unable to update team member. Please try again.",
    "remove_member": "Unable to remove team member. Please try again.",
    "accept_invite": "Unable to accept invitation. Please try again.",
    "resend_invite": "Unable to resend invitation. Please try again.",
    "fetch_team_stats": "Unable to retrieve team statistics. Please try again.",
    
    # Settings
    "fetch_profile": "Unable to retrieve profile. Please try again.",
    "update_profile": "Unable to update profile. Please try again.",
    "delete_account": "Unable to delete account. Please try again.",
    "anonymize_account": "Unable to anonymize account. Please try again.",
    "fetch_notification_settings": "Unable to retrieve notification settings. Please try again.",
    "update_notification_settings": "Unable to update notification settings. Please try again.",
    
    # Billing
    "fetch_plans": "Unable to retrieve plans. Please try again.",
    "create_checkout": "Unable to create checkout session. Please try again.",
    "create_portal": "Unable to access billing portal. Please try again.",
    "fetch_subscription": "Unable to retrieve subscription. Please try again.",
    "cancel_subscription": "Unable to cancel subscription. Please try again.",
    "fetch_invoices": "Unable to retrieve billing history. Please try again.",
    "download_invoice": "Unable to download invoice. Please try again.",
    "fix_customer": "Unable to fix customer record. Please try again.",
    "enterprise_inquiry": "Unable to submit inquiry. Please try again.",
    
    # Usage
    "fetch_usage": "Unable to retrieve usage data. Please try again.",
    
    # Uploads
    "check_duplicates": "Unable to check for duplicates. Please try again.",
    "get_upload_url": "Unable to get upload URL. Please try again.",
    "ingest_file": "Unable to process file. Please try again.",
    
    # DLQ / Failed Tasks
    "fetch_failed_task": "Unable to retrieve task information. Please try again.",
    "retry_task": "Unable to retry task. Please try again.",
    "resolve_task": "Unable to resolve task. Please try again.",
    "fetch_dlq_stats": "Unable to retrieve task statistics. Please try again.",
    "fetch_failed_tasks": "Unable to retrieve failed tasks. Please try again.",
    "trigger_retry_cycle": "Unable to trigger retry cycle. Please try again.",
    
    # Admin
    "fetch_audit_logs": "Unable to retrieve audit logs. Please try again.",
    
    # Webhooks
    "process_webhook": "Webhook processing failed.",
    
    # Health
    "health_check": "Health check failed.",
    
    # Database (generic)
    "database": "A database error occurred. Please try again.",
    "database_insert": "Unable to save data. Please try again.",
    "database_update": "Unable to update data. Please try again.",
    "database_delete": "Unable to delete data. Please try again.",
    "database_query": "Unable to retrieve data. Please try again.",
    
    # Generic
    "unknown": "An unexpected error occurred. Please try again.",
}


# =============================================================================
# CORE ERROR FUNCTIONS
# =============================================================================

def build_error_payload(
    code: str, 
    message: str, 
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build a structured error response payload.
    
    Args:
        code: Error code from ApiErrorCode enum
        message: User-friendly error message
        details: Optional additional details (only non-sensitive data)
    
    Returns:
        Structured error dict for HTTPException detail
    """
    payload: Dict[str, Any] = {"error": code, "message": message}
    if details:
        payload["details"] = details
    return payload


def raise_http_error(
    status_code: int, 
    code: str, 
    message: str, 
    details: Optional[Dict[str, Any]] = None
) -> NoReturn:
    """
    Raise an HTTPException with structured error payload.
    
    Args:
        status_code: HTTP status code
        code: Error code from ApiErrorCode enum
        message: User-friendly error message
        details: Optional additional details
    
    Raises:
        HTTPException with structured detail
    """
    raise HTTPException(
        status_code=status_code,
        detail=build_error_payload(code, message, details),
    )


def get_safe_message(operation: str) -> str:
    """
    Get a sanitized user-safe message for an operation.
    
    Args:
        operation: The operation key (e.g., "fetch_documents")
    
    Returns:
        User-safe error message
    """
    return SANITIZED_MESSAGES.get(operation, SANITIZED_MESSAGES["unknown"])


def api_error(
    code: ApiErrorCode,
    exception: Optional[Exception] = None,
    operation: str = "unknown",
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    details: Optional[Dict[str, Any]] = None,
    log_level: str = "error"
) -> HTTPException:
    """
    Create a production-safe API error.
    
    This function:
    1. Logs the full exception for debugging
    2. Returns a sanitized message to the user
    3. Never exposes internal details
    
    Args:
        code: ApiErrorCode enum value
        exception: The caught exception (logged, not exposed)
        operation: Operation key for message lookup
        status_code: HTTP status code (default 500)
        details: Optional safe details to include in response
        log_level: Logging level ("error", "warning", "info")
    
    Returns:
        HTTPException ready to be raised
    
    Usage:
        try:
            result = supabase.table("documents").select("*").execute()
        except Exception as e:
            raise api_error(ApiErrorCode.DATABASE_ERROR, e, "fetch_documents")
    """
    # Get user-safe message
    message = get_safe_message(operation)
    
    # Log the full exception for debugging (never exposed to user)
    if exception:
        log_message = f"[{code.value}] {operation}: {type(exception).__name__}: {exception}"
        if log_level == "error":
            logger.error(log_message)
        elif log_level == "warning":
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    return HTTPException(
        status_code=status_code,
        detail=build_error_payload(code.value, message, details)
    )


def api_error_404(
    resource: str,
    resource_id: Optional[str] = None,
    exception: Optional[Exception] = None
) -> HTTPException:
    """
    Convenience function for 404 Not Found errors.
    
    Args:
        resource: Type of resource (e.g., "document", "conversation")
        resource_id: Optional ID that wasn't found
        exception: Optional caught exception
    
    Returns:
        HTTPException with 404 status
    """
    message = f"{resource.capitalize()} not found"
    details = {"resource": resource}
    if resource_id:
        details["id"] = resource_id
    
    if exception:
        logger.warning(f"[NOT_FOUND] {resource} {resource_id or ''}: {exception}")
    
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=build_error_payload(ApiErrorCode.NOT_FOUND.value, message, details)
    )


def api_error_400(
    message: str,
    code: ApiErrorCode = ApiErrorCode.INVALID_INPUT,
    details: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """
    Convenience function for 400 Bad Request errors.
    
    Args:
        message: User-friendly validation message
        code: Specific error code (default INVALID_INPUT)
        details: Optional validation details
    
    Returns:
        HTTPException with 400 status
    """
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=build_error_payload(code.value, message, details)
    )


def api_error_403(
    reason: str = "Access denied",
    code: ApiErrorCode = ApiErrorCode.PERMISSION_DENIED,
    details: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """
    Convenience function for 403 Forbidden errors.
    
    Args:
        reason: Reason for denial
        code: Specific error code
        details: Optional details
    
    Returns:
        HTTPException with 403 status
    """
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=build_error_payload(code.value, reason, details)
    )


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'ApiErrorCode',
    'SANITIZED_MESSAGES',
    'build_error_payload',
    'raise_http_error',
    'get_safe_message',
    'api_error',
    'api_error_404',
    'api_error_400',
    'api_error_403',
]
