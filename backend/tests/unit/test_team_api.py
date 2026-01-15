import io
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, UploadFile


@pytest.mark.asyncio
async def test_get_current_team_success():
    with patch(
        "api.v1.team.team_service.get_user_team",
        new=AsyncMock(return_value={"id": "team-1", "name": "Team", "owner_id": "user-1", "created_at": "now"}),
    ):
        from api.v1.team import get_current_team

        result = await get_current_team(user_id="user-1")
        assert result["id"] == "team-1"


@pytest.mark.asyncio
async def test_get_current_team_missing():
    with patch("api.v1.team.team_service.get_user_team", new=AsyncMock(return_value=None)):
        from api.v1.team import get_current_team

        with pytest.raises(HTTPException) as exc:
            await get_current_team(user_id="user-1")
        assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_team_invalid_slug():
    with patch(
        "api.v1.team.team_service.get_user_team",
        new=AsyncMock(return_value={"id": "team-1", "is_owner": True}),
    ):
        from api.v1.team import update_team, TeamUpdate

        with pytest.raises(HTTPException) as exc:
            await update_team(TeamUpdate(slug="Bad Slug"), user_id="user-1")
        assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_team_success():
    supabase = MagicMock()
    table = MagicMock()
    table.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "team-1"}])
    supabase.table.return_value = table

    team_initial = {"id": "team-1", "is_owner": True}
    team_updated = {"id": "team-1", "name": "New", "is_owner": True}

    with patch("api.v1.team.get_supabase", return_value=supabase), \
         patch("api.v1.team.team_service.get_user_team", new=AsyncMock(side_effect=[team_initial, team_updated])):
        from api.v1.team import update_team, TeamUpdate

        result = await update_team(TeamUpdate(name="New"), user_id="user-1")
        assert result["name"] == "New"


@pytest.mark.asyncio
async def test_update_team_slug_success():
    supabase = MagicMock()
    table = MagicMock()
    table.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "team-1"}])
    supabase.table.return_value = table

    team_initial = {"id": "team-1", "is_owner": True}
    team_updated = {"id": "team-1", "slug": "new-slug", "is_owner": True}

    with patch("api.v1.team.get_supabase", return_value=supabase), \
         patch("api.v1.team.team_service.get_user_team", new=AsyncMock(side_effect=[team_initial, team_updated])):
        from api.v1.team import update_team, TeamUpdate

        result = await update_team(TeamUpdate(slug="new-slug"), user_id="user-1")
        assert result["slug"] == "new-slug"

@pytest.mark.asyncio
async def test_delete_team_non_owner():
    with patch(
        "api.v1.team.team_service.get_user_team",
        new=AsyncMock(return_value={"id": "team-1", "is_owner": False}),
    ):
        from api.v1.team import delete_team

        with pytest.raises(HTTPException) as exc:
            await delete_team(purge_data=False, user_id="user-1")
        assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_delete_team_success():
    supabase = MagicMock()
    table = MagicMock()
    table.delete.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    supabase.table.return_value = table

    with patch("api.v1.team.get_supabase", return_value=supabase), \
         patch(
             "api.v1.team.team_service.get_user_team",
             new=AsyncMock(return_value={"id": "team-1", "is_owner": True}),
         ), \
         patch("api.v1.team.team_service.invalidate_plan_cache") as invalidate_cache:
        from api.v1.team import delete_team

        result = await delete_team(purge_data=False, user_id="user-1")
        assert result["status"] == "success"
        invalidate_cache.assert_called_once_with("user-1")


@pytest.mark.asyncio
async def test_list_team_members_filters_and_search():
    supabase = MagicMock()
    query = MagicMock()
    query.eq.return_value = query
    query.order.return_value = query
    query.range.return_value = query
    query.execute.return_value = MagicMock(
        data=[
            {"email": "alice@example.com", "name": "Alice", "status": "active"},
            {"email": "bob@example.com", "name": "Bob", "status": "pending"},
        ]
    )
    table = MagicMock()
    table.select.return_value = query
    supabase.table.return_value = table

    with patch("api.v1.team.get_supabase", return_value=supabase):
        from api.v1.team import list_team_members

        result = await list_team_members(
            user_id="user-1",
            role="viewer",
            status="pending",
            search="bob",
            limit=10,
            offset=0,
        )

    assert len(result) == 1
    assert result[0]["email"] == "bob@example.com"


