"""
Dead Letter Queue API Endpoints

Production-grade API for managing failed tasks and retry operations.
"""

import logging
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field, ConfigDict

from api.v1.dependencies import get_current_user, require_admin, validate_team_access, require_paid_access
from api.v1.error_utils import api_error, ApiErrorCode
from core.db import get_supabase
from core.rate_limit import limiter
from worker.dlq_worker import retry_failed_tasks

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(validate_team_access), Depends(require_paid_access)])


# =============================================================================
# Pydantic Models
# =============================================================================

class FailedTaskResponse(BaseModel):
    """Response model for a failed task."""
    id: str
    task_id: str
    task_name: str
    user_id: str
    job_id: Optional[str] = None
    status: str
    attempt_count: int
    max_retries: int
    next_retry_at: Optional[datetime] = None
    exception_type: Optional[str] = None
    exception_message: Optional[str] = None
    traceback: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class DLQStatsResponse(BaseModel):
    """Response model for DLQ statistics."""
    total_failed: int = Field(..., description="Total number of failed tasks")
    total: int = Field(..., description="Alias for total_failed (frontend compatibility)")
    pending_retry: int = Field(..., description="Tasks waiting for retry")
    retrying: int = Field(..., description="Tasks currently retrying")
    permanently_failed: int = Field(..., description="Tasks that failed all retries")
    resolved: int = Field(..., description="Total tasks resolved (all time)")
    resolved_today: int = Field(..., description="Tasks resolved in last 24 hours")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_failed": 42,
                "total": 42,
                "pending_retry": 5,
                "retrying": 2,
                "permanently_failed": 10,
                "resolved": 25,
                "resolved_today": 3
            }
        }
    )


class ManualRetryRequest(BaseModel):
    """Request model for manual retry."""
    reason: Optional[str] = Field(None, description="Reason for manual retry")


class ManualRetryResponse(BaseModel):
    """Response model for manual retry."""
    success: bool
    message: str
    task_id: str
    new_status: str


class DLQListResponse(BaseModel):
    """Response model for list of failed tasks."""
    tasks: List[FailedTaskResponse]
    total: int
    page: int
    page_size: int


# =============================================================================
# User Endpoints
# =============================================================================

@router.get(
    "/failed-tasks/{job_id}",
    response_model=Optional[FailedTaskResponse],
    summary="Get failed task for a job",
    description="Retrieve the failed task information for a specific ingestion job"
)
@limiter.limit("60/minute")
async def get_failed_task_for_job(
    request: Request,
    job_id: str,
    user_id: str = Depends(get_current_user)
):
    """
    Get failed task information for a specific job.
    
    Returns the most recent failed task for the given job ID.
    Only returns tasks belonging to the authenticated user.
    """
    try:
        supabase = get_supabase()
        
        # Query failed_tasks table
        result = supabase.table("failed_tasks").select("*").eq(
            "job_id", job_id
        ).eq(
            "user_id", user_id  # Security: Only user's own tasks
        ).order(
            "created_at", desc=True
        ).limit(1).execute()
        
        if not result.data:
            return None
        
        task = result.data[0]
        
        # Convert to response model
        return FailedTaskResponse(
            id=task["id"],
            task_id=task["task_id"],
            task_name=task["task_name"],
            user_id=task["user_id"],
            job_id=task.get("job_id"),
            status=task["status"],
            attempt_count=task["attempt_count"],
            max_retries=task["max_retries"],
            next_retry_at=task.get("next_retry_at"),
            exception_type=task.get("exception_type"),
            exception_message=task.get("exception_message"),
            traceback=task.get("traceback"),
            created_at=task["created_at"],
            updated_at=task["updated_at"],
            resolved_at=task.get("resolved_at")
        )
        
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "fetch_failed_task")


@router.post(
    "/retry/{task_id}",
    response_model=ManualRetryResponse,
    summary="Manually retry a failed task",
    description="Trigger an immediate retry of a failed task"
)
@limiter.limit("20/minute")
async def manual_retry_task(
    http_request: Request,
    task_id: str,
    request: ManualRetryRequest = ManualRetryRequest(),
    user_id: str = Depends(get_current_user)
):
    """
    Manually trigger retry for a failed task.
    
    This bypasses the automatic retry schedule and immediately
    re-queues the task for execution.
    """
    try:
        supabase = get_supabase()
        
        # Get the task
        result = supabase.table("failed_tasks").select("*").eq(
            "id", task_id
        ).eq(
            "user_id", user_id  # Security: Only user's own tasks
        ).single().execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found or access denied"
            )
        
        task = result.data
        
        # Check if task can be retried
        if task["status"] == "resolved":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task already resolved, cannot retry"
            )
        
        if task["status"] == "retrying":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task is already retrying"
            )
        
        if task["attempt_count"] >= task["max_retries"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task has exceeded maximum retry attempts"
            )
        
        # Update task status to trigger immediate retry
        now = datetime.now(timezone.utc)
        update_result = supabase.table("failed_tasks").update({
            "status": "pending_retry",
            "next_retry_at": now.isoformat(),  # Immediate retry
            "updated_at": now.isoformat()
        }).eq("id", task_id).execute()
        
        if not update_result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update task status"
            )
        
        # Log manual retry
        logger.info(
            f"📥 [DLQ] Manual retry triggered for task {task_id} by user {user_id}"
            + (f" - Reason: {request.reason}" if request.reason else "")
        )
        
        return ManualRetryResponse(
            success=True,
            message="Task scheduled for immediate retry",
            task_id=task_id,
            new_status="pending_retry"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "retry_task")


