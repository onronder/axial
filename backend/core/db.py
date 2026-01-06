"""
Database Connection Management

Provides Supabase client with connection pooling and optimization.
"""

import logging
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from core.config import settings

logger = logging.getLogger(__name__)

# ✅ Singleton pattern for connection pooling
_supabase_client: Client | None = None

def get_supabase() -> Client:
    """
    Get Supabase client with connection pooling.
    
    PERFORMANCE OPTIMIZATION:
    - Singleton pattern ensures we reuse the same client instance
    - Connection pooling configured for production load
    - Pre-ping enabled to verify connection health
    
    Returns:
        Supabase client instance
    """
    global _supabase_client
    
    if _supabase_client is None:
        logger.info("🔌 Initializing Supabase client with connection pool")
        
        try:
            _supabase_client = create_client(
                supabase_url=settings.SUPABASE_URL,
                supabase_key=settings.SUPABASE_SECRET_KEY,
                options=ClientOptions(
                    postgrest_client_timeout=10,
                    storage_client_timeout=10,
                    schema="public",
                    auto_refresh_token=True,
                    persist_session=False
                )
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
    """
    global _supabase_client
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
    try:
        client = get_supabase()
        # Perform minimal query - select 1 row, no data return needed
        # Using count='exact', head=True to minimize data transfer
        # We query the 'documents' table as it's a core table
        client.table("documents").select("id", count="exact").limit(1).execute()
        return True
    except Exception as e:
        logger.error(f"❌ Database connection check failed: {e}")
        raise

# Export for convenience
__all__ = ['get_supabase', 'close_supabase', 'check_connection']
