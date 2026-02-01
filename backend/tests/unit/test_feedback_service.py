"""
Comprehensive tests for Feedback Service.

Tests cover:
- Feedback submission (new and update)
- Validation errors
- User feedback retrieval
- Team feedback listing
- Source metrics
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from datetime import datetime, timezone

from services.feedback_service import feedback_service, FeedbackService


class TestSubmitFeedback:
    """Test feedback submission functionality."""

    @pytest.mark.asyncio
    async def test_submit_new_feedback(self):
        """Should create new feedback when none exists."""
        mock_supabase = MagicMock()
        
        # Mock checking for existing feedback (none found)
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = Mock(data=None)
        
        # Mock insert
        mock_supabase.table.return_value.insert.return_value.execute.return_value = Mock(
            data=[{
                "id": "fb-123",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }]
        )
        
        result = await feedback_service.submit_feedback(
            supabase=mock_supabase,
            user_id="user-123",
            organization_id="org-456",
            message_id="msg-789",
            conversation_id="conv-101",
            rating="positive",
            query_text="What is AI?",
            answer_preview="AI stands for...",
            sources_snapshot=[{"doc_id": "doc-1"}],
            feedback_text="Great answer!"
        )
        
        assert result["id"] == "fb-123"
        assert result["rating"] == "positive"
        assert result["is_update"] is False

    @pytest.mark.asyncio
    async def test_update_existing_feedback(self):
        """Should update feedback when it already exists."""
        mock_supabase = MagicMock()
        
        # Mock checking for existing feedback (found)
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = Mock(
            data={"id": "fb-existing", "created_at": "2024-01-01T00:00:00Z"}
        )
        
        # Mock update
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock(
            data=[{
                "id": "fb-existing",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z"
            }]
        )
        
        result = await feedback_service.submit_feedback(
            supabase=mock_supabase,
            user_id="user-123",
            organization_id="org-456",
            message_id="msg-789",
            conversation_id="conv-101",
            rating="negative",
            query_text="What is AI?",
            answer_preview="AI stands for...",
            sources_snapshot=[],
        )
        
        assert result["id"] == "fb-existing"
        assert result["rating"] == "negative"
        assert result["is_update"] is True

    @pytest.mark.asyncio
    async def test_invalid_rating_raises_error(self):
        """Should raise ValueError for invalid rating."""
        mock_supabase = MagicMock()
        
        with pytest.raises(ValueError, match="Invalid rating"):
            await feedback_service.submit_feedback(
                supabase=mock_supabase,
                user_id="user-123",
                organization_id="org-456",
                message_id="msg-789",
                conversation_id="conv-101",
                rating="neutral",  # Invalid
                query_text="What is AI?",
                answer_preview="AI...",
                sources_snapshot=[]
            )

    @pytest.mark.asyncio
    async def test_feedback_text_too_long_raises_error(self):
        """Should raise ValueError when feedback_text exceeds 100 chars."""
        mock_supabase = MagicMock()
        
        with pytest.raises(ValueError, match="exceeds 100 characters"):
            await feedback_service.submit_feedback(
                supabase=mock_supabase,
                user_id="user-123",
                organization_id="org-456",
                message_id="msg-789",
                conversation_id="conv-101",
                rating="positive",
                query_text="What is AI?",
                answer_preview="AI...",
                sources_snapshot=[],
                feedback_text="x" * 101  # Too long
            )

    @pytest.mark.asyncio
    async def test_answer_preview_truncated(self):
        """Should truncate answer_preview to 500 chars."""
        mock_supabase = MagicMock()
        
        # Mock checking for existing feedback (none found)
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = Mock(data=None)
        
        # Mock insert
        mock_supabase.table.return_value.insert.return_value.execute.return_value = Mock(
            data=[{"id": "fb-123", "created_at": "2024-01-01T00:00:00Z"}]
        )
        
        long_preview = "x" * 1000
        
        result = await feedback_service.submit_feedback(
            supabase=mock_supabase,
            user_id="user-123",
            organization_id="org-456",
            message_id="msg-789",
            conversation_id="conv-101",
            rating="positive",
            query_text="What is AI?",
            answer_preview=long_preview,
            sources_snapshot=[]
        )
        
        # Verify insert was called with truncated preview
        insert_call = mock_supabase.table.return_value.insert.call_args
        inserted_data = insert_call[0][0]
        assert len(inserted_data["answer_preview"]) == 500

    @pytest.mark.asyncio
    async def test_submit_feedback_db_error(self):
        """Should raise RuntimeError when database operation fails."""
        mock_supabase = MagicMock()
        
        # Mock checking for existing feedback (none found)
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = Mock(data=None)
        
        # Mock insert returning empty data
        mock_supabase.table.return_value.insert.return_value.execute.return_value = Mock(data=[])
        
        with pytest.raises(RuntimeError, match="Failed to save feedback"):
            await feedback_service.submit_feedback(
                supabase=mock_supabase,
                user_id="user-123",
                organization_id="org-456",
                message_id="msg-789",
                conversation_id="conv-101",
                rating="positive",
                query_text="Test",
                answer_preview="Test",
                sources_snapshot=[]
            )


class TestGetUserFeedbackForConversation:
    """Test retrieving user feedback for a conversation."""

    @pytest.mark.asyncio
    async def test_get_feedback_for_conversation(self):
        """Should return user's feedback for a conversation as dict."""
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = Mock(
            data=[
                {"message_id": "msg-1", "rating": "positive"},
                {"message_id": "msg-2", "rating": "negative"},
            ]
        )
        
        result = await feedback_service.get_user_feedback_for_conversation(
            supabase=mock_supabase,
            user_id="user-123",
            conversation_id="conv-101"
        )
        
        # Returns dict mapping message_id -> rating
        assert result["msg-1"] == "positive"
        assert result["msg-2"] == "negative"

    @pytest.mark.asyncio
    async def test_get_feedback_empty(self):
        """Should return empty dict when no feedback exists."""
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = Mock(data=[])
        
        result = await feedback_service.get_user_feedback_for_conversation(
            supabase=mock_supabase,
            user_id="user-123",
            conversation_id="conv-101"
        )
        
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_feedback_none_data(self):
        """Should handle None data gracefully."""
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = Mock(data=None)
        
        result = await feedback_service.get_user_feedback_for_conversation(
            supabase=mock_supabase,
            user_id="user-123",
            conversation_id="conv-101"
        )
        
        assert result == {}


