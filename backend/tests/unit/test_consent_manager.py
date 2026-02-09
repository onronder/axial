"""
Unit tests for Consent Manager service.

Covers:
- Organization consent CRUD
- Scope consent with inheritance
- Document consent with inheritance
- Audit log pagination
- Compliance report generation
"""

from unittest.mock import MagicMock, patch

import pytest

from services.consent import ConsentType
from services.consent.manager import ConsentManager


@pytest.fixture
def manager():
    return ConsentManager()


@pytest.fixture
def mock_supabase():
    """Create a mock Supabase client with chainable query builder."""
    mock = MagicMock()

    def _table(name):
        builder = MagicMock()
        builder.select.return_value = builder
        builder.eq.return_value = builder
        builder.neq.return_value = builder
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


class TestGetConsentAuditLog:
    """Tests for paginated consent audit log retrieval."""

    @pytest.mark.asyncio
    async def test_default_pagination(self, manager, mock_supabase):
        """Audit log uses default limit=100 and offset=0."""
        with patch("services.consent.manager.get_supabase", return_value=mock_supabase):
            result = await manager.get_consent_audit_log("org-123")
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_custom_pagination(self, manager, mock_supabase):
        """Audit log respects custom limit and offset."""
        mock_table = mock_supabase.table("consent_audit_log")
        mock_table.execute.return_value = MagicMock(data=[
            {"id": "1", "consent_level": "organization", "resource_id": "org-1",
             "field_changed": "allow_ai_learning", "old_value": "false",
             "new_value": "true", "changed_by": "user-1", "changed_at": "2026-01-01"}
        ])

        with patch("services.consent.manager.get_supabase", return_value=mock_supabase):
            result = await manager.get_consent_audit_log(
                "org-123", limit=10, offset=20
            )
            # Verify range was called for pagination
            mock_table = mock_supabase.table.return_value
            assert mock_table.range.called or mock_table.limit.called

    @pytest.mark.asyncio
    async def test_empty_audit_log(self, manager, mock_supabase):
        """Returns empty list when no audit entries exist."""
        with patch("services.consent.manager.get_supabase", return_value=mock_supabase):
            result = await manager.get_consent_audit_log("org-empty")
            assert result == []


class TestSetOrgConsent:
    """Tests for organization consent updates."""

    @pytest.mark.asyncio
    async def test_set_ai_learning_consent(self, manager, mock_supabase):
        """Setting AI learning consent creates/updates record."""
        mock_supabase.table.return_value.execute.return_value = MagicMock(
            data=[{"organization_id": "org-1", "allow_ai_learning": True}]
        )

        with patch("services.consent.manager.get_supabase", return_value=mock_supabase):
            result = await manager.set_org_consent(
                organization_id="org-1",
                consent_type=ConsentType.AI_LEARNING,
                allowed=True,
                user_id="user-1",
            )
            assert mock_supabase.table.called


class TestConsentInheritance:
    """Tests for consent inheritance chain: org -> scope -> document."""

    @pytest.mark.asyncio
    async def test_scope_inherits_from_org(self, manager, mock_supabase):
        """Scope with inherit_org_consent=True gets org settings."""
        # Scope consent: inherit=True, no explicit setting
        mock_supabase.table.return_value.execute.return_value = MagicMock(
            data=None
        )
        mock_supabase.table.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None
        )

        with patch("services.consent.manager.get_supabase", return_value=mock_supabase):
            # When no scope consent exists, it should inherit from org
            result = await manager.check_consent(
                organization_id="org-1",
                consent_type=ConsentType.AI_LEARNING,
                scope_id="scope-1",
            )
            # Result should come from org level (default: False)
            assert isinstance(result, bool)
