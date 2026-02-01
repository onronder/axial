"""
Comprehensive Unit Tests for Feedback API Router

Tests all feedback endpoints:
- POST /chat/feedback - Submit feedback
- GET /chat/feedback/conversation/{id} - Get user feedback for conversation
- GET /analytics/feedback - Team feedback analytics (admin)
- GET /analytics/feedback/sources - Source quality metrics (admin)
- GET /admin/feedback/platform - Platform-wide analytics (platform admin)
- POST /admin/feedback/refresh-metrics - Refresh materialized view (platform admin)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi import HTTPException
from starlette.requests import Request
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _make_mock_request(method="POST", path="/api/v1/chat/feedback"):
    """Helper to create mock requests for feedback endpoints."""
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


class TestSubmitFeedbackValidation:
    """Test request validation for submit_feedback."""

    def test_submit_feedback_request_validates_rating(self):
        """Rating must be 'positive' or 'negative'."""
        from api.v1.feedback import SubmitFeedbackRequest
        from pydantic import ValidationError

        # Valid ratings should work
        valid = SubmitFeedbackRequest(
            message_id="msg-1",
            rating="positive",
            query_text="What is X?",
            answer_preview="X is...",
        )
        assert valid.rating == "positive"

        valid_neg = SubmitFeedbackRequest(
            message_id="msg-2",
            rating="negative",
            query_text="What is Y?",
            answer_preview="Y is...",
        )
        assert valid_neg.rating == "negative"

        # Invalid rating should fail
        with pytest.raises(ValidationError):
            SubmitFeedbackRequest(
                message_id="msg-3",
                rating="neutral",  # Invalid
                query_text="What?",
                answer_preview="Answer",
            )

    def test_submit_feedback_request_limits_feedback_text(self):
        """feedback_text must be 100 characters or less."""
        from api.v1.feedback import SubmitFeedbackRequest
        from pydantic import ValidationError

        # Valid short text
        valid = SubmitFeedbackRequest(
            message_id="msg-1",
            rating="positive",
            query_text="Q",
            answer_preview="A",
            feedback_text="Good answer!",
        )
        assert valid.feedback_text == "Good answer!"

        # Text exactly at limit
        valid_max = SubmitFeedbackRequest(
            message_id="msg-1",
            rating="positive",
            query_text="Q",
            answer_preview="A",
            feedback_text="x" * 100,
        )
        assert len(valid_max.feedback_text) == 100

        # Text over limit should fail
        with pytest.raises(ValidationError):
            SubmitFeedbackRequest(
                message_id="msg-1",
                rating="positive",
                query_text="Q",
                answer_preview="A",
                feedback_text="x" * 101,
            )


class TestSubmitFeedbackEndpoint:
    """Test POST /chat/feedback endpoint."""

    @pytest.mark.asyncio
    async def test_submit_feedback_success(self):
        """Successful feedback submission."""
        from api.v1.feedback import submit_feedback, SubmitFeedbackRequest

        mock_supabase = MagicMock()
        
        # Mock message lookup
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = Mock(
            data={"id": "msg-1", "conversation_id": "conv-1", "role": "assistant"}
        )
        
        # Mock conversation lookup (for second call)
        conversation_mock = MagicMock()
        conversation_mock.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = Mock(
            data={"id": "conv-1", "organization_id": "org-1"}
        )
        
        def table_router(name):
            if name == "messages":
                msg_mock = MagicMock()
                msg_mock.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = Mock(
                    data={"id": "msg-1", "conversation_id": "conv-1", "role": "assistant"}
                )
                return msg_mock
            elif name == "conversations":
                return conversation_mock
            return MagicMock()

        mock_supabase.table = table_router

        mock_feedback_service = AsyncMock(return_value={
            "id": "fb-1",
            "message_id": "msg-1",
            "rating": "positive",
            "created_at": "2024-01-01T00:00:00Z",
            "is_update": False,
        })

        payload = SubmitFeedbackRequest(
            message_id="msg-1",
            rating="positive",
            query_text="What is X?",
            answer_preview="X is...",
        )

        with patch("api.v1.feedback.get_supabase", return_value=mock_supabase), \
             patch("api.v1.feedback.feedback_service.submit_feedback", mock_feedback_service):
            result = await submit_feedback(
                request=_make_mock_request(),
                payload=payload,
                user_id="user-1",
                organization_id="org-1",
            )

        assert result.id == "fb-1"
        assert result.rating == "positive"

    @pytest.mark.asyncio
    async def test_submit_feedback_message_not_found(self):
        """Returns 404 if message doesn't exist."""
        from api.v1.feedback import submit_feedback, SubmitFeedbackRequest

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = Mock(
            data=None
        )

        payload = SubmitFeedbackRequest(
            message_id="nonexistent",
            rating="positive",
            query_text="Q",
            answer_preview="A",
        )

        with patch("api.v1.feedback.get_supabase", return_value=mock_supabase):
            with pytest.raises(HTTPException) as exc:
                await submit_feedback(
                    request=_make_mock_request(),
                    payload=payload,
                    user_id="user-1",
                    organization_id="org-1",
                )
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_submit_feedback_user_message_rejected(self):
        """Returns 400 if trying to rate a user message."""
        from api.v1.feedback import submit_feedback, SubmitFeedbackRequest

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = Mock(
            data={"id": "msg-1", "conversation_id": "conv-1", "role": "user"}  # Not assistant
        )

        payload = SubmitFeedbackRequest(
            message_id="msg-1",
            rating="positive",
            query_text="Q",
            answer_preview="A",
        )

        with patch("api.v1.feedback.get_supabase", return_value=mock_supabase):
            with pytest.raises(HTTPException) as exc:
                await submit_feedback(
                    request=_make_mock_request(),
                    payload=payload,
                    user_id="user-1",
                    organization_id="org-1",
                )
            assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_submit_feedback_conversation_org_mismatch(self):
        """Returns 403 if conversation belongs to different org."""
        from api.v1.feedback import submit_feedback, SubmitFeedbackRequest

        def table_router(name):
            if name == "messages":
                mock = MagicMock()
                mock.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = Mock(
                    data={"id": "msg-1", "conversation_id": "conv-1", "role": "assistant"}
                )
                return mock
            elif name == "conversations":
                mock = MagicMock()
                mock.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = Mock(
                    data={"id": "conv-1", "organization_id": "other-org"}  # Different org
                )
                return mock
            return MagicMock()

        mock_supabase = MagicMock()
        mock_supabase.table = table_router

        payload = SubmitFeedbackRequest(
            message_id="msg-1",
            rating="positive",
            query_text="Q",
            answer_preview="A",
        )

        with patch("api.v1.feedback.get_supabase", return_value=mock_supabase):
            with pytest.raises(HTTPException) as exc:
                await submit_feedback(
                    request=_make_mock_request(),
                    payload=payload,
                    user_id="user-1",
                    organization_id="org-1",
                )
            assert exc.value.status_code == 403


