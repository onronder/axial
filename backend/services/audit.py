"""
Audit Logging Service

Asynchronous audit logging for tracking critical user actions.
Uses FastAPI BackgroundTasks to avoid blocking the main request cycle.

Usage:
    from services.audit import audit_logger
    
    @router.delete("/documents/{id}")
    async def delete_document(id: str, background_tasks: BackgroundTasks, request: Request):
        # ... delete logic ...
        audit_logger.log(
            background_tasks,
            user_id=user_id,
            action="document.delete",
            resource_type="document",
            resource_id=id,
            details={"title": doc.title},
            request=request
        )
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import BackgroundTasks, Request

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Asynchronous audit logger that writes to Supabase.
    
    All logging is done in background tasks to avoid
    impacting request latency.
    """
    
    def __init__(self):
        self._enabled = True
    
    def log(
        self,
        background_tasks: BackgroundTasks,
        user_id: Optional[str],
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
    ) -> None:
        """
        Queue an audit log entry for background writing.
        
        Args:
            background_tasks: FastAPI BackgroundTasks instance
            user_id: ID of the user performing the action (None for system)
            action: Action identifier (e.g., 'document.delete', 'auth.login_fail')
            resource_type: Type of resource affected (e.g., 'document', 'chat')
            resource_id: ID of the affected resource
            details: Additional context (old/new values, metadata)
            request: FastAPI Request object for IP/UA extraction
        """
        if not self._enabled:
            return
        
        # Extract request context
        ip_address = None
        user_agent = None
        
        if request:
            # Get client IP (handles proxies)
            forwarded = request.headers.get("x-forwarded-for")
            if forwarded:
                ip_address = forwarded.split(",")[0].strip()
            else:
                ip_address = request.client.host if request.client else None
            
            user_agent = request.headers.get("user-agent", "")[:500]  # Truncate long UAs
        
        # Queue background task
        background_tasks.add_task(
            self._write_log,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
    
    async def _write_log(
        self,
        user_id: Optional[str],
        action: str,
        resource_type: Optional[str],
        resource_id: Optional[str],
        details: Dict[str, Any],
        ip_address: Optional[str],
        user_agent: Optional[str],
    ) -> None:
        """
        Actually write the log entry to database.
        
        This runs in the background, so errors are logged but not raised.
        """
        try:
            from core.db import get_supabase
            supabase = get_supabase()
            
            log_entry = {
                "user_id": user_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": details,
                "ip_address": ip_address,
                "user_agent": user_agent,
            }
            
            supabase.table("audit_logs").insert(log_entry).execute()
            
            logger.debug(f"📝 [Audit] {action} by {user_id or 'system'} on {resource_type}/{resource_id}")
            
        except Exception as e:
            # Never let audit logging break the main flow
            logger.error(f"❌ [Audit] Failed to write log: {e}")
    
    def log_sync(
        self,
        user_id: Optional[str],
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        Synchronous logging for use in Celery tasks (no BackgroundTasks available).
        
        Still non-blocking in terms of not raising on failure.
        """
        if not self._enabled:
            return
        
        try:
            from core.db import get_supabase
            supabase = get_supabase()
            
            log_entry = {
                "user_id": user_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": details or {},
                "ip_address": ip_address,
                "user_agent": user_agent,
            }
            
            supabase.table("audit_logs").insert(log_entry).execute()
            
            logger.debug(f"📝 [Audit] {action} by {user_id or 'system'} on {resource_type}/{resource_id}")
            
        except Exception as e:
            logger.error(f"❌ [Audit] Failed to write log: {e}")


# Singleton instance
audit_logger = AuditLogger()


# ============================================================================
# Convenience functions for common audit actions
# ============================================================================

def log_document_delete(
    background_tasks: BackgroundTasks,
    user_id: str,
    doc_id: str,
    doc_title: str,
    request: Request,
) -> None:
    """Log document deletion."""
    audit_logger.log(
        background_tasks,
        user_id=user_id,
        action="document.delete",
        resource_type="document",
        resource_id=doc_id,
        details={"title": doc_title},
        request=request,
    )


def log_chat_delete(
    background_tasks: BackgroundTasks,
    user_id: str,
    chat_id: str,
    chat_title: str,
    request: Request,
) -> None:
    """Log chat deletion."""
    audit_logger.log(
        background_tasks,
        user_id=user_id,
        action="chat.delete",
        resource_type="chat",
        resource_id=chat_id,
        details={"title": chat_title},
        request=request,
    )


def log_connector_sync(
    user_id: str,
    connector_type: str,
    status: str,  # 'start', 'success', 'fail'
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Log connector sync events (from Celery tasks)."""
    audit_logger.log_sync(
        user_id=user_id,
        action=f"connector.sync_{status}",
        resource_type="connector",
        resource_id=connector_type,
        details=details,
    )


def log_settings_update(
    background_tasks: BackgroundTasks,
    user_id: str,
    setting_name: str,
    old_value: Any,
    new_value: Any,
    request: Request,
) -> None:
    """Log settings changes."""
    audit_logger.log(
        background_tasks,
        user_id=user_id,
        action="settings.update",
        resource_type="settings",
        resource_id=setting_name,
        details={"old": old_value, "new": new_value},
        request=request,
    )


# ============================================================================
# Ghost Protocol: Security Event Logging
# ============================================================================

def log_security_wipe(
    user_id: Optional[str],
    event_type: str,  # document_wiped, scope_deleted, chunk_purged, organization_purged
    resource_id: str,
    resource_name: str,
    wipe_pattern: Optional[str] = None,
    wipe_verified: bool = False,
    duration_ms: int = 0,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log Ghost Protocol security wipe event (synchronous for Celery compatibility).

    These events are critical for compliance auditing and forensics.
    Always logged with ghost_protocol=True for easy filtering.

    Args:
        user_id: User who initiated the action
        event_type: Type of wipe event
        resource_id: ID of the affected resource
        resource_name: Human-readable name
        wipe_pattern: Wipe pattern used (dod_5220_22_m, random, etc.)
        wipe_verified: Whether verify read passed
        duration_ms: Operation duration in milliseconds
        metadata: Additional context
    """
    audit_logger.log_sync(
        user_id=user_id,
        action=f"security.{event_type}",
        resource_type=event_type.split("_")[0],
        resource_id=resource_id,
        details={
            "resource_name": resource_name,
            "wipe_pattern": wipe_pattern,
            "wipe_verified": wipe_verified,
            "duration_ms": duration_ms,
            "ghost_protocol": True,
            **(metadata or {}),
        },
    )


def log_approval_event(
    background_tasks: BackgroundTasks,
    user_id: str,
    action_type: str,  # request, approve, reject, execute
    approval_id: str,
    resource_type: str,
    resource_id: str,
    details: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None,
) -> None:
    """
    Log ScopeGuard approval workflow event.

    Args:
        background_tasks: FastAPI BackgroundTasks
        user_id: User performing the action
        action_type: Type of approval action
        approval_id: ID of the approval request
        resource_type: Type of resource being approved
        resource_id: ID of the resource
        details: Additional context
        request: FastAPI Request for IP/UA
    """
    audit_logger.log(
        background_tasks,
        user_id=user_id,
        action=f"approval.{action_type}",
        resource_type=resource_type,
        resource_id=resource_id,
        details={
            "approval_id": approval_id,
            "scope_guard": True,
            **(details or {}),
        },
        request=request,
    )


def log_consent_change(
    background_tasks: BackgroundTasks,
    user_id: str,
    consent_level: str,  # organization, scope, document
    resource_id: str,
    field_changed: str,
    old_value: Any,
    new_value: Any,
    request: Optional[Request] = None,
) -> None:
    """
    Log KVKK consent change event.

    Args:
        background_tasks: FastAPI BackgroundTasks
        user_id: User making the change
        consent_level: Level of consent (organization, scope, document)
        resource_id: ID of the resource
        field_changed: Which consent field changed
        old_value: Previous value
        new_value: New value
        request: FastAPI Request for IP/UA
    """
    audit_logger.log(
        background_tasks,
        user_id=user_id,
        action=f"consent.{consent_level}_update",
        resource_type=consent_level,
        resource_id=resource_id,
        details={
            "field_changed": field_changed,
            "old_value": old_value,
            "new_value": new_value,
            "kvkk_compliance": True,
        },
        request=request,
    )