@pytest.mark.asyncio
async def test_get_team_stats_counts_members():
    supabase = MagicMock()
    table = MagicMock()
    table.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[
            {"status": "active"},
            {"status": "pending"},
            {"status": "pending"},
        ]
    )
    supabase.table.return_value = table

    with patch("api.v1.team.get_supabase", return_value=supabase), \
         patch("api.v1.team.team_service.get_effective_plan", new=AsyncMock(return_value="pro")), \
         patch("core.quotas.get_plan_limits", return_value=SimpleNamespace(max_team_seats=5)):
        from api.v1.team import get_team_stats

        result = await get_team_stats(user_id="user-1")
        assert result.active_members == 1
        assert result.pending_invites == 2
        assert result.total_seats == 5


@pytest.mark.asyncio
async def test_invite_team_member_upgrade_required():
    with patch(
        "api.v1.team.team_service.invite_member",
        new=AsyncMock(return_value={"success": False, "code": "UPGRADE_REQUIRED", "error": "Upgrade"}),
    ):
        from api.v1.team import invite_team_member, InviteRequest

        with pytest.raises(HTTPException) as exc:
            await invite_team_member(InviteRequest(email="a@b.com"), user_id="user-1")
        assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_invite_team_member_success():
    with patch(
        "api.v1.team.team_service.invite_member",
        new=AsyncMock(return_value={"success": True, "member": {"id": "m-1"}}),
    ):
        from api.v1.team import invite_team_member, InviteRequest

        result = await invite_team_member(InviteRequest(email="a@b.com"), user_id="user-1")
        assert result.success is True


@pytest.mark.asyncio
async def test_bulk_invite_team_members_bad_csv():
    file = UploadFile(filename="invites.csv", file=io.BytesIO(b"\xff\xfe"))

    from api.v1.team import bulk_invite_team_members

    with pytest.raises(HTTPException) as exc:
        await bulk_invite_team_members(file=file, user_id="user-1")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_bulk_invite_team_members_upgrade_required():
    file = UploadFile(filename="invites.csv", file=io.BytesIO(b"email,role,name"))

    with patch(
        "api.v1.team.team_service.bulk_invite_csv",
        new=AsyncMock(return_value={"success": False, "code": "UPGRADE_REQUIRED", "error": "Upgrade"}),
    ):
        from api.v1.team import bulk_invite_team_members

        with pytest.raises(HTTPException) as exc:
            await bulk_invite_team_members(file=file, user_id="user-1")
        assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_invite_team_member_legacy_conflict():
    with patch(
        "api.v1.team.team_service.invite_member",
        new=AsyncMock(return_value={"success": False, "code": "ALREADY_EXISTS"}),
    ):
        from api.v1.team import invite_team_member_legacy, TeamMemberCreate

        with pytest.raises(HTTPException) as exc:
            await invite_team_member_legacy(TeamMemberCreate(email="a@b.com"), user_id="user-1")
        assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_invite_team_member_legacy_success():
    member = {"id": "member-1", "email": "a@b.com"}
    with patch(
        "api.v1.team.team_service.invite_member",
        new=AsyncMock(return_value={"success": True, "member": member}),
    ):
        from api.v1.team import invite_team_member_legacy, TeamMemberCreate

        result = await invite_team_member_legacy(TeamMemberCreate(email="a@b.com"), user_id="user-1")

    assert result["id"] == "member-1"


@pytest.mark.asyncio
async def test_update_team_member_invalid_role():
    from api.v1.team import update_team_member, TeamMemberUpdate

    with pytest.raises(HTTPException) as exc:
        await update_team_member(
            member_id="m-1",
            payload=TeamMemberUpdate(role="invalid"),
            user_id="user-1",
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_team_member_success():
    supabase = MagicMock()
    table = MagicMock()
    table.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": "m-1", "role": "editor", "status": "active"}]
    )
    supabase.table.return_value = table

    with patch("api.v1.team.get_supabase", return_value=supabase):
        from api.v1.team import update_team_member, TeamMemberUpdate

        result = await update_team_member(
            member_id="m-1",
            payload=TeamMemberUpdate(role="editor"),
            user_id="user-1",
        )
        assert result["role"] == "editor"


@pytest.mark.asyncio
async def test_update_team_member_updates_name():
    supabase = MagicMock()
    table = MagicMock()
    table.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": "m-1", "name": "New Name"}]
    )
    supabase.table.return_value = table

    with patch("api.v1.team.get_supabase", return_value=supabase):
        from api.v1.team import update_team_member, TeamMemberUpdate

        result = await update_team_member(
            member_id="m-1",
            payload=TeamMemberUpdate(name="New Name"),
            user_id="user-1",
        )

    assert result["name"] == "New Name"


