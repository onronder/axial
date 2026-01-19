"""
Test Suite for Ghost Protocol Security Module

Tests for Zero-Retention content encryption in security.py including:
- encrypt_text / decrypt_text functions
- Fail-secure behavior in production
- Strict mode enforcement
- Edge cases and error handling
"""

import importlib
import os
import sys
import types
from unittest.mock import MagicMock, patch

import pytest


def _reload_security(monkeypatch, **env):
    """Helper to reload security module with specific environment variables."""
    for key, value in env.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, str(value))
    import core.security as security
    return importlib.reload(security)


class FakeChunkCipher:
    """Fake Fernet cipher for testing without real encryption."""
    
    def __init__(self, invalid=False, explode=False, explode_encrypt=False):
        self.invalid = invalid
        self.explode = explode
        self.explode_encrypt = explode_encrypt
    
    def encrypt(self, value: bytes) -> bytes:
        if self.explode_encrypt:
            raise RuntimeError("encrypt boom")
        return b"gAAAAA_encrypted:" + value
    
    def decrypt(self, value: bytes) -> bytes:
        if self.explode:
            raise RuntimeError("decrypt boom")
        if self.invalid:
            # Simulate InvalidToken for non-encrypted content
            import core.security as security
            raise security.InvalidToken("invalid token")
        if value.startswith(b"gAAAAA_encrypted:"):
            return value[17:]  # Remove prefix
        # Not our encrypted format - raise InvalidToken
        import core.security as security
        raise security.InvalidToken("not encrypted")


class TestEncryptText:
    """Tests for encrypt_text function."""
    
    def test_encrypt_text_produces_ciphertext(self, monkeypatch):
        """encrypt_text should produce different output than input."""
        security = _reload_security(
            monkeypatch,
            ENVIRONMENT="test",
            SENTRY_DSN="",
            ENCRYPTION_KEY="YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=",
            CHUNK_ENCRYPTION_KEY="LGNy0DAbgvEq4Tvl-d3DN6EFkhiSbpN5mq0zZ3XEN2w=",
        )
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)
        monkeypatch.setattr(security, "_chunk_cipher", FakeChunkCipher())
        
        plaintext = "This is sensitive document content"
        encrypted = security.encrypt_text(plaintext)
        
        assert encrypted != plaintext
        assert "gAAAAA" in encrypted  # Fernet token prefix
    
    def test_encrypt_text_empty_returns_empty(self, monkeypatch):
        """encrypt_text should return empty string for empty input."""
        security = _reload_security(
            monkeypatch,
            ENVIRONMENT="test",
            SENTRY_DSN="",
            ENCRYPTION_KEY="YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=",
        )
        
        assert security.encrypt_text("") == ""
        assert security.encrypt_text(None) is None
    
    def test_encrypt_text_returns_plaintext_in_dev_without_key(self, monkeypatch):
        """In dev/test without key, encrypt_text returns plaintext with warning."""
        security = _reload_security(
            monkeypatch,
            ENVIRONMENT="development",
            SENTRY_DSN="",
            ENCRYPTION_KEY="YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=",
            CHUNK_ENCRYPTION_KEY=None,
        )
        
        plaintext = "test content"
        result = security.encrypt_text(plaintext)
        
        assert result == plaintext
    
    def test_encrypt_text_raises_in_production_without_key(self, monkeypatch):
        """In production without key, encrypt_text raises EncryptionError."""
        security = _reload_security(
            monkeypatch,
            ENVIRONMENT="test",  # Use test to avoid startup crash
            SENTRY_DSN="",
            ENCRYPTION_KEY="YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=",
            CHUNK_ENCRYPTION_KEY=None,
        )
        # Simulate production environment at runtime
        monkeypatch.setattr(security, "ENVIRONMENT", "production")
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", False)
        
        with pytest.raises(security.EncryptionError) as exc:
            security.encrypt_text("test content")
        
        assert "CHUNK_ENCRYPTION_KEY not configured" in str(exc.value)
    
    def test_encrypt_text_handles_unicode(self, monkeypatch):
        """encrypt_text should handle Unicode characters."""
        security = _reload_security(
            monkeypatch,
            ENVIRONMENT="test",
            SENTRY_DSN="",
            ENCRYPTION_KEY="YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=",
            CHUNK_ENCRYPTION_KEY="LGNy0DAbgvEq4Tvl-d3DN6EFkhiSbpN5mq0zZ3XEN2w=",
        )
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)
        monkeypatch.setattr(security, "_chunk_cipher", FakeChunkCipher())
        
        unicode_text = "Hello 世界 🔐 émojis"
        encrypted = security.encrypt_text(unicode_text)
        
        assert encrypted != unicode_text
    
    def test_encrypt_text_raises_on_cipher_error(self, monkeypatch):
        """encrypt_text should raise EncryptionError on cipher failure."""
        security = _reload_security(
            monkeypatch,
            ENVIRONMENT="test",
            SENTRY_DSN="",
            ENCRYPTION_KEY="YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=",
            CHUNK_ENCRYPTION_KEY="LGNy0DAbgvEq4Tvl-d3DN6EFkhiSbpN5mq0zZ3XEN2w=",
        )
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)
        monkeypatch.setattr(security, "_chunk_cipher", FakeChunkCipher(explode_encrypt=True))
        
        with pytest.raises(security.EncryptionError):
            security.encrypt_text("test content")


