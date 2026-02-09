"""
Test Suite for Security Module

Covers JWT verification, token encryption, auth dependency behavior,
and core rate limit helpers.
"""

import importlib
import os
import sys
import types
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request

from core.rate_limit import get_user_id_or_ip, rate_limit_exceeded_handler
from core.security import decrypt_token, encrypt_token, get_current_user


class FakeCipher:
    def __init__(self, invalid=False, explode=False, explode_encrypt=False):
        self.invalid = invalid
        self.explode = explode
        self.explode_encrypt = explode_encrypt

    def encrypt(self, value: bytes) -> bytes:
        if self.explode_encrypt:
            raise RuntimeError("encrypt boom")
        return b"enc:" + value

    def decrypt(self, value: bytes) -> bytes:
        if self.explode:
            raise RuntimeError("boom")
        if self.invalid:
            import core.security as security
            raise security.InvalidToken("invalid")
        if value.startswith(b"enc:"):
            return value[4:]
        return value


class DummyUser:
    def __init__(self, user_id: str):
        self.id = user_id


def load_main():
    sys.modules.setdefault("magic", types.ModuleType("magic"))
    if "main" in sys.modules:
        return importlib.reload(sys.modules["main"])
    return importlib.import_module("main")


class TestJWTVerification:
    """Tests for JWT token verification."""

    @pytest.mark.asyncio
    async def test_valid_jwt_returns_user_id(self):
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
        with patch("core.security.jwt.decode", return_value={"sub": "user-123"}):
            assert await get_current_user(creds) == "user-123"

    @pytest.mark.asyncio
    async def test_expired_jwt_raises_401(self):
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
        with patch("core.security.jwt.decode", side_effect=jwt.ExpiredSignatureError()):
            with pytest.raises(HTTPException) as exc:
                await get_current_user(creds)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_signature_raises_401(self):
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
        with patch("core.security.jwt.decode", side_effect=jwt.InvalidSignatureError()):
            with pytest.raises(HTTPException) as exc:
                await get_current_user(creds)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_token_raises_401(self):
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="")
        with patch("core.security.jwt.decode", side_effect=jwt.InvalidTokenError()):
            with pytest.raises(HTTPException) as exc:
                await get_current_user(creds)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_malformed_token_raises_401(self):
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad.token")
        with patch("core.security.jwt.decode", side_effect=jwt.DecodeError("bad")):
            with pytest.raises(HTTPException) as exc:
                await get_current_user(creds)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_authentication_rejects_invalid_payload(self):
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
        with patch("core.security.jwt.decode", return_value={"email": "x@example.com"}):
            with pytest.raises(HTTPException) as exc:
                await get_current_user(creds)
        assert exc.value.status_code == 401


class TestTokenEncryption:
    """Tests for OAuth token encryption."""

    def test_encrypt_token_produces_ciphertext(self, monkeypatch):
        import core.security as security

        monkeypatch.setattr(security, "HAS_ENCRYPTION", True)
        monkeypatch.setattr(security, "cipher_suite", FakeCipher())
        monkeypatch.setattr(security, "cipher_suites", None)

        plaintext = "my-secret-token"
        encrypted = encrypt_token(plaintext)

        assert encrypted != plaintext
        assert encrypted.startswith("enc:")

    def test_decrypt_token_recovers_plaintext(self, monkeypatch):
        import core.security as security

        monkeypatch.setattr(security, "HAS_ENCRYPTION", True)
        monkeypatch.setattr(security, "cipher_suite", FakeCipher())
        monkeypatch.setattr(security, "cipher_suites", None)

        original = "my-secret-token"
        encrypted = encrypt_token(original)
        decrypted = decrypt_token(encrypted)

        assert decrypted == original

    def test_decrypt_handles_legacy_plaintext(self, monkeypatch):
        import core.security as security

        invalid_token = type("InvalidToken", (Exception,), {})
        monkeypatch.setattr(security, "InvalidToken", invalid_token)
        monkeypatch.setattr(security, "HAS_ENCRYPTION", True)
        monkeypatch.setattr(security, "cipher_suite", FakeCipher(invalid=True))
        monkeypatch.setattr(security, "cipher_suites", None)

        legacy_token = "ya29.legacy-oauth-token"
        with pytest.raises(ValueError):
            decrypt_token(legacy_token)

    def test_encrypt_handles_special_characters(self, monkeypatch):
        import core.security as security

        monkeypatch.setattr(security, "HAS_ENCRYPTION", True)
        monkeypatch.setattr(security, "cipher_suite", FakeCipher())
        monkeypatch.setattr(security, "cipher_suites", None)

        token = "tok-en.with+symbols_123"
        encrypted = encrypt_token(token)
        assert encrypted != token

    def test_decrypt_with_wrong_key_fails_gracefully(self, monkeypatch):
        import core.security as security

        monkeypatch.setattr(security, "HAS_ENCRYPTION", True)
        monkeypatch.setattr(security, "cipher_suite", FakeCipher(explode=True))
        monkeypatch.setattr(security, "cipher_suites", None)

        token = "enc:payload"
        with pytest.raises(RuntimeError):
            decrypt_token(token)

    def test_decrypt_tries_multiple_keys(self, monkeypatch):
        import core.security as security

        monkeypatch.setattr(security, "HAS_ENCRYPTION", True)
        monkeypatch.setattr(security, "cipher_suites", [FakeCipher(invalid=True), FakeCipher()])
        monkeypatch.setattr(security, "cipher_suite", FakeCipher(invalid=True))

        token = "enc:payload"
        assert decrypt_token(token) == "payload"

    def test_encrypt_returns_plaintext_when_disabled(self, monkeypatch):
        import core.security as security

        monkeypatch.setattr(security, "HAS_ENCRYPTION", False)
        monkeypatch.setattr(security, "cipher_suite", None)
        monkeypatch.setattr(security, "cipher_suites", None)

        token = "plain-token"
        assert encrypt_token(token) == token

    def test_encrypt_returns_token_when_empty(self):
        assert encrypt_token("") == ""

    def test_decrypt_returns_plaintext_when_disabled(self, monkeypatch):
        import core.security as security

        monkeypatch.setattr(security, "HAS_ENCRYPTION", False)
        monkeypatch.setattr(security, "cipher_suite", None)
        monkeypatch.setattr(security, "cipher_suites", None)

        token = "plain-token"
        assert decrypt_token(token) == token

    def test_decrypt_returns_token_when_empty(self):
        assert decrypt_token("") == ""

    def test_encrypt_handles_exception(self, monkeypatch):
        import core.security as security

        monkeypatch.setattr(security, "HAS_ENCRYPTION", True)
        monkeypatch.setattr(security, "cipher_suite", FakeCipher(explode_encrypt=True))
        monkeypatch.setattr(security, "cipher_suites", None)

        token = "plain-token"
        assert encrypt_token(token) == token


