import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from services import usage as usage_service


def _make_table(execute_result=None, execute_side_effect=None):
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.single.return_value = table
    table.limit.return_value = table
    if execute_side_effect is not None:
        table.execute.side_effect = execute_side_effect
    else:
        table.execute.return_value = execute_result
    return table


@pytest.mark.asyncio
async def test_get_user_usage_handles_missing_profile():
    user_id = uuid4()
    supabase = MagicMock()
    profile_table = _make_table(execute_side_effect=Exception("PGRST116 no rows"))

    supabase.table.side_effect = lambda name: profile_table

    with patch("services.usage.get_supabase", return_value=supabase):
        usage = await usage_service.get_user_usage(user_id)

    assert usage.plan == "none"
    assert usage.subscription_status == "inactive"
    assert usage.files == 0


@pytest.mark.asyncio
async def test_get_user_usage_subscription_lookup_error_defaults_active():
    user_id = uuid4()
    supabase = MagicMock()

    profile_table = _make_table(execute_result=MagicMock(data={"plan": "starter"}))
    team_members_table = _make_table(execute_side_effect=Exception("boom"))
    documents_table = _make_table(
        execute_result=MagicMock(
            data=[{"file_size_bytes": 10}, {"file_size_bytes": None}]
        )
    )

    def table_side_effect(name):
        if name == "user_profiles":
            return profile_table
        if name == "team_members":
            return team_members_table
        if name == "documents":
            return documents_table
        return _make_table(execute_result=MagicMock(data=[]))

    supabase.table.side_effect = table_side_effect

    with patch("services.usage.get_supabase", return_value=supabase):
        usage = await usage_service.get_user_usage(user_id)

    assert usage.plan == "starter"
    assert usage.subscription_status == "active"
    assert usage.files == 2
    assert usage.storage_bytes == 10


@pytest.mark.asyncio
async def test_get_user_usage_reads_subscription_status():
    user_id = uuid4()
    supabase = MagicMock()

    profile_table = _make_table(execute_result=MagicMock(data={"plan": "starter"}))
    team_members_table = _make_table(execute_result=MagicMock(data=[{"team_id": "team-1"}]))
    subscriptions_table = _make_table(execute_result=MagicMock(data=[{"status": "past_due"}]))
    documents_table = _make_table(execute_result=MagicMock(data=[]))

    def table_side_effect(name):
        if name == "user_profiles":
            return profile_table
        if name == "team_members":
            return team_members_table
        if name == "subscriptions":
            return subscriptions_table
        if name == "documents":
            return documents_table
        return _make_table(execute_result=MagicMock(data=[]))

    supabase.table.side_effect = table_side_effect

    with patch("services.usage.get_supabase", return_value=supabase):
        usage = await usage_service.get_user_usage(user_id)

    assert usage.subscription_status == "past_due"


@pytest.mark.asyncio
async def test_get_user_usage_with_limits():
    user_id = uuid4()
    usage = usage_service.UserUsage(
        user_id=str(user_id),
        files=1,
        storage_bytes=10,
        storage_display="10 B",
        plan="starter",
        subscription_status="active",
    )

    with patch("services.usage.get_user_usage", return_value=usage):
        result = await usage_service.get_user_usage_with_limits(user_id)

    assert result.files_remaining >= 0
    assert result.storage_remaining_bytes >= 0


@pytest.mark.asyncio
async def test_check_feature_access_unknown_feature():
    user_id = uuid4()
    usage = usage_service.UserUsage(
        user_id=str(user_id),
        files=0,
        storage_bytes=0,
        storage_display="0 B",
        plan="free",
        subscription_status="active",
    )

    with patch("services.usage.get_user_usage", return_value=usage):
        result = await usage_service.check_feature_access(user_id, "unknown_feature")

    assert result["allowed"] is True
    assert result["reason"] is None


@pytest.mark.asyncio
async def test_check_feature_access_known_feature():
    user_id = uuid4()
    usage = usage_service.UserUsage(
        user_id=str(user_id),
        files=0,
        storage_bytes=0,
        storage_display="0 B",
        plan="pro",
        subscription_status="active",
    )

    with patch("services.usage.get_user_usage", return_value=usage):
        result = await usage_service.check_feature_access(user_id, "web_crawl")

    assert result["allowed"] is True
