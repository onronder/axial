"""
Test Suite for Security Module - Ghost Protocol & Content Encryption

Covers content encryption/decryption, key rotation, strict mode,
and all Ghost Protocol functionality.
"""

import importlib
import os
import pytest
from unittest.mock import patch, MagicMock


class FakeChunkCipher:
    """Fake cipher for testing chunk encryption without real cryptography."""
    
    def __init__(self, invalid=False, explode=False, decrypt_value=None):
        self.invalid = invalid
        self.explode = explode
        self.decrypt_value = decrypt_value
    
    def encrypt(self, data: bytes) -> bytes:
        if self.explode:
            raise RuntimeError("encrypt boom")
        return b"gAAAAA" + data  # Fernet tokens start with gAAAAA
    
    def decrypt(self, token: bytes) -> bytes:
        if self.explode:
            raise RuntimeError("decrypt boom")
        if self.invalid:
            import core.security as security
            raise security.InvalidToken("invalid token")
        if self.decrypt_value:
            return self.decrypt_value.encode('utf-8')
        if token.startswith(b"gAAAAA"):
            return token[6:]
        return token


# =============================================================================
# Ghost Protocol: encrypt_text Tests
# =============================================================================

class TestEncryptText:
    """Tests for Ghost Protocol encrypt_text function."""
    
    def test_encrypt_text_returns_empty_for_empty_input(self):
        from core.security import encrypt_text
        assert encrypt_text("") == ""
        assert encrypt_text(None) is None
    
    def test_encrypt_text_produces_ciphertext(self, monkeypatch):
        import core.security as security
        
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)
        monkeypatch.setattr(security, "_chunk_cipher", FakeChunkCipher())
        monkeypatch.setattr(security, "ENVIRONMENT", "development")
        
        plaintext = "Sensitive document content"
        encrypted = security.encrypt_text(plaintext)
        
        assert encrypted != plaintext
        assert encrypted.startswith("gAAAAA")
    
    def test_encrypt_text_tracks_success_metric(self, monkeypatch):
        import core.security as security
        
        mock_metric = MagicMock()
        monkeypatch.setattr(security, "encryption_operations", mock_metric)
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)
        monkeypatch.setattr(security, "_chunk_cipher", FakeChunkCipher())
        monkeypatch.setattr(security, "ENVIRONMENT", "development")
        
        security.encrypt_text("test content")
        
        mock_metric.labels.assert_called_with(operation="encrypt", result="success")
        mock_metric.labels().inc.assert_called()
    
    def test_encrypt_text_returns_plaintext_when_disabled(self, monkeypatch):
        import core.security as security
        
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", False)
        monkeypatch.setattr(security, "_chunk_cipher", None)
        monkeypatch.setattr(security, "ENVIRONMENT", "development")
        
        plaintext = "test content"
        result = security.encrypt_text(plaintext)
        
        assert result == plaintext
    
    def test_encrypt_text_raises_in_production_without_key(self, monkeypatch):
        import core.security as security
        
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", False)
        monkeypatch.setattr(security, "_chunk_cipher", None)
        monkeypatch.setattr(security, "ENVIRONMENT", "production")
        
        with pytest.raises(security.EncryptionError) as exc:
            security.encrypt_text("test content")
        
        assert "CHUNK_ENCRYPTION_KEY not configured" in str(exc.value)
    
    def test_encrypt_text_handles_encryption_failure(self, monkeypatch):
        import core.security as security
        
        mock_metric = MagicMock()
        monkeypatch.setattr(security, "encryption_operations", mock_metric)
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)
        monkeypatch.setattr(security, "_chunk_cipher", FakeChunkCipher(explode=True))
        monkeypatch.setattr(security, "ENVIRONMENT", "development")
        
        with pytest.raises(security.EncryptionError) as exc:
            security.encrypt_text("test content")
        
        assert "Content encryption failed" in str(exc.value)
        mock_metric.labels.assert_called_with(operation="encrypt", result="failure")
    
    def test_encrypt_text_handles_unicode_content(self, monkeypatch):
        import core.security as security
        
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)
        monkeypatch.setattr(security, "_chunk_cipher", FakeChunkCipher())
        monkeypatch.setattr(security, "ENVIRONMENT", "development")
        
        unicode_text = "Hello 世界 🌍 Привет"
        encrypted = security.encrypt_text(unicode_text)
        
        assert encrypted != unicode_text
        assert encrypted.startswith("gAAAAA")


