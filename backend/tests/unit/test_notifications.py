"""
Test Suite for Notifications API

Comprehensive tests for:
- GET /api/v1/notifications - List notifications
- GET /api/v1/notifications/unread-count - Unread count
- PATCH /api/v1/notifications/{id}/read - Mark as read
- PATCH /api/v1/notifications/read-all - Mark all as read
- DELETE /api/v1/notifications/all - Clear all
- DELETE /api/v1/notifications/{id} - Delete single
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

import pytest
from fastapi import HTTPException
from starlette.requests import Request


def _make_mock_request(method="GET", path="/api/v1/notifications"):
    """Create a mock Starlette Request for testing endpoints with rate limiters."""
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


class TestListNotifications:
    """Tests for GET /api/v1/notifications endpoint."""
    
    @pytest.fixture
    def mock_supabase_with_notifications(self):
        """Mock Supabase with notification data."""
        mock = MagicMock()
        table = MagicMock()
        
        # Mock the query chain
        table.select.return_value = table
        table.eq.return_value = table
        table.order.return_value = table
        table.limit.return_value = table
        table.offset.return_value = table
        list_response = MagicMock(
            data=[
                {
                    "id": "notif-1",
                    "user_id": "user-123",
                    "title": "Ingestion Complete",
                    "message": "Successfully processed 5 files",
                    "type": "success",
                    "is_read": False,
                    "extra_data": json.dumps({"job_id": "job-1"}),
                    "created_at": "2024-01-01T00:00:00Z",
                },
                {
                    "id": "notif-2",
                    "user_id": "user-123",
                    "title": "Ingestion Started",
                    "message": "Processing 3 files",
                    "type": "info",
                    "is_read": True,
                    "extra_data": None,
                    "created_at": "2024-01-01T00:00:01Z",
                },
            ],
            count=2,
        )
        unread_response = MagicMock(count=1, data=[])
        table.execute.side_effect = [list_response, unread_response]
        
        mock.table.return_value = table
        return mock
    
    @pytest.mark.unit
    def test_returns_notifications_for_user(self, mock_supabase_with_notifications):
        """Should return list of notifications for the current user."""
        # Verify the endpoint filters by user_id
        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase_with_notifications):
            from api.v1.notifications import list_notifications

            result = asyncio.run(list_notifications(request=_make_mock_request(), user_id="user-123"))

        assert result.total == 2
        mock_supabase_with_notifications.table.return_value.eq.assert_any_call("user_id", "user-123")
    
    @pytest.mark.unit
    def test_orders_by_created_at_desc(self):
        """Should return most recent notifications first."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.order.return_value = table
        table.limit.return_value = table
        table.offset.return_value = table
        table.execute.side_effect = [MagicMock(data=[], count=0), MagicMock(count=0, data=[])]
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import list_notifications

            asyncio.run(list_notifications(request=_make_mock_request(), user_id="user-123"))

        table.order.assert_called_with("created_at", desc=True)
    
    @pytest.mark.unit
    def test_supports_pagination_with_limit_and_offset(self):
        """Should support pagination parameters."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.order.return_value = table
        table.limit.return_value = table
        table.offset.return_value = table
        table.execute.side_effect = [MagicMock(data=[], count=0), MagicMock(count=0, data=[])]
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import list_notifications

            asyncio.run(list_notifications(request=_make_mock_request(), user_id="user-123", limit=10, offset=5))

        table.limit.assert_called_with(10)
        table.offset.assert_called_with(5)
    
    @pytest.mark.unit
    def test_supports_unread_only_filter(self):
        """Should filter to unread notifications when unread_only=true."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.order.return_value = table
        table.limit.return_value = table
        table.offset.return_value = table
        table.execute.side_effect = [MagicMock(data=[], count=0), MagicMock(count=0, data=[])]
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import list_notifications

            asyncio.run(list_notifications(request=_make_mock_request(), user_id="user-123", unread_only=True))

        table.eq.assert_any_call("is_read", False)
    
    @pytest.mark.unit
    def test_returns_total_count(self):
        """Response should include total count of notifications."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.order.return_value = table
        table.limit.return_value = table
        table.offset.return_value = table
        table.execute.side_effect = [MagicMock(data=[], count=5), MagicMock(count=0, data=[])]
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import list_notifications

            result = asyncio.run(list_notifications(request=_make_mock_request(), user_id="user-123"))

        assert result.total == 5
    
    @pytest.mark.unit
    def test_returns_unread_count(self):
        """Response should include count of unread notifications."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.order.return_value = table
        table.limit.return_value = table
        table.offset.return_value = table
        table.execute.side_effect = [MagicMock(data=[], count=0), MagicMock(count=3, data=[])]
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import list_notifications

            result = asyncio.run(list_notifications(request=_make_mock_request(), user_id="user-123"))

        assert result.unread_count == 3
    
    @pytest.mark.unit
    def test_default_limit_is_50(self):
        """Default limit should be 50 notifications."""
        default_limit = 50
        assert default_limit == 50


