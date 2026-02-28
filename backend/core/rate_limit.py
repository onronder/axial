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

import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)


def get_user_id_or_ip(request: Request) -> str:
    """
    Get rate limit key based on user ID (authenticated) or IP (anonymous).

    This provides per-user rate limiting for authenticated users,
    and per-IP limiting for anonymous requests.

    Parses the JWT from the Authorization header directly. This is safe because:
    - Actual auth verification happens in the get_current_user endpoint dependency
    - Rate limiting by a forged user_id only hurts the attacker
    """
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            import jwt

            token = auth_header[7:]
            # Decode without verification — we only need the sub claim for rate limiting.
            # Auth verification happens separately in get_current_user dependency.
            payload = jwt.decode(token, options={"verify_signature": False}, algorithms=["HS256"])
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
        except Exception:
            pass

    # Fall back to IP address
    return get_remote_address(request)


# Main limiter instance - use IP by default for simplicity
limiter = Limiter(key_func=get_remote_address)

# Per-user limiter for LLM/chat endpoints — prevents abuse in shared network environments
user_limiter = Limiter(key_func=get_user_id_or_ip)


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