# =============================================================================
# Ghost Protocol: decrypt_text Tests
# =============================================================================

class TestDecryptText:
    """Tests for Ghost Protocol decrypt_text function."""
    
    def test_decrypt_text_returns_empty_for_empty_input(self):
        from core.security import decrypt_text
        assert decrypt_text("") == ""
        assert decrypt_text(None) is None
    
    def test_decrypt_text_recovers_plaintext(self, monkeypatch):
        import core.security as security
        
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)
        monkeypatch.setattr(security, "_chunk_cipher", FakeChunkCipher())
        monkeypatch.setattr(security, "_chunk_ciphers", [FakeChunkCipher()])
        monkeypatch.setattr(security, "ENVIRONMENT", "development")
        
        original = "Sensitive content"
        encrypted = security.encrypt_text(original)
        decrypted = security.decrypt_text(encrypted)
        
        assert decrypted == original
    
    def test_decrypt_text_tracks_success_metric(self, monkeypatch):
        import core.security as security
        
        mock_metric = MagicMock()
        monkeypatch.setattr(security, "encryption_operations", mock_metric)
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)
        monkeypatch.setattr(security, "_chunk_ciphers", [FakeChunkCipher(decrypt_value="test")])
        monkeypatch.setattr(security, "ENVIRONMENT", "development")
        
        security.decrypt_text("gAAAAAdGVzdA==")
        
        mock_metric.labels.assert_called_with(operation="decrypt", result="success")
    
    def test_decrypt_text_returns_plaintext_when_disabled(self, monkeypatch):
        import core.security as security
        
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", False)
        monkeypatch.setattr(security, "_chunk_ciphers", [])
        monkeypatch.setattr(security, "ENVIRONMENT", "development")
        
        token = "some-plaintext"
        result = security.decrypt_text(token)
        
        assert result == token
    
    def test_decrypt_text_raises_in_production_without_key(self, monkeypatch):
        import core.security as security
        
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", False)
        monkeypatch.setattr(security, "_chunk_ciphers", [])
        monkeypatch.setattr(security, "ENVIRONMENT", "production")
        
        with pytest.raises(security.EncryptionError) as exc:
            security.decrypt_text("gAAAAAsomething")
        
        assert "CHUNK_ENCRYPTION_KEY not configured" in str(exc.value)
    
    def test_decrypt_text_tries_multiple_keys(self, monkeypatch):
        import core.security as security
        
        # First cipher fails, second succeeds
        ciphers = [
            FakeChunkCipher(invalid=True),
            FakeChunkCipher(decrypt_value="decrypted content")
        ]
        
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)
        monkeypatch.setattr(security, "_chunk_ciphers", ciphers)
        monkeypatch.setattr(security, "ENVIRONMENT", "development")
        
        result = security.decrypt_text("gAAAAAsomething")
        
        assert result == "decrypted content"
    
    def test_decrypt_text_strict_mode_rejects_unencrypted(self, monkeypatch):
        import core.security as security
        
        mock_metric = MagicMock()
        mock_settings = MagicMock()
        mock_settings.STRICT_ENCRYPTION_MODE = True
        
        monkeypatch.setattr(security, "encryption_operations", mock_metric)
        monkeypatch.setattr(security, "settings", mock_settings)
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)
        monkeypatch.setattr(security, "_chunk_ciphers", [FakeChunkCipher(invalid=True)])
        monkeypatch.setattr(security, "ENVIRONMENT", "development")
        
        with pytest.raises(security.UnencryptedContentError) as exc:
            security.decrypt_text("plaintext-content")
        
        assert "Ghost Protocol requires all content to be encrypted" in str(exc.value)
        mock_metric.labels.assert_called_with(operation="decrypt", result="unencrypted_strict")
    
    def test_decrypt_text_legacy_mode_returns_plaintext(self, monkeypatch):
        import core.security as security
        
        mock_metric = MagicMock()
        mock_settings = MagicMock()
        mock_settings.STRICT_ENCRYPTION_MODE = False
        
        monkeypatch.setattr(security, "encryption_operations", mock_metric)
        monkeypatch.setattr(security, "settings", mock_settings)
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)
        monkeypatch.setattr(security, "_chunk_ciphers", [FakeChunkCipher(invalid=True)])
        monkeypatch.setattr(security, "ENVIRONMENT", "development")
        
        plaintext = "legacy-plaintext"
        result = security.decrypt_text(plaintext)
        
        assert result == plaintext
        mock_metric.labels.assert_called_with(operation="decrypt", result="unencrypted_legacy")
    
    def test_decrypt_text_handles_decryption_failure(self, monkeypatch):
        import core.security as security
        
        # Create a cipher that raises a non-InvalidToken exception
        class ExplodingCipher:
            def decrypt(self, data: bytes) -> bytes:
                raise ValueError("decrypt boom")
        
        mock_metric = MagicMock()
        monkeypatch.setattr(security, "encryption_operations", mock_metric)
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)
        monkeypatch.setattr(security, "_chunk_ciphers", [ExplodingCipher()])
        monkeypatch.setattr(security, "ENVIRONMENT", "development")
        # Need to also patch InvalidToken so it doesn't accidentally match
        monkeypatch.setattr(security, "InvalidToken", type("InvalidToken", (Exception,), {}))
        
        with pytest.raises(security.EncryptionError) as exc:
            security.decrypt_text("gAAAAAsomething")
        
        assert "Content decryption failed" in str(exc.value)
        mock_metric.labels.assert_called_with(operation="decrypt", result="failure")