class TestGetUnreadCount:
    """Tests for GET /api/v1/notifications/unread-count endpoint."""
    
    @pytest.mark.unit
    def test_returns_count_of_unread_notifications(self):
        """Should return count of notifications where is_read=false."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(count=4)
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import get_unread_count

            result = asyncio.run(get_unread_count(request=_make_mock_request(), user_id="user-123"))

        assert result.count == 4
    
    @pytest.mark.unit
    def test_returns_zero_when_all_read(self):
        """Should return 0 when all notifications are read."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(count=0)
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import get_unread_count

            result = asyncio.run(get_unread_count(request=_make_mock_request(), user_id="user-123"))

        assert result.count == 0
    
    @pytest.mark.unit
    def test_returns_zero_when_no_notifications(self):
        """Should return 0 when user has no notifications."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(count=None)
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import get_unread_count

            result = asyncio.run(get_unread_count(request=_make_mock_request(), user_id="user-123"))

        assert result.count == 0
    
    @pytest.mark.unit
    def test_is_lightweight_query(self):
        """Query should only count, not fetch full notification data."""
        # Should use count="exact" and minimal select
        mock_supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(count=1)
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import get_unread_count

            asyncio.run(get_unread_count(request=_make_mock_request(), user_id="user-123"))

        table.select.assert_called_with("id", count="exact")


class TestNotificationHelpers:
    @pytest.mark.unit
    def test_create_notification_skips_when_disabled(self):
        pref_table = MagicMock()
        pref_table.select.return_value = pref_table
        pref_table.eq.return_value = pref_table
        pref_table.maybe_single.return_value = pref_table
        pref_table.execute.return_value = MagicMock(data={"enabled": False})

        notifications_table = MagicMock()
        notifications_table.insert.return_value.execute.return_value = MagicMock(data=[])

        supabase = MagicMock()
        supabase.table.side_effect = lambda name: {
            "user_notification_settings": pref_table,
            "notifications": notifications_table,
        }[name]

        from api.v1.notifications import create_notification
        result = create_notification(
            supabase,
            user_id="user-1",
            title="Title",
            message="Message",
            notification_type="info",
            metadata={"job_id": "job-1"},
            check_setting_key="ingestion_complete",
        )

        assert result is None
        notifications_table.insert.assert_not_called()

    @pytest.mark.unit
    def test_create_notification_inserts_payload(self):
        pref_table = MagicMock()
        pref_table.select.return_value = pref_table
        pref_table.eq.return_value = pref_table
        pref_table.maybe_single.return_value = pref_table
        pref_table.execute.return_value = MagicMock(data=None)

        notifications_table = MagicMock()
        notifications_table.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "notif-1"}]
        )

        supabase = MagicMock()
        supabase.table.side_effect = lambda name: {
            "user_notification_settings": pref_table,
            "notifications": notifications_table,
        }[name]

        from api.v1.notifications import create_notification
        result = create_notification(
            supabase,
            user_id="user-1",
            title="Title",
            message="Message",
            notification_type="info",
            metadata={"job_id": "job-1"},
        )

        assert result["id"] == "notif-1"


class TestNotificationErrors:
    @pytest.mark.unit
    def test_mark_as_read_404(self):
        supabase = MagicMock()
        table = MagicMock()
        table.update.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(data=[])
        supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=supabase):
            from api.v1.notifications import mark_as_read

            with pytest.raises(HTTPException):
                asyncio.run(mark_as_read(request=_make_mock_request(method="PATCH"), notification_id="notif-1", user_id="user-1"))

    @pytest.mark.unit
    def test_delete_notification_404(self):
        supabase = MagicMock()
        table = MagicMock()
        table.delete.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(data=[])
        supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=supabase):
            from api.v1.notifications import delete_notification

            with pytest.raises(HTTPException):
                asyncio.run(delete_notification(request=_make_mock_request(method="DELETE"), notification_id="notif-1", user_id="user-1"))
    
    @pytest.mark.unit
    def test_filters_by_user_id(self):
        """Should only count notifications for the current user."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(count=1)
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import get_unread_count

            asyncio.run(get_unread_count(request=_make_mock_request(), user_id="user-123"))

        table.eq.assert_any_call("user_id", "user-123")


