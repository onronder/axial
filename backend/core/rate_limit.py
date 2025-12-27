"""
Rate Limiting Module

Centralized rate limiter configuration for API endpoints.
Uses SlowAPI with Redis backend for distributed rate limiting.

Usage:
    from core.rate_limit import limiter
    
    @router.post("/endpoint")
    @limiter.limit("10/minute")
    async def my_endpoint(request: Request):
        ...
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


def get_user_id_or_ip(request: Request) -> str:
    """
    Get rate limit key based on user ID (authenticated) or IP (anonymous).
    
    This provides per-user rate limiting for authenticated users,
    and per-IP limiting for anonymous requests.
    """
    # Try to get user from request state (set by auth middleware)
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return f"user:{user.id}"
    
    # Fall back to IP address
    return get_remote_address(request)


# Main limiter instance - use IP by default for simplicity
limiter = Limiter(key_func=get_remote_address)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom handler for rate limit exceeded errors.
    Returns a JSON response with retry-after header.
    """
    logger.warning(f"⚠️ [RateLimit] Exceeded for {get_remote_address(request)}: {exc.detail}")
    
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "detail": "Too many requests. Please slow down.",
            "retry_after": str(exc.detail).split("per")[0].strip() if exc.detail else "1 minute"
        },
        headers={"Retry-After": "60"}
    )


# Rate limit tiers for different endpoint types
RATE_LIMITS = {
    "chat": "50/minute",        # Moderate - conversation heavy
    "ingest": "10/minute",      # Strict - resource intensive
    "documents": "60/minute",   # Lenient - read-heavy
    "integrations": "60/minute", # Lenient - OAuth callbacks
    "search": "30/minute",      # Moderate - uses embeddings
    "settings": "30/minute",    # Moderate - updates
    "team": "20/minute",        # Moderate - invites
}
