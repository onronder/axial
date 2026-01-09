from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from core import quotas


@pytest.mark.asyncio
async def test_check_quota_allows_within_limit():
    profiles_table = MagicMock()
    profiles_table.select.return_value = profiles_table
    profiles_table.eq.return_value = profiles_table
    profiles_table.single.return_value = profiles_table
    profiles_table.execute.return_value = MagicMock(data={"plan": "starter"})

    docs_table = MagicMock()
    docs_table.select.return_value = docs_table
    docs_table.eq.return_value = docs_table
    docs_table.execute.return_value = MagicMock(count=0)

    supabase = MagicMock()
    supabase.table.side_effect = lambda name: profiles_table if name == "user_profiles" else docs_table

    with patch("core.quotas.get_supabase", return_value=supabase):
        await quotas.check_quota("user-1", "files")


@pytest.mark.asyncio
async def test_check_quota_blocks_when_over_limit():
    profiles_table = MagicMock()
    profiles_table.select.return_value = profiles_table
    profiles_table.eq.return_value = profiles_table
    profiles_table.single.return_value = profiles_table
    profiles_table.execute.return_value = MagicMock(data={"plan": "starter"})

    docs_table = MagicMock()
    docs_table.select.return_value = docs_table
    docs_table.eq.return_value = docs_table
    docs_table.execute.return_value = MagicMock(count=quotas.settings.LIMITS_STARTER_FILES)

    supabase = MagicMock()
    supabase.table.side_effect = lambda name: profiles_table if name == "user_profiles" else docs_table

    with patch("core.quotas.get_supabase", return_value=supabase):
        with pytest.raises(HTTPException) as exc:
            await quotas.check_quota("user-1", "files")
    assert exc.value.status_code == 402


@pytest.mark.asyncio
async def test_check_quota_uses_pro_limit():
    profiles_table = MagicMock()
    profiles_table.select.return_value = profiles_table
    profiles_table.eq.return_value = profiles_table
    profiles_table.single.return_value = profiles_table
    profiles_table.execute.return_value = MagicMock(data={"plan": "pro"})

    docs_table = MagicMock()
    docs_table.select.return_value = docs_table
    docs_table.eq.return_value = docs_table
    docs_table.execute.return_value = MagicMock(count=0)

    supabase = MagicMock()
    supabase.table.side_effect = lambda name: profiles_table if name == "user_profiles" else docs_table

    with patch("core.quotas.get_supabase", return_value=supabase):
        await quotas.check_quota("user-1", "files")


@pytest.mark.asyncio
async def test_check_quota_enterprise_returns_without_check():
    profiles_table = MagicMock()
    profiles_table.select.return_value = profiles_table
    profiles_table.eq.return_value = profiles_table
    profiles_table.single.return_value = profiles_table
    profiles_table.execute.return_value = MagicMock(data={"plan": "enterprise"})

    supabase = MagicMock()
    supabase.table.return_value = profiles_table

    with patch("core.quotas.get_supabase", return_value=supabase):
        await quotas.check_quota("user-1", "files")


@pytest.mark.asyncio
async def test_check_quota_fails_open_on_db_error():
    profiles_table = MagicMock()
    profiles_table.select.return_value = profiles_table
    profiles_table.eq.return_value = profiles_table
    profiles_table.single.return_value = profiles_table
    profiles_table.execute.side_effect = Exception("boom")

    docs_table = MagicMock()
    docs_table.select.return_value = docs_table
    docs_table.eq.return_value = docs_table
    docs_table.execute.side_effect = Exception("boom")

    supabase = MagicMock()
    supabase.table.side_effect = lambda name: profiles_table if name == "user_profiles" else docs_table

    with patch("core.quotas.get_supabase", return_value=supabase):
        await quotas.check_quota("user-1", "files")


def test_format_bytes():
    assert quotas.format_bytes(1024) == "1024.0 B"
    assert quotas.format_bytes(1025) == "1.0 KB"


def test_get_plan_limits_defaults_to_free():
    limits = quotas.get_plan_limits("unknown-plan")
    assert limits.plan_name == "free"
