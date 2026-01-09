import runpy
from pathlib import Path

from test_jwt import build_expired_token, decode_token, run_demo


def test_build_expired_token_contains_three_parts():
    token = build_expired_token(now=1700000000)
    parts = token.split(".")
    assert len(parts) == 3


def test_decode_token_returns_payload():
    token = build_expired_token(now=1700000000)
    result = decode_token(token)
    assert "decoded" in result
    assert result["decoded"]["sub"] == "1234567890"


def test_decode_token_handles_error():
    result = decode_token("not-a-jwt")
    assert "error" in result


def test_run_demo_error_branch(monkeypatch):
    monkeypatch.setattr("test_jwt.decode_token", lambda _token: {"error": "bad"})
    result = run_demo()
    assert "error" in result


def test_module_main_executes():
    path = Path(__file__).resolve().parents[2] / "test_jwt.py"
    runpy.run_path(str(path), run_name="__main__")