class TestGetTeamFeedback:
    """Test team feedback listing."""

    @pytest.mark.asyncio
    async def test_get_team_feedback_basic(self):
        """Should list team feedback with pagination."""
        mock_supabase = MagicMock()
        mock_query = MagicMock()
        mock_supabase.table.return_value.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.range.return_value = mock_query
        mock_query.execute.return_value = Mock(
            data=[
                {
                    "id": "fb-1", "rating": "positive", "user_id": "u1", 
                    "organization_id": "org-1", "query_text": "What is AI?",
                    "answer_preview": "AI stands for...", "created_at": "2024-01-01",
                    "sources_snapshot": []
                },
            ],
            count=1
        )
        
        result = await feedback_service.get_team_feedback(
            supabase=mock_supabase,
            organization_id="org-456",
            limit=10,
            offset=0
        )
        
        assert "items" in result
        assert "total" in result
        assert "has_more" in result
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_get_team_feedback_with_rating_filter(self):
        """Should filter by rating."""
        mock_supabase = MagicMock()
        mock_query = MagicMock()
        mock_supabase.table.return_value.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.range.return_value = mock_query
        mock_query.execute.return_value = Mock(
            data=[{
                "id": "fb-1", "rating": "negative", "user_id": "u1",
                "query_text": "Test", "answer_preview": "Test", 
                "created_at": "2024-01-01", "sources_snapshot": []
            }],
            count=1
        )
        
        result = await feedback_service.get_team_feedback(
            supabase=mock_supabase,
            organization_id="org-456",
            rating="negative"
        )
        
        assert "items" in result

    @pytest.mark.asyncio
    async def test_get_team_feedback_with_date_range(self):
        """Should filter by date range."""
        mock_supabase = MagicMock()
        mock_query = MagicMock()
        mock_supabase.table.return_value.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.gte.return_value = mock_query
        mock_query.lte.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.range.return_value = mock_query
        mock_query.execute.return_value = Mock(data=[], count=0)
        
        result = await feedback_service.get_team_feedback(
            supabase=mock_supabase,
            organization_id="org-456",
            from_date="2024-01-01",
            to_date="2024-01-31"
        )
        
        # Verify date filters were applied
        mock_query.gte.assert_called_with("created_at", "2024-01-01")
        mock_query.lte.assert_called_with("created_at", "2024-01-31")

    @pytest.mark.asyncio
    async def test_get_team_feedback_limit_clamped(self):
        """Should clamp limit to 100."""
        mock_supabase = MagicMock()
        mock_query = MagicMock()
        mock_supabase.table.return_value.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.range.return_value = mock_query
        mock_query.execute.return_value = Mock(data=[], count=0)
        
        await feedback_service.get_team_feedback(
            supabase=mock_supabase,
            organization_id="org-456",
            limit=500  # Exceeds max
        )
        
        # Should clamp to 100
        mock_query.range.assert_called_with(0, 99)

    @pytest.mark.asyncio
    async def test_get_team_feedback_with_source_label(self):
        """Should filter by source label."""
        mock_supabase = MagicMock()
        mock_query = MagicMock()
        mock_supabase.table.return_value.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.contains.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.range.return_value = mock_query
        mock_query.execute.return_value = Mock(data=[], count=0)
        
        await feedback_service.get_team_feedback(
            supabase=mock_supabase,
            organization_id="org-456",
            source_label="knowledge-base"
        )
        
        # Verify source label filter was applied
        mock_query.contains.assert_called_with("sources_snapshot", [{"label": "knowledge-base"}])


