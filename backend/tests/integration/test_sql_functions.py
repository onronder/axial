"""
Integration Tests for SQL Functions

These tests verify that SQL functions in the database:
1. Execute without errors (no missing columns, syntax errors)
2. Return expected data types
3. Handle edge cases correctly

IMPORTANT: These tests require a real database connection.
Set the following environment variables:
- SUPABASE_URL
- SUPABASE_SERVICE_ROLE_KEY

Run with: pytest backend/tests/integration/test_sql_functions.py -v --tb=short

To skip in CI when no database is available, these tests are marked with:
    @pytest.mark.integration
    @pytest.mark.requires_db
"""

import os
import pytest
from uuid import uuid4
from typing import Optional

# Check if database is available
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
HAS_DATABASE = bool(SUPABASE_URL and SUPABASE_KEY)

# Skip all tests in this module if no database connection
pytestmark = [
    pytest.mark.integration,
    pytest.mark.requires_db,
    pytest.mark.skipif(not HAS_DATABASE, reason="Database connection required"),
]


@pytest.fixture(scope="module")
def supabase_client():
    """Create a Supabase client for integration tests."""
    if not HAS_DATABASE:
        pytest.skip("Database connection required")
    
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_KEY)


class TestGetEffectivePlan:
    """
    Tests for the get_effective_plan() SQL function.
    
    This function was broken by migration 20260216160000 which referenced
    the removed 'subscription_status' column from user_profiles.
    Fixed in migration 20260117140000_fix_get_effective_plan_v2.sql.
    """
    
    def test_function_executes_without_error(self, supabase_client):
        """
        Verify get_effective_plan() executes without SQL errors.
        
        This catches schema mismatches like missing columns.
        """
        # Use a random UUID - function should handle non-existent users gracefully
        test_user_id = str(uuid4())
        
        try:
            result = supabase_client.rpc(
                "get_effective_plan",
                {"target_user_id": test_user_id}
            ).execute()
            
            # Function should return a string (plan name)
            assert result.data is not None or result.data == "free"
            
        except Exception as e:
            # If we get a SQL error, the function is broken
            pytest.fail(f"get_effective_plan() SQL error: {e}")
    
    def test_returns_valid_plan_type(self, supabase_client):
        """Verify function returns a valid plan type."""
        test_user_id = str(uuid4())
        
        result = supabase_client.rpc(
            "get_effective_plan",
            {"target_user_id": test_user_id}
        ).execute()
        
        valid_plans = {"free", "starter", "pro", "enterprise", None}
        assert result.data in valid_plans or result.data is None, \
            f"Unexpected plan type: {result.data}"
    
    def test_nonexistent_user_returns_free(self, supabase_client):
        """Non-existent user should default to 'free' plan."""
        fake_user_id = str(uuid4())
        
        result = supabase_client.rpc(
            "get_effective_plan",
            {"target_user_id": fake_user_id}
        ).execute()
        
        # Non-existent users should get 'free' as default
        assert result.data == "free", \
            f"Expected 'free' for non-existent user, got: {result.data}"


class TestHybridSearch:
    """
    Tests for the hybrid_search() SQL function.
    
    This function combines vector and keyword search for RAG retrieval.
    """
    
    def test_function_executes_without_error(self, supabase_client):
        """Verify hybrid_search() executes without SQL errors."""
        # Create a dummy embedding (1536 dimensions for text-embedding-3-small)
        dummy_embedding = [0.0] * 1536
        
        try:
            result = supabase_client.rpc(
                "hybrid_search",
                {
                    "query_text": "test query",
                    "query_embedding": dummy_embedding,
                    "match_count": 5,
                    "filter_org_id": str(uuid4()),
                    "vector_weight": 0.7,
                    "keyword_weight": 0.3,
                    "similarity_threshold": 0.25
                }
            ).execute()
            
            # Should return an array (possibly empty)
            assert isinstance(result.data, list), \
                f"Expected list, got: {type(result.data)}"
                
        except Exception as e:
            pytest.fail(f"hybrid_search() SQL error: {e}")
    
    def test_returns_expected_columns(self, supabase_client):
        """Verify hybrid_search returns expected columns."""
        dummy_embedding = [0.0] * 1536
        
        result = supabase_client.rpc(
            "hybrid_search",
            {
                "query_text": "test",
                "query_embedding": dummy_embedding,
                "match_count": 1,
                "filter_org_id": None,
            }
        ).execute()
        
        # If there are results, check column structure
        if result.data and len(result.data) > 0:
            row = result.data[0]
            expected_columns = {
                "id", "content", "document_id", "chunk_index",
                "source_type", "scope_id", "title", "metadata",
                "vector_score", "keyword_score", "combined_score"
            }
            actual_columns = set(row.keys())
            missing = expected_columns - actual_columns
            assert not missing, f"Missing columns in hybrid_search result: {missing}"


