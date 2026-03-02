"""
Hybrid RAG SaaS API Main Application

Production-grade FastAPI application with hardened CORS configuration
for Supabase + Railway + Vercel deployment.
"""

# Suppress third-party deprecation warnings (MUST be first import)
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.gzip import GZipMiddleware

import core.suppress_warnings  # noqa: F401
from core.config import settings
from core.db import check_connection, get_supabase
from core.rate_limit import limiter
from core.shutdown import register_cleanup_handlers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# =============================================================================
# Sentry Error Tracking + Logs (Production)
# =============================================================================
def init_sentry() -> None:
    if settings.SENTRY_DSN and settings.ENVIRONMENT != "test":
        try:
            import logging as py_logging  # Explicit alias to avoid NameError

            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.logging import LoggingIntegration
            from sentry_sdk.integrations.starlette import StarletteIntegration

            # Enable Sentry logging integration
            logging_integration = LoggingIntegration(
                level=py_logging.INFO,        # Capture INFO and above as breadcrumbs
                event_level=py_logging.ERROR  # Send ERROR and above as events
            )

            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                # Performance Monitoring
                traces_sample_rate=0.1,  # 10% of transactions for performance
                # Profiling
                profiles_sample_rate=0.1,  # 10% of sampled transactions
                # Environment
                environment=settings.ENVIRONMENT,
                # Integrations
                integrations=[
                    FastApiIntegration(),
                    StarletteIntegration(),
                    logging_integration,
                ],
                # Release tracking
                release=os.getenv("RAILWAY_GIT_COMMIT_SHA", "local"),
                # Enable experimental logs feature (new in 2.35.0+)
                _experiments={
                    "enable_logs": True,
                },
            )
            logger.info("🔭 Sentry initialized with logging and error tracking")
        except ImportError:
            logger.warning("⚠️ sentry-sdk not installed, error tracking disabled")
        except Exception as e:
            logger.warning(f"⚠️ Sentry initialization failed: {e}")


init_sentry()

# Import routers
from api.v1.chat import router as chat_router
from api.v1.documents import router as documents_router
from api.v1.search import router as search_router
from api.v1.uploads import router as uploads_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    logger.info("🚀 Starting Axio Hub API...")

    # GAP 2 FIX: Register cleanup handlers for graceful shutdown
    # This must be called early to set up SIGTERM/SIGINT handlers
    register_cleanup_handlers()

    # Validate critical security config
    if settings.API_KEY == "default-insecure-key":
        raise RuntimeError(
            "CRITICAL: API_KEY is set to default value. "
            "Set a unique API_KEY environment variable."
        )

    if not settings.API_KEY:
        logger.warning(
            "⚠️ API_KEY is not set. "
            "Set a unique API_KEY environment variable for production."
        )

    # Warn about encryption config mismatch in non-production
    if (
        settings.STRICT_ENCRYPTION_MODE
        and not settings.CHUNK_ENCRYPTION_KEY
        and settings.ENVIRONMENT != "production"
    ):
        logger.warning(
            "⚠️ STRICT_ENCRYPTION_MODE=True but CHUNK_ENCRYPTION_KEY not set. "
            "Reads of encrypted content will fail. "
            "Set CHUNK_ENCRYPTION_KEY or set STRICT_ENCRYPTION_MODE=false for development."
        )

    # Startup: verify database connection
    try:
        await check_connection()
        logger.info("✅ Database connection verified")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        # In production, you might want to raise here

    yield

    # Shutdown: cleanup
    logger.info("👋 Shutting down Axio Hub API...")


# =============================================================================
# Rate Limiting Configuration (uses Redis backend from core.rate_limit)
# =============================================================================