@pytest.mark.asyncio
async def test_update_team_member_updates_status():
    supabase = MagicMock()
    table = MagicMock()
    table.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": "m-1", "status": "suspended"}]
    )
    supabase.table.return_value = table

    with patch("api.v1.team.get_supabase", return_value=supabase):
        from api.v1.team import update_team_member, TeamMemberUpdate

        result = await update_team_member(
            member_id="m-1",
            payload=TeamMemberUpdate(status="suspended"),
            user_id="user-1",
        )

    assert result["status"] == "suspended"

@pytest.mark.asyncio
async def test_remove_team_member_not_found():
    supabase = MagicMock()
    table = MagicMock()
    table.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=None
    )
    supabase.table.return_value = table

    with patch("api.v1.team.get_supabase", return_value=supabase):
        from api.v1.team import remove_team_member

        with pytest.raises(HTTPException) as exc:
            await remove_team_member(member_id="m-1", user_id="user-1")
        assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_resend_invitation_not_found():
    with patch(
        "api.v1.team.team_service.resend_invite",
        new=AsyncMock(return_value={"success": False, "error": "Pending member not found"}),
    ):
        from api.v1.team import resend_invitation

        with pytest.raises(HTTPException) as exc:
            await resend_invitation(member_id="m-1", user_id="user-1")
        assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_resend_invitation_success():
    with patch(
        "api.v1.team.team_service.resend_invite",
        new=AsyncMock(return_value={"success": True}),
    ):
        from api.v1.team import resend_invitation

        result = await resend_invitation(member_id="m-1", user_id="user-1")

    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_accept_invite_invalid_token():
    supabase = MagicMock()
    table = MagicMock()
    table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[]
    )
    supabase.table.return_value = table

    with patch("api.v1.team.get_supabase", return_value=supabase):
        from api.v1.team import accept_invite, AcceptInviteRequest

        with pytest.raises(HTTPException) as exc:
            await accept_invite(AcceptInviteRequest(token="bad"), user_id="user-1")
        assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_accept_invite_success():
    supabase = MagicMock()
    table = MagicMock()
    table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"team_id": "team-1", "teams": {"name": "Team"}}]
    )
    table.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "m-1"}])
    supabase.table.return_value = table

    with patch("api.v1.team.get_supabase", return_value=supabase), \
         patch("api.v1.team.team_service.invalidate_plan_cache") as invalidate_cache:
        from api.v1.team import accept_invite, AcceptInviteRequest

        result = await accept_invite(AcceptInviteRequest(token="m-1"), user_id="user-1")
        assert result.success is True
        invalidate_cache.assert_called_once_with("user-1")


@pytest.mark.asyncio
async def test_update_team_missing_team():
    with patch("api.v1.team.team_service.get_user_team", new=AsyncMock(return_value=None)):
        from api.v1.team import update_team, TeamUpdate

        with pytest.raises(HTTPException) as exc:
            await update_team(TeamUpdate(name="Name"), user_id="user-1")
        assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_team_non_owner():
    with patch(
        "api.v1.team.team_service.get_user_team",
        new=AsyncMock(return_value={"id": "team-1", "is_owner": False}),
    ):
        from api.v1.team import update_team, TeamUpdate

        with pytest.raises(HTTPException) as exc:
            await update_team(TeamUpdate(name="Name"), user_id="user-1")
        assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_update_team_no_fields():
    with patch(
        "api.v1.team.team_service.get_user_team",
        new=AsyncMock(return_value={"id": "team-1", "is_owner": True}),
    ):
        from api.v1.team import update_team, TeamUpdate

        with pytest.raises(HTTPException) as exc:
            await update_team(TeamUpdate(), user_id="user-1")
        assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_team_update_failed():
    supabase = MagicMock()
    table = MagicMock()
    table.update.return_value.eq.return_value.execute.return_value = MagicMock(data=None)
    supabase.table.return_value = table

    with patch("api.v1.team.get_supabase", return_value=supabase), \
         patch(
             "api.v1.team.team_service.get_user_team",
             new=AsyncMock(return_value={"id": "team-1", "is_owner": True}),
         ):
        from api.v1.team import update_team, TeamUpdate

        with pytest.raises(HTTPException) as exc:
            await update_team(TeamUpdate(name="New"), user_id="user-1")
        assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_update_team_handles_exception():
    supabase = MagicMock()
    supabase.table.side_effect = RuntimeError("db down")

    with patch("api.v1.team.get_supabase", return_value=supabase), \
         patch(
             "api.v1.team.team_service.get_user_team",
             new=AsyncMock(return_value={"id": "team-1", "is_owner": True}),
         ):
        from api.v1.team import update_team, TeamUpdate

        with pytest.raises(HTTPException) as exc:
            await update_team(TeamUpdate(name="New"), user_id="user-1")
        assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_delete_team_missing_team():
    with patch("api.v1.team.team_service.get_user_team", new=AsyncMock(return_value=None)):
        from api.v1.team import delete_team

        with pytest.raises(HTTPException) as exc:
            await delete_team(purge_data=False, user_id="user-1")
        assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_team_handles_exception():
    supabase = MagicMock()
    supabase.table.side_effect = RuntimeError("db down")

    with patch("api.v1.team.get_supabase", return_value=supabase), \
         patch(
             "api.v1.team.team_service.get_user_team",
             new=AsyncMock(return_value={"id": "team-1", "is_owner": True}),
         ):
        from api.v1.team import delete_team

        with pytest.raises(HTTPException) as exc:
            await delete_team(purge_data=False, user_id="user-1")
        assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_get_effective_plan_inherited():
    with patch("api.v1.team.team_service.get_effective_plan", new=AsyncMock(return_value="pro")), \
         patch(
             "api.v1.team.team_service.get_user_team",
             new=AsyncMock(return_value={"id": "team-1", "name": "Team", "is_owner": False}),
         ):
        from api.v1.team import get_effective_plan

        result = await get_effective_plan(user_id="user-1")

    assert result.inherited is True
    assert result.team_id == "team-1"
    assert result.team_name == "Team"


