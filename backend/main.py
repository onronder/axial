"""
Hybrid RAG SaaS API Main Application

Production-grade FastAPI application with proper CORS configuration
for Supabase + Railway + Vercel deployment.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.db import check_connection

# Import routers
from api.v1.ingest import router as ingest_router
from api.v1.search import router as search_router
from api.v1.chat import router as chat_router
from api.v1.documents import router as documents_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    # Startup: verify database connection
    check_connection()
    yield
    # Shutdown: cleanup if needed
    pass


app = FastAPI(
    title="Hybrid RAG SaaS API",
    version="1.0.0",
    lifespan=lifespan
)

# =============================================================================
# CORS Configuration - Production Grade
# =============================================================================
# Get allowed origins from environment variable (comma-separated)
# Example: ALLOWED_ORIGINS=https://myapp.vercel.app,https://www.myapp.com
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")

# Build origins list from environment
origins = []

if allowed_origins_env:
    # Parse comma-separated origins from environment
    origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]

# Add Vercel preview URLs pattern if VERCEL_ENV is set
vercel_env = os.getenv("VERCEL_ENV")
if vercel_env:
    # In production, only allow specific origins
    # In development/preview, be more permissive
    if vercel_env in ("preview", "development"):
        origins.append("https://*.vercel.app")

# Fallback for local development only
if not origins and os.getenv("ENVIRONMENT", "development") == "development":
    origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ]

# If still no origins configured, log a warning
if not origins:
    import logging
    logging.warning(
        "No CORS origins configured! Set ALLOWED_ORIGINS environment variable. "
        "Example: ALLOWED_ORIGINS=https://myapp.vercel.app"
    )
    # Allow all origins as last resort (not recommended for production)
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

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
app.include_router(settings_router, prefix="/api/v1", tags=["settings"])
app.include_router(team_router, prefix="/api/v1", tags=["team"])


# =============================================================================
# Health & Root Endpoints
# =============================================================================
@app.get("/health")
async def health_check():
    """Health check endpoint for Railway/load balancer monitoring."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/")
async def read_root():
    """API root endpoint with documentation links."""
    return {
        "message": "Hybrid RAG SaaS API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }
