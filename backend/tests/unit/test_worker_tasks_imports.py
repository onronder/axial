import builtins
import importlib.util

from worker import tasks as tasks_module


def test_tasks_metrics_import_failure_sets_none(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "core.metrics":
            raise ImportError("boom")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    spec = importlib.util.spec_from_file_location("tasks_no_metrics", tasks_module.__file__)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.job_counters_missing is None
    assert module.status_updates_total is None
