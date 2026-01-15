import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from core.exceptions import QuotaExceededError
from services import usage as usage_service


def _make_chain_table(data=None):
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.limit.return_value = table
    table.update.return_value = table
    table.upsert.return_value = table
    table.execute.return_value = SimpleNamespace(data=data)
    return table


@pytest.mark.asyncio
async def test_check_llm_quota_raises_on_zero_balance_override():
    teams_table = _make_chain_table(data=[{"llm_token_balance": 0}])
    org_usage_table = _make_chain_table(data=[{"llm_tokens_used": 5}])

    def table_side_effect(name):
        return {
            "teams": teams_table,
            "org_usage": org_usage_table,
        }.get(name, _make_chain_table())

    supabase = MagicMock()
    supabase.table.side_effect = table_side_effect

    with patch("services.usage.get_supabase", return_value=supabase):
        with pytest.raises(QuotaExceededError):
            await usage_service.check_llm_quota("org-1", "starter", required_tokens=1)


@pytest.mark.asyncio
async def test_check_llm_quota_allows_with_plan_balance():
    teams_table = _make_chain_table(data=[{"llm_token_balance": None}])
    org_usage_table = _make_chain_table(data=[{"llm_tokens_used": 10}])

    def table_side_effect(name):
        return {
            "teams": teams_table,
            "org_usage": org_usage_table,
        }.get(name, _make_chain_table())

    supabase = MagicMock()
    supabase.table.side_effect = table_side_effect

    with patch("services.usage.get_supabase", return_value=supabase):
        result = await usage_service.check_llm_quota("org-1", "starter", required_tokens=5)

    assert result["balance"] > 0


@pytest.mark.asyncio
async def test_record_llm_usage_updates_usage_and_balance():
    teams_table = _make_chain_table(data=[{"llm_token_balance": 50}])
    org_usage_table = _make_chain_table(data=[{"llm_tokens_used": 10}])

    def table_side_effect(name):
        return {
            "teams": teams_table,
            "org_usage": org_usage_table,
        }.get(name, _make_chain_table())

    supabase = MagicMock()
    supabase.table.side_effect = table_side_effect

    with patch("services.usage.get_supabase", return_value=supabase):
        await usage_service.record_llm_usage("org-1", 5, plan_code="starter", provider="openai", model="gpt-4o-mini")

    org_usage_table.upsert.assert_called_once()
    upsert_payload = org_usage_table.upsert.call_args[0][0]
    assert upsert_payload["llm_tokens_used"] == 15

    teams_table.update.assert_called_once()
    update_payload = teams_table.update.call_args[0][0]
    assert update_payload["llm_token_balance"] == 45
