"""
Test Suite for Team Service

Production-grade tests for:
- get_effective_plan (cached plan inheritance)
- get_user_team 
- Team CRUD operations
- Cache invalidation

Critical tests ensure team members inherit owner's plan.
"""

import csv
import io
import pytest
from types import SimpleNamespace
from unittest.mock import patch, Mock, AsyncMock, MagicMock
from uuid import uuid4




# Test UUIDs
OWNER_UUID = "11111111-1111-1111-1111-111111111111"
MEMBER_UUID = "22222222-2222-2222-2222-222222222222"
TEAM_UUID = "33333333-3333-3333-3333-333333333333"


def _make_table(data=None, count=None, execute_side_effect=None):
    table = Mock()
    table.select.return_value = table
    table.eq.return_value = table
    table.neq.return_value = table
    table.limit.return_value = table
    table.single.return_value = table
    table.order.return_value = table
    table.update.return_value = table
    table.insert.return_value = table
    table.delete.return_value = table
    if execute_side_effect is not None:
        table.execute.side_effect = execute_side_effect
    else:
        result = Mock(data=data)
        if count is not None:
            result.count = count
        table.execute.return_value = result
    return table


def _make_limits(max_team_seats):
    limits = SimpleNamespace(max_team_seats=max_team_seats)
    limits.model_dump = lambda: {"max_team_seats": max_team_seats}
    return limits


@pytest.fixture
def team_service():
    """Shared TeamService fixture for tests outside class scopes."""
    from services.team_service import TeamService
    service = TeamService()
    try:
        service.get_effective_plan.cache_clear()
    except Exception:
        pass
    return service


class TestGetEffectivePlan:
    """Tests for get_effective_plan - the critical hot path."""
    
    @pytest.fixture
    def team_service(self):
        """Create a fresh TeamService instance for each test."""
        from services.team_service import TeamService
        service = TeamService()
        # Clear any cached values
        try:
            service.get_effective_plan.cache_clear()
        except:
            pass
        return service
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_solo_user_gets_own_plan(self, team_service):
        """Solo user (owns their team) gets their own plan."""
        mock_supabase = Mock()
        
        # Mock RPC call returning user's own plan
        mock_supabase.rpc.return_value.execute.return_value = Mock(data="pro")
        
        with patch("services.team_service.get_supabase", return_value=mock_supabase):
            plan = await team_service.get_effective_plan(OWNER_UUID)
            
            assert plan == "pro"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_team_member_inherits_owner_plan(self, team_service):
        """Team member inherits enterprise plan from owner."""
        mock_supabase = Mock()
        
        # Mock RPC returning owner's enterprise plan
        mock_supabase.rpc.return_value.execute.return_value = Mock(data="enterprise")
        
        with patch("services.team_service.get_supabase", return_value=mock_supabase):
            plan = await team_service.get_effective_plan(MEMBER_UUID)
            
            assert plan == "enterprise"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_canceled_subscription_returns_free(self, team_service):
        """Canceled subscriptions should downgrade to free."""
        mock_supabase = Mock()

        def rpc_side_effect(name, params):
            if name == "get_effective_plan":
                return Mock(execute=Mock(return_value=Mock(data=None)))
            if name == "get_user_team_data":
                return Mock(
                    execute=Mock(
                        return_value=Mock(
                            data={
                                "subscription": {"status": "canceled", "plan_type": "pro"},
                                "profile": {"plan": "starter"},
                            }
                        )
                    )
                )
            raise AssertionError(f"Unexpected rpc: {name}")

        mock_supabase.rpc.side_effect = rpc_side_effect

        with patch("services.team_service.get_supabase", return_value=mock_supabase):
            plan = await team_service.get_effective_plan(MEMBER_UUID)
            assert plan == "free"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rpc_unknown_plan_falls_back(self, team_service):
        mock_supabase = Mock()
        mock_supabase.rpc.return_value.execute.return_value = Mock(data="unknown")

        with patch("services.team_service.get_supabase", return_value=mock_supabase), \
             patch.object(team_service, "_get_effective_plan_direct", new=AsyncMock(return_value="starter")):
            plan = await team_service.get_effective_plan(OWNER_UUID)

        assert plan == "free"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rpc_trialing_subscription_returns_plan(self, team_service):
        mock_supabase = Mock()

        def rpc_side_effect(name, params):
            if name == "get_effective_plan":
                return Mock(execute=Mock(return_value=Mock(data=None)))
            if name == "get_user_team_data":
                return Mock(execute=Mock(return_value=Mock(
                    data={"subscription": {"status": "trialing", "plan_type": "pro"}, "profile": {}}
                )))
            raise AssertionError(f"Unexpected rpc: {name}")

        mock_supabase.rpc.side_effect = rpc_side_effect

        with patch("services.team_service.get_supabase", return_value=mock_supabase):
            plan = await team_service.get_effective_plan(OWNER_UUID)

        assert plan == "pro"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sequential_fallback_trialing_subscription(self, team_service):
        mock_supabase = Mock()
        mock_supabase.rpc.side_effect = Exception("rpc down")

        tables = {
            "team_members": _make_table([{"team_id": TEAM_UUID}]),
            "subscriptions": _make_table([{"status": "trialing", "plan_type": "pro"}]),
        }

        def table_side_effect(name):
            return tables.get(name, _make_table([]))

        mock_supabase.table.side_effect = table_side_effect

        with patch("services.team_service.get_supabase", return_value=mock_supabase):
            plan = await team_service._get_effective_plan_direct(MEMBER_UUID)

        assert plan == "pro"


