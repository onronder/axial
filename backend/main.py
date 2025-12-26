"""
Hybrid RAG SaaS API Main Application

Production-grade FastAPI application with hardened CORS configuration
for Supabase + Railway + Vercel deployment.
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.gzip import GZipMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from core.db import check_connection, get_supabase
from core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# =============================================================================
# Sentry Error Tracking (Production)
# =============================================================================
if settings.SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            # Performance Monitoring
            traces_sample_rate=0.1,  # 10% of transactions for performance
            # Profiling
            profiles_sample_rate=0.1,  # 10% of sampled transactions
            # Environment
            environment=os.getenv("ENVIRONMENT", "development"),
            # Integrations
            integrations=[
                FastApiIntegration(),
                StarletteIntegration(),
            ],
            # Release tracking
            release=os.getenv("RAILWAY_GIT_COMMIT_SHA", "local"),
        )
        logger.info("🔭 Sentry initialized for error tracking")
    except ImportError:
        logger.warning("⚠️ sentry-sdk not installed, error tracking disabled")
    except Exception as e:
        logger.warning(f"⚠️ Sentry initialization failed: {e}")

# Import routers
from api.v1.ingest import router as ingest_router
from api.v1.search import router as search_router
from api.v1.chat import router as chat_router
from api.v1.documents import router as documents_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    logger.info("🚀 Starting Axio Hub API...")
    
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
# Rate Limiting Configuration
# =============================================================================
limiter = Limiter(key_func=get_remote_address)


app = FastAPI(
    title="Axio Hub RAG API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") != "production" else None,
)

# Register rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
    environment = os.getenv("ENVIRONMENT", "development")
    allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
    
    origins: list[str] = []
    
    # Parse comma-separated origins from environment
    if allowed_origins_env:
        origins = [
            origin.strip() 
            for origin in allowed_origins_env.split(",") 
            if origin.strip()
        ]
        logger.info(f"🔒 CORS: Loaded {len(origins)} origin(s) from ALLOWED_ORIGINS")
    
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
        
        # Add Vercel preview pattern for development
        vercel_env = os.getenv("VERCEL_ENV")
        if vercel_env in ("preview", "development"):
            origins.append("https://*.vercel.app")
            logger.info("🔓 CORS: Added Vercel preview pattern")
    
    return origins


# Configure and apply CORS
try:
    cors_origins = configure_cors()
except RuntimeError as e:
    # In development, fall back to permissive mode
    if os.getenv("ENVIRONMENT") != "production":
        logger.warning(f"⚠️ CORS configuration error (dev mode, using fallback): {e}")
        cors_origins = ["*"]
    else:
        raise

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Response-Time"],
)

# Add request tracing middleware
from core.tracing import RequestTracingMiddleware
app.add_middleware(RequestTracingMiddleware)

# Add GZip compression for responses > 500 bytes
app.add_middleware(GZipMiddleware, minimum_size=500)

# =============================================================================
# API Routers
# =============================================================================
app.include_router(ingest_router, prefix="/api/v1", tags=["ingestion"])
app.include_router(search_router, prefix="/api/v1", tags=["search"])
app.include_router(chat_router, prefix="/api/v1", tags=["chat"])
app.include_router(documents_router, prefix="/api/v1", tags=["documents"])

from api.v1.integrations import router as integrations_router
app.include_router(integrations_router, prefix="/api/v1", tags=["integrations"])

from api.v1.settings import router as settings_router
from api.v1.team import router as team_router
from api.v1.stream import router as stream_router
from api.v1.jobs import router as jobs_router
from api.v1.notifications import router as notifications_router
app.include_router(settings_router, prefix="/api/v1", tags=["settings"])
app.include_router(team_router, prefix="/api/v1", tags=["team"])
app.include_router(stream_router, prefix="/api/v1", tags=["streaming"])
app.include_router(jobs_router, prefix="/api/v1", tags=["jobs"])
app.include_router(notifications_router, prefix="/api/v1", tags=["notifications"])


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
    
    Returns 200 if healthy, 503 if degraded.
    """
    status = {
        "status": "healthy",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "services": {
            "database": "unknown",
            "redis": "unknown"
        }
    }
    
    is_healthy = True
    
    # Check Database connectivity
    try:
        supabase = get_supabase()
        # Lightweight query to verify connection
        supabase.table("documents").select("id").limit(1).execute()
        status["services"]["database"] = "up"
    except Exception as e:
        status["services"]["database"] = "down"
        status["status"] = "degraded"
        is_healthy = False
        logger.error(f"❌ Health check - Database: {e}")
    
    # Check Redis connectivity
    try:
        import redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url)
        r.ping()
        status["services"]["redis"] = "up"
    except Exception as e:
        status["services"]["redis"] = "down"
        status["status"] = "degraded"
        is_healthy = False
        logger.error(f"❌ Health check - Redis: {e}")
    
    if is_healthy:
        return status
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
