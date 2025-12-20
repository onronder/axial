"""
Unit Tests for Error Resilience Module

Tests retry decorators and circuit breaker functionality.
"""

import pytest
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
    with_retry_sync,
    is_retryable_error,
    CircuitBreaker,
    CircuitBreakerOpen,
    TRANSIENT_EXCEPTIONS,
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
        breaker = CircuitBreaker(failure_threshold=1, name="test")
        
        # Trip the breaker
        try:
            with breaker:
                raise ValueError("Error")
        except ValueError:
            pass
        
        assert breaker.state == "open"
        
        # Next request should be blocked
        with pytest.raises(CircuitBreakerOpen):
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
