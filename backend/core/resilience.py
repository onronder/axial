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
    wait_random_exponential,
    retry_if_exception_type,
    retry_if_exception,
    before_sleep_log,
    after_log,
    RetryError,
)
from httpx import HTTPStatusError, ConnectError, TimeoutException
import asyncio
import psutil

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
    BrokenPipeError,                # Broken pipe (connection closed by peer)
)

# HTTP/2 specific errors (from httpcore/h2)
# ConnectionTerminated is raised when HTTP/2 connection is unexpectedly closed
try:
    from httpcore import ConnectionNotAvailable, RemoteProtocolError
    HTTP2_TRANSIENT_EXCEPTIONS = (ConnectionNotAvailable, RemoteProtocolError)
except ImportError:
    HTTP2_TRANSIENT_EXCEPTIONS = ()

# Combined transient exceptions including HTTP/2 errors
ALL_TRANSIENT_EXCEPTIONS = TRANSIENT_EXCEPTIONS + HTTP2_TRANSIENT_EXCEPTIONS

# Rate limit status codes
RATE_LIMIT_STATUS_CODES = {429, 503, 502, 504}


def is_retryable_error(exception: BaseException) -> bool:
    """
    Determine if an exception should trigger a retry.
    """
    # Check for transient network errors (including HTTP/2 specific)
    if isinstance(exception, TRANSIENT_EXCEPTIONS):
        return True
    
    # Check for HTTP/2 specific transient errors
    if HTTP2_TRANSIENT_EXCEPTIONS and isinstance(exception, HTTP2_TRANSIENT_EXCEPTIONS):
        return True
    
    # Check for HTTP/2 ConnectionTerminated by string match (when class isn't importable)
    exc_name = type(exception).__name__
    exc_str = str(exception)
    if "ConnectionTerminated" in exc_name or "ConnectionTerminated" in exc_str:
        logger.debug(f"🔄 HTTP/2 connection terminated, will retry: {exception}")
        return True
    
    # Check for HTTP rate limit or server errors
    if isinstance(exception, HTTPStatusError):
        status_code = exception.response.status_code
        if status_code in RATE_LIMIT_STATUS_CODES or status_code >= 500:
            return True
        return False

    # Check for status codes on other exception types (e.g., requests, postgrest)
    status_code = getattr(exception, "status_code", None)
    response = getattr(exception, "response", None)
    if status_code is None and response is not None:
        status_code = getattr(response, "status_code", None)
    if status_code is not None:
        if status_code in RATE_LIMIT_STATUS_CODES or status_code >= 500:
            return True
        return False

    # OpenAI-specific transient errors (import lazily to avoid hard dependency at import time)
    try:
        from openai import RateLimitError, APIError, APITimeoutError, APIConnectionError, BadRequestError
        if isinstance(exception, BadRequestError):
            return False
        if isinstance(exception, (RateLimitError, APIError, APITimeoutError, APIConnectionError)):
            return True
    except ImportError:
        pass  # openai not installed
    
    return False


# =============================================================================
# Retry Decorators
# =============================================================================

def with_retry(
    max_attempts: int = 3,
    min_wait: float = 1,
    max_wait: float = 10,
    exceptions: tuple = TRANSIENT_EXCEPTIONS,
    use_retryable: bool = False,
    jitter: bool = False,
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
        retry_condition = (
            retry_if_exception(is_retryable_error)
            if use_retryable
            else retry_if_exception_type(exceptions)
        )
        wait_strategy = (
            wait_random_exponential(multiplier=1, min=min_wait, max=max_wait)
            if jitter
            else wait_exponential(multiplier=1, min=min_wait, max=max_wait)
        )
        @wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_strategy,
            retry=retry_condition,
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
    use_retryable: bool = False,
    jitter: bool = False,
):
    """
    Synchronous version of with_retry for non-async functions.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        retry_condition = (
            retry_if_exception(is_retryable_error)
            if use_retryable
            else retry_if_exception_type(exceptions)
        )
        wait_strategy = (
            wait_random_exponential(multiplier=1, min=min_wait, max=max_wait)
            if jitter
            else wait_exponential(multiplier=1, min=min_wait, max=max_wait)
        )
        @wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_strategy,
            retry=retry_condition,
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def with_retry_async(
    max_attempts: int = 3,
    min_wait: float = 1,
    max_wait: float = 10,
    exceptions: tuple = TRANSIENT_EXCEPTIONS,
    use_retryable: bool = False,
    jitter: bool = False,
):
    """
    Async retry decorator with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
        exceptions: Tuple of exception types to retry on
    
    Usage:
        @with_retry_async(max_attempts=3)
        async def fetch_data():
            ...
    """
    def decorator(func):
        retry_condition = (
            retry_if_exception(is_retryable_error)
            if use_retryable
            else retry_if_exception_type(exceptions)
        )
        wait_strategy = (
            wait_random_exponential(multiplier=1, min=min_wait, max=max_wait)
            if jitter
            else wait_exponential(multiplier=1, min=min_wait, max=max_wait)
        )
        @wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_strategy,
            retry=retry_condition,
            before_sleep=before_sleep_log(logger, logging.WARNING),
            after=after_log(logger, logging.INFO),
            reraise=True,
        )
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
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
                    if status in {403, 429}:
                        try:
                            from core.metrics import retry_total
                            retry_total.labels("google_drive", "rate_limit").inc()
                        except ImportError:
                            pass  # Metrics not available
                    logger.warning(f"🔄 Google API error {status}, will retry: {exception}")
                    return True
        except ImportError:
            pass
        
        return False
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_random_exponential(multiplier=2, min=2, max=30),
            retry=retry_if_exception(should_retry),
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

    async def __aenter__(self):
        """Async context manager entry — reuses sync logic."""
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit — reuses sync logic."""
        return self.__exit__(exc_type, exc_val, exc_tb)