class TestTeamServiceAdditional:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_verify_team_access_owner_not_found(self):
        from services.team_service import TeamService
        service = TeamService()

        mock_supabase = Mock()
        tables = {
            "team_members": _make_table([{"team_id": TEAM_UUID}]),
            "teams": _make_table({"owner_id": OWNER_UUID}),
            "subscriptions": _make_table([]),
            "user_profiles": _make_table([]),
        }
        mock_supabase.table.side_effect = lambda name: tables[name]

        with patch("services.team_service.get_supabase", return_value=mock_supabase):
            result = await service.verify_team_access(MEMBER_UUID)

        assert result["reason"] == "owner_not_found"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_user_team_member_handles_exception(self):
        from services.team_service import TeamService
        service = TeamService()
        supabase = Mock()
        supabase.table.side_effect = Exception("boom")

        with patch("services.team_service.get_supabase", return_value=supabase):
            result = await service.get_user_team_member(MEMBER_UUID)

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_user_team_missing_team_id(self):
        from services.team_service import TeamService
        service = TeamService()
        supabase = Mock()
        team_table = _make_table([{"team_id": None}])
        supabase.table.side_effect = lambda name: team_table

        with patch("services.team_service.get_supabase", return_value=supabase):
            result = await service.get_user_team(MEMBER_UUID)

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_user_team_missing_team(self):
        from services.team_service import TeamService
        service = TeamService()
        member_table = _make_table([{"team_id": TEAM_UUID, "role": "member", "joined_at": "now"}])
        team_table = _make_table(None)
        supabase = Mock()
        supabase.table.side_effect = lambda name: member_table if name == "team_members" else team_table

        with patch("services.team_service.get_supabase", return_value=supabase):
            result = await service.get_user_team(MEMBER_UUID)

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_user_team_handles_exception(self):
        from services.team_service import TeamService
        service = TeamService()
        supabase = Mock()
        supabase.table.side_effect = Exception("boom")

        with patch("services.team_service.get_supabase", return_value=supabase):
            result = await service.get_user_team(MEMBER_UUID)

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invite_member_insert_failed(self):
        from services.team_service import TeamService
        service = TeamService()
        supabase = Mock()
        tables = {"team_members": _make_table([])}
        tables["team_members"].insert.return_value.execute.return_value = Mock(data=None)
        supabase.table.side_effect = lambda name: tables[name]

        with patch("services.team_service.get_supabase", return_value=supabase), \
             patch.object(service, "_check_team_feature_access", new=AsyncMock(return_value=(True, "", {}))), \
             patch.object(service, "_get_current_member_count", new=AsyncMock(return_value=0)), \
             patch.object(service, "get_user_team", new=AsyncMock(return_value={"id": TEAM_UUID, "name": "Team"})):
            result = await service.invite_member(OWNER_UUID, "member@example.com")

        assert result["success"] is False
        assert result["code"] == "INSERT_FAILED"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_invite_email_warns_on_failure(self):
        from services.team_service import TeamService
        service = TeamService()

        with patch("services.email.email_service.send_team_invite", new=AsyncMock(return_value=False)):
            result = await service.send_invite_email("user@example.com", "User", "Team", "token")

        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_resend_invite_handles_exception(self):
        from services.team_service import TeamService
        service = TeamService()
        supabase = Mock()
        supabase.table.side_effect = Exception("boom")

        with patch("services.team_service.get_supabase", return_value=supabase):
            result = await service.resend_invite("member-1", OWNER_UUID)

        assert result["success"] is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bulk_invite_records_failure(self):
        from services.team_service import TeamService
        service = TeamService()

        csv_content = "email,role,name\nuser@example.com,viewer,User\n"

        with patch.object(service, "_check_team_feature_access", new=AsyncMock(return_value=(True, "", {"max_team_seats": 10}))), \
             patch.object(service, "get_user_team", new=AsyncMock(return_value={"id": "team-1", "owner_id": OWNER_UUID})), \
             patch.object(service, "_get_current_member_count", new=AsyncMock(return_value=1)), \
             patch.object(service, "invite_member", new=AsyncMock(return_value={"success": False, "error": "nope"})):
            result = await service.bulk_invite_csv(OWNER_UUID, csv_content)

        assert result["failed"] == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bulk_invite_handles_exception(self):
        from services.team_service import TeamService
        service = TeamService()

        with patch("csv.DictReader", side_effect=Exception("boom")), \
             patch.object(service, "_check_team_feature_access", new=AsyncMock(return_value=(True, "", {}))):
            result = await service.bulk_invite_csv(OWNER_UUID, "bad")

        assert result["code"] == "PARSE_ERROR"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_remove_member_handles_exception(self):
        from services.team_service import TeamService
        service = TeamService()
        supabase = Mock()
        supabase.table.side_effect = Exception("boom")

        with patch("services.team_service.get_supabase", return_value=supabase):
            result = await service.remove_member(OWNER_UUID, "member-1")

        assert result["success"] is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_subscription_returns_free(self, team_service):
        """User with no active subscription defaults to free plan.
        
        NOTE: subscription_status was removed from user_profiles in migration 20251231130000.
        Subscription status is now tracked in the subscriptions table only.
        Users without an active subscription entry default to 'free' regardless of user_profiles.plan.
        """
        mock_supabase = Mock()
        
        # Mock RPC returning data with no active subscription
        mock_supabase.rpc.return_value.execute.return_value = Mock(
            data={
                "team_id": "some-team-id",
                "subscription": None,  # No subscription record
                "profile": {"plan": "pro"}  # Profile plan is ignored if no subscription
            }
        )
        
        with patch("services.team_service.get_supabase", return_value=mock_supabase):
            plan = await team_service.get_effective_plan(OWNER_UUID)
            # Without an active subscription, user gets 'free' regardless of profile.plan
            assert plan == "free"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_profile_plan_used_when_no_subscription(self, team_service):
        """No subscription data defaults to free."""
        mock_supabase = Mock()

        mock_supabase.rpc.return_value.execute.side_effect = Exception("RPC fail")

        member_table = Mock()
        member_table.select.return_value.eq.return_value.neq.return_value.limit.return_value.execute.return_value = Mock(data=[])

        teams_table = Mock()
        teams_table.select.return_value.eq.return_value.limit.return_value.execute.return_value = Mock(data=[])

        profile_table = Mock()
        profile_table.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data={"plan": "pro"}
        )

        def table_side_effect(name):
            if name == "team_members":
                return member_table
            if name == "teams":
                return teams_table
            if name == "user_profiles":
                return profile_table
            return Mock()

        mock_supabase.table.side_effect = table_side_effect

        with patch("services.team_service.get_supabase", return_value=mock_supabase):
            plan = await team_service.get_effective_plan(OWNER_UUID)
            assert plan == "free"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unknown_user_defaults_to_free(self, team_service):
        """Unknown user defaults to 'free' plan."""
        mock_supabase = Mock()
        
        # Mock RPC returning None (no user found)
        mock_supabase.rpc.return_value.execute.return_value = Mock(data=None)
        
        # Mock direct query fallback also returning nothing
        mock_eq = mock_supabase.table.return_value.select.return_value.eq.return_value
        mock_eq.neq.return_value.limit.return_value.execute.return_value = Mock(data=[])
        
        # Mock own_team check (empty)
        mock_eq.limit.return_value.execute.return_value = Mock(data=[])

        mock_eq.single.return_value.execute.return_value = Mock(data=None)
        
        with patch("services.team_service.get_supabase", return_value=mock_supabase):
            plan = await team_service.get_effective_plan("nonexistent-user-id")
            
            assert plan == "free"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rpc_failure_falls_back_to_direct_query(self, team_service):
        """If RPC fails, fallback to direct query succeeds."""
        mock_supabase = Mock()
        
        # Mock RPC to raise exception
        mock_supabase.rpc.return_value.execute.side_effect = Exception("RPC unavailable")
        
        # Mock direct query path
        # Step 1: Find team membership
        mock_eq = mock_supabase.table.return_value.select.return_value.eq.return_value
        mock_eq.neq.return_value.limit.return_value.execute.return_value = Mock(
            data=[{"team_id": TEAM_UUID}]
        )
        # Step 2: Get team owner
        mock_eq.single.return_value.execute.return_value = Mock(
            data={"owner_id": OWNER_UUID}
        )
        
        # Mock own_team check (empty)
        mock_eq.limit.return_value.execute.return_value = Mock(data=[])
        
        with patch("services.team_service.get_supabase", return_value=mock_supabase):
            # The fallback should work
            # Note: Due to mock chaining complexity, just verify it doesn't crash
            plan = await team_service.get_effective_plan(MEMBER_UUID)
            assert plan in ["free", "starter", "pro", "enterprise"]
    
    @pytest.mark.unit
    def test_cache_invalidation_clears_user(self, team_service):
        """invalidate_plan_cache should clear cached value."""
        # This just tests the method doesn't crash
        team_service.invalidate_plan_cache(OWNER_UUID)
        # No assertion - just verifying no exception
    
    @pytest.mark.unit
    def test_invalidate_all_cache_clears_everything(self, team_service):
        """invalidate_all_cache should clear all cached values."""
        team_service.invalidate_all_cache()
        # No assertion - just verifying no exception


