"""
Vision LLM Circuit Breaker

Circuit breaker implementation for Vision LLM services.
Prevents cascading failures and manages API quota limits.
"""

import logging
import time
from enum import Enum
from typing import Tuple

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Blocking requests
    HALF_OPEN = "half_open" # Testing recovery


class VisionCircuitBreaker:
    """
    Circuit breaker for Vision LLM APIs.

    Tracks failures and temporarily disables the service when:
    - Too many consecutive failures occur
    - Quota/rate limit errors are detected

    States:
    - CLOSED: Normal operation, requests allowed
    - OPEN: Service disabled, requests blocked
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: int = 300,  # 5 minutes
        quota_timeout: int = 3600,    # 1 hour for quota errors
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Service name for logging
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds before trying recovery
            quota_timeout: Longer timeout for quota errors
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.quota_timeout = quota_timeout

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0
        self._is_quota_error = False

    @property
    def state(self) -> CircuitState:
        """Get current circuit state, checking for recovery."""
        if self._state == CircuitState.OPEN:
            timeout = self.quota_timeout if self._is_quota_error else self.recovery_timeout
            if time.time() - self._last_failure_time >= timeout:
                self._state = CircuitState.HALF_OPEN
                logger.info(f"[{self.name}] Circuit half-open, testing recovery")
        return self._state

    def can_execute(self) -> Tuple[bool, str]:
        """
        Check if a request can be executed.

        Returns:
            Tuple of (allowed, reason)
        """
        state = self.state

        if state == CircuitState.CLOSED:
            return True, "ok"
        elif state == CircuitState.HALF_OPEN:
            return True, "testing"
        else:  # OPEN
            if self._is_quota_error:
                return False, "quota_exceeded"
            return False, "circuit_open"

    def record_success(self) -> None:
        """Record successful execution."""
        if self._state == CircuitState.HALF_OPEN:
            logger.info(f"[{self.name}] Circuit closed after successful recovery")

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._is_quota_error = False

    def record_failure(self, error_type: str = "error") -> None:
        """
        Record failed execution.

        Args:
            error_type: Type of error ("error", "402", "quota", "rate_limit")
        """
        self._failure_count += 1
        self._last_failure_time = time.time()

        # Check for quota/billing errors
        is_quota = error_type in ("402", "quota", "rate_limit", "payment")
        if is_quota:
            self._is_quota_error = True
            self._state = CircuitState.OPEN
            logger.warning(
                f"[{self.name}] Circuit open due to quota error, "
                f"will retry in {self.quota_timeout}s"
            )
            return

        # Regular failure handling
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                f"[{self.name}] Circuit open after {self._failure_count} failures, "
                f"will retry in {self.recovery_timeout}s"
            )
        else:
            logger.debug(
                f"[{self.name}] Failure recorded "
                f"({self._failure_count}/{self.failure_threshold})"
            )


# Global circuit breakers for Vision services
OPENAI_VISION_CIRCUIT = VisionCircuitBreaker(
    name="OpenAI_Vision",
    failure_threshold=3,
    recovery_timeout=300,
    quota_timeout=3600,
)

GEMINI_VISION_CIRCUIT = VisionCircuitBreaker(
    name="Gemini_Vision",
    failure_threshold=3,
    recovery_timeout=300,
    quota_timeout=3600,
)


def get_circuit_for_provider(provider: str) -> VisionCircuitBreaker:
    """Get the circuit breaker for a vision provider."""
    if provider == "openai":
        return OPENAI_VISION_CIRCUIT
    elif provider == "gemini":
        return GEMINI_VISION_CIRCUIT
    else:
        # Return OpenAI circuit as default
        return OPENAI_VISION_CIRCUIT
