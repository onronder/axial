"""
Unit Tests for Error Resilience Module

Tests retry decorators and circuit breaker functionality.
"""

import asyncio
import builtins
import types
import importlib
import pytest
import httpx
from unittest.mock import Mock, patch
import sys
import os

# Set environment variables BEFORE importing modules that use settings
os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("ENVIRONMENT", "test")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.resilience import (
    with_retry,
    with_retry_async,
    with_google_retry,
    with_timeout,
    with_retry_sync,
    is_retryable_error,
    CircuitBreaker,
    CircuitBreakerOpen,
    TRANSIENT_EXCEPTIONS,
    check_memory_usage,
    enforce_memory_limit,
)


class TestRetryableErrors:
    """Test the is_retryable_error function."""
    
    def test_connection_error_is_retryable(self):
        """ConnectionError should be retryable."""
        error = ConnectionError("Connection refused")
        assert is_retryable_error(error) is True
    
    def test_timeout_error_is_retryable(self):
        """TimeoutError should be retryable."""
        error = TimeoutError("Request timed out")
        assert is_retryable_error(error) is True
    
    def test_value_error_not_retryable(self):
        """ValueError should not be retryable."""
        error = ValueError("Invalid value")
        assert is_retryable_error(error) is False

    def test_http_status_error_retryable_and_not(self):
        """HTTPStatusError should respect status codes."""
        request = httpx.Request("GET", "https://example.com")
        response_retry = httpx.Response(429, request=request)
        response_no_retry = httpx.Response(400, request=request)
        retry_error = httpx.HTTPStatusError("rate limited", request=request, response=response_retry)
        no_retry_error = httpx.HTTPStatusError("bad request", request=request, response=response_no_retry)

        assert is_retryable_error(retry_error) is True
        assert is_retryable_error(no_retry_error) is False

    def test_status_code_attribute_retryable(self):
        """status_code attribute on exceptions should be honored."""
        class StatusError(Exception):
            def __init__(self, status_code):
                self.status_code = status_code

        assert is_retryable_error(StatusError(503)) is True
        assert is_retryable_error(StatusError(400)) is False

    def test_response_status_code_retryable(self):
        """status_code on response attribute should be honored."""
        class Response:
            status_code = 502

        class ResponseError(Exception):
            def __init__(self):
                self.response = Response()

        assert is_retryable_error(ResponseError()) is True

    def test_openai_errors_are_retryable(self, monkeypatch):
        """OpenAI error types should be classified correctly."""
        fake_openai = types.ModuleType("openai")

        class RateLimitError(Exception):
            pass

        class APIError(Exception):
            pass

        class APITimeoutError(Exception):
            pass

        class APIConnectionError(Exception):
            pass

        class BadRequestError(Exception):
            pass

        fake_openai.RateLimitError = RateLimitError
        fake_openai.APIError = APIError
        fake_openai.APITimeoutError = APITimeoutError
        fake_openai.APIConnectionError = APIConnectionError
        fake_openai.BadRequestError = BadRequestError

        monkeypatch.setitem(sys.modules, "openai", fake_openai)

        assert is_retryable_error(RateLimitError()) is True
        assert is_retryable_error(BadRequestError()) is False


class TestSyncRetryDecorator:
    """Test the synchronous retry decorator."""
    
    def test_success_on_first_try(self):
        """Function should succeed on first attempt."""
        call_count = 0
        
        @with_retry_sync(max_attempts=3)
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = successful_func()
        assert result == "success"
        assert call_count == 1
    
    def test_retry_on_transient_error(self):
        """Function should retry on transient errors."""
        call_count = 0
        
        @with_retry_sync(max_attempts=3, min_wait=0.1, max_wait=0.2)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"
        
        result = flaky_func()
        assert result == "success"
        assert call_count == 3
    
    def test_max_attempts_exceeded(self):
        """Function should raise after max attempts."""
        @with_retry_sync(max_attempts=2, min_wait=0.1, max_wait=0.2)
        def always_fails():
            raise ConnectionError("Always fails")
        
        with pytest.raises(ConnectionError):
            always_fails()