# =============================================================================
# Key Rotation Utilities Tests
# =============================================================================

class TestKeyRotationUtilities:
    """Tests for encryption key rotation utilities."""
    
    def test_get_encryption_key_count_returns_zero_when_disabled(self, monkeypatch):
        import core.security as security
        
        monkeypatch.setattr(security, "_chunk_ciphers", [])
        
        assert security.get_encryption_key_count() == 0
    
    def test_get_encryption_key_count_returns_correct_count(self, monkeypatch):
        import core.security as security
        
        monkeypatch.setattr(security, "_chunk_ciphers", [
            FakeChunkCipher(),
            FakeChunkCipher(),
            FakeChunkCipher()
        ])
        
        assert security.get_encryption_key_count() == 3
    
    def test_generate_new_encryption_key_returns_valid_key(self, monkeypatch):
        import core.security as security
        
        monkeypatch.setattr(security, "_CRYPTO_AVAILABLE", True)
        
        # Need to mock Fernet for this test
        mock_key = b"mocked-key-base64-encoded====="
        mock_fernet_class = MagicMock()
        mock_fernet_class.generate_key.return_value = mock_key
        
        monkeypatch.setattr(security, "Fernet", mock_fernet_class)
        
        key = security.generate_new_encryption_key()
        
        assert key == mock_key.decode()
        mock_fernet_class.generate_key.assert_called_once()
    
    def test_generate_new_encryption_key_raises_without_crypto(self, monkeypatch):
        import core.security as security
        
        monkeypatch.setattr(security, "_CRYPTO_AVAILABLE", False)
        
        with pytest.raises(RuntimeError) as exc:
            security.generate_new_encryption_key()
        
        assert "cryptography package not installed" in str(exc.value)
    
    def test_re_encrypt_content_uses_primary_key(self, monkeypatch):
        import core.security as security
        
        # Set up ciphers - old key can decrypt, new key encrypts
        old_cipher = FakeChunkCipher(decrypt_value="plaintext content")
        new_cipher = FakeChunkCipher()
        
        monkeypatch.setattr(security, "HAS_CHUNK_ENCRYPTION", True)
        monkeypatch.setattr(security, "_chunk_cipher", new_cipher)  # Primary for encrypt
        monkeypatch.setattr(security, "_chunk_ciphers", [old_cipher])  # Old for decrypt
        monkeypatch.setattr(security, "ENVIRONMENT", "development")
        
        old_encrypted = "old-encrypted-content"
        new_encrypted = security.re_encrypt_content(old_encrypted)
        
        # Should be re-encrypted with new cipher (starts with gAAAAA)
        assert new_encrypted.startswith("gAAAAA")


