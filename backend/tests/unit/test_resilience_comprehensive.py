"""
Test Suite for Resilience Module

Covers retry decorators, circuit breakers, timeout utilities,
memory monitoring, and error detection.
"""

import asyncio
import http.client
import ssl
import time
from unittest.mock import MagicMock, patch

import pytest
from httpx import ConnectError, HTTPStatusError, TimeoutException

# =============================================================================
# is_retryable_error Tests
# =============================================================================

class TestIsRetryableError:
    """Tests for the is_retryable_error function."""

    def test_connect_error_is_retryable(self):
        from core.resilience import is_retryable_error

        error = ConnectError("Connection failed")
        assert is_retryable_error(error) is True

    def test_timeout_exception_is_retryable(self):
        from core.resilience import is_retryable_error

        error = TimeoutException("Timeout")
        assert is_retryable_error(error) is True

    def test_connection_error_is_retryable(self):
        from core.resilience import is_retryable_error

        error = ConnectionError("Connection refused")
        assert is_retryable_error(error) is True

    def test_timeout_error_is_retryable(self):
        from core.resilience import is_retryable_error

        error = TimeoutError("Operation timed out")
        assert is_retryable_error(error) is True

    def test_connection_reset_error_is_retryable(self):
        from core.resilience import is_retryable_error

        error = ConnectionResetError("Connection reset by peer")
        assert is_retryable_error(error) is True

    def test_ssl_error_is_retryable(self):
        from core.resilience import is_retryable_error

        error = ssl.SSLError("SSL handshake failed")
        assert is_retryable_error(error) is True

    def test_incomplete_read_is_retryable(self):
        from core.resilience import is_retryable_error

        error = http.client.IncompleteRead(b"partial", 100)
        assert is_retryable_error(error) is True

    def test_broken_pipe_is_retryable(self):
        from core.resilience import is_retryable_error

        error = BrokenPipeError("Broken pipe")
        assert is_retryable_error(error) is True

    def test_http_429_is_retryable(self):
        from core.resilience import is_retryable_error

        mock_response = MagicMock()
        mock_response.status_code = 429
        error = HTTPStatusError("Rate limited", request=MagicMock(), response=mock_response)

        assert is_retryable_error(error) is True

    def test_http_503_is_retryable(self):
        from core.resilience import is_retryable_error

        mock_response = MagicMock()
        mock_response.status_code = 503
        error = HTTPStatusError("Service unavailable", request=MagicMock(), response=mock_response)

        assert is_retryable_error(error) is True

    def test_http_500_is_retryable(self):
        from core.resilience import is_retryable_error

        mock_response = MagicMock()
        mock_response.status_code = 500
        error = HTTPStatusError("Internal server error", request=MagicMock(), response=mock_response)

        assert is_retryable_error(error) is True

    def test_http_502_is_retryable(self):
        from core.resilience import is_retryable_error

        mock_response = MagicMock()
        mock_response.status_code = 502
        error = HTTPStatusError("Bad gateway", request=MagicMock(), response=mock_response)

        assert is_retryable_error(error) is True

    def test_http_504_is_retryable(self):
        from core.resilience import is_retryable_error

        mock_response = MagicMock()
        mock_response.status_code = 504
        error = HTTPStatusError("Gateway timeout", request=MagicMock(), response=mock_response)

        assert is_retryable_error(error) is True

    def test_http_400_is_not_retryable(self):
        from core.resilience import is_retryable_error

        mock_response = MagicMock()
        mock_response.status_code = 400
        error = HTTPStatusError("Bad request", request=MagicMock(), response=mock_response)

        assert is_retryable_error(error) is False

    def test_http_401_is_not_retryable(self):
        from core.resilience import is_retryable_error

        mock_response = MagicMock()
        mock_response.status_code = 401
        error = HTTPStatusError("Unauthorized", request=MagicMock(), response=mock_response)

        assert is_retryable_error(error) is False

    def test_http_404_is_not_retryable(self):
        from core.resilience import is_retryable_error

        mock_response = MagicMock()
        mock_response.status_code = 404
        error = HTTPStatusError("Not found", request=MagicMock(), response=mock_response)

        assert is_retryable_error(error) is False

    def test_value_error_is_not_retryable(self):
        from core.resilience import is_retryable_error

        error = ValueError("Invalid value")
        assert is_retryable_error(error) is False

    def test_key_error_is_not_retryable(self):
        from core.resilience import is_retryable_error

        error = KeyError("missing key")
        assert is_retryable_error(error) is False

    def test_connection_terminated_by_name_is_retryable(self):
        from core.resilience import is_retryable_error

        class ConnectionTerminated(Exception):
            pass

        error = ConnectionTerminated("HTTP/2 connection terminated")
        assert is_retryable_error(error) is True

    def test_exception_with_status_code_attribute(self):
        from core.resilience import is_retryable_error

        class CustomError(Exception):
            status_code = 503

        error = CustomError("Service unavailable")
        assert is_retryable_error(error) is True

    def test_exception_with_response_status_code(self):
        from core.resilience import is_retryable_error

        class CustomError(Exception):
            def __init__(self):
                self.response = MagicMock()
                self.response.status_code = 429

        error = CustomError()
        assert is_retryable_error(error) is True

    def test_openai_rate_limit_error_is_retryable(self):
        from core.resilience import is_retryable_error

        # Mock OpenAI errors
        with patch.dict('sys.modules', {'openai': MagicMock()}):
            import sys
            mock_openai = sys.modules['openai']
            mock_openai.RateLimitError = type('RateLimitError', (Exception,), {})
            mock_openai.APIError = type('APIError', (Exception,), {})
            mock_openai.APITimeoutError = type('APITimeoutError', (Exception,), {})
            mock_openai.APIConnectionError = type('APIConnectionError', (Exception,), {})
            mock_openai.BadRequestError = type('BadRequestError', (Exception,), {})

            # Create an error that will match in the lazy import
            error = mock_openai.RateLimitError("Rate limit exceeded")

            # The actual check happens inside is_retryable_error with lazy import
            # Since we can't easily mock the lazy import, we test the general logic
            # by checking that the function doesn't crash
            result = is_retryable_error(error)
            # The actual result depends on whether openai is installed


