import asyncio
import builtins
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import core.db as db


def test_build_client_options_sets_storage():
    options = db._build_client_options()
    assert hasattr(options, "storage")
    assert options.storage is not None


def test_build_client_options_fallback_type_error(monkeypatch):
    class DummyOptions:
        def __init__(self, *args, **kwargs):
            if kwargs:
                raise TypeError("no kwargs")
            self.schema = "public"
            self.auto_refresh_token = True
            self.persist_session = True
            self.postgrest_client_timeout = 120
            self.storage_client_timeout = 20

    monkeypatch.setattr(db, "ClientOptions", DummyOptions)

    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "supabase_auth._sync.storage":
            raise ImportError("no storage")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    options = db._build_client_options()
    assert hasattr(options, "storage")
    assert options.storage is None


def test_build_client_options_adds_storage_when_missing(monkeypatch):
    class DummyOptions:
        def __init__(self, *args, **kwargs):
            self.schema = "public"

    class DummyStorage:
        pass

    monkeypatch.setattr(db, "ClientOptions", DummyOptions)
    monkeypatch.setitem(sys.modules, "supabase_auth._sync.storage", SimpleNamespace(SyncMemoryStorage=DummyStorage))

    options = db._build_client_options()
    assert isinstance(options.storage, DummyStorage)


def test_get_supabase_singleton(monkeypatch):
    dummy_client = MagicMock()
    monkeypatch.setattr(db, "create_client", MagicMock(return_value=dummy_client))
    db.close_supabase()
    first = db.get_supabase()
    second = db.get_supabase()
    assert first is second
    db.close_supabase()


def test_get_supabase_raises_when_create_fails(monkeypatch):
    db.close_supabase()
    monkeypatch.setattr(db, "create_client", MagicMock(side_effect=RuntimeError("boom")))
    with pytest.raises(RuntimeError):
        db.get_supabase()
    db.close_supabase()


def test_check_connection_raises_on_failure(monkeypatch):
    failing_client = MagicMock()
    failing_client.table.return_value.select.return_value.limit.return_value.execute.side_effect = RuntimeError("fail")
    monkeypatch.setattr(db, "get_supabase", MagicMock(return_value=failing_client))
    with pytest.raises(RuntimeError):
        asyncio.run(db.check_connection())


def test_check_connection_returns_true(monkeypatch):
    client = MagicMock()
    client.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock()
    monkeypatch.setattr(db, "get_supabase", MagicMock(return_value=client))
    assert asyncio.run(db.check_connection()) is True


def test_check_connection_retries_then_succeeds(monkeypatch):
    client = MagicMock()
    execute = client.table.return_value.select.return_value.limit.return_value.execute
    execute.side_effect = [RuntimeError("fail1"), MagicMock()]
    monkeypatch.setattr(db, "get_supabase", MagicMock(return_value=client))

    async def run_with_patch():
        # prevent real sleep during test
        async def fake_sleep(_):
            return None
        monkeypatch.setattr(db.asyncio, "sleep", fake_sleep)
        return await db.check_connection()

    assert asyncio.run(run_with_patch()) is True