class TestAsyncRetryDecorators:
    @pytest.mark.asyncio
    async def test_with_retry_async_success(self):
        call_count = 0

        @with_retry(max_attempts=3, min_wait=0.01, max_wait=0.02, use_retryable=True, jitter=True)
        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("retry")
            return "ok"

        result = await flaky()
        assert result == "ok"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_with_retry_async_decorator(self):
        call_count = 0

        @with_retry_async(
            max_attempts=2,
            min_wait=0.01,
            max_wait=0.02,
            exceptions=(ValueError,),
            jitter=True,
        )
        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("retry")
            return "ok"

        result = await flaky()
        assert result == "ok"
        assert call_count == 2


class TestGoogleRetryDecorator:
    def test_with_google_retry_on_http_error(self, monkeypatch):
        class DummyResp:
            def __init__(self, status):
                self.status = status

        class DummyHttpError(Exception):
            def __init__(self, status):
                super().__init__("boom")
                self.resp = DummyResp(status)

        googleapiclient = types.ModuleType("googleapiclient")
        google_errors = types.ModuleType("googleapiclient.errors")
        google_errors.HttpError = DummyHttpError
        googleapiclient.errors = google_errors
        monkeypatch.setitem(sys.modules, "googleapiclient", googleapiclient)
        monkeypatch.setitem(sys.modules, "googleapiclient.errors", google_errors)

        class Counter:
            def __init__(self):
                self.called = False

            def labels(self, *_args):
                return self

            def inc(self):
                self.called = True

        with patch("core.metrics.retry_total", Counter()):
            decorator = with_google_retry(max_attempts=2)
            should_retry = next(
                cell.cell_contents
                for cell in decorator.__closure__ or []
                if callable(cell.cell_contents) and getattr(cell.cell_contents, "__name__", "") == "should_retry"
            )
            assert should_retry(DummyHttpError(429)) is True

    def test_with_google_retry_transient_exception(self):
        decorator = with_google_retry(max_attempts=1)
        should_retry = next(
            cell.cell_contents
            for cell in decorator.__closure__ or []
            if callable(cell.cell_contents) and getattr(cell.cell_contents, "__name__", "") == "should_retry"
        )
        assert should_retry(ConnectionError("boom")) is True

    def test_with_google_retry_metrics_import_failure(self, monkeypatch):
        class DummyResp:
            def __init__(self, status):
                self.status = status

        class DummyHttpError(Exception):
            def __init__(self, status):
                super().__init__("boom")
                self.resp = DummyResp(status)

        googleapiclient = types.ModuleType("googleapiclient")
        google_errors = types.ModuleType("googleapiclient.errors")
        google_errors.HttpError = DummyHttpError
        googleapiclient.errors = google_errors
        monkeypatch.setitem(sys.modules, "googleapiclient", googleapiclient)
        monkeypatch.setitem(sys.modules, "googleapiclient.errors", google_errors)

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "core.metrics":
                raise ImportError("no metrics")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        decorator = with_google_retry(max_attempts=1)
        should_retry = next(
            cell.cell_contents
            for cell in decorator.__closure__ or []
            if callable(cell.cell_contents) and getattr(cell.cell_contents, "__name__", "") == "should_retry"
        )
        assert should_retry(DummyHttpError(429)) is True

    def test_with_google_retry_import_error(self, monkeypatch):
        calls = 0

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "googleapiclient.errors":
                raise ImportError("missing googleapiclient")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        @with_google_retry(max_attempts=2)
        def flaky():
            nonlocal calls
            calls += 1
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            flaky()

        assert calls == 1

    def test_google_retry_import_error_sets_fallback_exceptions(self, monkeypatch):
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "googleapiclient.errors":
                raise ImportError("missing")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        import core.resilience as resilience
        resilience = importlib.reload(resilience)
        assert ConnectionError in resilience.GOOGLE_RETRYABLE_EXCEPTIONS