app = FastAPI(
    title="Axio Hub RAG API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)

# Register rate limiters (IP-based default + per-user for LLM endpoints)
from core.rate_limit import user_limiter

app.state.limiter = limiter
app.state.user_limiter = user_limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Normalize all HTTP error responses to structured format
from starlette.exceptions import HTTPException as StarletteHTTPException


@app.exception_handler(StarletteHTTPException)
async def _normalize_http_errors(request: Request, exc: StarletteHTTPException):
    """Ensure all error responses use the structured {error, detail} format."""
    detail = exc.detail
    if isinstance(detail, str):
        # Normalize plain string detail to structured format
        body = {"error": f"HTTP_{exc.status_code}", "detail": detail}
    elif isinstance(detail, dict):
        # Already structured — pass through
        body = detail
    else:
        body = {"error": f"HTTP_{exc.status_code}", "detail": str(detail)}

    return JSONResponse(status_code=exc.status_code, content=body)


from fastapi.exceptions import RequestValidationError


@app.exception_handler(RequestValidationError)
async def _normalize_validation_errors(request: Request, exc: RequestValidationError):
    """Normalize FastAPI validation errors to structured {error, detail} format."""
    messages = "; ".join(
        f"{'.'.join(str(loc) for loc in e['loc'][1:]) or 'request'}: {e['msg']}"
        for e in exc.errors()
    )
    return JSONResponse(
        status_code=422,
        content={"error": "VALIDATION_ERROR", "detail": messages or "Invalid request data"},
    )

# =============================================================================
# CORS Configuration - Production Hardened
# =============================================================================

def configure_cors() -> list[str]:
    """
    Configure CORS origins with production-grade security.

    Rules:
    1. PRODUCTION: Requires ALLOWED_ORIGINS, fails if not set
    2. DEVELOPMENT: Allows localhost fallback
    3. Never allows wildcard (*) in production
    """
    environment = settings.ENVIRONMENT
    allowed_origins_env = settings.ALLOWED_ORIGINS

    origins: list[str] = []

    # Parse comma-separated origins from environment
    if allowed_origins_env:
        origins = [
            origin.strip()
            for origin in allowed_origins_env.split(",")
            if origin.strip()
        ]
        logger.info(f"🔒 CORS: Loaded {len(origins)} origin(s) from ALLOWED_ORIGINS")

    # Validate origin format (applies to all environments)
    validated_origins: list[str] = []
    for origin in origins:
        # Strip trailing slashes (common misconfiguration)
        origin = origin.rstrip("/")

        # Validate scheme is present
        if origin != "*" and not (origin.startswith("http://") or origin.startswith("https://")):
            logger.warning(f"⚠️ CORS: Dropping malformed origin (missing scheme): {origin}")
            continue

        # Validate no path component (origins should be scheme://host[:port] only)
        if origin != "*":
            from urllib.parse import urlparse
            parsed = urlparse(origin)
            if parsed.path and parsed.path != "/":
                logger.warning(f"⚠️ CORS: Dropping origin with path component: {origin}")
                continue

        validated_origins.append(origin)

    origins = validated_origins

    # Environment-specific handling
    if environment == "production":
        # PRODUCTION: Strict validation
        if not origins:
            error_msg = (
                "CRITICAL: ALLOWED_ORIGINS must be set in production! "
                "Example: ALLOWED_ORIGINS=https://app.example.com,https://www.example.com"
            )
            logger.error(f"🔴 {error_msg}")
            raise RuntimeError(error_msg)

        # Validate no wildcards in production
        if "*" in origins:
            error_msg = "CRITICAL: Wildcard (*) CORS origins not allowed in production!"
            logger.error(f"🔴 {error_msg}")
            raise RuntimeError(error_msg)

        # Validate all origins use HTTPS in production
        for origin in origins:
            if not origin.startswith("https://"):
                logger.warning(f"⚠️ Non-HTTPS origin in production: {origin}")

        logger.info(f"🔒 CORS: Production mode - {len(origins)} strict origin(s)")

    else:
        # DEVELOPMENT: Allow localhost fallback
        if not origins:
            origins = [
                "http://localhost:3000",
                "http://localhost:3001",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:3001",
            ]
            logger.info("🔓 CORS: Development mode - using localhost origins")

        # Add specific Vercel preview URL (not wildcard)
        vercel_env = os.getenv("VERCEL_ENV")
        if vercel_env in ("preview", "development"):
            # VERCEL_URL is auto-set by Vercel for each deployment (e.g. "my-app-abc123.vercel.app")
            vercel_url = os.getenv("VERCEL_URL")
            vercel_branch_url = os.getenv("VERCEL_BRANCH_URL")
            if vercel_url:
                origins.append(f"https://{vercel_url}")
            if vercel_branch_url and vercel_branch_url != vercel_url:
                origins.append(f"https://{vercel_branch_url}")
            if vercel_url or vercel_branch_url:
                logger.info("🔓 CORS: Added Vercel preview origin(s)")
            else:
                logger.warning("⚠️ CORS: VERCEL_ENV is set but VERCEL_URL is empty — no preview origin added")

    return origins


def build_cors_origins() -> list[str]:
    try:
        return configure_cors()
    except RuntimeError as e:
        # In development, fall back to permissive mode
        if settings.ENVIRONMENT != "production":
            logger.warning(f"⚠️ CORS configuration error (dev mode, using fallback): {e}")
            return ["*"]
        raise


# Configure and apply CORS
cors_origins = build_cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Idempotency-Key", "Idempotency-Key", "Accept", "Origin"],
    expose_headers=["X-Request-ID", "X-Response-Time"],
)

# Add request tracing middleware
from core.tracing import RequestTracingMiddleware

app.add_middleware(RequestTracingMiddleware)

# Add GZip compression for responses > 1500 bytes
# (avoids CPU overhead from compressing small JSON responses)
app.add_middleware(GZipMiddleware, minimum_size=1500)

# Request body size limit (100MB) to prevent large-payload DoS
MAX_REQUEST_BODY_BYTES = settings.MAX_FILE_SIZE  # 100MB from config

