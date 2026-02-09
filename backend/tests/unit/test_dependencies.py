from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_validate_team_access_allows_user():
    with patch(
        "api.v1.dependencies.team_service.verify_team_access",
        new=AsyncMock(return_value={"allowed": True}),
    ):
        from api.v1.dependencies import validate_team_access

        result = await validate_team_access(user_id="user-123")
        assert result == "user-123"


@pytest.mark.asyncio
async def test_validate_team_access_denies_user():
    with patch(
        "api.v1.dependencies.team_service.verify_team_access",
        new=AsyncMock(
            return_value={"allowed": False, "reason": "blocked", "message": "Denied"}
        ),
    ):
        from api.v1.dependencies import validate_team_access

        with pytest.raises(HTTPException) as exc:
            await validate_team_access(user_id="user-123")

        assert exc.value.status_code == 403
        assert exc.value.detail["error"] == "TEAM_ACCESS_DENIED"


@pytest.mark.asyncio
async def test_require_plan_allows_required_plan():
    from api.v1.dependencies import require_plan

    checker = await require_plan(["pro", "enterprise"])
    result = await checker(plan="pro")
    assert result == "pro"


@pytest.mark.asyncio
async def test_require_plan_blocks_other_plans():
    from api.v1.dependencies import require_plan

    checker = await require_plan(["pro"])
    with pytest.raises(HTTPException) as exc:
        await checker(plan="starter")

    assert exc.value.status_code == 403
    assert exc.value.detail["error"] == "PLAN_REQUIRED"


@pytest.mark.asyncio
async def test_require_admin_allows_owner():
    teams_table = MagicMock()
    teams_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": "team-1"}]
    )
    members_table = MagicMock()
    members_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[]
    )

    supabase = MagicMock()
    supabase.table.side_effect = lambda name: teams_table if name == "teams" else members_table

    with patch("api.v1.dependencies.get_supabase", return_value=supabase):
        from api.v1.dependencies import require_admin

        result = await require_admin(user_id="user-123")
        assert result == "user-123"


@pytest.mark.asyncio
async def test_require_admin_allows_admin_member():
    teams_table = MagicMock()
    teams_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[]
    )
    members_table = MagicMock()
    members_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"role": "admin"}]
    )

    supabase = MagicMock()
    supabase.table.side_effect = lambda name: teams_table if name == "teams" else members_table

    with patch("api.v1.dependencies.get_supabase", return_value=supabase):
        from api.v1.dependencies import require_admin

        result = await require_admin(user_id="user-123")
        assert result == "user-123"


@pytest.mark.asyncio
async def test_require_admin_denies_non_admin():
    teams_table = MagicMock()
    teams_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[]
    )
    members_table = MagicMock()
    members_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[]
    )

    supabase = MagicMock()
    supabase.table.side_effect = lambda name: teams_table if name == "teams" else members_table

    with patch("api.v1.dependencies.get_supabase", return_value=supabase):
        from api.v1.dependencies import require_admin

        with pytest.raises(HTTPException) as exc:
            await require_admin(user_id="user-123")

        assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_admin_handles_errors():
    with patch("api.v1.dependencies.get_supabase", side_effect=Exception("boom")):
        from api.v1.dependencies import require_admin

        with pytest.raises(HTTPException) as exc:
            await require_admin(user_id="user-123")

        assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_get_effective_plan_dependency_returns_plan():
    with patch(
        "api.v1.dependencies.team_service.get_effective_plan",
        new=AsyncMock(return_value="pro"),
    ):
        from api.v1.dependencies import get_effective_plan

        result = await get_effective_plan(user_id="user-123")

    assert result == "pro"


@pytest.mark.asyncio
async def test_require_paid_access_allows_paid_plan():
    with patch(
        "api.v1.dependencies.team_service.get_effective_plan",
        new=AsyncMock(return_value="pro"),
    ):
        from api.v1.dependencies import require_paid_access

        result = await require_paid_access(user_id="user-123")
        assert result == "user-123"


@pytest.mark.asyncio
async def test_require_paid_access_blocks_free_plan():
    with patch(
        "api.v1.dependencies.team_service.get_effective_plan",
        new=AsyncMock(return_value="free"),
    ):
        from api.v1.dependencies import require_paid_access

        with pytest.raises(HTTPException) as exc:
            await require_paid_access(user_id="user-123")

        assert exc.value.status_code == 402
        assert exc.value.detail["error"] == "SUBSCRIPTION_REQUIRED"

@pytest.mark.asyncio
async def test_require_paid_access_blocks_none_plan():
    """New users with plan='none' should also be blocked."""
    with patch(
        "api.v1.dependencies.team_service.get_effective_plan",
        new=AsyncMock(return_value="none"),
    ):
        from api.v1.dependencies import require_paid_access

        with pytest.raises(HTTPException) as exc:
            await require_paid_access(user_id="user-123")

        assert exc.value.status_code == 402
        assert exc.value.detail["error"] == "SUBSCRIPTION_REQUIRED"


@pytest.mark.asyncio
async def test_require_paid_access_allows_starter_plan():
    """Starter plan users should have access."""
    with patch(
        "api.v1.dependencies.team_service.get_effective_plan",
        new=AsyncMock(return_value="starter"),
    ):
        from api.v1.dependencies import require_paid_access

        result = await require_paid_access(user_id="user-123")
        assert result == "user-123"