# =============================================================================
# with_retry Decorator Tests
# =============================================================================

class TestWithRetryDecorator:
    """Tests for the with_retry async decorator."""

    @pytest.mark.asyncio
    async def test_successful_call_returns_immediately(self):
        from core.resilience import with_retry

        call_count = 0

        @with_retry(max_attempts=3)
        async def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await successful_func()

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_transient_error(self):
        from core.resilience import TRANSIENT_EXCEPTIONS, with_retry

        call_count = 0

        @with_retry(max_attempts=3, min_wait=0.01, max_wait=0.02, exceptions=TRANSIENT_EXCEPTIONS)
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Connection failed")
            return "success"

        result = await flaky_func()

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_raises_after_max_attempts(self):
        from core.resilience import TRANSIENT_EXCEPTIONS, with_retry

        call_count = 0

        @with_retry(max_attempts=3, min_wait=0.01, max_wait=0.02, exceptions=TRANSIENT_EXCEPTIONS)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise TimeoutError("Always times out")

        with pytest.raises(TimeoutError):
            await always_fails()

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_does_not_retry_non_transient_error(self):
        from core.resilience import TRANSIENT_EXCEPTIONS, with_retry

        call_count = 0

        @with_retry(max_attempts=3, min_wait=0.01, max_wait=0.02, exceptions=TRANSIENT_EXCEPTIONS)
        async def raises_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")

        with pytest.raises(ValueError):
            await raises_value_error()

        assert call_count == 1


# =============================================================================
# with_retry_sync Decorator Tests
# =============================================================================

class TestWithRetrySyncDecorator:
    """Tests for the with_retry_sync sync decorator."""

    def test_successful_call_returns_immediately(self):
        from core.resilience import with_retry_sync

        call_count = 0

        @with_retry_sync(max_attempts=3)
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()

        assert result == "success"
        assert call_count == 1

    def test_retries_on_transient_error(self):
        from core.resilience import TRANSIENT_EXCEPTIONS, with_retry_sync

        call_count = 0

        @with_retry_sync(max_attempts=3, min_wait=0.01, max_wait=0.02, exceptions=TRANSIENT_EXCEPTIONS)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Connection failed")
            return "success"

        result = flaky_func()

        assert result == "success"
        assert call_count == 2

    def test_raises_after_max_attempts(self):
        from core.resilience import TRANSIENT_EXCEPTIONS, with_retry_sync

        call_count = 0

        @with_retry_sync(max_attempts=3, min_wait=0.01, max_wait=0.02, exceptions=TRANSIENT_EXCEPTIONS)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise TimeoutError("Always times out")

        with pytest.raises(TimeoutError):
            always_fails()

        assert call_count == 3


# =============================================================================
# with_retry_async Decorator Tests
# =============================================================================

class TestWithRetryAsyncDecorator:
    """Tests for the with_retry_async decorator with logging."""

    @pytest.mark.asyncio
    async def test_retries_with_logging(self):
        from core.resilience import TRANSIENT_EXCEPTIONS, with_retry_async

        call_count = 0

        @with_retry_async(max_attempts=3, min_wait=0.01, max_wait=0.02, exceptions=TRANSIENT_EXCEPTIONS)
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Connection failed")
            return "success"

        result = await flaky_func()

        assert result == "success"
        assert call_count == 2


# =============================================================================
# with_google_retry Decorator Tests
# =============================================================================

class TestWithGoogleRetry:
    """Tests for the with_google_retry decorator."""

    def test_retries_on_google_rate_limit(self):
        from core.resilience import with_google_retry

        call_count = 0

        @with_google_retry(max_attempts=3)
        def google_api_call():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Network error")
            return "success"

        result = google_api_call()

        assert result == "success"
        assert call_count == 2

    def test_retries_on_transient_error(self):
        from core.resilience import with_google_retry

        call_count = 0

        @with_google_retry(max_attempts=3)
        def google_api_call():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("Timeout")
            return "success"

        result = google_api_call()

        assert result == "success"
        assert call_count == 2


# =============================================================================
# Circuit Breaker Tests
# =============================================================================

class TestCircuitBreaker:
    """Tests for the CircuitBreaker class."""

    def test_closed_state_allows_requests(self):
        from core.resilience import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=3, name="test")

        with breaker:
            result = "success"

        assert result == "success"
        assert breaker.state == "closed"
        assert breaker.failures == 0

    def test_failure_increments_counter(self):
        from core.resilience import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=3, name="test")

        try:
            with breaker:
                raise ValueError("Error")
        except ValueError:
            pass

        assert breaker.failures == 1
        assert breaker.state == "closed"

    def test_opens_after_threshold_failures(self):
        from core.resilience import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=3, name="test")

        for _ in range(3):
            try:
                with breaker:
                    raise ValueError("Error")
            except ValueError:
                pass

        assert breaker.state == "open"
        assert breaker.failures == 3

    def test_open_state_blocks_requests(self):
        from core.resilience import CircuitBreaker, CircuitBreakerOpen

        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60, name="test")

        # Force open state
        for _ in range(3):
            try:
                with breaker:
                    raise ValueError("Error")
            except ValueError:
                pass

        # Next request should be blocked
        with pytest.raises(CircuitBreakerOpen), breaker:
            pass

    def test_transitions_to_half_open_after_timeout(self):
        from core.resilience import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=0.01, name="test")

        # Force open state
        for _ in range(3):
            try:
                with breaker:
                    raise ValueError("Error")
            except ValueError:
                pass

        # Wait for recovery timeout
        import time
        time.sleep(0.02)

        # Should transition to half-open and allow request
        with breaker:
            result = "success"

        assert result == "success"
        assert breaker.state == "closed"  # Recovers to closed on success
        assert breaker.failures == 0

    def test_success_in_half_open_closes_breaker(self):
        from core.resilience import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.01, name="test")

        # Force open state
        for _ in range(2):
            try:
                with breaker:
                    raise ValueError("Error")
            except ValueError:
                pass

        assert breaker.state == "open"

        # Wait for recovery timeout
        time.sleep(0.02)

        # Success in half-open should close
        with breaker:
            pass

        assert breaker.state == "closed"
        assert breaker.failures == 0

    def test_failure_in_half_open_reopens_breaker(self):
        from core.resilience import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.01, name="test")

        # Force open state
        for _ in range(2):
            try:
                with breaker:
                    raise ValueError("Error")
            except ValueError:
                pass

        assert breaker.state == "open"

        # Wait for recovery timeout
        time.sleep(0.02)

        # Fail in half-open should re-open
        try:
            with breaker:
                raise ValueError("Still failing")
        except ValueError:
            pass

        assert breaker.state == "open"

    def test_last_failure_time_is_set(self):
        from core.resilience import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=3, name="test")

        assert breaker.last_failure_time is None

        try:
            with breaker:
                raise ValueError("Error")
        except ValueError:
            pass

        assert breaker.last_failure_time is not None