@app.middleware("http")
async def limit_request_body(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_REQUEST_BODY_BYTES:
        return JSONResponse(
            status_code=413,
            content={"detail": "Request body too large"},
        )
    return await call_next(request)

# =============================================================================
# API Routers
# =============================================================================
app.include_router(uploads_router, prefix="/api/v1/uploads", tags=["uploads"])
app.include_router(search_router, prefix="/api/v1", tags=["search"])
app.include_router(chat_router, prefix="/api/v1", tags=["chat"])
app.include_router(documents_router, prefix="/api/v1", tags=["documents"])

from api.v1.integrations import router as integrations_router

app.include_router(integrations_router, prefix="/api/v1", tags=["integrations"])

from api.v1.billing import router as billing_router
from api.v1.jobs import router as jobs_router
from api.v1.notifications import router as notifications_router
from api.v1.settings import router as settings_router
from api.v1.stream import router as stream_router
from api.v1.team import router as team_router
from api.v1.usage import router as usage_router
from api.v1.webhooks import router as webhooks_router

app.include_router(settings_router, prefix="/api/v1", tags=["settings"])
app.include_router(team_router, prefix="/api/v1", tags=["team"])
app.include_router(billing_router, prefix="/api/v1/billing", tags=["billing"])
app.include_router(stream_router, prefix="/api/v1", tags=["streaming"])
app.include_router(jobs_router, prefix="/api/v1", tags=["jobs"])
app.include_router(notifications_router, prefix="/api/v1", tags=["notifications"])
app.include_router(usage_router, prefix="/api/v1", tags=["usage"])
app.include_router(webhooks_router, prefix="/api/v1", tags=["webhooks"])

from api.v1.admin import router as admin_router
from api.v1.admin import user_router as admin_user_router

app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(admin_user_router, prefix="/api/v1/admin", tags=["admin-user"])

from api.v1.dlq import router as dlq_router

app.include_router(dlq_router, prefix="/api/v1/dlq", tags=["Dead Letter Queue"])

from api.v1.feedback import router as feedback_router

app.include_router(feedback_router, prefix="/api/v1", tags=["feedback"])

from api.v1.mcp import router as mcp_router

app.include_router(mcp_router, prefix="/api/v1", tags=["mcp"])

from api.v1.approvals import router as approvals_router

app.include_router(approvals_router, prefix="/api/v1", tags=["approvals"])

from api.v1.consent import router as consent_router

app.include_router(consent_router, prefix="/api/v1", tags=["consent"])

from api.v1.compliance import router as compliance_router

app.include_router(compliance_router, prefix="/api/v1", tags=["compliance"])


# =============================================================================
# Health & Root Endpoints
# =============================================================================
@app.get("/health")
async def health_check():
    """
    Enhanced health check endpoint for Railway/load balancer monitoring.

    Checks connectivity to:
    - Database (PostgreSQL via Supabase)
    - Redis (Celery broker)

    Rules:
    - Database DOWN -> 503 Service Unavailable (Critical)
    - Redis DOWN -> 200 OK (Degraded - Chat/Read APIs still work)
    """
    status = {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "services": {
            "database": "unknown",
            "redis": "unknown"
        },
        "issues": []
    }

    # 1. Check Database (CRITICAL)
    db_healthy = False
    try:
        supabase = get_supabase()
        # Lightweight query to verify connection
        supabase.table("documents").select("id").limit(1).execute()
        status["services"]["database"] = "up"
        db_healthy = True
    except Exception as e:
        status["services"]["database"] = "down"
        status["status"] = "unhealthy"
        logger.error(f"❌ Health check - Database: {e}")

    # 2. Check Redis (NON-CRITICAL for Read API)
    redis_healthy = False
    r = None
    try:
        import redis
        redis_url = settings.REDIS_URL
        r = redis.from_url(redis_url)
        r.ping()
        status["services"]["redis"] = "up"
        redis_healthy = True
    except Exception as e:
        status["services"]["redis"] = "down"
        # Only downgrade to degraded if DB is otherwise fine
        if status["status"] != "unhealthy":
            status["status"] = "degraded"
        status["issues"].append("redis_down")
        logger.error(f"❌ Health check - Redis: {e}")
    finally:
        if r is not None:
            try:
                r.close()
            except Exception as e:
                logger.debug(f"[Health] Failed to close Redis connection: {e}")

    # Decision Matrix:
    # DB Down -> 503 (Unhealthy)
    # DB Up + Redis Down -> 200 (Degraded)
    # DB Up + Redis Up -> 200 (Healthy)

    if db_healthy:
        return status  # Returns 200 even if degraded
    else:
        return JSONResponse(status_code=503, content=status)


@app.get("/")
async def read_root():
    """API root endpoint with documentation links."""
    return {
        "message": "Axio Hub RAG API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }
