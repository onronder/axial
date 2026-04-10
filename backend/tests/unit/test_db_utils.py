import importlib
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


def test_metrics_import_fallback(monkeypatch):
    original_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "core.metrics":
            raise ImportError("no metrics")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    import core.db_utils as db_utils
    db_utils = importlib.reload(db_utils)
    assert db_utils.retry_total is None
    assert db_utils.retry_success is None
    assert db_utils.retry_failure is None
    assert db_utils.operation_duration is None


def test_is_retryable_supabase_error_reads_response_status():
    import core.db_utils as db_utils

    class DummyResponse:
        status_code = 429

    class DummyError(Exception):
        response = DummyResponse()

    assert db_utils.is_retryable_supabase_error(DummyError())


def test_insert_rows_with_retry_raises_when_max_attempts_zero():
    import core.db_utils as db_utils

    class DummySupabase:
        def table(self, name):
            raise AssertionError("should not be called")

    supabase = DummySupabase()
    try:
        db_utils.insert_rows_with_retry(
            supabase,
            "documents",
            [{"id": 1}],
            context="test",
            max_attempts=0,
        )
    except RuntimeError as exc:
        assert "exhausted" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")


def test_delete_rows_with_retry_raises_when_max_attempts_zero():
    import core.db_utils as db_utils

    class DummySupabase:
        def table(self, name):
            raise AssertionError("should not be called")

    supabase = DummySupabase()
    try:
        db_utils.delete_rows_with_retry(
            supabase,
            "documents",
            "id",
            "doc-1",
            context="test",
            max_attempts=0,
        )
    except RuntimeError as exc:
        assert "exhausted" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")


def test_get_status_code_prefers_explicit_status():
    import core.db_utils as db_utils

    class DummyError(Exception):
        status_code = 503

    assert db_utils._get_status_code(DummyError()) == 503


def test_get_status_code_reads_response_status():
    import core.db_utils as db_utils

    class DummyResponse:
        status_code = 429

    class DummyError(Exception):
        response = DummyResponse()

    assert db_utils._get_status_code(DummyError()) == 429


def test_insert_rows_with_retry_raises_on_empty_rows():
    import core.db_utils as db_utils

    supabase = MagicMock()

    with pytest.raises(ValueError):
        db_utils.insert_rows_with_retry(
            supabase,
            "documents",
            [],
            context="empty",
            max_attempts=1,
        )


def test_insert_rows_with_retry_success_records_metrics(monkeypatch):
    import core.db_utils as db_utils

    table = MagicMock()
    table.insert.return_value = table
    table.execute.return_value = SimpleNamespace(data=[{"id": "doc-1"}])

    supabase = MagicMock()
    supabase.table.return_value = table

    op_metric = MagicMock()
    op_metric.labels.return_value = op_metric

    retry_success = MagicMock()
    retry_success.labels.return_value = retry_success

    monkeypatch.setattr(db_utils, "operation_duration", op_metric)
    monkeypatch.setattr(db_utils, "retry_success", retry_success)

    result, duration = db_utils.insert_rows_with_retry(
        supabase,
        "documents",
        [{"id": "doc-1"}],
        context="success",
        max_attempts=1,
    )

    assert result.data[0]["id"] == "doc-1"
    assert duration >= 0
    op_metric.observe.assert_called()
    retry_success.inc.assert_not_called()


