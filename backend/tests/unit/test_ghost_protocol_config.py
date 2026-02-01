"""
Test Suite for Ghost Protocol Configuration

Tests for Zero-Retention security settings in config.py including:
- CHUNK_ENCRYPTION_KEY configuration
- MAX_RAM_PROCESS_LIMIT settings
- SECURE_WIPE_PASSES configuration
- STRICT_ENCRYPTION_MODE settings
"""

import importlib
import os
import sys

import pytest


def _reload_config(monkeypatch, **env):
    """Helper to reload config module with specific environment variables."""
    for key, value in env.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, str(value))
    import core.config as config
    return importlib.reload(config)


class TestGhostProtocolConfigDefaults:
    """Tests for Ghost Protocol default configuration values."""

    def test_chunk_encryption_key_can_be_configured(self, monkeypatch):
        """CHUNK_ENCRYPTION_KEY can be configured via environment."""
        # Note: In production .env files, CHUNK_ENCRYPTION_KEY may already be set.
        # This test verifies it can be configured, not that it defaults to None.
        test_key = "TestEncryptionKey123456789012345="  # 32 bytes base64
        config = _reload_config(
            monkeypatch,
            SENTRY_DSN="",
            ENVIRONMENT="test",
            CHUNK_ENCRYPTION_KEY=test_key,
        )
        assert config.settings.CHUNK_ENCRYPTION_KEY == test_key

    def test_max_ram_process_limit_default_is_10mb(self, monkeypatch):
        """MAX_RAM_PROCESS_LIMIT should default to 10MB."""
        config = _reload_config(
            monkeypatch,
            SENTRY_DSN="",
            ENVIRONMENT="test",
        )
        assert config.settings.MAX_RAM_PROCESS_LIMIT == 10 * 1024 * 1024

    def test_secure_wipe_passes_default_is_one(self, monkeypatch):
        """SECURE_WIPE_PASSES should default to 1 (fast mode)."""
        config = _reload_config(
            monkeypatch,
            SENTRY_DSN="",
            ENVIRONMENT="test",
        )
        assert config.settings.SECURE_WIPE_PASSES == 1

    def test_strict_encryption_mode_default_is_true(self, monkeypatch):
        """STRICT_ENCRYPTION_MODE should default to True (fail on unencrypted)."""
        config = _reload_config(
            monkeypatch,
            SENTRY_DSN="",
            ENVIRONMENT="test",
        )
        assert config.settings.STRICT_ENCRYPTION_MODE is True


class TestGhostProtocolConfigCustomValues:
    """Tests for Ghost Protocol custom configuration values."""

    def test_chunk_encryption_key_can_be_set(self, monkeypatch):
        """CHUNK_ENCRYPTION_KEY can be set via environment variable."""
        test_key = "YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY="
        config = _reload_config(
            monkeypatch,
            SENTRY_DSN="",
            ENVIRONMENT="test",
            CHUNK_ENCRYPTION_KEY=test_key,
        )
        assert config.settings.CHUNK_ENCRYPTION_KEY == test_key

    def test_max_ram_process_limit_can_be_customized(self, monkeypatch):
        """MAX_RAM_PROCESS_LIMIT can be set to custom value."""
        custom_limit = 5 * 1024 * 1024  # 5MB
        config = _reload_config(
            monkeypatch,
            SENTRY_DSN="",
            ENVIRONMENT="test",
            MAX_RAM_PROCESS_LIMIT=str(custom_limit),
        )
        assert config.settings.MAX_RAM_PROCESS_LIMIT == custom_limit

    def test_secure_wipe_passes_can_be_set_to_dod_mode(self, monkeypatch):
        """SECURE_WIPE_PASSES can be set to 3 (DoD compliant)."""
        config = _reload_config(
            monkeypatch,
            SENTRY_DSN="",
            ENVIRONMENT="test",
            SECURE_WIPE_PASSES="3",
        )
        assert config.settings.SECURE_WIPE_PASSES == 3

    def test_strict_encryption_mode_can_be_disabled(self, monkeypatch):
        """STRICT_ENCRYPTION_MODE can be disabled for legacy migrations."""
        config = _reload_config(
            monkeypatch,
            SENTRY_DSN="",
            ENVIRONMENT="test",
            STRICT_ENCRYPTION_MODE="false",
        )
        assert config.settings.STRICT_ENCRYPTION_MODE is False


class TestGhostProtocolConfigTypes:
    """Tests for Ghost Protocol configuration type validation."""

    def test_max_ram_process_limit_is_integer(self, monkeypatch):
        """MAX_RAM_PROCESS_LIMIT should be an integer."""
        config = _reload_config(
            monkeypatch,
            SENTRY_DSN="",
            ENVIRONMENT="test",
        )
        assert isinstance(config.settings.MAX_RAM_PROCESS_LIMIT, int)

    def test_secure_wipe_passes_is_integer(self, monkeypatch):
        """SECURE_WIPE_PASSES should be an integer."""
        config = _reload_config(
            monkeypatch,
            SENTRY_DSN="",
            ENVIRONMENT="test",
        )
        assert isinstance(config.settings.SECURE_WIPE_PASSES, int)

    def test_strict_encryption_mode_is_boolean(self, monkeypatch):
        """STRICT_ENCRYPTION_MODE should be a boolean."""
        config = _reload_config(
            monkeypatch,
            SENTRY_DSN="",
            ENVIRONMENT="test",
        )
        assert isinstance(config.settings.STRICT_ENCRYPTION_MODE, bool)


class TestGhostProtocolConfigEdgeCases:
    """Tests for Ghost Protocol configuration edge cases."""

    def test_max_ram_process_limit_zero_forces_disk_mode(self, monkeypatch):
        """Setting MAX_RAM_PROCESS_LIMIT to 0 should be valid (forces disk mode)."""
        config = _reload_config(
            monkeypatch,
            SENTRY_DSN="",
            ENVIRONMENT="test",
            MAX_RAM_PROCESS_LIMIT="0",
        )
        assert config.settings.MAX_RAM_PROCESS_LIMIT == 0

    def test_secure_wipe_passes_minimum_is_one(self, monkeypatch):
        """SECURE_WIPE_PASSES of 1 should be valid (minimum secure)."""
        config = _reload_config(
            monkeypatch,
            SENTRY_DSN="",
            ENVIRONMENT="test",
            SECURE_WIPE_PASSES="1",
        )
        assert config.settings.SECURE_WIPE_PASSES == 1

    def test_large_max_ram_process_limit(self, monkeypatch):
        """Large MAX_RAM_PROCESS_LIMIT values should be valid."""
        large_limit = 100 * 1024 * 1024  # 100MB
        config = _reload_config(
            monkeypatch,
            SENTRY_DSN="",
            ENVIRONMENT="test",
            MAX_RAM_PROCESS_LIMIT=str(large_limit),
        )
        assert config.settings.MAX_RAM_PROCESS_LIMIT == large_limit
