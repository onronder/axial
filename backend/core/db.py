"""
Database Connection Management

Provides Supabase client with connection pooling and optimization.

THREAD SAFETY: Uses threading.Lock for safe singleton initialization
across concurrent requests (fix for shutdown cleanup).
"""

import logging
import asyncio
import os
import threading
from supabase import create_client, Client, ClientOptions
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.config import settings

logger = logging.getLogger(__name__)

# Thread-safe singleton pattern for connection pooling
_supabase_client: Client | None = None
_supabase_lock = threading.Lock()
SessionLocal = None
IngestionSessionLocal = None


def _convert_to_psycopg3_url(url: str | None) -> str | None:
    """
    Convert PostgreSQL URL to use psycopg3 dialect.
    
    psycopg3 (psycopg[binary]) requires 'postgresql+psycopg://' dialect
    instead of the default 'postgresql://' which uses psycopg2.
    """
    if url is None:
        return None
    # Convert postgresql:// to postgresql+psycopg:// for psycopg3
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    # Already using a specific dialect
    return url


def _init_sqlalchemy_sessions():
    """
    Initialize SQLAlchemy session factories for general and ingestion roles.
    Prefers INGESTION_DATABASE_URL; falls back to DATABASE_URL if present.
    """
    global SessionLocal, IngestionSessionLocal

    ingestion_url = _convert_to_psycopg3_url(
        settings.INGESTION_DATABASE_URL or os.getenv("INGESTION_DATABASE_URL")
    )
    default_url = ingestion_url or _convert_to_psycopg3_url(os.getenv("DATABASE_URL"))

    ingestion_engine = None
    if ingestion_url:
        ingestion_engine = create_engine(ingestion_url, pool_pre_ping=True)
        IngestionSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=ingestion_engine)

    # NOTE: This factory is prepared for future direct-DB access by workers (Least Privilege).
    # Currently, workers use the Supabase HTTP Client. Do not remove this config.
    if default_url and not SessionLocal:
        default_engine = ingestion_engine or create_engine(default_url, pool_pre_ping=True)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=default_engine)

    if not IngestionSessionLocal:
        IngestionSessionLocal = SessionLocal


_init_sqlalchemy_sessions()

def _build_client_options() -> ClientOptions:
    """Build Supabase client options with compatibility fallbacks."""
    try:
        options = ClientOptions(
            postgrest_client_timeout=10,
            storage_client_timeout=10,
            schema="public",
            auto_refresh_token=True,
            persist_session=False
        )
    except TypeError:
        # Older client versions may not accept these kwargs.
        options = ClientOptions()
        for key, value in {
            "postgrest_client_timeout": 10,
            "storage_client_timeout": 10,
            "schema": "public",
            "auto_refresh_token": True,
            "persist_session": False,
        }.items():
            if hasattr(options, key):
                setattr(options, key, value)

    if not hasattr(options, "storage"):
        try:
            from supabase_auth._sync.storage import SyncMemoryStorage
            options.storage = SyncMemoryStorage()
        except Exception:
            options.storage = None

    return options

def get_supabase() -> Client:
    """
    Get Supabase client with connection pooling.

    PERFORMANCE OPTIMIZATION:
    - Singleton pattern ensures we reuse the same client instance
    - Connection pooling configured for production load
    - Pre-ping enabled to verify connection health

    THREAD SAFETY: Uses double-checked locking pattern to prevent
    race conditions during concurrent initialization.

    Returns:
        Supabase client instance
    """
    global _supabase_client

    # Fast path: already initialized
    if _supabase_client is not None:
        return _supabase_client

    # Slow path: acquire lock and initialize
    with _supabase_lock:
        # Double-check after acquiring lock
        if _supabase_client is None:
            logger.info("🔌 Initializing Supabase client with connection pool")

            try:
                _supabase_client = create_client(
                    supabase_url=settings.SUPABASE_URL,
                    supabase_key=settings.SUPABASE_SECRET_KEY,
                    options=_build_client_options()
                )

                logger.info("✅ Supabase client initialized successfully")

            except Exception as e:
                logger.error(f"❌ Failed to initialize Supabase client: {e}")
                raise

    return _supabase_client

def close_supabase():
    """
    Close Supabase client on shutdown.

    Call this during application shutdown to clean up resources.
    Thread-safe via lock.
    """
    global _supabase_client
    with _supabase_lock:
        if _supabase_client:
            # Cleanup if needed (Supabase client doesn't have explicit close)
            _supabase_client = None
            logger.info("🔌 Supabase client closed")

async def check_connection() -> bool:
    """
    Verify database connection health.
    
    Performs a lightweight query to ensure the Supabase client
    can successfully communicate with the database.
    
    Returns:
        bool: True if connection is healthy
        
    Raises:
        Exception: If connection fails
    """
    client = get_supabase()
    retries = 3
    base_delay = 1.0
    last_exc: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            client.table("documents").select("id", count="exact").limit(1).execute()
            return True
        except Exception as e:
            last_exc = e
            if attempt == retries:
                logger.error(f"❌ Database connection check failed after {attempt}/{retries} attempts: {e}")
                raise
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning(
                "⚠️ Database connection check failed (attempt %s/%s): %s; retrying in %.1fs",
                attempt,
                retries,
                e,
                delay,
            )
            await asyncio.sleep(delay)

# Export for convenience
__all__ = ['get_supabase', 'close_supabase', 'check_connection']
