from unittest.mock import patch
import builtins

import pytest

from core import job_counters


class FakePipeline:
    def __init__(self, client):
        self.client = client

    def hincrby(self, key, field, amount):
        self.client.hincrby(key, field, amount)
        return self

    def set(self, key, value):
        self.client.set(key, value)
        return self

    def expire(self, key, ttl):
        self.client.expire(key, ttl)
        return self

    def execute(self):
        return True


class FakeRedis:
    def __init__(self):
        self.hashes = {}
        self.values = {}

    def hset(self, key, mapping):
        self.hashes[key] = dict(mapping)
        return True

    def expire(self, key, ttl):
        return True

    def hmget(self, key, fields):
        data = self.hashes.get(key, {})
        return [data.get(field) for field in fields]

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.values:
            return False
        self.values[key] = value
        return True

    def hincrby(self, key, field, amount):
        self.hashes.setdefault(key, {})
        self.hashes[key][field] = int(self.hashes[key].get(field, 0)) + amount
        return self.hashes[key][field]

    def delete(self, *keys):
        for key in keys:
            self.hashes.pop(key, None)
            self.values.pop(key, None)

    def pipeline(self):
        return FakePipeline(self)


def test_job_counter_flow():
    client = FakeRedis()

    with patch("core.job_counters._get_redis_client", return_value=client):
        assert job_counters.init_job_counters("ingest_job", "job-1", 2) is True
        counters = job_counters.get_job_counters("ingest_job", "job-1")
        assert counters["total"] == 2
        assert counters["processed"] == 0

        counters = job_counters.record_job_outcome("ingest_job", "job-1", "file-1", "success")
        assert counters["processed"] == 1
        assert counters["success"] == 1

        counters = job_counters.record_job_outcome("ingest_job", "job-1", "file-1", "success")
        assert counters["processed"] == 1

        job_counters.record_job_update("ingest_job", "job-1", "job_status_updates")
        counters = job_counters.get_job_counters("ingest_job", "job-1")
        assert counters["job_status_updates"] == 1

        assert job_counters.mark_job_finalizing("ingest_job", "job-1") is True
        assert job_counters.mark_job_finalizing("ingest_job", "job-1") is False

        job_counters.clear_job_counters("ingest_job", "job-1")
        assert job_counters.get_job_counters("ingest_job", "job-1") is None


def test_item_key_requires_item_id():
    try:
        job_counters._item_key("ingest_job", "job-1", "")
    except ValueError as exc:
        assert "item_id is required" in str(exc)


def test_record_job_update_ignores_unknown_field():
    client = FakeRedis()
    with patch("core.job_counters._get_redis_client", return_value=client):
        job_counters.init_job_counters("ingest_job", "job-1", 1)
        job_counters.record_job_update("ingest_job", "job-1", "unknown_field")
        counters = job_counters.get_job_counters("ingest_job", "job-1")
        assert counters["job_status_updates"] == 0


def test_normalize_item_id_handles_empty():
    assert job_counters._normalize_item_id("") is None


def test_to_int_handles_invalid():
    assert job_counters._to_int(None) == 0
    assert job_counters._to_int("nope") == 0


