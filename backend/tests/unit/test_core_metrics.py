import importlib
import sys
import types


def _reload_metrics(monkeypatch):
    import core.metrics as metrics
    return importlib.reload(metrics)


def test_metrics_enabled_when_prometheus_available(monkeypatch):
    fake_prom = types.ModuleType("prometheus_client")

    class DummyMetric:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

        def inc(self, *args, **kwargs):
            return None

        def observe(self, *args, **kwargs):
            return None

        def set(self, *args, **kwargs):
            return None

        def info(self, *args, **kwargs):
            return None

    fake_prom.Counter = DummyMetric
    fake_prom.Histogram = DummyMetric
    fake_prom.Gauge = DummyMetric
    fake_prom.Info = DummyMetric

    monkeypatch.setitem(sys.modules, "prometheus_client", fake_prom)
    metrics = _reload_metrics(monkeypatch)
    assert metrics.METRICS_ENABLED is True


def test_metrics_dummy_set_when_prometheus_missing(monkeypatch):
    original_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "prometheus_client":
            raise ImportError("no prom")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    sys.modules.pop("prometheus_client", None)

    metrics = _reload_metrics(monkeypatch)
    assert metrics.METRICS_ENABLED is False
    metrics.MEMORY_USAGE.set(1)
    metrics.operation_duration.observe(1.0)
    metrics.MEMORY_USAGE.labels("dummy").inc()


def test_metrics_system_info_exception_is_handled(monkeypatch):
    fake_prom = types.ModuleType("prometheus_client")

    class DummyMetric:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

        def inc(self, *args, **kwargs):
            return None

        def observe(self, *args, **kwargs):
            return None

        def set(self, *args, **kwargs):
            return None

        def info(self, *args, **kwargs):
            raise RuntimeError("info failed")

    fake_prom.Counter = DummyMetric
    fake_prom.Histogram = DummyMetric
    fake_prom.Gauge = DummyMetric
    fake_prom.Info = DummyMetric

    monkeypatch.setitem(sys.modules, "prometheus_client", fake_prom)
    _reload_metrics(monkeypatch)


# =============================================================================
# H8: LLM Operational Metrics Tests
# =============================================================================

def test_llm_metrics_defined():
    """H8: LLM operational metrics must be registered."""
    from core.metrics import (
        llm_request_duration,
        llm_tokens_total,
        llm_routing_decisions,
        retrieval_score,
        semantic_cache_ops,
        guardrail_classifications,
    )
    assert llm_request_duration is not None
    assert llm_tokens_total is not None
    assert llm_routing_decisions is not None
    assert retrieval_score is not None
    assert semantic_cache_ops is not None
    assert guardrail_classifications is not None


def test_llm_metrics_have_correct_labels():
    """H8: Verify metric label names."""
    from core.metrics import METRICS_ENABLED, llm_request_duration, llm_tokens_total

    if METRICS_ENABLED:
        assert "provider" in llm_request_duration._labelnames
        assert "model" in llm_request_duration._labelnames
        assert "type" in llm_tokens_total._labelnames
