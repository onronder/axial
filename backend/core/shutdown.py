"""
Graceful Shutdown Handler

Ensures clean shutdown of services and connections.
"""

import signal
import sys
import logging
import asyncio
from typing import Callable, List

logger = logging.getLogger(__name__)


class GracefulShutdown:
    """
    Handles graceful shutdown of the application.
    
    Registers signal handlers and cleanup functions.
    """
    
    def __init__(self):
        self.shutdown_handlers: List[Callable] = []
        self.is_shutting_down = False
    
    def register_handler(self, handler: Callable):
        """Register a cleanup handler to run on shutdown."""
        self.shutdown_handlers.append(handler)
    
    def setup(self):
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
        logger.info("✅ Graceful shutdown handlers registered")
    
    def _handle_signal(self, signum, frame):
        """Handle shutdown signals."""
        if self.is_shutting_down:
            logger.warning("⚠️ Shutdown already in progress, forcing exit")
            sys.exit(1)
        
        self.is_shutting_down = True
        signal_name = signal.Signals(signum).name
        logger.info(f"🛑 Received {signal_name}, initiating graceful shutdown...")
        
        # Run all cleanup handlers
        for handler in self.shutdown_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.run(handler())
                else:
                    handler()
            except Exception as e:
                logger.error(f"Error in shutdown handler: {e}")
        
        logger.info("✅ Graceful shutdown complete")
        sys.exit(0)


# Global instance
shutdown_manager = GracefulShutdown()


# Common cleanup handlers

async def cleanup_database_connections():
    """Close database connections."""
    logger.info("Closing database connections...")
    # Add database cleanup logic here


async def cleanup_celery_tasks():
    """Wait for running Celery tasks to complete."""
    logger.info("Waiting for Celery tasks to complete...")
    from core.celery_app import celery_app
    
    # Give tasks 30 seconds to complete
    celery_app.control.shutdown(timeout=30)


async def cleanup_file_handles():
    """Close any open file handles."""
    logger.info("Closing file handles...")
    # Add file cleanup logic here


def register_cleanup_handlers():
    """Register all cleanup handlers."""
    shutdown_manager.register_handler(cleanup_database_connections)
    shutdown_manager.register_handler(cleanup_celery_tasks)
    shutdown_manager.register_handler(cleanup_file_handles)
    shutdown_manager.setup()
