"""
Scope Guard Approval API Endpoints

Human-in-the-loop approval workflow for destructive actions.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, status, Query
from pydantic import BaseModel, Field

from api.v1.dependencies import (
    require_admin,
    require_editor,
    get_user_organization_id,
    validate_team_access,
)
from core.rate_limit import limiter
from api.v1.error_utils import api_error, ApiErrorCode
from services.scope_guard import (
    ScopeGuardStateMachine,
    ActionType,
    ApprovalState,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    dependencies=[Depends(validate_team_access)],
)


# =============================================================================
# Request/Response Models
# =============================================================================

class ApprovalRequestPayload(BaseModel):
    """Request payload for creating an approval request."""
    action_type: str = Field(..., max_length=50)
    resource_type: str = Field(..., max_length=50)
    resource_id: str = Field(..., max_length=100)
    context: Optional[dict] = None
    ttl_minutes: int = Field(default=30, ge=1, le=1440)


class ApprovalResponse(BaseModel):
    """Response for approval operations."""
    approval_id: str
    status: str
    action_type: str
    resource_type: str
    resource_id: str
    expires_at: Optional[str] = None
    mandate: Optional[dict] = None
    message: str


class ExecutePayload(BaseModel):
    """Payload for executing an approved action."""
    mandate_signature: str


class ApprovalListItem(BaseModel):
    """Item in the pending approvals list."""
    id: str
    action_type: str
    resource_type: str
    resource_id: str
    status: str
    requested_by: str
    requested_at: str
    expires_at: str
    request_context: dict = {}


# =============================================================================
# Approval Endpoints
# =============================================================================

@router.post("/approvals/request", response_model=ApprovalResponse)
@limiter.limit("10/minute")
async def request_approval(
    payload: ApprovalRequestPayload,
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(require_editor),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    Request approval for a destructive action.

    Returns a mandate that must be approved by an admin before execution.
    The mandate expires after the specified TTL (default 30 minutes).

    Args:
        payload: Action details and context
            - action_type: Type of action (delete_scope, bulk_delete, purge_all)
            - resource_type: Type of resource (scope, document, etc.)
            - resource_id: ID of the resource
            - context: Additional context for the approval
            - ttl_minutes: Time before expiration (default 30)

    Returns:
        Approval request with mandate for later verification
    """
    from services.audit import audit_logger

    try:
        action_type = ActionType(payload.action_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action type: {payload.action_type}"
        )

    state_machine = ScopeGuardStateMachine()

    # Check if this action requires approval
    if not state_machine.requires_approval(action_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Action {action_type.value} does not require approval"
        )

    try:
        result = await state_machine.request_approval(
            action_type=action_type,
            resource_type=payload.resource_type,
            resource_id=payload.resource_id,
            organization_id=organization_id,
            requested_by=user_id,
            context=payload.context,
            ttl_minutes=payload.ttl_minutes,
        )

        # Audit log
        audit_logger.log(
            background_tasks,
            user_id=user_id,
            action="approval.request",
            resource_type=payload.resource_type,
            resource_id=payload.resource_id,
            details={
                "action_type": payload.action_type,
                "approval_id": result["approval_id"],
            },
            request=request,
        )

        return ApprovalResponse(**result)

    except Exception as e:
        raise api_error(ApiErrorCode.PROCESSING_ERROR, e, "request_approval")