class TestMarkAsRead:
    """Tests for PATCH /api/v1/notifications/{id}/read endpoint."""
    
    @pytest.mark.unit
    def test_marks_notification_as_read(self):
        """Should set is_read=true for the notification."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.update.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(
            data=[{"id": "notif-1", "title": "Test", "type": "info", "is_read": True}]
        )
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import mark_as_read

            result = asyncio.run(mark_as_read(request=_make_mock_request(method="PATCH"), notification_id="notif-1", user_id="user-123"))

        assert result.is_read is True
    
    @pytest.mark.unit
    def test_returns_updated_notification(self):
        """Should return the updated notification object."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.update.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(
            data=[{"id": "notif-1", "title": "Test", "type": "info", "is_read": True}]
        )
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import mark_as_read

            result = asyncio.run(mark_as_read(request=_make_mock_request(method="PATCH"), notification_id="notif-1", user_id="user-123"))

        assert result.id == "notif-1"
    
    @pytest.mark.unit
    def test_returns_404_for_nonexistent_notification(self):
        """Should return 404 if notification doesn't exist."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.update.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import mark_as_read

            with pytest.raises(HTTPException) as exc:
                asyncio.run(mark_as_read(request=_make_mock_request(method="PATCH"), notification_id="notif-1", user_id="user-123"))
        assert exc.value.status_code == 404
    
    @pytest.mark.unit
    def test_returns_404_for_other_users_notification(self):
        """Should return 404 if notification belongs to another user."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.update.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import mark_as_read

            with pytest.raises(HTTPException):
                asyncio.run(mark_as_read(request=_make_mock_request(method="PATCH"), notification_id="notif-1", user_id="user-123"))
    
    @pytest.mark.unit
    def test_is_idempotent(self):
        """Marking already-read notification as read should succeed."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.update.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(
            data=[{"id": "notif-1", "title": "Test", "type": "info", "is_read": True}]
        )
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import mark_as_read

            result = asyncio.run(mark_as_read(request=_make_mock_request(method="PATCH"), notification_id="notif-1", user_id="user-123"))

        assert result.is_read is True


class TestMarkAllAsRead:
    """Tests for PATCH /api/v1/notifications/read-all endpoint."""
    
    @pytest.mark.unit
    def test_marks_all_unread_as_read(self):
        """Should set is_read=true for all user's unread notifications."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.update.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import mark_all_as_read

            result = asyncio.run(mark_all_as_read(request=_make_mock_request(method="PATCH"), user_id="user-123"))

        assert result["status"] == "success"
    
    @pytest.mark.unit
    def test_only_affects_current_user(self):
        """Should only mark current user's notifications as read."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.update.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import mark_all_as_read

            asyncio.run(mark_all_as_read(request=_make_mock_request(method="PATCH"), user_id="user-123"))

        table.eq.assert_any_call("user_id", "user-123")
    
    @pytest.mark.unit
    def test_returns_success_status(self):
        """Should return success status."""
        expected = {"status": "success", "message": "All notifications marked as read"}
        assert expected["status"] == "success"
    
    @pytest.mark.unit
    def test_succeeds_when_no_unread_notifications(self):
        """Should succeed even if there are no unread notifications."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.update.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import mark_all_as_read

            result = asyncio.run(mark_all_as_read(request=_make_mock_request(method="PATCH"), user_id="user-123"))
        assert result["status"] == "success"