class TestGetConversationFeedback:
    """Test GET /chat/feedback/conversation/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_conversation_feedback_success(self):
        """Returns user feedback mapping for conversation."""
        from api.v1.feedback import get_conversation_feedback

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = Mock(
            data={"id": "conv-1"}
        )

        mock_feedback_service = AsyncMock(return_value={
            "msg-1": "positive",
            "msg-2": "negative",
        })

        with patch("api.v1.feedback.get_supabase", return_value=mock_supabase), \
             patch("api.v1.feedback.feedback_service.get_user_feedback_for_conversation", mock_feedback_service):
            result = await get_conversation_feedback(
                request=_make_mock_request("GET"),
                conversation_id="conv-1",
                user_id="user-1",
            )

        assert result.feedback == {"msg-1": "positive", "msg-2": "negative"}

    @pytest.mark.asyncio
    async def test_get_conversation_feedback_not_found(self):
        """Returns 404 if conversation doesn't exist."""
        from api.v1.feedback import get_conversation_feedback

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = Mock(
            data=None
        )

        with patch("api.v1.feedback.get_supabase", return_value=mock_supabase):
            with pytest.raises(HTTPException) as exc:
                await get_conversation_feedback(
                    request=_make_mock_request("GET"),
                    conversation_id="nonexistent",
                    user_id="user-1",
                )
            assert exc.value.status_code == 404


