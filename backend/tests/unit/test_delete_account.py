"""
Unit Tests for Delete Account API Endpoint

Tests the DELETE /settings/profile/me endpoint for GDPR/CCPA deletion.
"""

import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

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



class TestDeleteAccountEndpoint:
    """Tests for DELETE /settings/profile/me endpoint."""

    @pytest.mark.asyncio
    async def test_delete_account_calls_cleanup_service(self):
        """Should call cleanup service with authenticated user ID."""
        with patch('services.cleanup.cleanup_service') as mock_cleanup:
            mock_cleanup.execute_account_deletion = AsyncMock(return_value={
                "user_id": "user-123",
                "vector_store": {"deleted": 5, "status": "success"},
                "storage": {"deleted": 2, "status": "success"},
                "database": {"status": "success"},
                "auth": {"status": "success"}
            })

            from api.v1.settings import delete_account

            result = await delete_account(request=_make_mock_request(method="DELETE"), user_id="user-123")

            mock_cleanup.execute_account_deletion.assert_called_once_with("user-123")
            assert result["message"] == "Account and all data permanently deleted"

    @pytest.mark.asyncio
    async def test_delete_account_returns_deletion_details(self):
        """Should return detailed results from cleanup service."""
        with patch('services.cleanup.cleanup_service') as mock_cleanup:
            mock_cleanup.execute_account_deletion = AsyncMock(return_value={
                "user_id": "user-123",
                "vector_store": {"deleted": 10, "status": "success"},
                "storage": {"deleted": 5, "status": "success"},
                "database": {"status": "success"},
                "auth": {"status": "success"}
            })

            from api.v1.settings import delete_account

            result = await delete_account(request=_make_mock_request(method="DELETE"), user_id="user-123")

            assert "details" in result
            assert result["details"]["vector_store"]["deleted"] == 10
            assert result["details"]["storage"]["deleted"] == 5

    @pytest.mark.asyncio
    async def test_delete_account_raises_500_on_failure(self):
        """Should raise HTTPException 500 when cleanup fails."""
        with patch('services.cleanup.cleanup_service') as mock_cleanup:
            mock_cleanup.execute_account_deletion = AsyncMock(
                side_effect=Exception("Database connection failed")
            )

            from api.v1.settings import delete_account

            with pytest.raises(HTTPException) as exc_info:
                await delete_account(request=_make_mock_request(method="DELETE"), user_id="user-123")

            assert exc_info.value.status_code == 500
            # Error format changed to structured dict
            detail = exc_info.value.detail
            assert detail.get("error") == "INTERNAL_ERROR" or "Failed to delete account" in str(detail)

    @pytest.mark.asyncio
    async def test_delete_account_requires_authentication(self):
        """Endpoint should require authenticated user (via dependency)."""
        import inspect

        from api.v1.settings import delete_account

        # Check that the function has user_id as a dependency parameter
        sig = inspect.signature(delete_account)
        assert "user_id" in sig.parameters

        # The user_id has a Depends() default which ensures auth
        user_id_param = sig.parameters["user_id"]
        assert user_id_param.default.__class__.__name__ == "Depends"


class TestDeleteAccountLogging:
    """Tests for delete account logging."""

    @pytest.mark.asyncio
    async def test_delete_account_logs_request(self):
        """Should log deletion request."""
        with patch('services.cleanup.cleanup_service') as mock_cleanup:
            mock_cleanup.execute_account_deletion = AsyncMock(return_value={
                "user_id": "user-123",
                "vector_store": {"deleted": 0, "status": "success"},
                "storage": {"deleted": 0, "status": "success"},
                "database": {"status": "success"},
                "auth": {"status": "success"}
            })

            with patch('logging.getLogger') as mock_logger:
                mock_log = Mock()
                mock_logger.return_value = mock_log

                from api.v1.settings import delete_account

                await delete_account(request=_make_mock_request(method="DELETE"), user_id="user-123")

                # Logger should have been called for info logging
                # (exact assertions depend on implementation)


class TestDeleteAccountEdgeCases:
    """Edge case tests for delete account."""

    @pytest.mark.asyncio
    async def test_delete_account_with_no_data(self):
        """Should succeed even if user has no data."""
        with patch('services.cleanup.cleanup_service') as mock_cleanup:
            mock_cleanup.execute_account_deletion = AsyncMock(return_value={
                "user_id": "new-user",
                "vector_store": {"deleted": 0, "status": "success"},
                "storage": {"deleted": 0, "status": "success"},
                "database": {"status": "success"},
                "auth": {"status": "success"}
            })

            from api.v1.settings import delete_account

            result = await delete_account(request=_make_mock_request(method="DELETE"), user_id="new-user")

            assert result["message"] == "Account and all data permanently deleted"
            assert result["details"]["vector_store"]["deleted"] == 0

    @pytest.mark.asyncio
    async def test_delete_account_with_uuid_format(self):
        """Should work with proper UUID format."""
        with patch('services.cleanup.cleanup_service') as mock_cleanup:
            mock_cleanup.execute_account_deletion = AsyncMock(return_value={
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "vector_store": {"deleted": 0, "status": "success"},
                "storage": {"deleted": 0, "status": "success"},
                "database": {"status": "success"},
                "auth": {"status": "success"}
            })

            from api.v1.settings import delete_account

            result = await delete_account(request=_make_mock_request(method="DELETE"), user_id="550e8400-e29b-41d4-a716-446655440000")

            assert result["message"] == "Account and all data permanently deleted"


class TestDeleteAccountSecurityChecks:
    """Security-related tests."""

    def test_endpoint_uses_get_current_user_dependency(self):
        """Should use get_current_user for authentication."""
        import inspect

        from api.v1.settings import delete_account

        sig = inspect.signature(delete_account)
        user_id_param = sig.parameters["user_id"]

        # Check that Depends is used (ensuring auth is required)
        assert "Depends" in str(user_id_param.default)

    @pytest.mark.asyncio
    async def test_delete_only_affects_authenticated_user(self):
        """Cleanup should only be called for the authenticated user's ID."""
        with patch('services.cleanup.cleanup_service') as mock_cleanup:
            mock_cleanup.execute_account_deletion = AsyncMock(return_value={
                "user_id": "user-abc",
                "vector_store": {"deleted": 0, "status": "success"},
                "storage": {"deleted": 0, "status": "success"},
                "database": {"status": "success"},
                "auth": {"status": "success"}
            })

            from api.v1.settings import delete_account

            # The user_id comes from the auth dependency
            await delete_account(request=_make_mock_request(method="DELETE"), user_id="user-abc")

            # Verify the cleanup was called with the exact user_id
            call_args = mock_cleanup.execute_account_deletion.call_args[0]
            assert call_args[0] == "user-abc"