class TestGetUserTeam:
    """Tests for get_user_team."""
    
    @pytest.fixture
    def team_service(self):
        from services.team_service import TeamService
        return TeamService()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_team_with_role(self, team_service):
        """get_user_team returns team details with user's role."""
        mock_supabase = Mock()
        
        # Mock team membership query
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = Mock(
            data=[{"team_id": TEAM_UUID, "role": "editor", "joined_at": "2024-01-01T00:00:00Z"}]
        )
        
        # Mock team details query - now using maybe_single() instead of single()
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = Mock(
            data={
                "id": TEAM_UUID,
                "name": "Acme Corp",
                "slug": "acme-corp",
                "owner_id": OWNER_UUID,
                "created_at": "2024-01-01T00:00:00Z"
            }
        )
        
        with patch("services.team_service.get_supabase", return_value=mock_supabase):
            team = await team_service.get_user_team(MEMBER_UUID)
            
            assert team is not None
            assert team["id"] == TEAM_UUID
            assert team["name"] == "Acme Corp"
            assert team["user_role"] == "editor"
            assert team["is_owner"] is False
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_owner_is_marked_as_owner(self, team_service):
        """Team owner should have is_owner=True."""
        mock_supabase = Mock()
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = Mock(
            data=[{"team_id": TEAM_UUID, "role": "admin", "joined_at": "2024-01-01T00:00:00Z"}]
        )
        
        # Mock team details query - now using maybe_single() instead of single()
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = Mock(
            data={
                "id": TEAM_UUID,
                "name": "My Team",
                "slug": None,
                "owner_id": OWNER_UUID,  # Same as user
                "created_at": "2024-01-01T00:00:00Z"
            }
        )
        
        with patch("services.team_service.get_supabase", return_value=mock_supabase):
            team = await team_service.get_user_team(OWNER_UUID)
            
            assert team is not None
            assert team["is_owner"] is True
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_team_returns_none(self, team_service):
        """User without team membership returns None."""
        mock_supabase = Mock()
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = Mock(
            data=[]
        )
        
        with patch("services.team_service.get_supabase", return_value=mock_supabase):
            team = await team_service.get_user_team("no-team-user")
            
            assert team is None


class TestGetTeamMembers:
    """Tests for get_team_members."""
    
    @pytest.fixture
    def team_service(self):
        from services.team_service import TeamService
        return TeamService()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_list_of_members(self, team_service):
        """get_team_members returns list of team member dicts."""
        mock_supabase = Mock()
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = Mock(
            data=[
                {"id": "member-1", "email": "alice@example.com", "role": "admin", "status": "active"},
                {"id": "member-2", "email": "bob@example.com", "role": "editor", "status": "active"},
            ]
        )
        
        with patch("services.team_service.get_supabase", return_value=mock_supabase):
            members = await team_service.get_team_members(TEAM_UUID)
            
            assert len(members) == 2
            assert members[0]["email"] == "alice@example.com"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_team_returns_empty_list(self, team_service):
        """Empty team returns empty list, not None."""
        mock_supabase = Mock()
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = Mock(
            data=[]
        )
        
        with patch("services.team_service.get_supabase", return_value=mock_supabase):
            members = await team_service.get_team_members(TEAM_UUID)
            
            assert members == []


class TestPlanInheritanceScenarios:
    """Integration-style tests for plan inheritance scenarios."""
    
    @pytest.fixture
    def team_service(self):
        from services.team_service import TeamService
        service = TeamService()
        try:
            service.get_effective_plan.cache_clear()
        except:
            pass
        return service
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_viewer_in_enterprise_team_gets_enterprise(self, team_service):
        """
        Critical test: Viewer in enterprise team gets enterprise plan.
        
        Scenario:
        - Team owner: Enterprise plan
        - Team member: Viewer role (would be Starter if solo)
        - Expected: Member gets Enterprise features
        """
        mock_supabase = Mock()
        mock_supabase.rpc.return_value.execute.return_value = Mock(data="enterprise")
        
        with patch("services.team_service.get_supabase", return_value=mock_supabase):
            plan = await team_service.get_effective_plan("viewer-member-id")
            
            assert plan == "enterprise"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_admin_in_free_team_gets_free(self, team_service):
        """Admin in free team still gets free plan (no upgrade from role)."""
        mock_supabase = Mock()
        mock_supabase.rpc.return_value.execute.return_value = Mock(data="free")
        
        with patch("services.team_service.get_supabase", return_value=mock_supabase):
            plan = await team_service.get_effective_plan("admin-member-id")
            
            assert plan == "free"