def test_insert_rows_with_retry_retries_then_succeeds(monkeypatch):
    import core.db_utils as db_utils

    class DummyError(Exception):
        status_code = 429

    table = MagicMock()
    table.insert.return_value = table
    table.execute.side_effect = [DummyError("rate limit"), SimpleNamespace(data=[{"id": "doc-1"}])]

    supabase = MagicMock()
    supabase.table.return_value = table

    retry_total = MagicMock()
    retry_total.labels.return_value = retry_total
    retry_success = MagicMock()
    retry_success.labels.return_value = retry_success

    monkeypatch.setattr(db_utils, "retry_total", retry_total)
    monkeypatch.setattr(db_utils, "retry_success", retry_success)
    monkeypatch.setattr(db_utils.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(db_utils.random, "uniform", lambda _a, _b: 0.0)

    result, _duration = db_utils.insert_rows_with_retry(
        supabase,
        "documents",
        [{"id": "doc-1"}],
        context="retry",
        max_attempts=2,
    )

    assert result.data[0]["id"] == "doc-1"
    assert table.execute.call_count == 2
    retry_total.inc.assert_called_once()
    retry_success.inc.assert_called_once()


def test_insert_rows_with_retry_suppresses_intermediate_warning_logs(monkeypatch):
    import core.db_utils as db_utils

    class DummyError(Exception):
        status_code = 429

    table = MagicMock()
    table.insert.return_value = table
    table.execute.side_effect = [
        DummyError("rate limit"),
        DummyError("rate limit again"),
        SimpleNamespace(data=[{"id": "doc-1"}]),
    ]

    supabase = MagicMock()
    supabase.table.return_value = table

    monkeypatch.setattr(db_utils.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(db_utils.random, "uniform", lambda _a, _b: 0.0)
    warning = MagicMock()
    debug = MagicMock()
    monkeypatch.setattr(db_utils.logger, "warning", warning)
    monkeypatch.setattr(db_utils.logger, "debug", debug)

    db_utils.insert_rows_with_retry(
        supabase,
        "documents",
        [{"id": "doc-1"}],
        context="retry",
        max_attempts=3,
    )

    warning.assert_called_once()
    debug.assert_called_once()


def test_insert_rows_with_retry_non_retryable_raises(monkeypatch):
    import core.db_utils as db_utils

    class DummyError(Exception):
        status_code = 400

    table = MagicMock()
    table.insert.return_value = table
    table.execute.side_effect = DummyError("bad request")

    supabase = MagicMock()
    supabase.table.return_value = table

    retry_failure = MagicMock()
    retry_failure.labels.return_value = retry_failure

    monkeypatch.setattr(db_utils, "retry_failure", retry_failure)
    monkeypatch.setattr(db_utils, "is_retryable_error", lambda _exc: False)

    with pytest.raises(DummyError):
        db_utils.insert_rows_with_retry(
            supabase,
            "documents",
            [{"id": "doc-1"}],
            context="no-retry",
            max_attempts=2,
        )

    retry_failure.inc.assert_called_once()


def test_delete_rows_with_retry_success(monkeypatch):
    import core.db_utils as db_utils

    table = MagicMock()
    table.delete.return_value = table
    table.eq.return_value = table
    table.execute.return_value = SimpleNamespace(data=[{"id": "doc-1"}])

    supabase = MagicMock()
    supabase.table.return_value = table

    op_metric = MagicMock()
    op_metric.labels.return_value = op_metric
    monkeypatch.setattr(db_utils, "operation_duration", op_metric)

    result, _duration = db_utils.delete_rows_with_retry(
        supabase,
        "documents",
        "id",
        "doc-1",
        context="delete",
        max_attempts=1,
    )

    assert result.data[0]["id"] == "doc-1"
    op_metric.observe.assert_called()


def test_delete_rows_with_retry_retries_then_fails(monkeypatch):
    import core.db_utils as db_utils

    class DummyError(Exception):
        status_code = 503

    table = MagicMock()
    table.delete.return_value = table
    table.eq.return_value = table
    table.execute.side_effect = DummyError("down")

    supabase = MagicMock()
    supabase.table.return_value = table

    retry_total = MagicMock()
    retry_total.labels.return_value = retry_total
    retry_failure = MagicMock()
    retry_failure.labels.return_value = retry_failure

    monkeypatch.setattr(db_utils, "retry_total", retry_total)
    monkeypatch.setattr(db_utils, "retry_failure", retry_failure)
    monkeypatch.setattr(db_utils.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(db_utils.random, "uniform", lambda _a, _b: 0.0)

    with pytest.raises(DummyError):
        db_utils.delete_rows_with_retry(
            supabase,
            "documents",
            "id",
            "doc-1",
            context="delete-retry",
            max_attempts=2,
        )

    assert retry_total.inc.call_count == 2
    retry_failure.inc.assert_called_once()


def test_delete_rows_with_retry_logs_first_and_last_attempts(monkeypatch):
    import core.db_utils as db_utils

    class DummyError(Exception):
        status_code = 503

    table = MagicMock()
    table.delete.return_value = table
    table.eq.return_value = table
    table.execute.side_effect = [
        DummyError("down"),
        DummyError("still down"),
        DummyError("terminal"),
    ]

    supabase = MagicMock()
    supabase.table.return_value = table

    monkeypatch.setattr(db_utils.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(db_utils.random, "uniform", lambda _a, _b: 0.0)
    warning = MagicMock()
    debug = MagicMock()
    monkeypatch.setattr(db_utils.logger, "warning", warning)
    monkeypatch.setattr(db_utils.logger, "debug", debug)

    with pytest.raises(DummyError):
        db_utils.delete_rows_with_retry(
            supabase,
            "documents",
            "id",
            "doc-1",
            context="delete",
            max_attempts=3,
        )

    assert warning.call_count == 2
    debug.assert_called_once()


def test_delete_rows_with_retry_records_retry_success(monkeypatch):
    import core.db_utils as db_utils

    class DummyError(Exception):
        status_code = 503

    table = MagicMock()
    table.delete.return_value = table
    table.eq.return_value = table
    table.execute.side_effect = [DummyError("down"), SimpleNamespace(data=[{"id": "doc-1"}])]

    supabase = MagicMock()
    supabase.table.return_value = table

    retry_success = MagicMock()
    retry_success.labels.return_value = retry_success
    monkeypatch.setattr(db_utils, "retry_success", retry_success)
    monkeypatch.setattr(db_utils.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(db_utils.random, "uniform", lambda _a, _b: 0.0)

    db_utils.delete_rows_with_retry(
        supabase,
        "documents",
        "id",
        "doc-1",
        context="delete",
        max_attempts=2,
    )

    retry_success.inc.assert_called_once()