class TestDecryptText:
    """Tests for decrypt_text function."""
    
    def test_decrypt_text_recovers_plaintext(self, monkeypatch):
        """decrypt_text should recover the original plaintext."""
        security = _reload_security(
            monkeypatch,
            ENVIRONMENT="test",
            SENTRY_DSN="",
            ENCRYPTION_KEY="YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=",
            CHUNK_ENCRYPTION_KEY="LGNy0DAbgvEq4Tvl-d3DN6EFkhiSbpN5mq0zZ3XEN2w=",
        )
        fake_cipher = FakeChunkCipher()
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)
        monkeypatch.setattr(security, "_chunk_cipher", fake_cipher)
        monkeypatch.setattr(security, "_chunk_ciphers", [fake_cipher])  # Key rotation support
        
        original = "This is sensitive document content"
        encrypted = security.encrypt_text(original)
        decrypted = security.decrypt_text(encrypted)
        
        assert decrypted == original
    
    def test_decrypt_text_empty_returns_empty(self, monkeypatch):
        """decrypt_text should return empty string for empty input."""
        security = _reload_security(
            monkeypatch,
            ENVIRONMENT="test",
            SENTRY_DSN="",
            ENCRYPTION_KEY="YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=",
        )
        
        assert security.decrypt_text("") == ""
        assert security.decrypt_text(None) is None
    
    def test_decrypt_text_strict_mode_rejects_plaintext(self, monkeypatch):
        """In strict mode, decrypt_text raises on unencrypted content."""
        security = _reload_security(
            monkeypatch,
            ENVIRONMENT="test",
            SENTRY_DSN="",
            ENCRYPTION_KEY="YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=",
            CHUNK_ENCRYPTION_KEY="LGNy0DAbgvEq4Tvl-d3DN6EFkhiSbpN5mq0zZ3XEN2w=",
            STRICT_ENCRYPTION_MODE="true",
        )
        fake_cipher = FakeChunkCipher(invalid=True)
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)
        monkeypatch.setattr(security, "_chunk_cipher", fake_cipher)
        monkeypatch.setattr(security, "_chunk_ciphers", [fake_cipher])  # Key rotation support
        
        # Mock settings to have STRICT_ENCRYPTION_MODE = True
        mock_settings = MagicMock()
        mock_settings.STRICT_ENCRYPTION_MODE = True
        monkeypatch.setattr(security, "settings", mock_settings)
        
        with pytest.raises(security.UnencryptedContentError) as exc:
            security.decrypt_text("plaintext that was never encrypted")
        
        assert "Ghost Protocol requires all content to be encrypted" in str(exc.value)
    
    def test_decrypt_text_legacy_mode_allows_plaintext(self, monkeypatch):
        """In legacy mode (strict=False), decrypt_text returns plaintext."""
        security = _reload_security(
            monkeypatch,
            ENVIRONMENT="test",
            SENTRY_DSN="",
            ENCRYPTION_KEY="YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=",
            CHUNK_ENCRYPTION_KEY="LGNy0DAbgvEq4Tvl-d3DN6EFkhiSbpN5mq0zZ3XEN2w=",
        )
        fake_cipher = FakeChunkCipher(invalid=True)
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)
        monkeypatch.setattr(security, "_chunk_cipher", fake_cipher)
        monkeypatch.setattr(security, "_chunk_ciphers", [fake_cipher])  # Key rotation support
        
        # Mock settings to have STRICT_ENCRYPTION_MODE = False
        mock_settings = MagicMock()
        mock_settings.STRICT_ENCRYPTION_MODE = False
        monkeypatch.setattr(security, "settings", mock_settings)
        
        plaintext = "legacy plaintext content"
        result = security.decrypt_text(plaintext)
        
        assert result == plaintext
    
    def test_decrypt_text_raises_in_production_without_key(self, monkeypatch):
        """In production without key, decrypt_text raises EncryptionError."""
        security = _reload_security(
            monkeypatch,
            ENVIRONMENT="test",
            SENTRY_DSN="",
            ENCRYPTION_KEY="YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=",
            CHUNK_ENCRYPTION_KEY=None,
        )
        monkeypatch.setattr(security, "ENVIRONMENT", "production")
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", False)
        
        with pytest.raises(security.EncryptionError) as exc:
            security.decrypt_text("some encrypted content")
        
        assert "CHUNK_ENCRYPTION_KEY not configured" in str(exc.value)
    
    def test_decrypt_text_raises_on_cipher_error(self, monkeypatch):
        """decrypt_text should raise EncryptionError on cipher failure."""
        security = _reload_security(
            monkeypatch,
            ENVIRONMENT="test",
            SENTRY_DSN="",
            ENCRYPTION_KEY="YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=",
            CHUNK_ENCRYPTION_KEY="LGNy0DAbgvEq4Tvl-d3DN6EFkhiSbpN5mq0zZ3XEN2w=",
        )
        fake_cipher = FakeChunkCipher(explode=True)
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)
        monkeypatch.setattr(security, "_chunk_cipher", fake_cipher)
        monkeypatch.setattr(security, "_chunk_ciphers", [fake_cipher])  # Key rotation support
        
        with pytest.raises(security.EncryptionError):
            security.decrypt_text("gAAAAA_encrypted:test")