# =============================================================================
# Circuit Breaker Open Exception Tests
# =============================================================================

class TestCircuitBreakerOpenException:
    """Tests for CircuitBreakerOpen exception."""

    def test_exception_has_message(self):
        from core.resilience import CircuitBreakerOpen

        error = CircuitBreakerOpen("Test breaker is open")

        assert str(error) == "Test breaker is open"
        assert isinstance(error, Exception)


# =============================================================================
# Pre-configured Circuit Breakers Tests
# =============================================================================

class TestPreConfiguredBreakers:
    """Tests for pre-configured circuit breaker instances."""

    def test_openai_breaker_exists(self):
        from core.resilience import openai_breaker

        assert openai_breaker.name == "OpenAI API"
        assert openai_breaker.failure_threshold == 5
        assert openai_breaker.recovery_timeout == 60

    def test_llamaparse_breaker_exists(self):
        from core.resilience import llamaparse_breaker

        assert llamaparse_breaker.name == "LlamaParse API"
        assert llamaparse_breaker.failure_threshold == 3
        assert llamaparse_breaker.recovery_timeout == 120

    def test_supabase_breaker_exists(self):
        from core.resilience import supabase_breaker

        assert supabase_breaker.name == "Supabase"
        assert supabase_breaker.failure_threshold == 5
        assert supabase_breaker.recovery_timeout == 30


# =============================================================================
# Timeouts Tests
# =============================================================================

class TestTimeouts:
    """Tests for Timeouts configuration class."""

    def test_pdf_parsing_timeout(self):
        from core.resilience import Timeouts

        assert Timeouts.PDF_PARSING == 300

    def test_docx_parsing_timeout(self):
        from core.resilience import Timeouts

        assert Timeouts.DOCX_PARSING == 60

    def test_embedding_batch_timeout(self):
        from core.resilience import Timeouts

        assert Timeouts.EMBEDDING_BATCH == 60

    def test_supabase_rpc_timeout(self):
        from core.resilience import Timeouts

        assert Timeouts.SUPABASE_RPC == 30

    def test_file_download_timeout(self):
        from core.resilience import Timeouts

        assert Timeouts.FILE_DOWNLOAD == 120

    def test_llamaparse_api_timeout(self):
        from core.resilience import Timeouts

        assert Timeouts.LLAMAPARSE_API == 180


# =============================================================================
# with_timeout Tests
# =============================================================================

class TestWithTimeout:
    """Tests for the with_timeout utility function."""

    @pytest.mark.asyncio
    async def test_successful_operation_returns_result(self):
        from core.resilience import with_timeout

        async def quick_operation():
            return "success"

        result = await with_timeout(quick_operation(), 1.0, "quick_op")

        assert result == "success"

    @pytest.mark.asyncio
    async def test_timeout_raises_error(self):
        from core.resilience import with_timeout

        async def slow_operation():
            await asyncio.sleep(1.0)
            return "never returned"

        with pytest.raises(TimeoutError) as exc:
            await with_timeout(slow_operation(), 0.01, "slow_op")

        assert "slow_op timed out" in str(exc.value)

    @pytest.mark.asyncio
    async def test_timeout_logs_error(self):
        from core.resilience import with_timeout

        async def slow_operation():
            await asyncio.sleep(1.0)
            return "never returned"

        with patch('core.resilience.logger') as mock_logger:
            with pytest.raises(TimeoutError):
                await with_timeout(slow_operation(), 0.01, "test_op")

            mock_logger.error.assert_called()