def test_get_redis_client_import_error(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "redis":
            raise ImportError("missing redis")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert job_counters._get_redis_client() is None


def test_init_job_counters_requires_job_id():
    client = FakeRedis()
    with patch("core.job_counters._get_redis_client", return_value=client):
        assert job_counters.init_job_counters("ingest_job", "", 1) is False


def test_init_job_counters_returns_false_without_client():
    with patch("core.job_counters._get_redis_client", return_value=None):
        assert job_counters.init_job_counters("ingest_job", "job-1", 1) is False


def test_init_job_counters_handles_exception():
    class BadRedis(FakeRedis):
        def hset(self, key, mapping):
            raise RuntimeError("boom")

    with patch("core.job_counters._get_redis_client", return_value=BadRedis()):
        assert job_counters.init_job_counters("ingest_job", "job-1", 1) is False


def test_get_job_counters_empty_returns_none():
    client = FakeRedis()
    with patch("core.job_counters._get_redis_client", return_value=client):
        assert job_counters.get_job_counters("ingest_job", "job-1") is None


def test_get_job_counters_handles_exception():
    class BadRedis(FakeRedis):
        def hmget(self, key, fields):
            raise RuntimeError("boom")

    with patch("core.job_counters._get_redis_client", return_value=BadRedis()):
        assert job_counters.get_job_counters("ingest_job", "job-1") is None


def test_record_job_outcome_defaults_to_failed():
    client = FakeRedis()
    with patch("core.job_counters._get_redis_client", return_value=client):
        job_counters.init_job_counters("ingest_job", "job-1", 1)
        counters = job_counters.record_job_outcome("ingest_job", "job-1", "file-1", "weird")
        assert counters["failed"] == 1


def test_record_job_outcome_replaces_previous():
    client = FakeRedis()
    with patch("core.job_counters._get_redis_client", return_value=client):
        job_counters.init_job_counters("ingest_job", "job-1", 1)
        job_counters.record_job_outcome("ingest_job", "job-1", "file-1", "success")
        counters = job_counters.record_job_outcome("ingest_job", "job-1", "file-1", "failed")
        assert counters["success"] == 0
        assert counters["failed"] == 1
        assert counters["processed"] == 1


def test_record_job_outcome_handles_exception():
    class BadRedis(FakeRedis):
        def pipeline(self):
            raise RuntimeError("boom")

    with patch("core.job_counters._get_redis_client", return_value=BadRedis()):
        assert job_counters.record_job_outcome("ingest_job", "job-1", "file-1", "success") is None


def test_mark_job_finalizing_handles_exception():
    class BadRedis(FakeRedis):
        def set(self, key, value, nx=False, ex=None):
            raise RuntimeError("boom")

    with patch("core.job_counters._get_redis_client", return_value=BadRedis()):
        assert job_counters.mark_job_finalizing("ingest_job", "job-1") is False


def test_clear_job_counters_no_client():
    with patch("core.job_counters._get_redis_client", return_value=None):
        job_counters.clear_job_counters("ingest_job", "job-1")


def test_get_job_counters_requires_job_id():
    assert job_counters.get_job_counters("ingest_job", "") is None


def test_get_job_counters_no_client():
    with patch("core.job_counters._get_redis_client", return_value=None):
        assert job_counters.get_job_counters("ingest_job", "job-1") is None


def test_record_job_outcome_requires_ids():
    assert job_counters.record_job_outcome("ingest_job", "", "file-1", "success") is None
    assert job_counters.record_job_outcome("ingest_job", "job-1", "", "success") is None


def test_record_job_outcome_no_client():
    with patch("core.job_counters._get_redis_client", return_value=None):
        assert job_counters.record_job_outcome("ingest_job", "job-1", "file-1", "success") is None


def test_record_job_update_requires_job_id():
    job_counters.record_job_update("ingest_job", "", "job_status_updates")


def test_record_job_update_no_client():
    with patch("core.job_counters._get_redis_client", return_value=None):
        job_counters.record_job_update("ingest_job", "job-1", "job_status_updates")


def test_mark_job_finalizing_requires_job_id():
    assert job_counters.mark_job_finalizing("ingest_job", "") is False


def test_mark_job_finalizing_no_client():
    with patch("core.job_counters._get_redis_client", return_value=None):
        assert job_counters.mark_job_finalizing("ingest_job", "job-1") is False


def test_clear_job_counters_requires_job_id():
    job_counters.clear_job_counters("ingest_job", "")


def test_clear_job_counters_handles_exception():
    class BadRedis(FakeRedis):
        def delete(self, *keys):
            raise RuntimeError("boom")

    with patch("core.job_counters._get_redis_client", return_value=BadRedis()):
        job_counters.clear_job_counters("ingest_job", "job-1")


def test_job_counter_wrappers_delegate():
    with patch("core.job_counters.record_job_outcome", return_value={"ok": 1}) as record_outcome:
        assert job_counters.record_ingest_outcome("job-1", "file-1", "success") == {"ok": 1}
        record_outcome.assert_called_once()

    with patch("core.job_counters.get_job_counters", return_value={"total": 1}) as get_counters:
        assert job_counters.get_ingest_job_counters("job-1") == {"total": 1}
        get_counters.assert_called_once()

    with patch("core.job_counters.mark_job_finalizing", return_value=True) as mark_finalize:
        assert job_counters.mark_ingest_job_finalizing("job-1") is True
        mark_finalize.assert_called_once()

    with patch("core.job_counters.clear_job_counters") as clear_counters:
        job_counters.clear_ingest_job_counters("job-1")
        clear_counters.assert_called_once()

    with patch("core.job_counters.init_job_counters", return_value=True) as init_job:
        assert job_counters.init_crawl_counters("crawl-1", 5) is True
        init_job.assert_called_once()

    with patch("core.job_counters.record_job_update") as record_update:
        job_counters.record_ingest_job_update("job-1")
        job_counters.record_ingest_file_update("job-1")
        job_counters.record_crawl_job_update("crawl-1")
        assert record_update.call_count == 3

    with patch("core.job_counters.record_job_outcome", return_value={"ok": 2}) as record_crawl_outcome:
        assert job_counters.record_crawl_outcome("crawl-1", "http://example.com", "success") == {"ok": 2}
        record_crawl_outcome.assert_called_once()

    with patch("core.job_counters.get_job_counters", return_value={"total": 2}) as get_crawl_counters:
        assert job_counters.get_crawl_counters("crawl-1") == {"total": 2}
        get_crawl_counters.assert_called_once()

    with patch("core.job_counters.mark_job_finalizing", return_value=False) as mark_crawl_finalize:
        assert job_counters.mark_crawl_finalizing("crawl-1") is False
        mark_crawl_finalize.assert_called_once()

    with patch("core.job_counters.clear_job_counters") as clear_crawl:
        job_counters.clear_crawl_counters("crawl-1")
        clear_crawl.assert_called_once()
