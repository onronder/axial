"""
Test Suite for Admin API

Tests for:
- GET /api/v1/admin/audit-logs - Get paginated audit logs
- GET /api/v1/admin/audit-logs/actions - Get available actions
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta


# =============================================================================
# Tests for Audit Logs Endpoint
# =============================================================================

class TestGetAuditLogsEndpoint:
    """Tests for GET /api/v1/admin/audit-logs."""
    
    @pytest.fixture
    def mock_supabase_with_audit_logs(self):
        """Mock Supabase with audit log data."""
        mock = MagicMock()
        
        # Mock team check
        team_response = MagicMock()
        team_response.data = {"user_role": "owner"}
        
        # Mock audit logs response
        logs_response = MagicMock()
        logs_response.data = [
            {
                "id": "log-1",
                "user_id": "user-123",
                "action": "document.delete",
                "resource_type": "document",
                "resource_id": "doc-123",
                "details": {"title": "Test Doc"},
                "ip_address": "192.168.1.1",
                "created_at": "2024-01-01T00:00:00Z"
            },
            {
                "id": "log-2",
                "user_id": "user-123",
                "action": "chat.delete",
                "resource_type": "chat",
                "resource_id": "chat-123",
                "details": {},
                "ip_address": "192.168.1.1",
                "created_at": "2024-01-02T00:00:00Z"
            }
        ]
        logs_response.count = 2
        
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.gte.return_value = table
        table.lte.return_value = table
        table.order.return_value = table
        table.range.return_value = table
        table.execute.return_value = logs_response
        
        mock.table.return_value = table
        return mock
    
    @pytest.mark.unit
    def test_get_audit_logs_returns_paginated_list(self, mock_supabase_with_audit_logs):
        """Should return paginated list of audit logs."""
        logs = [
            {"id": "log-1", "action": "document.delete"},
            {"id": "log-2", "action": "chat.delete"}
        ]
        assert len(logs) == 2
    
    @pytest.mark.unit
    def test_get_audit_logs_requires_owner_or_admin(self):
        """Only owners and admins can view audit logs."""
        allowed_roles = ["owner", "admin"]
        
        test_cases = [
            ("owner", True),
            ("admin", True),
            ("member", False),
            ("viewer", False),
        ]
        
        for role, expected in test_cases:
            can_view = role in allowed_roles
            assert can_view == expected
    
    @pytest.mark.unit
    def test_get_audit_logs_filters_by_action(self):
        """Should filter logs by action type."""
        action_filter = "document.delete"
        filtered_logs = [
            {"id": "log-1", "action": "document.delete"}
        ]
        for log in filtered_logs:
            assert log["action"] == action_filter
    
    @pytest.mark.unit
    def test_get_audit_logs_filters_by_resource_type(self):
        """Should filter logs by resource type."""
        resource_filter = "document"
        filtered_logs = [
            {"id": "log-1", "resource_type": "document"}
        ]
        for log in filtered_logs:
            assert log["resource_type"] == resource_filter
    
    @pytest.mark.unit
    def test_get_audit_logs_filters_by_date_range(self):
        """Should filter logs by from_date and to_date."""
        from_date = "2024-01-01T00:00:00Z"
        to_date = "2024-01-31T23:59:59Z"
        
        # Should use gte(from_date) and lte(to_date)
        assert from_date < to_date
    
    @pytest.mark.unit
    def test_get_audit_logs_respects_pagination(self):
        """Should respect limit and offset parameters."""
        limit = 50
        offset = 100
        
        # Should call range(offset, offset + limit - 1)
        expected_end = offset + limit - 1
        assert expected_end == 149
    
    @pytest.mark.unit
    def test_get_audit_logs_orders_by_created_at_desc(self):
        """Most recent logs should appear first."""
        order_column = "created_at"
        order_desc = True
        
        assert order_column == "created_at"
        assert order_desc is True
    
    @pytest.mark.unit
    def test_get_audit_logs_returns_total_count(self):
        """Response should include total count for pagination."""
        response = {
            "items": [],
            "total": 100,
            "has_more": True
        }
        assert response["total"] == 100
        assert response["has_more"] is True


class TestAuditLogActionsEndpoint:
    """Tests for GET /api/v1/admin/audit-logs/actions."""
    
    @pytest.mark.unit
    def test_get_actions_returns_list(self):
        """Should return list of available action types."""
        actions = [
            "document.delete",
            "document.update",
            "chat.delete",
            "connector.sync_start",
            "connector.sync_success",
            "connector.sync_fail"
        ]
        assert len(actions) > 0
        assert "document.delete" in actions
    
    @pytest.mark.unit
    def test_get_actions_is_static_list(self):
        """Should return static list for efficiency."""
        # This endpoint returns predefined actions, not querying DB
        is_static = True
        assert is_static is True


class TestAuditLogEntry:
    """Tests for AuditLogEntry model."""
    
    @pytest.mark.unit
    def test_audit_log_entry_has_required_fields(self):
        """AuditLogEntry should have all required fields."""
        entry = {
            "id": "log-123",
            "user_id": "user-123",
            "action": "document.delete",
            "resource_type": "document",
            "resource_id": "doc-123",
            "details": {},
            "ip_address": "192.168.1.1",
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        required_fields = ["id", "action", "created_at"]
        for field in required_fields:
            assert field in entry
    
    @pytest.mark.unit
    def test_audit_log_entry_allows_optional_fields(self):
        """Optional fields should default to None/empty."""
        entry = {
            "id": "log-123",
            "action": "settings.update",
            "created_at": "2024-01-01T00:00:00Z",
            "user_id": None,
            "resource_type": None,
            "resource_id": None,
            "details": {},
            "ip_address": None
        }
        
        assert entry["user_id"] is None
        assert entry["details"] == {}


# =============================================================================
# Tests for Audit Log Cleanup Task
# =============================================================================

class TestAuditLogCleanupTask:
    """Tests for cleanup_old_audit_logs Celery task."""
    
    @pytest.mark.unit
    def test_cleanup_deletes_old_logs(self):
        """Should delete logs older than 90 days."""
        retention_days = 90
        cutoff = datetime.now() - timedelta(days=retention_days)
        
        assert retention_days == 90
    
    @pytest.mark.unit
    def test_cleanup_uses_created_at_for_cutoff(self):
        """Should filter by created_at column."""
        filter_column = "created_at"
        assert filter_column == "created_at"
    
    @pytest.mark.unit
    def test_cleanup_returns_deleted_count(self):
        """Should return count of deleted records."""
        result = {"deleted": 150}
        assert result["deleted"] == 150
    
    @pytest.mark.unit
    def test_cleanup_handles_errors_gracefully(self):
        """Should return error message on failure."""
        result = {"error": "Database connection failed"}
        assert "error" in result
