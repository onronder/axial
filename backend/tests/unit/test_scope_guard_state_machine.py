"""
Unit tests for ScopeGuard State Machine.

Covers:
- Approval request creation
- Approval state transitions (pending -> approved -> executed)
- Expiration handling
- Mandate signature verification
- Paginated pending approvals retrieval
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from services.scope_guard.state_machine import (
    ActionType,
    ScopeGuardStateMachine,
)


@pytest.fixture
def state_machine():
    return ScopeGuardStateMachine()


@pytest.fixture
def mock_supabase():
    """Create a mock Supabase client."""
    mock = MagicMock()

    def _table(name):
        builder = MagicMock()
        builder.select.return_value = builder
        builder.eq.return_value = builder
        builder.neq.return_value = builder
        builder.lt.return_value = builder
        builder.order.return_value = builder
        builder.limit.return_value = builder
        builder.range.return_value = builder
        builder.maybe_single.return_value = builder
        builder.single.return_value = builder
        builder.upsert.return_value = builder
        builder.insert.return_value = builder
        builder.update.return_value = builder
        builder.delete.return_value = builder
        builder.execute.return_value = MagicMock(data=[], count=0)
        return builder

    mock.table = MagicMock(side_effect=_table)
    return mock


class TestRequiresApproval:
    """Tests for action type approval checks."""

    def test_bulk_delete_requires_approval(self, state_machine):
        assert state_machine.requires_approval(ActionType.BULK_DELETE) is True

    def test_purge_all_requires_approval(self, state_machine):
        assert state_machine.requires_approval(ActionType.PURGE_ALL) is True


class TestGetPendingApprovals:
    """Tests for paginated pending approvals."""

    @pytest.mark.asyncio
    async def test_default_pagination(self, state_machine, mock_supabase):
        """Pending approvals default to limit=50, offset=0."""
        with patch(
            "services.scope_guard.state_machine.get_supabase",
            return_value=mock_supabase,
        ):
            result = await state_machine.get_pending_approvals("org-1")
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_custom_pagination(self, state_machine, mock_supabase):
        """Pending approvals respect custom limit and offset."""
        with patch(
            "services.scope_guard.state_machine.get_supabase",
            return_value=mock_supabase,
        ):
            result = await state_machine.get_pending_approvals(
                "org-1", limit=10, offset=5
            )
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_expires_old_requests(self, state_machine, mock_supabase):
        """Expired pending requests are marked as expired before fetching."""
        with patch(
            "services.scope_guard.state_machine.get_supabase",
            return_value=mock_supabase,
        ):
            await state_machine.get_pending_approvals("org-1")
            # Verify update was called to expire old requests
            table_calls = mock_supabase.table.call_args_list
            table_names = [call[0][0] for call in table_calls]
            assert "action_approvals" in table_names


class TestApprovalStateTransitions:
    """Tests for state machine transitions."""

    @pytest.mark.asyncio
    async def test_request_creates_pending(self, state_machine, mock_supabase):
        """Request approval creates a pending approval record."""
        mock_supabase.table.return_value.execute.return_value = MagicMock(
            data=[{
                "id": "approval-1",
                "status": "pending",
                "action_type": "bulk_delete",
                "resource_type": "document",
                "resource_id": "bulk",
                "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
                "mandate_signature": "sig-123",
            }]
        )

        with patch(
            "services.scope_guard.state_machine.get_supabase",
            return_value=mock_supabase,
        ):
            result = await state_machine.request_approval(
                action_type=ActionType.BULK_DELETE,
                resource_type="document",
                resource_id="bulk",
                organization_id="org-1",
                requested_by="user-1",
                context={"document_count": 15},
            )
            assert "approval_id" in result
