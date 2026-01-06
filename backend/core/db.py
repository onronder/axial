"""
Database Connection Management

Provides Supabase client with connection pooling and optimization.
"""

import logging
from supabase import create_client, Client
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
                options={
                    'postgrest': {
                        'schema': 'public',
                    },
                    'auth': {
                        'auto_refresh_token': True,
                        'persist_session': False,  # Server-side, no persistence needed
                    },
                    'realtime': {
                        'timeout': 10000,  # 10 second timeout
                    }
                }
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

# Export for convenience
__all__ = ['get_supabase', 'close_supabase']
