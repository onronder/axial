import runpy
from pathlib import Path
from types import SimpleNamespace

from debug_auth_request import run_requests, DEFAULT_URL, DUMMY_TOKEN


class DummyRequests:
    def __init__(self, responses=None, raise_exc=False):
        self._responses = responses or []
        self._raise = raise_exc
        self.calls = []

    def post(self, url, headers=None, data=None, files=None, json=None, **_kwargs):
        if json is not None and data is None:
            data = json
        self.calls.append({"url": url, "headers": headers, "data": data, "files": files, "json": json})
        if self._raise:
            raise RuntimeError("network error")
        if self._responses:
            return self._responses.pop(0)
        return SimpleNamespace(status_code=200, text="ok")


def test_run_requests_success_path():
    dummy = DummyRequests(responses=[
        SimpleNamespace(status_code=401, text="unauthorized"),
        SimpleNamespace(status_code=403, text="forbidden"),
    ])
    output = run_requests(url=DEFAULT_URL, requests_module=dummy, print_fn=lambda *_: None)

    assert len(output) == 2
    assert output[0]["status_code"] == 401
    assert output[1]["status_code"] == 403
    assert dummy.calls[1]["headers"]["Authorization"].endswith(DUMMY_TOKEN)


def test_run_requests_handles_errors():
    dummy = DummyRequests(raise_exc=True)
    output = run_requests(url=DEFAULT_URL, requests_module=dummy, print_fn=lambda *_: None)

    assert len(output) == 2
    assert "error" in output[0]
    assert "error" in output[1]


def test_module_main_executes(monkeypatch):
    import requests

    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: SimpleNamespace(status_code=200, text="ok"))
    path = Path(__file__).resolve().parents[2] / "debug_auth_request.py"
    runpy.run_path(str(path), run_name="__main__")