class TestHybridSearchScoped:
    """Tests for the hybrid_search_scoped() SQL function."""
    
    def test_function_executes_without_error(self, supabase_client):
        """Verify hybrid_search_scoped() executes without SQL errors."""
        dummy_embedding = [0.0] * 1536
        
        try:
            result = supabase_client.rpc(
                "hybrid_search_scoped",
                {
                    "query_text": "test query",
                    "query_embedding": dummy_embedding,
                    "match_count": 5,
                    "filter_org_id": str(uuid4()),
                    "filter_scope_ids": None,  # No scope filter
                    "vector_weight": 0.7,
                    "keyword_weight": 0.3,
                    "similarity_threshold": 0.25
                }
            ).execute()
            
            assert isinstance(result.data, list)
            
        except Exception as e:
            pytest.fail(f"hybrid_search_scoped() SQL error: {e}")


class TestMatchDocuments:
    """Tests for the match_documents() SQL function."""
    
    def test_function_executes_without_error(self, supabase_client):
        """Verify match_documents() executes without SQL errors."""
        dummy_embedding = [0.0] * 1536
        
        try:
            result = supabase_client.rpc(
                "match_documents",
                {
                    "query_embedding": dummy_embedding,
                    "match_threshold": 0.5,
                    "match_count": 5,
                    "filter_org_id": str(uuid4())
                }
            ).execute()
            
            assert isinstance(result.data, list)
            
        except Exception as e:
            pytest.fail(f"match_documents() SQL error: {e}")


class TestGetUserTeamData:
    """Tests for the get_user_team_data() SQL function."""
    
    def test_function_executes_without_error(self, supabase_client):
        """Verify get_user_team_data() executes without SQL errors."""
        try:
            result = supabase_client.rpc(
                "get_user_team_data",
                {"p_user_id": str(uuid4())}
            ).execute()
            
            # Should return JSONB (dict or None)
            assert result.data is None or isinstance(result.data, dict)
            
        except Exception as e:
            pytest.fail(f"get_user_team_data() SQL error: {e}")


class TestRecalculateUserUsage:
    """Tests for the recalculate_user_usage() SQL function."""
    
    def test_function_executes_without_error(self, supabase_client):
        """Verify recalculate_user_usage() executes without SQL errors."""
        try:
            # This function modifies data, so use a fake user ID
            # It should handle non-existent users gracefully
            result = supabase_client.rpc(
                "recalculate_user_usage",
                {"target_user_id": str(uuid4())}
            ).execute()
            
            # Function returns VOID, so data should be None or empty
            # No exception means success
            
        except Exception as e:
            pytest.fail(f"recalculate_user_usage() SQL error: {e}")


class TestIsOrgMember:
    """Tests for the is_org_member() SQL function."""
    
    def test_function_executes_without_error(self, supabase_client):
        """Verify is_org_member() executes without SQL errors."""
        try:
            result = supabase_client.rpc(
                "is_org_member",
                {
                    "p_org_id": str(uuid4()),
                    "p_user_id": str(uuid4())
                }
            ).execute()
            
            # Should return boolean
            assert isinstance(result.data, bool)
            
        except Exception as e:
            pytest.fail(f"is_org_member() SQL error: {e}")


# =============================================================================
# Schema Validation Tests
# =============================================================================

class TestSchemaConsistency:
    """
    Tests to verify database schema matches expected structure.
    
    These catch issues where migrations modify tables but functions
    still reference old column names.
    """
    
    def test_user_profiles_has_expected_columns(self, supabase_client):
        """Verify user_profiles table has expected columns."""
        # Query one row to get column names
        result = supabase_client.table("user_profiles").select("*").limit(1).execute()
        
        if result.data and len(result.data) > 0:
            columns = set(result.data[0].keys())
            
            # subscription_status was REMOVED in migration 20251231130000
            assert "subscription_status" not in columns, \
                "subscription_status column should be REMOVED from user_profiles"
            
            # These columns should exist
            expected_columns = {"user_id", "plan"}
            missing = expected_columns - columns
            assert not missing, f"Missing expected columns in user_profiles: {missing}"
    
    def test_subscriptions_has_expected_columns(self, supabase_client):
        """Verify subscriptions table has expected columns."""
        result = supabase_client.table("subscriptions").select("*").limit(1).execute()
        
        if result.data and len(result.data) > 0:
            columns = set(result.data[0].keys())
            
            # These columns should exist in subscriptions table
            expected_columns = {"team_id", "status", "plan_type"}
            missing = expected_columns - columns
            assert not missing, f"Missing expected columns in subscriptions: {missing}"
    
    def test_documents_has_expected_columns(self, supabase_client):
        """Verify documents table has expected columns."""
        result = supabase_client.table("documents").select("*").limit(1).execute()
        
        if result.data and len(result.data) > 0:
            columns = set(result.data[0].keys())
            
            expected_columns = {
                "id", "user_id", "organization_id", "title",
                "source_type", "source_id", "scope_id", "metadata"
            }
            missing = expected_columns - columns
            assert not missing, f"Missing expected columns in documents: {missing}"
    
    def test_document_chunks_has_expected_columns(self, supabase_client):
        """Verify document_chunks table has expected columns."""
        result = supabase_client.table("document_chunks").select("*").limit(1).execute()
        
        if result.data and len(result.data) > 0:
            columns = set(result.data[0].keys())
            
            expected_columns = {
                "id", "document_id", "chunk_index", "content", "embedding"
            }
            missing = expected_columns - columns
            assert not missing, f"Missing expected columns in document_chunks: {missing}"