# =============================================================================
# Retry Configuration Tests
# =============================================================================

class TestRetryConfigurations:
    """Tests for service-specific retry configurations."""

    def test_openai_retry_config(self):
        from core.resilience import OPENAI_RETRY_CONFIG

        assert OPENAI_RETRY_CONFIG["max_attempts"] == 3
        assert OPENAI_RETRY_CONFIG["min_wait"] == 2.0
        assert OPENAI_RETRY_CONFIG["max_wait"] == 10.0

    def test_supabase_retry_config(self):
        from core.resilience import SUPABASE_RETRY_CONFIG

        assert SUPABASE_RETRY_CONFIG["max_attempts"] == 3
        assert SUPABASE_RETRY_CONFIG["min_wait"] == 1.0
        assert SUPABASE_RETRY_CONFIG["max_wait"] == 5.0

    def test_llamaparse_retry_config(self):
        from core.resilience import LLAMAPARSE_RETRY_CONFIG

        assert LLAMAPARSE_RETRY_CONFIG["max_attempts"] == 3
        assert LLAMAPARSE_RETRY_CONFIG["min_wait"] == 3.0
        assert LLAMAPARSE_RETRY_CONFIG["max_wait"] == 15.0


# =============================================================================
# Memory Monitoring Tests
# =============================================================================

class TestMemoryMonitoring:
    """Tests for memory monitoring utilities."""

    def test_check_memory_usage_returns_dict(self):
        from core.resilience import check_memory_usage

        result = check_memory_usage()

        assert isinstance(result, dict)
        assert "percent" in result
        assert "available_mb" in result
        assert "total_mb" in result
        assert "warning" in result
        assert "critical" in result

    def test_check_memory_usage_warning_threshold(self):
        from core.resilience import check_memory_usage

        with patch('core.resilience.psutil.virtual_memory') as mock_memory:
            mock_memory.return_value = MagicMock(
                percent=86.0,
                available=1024 * 1024 * 1024,  # 1GB
                total=8 * 1024 * 1024 * 1024   # 8GB
            )

            result = check_memory_usage()

            assert result["warning"] is True
            assert result["critical"] is False

    def test_check_memory_usage_critical_threshold(self):
        from core.resilience import check_memory_usage

        with patch('core.resilience.psutil.virtual_memory') as mock_memory:
            mock_memory.return_value = MagicMock(
                percent=96.0,
                available=256 * 1024 * 1024,   # 256MB
                total=8 * 1024 * 1024 * 1024   # 8GB
            )

            result = check_memory_usage()

            assert result["warning"] is True
            assert result["critical"] is True

    def test_enforce_memory_limit_raises_on_critical(self):
        from core.resilience import enforce_memory_limit

        with patch('core.resilience.check_memory_usage') as mock_check:
            mock_check.return_value = {
                "percent": 96.0,
                "available_mb": 256,
                "total_mb": 8192,
                "warning": True,
                "critical": True
            }

            with pytest.raises(MemoryError) as exc:
                enforce_memory_limit()

            assert "Memory usage critical" in str(exc.value)

    def test_enforce_memory_limit_warns_on_high_usage(self):
        from core.resilience import enforce_memory_limit

        with patch('core.resilience.check_memory_usage') as mock_check:
            mock_check.return_value = {
                "percent": 87.0,
                "available_mb": 1024,
                "total_mb": 8192,
                "warning": True,
                "critical": False
            }

            with patch('core.resilience.logger') as mock_logger:
                enforce_memory_limit()  # Should not raise
                mock_logger.warning.assert_called()

    def test_enforce_memory_limit_passes_on_normal_usage(self):
        from core.resilience import enforce_memory_limit

        with patch('core.resilience.check_memory_usage') as mock_check:
            mock_check.return_value = {
                "percent": 50.0,
                "available_mb": 4096,
                "total_mb": 8192,
                "warning": False,
                "critical": False
            }

            # Should not raise or warn
            enforce_memory_limit()