class TestCircuitBreaker:
    """Test the circuit breaker implementation."""
    
    def test_closed_state_allows_requests(self):
        """Closed circuit breaker should allow requests."""
        breaker = CircuitBreaker(failure_threshold=3, name="test")
        
        with breaker:
            pass  # Should not raise
        
        assert breaker.state == "closed"
        assert breaker.failures == 0
    
    def test_failures_increment(self):
        """Failures should increment counter."""
        breaker = CircuitBreaker(failure_threshold=3, name="test")
        
        try:
            with breaker:
                raise ValueError("Test error")
        except ValueError:
            pass
        
        assert breaker.failures == 1
        assert breaker.state == "closed"
    
    def test_opens_after_threshold(self):
        """Circuit breaker should open after failure threshold."""
        breaker = CircuitBreaker(failure_threshold=2, name="test")
        
        # First failure
        try:
            with breaker:
                raise ValueError("Error 1")
        except ValueError:
            pass
        
        # Second failure - should open
        try:
            with breaker:
                raise ValueError("Error 2")
        except ValueError:
            pass
        
        assert breaker.state == "open"
        assert breaker.failures == 2
    
    def test_open_blocks_requests(self):
        """Open circuit breaker should block requests."""
        import core.resilience as resilience
        breaker = CircuitBreaker(failure_threshold=1, name="test")
        
        # Trip the breaker
        try:
            with breaker:
                raise ValueError("Error")
        except ValueError:
            pass
        
        assert breaker.state == "open"
        
        # Next request should be blocked
        with pytest.raises(resilience.CircuitBreakerOpen):
            with breaker:
                pass
    
    def test_success_resets_failures(self):
        """Successful requests should reset failure count."""
        breaker = CircuitBreaker(failure_threshold=3, name="test")
        
        # Add a failure
        try:
            with breaker:
                raise ValueError("Error")
        except ValueError:
            pass
        
        assert breaker.failures == 1
        
        # Successful request
        with breaker:
            pass
        
        assert breaker.failures == 0

    def test_half_open_recovers(self):
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=1, name="test")
        breaker.state = "open"
        breaker.last_failure_time = 1

        with patch("time.time", return_value=10):
            with breaker:
                pass

        assert breaker.state == "closed"


class TestTimeoutsAndMemory:
    @pytest.mark.asyncio
    async def test_with_timeout_raises(self):
        with pytest.raises(TimeoutError):
            await with_timeout(asyncio.sleep(0.01), timeout_seconds=0.001, operation_name="test")

    @pytest.mark.asyncio
    async def test_with_timeout_success(self):
        result = await with_timeout(asyncio.sleep(0), timeout_seconds=1, operation_name="test")
        assert result is None

    def test_check_memory_usage(self, monkeypatch):
        class FakeMemory:
            percent = 50
            available = 1024 * 1024 * 10
            total = 1024 * 1024 * 100

        monkeypatch.setattr("core.resilience.psutil.virtual_memory", lambda: FakeMemory())
        status = check_memory_usage()
        assert status["percent"] == 50
        assert status["warning"] is False
        assert status["critical"] is False

    def test_enforce_memory_limit_warning(self, monkeypatch):
        class FakeMemory:
            percent = 90
            available = 1024 * 1024 * 10
            total = 1024 * 1024 * 100

        monkeypatch.setattr("core.resilience.psutil.virtual_memory", lambda: FakeMemory())
        enforce_memory_limit()

    def test_enforce_memory_limit_critical(self, monkeypatch):
        class FakeMemory:
            percent = 96
            available = 1024 * 1024 * 2
            total = 1024 * 1024 * 100

        monkeypatch.setattr("core.resilience.psutil.virtual_memory", lambda: FakeMemory())
        with pytest.raises(MemoryError):
            enforce_memory_limit()