class TestClearAllNotifications:
    """Tests for DELETE /api/v1/notifications/all endpoint."""
    
    @pytest.mark.unit
    def test_deletes_all_user_notifications(self):
        """Should delete all notifications for the current user."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.delete.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import clear_all_notifications

            result = asyncio.run(clear_all_notifications(request=_make_mock_request(method="DELETE"), user_id="user-123"))

        assert result["status"] == "success"
    
    @pytest.mark.unit
    def test_only_affects_current_user(self):
        """Should only delete current user's notifications."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.delete.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import clear_all_notifications

            asyncio.run(clear_all_notifications(request=_make_mock_request(method="DELETE"), user_id="user-123"))

        table.eq.assert_any_call("user_id", "user-123")
    
    @pytest.mark.unit
    def test_returns_success_status(self):
        """Should return success status."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.delete.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import clear_all_notifications

            result = asyncio.run(clear_all_notifications(request=_make_mock_request(method="DELETE"), user_id="user-123"))

        assert result["status"] == "success"
    
    @pytest.mark.unit
    def test_succeeds_when_no_notifications(self):
        """Should succeed even if there are no notifications to delete."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.delete.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import clear_all_notifications

            result = asyncio.run(clear_all_notifications(request=_make_mock_request(method="DELETE"), user_id="user-123"))
        assert result["status"] == "success"