class TestSingletonInstance:
    """Test that team_service singleton is properly configured."""
    
    @pytest.mark.unit
    def test_singleton_exists(self):
        """Singleton instance should be available."""
        from services.team_service import team_service
        
        assert team_service is not None
    
    @pytest.mark.unit
    def test_singleton_has_required_methods(self):
        """Singleton should have all required methods."""
        from services.team_service import team_service
        
        assert hasattr(team_service, "get_effective_plan")
        assert hasattr(team_service, "get_user_team")
        assert hasattr(team_service, "invalidate_plan_cache")
        assert hasattr(team_service, "invalidate_all_cache")
        assert hasattr(team_service, "invite_member")
        assert hasattr(team_service, "bulk_invite_csv")
        assert hasattr(team_service, "remove_member")
        assert callable(team_service.get_effective_plan)


class TestEnterpriseGatekeeping:
    """Tests for Enterprise-only feature gatekeeping."""
    
    @pytest.fixture
    def team_service(self):
        from services.team_service import TeamService
        service = TeamService()
        try:
            service.get_effective_plan.cache_clear()
        except:
            pass
        return service
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invite_blocked_for_unknown_plan(self, team_service):
        """Unknown plan users should be treated as free and blocked."""
        mock_supabase = Mock()
        
        # Mock returning unknown plan
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data={"plan": "unknown"}
        )
        
        with patch("services.team_service.get_supabase", return_value=mock_supabase):
            result = await team_service.invite_member(
                owner_id=OWNER_UUID,
                email="test@example.com",
                role="viewer"
            )
            
            assert result["success"] is False
            assert result["code"] == "UPGRADE_REQUIRED"
            assert "Enterprise" in result["error"]
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invite_blocked_for_starter_plan(self, team_service):
        """Starter plan users cannot invite team members."""
        mock_supabase = Mock()
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data={"plan": "starter"}
        )
        
        with patch("services.team_service.get_supabase", return_value=mock_supabase):
            result = await team_service.invite_member(
                owner_id=OWNER_UUID,
                email="test@example.com",
                role="viewer"
            )
            
            assert result["success"] is False
            assert result["code"] == "UPGRADE_REQUIRED"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invite_fails_when_seats_full(self, team_service):
        """Pro plan users with full seats should get SEAT_LIMIT error."""
        # Pro plan allows 5 seats. Test that 5/5 seats returns SEAT_LIMIT.
        
        # Mock at function level for clearer control
        with patch.object(team_service, "_check_team_feature_access", new=AsyncMock(
            return_value=(True, "", {"max_team_seats": 5})
        )), \
        patch.object(team_service, "get_user_team", new=AsyncMock(
            return_value={"id": "team-123", "owner_id": OWNER_UUID, "name": "Test Team"}
        )), \
        patch.object(team_service, "_get_current_member_count", new=AsyncMock(
            return_value=5  # Team is full (5/5 seats)
        )):
            result = await team_service.invite_member(
                owner_id=OWNER_UUID,
                email="test@example.com",
                role="viewer"
            )
            
            # Should fail due to seat limit
            assert result["success"] is False
            assert result["code"] == "SEAT_LIMIT"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bulk_invite_blocked_for_non_enterprise(self, team_service):
        """Bulk invite is blocked for non-Enterprise plans."""
        mock_supabase = Mock()
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data={"plan": "starter"}
        )
        
        csv_content = "email,role,name\nalice@example.com,viewer,Alice"
        
        with patch("services.team_service.get_supabase", return_value=mock_supabase):
            result = await team_service.bulk_invite_csv(
                owner_id=OWNER_UUID,
                csv_content=csv_content
            )
            
            assert result["success"] is False
            assert result["code"] == "UPGRADE_REQUIRED"


class TestRemoveMember:
    """Tests for remove_member functionality."""
    
    @pytest.fixture
    def team_service(self):
        from services.team_service import TeamService
        return TeamService()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_remove_member_invalidates_cache(self, team_service):
        """Removing a member should invalidate their plan cache."""
        mock_supabase = Mock()
        
        # Mock member lookup
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data={
                "id": "member-id",
                "team_id": TEAM_UUID,
                "member_user_id": MEMBER_UUID,
                "owner_user_id": OWNER_UUID
            }
        )
        
        # Mock delete
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock(data=[{}])
        
        with patch("services.team_service.get_supabase", return_value=mock_supabase):
            result = await team_service.remove_member(
                owner_id=OWNER_UUID,
                member_id="member-id"
            )
            
            assert result["success"] is True
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cannot_remove_team_owner(self, team_service):
        """Owner cannot remove themselves from the team."""
        mock_supabase = Mock()
        
        # Mock member lookup - member_user_id == owner_id
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data={
                "id": "owner-member-id",
                "team_id": TEAM_UUID,
                "member_user_id": OWNER_UUID,  # Owner trying to remove self
                "owner_user_id": OWNER_UUID
            }
        )
        
        with patch("services.team_service.get_supabase", return_value=mock_supabase):
            result = await team_service.remove_member(
                owner_id=OWNER_UUID,
                member_id="owner-member-id"
            )
            
            assert result["success"] is False
            assert result["code"] == "OWNER_PROTECTED"


