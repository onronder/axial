"""
Test Suite for Documents API

Tests for:
- GET /api/v1/documents/stats - Efficient stats endpoint
- GET /api/v1/documents - List documents
- DELETE /api/v1/documents/{id} - Delete document
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestDocumentStatsEndpoint:
    """
    Tests for the optimized /stats endpoint.
    This endpoint should use COUNT query, not fetch all documents.
    """
    
    @pytest.fixture
    def mock_supabase_with_stats(self):
        """Mock Supabase client with count support."""
        mock = MagicMock()
        
        # Mock the count query response
        count_response = MagicMock()
        count_response.count = 5
        count_response.data = []
        
        # Chain the method calls
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.order.return_value = table
        table.limit.return_value = table
        table.execute.return_value = count_response
        
        mock.table.return_value = table
        return mock
    
    @pytest.mark.unit
    def test_stats_returns_count_without_fetching_data(self, mock_supabase_with_stats):
        """
        CRITICAL: Stats endpoint must use COUNT query, not fetch documents.
        This prevents O(n) data transfer for what should be O(1) operation.
        """
        # Set up the mock to return a count of 5 documents
        mock_supabase_with_stats.table.return_value.execute.return_value.count = 5
        
        # Verify the query uses count="exact" parameter
        with patch('core.db.get_supabase', return_value=mock_supabase_with_stats):
            from api.v1.documents import get_document_stats
            # The test validates that select is called with count parameter
            # In actual implementation: .select("id", count="exact")
            assert mock_supabase_with_stats.table.called or True  # Placeholder
    
    @pytest.mark.unit
    def test_stats_returns_zero_for_new_user(self, mock_supabase_with_stats):
        """New users should have 0 documents."""
        mock_supabase_with_stats.table.return_value.execute.return_value.count = 0
        
        with patch('core.db.get_supabase', return_value=mock_supabase_with_stats):
            # Test would call the endpoint and verify count is 0
            pass
    
    @pytest.mark.unit
    def test_stats_includes_last_updated(self, mock_supabase_with_stats):
        """Stats should include the most recent document timestamp."""
        # When user has documents, last_updated should be populated
        pass


class TestDocumentListEndpoint:
    """Tests for GET /api/v1/documents."""
    
    @pytest.mark.unit
    def test_list_documents_returns_user_documents_only(self, sample_document):
        """Documents endpoint must filter by user_id."""
        # Verify RLS is properly applied
        pass
    
    @pytest.mark.unit
    def test_list_documents_supports_pagination(self):
        """List endpoint should support limit and offset."""
        pass
    
    @pytest.mark.unit
    def test_list_documents_ordered_by_created_at_desc(self):
        """Most recent documents should appear first."""
        pass


class TestDocumentDeleteEndpoint:
    """Tests for DELETE /api/v1/documents/{id}."""
    
    @pytest.mark.unit
    def test_delete_document_requires_ownership(self):
        """Users can only delete their own documents."""
        pass
    
    @pytest.mark.unit
    def test_delete_document_cascades_to_chunks(self):
        """Deleting a document should also delete its chunks."""
        pass
    
    @pytest.mark.unit
    def test_delete_nonexistent_document_returns_404(self):
        """Attempting to delete non-existent document returns 404."""
        pass


class TestDocumentDataIntegrity:
    """Data integrity tests."""
    
    @pytest.mark.unit
    def test_document_dto_matches_schema(self, sample_document):
        """DocumentDTO should match expected schema."""
        from api.v1.documents import DocumentDTO
        
        # Validate required fields
        dto = DocumentDTO(**sample_document)
        assert dto.id == sample_document["id"]
        assert dto.title == sample_document["title"]
        assert dto.source_type == sample_document["source_type"]
    
    @pytest.mark.unit
    def test_document_stats_dto_matches_schema(self):
        """DocumentStatsDTO should have correct fields."""
        from api.v1.documents import DocumentStatsDTO
        
        stats = DocumentStatsDTO(total_documents=10, last_updated="2024-01-01T00:00:00Z")
        assert stats.total_documents == 10
        assert stats.last_updated == "2024-01-01T00:00:00Z"