@router.post(
    "/resolve/{task_id}",
    response_model=ManualRetryResponse,
    summary="Resolve a failed task",
    description="Mark a failed task as resolved (dismisses it from the list)"
)
@limiter.limit("30/minute")
async def resolve_failed_task(
    request: Request,
    task_id: str,
    user_id: str = Depends(get_current_user)
):
    """
    Mark a failed task as resolved.
    
    This removes the task from the active failed list.
    Used when the issue has been fixed manually or the task is no longer needed.
    """
    try:
        supabase = get_supabase()
        
        # Get the task
        result = supabase.table("failed_tasks").select("*").eq(
            "id", task_id
        ).eq(
            "user_id", user_id  # Security: Only user's own tasks
        ).single().execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found or access denied"
            )
        
        task = result.data
        
        if task["status"] == "resolved":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task is already resolved"
            )
        
        # Update task status to resolved
        now = datetime.now(timezone.utc)
        update_result = supabase.table("failed_tasks").update({
            "status": "resolved",
            "resolved_at": now.isoformat(),
            "updated_at": now.isoformat()
        }).eq("id", task_id).execute()
        
        if not update_result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update task status"
            )
        
        logger.info(f"📥 [DLQ] Task {task_id} marked as resolved by user {user_id}")
        
        return ManualRetryResponse(
            success=True,
            message="Task marked as resolved",
            task_id=task_id,
            new_status="resolved"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "resolve_task")


@router.get(
    "/stats",
    response_model=DLQStatsResponse,
    summary="Get DLQ statistics",
    description="Retrieve statistics about failed tasks for the current user"
)
@limiter.limit("60/minute")
async def get_dlq_stats(
    request: Request,
    user_id: str = Depends(get_current_user)
):
    """
    Get DLQ statistics for the authenticated user.
    
    Returns counts of tasks in each status category including resolved_today.
    """
    try:
        supabase = get_supabase()
        
        # Get all tasks for user with resolved_at for today calculation
        result = supabase.table("failed_tasks").select(
            "status, resolved_at"
        ).eq(
            "user_id", user_id
        ).execute()
        
        if not result.data:
            return DLQStatsResponse(
                total_failed=0,
                total=0,
                pending_retry=0,
                retrying=0,
                permanently_failed=0,
                resolved=0,
                resolved_today=0
            )
        
        # Count by status
        status_counts = {
            "pending_retry": 0,
            "retrying": 0,
            "permanently_failed": 0,
            "resolved": 0
        }
        
        # Calculate resolved_today (last 24 hours)
        now = datetime.now(timezone.utc)
        today_start = now - timedelta(hours=24)
        resolved_today = 0
        
        for task in result.data:
            task_status = task["status"]
            if task_status in status_counts:
                status_counts[task_status] += 1
            
            # Check if resolved within last 24 hours
            resolved_at = task.get("resolved_at")
            if resolved_at and task_status == "resolved":
                try:
                    resolved_dt = datetime.fromisoformat(resolved_at.replace("Z", "+00:00"))
                    if resolved_dt >= today_start:
                        resolved_today += 1
                except (ValueError, TypeError):
                    pass
        
        total = len(result.data)
        
        return DLQStatsResponse(
            total_failed=total,
            total=total,
            pending_retry=status_counts["pending_retry"],
            retrying=status_counts["retrying"],
            permanently_failed=status_counts["permanently_failed"],
            resolved=status_counts["resolved"],
            resolved_today=resolved_today
        )
        
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "fetch_dlq_stats")


@router.get(
    "/my-tasks",
    response_model=DLQListResponse,
    summary="Get all failed tasks for current user",
    description="Retrieve paginated list of all failed tasks for the authenticated user"
)
@limiter.limit("60/minute")
async def get_my_failed_tasks(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    status_filter: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """
    Get all failed tasks for the authenticated user.
    
    Supports pagination and filtering by status.
    """
    try:
        supabase = get_supabase()
        
        # Build query
        query = supabase.table("failed_tasks").select(
            "*", count="exact"
        ).eq("user_id", user_id)
        
        # Apply status filter if provided
        if status_filter:
            valid_statuses = ["failed", "pending_retry", "retrying", "permanently_failed", "resolved"]
            if status_filter not in valid_statuses:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status filter. Must be one of: {', '.join(valid_statuses)}"
                )
            query = query.eq("status", status_filter)
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.order("created_at", desc=True).range(offset, offset + page_size - 1)
        
        result = query.execute()
        
        tasks = [
            FailedTaskResponse(
                id=task["id"],
                task_id=task["task_id"],
                task_name=task["task_name"],
                user_id=task["user_id"],
                job_id=task.get("job_id"),
                status=task["status"],
                attempt_count=task["attempt_count"],
                max_retries=task["max_retries"],
                next_retry_at=task.get("next_retry_at"),
                exception_type=task.get("exception_type"),
                exception_message=task.get("exception_message"),
                traceback=task.get("traceback"),
                created_at=task["created_at"],
                updated_at=task["updated_at"],
                resolved_at=task.get("resolved_at")
            )
            for task in result.data
        ]
        
        return DLQListResponse(
            tasks=tasks,
            total=result.count or 0,
            page=page,
            page_size=page_size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "fetch_failed_tasks")


