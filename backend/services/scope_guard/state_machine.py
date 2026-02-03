"""
Scope Guard State Machine

Manages the approval workflow for destructive actions.
Enforces state transitions and timeout handling.
"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel

from services.scope_guard.mandate import MandateGenerator, Mandate

logger = logging.getLogger(__name__)


class ApprovalState(str, Enum):
    """Approval workflow states."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    EXECUTED = "executed"


class ActionType(str, Enum):
    """Types of actions that require approval."""
    DELETE_SCOPE = "delete_scope"
    BULK_DELETE = "bulk_delete"
    PURGE_ALL = "purge_all"
    REVOKE_ACCESS = "revoke_access"
    DELETE_CONNECTOR = "delete_connector"


class ApprovalRequest(BaseModel):
    """Model for an approval request."""
    id: str
    organization_id: str
    action_type: ActionType
    resource_type: str
    resource_id: str
    status: ApprovalState
    mandate_nonce: str
    mandate_signature: str
    requested_by: str
    approved_by: Optional[str] = None
    requested_at: datetime
    expires_at: datetime
    approved_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    request_context: Dict[str, Any] = {}
    execution_result: Dict[str, Any] = {}


class ScopeGuardStateMachine:
    """
    State machine for action approval workflow.

    State transitions:
    - IDLE → PENDING (request_approval)
    - PENDING → APPROVED (approve)
    - PENDING → REJECTED (reject)
    - PENDING → EXPIRED (timeout after 30 min)
    - APPROVED → EXECUTED (execute)

    All destructive actions in APPROVAL_REQUIRED must go through
    this workflow to ensure human-in-the-loop verification.
    """

    # Actions that require approval
    APPROVAL_REQUIRED: Set[ActionType] = {
        ActionType.DELETE_SCOPE,
        ActionType.BULK_DELETE,
        ActionType.PURGE_ALL,
    }

    # Default approval timeout in minutes
    DEFAULT_TTL_MINUTES = 30

    def __init__(self):
        self.mandate_generator = MandateGenerator()

    def requires_approval(self, action_type: ActionType) -> bool:
        """Check if an action type requires approval."""
        return action_type in self.APPROVAL_REQUIRED

    async def request_approval(
        self,
        action_type: ActionType,
        resource_type: str,
        resource_id: str,
        organization_id: str,
        requested_by: str,
        context: Optional[Dict[str, Any]] = None,
        ttl_minutes: int = DEFAULT_TTL_MINUTES,
    ) -> Dict[str, Any]:
        """
        Create an approval request and generate mandate.

        Args:
            action_type: Type of action to approve
            resource_type: Type of resource (scope, document, etc.)
            resource_id: ID of the resource
            organization_id: Organization context
            requested_by: User ID requesting the action
            context: Additional context for the approval
            ttl_minutes: Time before approval expires

        Returns:
            Approval request details with mandate
        """
        from core.db import get_supabase

        # Generate cryptographic mandate
        mandate = self.mandate_generator.create(
            action=action_type.value,
            resource_id=resource_id,
            organization_id=organization_id,
            ttl_minutes=ttl_minutes,
        )

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=ttl_minutes)

        supabase = get_supabase()

        # Insert approval request
        result = supabase.table("action_approvals").insert({
            "organization_id": organization_id,
            "action_type": action_type.value,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "status": ApprovalState.PENDING.value,
            "mandate_nonce": mandate.nonce,
            "mandate_signature": mandate.signature,
            "requested_by": requested_by,
            "expires_at": expires_at.isoformat(),
            "request_context": context or {},
        }).execute()

        if not result.data:
            raise Exception("Failed to create approval request")

        approval = result.data[0]

        logger.info(
            f"[ScopeGuard] Approval requested: {action_type.value} on "
            f"{resource_type}/{resource_id} by {requested_by[:8]}..."
        )

        return {
            "approval_id": approval["id"],
            "status": ApprovalState.PENDING.value,
            "action_type": action_type.value,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "expires_at": expires_at.isoformat(),
            "mandate": {
                "nonce": mandate.nonce,
                "signature": mandate.signature,
            },
            "message": (
                f"Approval required for {action_type.value}. "
                f"This request expires in {ttl_minutes} minutes."
            ),
        }

    async def approve(
        self,
        approval_id: str,
        organization_id: str,
        approver_id: str,
    ) -> Dict[str, Any]:
        """
        Approve a pending action request.

        Only admins can approve requests. Validates that:
        - Request exists and belongs to organization
        - Request is in PENDING state
        - Request has not expired

        Args:
            approval_id: ID of the approval request
            organization_id: Organization context
            approver_id: Admin user approving

        Returns:
            Updated approval status
        """
        from core.db import get_supabase

        supabase = get_supabase()

        # Fetch approval request
        result = supabase.table("action_approvals")\
            .select("*")\
            .eq("id", approval_id)\
            .eq("organization_id", organization_id)\
            .maybe_single()\
            .execute()

        if not result.data:
            raise ValueError(f"Approval request not found: {approval_id}")

        approval = result.data

        # Check state
        if approval["status"] != ApprovalState.PENDING.value:
            raise ValueError(
                f"Cannot approve request in state: {approval['status']}"
            )

        # Check expiration
        expires_at = datetime.fromisoformat(
            approval["expires_at"].replace("Z", "+00:00")
        )
        if expires_at < datetime.now(timezone.utc):
            # Update to expired
            supabase.table("action_approvals")\
                .update({"status": ApprovalState.EXPIRED.value})\
                .eq("id", approval_id)\
                .execute()
            raise ValueError("Approval request has expired")

        # Check approver is not same as requester
        if approval["requested_by"] == approver_id:
            raise ValueError("Cannot approve your own request")

        # Update to approved
        now = datetime.now(timezone.utc)
        update_result = supabase.table("action_approvals")\
            .update({
                "status": ApprovalState.APPROVED.value,
                "approved_by": approver_id,
                "approved_at": now.isoformat(),
            })\
            .eq("id", approval_id)\
            .eq("status", ApprovalState.PENDING.value)\
            .execute()

        if not update_result.data:
            raise ValueError("Failed to approve request (state may have changed)")

        logger.info(
            f"[ScopeGuard] Approval granted: {approval['action_type']} on "
            f"{approval['resource_type']}/{approval['resource_id']} "
            f"by {approver_id[:8]}..."
        )

        return {
            "approval_id": approval_id,
            "status": ApprovalState.APPROVED.value,
            "approved_by": approver_id,
            "approved_at": now.isoformat(),
            "message": "Action approved. Use the mandate signature to execute.",
        }

    async def reject(
        self,
        approval_id: str,
        organization_id: str,
        rejector_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Reject a pending action request.

        Args:
            approval_id: ID of the approval request
            organization_id: Organization context
            rejector_id: Admin user rejecting
            reason: Optional rejection reason

        Returns:
            Updated approval status
        """
        from core.db import get_supabase

        supabase = get_supabase()

        # Update to rejected
        result = supabase.table("action_approvals")\
            .update({
                "status": ApprovalState.REJECTED.value,
                "approved_by": rejector_id,  # Using approved_by to track who rejected
                "approved_at": datetime.now(timezone.utc).isoformat(),
                "execution_result": {"rejection_reason": reason} if reason else {},
            })\
            .eq("id", approval_id)\
            .eq("organization_id", organization_id)\
            .eq("status", ApprovalState.PENDING.value)\
            .execute()

        if not result.data:
            raise ValueError("Failed to reject request (not found or already processed)")

        logger.info(
            f"[ScopeGuard] Approval rejected: {approval_id[:8]}... by {rejector_id[:8]}..."
        )

        return {
            "approval_id": approval_id,
            "status": ApprovalState.REJECTED.value,
            "message": "Action request rejected.",
        }

    async def execute(
        self,
        approval_id: str,
        organization_id: str,
        executor_id: str,
        mandate_signature: str,
    ) -> Dict[str, Any]:
        """
        Execute an approved action.

        Validates the mandate signature before execution.

        Args:
            approval_id: ID of the approval request
            organization_id: Organization context
            executor_id: User executing the action
            mandate_signature: The mandate signature for verification

        Returns:
            Execution result
        """
        from core.db import get_supabase

        supabase = get_supabase()

        # Fetch approval
        result = supabase.table("action_approvals")\
            .select("*")\
            .eq("id", approval_id)\
            .eq("organization_id", organization_id)\
            .maybe_single()\
            .execute()

        if not result.data:
            raise ValueError(f"Approval request not found: {approval_id}")

        approval = result.data

        # Check state
        if approval["status"] != ApprovalState.APPROVED.value:
            raise ValueError(
                f"Cannot execute request in state: {approval['status']}"
            )

        # Check expiration
        expires_at = datetime.fromisoformat(
            approval["expires_at"].replace("Z", "+00:00")
        )
        if expires_at < datetime.now(timezone.utc):
            supabase.table("action_approvals")\
                .update({"status": ApprovalState.EXPIRED.value})\
                .eq("id", approval_id)\
                .execute()
            raise ValueError("Approval has expired")

        # Verify mandate signature
        if approval["mandate_signature"] != mandate_signature:
            logger.warning(
                f"[ScopeGuard] Invalid mandate signature for {approval_id[:8]}..."
            )
            raise ValueError("Invalid mandate signature")

        # Execute the action
        try:
            execution_result = await self._execute_action(
                action_type=ActionType(approval["action_type"]),
                resource_type=approval["resource_type"],
                resource_id=approval["resource_id"],
                organization_id=organization_id,
                context=approval.get("request_context", {}),
            )

            # Update to executed
            now = datetime.now(timezone.utc)
            supabase.table("action_approvals")\
                .update({
                    "status": ApprovalState.EXECUTED.value,
                    "executed_at": now.isoformat(),
                    "execution_result": execution_result,
                })\
                .eq("id", approval_id)\
                .execute()

            logger.info(
                f"[ScopeGuard] Action executed: {approval['action_type']} on "
                f"{approval['resource_type']}/{approval['resource_id']}"
            )

            return {
                "approval_id": approval_id,
                "status": ApprovalState.EXECUTED.value,
                "executed_at": now.isoformat(),
                "result": execution_result,
            }

        except Exception as e:
            # Record failure
            supabase.table("action_approvals")\
                .update({
                    "execution_result": {"error": str(e)},
                })\
                .eq("id", approval_id)\
                .execute()
            raise

    async def _execute_action(
        self,
        action_type: ActionType,
        resource_type: str,
        resource_id: str,
        organization_id: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute the approved action.

        Routes to appropriate handler based on action type.
        """
        from services.cleanup import cleanup_service

        if action_type == ActionType.DELETE_SCOPE:
            # Delete all documents in scope
            deleted_count = await cleanup_service.delete_scope(
                scope_id=resource_id,
                organization_id=organization_id,
            )
            return {"deleted_documents": deleted_count}

        elif action_type == ActionType.BULK_DELETE:
            # Bulk delete documents
            document_ids = context.get("document_ids", [])
            deleted = []
            failed = []
            for doc_id in document_ids:
                try:
                    await cleanup_service.delete_single_document(
                        doc_id=doc_id,
                        user_id=context.get("user_id"),
                        organization_id=organization_id,
                    )
                    deleted.append(doc_id)
                except Exception as e:
                    failed.append({"id": doc_id, "error": str(e)})
            return {"deleted": len(deleted), "failed": failed}

        elif action_type == ActionType.PURGE_ALL:
            # Purge all organization data
            # This is a very destructive action
            result = await cleanup_service.purge_organization(
                organization_id=organization_id,
            )
            return result

        else:
            raise ValueError(f"Unknown action type: {action_type}")

    async def get_pending_approvals(
        self,
        organization_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Get all pending approval requests for an organization.
        """
        from core.db import get_supabase

        supabase = get_supabase()

        # Also expire old requests
        now = datetime.now(timezone.utc)
        supabase.table("action_approvals")\
            .update({"status": ApprovalState.EXPIRED.value})\
            .eq("organization_id", organization_id)\
            .eq("status", ApprovalState.PENDING.value)\
            .lt("expires_at", now.isoformat())\
            .execute()

        # Fetch pending
        result = supabase.table("action_approvals")\
            .select("*")\
            .eq("organization_id", organization_id)\
            .eq("status", ApprovalState.PENDING.value)\
            .order("requested_at", desc=True)\
            .execute()

        return result.data or []

    async def get_approval(
        self,
        approval_id: str,
        organization_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific approval request.
        """
        from core.db import get_supabase

        supabase = get_supabase()

        result = supabase.table("action_approvals")\
            .select("*")\
            .eq("id", approval_id)\
            .eq("organization_id", organization_id)\
            .maybe_single()\
            .execute()

        return result.data


# Singleton instance
scope_guard = ScopeGuardStateMachine()