class TestGetSourceMetrics:
    """Test source metrics retrieval from materialized view."""

    @pytest.mark.asyncio
    async def test_get_source_metrics(self):
        """Should return source metrics with positive/negative counts."""
        mock_supabase = MagicMock()
        mock_query = MagicMock()
        mock_supabase.table.return_value.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.gte.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = Mock(
            data=[
                {
                    "source_label": "doc1.pdf",
                    "source_type": "pdf",
                    "source_url": None,
                    "positive_count": 10,
                    "negative_count": 2,
                    "total_feedback": 12,
                    "negative_rate_pct": 16.67,
                    "last_feedback_at": "2024-01-15",
                },
            ],
            count=1
        )
        
        result = await feedback_service.get_source_metrics(
            supabase=mock_supabase,
            organization_id="org-456"
        )
        
        # Should have aggregated items
        assert "items" in result
        assert "total" in result
        assert len(result["items"]) == 1
        assert result["items"][0]["source_label"] == "doc1.pdf"


class TestGetPlatformFeedback:
    """Test platform-wide feedback (admin only)."""

    @pytest.mark.asyncio
    async def test_get_platform_feedback(self):
        """Should return platform-wide feedback."""
        mock_supabase = MagicMock()
        mock_query = MagicMock()
        mock_supabase.table.return_value.select.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.range.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.gte.return_value = mock_query
        mock_query.lte.return_value = mock_query
        mock_query.execute.return_value = Mock(
            data=[{
                "id": "fb-1", "organization_id": "org-1", "user_id": "u1",
                "rating": "positive", "query_text": "Test", "answer_preview": "Test",
                "created_at": "2024-01-01", "sources_snapshot": []
            }],
            count=1
        )
        
        # Mock the helper methods
        mock_supabase.auth.admin.get_user_by_id.return_value = Mock(
            user=Mock(email="test@example.com")
        )
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data={"name": "Test Org"}
        )
        
        result = await feedback_service.get_platform_feedback(
            supabase=mock_supabase,
            limit=10
        )
        
        assert "items" in result
        assert "total" in result


class TestRefreshMetrics:
    """Test metrics refresh functionality."""

    @pytest.mark.asyncio
    async def test_refresh_metrics(self):
        """Should trigger metrics refresh."""
        mock_supabase = MagicMock()
        mock_supabase.rpc.return_value.execute.return_value = Mock(data=None)
        
        # Should not raise
        await feedback_service.refresh_metrics(supabase=mock_supabase)
        
        mock_supabase.rpc.assert_called()


class TestFeedbackServiceSingleton:
    """Test service singleton instance."""

    def test_feedback_service_is_instance(self):
        """Should have a singleton instance available."""
        assert isinstance(feedback_service, FeedbackService)

    def test_multiple_imports_same_instance(self):
        """Should return same instance on multiple imports."""
        from services.feedback_service import feedback_service as fs2
        assert feedback_service is fs2
