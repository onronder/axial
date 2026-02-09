from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException

from api.v1 import admin


def _make_mock_request(method="GET", path="/api/v1"):
    """Create a mock Starlette Request for testing endpoints with rate limiters."""
    from starlette.requests import Request
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": [],
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 12345),
        "app": None,
    }
    return Request(scope=scope)



class TestAdminAuditLogs:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_audit_logs_returns_items(self):
        supabase = MagicMock()
        query = MagicMock()
        query.select.return_value = query
        query.eq.return_value = query
        query.in_.return_value = query
        query.gte.return_value = query
        query.lte.return_value = query
        query.order.return_value = query
        query.range.return_value = query
        query.execute.return_value = Mock(
            data=[
                {
                    "id": "log-1",
                    "user_id": "user-1",
                    "action": "document.delete",
                    "resource_type": "document",
                    "resource_id": "doc-1",
                    "details": {},
                    "ip_address": "127.0.0.1",
                    "created_at": "2024-01-01T00:00:00Z",
                }
            ],
            count=1,
        )
        supabase.table.return_value = query

        with patch("api.v1.admin.get_supabase", return_value=supabase), \
             patch("api.v1.admin.team_service.get_user_team", new=AsyncMock(return_value={"user_role": "owner"})):
            result = await admin.get_audit_logs(
                request=_make_mock_request(),
                user_id="user-1",
                limit=10,
                offset=0,
                action="document.delete",
                resource_type="document",
                from_date="2024-01-01T00:00:00Z",
                to_date="2024-01-31T00:00:00Z",
            )

        assert result.total == 1
        assert result.items[0].action == "document.delete"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_audit_logs_blocks_non_admin(self):
        supabase = MagicMock()

        with patch("api.v1.admin.get_supabase", return_value=supabase), \
             patch("api.v1.admin.team_service.get_user_team", new=AsyncMock(return_value={"user_role": "viewer"})):
            with pytest.raises(HTTPException) as excinfo:
                await admin.get_audit_logs(request=_make_mock_request(), user_id="user-1")

        assert excinfo.value.status_code == 403

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_audit_logs_handles_failure(self):
        supabase = MagicMock()
        query = MagicMock()
        query.select.return_value = query
        query.eq.return_value = query
        query.order.return_value = query
        query.range.return_value = query
        query.execute.side_effect = Exception("db failure")
        supabase.table.return_value = query

        with patch("api.v1.admin.get_supabase", return_value=supabase), \
             patch("api.v1.admin.team_service.get_user_team", new=AsyncMock(return_value={"user_role": "owner"})):
            with pytest.raises(HTTPException) as excinfo:
                await admin.get_audit_logs(request=_make_mock_request(), user_id="user-1")

        assert excinfo.value.status_code == 500


class TestAdminAuditActions:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_audit_log_actions(self):
        result = await admin.get_audit_log_actions(request=_make_mock_request(), user_id="user-1")
        assert "document.delete" in result["actions"]
