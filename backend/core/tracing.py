"""
Request Tracing Middleware

Adds request tracing and observability to the FastAPI application.
Each request gets a unique request ID for correlation across logs.
"""

import uuid
import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds request tracing capabilities:
    
    - Generates unique X-Request-ID for each request
    - Logs request start/end with timing
    - Stores request context for correlation
    
    Usage in main.py:
        from core.tracing import RequestTracingMiddleware
        app.add_middleware(RequestTracingMiddleware)
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Store in request state for access in route handlers
        request.state.request_id = request_id
        
        # Extract user identifier (if available from auth header)
        auth_header = request.headers.get("Authorization", "")
        user_hint = "anonymous"
        if auth_header.startswith("Bearer "):
            # Just use first 8 chars of token as hint (for logging, not security)
            user_hint = auth_header[7:15] + "..."
        
        # Log request start
        start_time = time.perf_counter()
        logger.info(
            f"➡️  [{request_id[:8]}] {request.method} {request.url.path} "
            f"(user: {user_hint})"
        )
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log exception with request ID for correlation
            duration = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"❌ [{request_id[:8]}] {request.method} {request.url.path} "
                f"FAILED after {duration:.1f}ms: {str(e)}"
            )
            raise
        
        # Calculate duration
        duration = (time.perf_counter() - start_time) * 1000
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration:.1f}ms"
        
        # Log request completion
        status_emoji = "✅" if response.status_code < 400 else "⚠️" if response.status_code < 500 else "❌"
        logger.info(
            f"{status_emoji} [{request_id[:8]}] {request.method} {request.url.path} "
            f"→ {response.status_code} ({duration:.1f}ms)"
        )
        
        return response


class RequestContextLogger:
    """
    Context-aware logger that includes request ID in all log messages.
    
    Usage in route handlers:
        from core.tracing import get_request_logger
        
        @app.get("/example")
        async def example(request: Request):
            log = get_request_logger(request)
            log.info("Processing request")  # Includes request ID
    """
    
    def __init__(self, request_id: str, logger: logging.Logger):
        self.request_id = request_id
        self.logger = logger
    
    def _format(self, message: str) -> str:
        return f"[{self.request_id[:8]}] {message}"
    
    def debug(self, message: str):
        self.logger.debug(self._format(message))
    
    def info(self, message: str):
        self.logger.info(self._format(message))
    
    def warning(self, message: str):
        self.logger.warning(self._format(message))
    
    def error(self, message: str):
        self.logger.error(self._format(message))
    
    def exception(self, message: str):
        self.logger.exception(self._format(message))


def get_request_logger(request: Request) -> RequestContextLogger:
    """Get a logger with request context."""
    request_id = getattr(request.state, "request_id", "unknown")
    return RequestContextLogger(request_id, logger)
