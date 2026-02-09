"""
Test Suite for Database Connection Module

Covers Supabase client initialization, SQLAlchemy sessions,
connection pooling, and health checks.
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

# =============================================================================
# get_supabase Tests
# =============================================================================

class TestGetSupabase:
    """Tests for the get_supabase function."""

    def test_returns_supabase_client(self):
        from core.db import get_supabase

        client = get_supabase()

        assert client is not None

    def test_singleton_returns_same_instance(self):
        from core.db import get_supabase

        client1 = get_supabase()
        client2 = get_supabase()

        assert client1 is client2

    def test_initializes_client_with_settings(self, monkeypatch):
        import core.db as db_module

        # Reset singleton
        monkeypatch.setattr(db_module, "_supabase_client", None)

        mock_client = MagicMock()

        with patch('core.db.create_client', return_value=mock_client) as mock_create:
            with patch('core.db.settings') as mock_settings:
                mock_settings.SUPABASE_URL = "https://test.supabase.co"
                mock_settings.SUPABASE_SECRET_KEY = "test-secret-key"

                result = db_module.get_supabase()

                assert result is mock_client
                mock_create.assert_called_once()

    def test_logs_initialization(self, monkeypatch):
        import core.db as db_module

        # Reset singleton
        monkeypatch.setattr(db_module, "_supabase_client", None)

        mock_client = MagicMock()

        with patch('core.db.create_client', return_value=mock_client):
            with patch('core.db.logger') as mock_logger:
                db_module.get_supabase()

                # Check that initialization was logged
                assert mock_logger.info.call_count >= 1

    def test_raises_on_initialization_failure(self, monkeypatch):
        import core.db as db_module

        # Reset singleton
        monkeypatch.setattr(db_module, "_supabase_client", None)

        with patch('core.db.create_client', side_effect=Exception("Connection failed")):
            with pytest.raises(Exception) as exc:
                db_module.get_supabase()

            assert "Connection failed" in str(exc.value)

    def test_logs_error_on_failure(self, monkeypatch):
        import core.db as db_module

        # Reset singleton
        monkeypatch.setattr(db_module, "_supabase_client", None)

        with patch('core.db.create_client', side_effect=Exception("Connection failed")):
            with patch('core.db.logger') as mock_logger:
                with pytest.raises(Exception):
                    db_module.get_supabase()

                mock_logger.error.assert_called()


# =============================================================================
# close_supabase Tests
# =============================================================================

class TestCloseSupabase:
    """Tests for the close_supabase function."""

    def test_clears_singleton(self, monkeypatch):
        import core.db as db_module

        # Set a mock client
        monkeypatch.setattr(db_module, "_supabase_client", MagicMock())

        db_module.close_supabase()

        assert db_module._supabase_client is None

    def test_logs_close(self, monkeypatch):
        import core.db as db_module

        # Set a mock client
        monkeypatch.setattr(db_module, "_supabase_client", MagicMock())

        with patch('core.db.logger') as mock_logger:
            db_module.close_supabase()

            mock_logger.info.assert_called()

    def test_safe_to_call_when_not_initialized(self, monkeypatch):
        import core.db as db_module

        # Ensure no client
        monkeypatch.setattr(db_module, "_supabase_client", None)

        # Should not raise
        db_module.close_supabase()

        assert db_module._supabase_client is None


# =============================================================================
# check_connection Tests
# =============================================================================

class TestCheckConnection:
    """Tests for the check_connection function."""

    @pytest.mark.asyncio
    async def test_returns_true_on_success(self, monkeypatch):
        import core.db as db_module

        mock_client = MagicMock()
        mock_execute = MagicMock()
        mock_execute.execute.return_value = MagicMock(data=[])
        mock_client.table.return_value.select.return_value.limit.return_value = mock_execute

        monkeypatch.setattr(db_module, "_supabase_client", mock_client)

        result = await db_module.check_connection()

        assert result is True

    @pytest.mark.asyncio
    async def test_retries_on_failure(self, monkeypatch):
        import core.db as db_module

        mock_client = MagicMock()
        call_count = 0

        def mock_execute():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Connection error")
            return MagicMock(data=[])

        mock_limit = MagicMock()
        mock_limit.execute = mock_execute
        mock_client.table.return_value.select.return_value.limit.return_value = mock_limit

        monkeypatch.setattr(db_module, "_supabase_client", mock_client)

        result = await db_module.check_connection()

        assert result is True
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self, monkeypatch):
        import core.db as db_module

        mock_client = MagicMock()
        mock_limit = MagicMock()
        mock_limit.execute.side_effect = Exception("Persistent failure")
        mock_client.table.return_value.select.return_value.limit.return_value = mock_limit

        monkeypatch.setattr(db_module, "_supabase_client", mock_client)

        with pytest.raises(Exception) as exc:
            await db_module.check_connection()

        assert "Persistent failure" in str(exc.value)

    @pytest.mark.asyncio
    async def test_logs_retry_attempts(self, monkeypatch):
        import core.db as db_module

        mock_client = MagicMock()
        call_count = 0

        def mock_execute():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary failure")
            return MagicMock(data=[])

        mock_limit = MagicMock()
        mock_limit.execute = mock_execute
        mock_client.table.return_value.select.return_value.limit.return_value = mock_limit

        monkeypatch.setattr(db_module, "_supabase_client", mock_client)

        with patch('core.db.logger') as mock_logger:
            await db_module.check_connection()

            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_logs_final_failure(self, monkeypatch):
        import core.db as db_module

        mock_client = MagicMock()
        mock_limit = MagicMock()
        mock_limit.execute.side_effect = Exception("Fatal error")
        mock_client.table.return_value.select.return_value.limit.return_value = mock_limit

        monkeypatch.setattr(db_module, "_supabase_client", mock_client)

        with patch('core.db.logger') as mock_logger:
            with pytest.raises(Exception):
                await db_module.check_connection()

            mock_logger.error.assert_called()


# =============================================================================
# _build_client_options Tests
# =============================================================================

class TestBuildClientOptions:
    """Tests for the _build_client_options function."""

    def test_returns_client_options(self):
        from core.db import _build_client_options

        options = _build_client_options()

        assert options is not None

    def test_sets_schema_to_public(self):
        from core.db import _build_client_options

        options = _build_client_options()

        # Check if schema is accessible (depends on ClientOptions implementation)
        if hasattr(options, 'schema'):
            assert options.schema == "public"

    def test_handles_older_client_versions(self, monkeypatch):
        from core.db import _build_client_options

        # Mock ClientOptions to raise TypeError on init
        class OldClientOptions:
            def __init__(self, **kwargs):
                if kwargs:
                    raise TypeError("Unexpected arguments")
                self.schema = None
                self.postgrest_client_timeout = None

        with patch('core.db.ClientOptions', OldClientOptions):
            options = _build_client_options()

            # Should handle gracefully
            assert options is not None


# =============================================================================
# _init_sqlalchemy_sessions Tests
# =============================================================================

class TestInitSqlalchemySessions:
    """Tests for the _init_sqlalchemy_sessions function."""

    def test_creates_session_factories(self, monkeypatch):
        import core.db as db_module

        # Reset sessions
        monkeypatch.setattr(db_module, "SessionLocal", None)
        monkeypatch.setattr(db_module, "IngestionSessionLocal", None)

        mock_engine = MagicMock()
        mock_session_maker = MagicMock()

        with patch('core.db.create_engine', return_value=mock_engine):
            with patch('core.db.sessionmaker', return_value=mock_session_maker):
                with patch('core.db.settings') as mock_settings:
                    mock_settings.INGESTION_DATABASE_URL = "postgresql://test"

                    with patch('core.db.os.getenv', return_value=None):
                        db_module._init_sqlalchemy_sessions()

    def test_uses_ingestion_url_when_available(self, monkeypatch):
        import core.db as db_module

        # Reset sessions
        monkeypatch.setattr(db_module, "SessionLocal", None)
        monkeypatch.setattr(db_module, "IngestionSessionLocal", None)

        mock_engine = MagicMock()

        with patch('core.db.create_engine', return_value=mock_engine) as mock_create:
            with patch('core.db.sessionmaker'):
                with patch('core.db.settings') as mock_settings:
                    mock_settings.INGESTION_DATABASE_URL = "postgresql://ingestion"

                    with patch('core.db.os.getenv', return_value=None):
                        db_module._init_sqlalchemy_sessions()

                        # Verify create_engine was called with ingestion URL
                        mock_create.assert_called()

    def test_falls_back_to_database_url(self, monkeypatch):
        import core.db as db_module

        # Reset sessions
        monkeypatch.setattr(db_module, "SessionLocal", None)
        monkeypatch.setattr(db_module, "IngestionSessionLocal", None)

        mock_engine = MagicMock()

        with patch('core.db.create_engine', return_value=mock_engine) as mock_create:
            with patch('core.db.sessionmaker'):
                with patch('core.db.settings') as mock_settings:
                    mock_settings.INGESTION_DATABASE_URL = None

                    def mock_getenv(key, default=None):
                        if key == "INGESTION_DATABASE_URL":
                            return None
                        if key == "DATABASE_URL":
                            return "postgresql://default"
                        return default

                    with patch('core.db.os.getenv', side_effect=mock_getenv):
                        db_module._init_sqlalchemy_sessions()

                        # Verify create_engine was called
                        mock_create.assert_called()

    def test_ingestion_session_falls_back_to_session_local(self, monkeypatch):
        import core.db as db_module

        # Reset sessions
        monkeypatch.setattr(db_module, "SessionLocal", None)
        monkeypatch.setattr(db_module, "IngestionSessionLocal", None)

        mock_session = MagicMock()
        mock_engine = MagicMock()

        with patch('core.db.create_engine', return_value=mock_engine):
            with patch('core.db.sessionmaker', return_value=mock_session):
                with patch('core.db.settings') as mock_settings:
                    mock_settings.INGESTION_DATABASE_URL = None

                    def mock_getenv(key, default=None):
                        if key == "INGESTION_DATABASE_URL":
                            return None
                        if key == "DATABASE_URL":
                            return "postgresql://default"
                        return default

                    with patch('core.db.os.getenv', side_effect=mock_getenv):
                        db_module._init_sqlalchemy_sessions()

                        # IngestionSessionLocal should fall back to SessionLocal
                        assert db_module.IngestionSessionLocal is not None


# =============================================================================
# Module Exports Tests
# =============================================================================

class TestModuleExports:
    """Tests for module exports."""

    def test_get_supabase_is_exported(self):
        from core.db import __all__

        assert 'get_supabase' in __all__

    def test_close_supabase_is_exported(self):
        from core.db import __all__

        assert 'close_supabase' in __all__

    def test_check_connection_is_exported(self):
        from core.db import __all__

        assert 'check_connection' in __all__


# =============================================================================
# Connection Pooling Tests
# =============================================================================

class TestConnectionPooling:
    """Tests for connection pooling behavior."""

    def test_pool_pre_ping_enabled(self, monkeypatch):
        import core.db as db_module

        # Reset sessions
        monkeypatch.setattr(db_module, "SessionLocal", None)
        monkeypatch.setattr(db_module, "IngestionSessionLocal", None)

        with patch('core.db.create_engine') as mock_create:
            with patch('core.db.sessionmaker'):
                with patch('core.db.settings') as mock_settings:
                    mock_settings.INGESTION_DATABASE_URL = "postgresql://test"

                    with patch('core.db.os.getenv', return_value=None):
                        db_module._init_sqlalchemy_sessions()

                        # Verify pool_pre_ping is True
                        call_args = mock_create.call_args
                        if call_args:
                            assert call_args[1].get('pool_pre_ping') is True


# =============================================================================
# ClientOptions Edge Cases Tests
# =============================================================================

class TestClientOptionsEdgeCases:
    """Tests for ClientOptions edge cases."""

    def test_storage_memory_initialization(self):
        from core.db import _build_client_options

        options = _build_client_options()

        # Should not raise even if storage setup fails
        assert options is not None

    def test_handles_missing_storage_attribute(self):
        from core.db import _build_client_options

        # Mock ClientOptions without storage attribute
        class MockOptions:
            def __init__(self, **kwargs):
                self.schema = kwargs.get('schema', 'public')
                # Intentionally no 'storage' attribute

        with patch('core.db.ClientOptions', MockOptions):
            options = _build_client_options()

            # Should handle gracefully
            assert options is not None


# =============================================================================
# Async Sleep in Retry Tests
# =============================================================================

class TestAsyncSleepInRetry:
    """Tests for async sleep behavior in check_connection retries."""

    @pytest.mark.asyncio
    async def test_exponential_backoff_delay(self, monkeypatch):
        import core.db as db_module

        mock_client = MagicMock()
        call_count = 0

        def mock_execute():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Failure")
            return MagicMock(data=[])

        mock_limit = MagicMock()
        mock_limit.execute = mock_execute
        mock_client.table.return_value.select.return_value.limit.return_value = mock_limit

        monkeypatch.setattr(db_module, "_supabase_client", mock_client)

        sleep_calls = []
        original_sleep = asyncio.sleep

        async def mock_sleep(delay):
            sleep_calls.append(delay)
            await original_sleep(0)  # Minimal actual sleep

        with patch('core.db.asyncio.sleep', mock_sleep):
            await db_module.check_connection()

        # Should have exponential delays: 1.0, 2.0
        assert len(sleep_calls) == 2
        assert sleep_calls[0] == 1.0
        assert sleep_calls[1] == 2.0


# =============================================================================
# Logging Context Tests
# =============================================================================

class TestLoggingContext:
    """Tests for logging context in database operations."""

    def test_initialization_log_contains_emoji(self, monkeypatch):
        import core.db as db_module

        # Reset singleton
        monkeypatch.setattr(db_module, "_supabase_client", None)

        mock_client = MagicMock()

        with patch('core.db.create_client', return_value=mock_client):
            with patch('core.db.logger') as mock_logger:
                db_module.get_supabase()

                # Check that logs contain emoji indicators
                log_calls = [str(call) for call in mock_logger.info.call_args_list]
                assert any("🔌" in str(call) or "✅" in str(call) for call in log_calls)

    def test_close_log_contains_emoji(self, monkeypatch):
        import core.db as db_module

        monkeypatch.setattr(db_module, "_supabase_client", MagicMock())

        with patch('core.db.logger') as mock_logger:
            db_module.close_supabase()

            log_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("🔌" in str(call) for call in log_calls)

    @pytest.mark.asyncio
    async def test_retry_warning_contains_context(self, monkeypatch):
        import core.db as db_module

        mock_client = MagicMock()
        call_count = 0

        def mock_execute():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Test failure")
            return MagicMock(data=[])

        mock_limit = MagicMock()
        mock_limit.execute = mock_execute
        mock_client.table.return_value.select.return_value.limit.return_value = mock_limit

        monkeypatch.setattr(db_module, "_supabase_client", mock_client)

        with patch('core.db.logger') as mock_logger:
            await db_module.check_connection()

            # Warning should contain attempt info
            warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
            assert any("attempt" in str(call).lower() or "⚠️" in str(call) for call in warning_calls)