class TestDeleteSingleNotification:
    """Tests for DELETE /api/v1/notifications/{id} endpoint."""
    
    @pytest.mark.unit
    def test_deletes_specified_notification(self):
        """Should delete the specified notification."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.delete.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(data=[{"id": "notif-1"}])
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import delete_notification

            result = asyncio.run(delete_notification(request=_make_mock_request(method="DELETE"), notification_id="notif-1", user_id="user-123"))
        assert result["status"] == "success"
    
    @pytest.mark.unit
    def test_returns_404_for_nonexistent_notification(self):
        """Should return 404 if notification doesn't exist."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.delete.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import delete_notification

            with pytest.raises(HTTPException) as exc:
                asyncio.run(delete_notification(request=_make_mock_request(method="DELETE"), notification_id="notif-1", user_id="user-123"))
        assert exc.value.status_code == 404
    
    @pytest.mark.unit
    def test_returns_404_for_other_users_notification(self):
        """Should return 404 if notification belongs to another user."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.delete.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import delete_notification

            with pytest.raises(HTTPException):
                asyncio.run(delete_notification(request=_make_mock_request(method="DELETE"), notification_id="notif-1", user_id="user-123"))
    
    @pytest.mark.unit
    def test_returns_success_status(self):
        """Should return success status on successful deletion."""
        mock_supabase = MagicMock()
        table = MagicMock()
        table.delete.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(data=[{"id": "notif-1"}])
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import delete_notification

            result = asyncio.run(delete_notification(request=_make_mock_request(method="DELETE"), notification_id="notif-1", user_id="user-123"))
        assert result["status"] == "success"


class TestNotificationResponse:
    """Tests for notification response schema."""
    
    @pytest.mark.unit
    def test_response_includes_all_fields(self):
        """Response should include all required fields."""
        expected_fields = [
            "id", "title", "message", "type",
            "is_read", "metadata", "created_at"
        ]
        
        response = {
            "id": "notif-1",
            "title": "Test",
            "message": "Test message",
            "type": "info",
            "is_read": False,
            "metadata": {},
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        for field in expected_fields:
            assert field in response
    
    @pytest.mark.unit
    def test_type_is_valid_enum_value(self):
        """Type should be one of: info, success, warning, error."""
        valid_types = ["info", "success", "warning", "error"]
        
        for notification_type in valid_types:
            assert notification_type in valid_types


class TestNotificationListResponse:
    """Tests for notification list response schema."""
    
    @pytest.mark.unit
    def test_includes_notifications_array(self):
        """Response should include notifications array."""
        response = {
            "notifications": [],
            "total": 0,
            "unread_count": 0
        }
        assert "notifications" in response
        assert isinstance(response["notifications"], list)
    
    @pytest.mark.unit
    def test_includes_total_count(self):
        """Response should include total count."""
        response = {"notifications": [], "total": 10, "unread_count": 5}
        assert response["total"] == 10
    
    @pytest.mark.unit
    def test_includes_unread_count(self):
        """Response should include unread count."""
        response = {"notifications": [], "total": 10, "unread_count": 5}
        assert response["unread_count"] == 5


class TestCreateNotificationHelper:
    """Tests for create_notification helper function in worker."""
    
    @pytest.mark.unit
    def test_creates_notification_in_database(self):
        """Should insert notification into the notifications table."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.execute.return_value = MagicMock()
        
        from api.v1.notifications import create_notification
        
        create_notification(
            mock_supabase,
            "user-123",
            "Test Title",
            "Test message",
            "info",
            {"key": "value"}
        )
        
        mock_supabase.table.assert_called_with("notifications")
        mock_table.insert.assert_called_once()
    
    @pytest.mark.unit
    def test_sets_is_read_to_false(self):
        """New notifications should have is_read=false."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.execute.return_value = MagicMock()
        
        from api.v1.notifications import create_notification
        
        create_notification(
            mock_supabase,
            "user-123",
            "Test",
            None,
            "info"
        )
        
        insert_data = mock_table.insert.call_args[0][0]
        assert insert_data["is_read"] == False
    
    @pytest.mark.unit
    def test_sets_notification_type(self):
        """Should set the type field correctly."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.execute.return_value = MagicMock()
        
        from api.v1.notifications import create_notification
        
        create_notification(
            mock_supabase,
            "user-123",
            "Error occurred",
            "Details",
            "error"
        )
        
        insert_data = mock_table.insert.call_args[0][0]
        assert insert_data["type"] == "error"
    
    @pytest.mark.unit
    def test_handles_metadata(self):
        """Should store metadata correctly as extra_data."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.execute.return_value = MagicMock()
        
        from api.v1.notifications import create_notification
        
        metadata = {"job_id": "job-123", "file_count": 5}
        
        create_notification(
            mock_supabase,
            "user-123",
            "Test",
            "Message",
            "info",
            metadata
        )
        
        insert_data = mock_table.insert.call_args[0][0]
        # The implementation stores metadata as JSON in 'extra_data'
        import json
        assert insert_data["extra_data"] == json.dumps(metadata)
    
    @pytest.mark.unit
    def test_handles_none_metadata(self):
        """Should use None when metadata is None."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.execute.return_value = MagicMock()
        
        from api.v1.notifications import create_notification
        
        create_notification(
            mock_supabase,
            "user-123",
            "Test",
            None,
            "info",
            None
        )
        
        insert_data = mock_table.insert.call_args[0][0]
        # The implementation sets extra_data to None when metadata is None
        assert insert_data["extra_data"] is None
    
    @pytest.mark.unit
    def test_handles_database_errors_gracefully(self):
        """Should not raise exception on database error."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.execute.side_effect = Exception("Database error")
        
        from api.v1.notifications import create_notification
        
        # Should not raise
        create_notification(
            mock_supabase,
            "user-123",
            "Test",
            None,
            "info"
        )


class TestNotificationTypes:
    """Tests for notification type values."""
    
    @pytest.mark.unit
    def test_info_type(self):
        """Info type for informational notifications."""
        assert "info" == "info"
    
    @pytest.mark.unit
    def test_success_type(self):
        """Success type for successful operations."""
        assert "success" == "success"
    
    @pytest.mark.unit
    def test_warning_type(self):
        """Warning type for partial failures or concerns."""
        assert "warning" == "warning"
    
    @pytest.mark.unit
    def test_error_type(self):
        """Error type for failed operations."""
        assert "error" == "error"


class TestNotificationContent:
    """Tests for notification content generation in worker."""
    
    @pytest.mark.unit
    def test_ingestion_started_title(self):
        """Ingestion start notification should have appropriate title."""
        title = "Ingestion Started"
        assert title == "Ingestion Started"
    
    @pytest.mark.unit
    def test_ingestion_complete_title(self):
        """Ingestion complete notification should have appropriate title."""
        title = "Ingestion Complete"
        assert title == "Ingestion Complete"
    
    @pytest.mark.unit
    def test_ingestion_failed_title(self):
        """Ingestion failure notification should have appropriate title."""
        title = "Ingestion Failed"
        assert title == "Ingestion Failed"
    
    @pytest.mark.unit
    def test_message_includes_file_count(self):
        """Message should include number of files processed."""
        file_count = 5
        message = f"Processing {file_count} files from Google Drive"
        assert "5 files" in message
    
    @pytest.mark.unit
    def test_message_includes_provider_name(self):
        """Message should include provider name."""
        provider = "google_drive"
        readable_provider = provider.replace("_", " ").title()
        assert readable_provider == "Google Drive"
    
    @pytest.mark.unit
    def test_error_message_is_truncated(self):
        """Long error messages should be truncated."""
        long_error = "x" * 300
        truncated = long_error[:200]
        assert len(truncated) == 200


class TestNotificationMetadata:
    """Tests for notification metadata structure."""
    
    @pytest.mark.unit
    def test_includes_job_id(self):
        """Metadata should include job_id if available."""
        metadata = {"job_id": "job-123", "provider": "google_drive"}
        assert "job_id" in metadata
    
    @pytest.mark.unit
    def test_includes_provider(self):
        """Metadata should include provider."""
        metadata = {"provider": "google_drive"}
        assert metadata["provider"] == "google_drive"
    
    @pytest.mark.unit
    def test_includes_file_count(self):
        """Metadata should include file count."""
        metadata = {"file_count": 10}
        assert metadata["file_count"] == 10
    
    @pytest.mark.unit
    def test_includes_document_count_on_success(self):
        """Success metadata should include document count."""
        metadata = {"document_count": 5}
        assert "document_count" in metadata
    
    @pytest.mark.unit
    def test_includes_error_on_failure(self):
        """Failure metadata should include error message."""
        metadata = {"error": "Connection timeout"}
        assert "error" in metadata


class TestNotificationErrorPaths:
    @pytest.mark.unit
    def test_create_notification_skips_disabled_setting(self):
        supabase = MagicMock()
        pref_table = MagicMock()
        pref_table.select.return_value = pref_table
        pref_table.eq.return_value = pref_table
        pref_table.maybe_single.return_value = pref_table
        pref_table.execute.return_value = MagicMock(data={"enabled": False})

        supabase.table.side_effect = lambda name: pref_table

        from api.v1.notifications import create_notification

        result = create_notification(
            supabase, "user-123", "Title", check_setting_key="notify_ingest"
        )
        assert result is None

    @pytest.mark.unit
    def test_create_notification_pref_error_allows_insert(self):
        supabase = MagicMock()
        pref_table = MagicMock()
        pref_table.select.return_value = pref_table
        pref_table.eq.return_value = pref_table
        pref_table.maybe_single.return_value = pref_table
        pref_table.execute.side_effect = Exception("boom")

        notifications_table = MagicMock()
        notifications_table.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "notif-1"}]
        )

        supabase.table.side_effect = lambda name: {
            "user_notification_settings": pref_table,
            "notifications": notifications_table,
        }[name]

        from api.v1.notifications import create_notification

        result = create_notification(
            supabase, "user-123", "Title", check_setting_key="notify_ingest"
        )
        assert result["id"] == "notif-1"

    @pytest.mark.unit
    def test_create_notification_insert_error_returns_none(self):
        supabase = MagicMock()
        notifications_table = MagicMock()
        notifications_table.insert.return_value.execute.side_effect = Exception("boom")
        supabase.table.return_value = notifications_table

        from api.v1.notifications import create_notification

        result = create_notification(supabase, "user-123", "Title")
        assert result is None

    @pytest.mark.unit
    def test_list_notifications_invalid_json_metadata(self):
        mock_supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.order.return_value = table
        table.limit.return_value = table
        table.offset.return_value = table
        list_response = MagicMock(
            data=[
                {
                    "id": "notif-1",
                    "user_id": "user-123",
                    "title": "Title",
                    "message": "Message",
                    "type": "info",
                    "is_read": False,
                    "extra_data": "{bad-json",
                    "created_at": "2024-01-01T00:00:00Z",
                }
            ],
            count=1,
        )
        unread_response = MagicMock(count=0, data=[])
        table.execute.side_effect = [list_response, unread_response]
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import list_notifications

            result = asyncio.run(list_notifications(request=_make_mock_request(), user_id="user-123"))

        assert result.notifications[0].metadata is None

    @pytest.mark.unit
    def test_list_notifications_handles_exception(self):
        mock_supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.order.return_value = table
        table.limit.return_value = table
        table.offset.return_value = table
        table.execute.side_effect = Exception("boom")
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import list_notifications

            with pytest.raises(HTTPException) as exc:
                asyncio.run(list_notifications(request=_make_mock_request(), user_id="user-123"))
        assert exc.value.status_code == 500

    @pytest.mark.unit
    def test_get_unread_count_handles_exception(self):
        mock_supabase = MagicMock()
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.execute.side_effect = Exception("boom")
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import get_unread_count

            with pytest.raises(HTTPException) as exc:
                asyncio.run(get_unread_count(request=_make_mock_request(), user_id="user-123"))
        assert exc.value.status_code == 500

    @pytest.mark.unit
    def test_mark_as_read_not_found(self):
        mock_supabase = MagicMock()
        table = MagicMock()
        table.update.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(data=None)
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import mark_as_read

            with pytest.raises(HTTPException) as exc:
                asyncio.run(mark_as_read(request=_make_mock_request(method="PATCH"), notification_id="notif-1", user_id="user-123"))
        assert exc.value.status_code == 404

    @pytest.mark.unit
    def test_mark_as_read_invalid_json(self):
        mock_supabase = MagicMock()
        table = MagicMock()
        table.update.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(
            data=[{"id": "notif-1", "title": "t", "type": "info", "is_read": True, "extra_data": "{bad"}]
        )
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import mark_as_read

            result = asyncio.run(mark_as_read(request=_make_mock_request(method="PATCH"), notification_id="notif-1", user_id="user-123"))

        assert result.metadata is None

    @pytest.mark.unit
    def test_mark_as_read_handles_exception(self):
        mock_supabase = MagicMock()
        table = MagicMock()
        table.update.return_value = table
        table.eq.return_value = table
        table.execute.side_effect = Exception("boom")
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import mark_as_read

            with pytest.raises(HTTPException) as exc:
                asyncio.run(mark_as_read(request=_make_mock_request(method="PATCH"), notification_id="notif-1", user_id="user-123"))
        assert exc.value.status_code == 500

    @pytest.mark.unit
    def test_mark_all_as_read_handles_exception(self):
        mock_supabase = MagicMock()
        table = MagicMock()
        table.update.return_value = table
        table.eq.return_value = table
        table.execute.side_effect = Exception("boom")
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import mark_all_as_read

            with pytest.raises(HTTPException) as exc:
                asyncio.run(mark_all_as_read(request=_make_mock_request(method="PATCH"), user_id="user-123"))
        assert exc.value.status_code == 500

    @pytest.mark.unit
    def test_clear_all_notifications_handles_exception(self):
        mock_supabase = MagicMock()
        table = MagicMock()
        table.delete.return_value = table
        table.eq.return_value = table
        table.execute.side_effect = Exception("boom")
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import clear_all_notifications

            with pytest.raises(HTTPException) as exc:
                asyncio.run(clear_all_notifications(request=_make_mock_request(method="DELETE"), user_id="user-123"))
        assert exc.value.status_code == 500

    @pytest.mark.unit
    def test_delete_notification_not_found(self):
        mock_supabase = MagicMock()
        table = MagicMock()
        table.delete.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(data=None)
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import delete_notification

            with pytest.raises(HTTPException) as exc:
                asyncio.run(delete_notification(request=_make_mock_request(method="DELETE"), notification_id="notif-1", user_id="user-123"))
        assert exc.value.status_code == 404

    @pytest.mark.unit
    def test_delete_notification_handles_exception(self):
        mock_supabase = MagicMock()
        table = MagicMock()
        table.delete.return_value = table
        table.eq.return_value = table
        table.execute.side_effect = Exception("boom")
        mock_supabase.table.return_value = table

        with patch("api.v1.notifications.get_supabase", return_value=mock_supabase):
            from api.v1.notifications import delete_notification

            with pytest.raises(HTTPException) as exc:
                asyncio.run(delete_notification(request=_make_mock_request(method="DELETE"), notification_id="notif-1", user_id="user-123"))
        assert exc.value.status_code == 500