@pytest.mark.asyncio
async def test_list_team_members_handles_error():
    supabase = MagicMock()
    query = MagicMock()
    query.eq.return_value = query
    query.order.return_value = query
    query.range.return_value = query
    query.execute.side_effect = RuntimeError("db down")
    table = MagicMock()
    table.select.return_value = query
    supabase.table.return_value = table

    with patch("api.v1.team.get_supabase", return_value=supabase):
        from api.v1.team import list_team_members

        with pytest.raises(HTTPException) as exc:
            await list_team_members(user_id="user-1")
        assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_get_team_stats_handles_error():
    supabase = MagicMock()
    table = MagicMock()
    table.select.return_value.eq.return_value.execute.side_effect = RuntimeError("db down")
    supabase.table.return_value = table

    with patch("api.v1.team.get_supabase", return_value=supabase), \
         patch("api.v1.team.team_service.get_effective_plan", new=AsyncMock(return_value="pro")):
        from api.v1.team import get_team_stats

        with pytest.raises(HTTPException) as exc:
            await get_team_stats(user_id="user-1")
        assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_invite_team_member_already_exists():
    with patch(
        "api.v1.team.team_service.invite_member",
        new=AsyncMock(return_value={"success": False, "code": "ALREADY_EXISTS", "error": "Exists"}),
    ):
        from api.v1.team import invite_team_member, InviteRequest

        with pytest.raises(HTTPException) as exc:
            await invite_team_member(InviteRequest(email="a@b.com"), user_id="user-1")
        assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_invite_team_member_seat_limit():
    with patch(
        "api.v1.team.team_service.invite_member",
        new=AsyncMock(return_value={"success": False, "code": "SEAT_LIMIT", "error": "limit"}),
    ):
        from api.v1.team import invite_team_member, InviteRequest

        with pytest.raises(HTTPException) as exc:
            await invite_team_member(InviteRequest(email="a@b.com"), user_id="user-1")
        assert exc.value.status_code == 402


@pytest.mark.asyncio
async def test_invite_team_member_generic_error():
    with patch(
        "api.v1.team.team_service.invite_member",
        new=AsyncMock(return_value={"success": False, "code": "OTHER", "error": "bad"}),
    ):
        from api.v1.team import invite_team_member, InviteRequest

        with pytest.raises(HTTPException) as exc:
            await invite_team_member(InviteRequest(email="a@b.com"), user_id="user-1")
        assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_bulk_invite_team_members_success():
    file = UploadFile(filename="invites.csv", file=io.BytesIO(b"email,role,name"))

    with patch(
        "api.v1.team.team_service.bulk_invite_csv",
        new=AsyncMock(return_value={"success": True, "invited": 1, "errors": []}),
    ):
        from api.v1.team import bulk_invite_team_members

        result = await bulk_invite_team_members(file=file, user_id="user-1")

    assert result.success is True


