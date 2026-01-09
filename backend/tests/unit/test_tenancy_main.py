import runpy
from pathlib import Path


def test_tenancy_main_guard_runs(monkeypatch):
    monkeypatch.delenv("RUN_MANUAL_TENANCY_CHECKS", raising=False)
    tenancy_path = Path(__file__).resolve().parents[2] / "test_tenancy.py"
    runpy.run_path(str(tenancy_path), run_name="__main__")
