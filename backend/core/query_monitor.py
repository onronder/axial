"""
Database Query Performance Monitoring

Tracks query execution times and identifies slow queries.
"""

import time
import logging
from typing import Optional, Callable, Any
from functools import wraps
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Slow query threshold in seconds
SLOW_QUERY_THRESHOLD = 1.0

# Query statistics
query_stats = {
    "total_queries": 0,
    "slow_queries": 0,
    "total_time": 0.0,
    "slowest_query": {"query": "", "time": 0.0}
}


@contextmanager
def monitor_query(query_name: str, log_slow: bool = True):
    """
    Context manager to monitor query execution time.
    
    Usage:
        with monitor_query("fetch_user_data"):
            result = supabase.table("users").select("*").execute()
    """
    start_time = time.time()
    
    try:
        yield
    finally:
        execution_time = time.time() - start_time
        
        # Update statistics
        query_stats["total_queries"] += 1
        query_stats["total_time"] += execution_time
        
        # Check if slow
        if execution_time > SLOW_QUERY_THRESHOLD:
            query_stats["slow_queries"] += 1
            
            if log_slow:
                logger.warning(
                    f"🐌 Slow query detected: {query_name} took {execution_time:.2f}s "
                    f"(threshold: {SLOW_QUERY_THRESHOLD}s)"
                )
        
        # Update slowest query
        if execution_time > query_stats["slowest_query"]["time"]:
            query_stats["slowest_query"] = {
                "query": query_name,
                "time": execution_time
            }
        
        # Log all queries in debug mode
        logger.debug(f"📊 Query {query_name} executed in {execution_time:.3f}s")


def track_query_performance(query_name: str):
    """
    Decorator to track query performance.
    
    Usage:
        @track_query_performance("get_user_documents")
        async def get_user_documents(user_id: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            with monitor_query(query_name):
                return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            with monitor_query(query_name):
                return func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def get_query_stats() -> dict:
    """Get current query statistics."""
    if query_stats["total_queries"] == 0:
        return {
            "total_queries": 0,
            "slow_queries": 0,
            "average_time": 0.0,
            "slowest_query": None
        }
    
    return {
        "total_queries": query_stats["total_queries"],
        "slow_queries": query_stats["slow_queries"],
        "slow_query_percentage": (query_stats["slow_queries"] / query_stats["total_queries"]) * 100,
        "average_time": query_stats["total_time"] / query_stats["total_queries"],
        "total_time": query_stats["total_time"],
        "slowest_query": query_stats["slowest_query"]
    }


def reset_query_stats():
    """Reset query statistics."""
    query_stats["total_queries"] = 0
    query_stats["slow_queries"] = 0
    query_stats["total_time"] = 0.0
    query_stats["slowest_query"] = {"query": "", "time": 0.0}


def log_query_stats():
    """Log current query statistics."""
    stats = get_query_stats()
    
    if stats["total_queries"] == 0:
        logger.info("📊 No queries executed yet")
        return
    
    logger.info(
        f"📊 Query Statistics:\n"
        f"  Total queries: {stats['total_queries']}\n"
        f"  Slow queries: {stats['slow_queries']} ({stats['slow_query_percentage']:.1f}%)\n"
        f"  Average time: {stats['average_time']:.3f}s\n"
        f"  Total time: {stats['total_time']:.2f}s\n"
        f"  Slowest query: {stats['slowest_query']['query']} ({stats['slowest_query']['time']:.2f}s)"
    )