class TestTeamFeedbackAnalytics:
    """Test GET /analytics/feedback endpoint."""

    @pytest.mark.asyncio
    async def test_get_team_feedback_success(self):
        """Returns paginated feedback with summary."""
        from api.v1.feedback import get_team_feedback

        mock_supabase = MagicMock()
        
        mock_feedback_service = AsyncMock(return_value={
            "items": [
                {
                    "id": "fb-1",
                    "rating": "negative",
                    "feedback_text": "Wrong answer",
                    "query_text": "What is X?",
                    "answer_preview": "X is...",
                    "sources": [],
                    "user_email": "user@test.com",
                    "created_at": "2024-01-01T00:00:00Z",
                }
            ],
            "total": 1,
            "has_more": False,
            "summary": {
                "positive_count": 5,
                "negative_count": 3,
                "total_count": 8,
                "negative_rate_pct": 37.5,
            },
        })

        with patch("api.v1.feedback.get_supabase", return_value=mock_supabase), \
             patch("api.v1.feedback.feedback_service.get_team_feedback", mock_feedback_service):
            result = await get_team_feedback(
                request=_make_mock_request("GET"),
                user_id="admin-1",
                organization_id="org-1",
                limit=50,
                offset=0,
                rating=None,
                from_date=None,
                to_date=None,
                source_label=None,
            )

        assert result.total == 1
        assert result.summary.negative_rate_pct == 37.5
        assert len(result.items) == 1

    @pytest.mark.asyncio
    async def test_get_team_feedback_invalid_rating_filter(self):
        """Returns 400 for invalid rating filter."""
        from api.v1.feedback import get_team_feedback

        mock_supabase = MagicMock()

        with patch("api.v1.feedback.get_supabase", return_value=mock_supabase):
            with pytest.raises(HTTPException) as exc:
                await get_team_feedback(
                    request=_make_mock_request("GET"),
                    user_id="admin-1",
                    organization_id="org-1",
                    rating="invalid",  # Not 'positive' or 'negative'
                )
            assert exc.value.status_code == 400


class TestSourceMetrics:
    """Test GET /analytics/feedback/sources endpoint."""

    @pytest.mark.asyncio
    async def test_get_source_metrics_success(self):
        """Returns source quality metrics."""
        from api.v1.feedback import get_source_metrics

        mock_supabase = MagicMock()
        
        mock_feedback_service = AsyncMock(return_value={
            "items": [
                {
                    "source_label": "Doc 1",
                    "source_type": "file_upload",
                    "source_url": None,
                    "positive_count": 10,
                    "negative_count": 5,
                    "total_feedback": 15,
                    "negative_rate_pct": 33.3,
                    "last_feedback_at": "2024-01-01T00:00:00Z",
                }
            ],
            "total": 1,
        })

        with patch("api.v1.feedback.get_supabase", return_value=mock_supabase), \
             patch("api.v1.feedback.feedback_service.get_source_metrics", mock_feedback_service):
            result = await get_source_metrics(
                request=_make_mock_request("GET"),
                user_id="admin-1",
                organization_id="org-1",
                min_feedback_count=5,
                sort_by="negative_rate_pct",
                sort_order="desc",
                limit=20,
            )

        assert result.total == 1
        assert result.items[0].source_label == "Doc 1"

    @pytest.mark.asyncio
    async def test_get_source_metrics_invalid_sort_order(self):
        """Returns 400 for invalid sort_order."""
        from api.v1.feedback import get_source_metrics

        mock_supabase = MagicMock()

        with patch("api.v1.feedback.get_supabase", return_value=mock_supabase):
            with pytest.raises(HTTPException) as exc:
                await get_source_metrics(
                    request=_make_mock_request("GET"),
                    user_id="admin-1",
                    organization_id="org-1",
                    sort_order="invalid",  # Not 'asc' or 'desc'
                )
            assert exc.value.status_code == 400