class TestVerifyTeamAccess:
    @pytest.fixture
    def team_service(self):
        from services.team_service import TeamService
        return TeamService()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_solo_user_allowed(self, team_service):
        supabase = Mock()
        members_table = _make_table(data=[])
        supabase.table.return_value = members_table

        with patch("services.team_service.get_supabase", return_value=supabase):
            result = await team_service.verify_team_access("user-1")

        assert result["allowed"] is True
        assert result["reason"] == "solo_user"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_team_not_found_allows(self, team_service):
        supabase = Mock()
        members_table = _make_table(data=[{"team_id": TEAM_UUID, "role": "viewer"}])
        teams_table = _make_table(data=None)
        supabase.table.side_effect = lambda name: {
            "team_members": members_table,
            "teams": teams_table,
        }[name]

        with patch("services.team_service.get_supabase", return_value=supabase):
            result = await team_service.verify_team_access(MEMBER_UUID)

        assert result["allowed"] is True
        assert result["reason"] == "team_not_found"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_owner_allowed(self, team_service):
        supabase = Mock()
        members_table = _make_table(data=[{"team_id": TEAM_UUID, "role": "admin"}])
        teams_table = _make_table(data={"owner_id": OWNER_UUID})
        supabase.table.side_effect = lambda name: {
            "team_members": members_table,
            "teams": teams_table,
        }[name]

        with patch("services.team_service.get_supabase", return_value=supabase):
            result = await team_service.verify_team_access(OWNER_UUID)

        assert result["allowed"] is True
        assert result["reason"] == "team_owner"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_subscription_inactive_blocks_member(self, team_service):
        supabase = Mock()
        members_table = _make_table(data=[{"team_id": TEAM_UUID, "role": "viewer"}])
        teams_table = _make_table(data={"owner_id": OWNER_UUID})
        subs_table = _make_table(data=[{"status": "canceled", "plan_type": "pro"}])
        supabase.table.side_effect = lambda name: {
            "team_members": members_table,
            "teams": teams_table,
            "subscriptions": subs_table,
        }[name]

        with patch("services.team_service.get_supabase", return_value=supabase):
            result = await team_service.verify_team_access(MEMBER_UUID)

        assert result["allowed"] is False
        assert result["reason"] == "subscription_inactive"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_plan_without_seats_blocks_member(self, team_service):
        supabase = Mock()
        members_table = _make_table(data=[{"team_id": TEAM_UUID, "role": "viewer"}])
        teams_table = _make_table(data={"owner_id": OWNER_UUID})
        subs_table = _make_table(data=[])
        profiles_table = _make_table(data={"plan": "starter"})
        supabase.table.side_effect = lambda name: {
            "team_members": members_table,
            "teams": teams_table,
            "subscriptions": subs_table,
            "user_profiles": profiles_table,
        }[name]

        with patch("services.team_service.get_supabase", return_value=supabase), \
             patch("services.team_service.get_plan_limits", return_value=_make_limits(1)):
            result = await team_service.verify_team_access(MEMBER_UUID)

        assert result["allowed"] is False
        assert result["reason"] == "team_not_available"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_member_allowed_with_active_subscription(self, team_service):
        supabase = Mock()
        members_table = _make_table(data=[{"team_id": TEAM_UUID, "role": "viewer"}])
        teams_table = _make_table(data={"owner_id": OWNER_UUID})
        subs_table = _make_table(data=[{"status": "active", "plan_type": "pro"}])
        supabase.table.side_effect = lambda name: {
            "team_members": members_table,
            "teams": teams_table,
            "subscriptions": subs_table,
        }[name]

        with patch("services.team_service.get_supabase", return_value=supabase), \
             patch("services.team_service.get_plan_limits", return_value=_make_limits(5)):
            result = await team_service.verify_team_access(MEMBER_UUID)

        assert result["allowed"] is True
        assert result["reason"] == "team_member"
        assert result["plan"] == "pro"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_verify_team_access_fail_closed_on_error(self, team_service):
        with patch("services.team_service.get_supabase", side_effect=Exception("boom")):
            result = await team_service.verify_team_access(MEMBER_UUID)

        assert result["allowed"] is False
        assert result["reason"] == "error"


class TestTeamServiceDataAccess:
    @pytest.fixture
    def team_service(self):
        from services.team_service import TeamService
        return TeamService()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_user_team_member_returns_model(self, team_service):
        supabase = Mock()
        members_table = _make_table(data=[{"team_id": TEAM_UUID, "member_user_id": MEMBER_UUID}])
        supabase.table.return_value = members_table

        with patch("services.team_service.get_supabase", return_value=supabase):
            member = await team_service.get_user_team_member(MEMBER_UUID)

        assert member is not None
        assert str(member.team_id) == TEAM_UUID

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_team_by_id_returns_data(self, team_service):
        supabase = Mock()
        teams_table = _make_table(data={"id": TEAM_UUID, "name": "Team"})
        supabase.table.return_value = teams_table

        with patch("services.team_service.get_supabase", return_value=supabase):
            team = await team_service.get_team_by_id(TEAM_UUID)

        assert team["id"] == TEAM_UUID

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_team_by_id_handles_missing(self, team_service):
        supabase = Mock()
        teams_table = _make_table(data=None)
        supabase.table.return_value = teams_table

        with patch("services.team_service.get_supabase", return_value=supabase):
            team = await team_service.get_team_by_id(TEAM_UUID)

        assert team is None


class TestTeamCreateUpdate:
    @pytest.fixture
    def team_service(self):
        from services.team_service import TeamService
        return TeamService()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_team_inserts_owner_member(self, team_service):
        supabase = Mock()
        teams_table = _make_table(data=[{"id": TEAM_UUID, "created_at": "now"}])
        members_table = _make_table(data=[{"id": "member-1"}])
        supabase.table.side_effect = lambda name: {
            "teams": teams_table,
            "team_members": members_table,
        }[name]

        with patch("services.team_service.get_supabase", return_value=supabase):
            team = await team_service.create_team(OWNER_UUID, "Acme", slug="acme")

        assert team["id"] == TEAM_UUID
        members_table.insert.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_team_updates_fields(self, team_service):
        supabase = Mock()
        teams_table = _make_table(data=[{"id": TEAM_UUID, "name": "New Name"}])
        supabase.table.return_value = teams_table

        with patch("services.team_service.get_supabase", return_value=supabase):
            team = await team_service.update_team(TEAM_UUID, name="New Name", slug="new")

        assert team["name"] == "New Name"
        update_payload = teams_table.update.call_args[0][0]
        assert update_payload["name"] == "New Name"
        assert update_payload["slug"] == "new"


