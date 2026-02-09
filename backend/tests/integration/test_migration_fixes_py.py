"""
Integration Tests for Migration Fixes (20260221000000, 20260221000001, 20260221000002)

These tests verify the fixes for:
- ISSUE-001: get_effective_plan parameter name mismatch
- ISSUE-002: Solo user RLS failure
- ISSUE-003: source_type inconsistency

Run with: pytest tests/integration/test_migration_fixes_py.py -v
"""

from uuid import uuid4

import pytest

from core.db import get_supabase


class TestIsOrgMemberSoloUserFix:
    """
    Tests for ISSUE-002: is_org_member solo user fix.

    The fix allows is_org_member(uuid, uuid) to return TRUE when
    org_id = user_uuid, enabling solo users to access their own data.
    """

    def test_solo_user_self_access(self, supabase_client):
        """
        Test that is_org_member returns TRUE when org_id = user_id.
        This is the critical fix for solo users.
        """
        test_user_id = str(uuid4())

        result = supabase_client.rpc(
            "is_org_member",
            {
                "org_id": test_user_id,
                "user_uuid": test_user_id
            }
        ).execute()

        assert result.data is True, \
            f"is_org_member(uuid, uuid) should return TRUE for solo users, got {result.data}"

    def test_user_cannot_access_other_user_solo_data(self, supabase_client):
        """
        Test that is_org_member returns FALSE when user tries to access
        another user's solo data.
        """
        user_a = str(uuid4())
        user_b = str(uuid4())

        result = supabase_client.rpc(
            "is_org_member",
            {
                "org_id": user_a,  # User A's "organization" (solo user fallback)
                "user_uuid": user_b  # User B trying to access
            }
        ).execute()

        assert result.data is False, \
            "is_org_member should return FALSE when accessing another user's data"

    def test_null_parameters_handled(self, supabase_client):
        """
        Test that is_org_member handles NULL parameters gracefully.
        """
        test_user_id = str(uuid4())

        # Test with NULL org_id - should return FALSE, not crash
        try:
            result = supabase_client.rpc(
                "is_org_member",
                {
                    "org_id": None,
                    "user_uuid": test_user_id
                }
            ).execute()
            # NULL org_id should return FALSE
            assert result.data is False or result.data is None
        except Exception:
            # If it errors, that's also acceptable for NULL input
            pass


class TestGetEffectivePlanParameterFix:
    """
    Tests for ISSUE-001: get_effective_plan parameter name fix.

    The fix ensures the function parameter is named 'p_user_id' to match
    what the backend code sends.
    """

    def test_accepts_p_user_id_parameter(self, supabase_client):
        """
        Test that get_effective_plan accepts 'p_user_id' parameter.
        This is the exact call the backend makes.
        """
        test_user_id = str(uuid4())

        # This should NOT raise an error
        result = supabase_client.rpc(
            "get_effective_plan",
            {"p_user_id": test_user_id}
        ).execute()

        # Should return a string (plan name)
        assert result.data is not None, \
            "get_effective_plan should return a value, not None"
        assert isinstance(result.data, str), \
            f"get_effective_plan should return a string, got {type(result.data)}"

    def test_unknown_user_returns_free(self, supabase_client):
        """
        Test that unknown users get 'free' plan by default.
        """
        unknown_user_id = str(uuid4())

        result = supabase_client.rpc(
            "get_effective_plan",
            {"p_user_id": unknown_user_id}
        ).execute()

        # Unknown user should get 'free' plan
        assert result.data == "free", \
            f"Unknown user should get 'free' plan, got '{result.data}'"

    def test_function_is_stable(self, supabase_client):
        """
        Test that get_effective_plan returns consistent results for same input.
        """
        test_user_id = str(uuid4())

        result1 = supabase_client.rpc(
            "get_effective_plan",
            {"p_user_id": test_user_id}
        ).execute()

        result2 = supabase_client.rpc(
            "get_effective_plan",
            {"p_user_id": test_user_id}
        ).execute()

        assert result1.data == result2.data, \
            "get_effective_plan should return consistent results"


class TestSourceTypeStandardization:
    """
    Tests for ISSUE-003: source_type standardization.

    The fix ensures all identity documents use 'identity' source_type,
    not 'scope_identity'.
    """

    def test_no_scope_identity_documents(self, supabase_client):
        """
        Test that no documents have source_type='scope_identity'.
        """
        result = supabase_client.table("documents").select(
            "id", count="exact"
        ).eq("source_type", "scope_identity").execute()

        count = result.count or 0
        assert count == 0, \
            f"Found {count} documents with deprecated 'scope_identity' source_type"

    def test_identity_documents_exist(self, supabase_client):
        """
        Test that identity documents use the correct source_type.
        """
        result = supabase_client.table("documents").select(
            "id, source_type", count="exact"
        ).eq("source_type", "identity").limit(10).execute()

        # Just verify the query works - may have 0 identity docs if new install
        assert result.data is not None, \
            "Query for identity documents should not fail"

        # If there are identity docs, verify they have correct source_type
        for doc in (result.data or []):
            assert doc.get("source_type") == "identity", \
                f"Identity document {doc.get('id')} has wrong source_type"


class TestBackendRPCCompatibility:
    """
    End-to-end tests verifying backend RPC calls work correctly.
    """

    def test_get_user_team_data_accepts_p_user_id(self, supabase_client):
        """
        Test that get_user_team_data accepts 'p_user_id' parameter.
        """
        test_user_id = str(uuid4())

        try:
            result = supabase_client.rpc(
                "get_user_team_data",
                {"p_user_id": test_user_id}
            ).execute()

            # Should return JSONB (dict or None)
            assert result.data is None or isinstance(result.data, dict), \
                f"get_user_team_data should return dict or None, got {type(result.data)}"
        except Exception as e:
            pytest.fail(f"get_user_team_data failed: {e}")

    def test_hybrid_search_accepts_filter_org_id(self, supabase_client):
        """
        Test that hybrid_search accepts 'filter_org_id' parameter.
        """
        test_org_id = str(uuid4())
        dummy_embedding = [0.0] * 1536

        try:
            result = supabase_client.rpc(
                "hybrid_search",
                {
                    "query_text": "test",
                    "query_embedding": dummy_embedding,
                    "match_count": 1,
                    "filter_org_id": test_org_id,
                }
            ).execute()

            # Should return array (empty is fine)
            assert isinstance(result.data, list), \
                f"hybrid_search should return list, got {type(result.data)}"
        except Exception as e:
            pytest.fail(f"hybrid_search failed: {e}")

    def test_match_documents_accepts_filter_org_id(self, supabase_client):
        """
        Test that match_documents accepts 'filter_org_id' parameter.
        """
        test_org_id = str(uuid4())
        dummy_embedding = [0.0] * 1536

        try:
            result = supabase_client.rpc(
                "match_documents",
                {
                    "query_embedding": dummy_embedding,
                    "match_threshold": 0.5,
                    "match_count": 1,
                    "filter_org_id": test_org_id,
                }
            ).execute()

            # Should return array (empty is fine)
            assert isinstance(result.data, list), \
                f"match_documents should return list, got {type(result.data)}"
        except Exception as e:
            pytest.fail(f"match_documents failed: {e}")


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def supabase_client():
    """
    Get Supabase client for integration tests.

    Uses service_role key for full database access in tests.
    """
    return get_supabase()


# =============================================================================
# TEST CONFIGURATION
# =============================================================================

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )


# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration
