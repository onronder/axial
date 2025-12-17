from supabase import create_client, Client
from core.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize Supabase Client with v2 Secret Key
# Using SECRET key allows bypassing RLS if needed, which is typical for ingestion backends.
try:
    supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {e}")
    raise

def get_supabase() -> Client:
    """Returns the Supabase client instance."""
    return supabase

async def check_connection() -> bool:
    """
    Checks if the Supabase connection is active.
    """
    try:
        # Minimal query to check connectivity
        get_supabase().table("documents").select("id").limit(1).execute()
        return True
    except Exception as e:
        logger.warning(f"Health check failed (Supabase reachable?): {e}")
        return False
