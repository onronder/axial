from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest
from starlette.requests import Request

from api.v1.dlq import (
    get_failed_task_for_job,
    manual_retry_task,
    resolve_failed_task,
    get_dlq_stats,
    get_my_failed_tasks,
    admin_get_all_failed_tasks,
    admin_trigger_retry_cycle,
    admin_get_global_stats,
    ManualRetryRequest,
    HTTPException,
)


@pytest.fixture
def mock_request():
    """Create a mock request for rate-limited DLQ endpoints."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/dlq",
        "query_string": b"",
        "headers": [],
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 12345),
        "app": None,
    }
    return Request(scope=scope)


def _sample_task(task_id="task-1", status="failed", attempt_count=1, max_retries=3):
    now = datetime.now(timezone.utc)
    return {
        "id": task_id,
        "task_id": "celery-1",
        "task_name": "process_file",
        "user_id": "user-1",
        "job_id": "job-1",
        "status": status,
        "attempt_count": attempt_count,
        "max_retries": max_retries,
        "created_at": now,
        "updated_at": now,
    }


@pytest.mark.asyncio
async def test_get_failed_task_for_job_returns_none(mock_request):
    supabase = MagicMock()
    supabase.table().select().eq().eq().order().limit().execute.return_value = Mock(data=[])

    with patch("api.v1.dlq.get_supabase", return_value=supabase):
        result = await get_failed_task_for_job(request=mock_request, job_id="job-1", user_id="user-1")

    assert result is None


@pytest.mark.asyncio
async def test_get_failed_task_for_job_returns_task(mock_request):
    supabase = MagicMock()
    supabase.table().select().eq().eq().order().limit().execute.return_value = Mock(
        data=[_sample_task()]
    )

    with patch("api.v1.dlq.get_supabase", return_value=supabase):
        result = await get_failed_task_for_job(request=mock_request, job_id="job-1", user_id="user-1")

    assert result.task_id == "celery-1"


@pytest.mark.asyncio
async def test_get_failed_task_for_job_handles_error(mock_request):
    supabase = MagicMock()
    supabase.table().select().eq().eq().order().limit().execute.side_effect = Exception("boom")

    with patch("api.v1.dlq.get_supabase", return_value=supabase):
        with pytest.raises(HTTPException) as exc:
            await get_failed_task_for_job(request=mock_request, job_id="job-1", user_id="user-1")

    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_manual_retry_task_not_found(mock_request):
    supabase = MagicMock()
    supabase.table().select().eq().eq().single().execute.return_value = Mock(data=None)

    with patch("api.v1.dlq.get_supabase", return_value=supabase):
        with pytest.raises(HTTPException) as exc:
            await manual_retry_task(http_request=mock_request, task_id="task-1", request=ManualRetryRequest(), user_id="user-1")
        assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_manual_retry_task_resolved_rejected(mock_request):
    supabase = MagicMock()
    supabase.table().select().eq().eq().single().execute.return_value = Mock(data=_sample_task(status="resolved"))

    with patch("api.v1.dlq.get_supabase", return_value=supabase):
        with pytest.raises(HTTPException) as exc:
            await manual_retry_task(http_request=mock_request, task_id="task-1", request=ManualRetryRequest(), user_id="user-1")
        assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_manual_retry_task_retrying_rejected(mock_request):
    supabase = MagicMock()
    supabase.table().select().eq().eq().single().execute.return_value = Mock(data=_sample_task(status="retrying"))

    with patch("api.v1.dlq.get_supabase", return_value=supabase):
        with pytest.raises(HTTPException) as exc:
            await manual_retry_task(http_request=mock_request, task_id="task-1", request=ManualRetryRequest(), user_id="user-1")
        assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_manual_retry_task_exceeds_retries(mock_request):
    supabase = MagicMock()
    supabase.table().select().eq().eq().single().execute.return_value = Mock(
        data=_sample_task(attempt_count=3, max_retries=3)
    )

    with patch("api.v1.dlq.get_supabase", return_value=supabase):
        with pytest.raises(HTTPException) as exc:
            await manual_retry_task(http_request=mock_request, task_id="task-1", request=ManualRetryRequest(), user_id="user-1")
        assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_manual_retry_task_success(mock_request):
    supabase = MagicMock()
    supabase.table().select().eq().eq().single().execute.return_value = Mock(data=_sample_task())
    supabase.table().update().eq().execute.return_value = Mock(data=[{"id": "task-1"}])

    with patch("api.v1.dlq.get_supabase", return_value=supabase):
        result = await manual_retry_task(http_request=mock_request, task_id="task-1", request=ManualRetryRequest(), user_id="user-1")

    assert result.success is True
    assert result.new_status == "pending_retry"


@pytest.mark.asyncio
async def test_manual_retry_task_update_failure(mock_request):
    supabase = MagicMock()
    supabase.table().select().eq().eq().single().execute.return_value = Mock(data=_sample_task())
    supabase.table().update().eq().execute.return_value = Mock(data=[])

    with patch("api.v1.dlq.get_supabase", return_value=supabase):
        with pytest.raises(HTTPException) as exc:
            await manual_retry_task(http_request=mock_request, task_id="task-1", request=ManualRetryRequest(), user_id="user-1")

    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_manual_retry_task_exception(mock_request):
    supabase = MagicMock()
    supabase.table().select().eq().eq().single().execute.return_value = Mock(data=_sample_task())
    supabase.table().update().eq().execute.side_effect = Exception("boom")

    with patch("api.v1.dlq.get_supabase", return_value=supabase):
        with pytest.raises(HTTPException) as exc:
            await manual_retry_task(http_request=mock_request, task_id="task-1", request=ManualRetryRequest(), user_id="user-1")

    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_resolve_failed_task_already_resolved(mock_request):
    supabase = MagicMock()
    supabase.table().select().eq().eq().single().execute.return_value = Mock(data=_sample_task(status="resolved"))

    with patch("api.v1.dlq.get_supabase", return_value=supabase):
        with pytest.raises(HTTPException) as exc:
            await resolve_failed_task(request=mock_request, task_id="task-1", user_id="user-1")
        assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_resolve_failed_task_success(mock_request):
    supabase = MagicMock()
    supabase.table().select().eq().eq().single().execute.return_value = Mock(data=_sample_task())
    supabase.table().update().eq().execute.return_value = Mock(data=[{"id": "task-1"}])

    with patch("api.v1.dlq.get_supabase", return_value=supabase):
        result = await resolve_failed_task(request=mock_request, task_id="task-1", user_id="user-1")

    assert result.new_status == "resolved"


@pytest.mark.asyncio
async def test_resolve_failed_task_not_found(mock_request):
    supabase = MagicMock()
    supabase.table().select().eq().eq().single().execute.return_value = Mock(data=None)

    with patch("api.v1.dlq.get_supabase", return_value=supabase):
        with pytest.raises(HTTPException) as exc:
            await resolve_failed_task(request=mock_request, task_id="task-1", user_id="user-1")

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_resolve_failed_task_update_failure(mock_request):
    supabase = MagicMock()
    supabase.table().select().eq().eq().single().execute.return_value = Mock(data=_sample_task())
    supabase.table().update().eq().execute.return_value = Mock(data=[])

    with patch("api.v1.dlq.get_supabase", return_value=supabase):
        with pytest.raises(HTTPException) as exc:
            await resolve_failed_task(request=mock_request, task_id="task-1", user_id="user-1")

    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_resolve_failed_task_exception(mock_request):
    supabase = MagicMock()
    supabase.table().select().eq().eq().single().execute.return_value = Mock(data=_sample_task())
    supabase.table().update().eq().execute.side_effect = Exception("boom")

    with patch("api.v1.dlq.get_supabase", return_value=supabase):
        with pytest.raises(HTTPException) as exc:
            await resolve_failed_task(request=mock_request, task_id="task-1", user_id="user-1")

    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_get_dlq_stats_empty(mock_request):
    supabase = MagicMock()
    supabase.table().select().eq().execute.return_value = Mock(data=[])

    with patch("api.v1.dlq.get_supabase", return_value=supabase):
        stats = await get_dlq_stats(request=mock_request, user_id="user-1")

    assert stats.total_failed == 0


@pytest.mark.asyncio
async def test_get_dlq_stats_counts(mock_request):
    supabase = MagicMock()
    supabase.table().select().eq().execute.return_value = Mock(data=[
        {"status": "pending_retry"},
        {"status": "retrying"},
        {"status": "resolved"},
    ])

    with patch("api.v1.dlq.get_supabase", return_value=supabase):
        stats = await get_dlq_stats(request=mock_request, user_id="user-1")

    assert stats.total_failed == 3
    assert stats.pending_retry == 1
    assert stats.retrying == 1
    assert stats.resolved == 1


@pytest.mark.asyncio
async def test_get_dlq_stats_handles_error(mock_request):
    supabase = MagicMock()
    supabase.table().select().eq().execute.side_effect = Exception("boom")

    with patch("api.v1.dlq.get_supabase", return_value=supabase):
        with pytest.raises(HTTPException) as exc:
            await get_dlq_stats(request=mock_request, user_id="user-1")

    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_get_my_failed_tasks_invalid_status(mock_request):
    with pytest.raises(HTTPException) as exc:
        await get_my_failed_tasks(request=mock_request, status_filter="bad", user_id="user-1")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_get_my_failed_tasks_success(mock_request):
    supabase = MagicMock()
    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.order.return_value = query
    query.range.return_value = query
    query.execute.return_value = Mock(data=[_sample_task()], count=1)
    supabase.table.return_value = query

    with patch("api.v1.dlq.get_supabase", return_value=supabase):
        result = await get_my_failed_tasks(request=mock_request, user_id="user-1")

    assert result.total == 1
    assert len(result.tasks) == 1


@pytest.mark.asyncio
async def test_get_my_failed_tasks_with_status_filter(mock_request):
    supabase = MagicMock()
    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.order.return_value = query
    query.range.return_value = query
    query.execute.return_value = Mock(data=[_sample_task(status="failed")], count=1)
    supabase.table.return_value = query

    with patch("api.v1.dlq.get_supabase", return_value=supabase):
        result = await get_my_failed_tasks(request=mock_request, status_filter="failed", user_id="user-1")

    assert result.total == 1


@pytest.mark.asyncio
async def test_get_my_failed_tasks_handles_error(mock_request):
    supabase = MagicMock()
    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.order.return_value = query
    query.range.return_value = query
    query.execute.side_effect = Exception("boom")
    supabase.table.return_value = query

    with patch("api.v1.dlq.get_supabase", return_value=supabase):
        with pytest.raises(HTTPException) as exc:
            await get_my_failed_tasks(request=mock_request, user_id="user-1")

    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_admin_get_all_failed_tasks_success(mock_request):
    supabase = MagicMock()
    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.order.return_value = query
    query.range.return_value = query
    query.execute.return_value = Mock(data=[_sample_task()], count=1)
    supabase.table.return_value = query

    with patch("api.v1.dlq.get_supabase", return_value=supabase):
        result = await admin_get_all_failed_tasks(request=mock_request, user_id="admin")

    assert result.total == 1


@pytest.mark.asyncio
async def test_admin_get_all_failed_tasks_status_filter(mock_request):
    supabase = MagicMock()
    query = MagicMock()
    query.eq.return_value = query
    query.order.return_value = query
    query.range.return_value = query
    query.execute.return_value = Mock(data=[_sample_task(status="failed")], count=1)
    supabase.table.return_value = query

    with patch("api.v1.dlq.get_supabase", return_value=supabase):
        result = await admin_get_all_failed_tasks(request=mock_request, status_filter="failed", user_id="admin")

    assert result.total == 1


@pytest.mark.asyncio
async def test_admin_get_all_failed_tasks_handles_error(mock_request):
    supabase = MagicMock()
    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.order.return_value = query
    query.range.return_value = query
    query.execute.side_effect = Exception("boom")
    supabase.table.return_value = query

    with patch("api.v1.dlq.get_supabase", return_value=supabase):
        with pytest.raises(HTTPException) as exc:
            await admin_get_all_failed_tasks(request=mock_request, user_id="admin")

    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_admin_trigger_retry_cycle(mock_request):
    with patch("api.v1.dlq.retry_failed_tasks", return_value={"retried": 1, "failed": 0}):
        result = await admin_trigger_retry_cycle(request=mock_request, user_id="admin")

    assert result["retried"] == 1


@pytest.mark.asyncio
async def test_admin_trigger_retry_cycle_handles_error(mock_request):
    with patch("api.v1.dlq.retry_failed_tasks", side_effect=Exception("boom")):
        with pytest.raises(HTTPException) as exc:
            await admin_trigger_retry_cycle(request=mock_request, user_id="admin")

    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_admin_get_global_stats_empty(mock_request):
    supabase = MagicMock()
    supabase.table().select().execute.return_value = Mock(data=[])

    with patch("api.v1.dlq.get_supabase", return_value=supabase):
        result = await admin_get_global_stats(request=mock_request, user_id="admin")

    assert result["total_failed"] == 0


@pytest.mark.asyncio
async def test_admin_get_global_stats_counts(mock_request):
    supabase = MagicMock()
    supabase.table().select().execute.return_value = Mock(data=[
        {"status": "pending_retry", "user_id": "user-1"},
        {"status": "resolved", "user_id": "user-2"},
    ])

    with patch("api.v1.dlq.get_supabase", return_value=supabase):
        result = await admin_get_global_stats(request=mock_request, user_id="admin")

    assert result["total_failed"] == 2
    assert result["unique_users"] == 2


@pytest.mark.asyncio
async def test_admin_get_global_stats_handles_error(mock_request):
    supabase = MagicMock()
    supabase.table().select().execute.side_effect = Exception("boom")

    with patch("api.v1.dlq.get_supabase", return_value=supabase):
        with pytest.raises(HTTPException) as exc:
            await admin_get_global_stats(request=mock_request, user_id="admin")

    assert exc.value.status_code == 500