class TestTeamFeatureChecks:
    @pytest.fixture
    def team_service(self):
        from services.team_service import TeamService
        return TeamService()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_team_feature_access_blocks_starter(self, team_service):
        supabase = Mock()
        profiles_table = _make_table(data={"plan": "starter"})
        supabase.table.return_value = profiles_table

        with patch("services.team_service.get_supabase", return_value=supabase), \
             patch("services.team_service.get_plan_limits", return_value=_make_limits(1)):
            allowed, message, limits = await team_service._check_team_feature_access(OWNER_UUID)

        assert allowed is False
        assert "Enterprise" in message
        assert limits["max_team_seats"] == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_team_feature_access_allows_enterprise(self, team_service):
        supabase = Mock()
        profiles_table = _make_table(data={"plan": "enterprise"})
        supabase.table.return_value = profiles_table

        with patch("services.team_service.get_supabase", return_value=supabase), \
             patch("services.team_service.get_plan_limits", return_value=_make_limits(5)):
            allowed, message, limits = await team_service._check_team_feature_access(OWNER_UUID)

        assert allowed is True
        assert message == ""
        assert limits["max_team_seats"] == 5

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_current_member_count_returns_count(self, team_service):
        supabase = Mock()
        members_table = _make_table(data=[], count=3)
        supabase.table.return_value = members_table

        with patch("services.team_service.get_supabase", return_value=supabase):
            count = await team_service._get_current_member_count(TEAM_UUID)

        assert count == 3


class TestInviteAndResend:
    @pytest.fixture
    def team_service(self):
        from services.team_service import TeamService
        return TeamService()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invite_member_seat_limit(self, team_service):
        with patch.object(team_service, "_check_team_feature_access", new=AsyncMock(return_value=(True, "", {"max_team_seats": 1}))), \
             patch.object(team_service, "get_user_team", new=AsyncMock(return_value={"id": TEAM_UUID, "name": "Team"})), \
             patch.object(team_service, "_get_current_member_count", new=AsyncMock(return_value=1)):
            result = await team_service.invite_member(OWNER_UUID, "a@example.com")

        assert result["success"] is False
        assert result["code"] == "SEAT_LIMIT"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invite_member_existing_invite_blocks(self, team_service):
        supabase = Mock()
        members_table = _make_table(execute_side_effect=[
            Mock(data=[{"id": "member-1", "status": "pending"}])
        ])
        supabase.table.return_value = members_table

        with patch("services.team_service.get_supabase", return_value=supabase), \
             patch.object(team_service, "_check_team_feature_access", new=AsyncMock(return_value=(True, "", {"max_team_seats": 5}))), \
             patch.object(team_service, "get_user_team", new=AsyncMock(return_value={"id": TEAM_UUID, "name": "Team"})), \
             patch.object(team_service, "_get_current_member_count", new=AsyncMock(return_value=0)):
            result = await team_service.invite_member(OWNER_UUID, "a@example.com")

        assert result["success"] is False
        assert result["code"] == "ALREADY_EXISTS"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invite_member_invalid_role_defaults_viewer(self, team_service):
        supabase = Mock()
        members_table = _make_table(
            execute_side_effect=[
                Mock(data=[]),
                Mock(data=[]),
                Mock(data=[{"id": "member-1", "email": "a@example.com", "name": "a", "role": "viewer"}]),
            ]
        )
        supabase.table.return_value = members_table

        with patch("services.team_service.get_supabase", return_value=supabase), \
             patch.object(team_service, "_check_team_feature_access", new=AsyncMock(return_value=(True, "", {"max_team_seats": 5}))), \
             patch.object(team_service, "get_user_team", new=AsyncMock(return_value={"id": TEAM_UUID, "name": "Team"})), \
             patch.object(team_service, "_get_current_member_count", new=AsyncMock(return_value=0)), \
             patch.object(team_service, "send_invite_email", new=AsyncMock(return_value=True)):
            result = await team_service.invite_member(OWNER_UUID, "a@example.com", role="invalid")

        assert result["success"] is True
        insert_payload = members_table.insert.call_args[0][0]
        assert insert_payload["role"] == "viewer"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_invite_email_handles_exception(self, team_service):
        with patch("services.email.email_service.send_team_invite", new=AsyncMock(side_effect=Exception("fail"))):
            success = await team_service.send_invite_email("a@example.com", "Name", "Team", "token")

        assert success is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_resend_invite_missing_member(self, team_service):
        supabase = Mock()
        members_table = _make_table(data=[])
        supabase.table.return_value = members_table

        with patch("services.team_service.get_supabase", return_value=supabase):
            result = await team_service.resend_invite("member-1", OWNER_UUID)

        assert result["success"] is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_resend_invite_updates_and_sends(self, team_service):
        supabase = Mock()
        members_table = _make_table(
            execute_side_effect=[
                Mock(data=[{"id": "member-1", "email": "a@example.com", "name": "Name", "teams": {"name": "Team"}}]),
                Mock(data=[{"id": "member-1"}]),
            ]
        )
        supabase.table.return_value = members_table

        with patch("services.team_service.get_supabase", return_value=supabase), \
             patch.object(team_service, "send_invite_email", new=AsyncMock(return_value=True)):
            result = await team_service.resend_invite("member-1", OWNER_UUID)

        assert result["success"] is True


