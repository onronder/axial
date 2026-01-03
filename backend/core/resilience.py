"""
Error Resilience Module with Tenacity

Provides retry decorators and utilities for resilient API calls,
especially for external services like Google Drive, Notion, etc.
"""

import logging
import ssl
import http.client
from functools import wraps
from typing import Callable, TypeVar, Any
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    RetryError,
)
from httpx import HTTPStatusError, ConnectError, TimeoutException

logger = logging.getLogger(__name__)

T = TypeVar("T")


# =============================================================================
# Exception Types for Retry
# =============================================================================

# Transient errors that should trigger retry
# Includes network errors, SSL issues, and incomplete reads
TRANSIENT_EXCEPTIONS = (
    ConnectError,
    TimeoutException,
    ConnectionError,
    TimeoutError,
    ConnectionResetError,           # Connection reset by peer
    ssl.SSLError,                   # SSL/TLS errors (EOF, handshake failures)
    http.client.IncompleteRead,     # Partial response received
    OSError,                        # Generic I/O errors (includes many network issues)
)

# Rate limit status codes
RATE_LIMIT_STATUS_CODES = {429, 503, 502, 504}


def is_retryable_error(exception: BaseException) -> bool:
    """
    Determine if an exception should trigger a retry.
    """
    # Check for transient network errors
    if isinstance(exception, TRANSIENT_EXCEPTIONS):
        return True
    
    # Check for HTTP rate limit or server errors
    if isinstance(exception, HTTPStatusError):
        return exception.response.status_code in RATE_LIMIT_STATUS_CODES
    
    return False


# =============================================================================
# Retry Decorators
# =============================================================================

def with_retry(
    max_attempts: int = 3,
    min_wait: float = 1,
    max_wait: float = 10,
    exceptions: tuple = TRANSIENT_EXCEPTIONS,
):
    """
    Decorator that adds retry logic with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
        exceptions: Tuple of exception types to retry on
    
    Usage:
        @with_retry(max_attempts=3)
        async def fetch_documents():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(exceptions),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def with_retry_sync(
    max_attempts: int = 3,
    min_wait: float = 1,
    max_wait: float = 10,
    exceptions: tuple = TRANSIENT_EXCEPTIONS,
):
    """
    Synchronous version of with_retry for non-async functions.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(exceptions),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# =============================================================================
# Google API Specific Retry
# =============================================================================

# Google API errors that should trigger retry
try:
    from googleapiclient.errors import HttpError as GoogleHttpError
    GOOGLE_RETRYABLE_EXCEPTIONS = (
        GoogleHttpError,
        ConnectionError,
        TimeoutError,
    )
except ImportError:
    GOOGLE_RETRYABLE_EXCEPTIONS = (
        ConnectionError,
        TimeoutError,
    )


def with_google_retry(max_attempts: int = 3):
    """
    Retry decorator specifically for Google API calls.
    
    Handles:
    - Rate limiting (403, 429)
    - Temporary server errors (500, 502, 503)
    - Network issues
    
    Usage:
        @with_google_retry(max_attempts=3)
        def fetch_drive_files():
            ...
    """
    def should_retry(exception: BaseException) -> bool:
        if isinstance(exception, TRANSIENT_EXCEPTIONS):
            return True
        
        # Check for Google API specific errors
        try:
            from googleapiclient.errors import HttpError
            if isinstance(exception, HttpError):
                status = exception.resp.status
                # Retry on rate limit and server errors
                if status in {403, 429, 500, 502, 503, 504}:
                    logger.warning(f"🔄 Google API error {status}, will retry: {exception}")
                    return True
        except ImportError:
            pass
        
        return False
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=2, min=2, max=30),
            retry=should_retry,
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# =============================================================================
# Circuit Breaker Pattern (Future Enhancement)
# =============================================================================

class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open and calls are blocked."""
    pass


class CircuitBreaker:
    """
    Simple circuit breaker implementation.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests are blocked
    - HALF_OPEN: Testing if service recovered
    
    Usage:
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        
        try:
            with breaker:
                result = await call_external_api()
        except CircuitBreakerOpen:
            return fallback_response()
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60,
        name: str = "default"
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name
        self.failures = 0
        self.last_failure_time: float | None = None
        self.state = "closed"
    
    def __enter__(self):
        import time
        
        if self.state == "open":
            # Check if recovery timeout has passed
            if self.last_failure_time and time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = "half_open"
                logger.info(f"⚡ Circuit breaker '{self.name}' entering half-open state")
            else:
                logger.warning(f"⚡ Circuit breaker '{self.name}' is OPEN, blocking request")
                raise CircuitBreakerOpen(f"Circuit breaker '{self.name}' is open")
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        
        if exc_type is None:
            # Success - reset failures
            if self.state == "half_open":
                logger.info(f"⚡ Circuit breaker '{self.name}' recovered, closing")
            self.state = "closed"
            self.failures = 0
        else:
            # Failure - increment counter
            self.failures += 1
            self.last_failure_time = time.time()
            
            if self.failures >= self.failure_threshold:
                self.state = "open"
                logger.error(f"⚡ Circuit breaker '{self.name}' OPENED after {self.failures} failures")
            
        return False  # Don't suppress the exception