class TestGhostProtocolRoundTrip:
    """Tests for encrypt/decrypt round-trip integrity."""
    
    def test_roundtrip_preserves_content(self, monkeypatch):
        """Encrypt then decrypt should return original content."""
        security = _reload_security(
            monkeypatch,
            ENVIRONMENT="test",
            SENTRY_DSN="",
            ENCRYPTION_KEY="YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=",
            CHUNK_ENCRYPTION_KEY="LGNy0DAbgvEq4Tvl-d3DN6EFkhiSbpN5mq0zZ3XEN2w=",
        )
        fake_cipher = FakeChunkCipher()
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)
        monkeypatch.setattr(security, "_chunk_cipher", fake_cipher)
        monkeypatch.setattr(security, "_chunk_ciphers", [fake_cipher])  # Key rotation support
        
        test_cases = [
            "Simple text",
            "Text with special chars: <>&\"'",
            "Unicode: 日本語 العربية 한국어",
            "Newlines:\nLine 2\nLine 3",
            "Tabs:\tColumn1\tColumn2",
            "Very " + "long " * 1000 + "content",
        ]
        
        for original in test_cases:
            encrypted = security.encrypt_text(original)
            decrypted = security.decrypt_text(encrypted)
            assert decrypted == original, f"Round-trip failed for: {original[:50]}..."
    
    def test_different_content_produces_different_ciphertext(self, monkeypatch):
        """Different content should produce different encrypted output."""
        security = _reload_security(
            monkeypatch,
            ENVIRONMENT="test",
            SENTRY_DSN="",
            ENCRYPTION_KEY="YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=",
            CHUNK_ENCRYPTION_KEY="LGNy0DAbgvEq4Tvl-d3DN6EFkhiSbpN5mq0zZ3XEN2w=",
        )
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)
        monkeypatch.setattr(security, "_chunk_cipher", FakeChunkCipher())
        
        encrypted1 = security.encrypt_text("Content A")
        encrypted2 = security.encrypt_text("Content B")
        
        assert encrypted1 != encrypted2