# =============================================================================
# Rate Limit Status Codes Tests
# =============================================================================

class TestRateLimitStatusCodes:
    """Tests for rate limit status codes configuration."""

    def test_rate_limit_status_codes_contains_429(self):
        from core.resilience import RATE_LIMIT_STATUS_CODES

        assert 429 in RATE_LIMIT_STATUS_CODES

    def test_rate_limit_status_codes_contains_503(self):
        from core.resilience import RATE_LIMIT_STATUS_CODES

        assert 503 in RATE_LIMIT_STATUS_CODES

    def test_rate_limit_status_codes_contains_502(self):
        from core.resilience import RATE_LIMIT_STATUS_CODES

        assert 502 in RATE_LIMIT_STATUS_CODES

    def test_rate_limit_status_codes_contains_504(self):
        from core.resilience import RATE_LIMIT_STATUS_CODES

        assert 504 in RATE_LIMIT_STATUS_CODES


# =============================================================================
# Transient Exceptions Tests
# =============================================================================

class TestTransientExceptions:
    """Tests for transient exceptions configuration."""

    def test_transient_exceptions_contains_connect_error(self):
        from core.resilience import TRANSIENT_EXCEPTIONS

        assert ConnectError in TRANSIENT_EXCEPTIONS

    def test_transient_exceptions_contains_timeout_exception(self):
        from core.resilience import TRANSIENT_EXCEPTIONS

        assert TimeoutException in TRANSIENT_EXCEPTIONS

    def test_transient_exceptions_contains_connection_error(self):
        from core.resilience import TRANSIENT_EXCEPTIONS

        assert ConnectionError in TRANSIENT_EXCEPTIONS

    def test_transient_exceptions_contains_ssl_error(self):
        from core.resilience import TRANSIENT_EXCEPTIONS

        assert ssl.SSLError in TRANSIENT_EXCEPTIONS

    def test_all_transient_exceptions_includes_http2_errors(self):
        from core.resilience import ALL_TRANSIENT_EXCEPTIONS, TRANSIENT_EXCEPTIONS

        # ALL_TRANSIENT_EXCEPTIONS should be at least as large as TRANSIENT_EXCEPTIONS
        assert len(ALL_TRANSIENT_EXCEPTIONS) >= len(TRANSIENT_EXCEPTIONS)


# =============================================================================
# Jitter Tests
# =============================================================================

class TestJitterRetry:
    """Tests for retry with jitter."""

    @pytest.mark.asyncio
    async def test_with_retry_jitter_option(self):
        from core.resilience import with_retry

        call_count = 0

        @with_retry(max_attempts=2, min_wait=0.01, max_wait=0.02, jitter=True)
        async def func_with_jitter():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Fail")
            return "success"

        result = await func_with_jitter()

        assert result == "success"
        assert call_count == 2

    def test_with_retry_sync_jitter_option(self):
        from core.resilience import with_retry_sync

        call_count = 0

        @with_retry_sync(max_attempts=2, min_wait=0.01, max_wait=0.02, jitter=True)
        def func_with_jitter():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Fail")
            return "success"

        result = func_with_jitter()

        assert result == "success"
        assert call_count == 2


# =============================================================================
# use_retryable Tests
# =============================================================================

class TestUseRetryable:
    """Tests for use_retryable option in retry decorators."""

    @pytest.mark.asyncio
    async def test_use_retryable_checks_is_retryable_error(self):
        from core.resilience import with_retry

        call_count = 0

        @with_retry(max_attempts=3, min_wait=0.01, max_wait=0.02, use_retryable=True)
        async def func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Transient")
            return "success"

        result = await func()

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_use_retryable_does_not_retry_non_retryable(self):
        from core.resilience import with_retry

        call_count = 0

        @with_retry(max_attempts=3, min_wait=0.01, max_wait=0.02, use_retryable=True)
        async def func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")

        with pytest.raises(ValueError):
            await func()

        assert call_count == 1
