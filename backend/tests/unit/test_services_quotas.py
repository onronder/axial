from unittest.mock import MagicMock, patch

from services import quotas


def _build_table(*, data=None, count=None):
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.neq.return_value = table
    table.limit.return_value = table
    table.in_.return_value = table
    table.execute.return_value = MagicMock(data=data or [], count=count)
    return table


def _build_supabase(table_map):
    supabase = MagicMock()
    supabase.table.side_effect = lambda name: table_map[name]
    return supabase


def test_check_admission_uses_live_documents_for_storage():
    supabase = _build_supabase(
        {
            "org_usage": _build_table(data=[{"storage_used_mb": 9999, "job_count_cycle": 0}]),
            "documents": _build_table(data=[]),
            "teams": _build_table(data=[{"owner_id": "owner-1"}]),
            "team_members": _build_table(data=[]),
            "ingestion_jobs": _build_table(data=[], count=0),
        }
    )

    with patch("services.quotas.get_supabase", return_value=supabase):
        result = quotas.check_admission(
            org_id="org-1",
            plan_code="starter",
            file_size_bytes=None,
            job_count_increment=1,
        )

    assert result["allowed"] is True
    assert result["usage"]["storage_used_mb"] == 0.0


def test_increment_usage_refreshes_live_storage_snapshot():
    org_usage_table = _build_table(data=[{"storage_used_mb": 0, "job_count_cycle": 2}])
    documents_table = _build_table(data=[{"file_size_bytes": 5 * 1024 * 1024}])
    supabase = _build_supabase(
        {
            "org_usage": org_usage_table,
            "documents": documents_table,
        }
    )

    with patch("services.quotas.get_supabase", return_value=supabase):
        quotas.increment_usage(org_id="org-1", storage_bytes=None, job_count_increment=1)

    payload = org_usage_table.upsert.call_args.args[0]
    assert payload["storage_used_mb"] == 5.0
    assert payload["job_count_cycle"] == 3
