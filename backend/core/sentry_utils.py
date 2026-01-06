"""
Sentry Breadcrumbs Utility

Provides helper functions for adding structured breadcrumbs to Sentry
for better debugging and error tracking across the application.
"""

import logging
from typing import Any, Dict, Optional
from functools import wraps

logger = logging.getLogger(__name__)

# Try to import Sentry SDK
try:
    import sentry_sdk
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False
    logger.warning("Sentry SDK not available, breadcrumbs will be logged only")


def add_breadcrumb(
    message: str,
    category: str = "general",
    level: str = "info",
    data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Add a breadcrumb for debugging.
    
    Args:
        message: Description of the action
        category: Category for grouping (e.g., 'task', 'api', 'db', 'external')
        level: Severity level ('debug', 'info', 'warning', 'error')
        data: Additional context data
    """
    if SENTRY_AVAILABLE:
        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=data or {}
        )
    else:
        # Fallback to logging when Sentry is not available
        log_level = getattr(logging, level.upper(), logging.INFO)
        logger.log(log_level, f"[{category}] {message}", extra=data or {})


def set_user_context(user_id: str, email: Optional[str] = None) -> None:
    """
    Set user context for error tracking.
    
    Args:
        user_id: User's unique identifier
        email: User's email (optional, for better identification)
    """
    if SENTRY_AVAILABLE:
        sentry_sdk.set_user({
            "id": user_id,
            "email": email
        })


def set_tag(key: str, value: str) -> None:
    """Set a tag for filtering in Sentry."""
    if SENTRY_AVAILABLE:
        sentry_sdk.set_tag(key, value)


def set_context(name: str, data: Dict[str, Any]) -> None:
    """Set additional context for debugging."""
    if SENTRY_AVAILABLE:
        sentry_sdk.set_context(name, data)


# ============================================================
# Category-specific breadcrumb helpers
# ============================================================

def task_started(task_name: str, task_id: str, **kwargs: Any) -> None:
    """Log the start of a background task."""
    add_breadcrumb(
        message=f"Task started: {task_name}",
        category="task",
        level="info",
        data={"task_id": task_id, **kwargs}
    )
    set_tag("task_name", task_name)


def task_completed(task_name: str, task_id: str, result: Optional[Any] = None) -> None:
    """Log successful task completion."""
    add_breadcrumb(
        message=f"Task completed: {task_name}",
        category="task",
        level="info",
        data={"task_id": task_id, "result_type": type(result).__name__ if result else None}
    )


def task_failed(task_name: str, task_id: str, error: str) -> None:
    """Log task failure."""
    add_breadcrumb(
        message=f"Task failed: {task_name}",
        category="task",
        level="error",
        data={"task_id": task_id, "error": error}
    )


def api_request(endpoint: str, method: str, user_id: Optional[str] = None) -> None:
    """Log API endpoint access."""
    add_breadcrumb(
        message=f"{method} {endpoint}",
        category="api",
        level="info",
        data={"user_id": user_id} if user_id else {}
    )


def db_operation(operation: str, table: str, count: Optional[int] = None) -> None:
    """Log database operation."""
    add_breadcrumb(
        message=f"DB: {operation} on {table}",
        category="db",
        level="debug",
        data={"count": count} if count else {}
    )


def external_call(service: str, endpoint: str, success: bool = True) -> None:
    """Log external API call."""
    add_breadcrumb(
        message=f"External: {service} - {endpoint}",
        category="external",
        level="info" if success else "warning",
        data={"success": success}
    )


def file_processing(filename: str, stage: str, progress: Optional[int] = None) -> None:
    """Log file processing progress."""
    add_breadcrumb(
        message=f"File: {filename} - {stage}",
        category="processing",
        level="info",
        data={"progress": progress} if progress else {}
    )


# ============================================================
# Decorator for automatic task breadcrumbs
# ============================================================

def with_breadcrumbs(category: str = "task"):
    """
    Decorator to automatically add start/complete/error breadcrumbs.
    
    Usage:
        @with_breadcrumbs("task")
        def my_task():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            add_breadcrumb(
                message=f"Starting: {func_name}",
                category=category,
                level="info",
                data={"args_count": len(args), "kwargs_keys": list(kwargs.keys())}
            )
            try:
                result = func(*args, **kwargs)
                add_breadcrumb(
                    message=f"Completed: {func_name}",
                    category=category,
                    level="info"
                )
                return result
            except Exception as e:
                add_breadcrumb(
                    message=f"Failed: {func_name}",
                    category=category,
                    level="error",
                    data={"error": str(e), "error_type": type(e).__name__}
                )
                raise
        return wrapper
    return decorator


def with_breadcrumbs_async(category: str = "task"):
    """
    Async decorator for automatic breadcrumbs.
    
    Usage:
        @with_breadcrumbs_async("api")
        async def my_handler():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            func_name = func.__name__
            add_breadcrumb(
                message=f"Starting: {func_name}",
                category=category,
                level="info"
            )
            try:
                result = await func(*args, **kwargs)
                add_breadcrumb(
                    message=f"Completed: {func_name}",
                    category=category,
                    level="info"
                )
                return result
            except Exception as e:
                add_breadcrumb(
                    message=f"Failed: {func_name}",
                    category=category,
                    level="error",
                    data={"error": str(e), "error_type": type(e).__name__}
                )
                raise
        return wrapper
    return decorator
