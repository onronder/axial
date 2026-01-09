import runpy
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from test_tenancy import (
    verify_orphan_user_recovery,
    verify_invite_skip_onboarding,
    run_manual_checks,
)


@pytest.mark.asyncio
async def test_verify_orphan_user_recovery_happy_path():
    fixed_uuid = uuid.UUID("00000000-0000-0000-0000-000000000001")
    expected_email = f"test_orphan_{fixed_uuid}@example.com"

    with patch("test_tenancy.uuid.uuid4", return_value=fixed_uuid):
        supabase = MagicMock()
        supabase.auth.admin.create_user.return_value = SimpleNamespace(user=SimpleNamespace(id="user-1"))
        supabase.auth.admin.delete_user.return_value = None

        profile_data = {"email": expected_email, "plan": "free", "role": "member"}
        table_mock = MagicMock()
        table_mock.select.return_value.eq.return_value.execute.return_value.data = [profile_data]

        supabase.table.return_value = table_mock

        async def noop_sleep(_):
            return None

        result = await verify_orphan_user_recovery(supabase, sleep_func=noop_sleep)
        assert result["user_id"] == "user-1"
        assert result["profile"]["plan"] == "free"
        supabase.auth.admin.delete_user.assert_called_once_with("user-1")


@pytest.mark.asyncio
async def test_verify_invite_skip_onboarding_paths():
    supabase = MagicMock()
    supabase.auth.admin.create_user.side_effect = [
        SimpleNamespace(user=SimpleNamespace(id="user-1")),
        SimpleNamespace(user=SimpleNamespace(id="user-2")),
    ]

    teams_table = MagicMock()
    teams_table.insert.return_value.execute.return_value.data = [{"id": "team-1"}]
    teams_table.delete.return_value.eq.return_value.execute.return_value.data = []

    team_members_table = MagicMock()
    team_members_table.insert.return_value.execute.return_value.data = []

    def table_side_effect(name):
        if name == "teams":
            return teams_table
        if name == "team_members":
            return team_members_table
        return MagicMock()

    supabase.table.side_effect = table_side_effect

    async def fake_get_profile(user_id=None):
        return SimpleNamespace(has_team=user_id == "user-1")

    result = await verify_invite_skip_onboarding(supabase, get_profile_func=fake_get_profile)
    assert result["user_id"] == "user-1"
    assert result["team_id"] == "team-1"
    supabase.auth.admin.delete_user.assert_any_call("user-1")
    supabase.auth.admin.delete_user.assert_any_call("user-2")


def test_run_manual_checks_skips_by_default(monkeypatch):
    monkeypatch.delenv("RUN_MANUAL_TENANCY_CHECKS", raising=False)
    result = run_manual_checks()
    assert result["status"] == "skipped"


def test_run_manual_checks_runs(monkeypatch):
    monkeypatch.setenv("RUN_MANUAL_TENANCY_CHECKS", "1")
    with patch("test_tenancy.get_supabase") as mock_supabase, \
         patch("test_tenancy.verify_orphan_user_recovery") as mock_orphan, \
         patch("test_tenancy.verify_invite_skip_onboarding") as mock_invite:
        mock_supabase.return_value = MagicMock()
        mock_orphan.return_value = MagicMock()
        mock_invite.return_value = MagicMock()
        result = run_manual_checks()
    assert result["status"] == "completed"


def test_module_main_skips(monkeypatch):
    monkeypatch.delenv("RUN_MANUAL_TENANCY_CHECKS", raising=False)
    path = Path(__file__).resolve().parents[3] / "tenancy_smoke.py"
    runpy.run_path(str(path), run_name="__main__")