class TestPlatformAdmin:
    """Test platform admin dependency and endpoints."""

    @pytest.mark.asyncio
    async def test_require_platform_admin_axiohub_email(self):
        """@axiohub.io email grants platform admin access."""
        from api.v1.feedback import require_platform_admin

        mock_supabase = MagicMock()
        mock_user_result = Mock()
        mock_user_result.user = Mock()
        mock_user_result.user.email = "admin@axiohub.io"
        mock_supabase.auth.admin.get_user_by_id.return_value = mock_user_result

        with patch("api.v1.feedback.get_supabase", return_value=mock_supabase):
            result = await require_platform_admin(user_id="user-1")
        
        assert result == "user-1"

    @pytest.mark.asyncio
    async def test_require_platform_admin_flag(self):
        """is_platform_admin flag grants access."""
        from api.v1.feedback import require_platform_admin

        mock_supabase = MagicMock()
        # User has non-axiohub email
        mock_user_result = Mock()
        mock_user_result.user = Mock()
        mock_user_result.user.email = "user@other.com"
        mock_supabase.auth.admin.get_user_by_id.return_value = mock_user_result
        
        # But has is_platform_admin flag
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = Mock(
            data={"is_platform_admin": True}
        )

        with patch("api.v1.feedback.get_supabase", return_value=mock_supabase):
            result = await require_platform_admin(user_id="user-1")
        
        assert result == "user-1"

    @pytest.mark.asyncio
    async def test_require_platform_admin_denied(self):
        """Non-admin users are denied."""
        from api.v1.feedback import require_platform_admin

        mock_supabase = MagicMock()
        mock_user_result = Mock()
        mock_user_result.user = Mock()
        mock_user_result.user.email = "user@other.com"
        mock_supabase.auth.admin.get_user_by_id.return_value = mock_user_result
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = Mock(
            data={"is_platform_admin": False}
        )

        with patch("api.v1.feedback.get_supabase", return_value=mock_supabase):
            with pytest.raises(HTTPException) as exc:
                await require_platform_admin(user_id="user-1")
            assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_platform_feedback_success(self):
        """Platform admin can access platform-wide feedback."""
        from api.v1.feedback import get_platform_feedback

        mock_supabase = MagicMock()
        
        mock_feedback_service = AsyncMock(return_value={
            "items": [],
            "total": 0,
            "has_more": False,
        })

        with patch("api.v1.feedback.get_supabase", return_value=mock_supabase), \
             patch("api.v1.feedback.feedback_service.get_platform_feedback", mock_feedback_service):
            result = await get_platform_feedback(
                request=_make_mock_request("GET"),
                user_id="admin-1",
            )

        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_refresh_metrics_success(self):
        """Platform admin can refresh metrics view."""
        from api.v1.feedback import refresh_metrics

        mock_supabase = MagicMock()
        mock_feedback_service = AsyncMock()

        with patch("api.v1.feedback.get_supabase", return_value=mock_supabase), \
             patch("api.v1.feedback.feedback_service.refresh_metrics", mock_feedback_service):
            result = await refresh_metrics(
                request=_make_mock_request("POST"),
                user_id="admin-1",
            )

        assert result["status"] == "success"
        mock_feedback_service.assert_called_once()