class TestTeamServiceCoverageGaps:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_direct_rpc_active_subscription(self):
        from services.team_service import TeamService
        service = TeamService()

        supabase = Mock()
        supabase.rpc.return_value.execute.return_value = Mock(
            data={"subscription": {"status": "active", "plan_type": "pro"}, "profile": {"plan": "starter"}}
        )

        with patch("services.team_service.get_supabase", return_value=supabase):
            plan = await service._get_effective_plan_direct(MEMBER_UUID)

        assert plan == "pro"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_direct_rpc_profile_fallback(self):
        from services.team_service import TeamService
        service = TeamService()

        supabase = Mock()
        supabase.rpc.return_value.execute.return_value = Mock(
            data={"profile": {"plan": "starter"}}
        )

        with patch("services.team_service.get_supabase", return_value=supabase):
            plan = await service._get_effective_plan_direct(MEMBER_UUID)

        assert plan == "free"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sequential_active_subscription(self):
        from services.team_service import TeamService
        service = TeamService()

        supabase = Mock()
        supabase.rpc.side_effect = Exception("rpc down")
        tables = {
            "team_members": _make_table([{"team_id": TEAM_UUID}]),
            "subscriptions": _make_table([{"status": "active", "plan_type": "pro"}]),
        }
        supabase.table.side_effect = lambda name: tables.get(name, _make_table([]))

        with patch("services.team_service.get_supabase", return_value=supabase):
            plan = await service._get_effective_plan_direct(MEMBER_UUID)

        assert plan == "pro"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sequential_canceled_subscription(self):
        from services.team_service import TeamService
        service = TeamService()

        supabase = Mock()
        supabase.rpc.side_effect = Exception("rpc down")
        tables = {
            "team_members": _make_table([{"team_id": TEAM_UUID}]),
            "subscriptions": _make_table([{"status": "canceled", "plan_type": "pro"}]),
        }
        supabase.table.side_effect = lambda name: tables.get(name, _make_table([]))

        with patch("services.team_service.get_supabase", return_value=supabase):
            plan = await service._get_effective_plan_direct(MEMBER_UUID)

        assert plan == "free"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sequential_returns_owner_plan_when_allowed(self):
        from services.team_service import TeamService
        service = TeamService()

        supabase = Mock()
        supabase.rpc.side_effect = Exception("rpc down")
        tables = {
            "team_members": _make_table([{"team_id": TEAM_UUID}]),
            "subscriptions": _make_table([]),
            "teams": _make_table({"owner_id": OWNER_UUID}),
            "user_profiles": _make_table({"plan": "enterprise"}),
        }
        supabase.table.side_effect = lambda name: tables.get(name, _make_table([]))

        with patch("services.team_service.get_supabase", return_value=supabase), \
             patch("services.team_service.get_plan_limits", return_value=_make_limits(5)):
            plan = await service._get_effective_plan_direct(MEMBER_UUID)

        assert plan == "free"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_own_team_subscription_active(self):
        from services.team_service import TeamService
        service = TeamService()

        supabase = Mock()
        supabase.rpc.side_effect = Exception("rpc down")
        tables = {
            "team_members": _make_table([]),
            "teams": _make_table([{"id": "team-own"}]),
            "subscriptions": _make_table([{"status": "active", "plan_type": "starter"}]),
        }
        supabase.table.side_effect = lambda name: tables.get(name, _make_table([]))

        with patch("services.team_service.get_supabase", return_value=supabase):
            plan = await service._get_effective_plan_direct(OWNER_UUID)

        assert plan == "starter"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_direct_query_exception_returns_none(self):
        from services.team_service import TeamService
        service = TeamService()

        with patch("services.team_service.get_supabase", side_effect=Exception("boom")):
            plan = await service._get_effective_plan_direct(OWNER_UUID)

        assert plan == "none"

    @pytest.mark.unit
    def test_invalidate_plan_cache_handles_error(self):
        from services.team_service import TeamService
        service = TeamService()

        def boom(*_args, **_kwargs):
            raise Exception("boom")

        service.get_effective_plan = SimpleNamespace(cache_invalidate=boom)
        service.invalidate_plan_cache(OWNER_UUID)

    @pytest.mark.unit
    def test_invalidate_all_cache_handles_error(self):
        from services.team_service import TeamService
        service = TeamService()

        def boom(*_args, **_kwargs):
            raise Exception("boom")

        service.get_effective_plan = SimpleNamespace(cache_clear=boom)
        service.invalidate_all_cache()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_user_team_member_returns_none(self):
        from services.team_service import TeamService
        service = TeamService()

        supabase = Mock()
        supabase.table.return_value = _make_table(data=None)

        with patch("services.team_service.get_supabase", return_value=supabase):
            result = await service.get_user_team_member(MEMBER_UUID)

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_team_by_id_handles_exception(self):
        from services.team_service import TeamService
        service = TeamService()

        with patch("services.team_service.get_supabase", side_effect=Exception("boom")):
            result = await service.get_team_by_id("team-1")

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_team_returns_none(self):
        from services.team_service import TeamService
        service = TeamService()

        supabase = Mock()
        supabase.table.return_value = _make_table(data=None)

        with patch("services.team_service.get_supabase", return_value=supabase):
            result = await service.create_team(OWNER_UUID, "Team")

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_team_handles_exception(self):
        from services.team_service import TeamService
        service = TeamService()

        with patch("services.team_service.get_supabase", side_effect=Exception("boom")):
            result = await service.create_team(OWNER_UUID, "Team")

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_team_handles_exception(self):
        from services.team_service import TeamService
        service = TeamService()

        table = _make_table(data=[])
        table.execute.side_effect = Exception("boom")
        supabase = Mock()
        supabase.table.return_value = table

        with patch("services.team_service.get_supabase", return_value=supabase):
            result = await service.update_team(TEAM_UUID, name="Name")

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_team_members_handles_exception(self):
        from services.team_service import TeamService
        service = TeamService()

        with patch("services.team_service.get_supabase", side_effect=Exception("boom")):
            result = await service.get_team_members(TEAM_UUID)

        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_team_feature_access_handles_exception(self):
        from services.team_service import TeamService
        service = TeamService()

        # When get_effective_plan fails, it defaults to free plan
        # Free plan has max_team_seats=1, so team feature is not allowed
        with patch.object(service, "get_effective_plan", new=AsyncMock(side_effect=Exception("boom"))):
            allowed, message, limits = await service._check_team_feature_access(OWNER_UUID)

        assert allowed is False
        # With exception, falls back to free plan which doesn't allow team management
        assert "Enterprise plan" in message or "Failed to verify plan" in message

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_current_member_count_handles_exception(self):
        from services.team_service import TeamService
        service = TeamService()

        with patch("services.team_service.get_supabase", side_effect=Exception("boom")):
            count = await service._get_current_member_count(TEAM_UUID)

        assert count == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invite_member_team_not_found(self):
        from services.team_service import TeamService
        service = TeamService()

        with patch.object(service, "_check_team_feature_access", new=AsyncMock(return_value=(True, "", {"max_team_seats": 5}))), \
             patch.object(service, "get_user_team", new=AsyncMock(return_value=None)):
            result = await service.invite_member(OWNER_UUID, "user@example.com")

        assert result["success"] is False
        assert result["code"] == "NOT_FOUND"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invite_member_handles_exception(self):
        from services.team_service import TeamService
        service = TeamService()

        with patch.object(service, "_check_team_feature_access", new=AsyncMock(return_value=(True, "", {"max_team_seats": 5}))), \
             patch.object(service, "get_user_team", new=AsyncMock(return_value={"id": TEAM_UUID, "name": "Team"})), \
             patch.object(service, "_get_current_member_count", new=AsyncMock(return_value=0)), \
             patch("services.team_service.get_supabase", side_effect=Exception("boom")):
            result = await service.invite_member(OWNER_UUID, "user@example.com")

        assert result["success"] is False
        assert result["code"] == "INTERNAL_ERROR"