@pytest.mark.asyncio
async def test_invite_team_member_legacy_upgrade_required():
    with patch(
        "api.v1.team.team_service.invite_member",
        new=AsyncMock(return_value={"success": False, "code": "UPGRADE_REQUIRED", "error": "Upgrade"}),
    ):
        from api.v1.team import invite_team_member_legacy, TeamMemberCreate

        with pytest.raises(HTTPException) as exc:
            await invite_team_member_legacy(TeamMemberCreate(email="a@b.com"), user_id="user-1")
        assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_invite_team_member_legacy_generic_error():
    with patch(
        "api.v1.team.team_service.invite_member",
        new=AsyncMock(return_value={"success": False, "code": "OTHER", "error": "bad"}),
    ):
        from api.v1.team import invite_team_member_legacy, TeamMemberCreate

        with pytest.raises(HTTPException) as exc:
            await invite_team_member_legacy(TeamMemberCreate(email="a@b.com"), user_id="user-1")
        assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_invite_team_member_legacy_missing_member():
    with patch(
        "api.v1.team.team_service.invite_member",
        new=AsyncMock(return_value={"success": True}),
    ):
        from api.v1.team import invite_team_member_legacy, TeamMemberCreate

        with pytest.raises(HTTPException) as exc:
            await invite_team_member_legacy(TeamMemberCreate(email="a@b.com"), user_id="user-1")
        assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_update_team_member_invalid_status():
    from api.v1.team import update_team_member, TeamMemberUpdate

    with pytest.raises(HTTPException) as exc:
        await update_team_member(
            member_id="m-1",
            payload=TeamMemberUpdate(status="invalid"),
            user_id="user-1",
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_team_member_no_fields():
    from api.v1.team import update_team_member, TeamMemberUpdate

    with pytest.raises(HTTPException) as exc:
        await update_team_member(
            member_id="m-1",
            payload=TeamMemberUpdate(),
            user_id="user-1",
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_team_member_not_found():
    supabase = MagicMock()
    table = MagicMock()
    table.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=None)
    supabase.table.return_value = table

    with patch("api.v1.team.get_supabase", return_value=supabase):
        from api.v1.team import update_team_member, TeamMemberUpdate

        with pytest.raises(HTTPException) as exc:
            await update_team_member(
                member_id="m-1",
                payload=TeamMemberUpdate(role="editor"),
                user_id="user-1",
            )
        assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_team_member_handles_exception():
    supabase = MagicMock()
    table = MagicMock()
    table.update.return_value.eq.return_value.eq.return_value.execute.side_effect = RuntimeError("db down")
    supabase.table.return_value = table

    with patch("api.v1.team.get_supabase", return_value=supabase):
        from api.v1.team import update_team_member, TeamMemberUpdate

        with pytest.raises(HTTPException) as exc:
            await update_team_member(
                member_id="m-1",
                payload=TeamMemberUpdate(role="editor"),
                user_id="user-1",
            )
        assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_remove_team_member_handles_exception():
    supabase = MagicMock()
    table = MagicMock()
    table.delete.return_value.eq.return_value.eq.return_value.execute.side_effect = RuntimeError("db down")
    supabase.table.return_value = table

    with patch("api.v1.team.get_supabase", return_value=supabase):
        from api.v1.team import remove_team_member

        with pytest.raises(HTTPException) as exc:
            await remove_team_member(member_id="m-1", user_id="user-1")
        assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_resend_invitation_unknown_error():
    with patch(
        "api.v1.team.team_service.resend_invite",
        new=AsyncMock(return_value={"success": False, "error": "Boom"}),
    ):
        from api.v1.team import resend_invitation

        with pytest.raises(HTTPException) as exc:
            await resend_invitation(member_id="m-1", user_id="user-1")
        assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_accept_invite_update_failure():
    supabase = MagicMock()
    table = MagicMock()
    table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"team_id": "team-1", "teams": {"name": "Team"}}]
    )
    table.update.return_value.eq.return_value.execute.return_value = MagicMock(data=None)
    supabase.table.return_value = table

    with patch("api.v1.team.get_supabase", return_value=supabase):
        from api.v1.team import accept_invite, AcceptInviteRequest

        with pytest.raises(HTTPException) as exc:
            await accept_invite(AcceptInviteRequest(token="m-1"), user_id="user-1")
        assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_accept_invite_handles_exception():
    supabase = MagicMock()
    table = MagicMock()
    table.select.return_value.eq.return_value.eq.return_value.execute.side_effect = RuntimeError("db down")
    supabase.table.return_value = table

    with patch("api.v1.team.get_supabase", return_value=supabase):
        from api.v1.team import accept_invite, AcceptInviteRequest

        with pytest.raises(HTTPException) as exc:
            await accept_invite(AcceptInviteRequest(token="m-1"), user_id="user-1")
        assert exc.value.status_code == 500