@router.post("/approvals/{approval_id}/approve")
@limiter.limit("10/minute")
async def approve_action(
    approval_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(require_admin),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    Approve a pending action request.

    Only organization admins can approve requests.
    The approver cannot be the same as the requester.

    Args:
        approval_id: ID of the approval request

    Returns:
        Updated approval status
    """
    from services.audit import audit_logger

    state_machine = ScopeGuardStateMachine()

    try:
        result = await state_machine.approve(
            approval_id=approval_id,
            organization_id=organization_id,
            approver_id=user_id,
        )

        # Audit log
        audit_logger.log(
            background_tasks,
            user_id=user_id,
            action="approval.approve",
            resource_type="approval",
            resource_id=approval_id,
            details={},
            request=request,
        )

        return result

    except ValueError as e:
        raise api_error(ApiErrorCode.PROCESSING_ERROR, e, "approve_action",
                        status_code=status.HTTP_400_BAD_REQUEST, log_level="warning")
    except Exception as e:
        raise api_error(ApiErrorCode.PROCESSING_ERROR, e, "approve_action")


@router.post("/approvals/{approval_id}/reject")
@limiter.limit("10/minute")
async def reject_action(
    approval_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    reason: Optional[str] = None,
    user_id: str = Depends(require_admin),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    Reject a pending action request.

    Only organization admins can reject requests.

    Args:
        approval_id: ID of the approval request
        reason: Optional rejection reason

    Returns:
        Updated approval status
    """
    from services.audit import audit_logger

    state_machine = ScopeGuardStateMachine()

    try:
        result = await state_machine.reject(
            approval_id=approval_id,
            organization_id=organization_id,
            rejector_id=user_id,
            reason=reason,
        )

        # Audit log
        audit_logger.log(
            background_tasks,
            user_id=user_id,
            action="approval.reject",
            resource_type="approval",
            resource_id=approval_id,
            details={"reason": reason},
            request=request,
        )

        return result

    except ValueError as e:
        raise api_error(ApiErrorCode.PROCESSING_ERROR, e, "reject_action",
                        status_code=status.HTTP_400_BAD_REQUEST, log_level="warning")
    except Exception as e:
        raise api_error(ApiErrorCode.PROCESSING_ERROR, e, "reject_action")


@router.post("/approvals/{approval_id}/execute")
@limiter.limit("10/minute")
async def execute_approved(
    approval_id: str,
    payload: ExecutePayload,
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(require_editor),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    Execute an approved action.

    Requires the mandate signature from the original approval request.
    The action must be in APPROVED state and not expired.

    Args:
        approval_id: ID of the approval request
        payload: Contains the mandate_signature for verification

    Returns:
        Execution result
    """
    from services.audit import audit_logger

    state_machine = ScopeGuardStateMachine()

    try:
        result = await state_machine.execute(
            approval_id=approval_id,
            organization_id=organization_id,
            executor_id=user_id,
            mandate_signature=payload.mandate_signature,
        )

        # Audit log
        audit_logger.log(
            background_tasks,
            user_id=user_id,
            action="approval.execute",
            resource_type="approval",
            resource_id=approval_id,
            details={"result": result.get("result", {})},
            request=request,
        )

        return result

    except ValueError as e:
        raise api_error(ApiErrorCode.PROCESSING_ERROR, e, "execute_approved",
                        status_code=status.HTTP_400_BAD_REQUEST, log_level="warning")
    except Exception as e:
        raise api_error(ApiErrorCode.PROCESSING_ERROR, e, "execute_approved")


@router.get("/approvals/pending", response_model=List[ApprovalListItem])
@limiter.limit("30/minute")
async def list_pending(
    request: Request,
    user_id: str = Depends(require_admin),
    organization_id: str = Depends(get_user_organization_id),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """
    List pending approval requests with pagination.

    Only organization admins can view pending approvals.
    Expired requests are automatically marked as expired.

    Returns:
        List of pending approval requests
    """
    state_machine = ScopeGuardStateMachine()

    try:
        approvals = await state_machine.get_pending_approvals(
            organization_id, limit=limit, offset=offset
        )
        return [
            ApprovalListItem(
                id=a["id"],
                action_type=a["action_type"],
                resource_type=a["resource_type"],
                resource_id=a["resource_id"],
                status=a["status"],
                requested_by=a["requested_by"],
                requested_at=a["requested_at"],
                expires_at=a["expires_at"],
                request_context=a.get("request_context", {}),
            )
            for a in approvals
        ]
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "list_approvals")


@router.get("/approvals/{approval_id}")
@limiter.limit("30/minute")
async def get_approval(
    approval_id: str,
    request: Request,
    user_id: str = Depends(validate_team_access),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    Get a specific approval request.

    Returns full details of the approval request.
    """
    state_machine = ScopeGuardStateMachine()

    try:
        approval = await state_machine.get_approval(approval_id, organization_id)
        if not approval:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approval request not found"
            )
        return approval
    except HTTPException:
        raise
    except Exception as e:
        raise api_error(ApiErrorCode.DATABASE_ERROR, e, "get_approval")