# =============================================================================
# Admin Endpoints
# =============================================================================

@router.get(
    "/admin/all",
    response_model=DLQListResponse,
    summary="[Admin] Get all failed tasks",
    description="Admin endpoint to retrieve all failed tasks across all users"
)
@limiter.limit("30/minute")
async def admin_get_all_failed_tasks(
    request: Request,
    page: int = 1,
    page_size: int = 50,
    status_filter: Optional[str] = None,
    user_id: str = Depends(get_current_user),
    _: bool = Depends(require_admin)
):
    """
    Admin: Get all failed tasks across all users.
    
    Requires admin privileges.
    """
    try:
        supabase = get_supabase()
        
        # Build query
        query = supabase.table("failed_tasks").select("*", count="exact")
        
        # Apply status filter if provided
        if status_filter:
            query = query.eq("status", status_filter)
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.order("created_at", desc=True).range(offset, offset + page_size - 1)
        
        result = query.execute()
        
        tasks = [
            FailedTaskResponse(
                id=task["id"],
                task_id=task["task_id"],
                task_name=task["task_name"],
                user_id=task["user_id"],
                job_id=task.get("job_id"),
                status=task["status"],
                attempt_count=task["attempt_count"],
                max_retries=task["max_retries"],
                next_retry_at=task.get("next_retry_at"),
                exception_type=task.get("exception_type"),
                exception_message=task.get("exception_message"),
                traceback=task.get("traceback"),
                created_at=task["created_at"],
                updated_at=task["updated_at"],
                resolved_at=task.get("resolved_at")
            )
            for task in result.data
        ]
        
        logger.info(f"📥 [DLQ Admin] User {user_id} retrieved {len(tasks)} failed tasks")
        
        return DLQListResponse(
            tasks=tasks,
            total=result.count or 0,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "fetch_failed_tasks")


@router.post(
    "/admin/trigger-retry-cycle",
    summary="[Admin] Trigger retry cycle",
    description="Admin endpoint to manually trigger the DLQ retry cycle"
)
@limiter.limit("5/minute")
async def admin_trigger_retry_cycle(
    request: Request,
    user_id: str = Depends(get_current_user),
    _: bool = Depends(require_admin)
):
    """
    Admin: Manually trigger the DLQ retry cycle.
    
    This runs the same logic as the Celery Beat periodic task.
    Requires admin privileges.
    """
    try:
        logger.info(f"📥 [DLQ Admin] User {user_id} triggered manual retry cycle")
        
        # Run the retry cycle
        result = retry_failed_tasks()
        
        return {
            "success": True,
            "message": "Retry cycle completed",
            "retried": result.get("retried", 0),
            "failed": result.get("failed", 0)
        }
        
    except Exception as e:
        raise api_error(ApiErrorCode.INTERNAL_ERROR, e, "trigger_retry_cycle")


@router.get(
    "/admin/stats",
    summary="[Admin] Get global DLQ statistics",
    description="Admin endpoint to get DLQ statistics across all users"
)
@limiter.limit("30/minute")
async def admin_get_global_stats(
    request: Request,
    user_id: str = Depends(get_current_user),
    _: bool = Depends(require_admin)
):
    """
    Admin: Get global DLQ statistics across all users.
    
    Requires admin privileges.
    """
    try:
        supabase = get_supabase()
        
        # Get all tasks
        result = supabase.table("failed_tasks").select("status, user_id").execute()
        
        if not result.data:
            return {
                "total_failed": 0,
                "pending_retry": 0,
                "retrying": 0,
                "permanently_failed": 0,
                "resolved": 0,
                "unique_users": 0
            }
        
        # Count by status
        status_counts = {
            "pending_retry": 0,
            "retrying": 0,
            "permanently_failed": 0,
            "resolved": 0
        }
        
        unique_users = set()
        
        for task in result.data:
            task_status = task["status"]
            if task_status in status_counts:
                status_counts[task_status] += 1
            if task.get("user_id"):
                unique_users.add(task["user_id"])
        
        return {
            "total_failed": len(result.data),
            "pending_retry": status_counts["pending_retry"],
            "retrying": status_counts["retrying"],
            "permanently_failed": status_counts["permanently_failed"],
            "resolved": status_counts["resolved"],
            "unique_users": len(unique_users)
        }
        
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "fetch_dlq_stats")
