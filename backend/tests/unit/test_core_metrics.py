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