class TestFeedbackErrorHandling:
    """Test error handling in feedback endpoints."""

    @pytest.mark.asyncio
    async def test_submit_feedback_db_error(self):
        """Database errors are handled gracefully."""
        from api.v1.feedback import submit_feedback, SubmitFeedbackRequest

        def table_router(name):
            if name == "messages":
                mock = MagicMock()
                mock.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = Mock(
                    data={"id": "msg-1", "conversation_id": "conv-1", "role": "assistant"}
                )
                return mock
            elif name == "conversations":
                mock = MagicMock()
                mock.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = Mock(
                    data={"id": "conv-1", "organization_id": "org-1"}
                )
                return mock
            return MagicMock()

        mock_supabase = MagicMock()
        mock_supabase.table = table_router

        mock_feedback_service = AsyncMock(side_effect=Exception("Database error"))

        payload = SubmitFeedbackRequest(
            message_id="msg-1",
            rating="positive",
            query_text="Q",
            answer_preview="A",
        )

        with patch("api.v1.feedback.get_supabase", return_value=mock_supabase), \
             patch("api.v1.feedback.feedback_service.submit_feedback", mock_feedback_service):
            with pytest.raises(HTTPException) as exc:
                await submit_feedback(
                    request=_make_mock_request(),
                    payload=payload,
                    user_id="user-1",
                    organization_id="org-1",
                )
            assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_get_conversation_feedback_db_error(self):
        """Database errors handled in conversation feedback."""
        from api.v1.feedback import get_conversation_feedback

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = Mock(
            data={"id": "conv-1"}
        )

        mock_feedback_service = AsyncMock(side_effect=Exception("Database error"))

        with patch("api.v1.feedback.get_supabase", return_value=mock_supabase), \
             patch("api.v1.feedback.feedback_service.get_user_feedback_for_conversation", mock_feedback_service):
            with pytest.raises(HTTPException) as exc:
                await get_conversation_feedback(
                    request=_make_mock_request("GET"),
                    conversation_id="conv-1",
                    user_id="user-1",
                )
            assert exc.value.status_code == 500


class TestSourceSnapshotModel:
    """Test SourceSnapshot request model."""

    def test_source_snapshot_all_fields(self):
        """SourceSnapshot accepts all optional fields."""
        from api.v1.feedback import SourceSnapshot

        source = SourceSnapshot(
            index=1,
            type="file_upload",
            label="Document.pdf",
            url="https://storage.example.com/doc.pdf",
            page=5,
            section="Introduction",
        )
        
        assert source.index == 1
        assert source.type == "file_upload"
        assert source.label == "Document.pdf"
        assert source.page == 5

    def test_source_snapshot_minimal(self):
        """SourceSnapshot works with no fields."""
        from api.v1.feedback import SourceSnapshot

        source = SourceSnapshot()
        assert source.index is None
        assert source.type is None


class TestResponseModels:
    """Test response model construction."""

    def test_feedback_response_model(self):
        """FeedbackResponse model works correctly."""
        from api.v1.feedback import FeedbackResponse

        response = FeedbackResponse(
            id="fb-1",
            message_id="msg-1",
            rating="positive",
            created_at="2024-01-01T00:00:00Z",
            is_update=False,
        )
        
        assert response.id == "fb-1"
        assert response.is_update is False

    def test_feedback_summary_model(self):
        """FeedbackSummary model calculates correctly."""
        from api.v1.feedback import FeedbackSummary

        summary = FeedbackSummary(
            positive_count=7,
            negative_count=3,
            total_count=10,
            negative_rate_pct=30.0,
        )
        
        assert summary.total_count == 10
        assert summary.negative_rate_pct == 30.0

    def test_source_metric_item_model(self):
        """SourceMetricItem model works correctly."""
        from api.v1.feedback import SourceMetricItem

        item = SourceMetricItem(
            source_label="Important Doc",
            source_type="google_drive",
            source_url="https://drive.google.com/file/123",
            positive_count=20,
            negative_count=5,
            total_feedback=25,
            negative_rate_pct=20.0,
            last_feedback_at="2024-01-15T00:00:00Z",
        )
        
        assert item.source_label == "Important Doc"
        assert item.negative_rate_pct == 20.0