# =============================================================================
# Exception Classes Tests
# =============================================================================

class TestExceptionClasses:
    """Tests for custom exception classes."""
    
    def test_encryption_error_is_exception(self):
        from core.security import EncryptionError
        
        error = EncryptionError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"
    
    def test_unencrypted_content_error_is_exception(self):
        from core.security import UnencryptedContentError
        
        error = UnencryptedContentError("content not encrypted")
        assert isinstance(error, Exception)
        assert str(error) == "content not encrypted"


# =============================================================================
# Module Initialization Tests
# =============================================================================

class TestModuleInitialization:
    """Tests for module-level initialization."""
    
    def test_chunk_encryption_disabled_without_key(self, monkeypatch):
        import core.security as security
        
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.delenv("CHUNK_ENCRYPTION_KEY", raising=False)
        
        security_reloaded = importlib.reload(security)
        
        # In dev without key, should be disabled
        assert security_reloaded.HAS_CHUNK_ENCRYPTION is False or security_reloaded._chunk_cipher is None
    
    def test_multiple_chunk_keys_supported(self, monkeypatch):
        import core.security as security
        
        try:
            from cryptography.fernet import Fernet
            key1 = Fernet.generate_key().decode()
            key2 = Fernet.generate_key().decode()
            
            monkeypatch.setenv("ENVIRONMENT", "test")
            monkeypatch.setenv("CHUNK_ENCRYPTION_KEY", f"{key1},{key2}")
            monkeypatch.setenv("ENCRYPTION_KEY", key1)
            
            security_reloaded = importlib.reload(security)
            
            assert security_reloaded.HAS_CHUNK_ENCRYPTION is True
            assert len(security_reloaded._chunk_ciphers) == 2
        finally:
            # Restore original state
            monkeypatch.delenv("CHUNK_ENCRYPTION_KEY", raising=False)
            importlib.reload(security)
    
    def test_whitespace_in_keys_is_stripped(self, monkeypatch):
        import core.security as security
        
        try:
            from cryptography.fernet import Fernet
            key = Fernet.generate_key().decode()
            
            monkeypatch.setenv("ENVIRONMENT", "test")
            monkeypatch.setenv("CHUNK_ENCRYPTION_KEY", f"  {key}  ,  ")
            monkeypatch.setenv("ENCRYPTION_KEY", key)
            
            security_reloaded = importlib.reload(security)
            
            # Should only have 1 key (whitespace-only entries filtered)
            assert len(security_reloaded._chunk_ciphers) == 1
        finally:
            monkeypatch.delenv("CHUNK_ENCRYPTION_KEY", raising=False)
            importlib.reload(security)


# =============================================================================
# Metrics Integration Tests
# =============================================================================

class TestMetricsIntegration:
    """Tests for metrics integration."""
    
    def test_dummy_metric_does_not_raise(self):
        """Test that the dummy metric class works when metrics are unavailable."""
        import core.security as security
        
        # If metrics aren't available, should use dummy that doesn't raise
        try:
            security.encryption_operations.labels(operation="test", result="test").inc()
        except Exception as e:
            pytest.fail(f"Dummy metric raised exception: {e}")