# =============================================================================
# Service-Specific Circuit Breaker Instances
# =============================================================================

# Circuit breaker for OpenAI API
openai_breaker = CircuitBreaker(
    failure_threshold=5,  # Open after 5 consecutive failures
    recovery_timeout=60,  # Stay open for 60 seconds
    name="OpenAI API"
)

# Circuit breaker for LlamaParse API
llamaparse_breaker = CircuitBreaker(
    failure_threshold=3,  # Open after 3 failures (more sensitive - expensive service)
    recovery_timeout=120,  # Stay open for 2 minutes
    name="LlamaParse API"
)

# Circuit breaker for Supabase
supabase_breaker = CircuitBreaker(
    failure_threshold=5,  # Open after 5 consecutive failures
    recovery_timeout=30,  # Stay open for 30 seconds
    name="Supabase"
)

# Circuit breaker for Google Drive API
google_drive_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    name="Google Drive API"
)

# Circuit breaker for Notion API
notion_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    name="Notion API"
)

# Circuit breaker for Dropbox API
dropbox_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    name="Dropbox API"
)

logger.info("🔌 Circuit breakers initialized for: OpenAI, LlamaParse, Supabase, Google Drive, Notion, Dropbox")


# =============================================================================
# Timeout Utilities
# =============================================================================

class Timeouts:
    """Centralized timeout configuration for all operations."""
    PDF_PARSING = 300  # 5 minutes for complex PDFs
    DOCX_PARSING = 60   # 1 minute for DOCX
    EMBEDDING_BATCH = 60  # 1 minute per batch
    SUPABASE_RPC = 30   # 30 seconds for DB operations
    FILE_DOWNLOAD = 120  # 2 minutes for file downloads
    LLAMAPARSE_API = 180  # 3 minutes for LlamaParse


async def with_timeout(
    coro,
    timeout_seconds: float,
    operation_name: str = "operation"
):
    """
    Execute async operation with timeout.
    
    Args:
        coro: Coroutine to execute
        timeout_seconds: Timeout in seconds
        operation_name: Name for error messages
        
    Returns:
        Result of coroutine
        
    Raises:
        TimeoutError: If operation exceeds timeout
    """
    try:
        result = await asyncio.wait_for(coro, timeout=timeout_seconds)
        return result
    except asyncio.TimeoutError:
        logger.error(
            f"⏱️ Timeout: {operation_name} exceeded {timeout_seconds}s"
        )
        raise TimeoutError(
            f"{operation_name} timed out after {timeout_seconds} seconds"
        )


# =============================================================================
# Service-Specific Retry Configurations
# =============================================================================

OPENAI_RETRY_CONFIG = {
    "max_attempts": 3,
    "min_wait": 2.0,
    "max_wait": 10.0,
    "exceptions": TRANSIENT_EXCEPTIONS
}

SUPABASE_RETRY_CONFIG = {
    "max_attempts": 3,
    "min_wait": 1.0,
    "max_wait": 5.0,
    "exceptions": TRANSIENT_EXCEPTIONS
}

LLAMAPARSE_RETRY_CONFIG = {
    "max_attempts": 3,
    "min_wait": 3.0,
    "max_wait": 15.0,
    "exceptions": TRANSIENT_EXCEPTIONS
}

logger.info("✅ Retry configurations loaded: OpenAI, Supabase, LlamaParse")


# =============================================================================
# Memory Monitoring
# =============================================================================

def check_memory_usage() -> dict:
    """Check current memory usage."""
    memory = psutil.virtual_memory()
    return {
        "percent": memory.percent,
        "available_mb": memory.available / 1024 / 1024,
        "total_mb": memory.total / 1024 / 1024,
        "warning": memory.percent > 85,  # Warning at 85%
        "critical": memory.percent > 95  # Critical at 95%
    }


def enforce_memory_limit():
    """Raise error if memory usage is critical."""
    status = check_memory_usage()
    
    if status["critical"]:
        raise MemoryError(
            f"Memory usage critical: {status['percent']:.1f}% "
            f"({status['available_mb']:.0f}MB available)"
        )
    
    if status["warning"]:
        logger.warning(
            f"⚠️ Memory usage high: {status['percent']:.1f}%"
        )