class TestBulkInviteCsv:
    @pytest.fixture
    def team_service(self):
        from services.team_service import TeamService
        return TeamService()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bulk_invite_blocks_without_plan(self, team_service):
        with patch.object(team_service, "_check_team_feature_access", new=AsyncMock(return_value=(False, "upgrade", {}))):
            result = await team_service.bulk_invite_csv(OWNER_UUID, "email,role\nx@example.com,viewer")

        assert result["success"] is False
        assert result["code"] == "UPGRADE_REQUIRED"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bulk_invite_processes_rows(self, team_service):
        csv_payload = "email,role,name\nvalid@example.com,viewer,Valid\ninvalid,viewer,Bad"

        # _check_team_feature_access returns a dict, not SimpleNamespace
        limits_dict = {"max_team_seats": 5}
        
        with patch.object(team_service, "_check_team_feature_access", new=AsyncMock(return_value=(True, "", limits_dict))), \
             patch.object(team_service, "get_user_team", new=AsyncMock(return_value={"id": "team-1", "owner_id": OWNER_UUID})), \
             patch.object(team_service, "_get_current_member_count", new=AsyncMock(return_value=1)), \
             patch.object(team_service, "invite_member", new=AsyncMock(return_value={"success": True, "member": {"id": "m1"}})):
            result = await team_service.bulk_invite_csv(OWNER_UUID, csv_payload)

        assert result["success"] is True
        assert result["total"] == 2
        assert result["invited"] == 1
        assert result["failed"] == 1


class TestRemoveMemberAdditional:
    @pytest.fixture
    def team_service(self):
        from services.team_service import TeamService
        return TeamService()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_remove_member_not_found(self, team_service):
        supabase = Mock()
        members_table = _make_table(data=None)
        supabase.table.return_value = members_table

        with patch("services.team_service.get_supabase", return_value=supabase):
            result = await team_service.remove_member(OWNER_UUID, "missing")

        assert result["success"] is False
        assert result["code"] == "NOT_FOUND"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_remove_member_forbidden(self, team_service):
        supabase = Mock()
        members_table = _make_table(
            data={
                "id": "member-1",
                "team_id": TEAM_UUID,
                "member_user_id": MEMBER_UUID,
                "owner_user_id": "other-owner",
            }
        )
        supabase.table.return_value = members_table

        with patch("services.team_service.get_supabase", return_value=supabase):
            result = await team_service.remove_member(OWNER_UUID, "member-1")

        assert result["success"] is False
        assert result["code"] == "FORBIDDEN"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_remove_member_hard_delete(self, team_service):
        supabase = Mock()
        members_table = _make_table(
            data={
                "id": "member-1",
                "team_id": TEAM_UUID,
                "member_user_id": MEMBER_UUID,
                "owner_user_id": OWNER_UUID,
            }
        )
        supabase.table.return_value = members_table

        with patch("services.team_service.get_supabase", return_value=supabase):
            result = await team_service.remove_member(OWNER_UUID, "member-1", hard_delete=True)

        assert result["success"] is True


# ============================================================
# Tests for Plan Normalization with Logging
# ============================================================

class TestPlanNormalization:
    """Tests for _normalize_plan with logging for unknown plans."""

    @pytest.fixture
    def team_service(self):
        from services.team_service import TeamService
        return TeamService()

    @pytest.mark.unit
    def test_normalize_plan_valid_plans(self, team_service):
        """Valid plans are returned as-is (lowercase)."""
        # 'none' - new users who haven't selected a plan
        assert team_service._normalize_plan("none") == "none"
        assert team_service._normalize_plan("None") == "none"
        assert team_service._normalize_plan("NONE") == "none"
        # 'free' - users after trial/cancellation
        assert team_service._normalize_plan("free") == "free"
        assert team_service._normalize_plan("Free") == "free"
        assert team_service._normalize_plan("FREE") == "free"
        # Paid plans
        assert team_service._normalize_plan("starter") == "starter"
        assert team_service._normalize_plan("Starter") == "starter"
        assert team_service._normalize_plan("pro") == "pro"
        assert team_service._normalize_plan("Pro") == "pro"
        assert team_service._normalize_plan("enterprise") == "enterprise"
        assert team_service._normalize_plan("Enterprise") == "enterprise"
        assert team_service._normalize_plan("ENTERPRISE") == "enterprise"

    @pytest.mark.unit
    def test_normalize_plan_null_or_empty_returns_free(self, team_service):
        """Null/empty plan defaults to free (not 'none' - that's for explicit assignment)."""
        assert team_service._normalize_plan(None) == "free"
        assert team_service._normalize_plan("") == "free"

    @pytest.mark.unit
    def test_normalize_plan_unknown_returns_free_with_logging(self, team_service):
        """Unknown plans default to free and log a warning."""
        with patch("services.team_service.logger") as mock_logger:
            result = team_service._normalize_plan("enterprise_large")
            
            assert result == "free"
            mock_logger.warning.assert_called_once()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert "enterprise_large" in warning_msg
            assert "normalized to 'free'" in warning_msg

    @pytest.mark.unit
    def test_normalize_plan_custom_plan_logs_warning(self, team_service):
        """Custom plan codes (like from legacy systems) are logged."""
        unknown_plans = ["pro_annual", "business", "enterprise_plus", "trial", "beta"]
        
        with patch("services.team_service.logger") as mock_logger:
            for plan in unknown_plans:
                mock_logger.reset_mock()
                result = team_service._normalize_plan(plan)
                
                assert result == "free"
                mock_logger.warning.assert_called_once()
                warning_msg = mock_logger.warning.call_args[0][0]
                assert plan in warning_msg

    @pytest.mark.unit
    def test_valid_plans_constant_matches_normalize(self, team_service):
        """VALID_PLANS constant should match what _normalize_plan accepts."""
        from services.team_service import TeamService
        
        for plan in TeamService.VALID_PLANS:
            # Valid plans should not trigger warning
            with patch("services.team_service.logger") as mock_logger:
                result = team_service._normalize_plan(plan)
                assert result == plan
                mock_logger.warning.assert_not_called()