class TestGhostProtocolExceptions:
    """Tests for Ghost Protocol custom exceptions."""
    
    def test_encryption_error_is_exception(self):
        """EncryptionError should be a proper Exception subclass."""
        from core.security import EncryptionError
        
        assert issubclass(EncryptionError, Exception)
        
        error = EncryptionError("test message")
        assert str(error) == "test message"
    
    def test_unencrypted_content_error_is_exception(self):
        """UnencryptedContentError should be a proper Exception subclass."""
        from core.security import UnencryptedContentError
        
        assert issubclass(UnencryptedContentError, Exception)
        
        error = UnencryptedContentError("policy violation")
        assert str(error) == "policy violation"


class TestProductionSafety:
    """Tests for production fail-secure behavior."""
    
    def test_production_requires_chunk_encryption_key(self, monkeypatch):
        """Production should crash on startup without CHUNK_ENCRYPTION_KEY."""
        import core.security as security
        
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.delenv("CHUNK_ENCRYPTION_KEY", raising=False)
        
        with pytest.raises(RuntimeError) as exc:
            importlib.reload(security)
        
        assert "CHUNK_ENCRYPTION_KEY is required in production" in str(exc.value)
        
        # Restore test environment
        monkeypatch.setenv("ENVIRONMENT", "test")
        monkeypatch.setenv(
            "ENCRYPTION_KEY",
            os.environ.get("ENCRYPTION_KEY", "YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=")
        )
        importlib.reload(security)


class TestModuleExports:
    """Tests for module-level exports and constants."""
    
    def test_has_chunk_encryption_flag_exists(self, monkeypatch):
        """HAS_CHUNK_ENCRYPTION flag should be available."""
        security = _reload_security(
            monkeypatch,
            ENVIRONMENT="test",
            SENTRY_DSN="",
            ENCRYPTION_KEY="YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=",
        )
        
        assert hasattr(security, "HAS_CHUNK_ENCRYPTION")
        assert isinstance(security.HAS_CHUNK_ENCRYPTION, bool)
    
    def test_chunk_cipher_is_not_exposed(self, monkeypatch):
        """_chunk_cipher should be private (underscore prefix)."""
        security = _reload_security(
            monkeypatch,
            ENVIRONMENT="test",
            SENTRY_DSN="",
            ENCRYPTION_KEY="YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=",
            CHUNK_ENCRYPTION_KEY="LGNy0DAbgvEq4Tvl-d3DN6EFkhiSbpN5mq0zZ3XEN2w=",
        )
        
        # Should exist but be "private"
        assert hasattr(security, "_chunk_cipher")
        # Should NOT have public version
        assert not hasattr(security, "chunk_cipher")
    
    def test_exceptions_are_exported(self):
        """Custom exceptions should be importable from security module."""
        from core.security import EncryptionError, UnencryptedContentError
        
        assert EncryptionError is not None
        assert UnencryptedContentError is not None
