from connectors import limits


def test_get_limit_defaults_to_config(monkeypatch):
    monkeypatch.setattr(limits.settings, "CONNECTOR_CONCURRENCY_DEFAULT", 7)
    assert limits._get_limit("unknown") == 7


def test_get_limiter_returns_existing_instance(monkeypatch):
    limits._LIMITERS.clear()
    monkeypatch.setattr(limits.settings, "CONNECTOR_CONCURRENCY_DEFAULT", 2)

    limiter1 = limits._get_limiter("custom")
    limiter2 = limits._get_limiter("custom")

    assert limiter1 is limiter2


def test_get_limit_uses_youtube_specific_setting(monkeypatch):
    monkeypatch.setattr(limits.settings, "CONNECTOR_CONCURRENCY_YOUTUBE", 1)
    assert limits._get_limit("youtube") == 1