def test_security_requires_encryption_key_in_production(monkeypatch):
    import core.security as security

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)

    with pytest.raises(RuntimeError):
        importlib.reload(security)

    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("ENCRYPTION_KEY", os.environ.get("ENCRYPTION_KEY", "YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY="))
    importlib.reload(security)


def test_security_import_without_encryption_key(monkeypatch):
    import core.security as security

    module = types.ModuleType("cryptography.fernet")
    module.Fernet = MagicMock()
    module.InvalidToken = Exception

    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    monkeypatch.setitem(sys.modules, "cryptography.fernet", module)

    security = importlib.reload(security)
    assert security.HAS_ENCRYPTION is False
    assert security.cipher_suite is None


def test_security_import_supports_multiple_keys(monkeypatch):
    from cryptography.fernet import Fernet

    import core.security as security

    key_one = Fernet.generate_key().decode()
    key_two = Fernet.generate_key().decode()

    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("ENCRYPTION_KEY", f"{key_one},{key_two}")

    security = importlib.reload(security)
    assert security.HAS_ENCRYPTION is True
    assert security.cipher_suites is not None
    assert len(security.cipher_suites) == 2


def test_security_import_handles_missing_cryptography(monkeypatch):
    import core.security as security
    original_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "cryptography.fernet":
            raise ImportError("missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")

    security = importlib.reload(security)
    assert security.HAS_ENCRYPTION is False
    assert security.cipher_suite is None


class TestAuthenticationMiddleware:
    """Tests for get_current_user dependency."""

    def test_get_current_user_no_debug_logging(self):
        import inspect

        source = inspect.getsource(get_current_user)
        assert "print(token" not in source.lower()


class TestRateLimiting:
    """Tests for rate limiting helpers."""

    def test_excessive_requests_are_throttled(self):
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "client": ("127.0.0.1", 1234),
        }
        request = Request(scope)
        limit = types.SimpleNamespace(error_message=None, limit="10/minute")
        exc = RateLimitExceeded(limit)

        response = rate_limit_exceeded_handler(request, exc)

        assert response.status_code == 429
        assert response.headers.get("Retry-After") == "60"

    def test_rate_limit_key_uses_user_id_when_available(self):
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "client": ("127.0.0.1", 1234),
        }
        request = Request(scope)
        request.state.user = DummyUser("user-123")

        assert get_user_id_or_ip(request) == "user:user-123"

    def test_rate_limit_key_falls_back_to_ip(self):
        """Test that rate limit key falls back to IP for unauthenticated requests."""
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "client": ("127.0.0.1", 1234),
        }
        request = Request(scope)
        # The function returns the client IP from the request scope
        # slowapi's get_remote_address extracts from request.client
        result = get_user_id_or_ip(request)
        # Should return an IP address string (not a user ID)
        assert not result.startswith("user:")
        # Should be a valid IP address format
        assert "." in result or ":" in result


class TestCORS:
    """Tests for CORS configuration."""

    def test_production_cors_rejects_unknown_origins(self, monkeypatch):
        main = load_main()

        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)

        with pytest.raises(RuntimeError):
            main.configure_cors()

    def test_development_cors_allows_localhost(self, monkeypatch):
        main = load_main()

        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)

        origins = main.configure_cors()
        assert "http://localhost:3000" in origins
