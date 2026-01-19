"""
Ghost Protocol: Celery Signal Handlers for Emergency Cleanup

This module registers Celery signal handlers to ensure proper cleanup
of sensitive data when worker processes are shut down.

Signal Handlers:
- worker_shutting_down: Called when Celery receives shutdown signal
- worker_process_shutdown: Called when worker process is terminating
- task_prerun: Track active tasks for cleanup
- task_postrun: Cleanup completed tasks

The handlers ensure:
1. All tracked temp files are securely wiped (cryptographic overwrite)
2. S3 staging files from interrupted tasks are removed
3. Metrics are recorded for monitoring

Usage:
    # In celery_app.py or worker initialization
    import worker.ghost_protocol_signals  # noqa: F401
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Track currently running tasks for cleanup on shutdown
_active_tasks: dict = {}  # task_id -> {file_data, storage_path}

try:
    from celery.signals import (
        worker_shutting_down,
        worker_process_shutdown,
        task_prerun,
        task_postrun,
        task_failure,
    )
    CELERY_SIGNALS_AVAILABLE = True
except ImportError:
    CELERY_SIGNALS_AVAILABLE = False
    logger.warning("⚠️ [GhostProtocol] Celery signals not available")


def _perform_emergency_cleanup(reason: str = "shutdown"):
    """
    Perform emergency cleanup of all tracked resources.
    
    Called on worker shutdown to ensure no sensitive data remains.
    """
    from services.secure_cleanup import (
        _emergency_cleanup,
        cleanup_staging_file,
    )
    
    logger.warning(f"🚨 [GhostProtocol] Worker {reason}: initiating emergency cleanup")
    
    # 1. Cleanup tracked temp files (dead man's switch)
    _emergency_cleanup(trigger=f"celery_{reason}")
    
    # 2. Cleanup S3 staging files from interrupted tasks
    active_count = len(_active_tasks)
    if active_count > 0:
        logger.warning(
            f"🚨 [GhostProtocol] Cleaning up {active_count} interrupted task(s)"
        )
        for task_id, task_data in list(_active_tasks.items()):
            storage_path = task_data.get("storage_path")
            if storage_path:
                try:
                    cleanup_staging_file(storage_path)
                    logger.info(f"🗑️ [GhostProtocol] Cleaned S3 for interrupted task {task_id[:8]}...")
                except Exception as e:
                    logger.error(f"❌ [GhostProtocol] Failed to cleanup S3 for {task_id[:8]}: {e}")
        _active_tasks.clear()


if CELERY_SIGNALS_AVAILABLE:
    
    @worker_shutting_down.connect
    def on_worker_shutting_down(sender, sig, how, exitcode, **kwargs):
        """
        Handle Celery worker shutdown signal (SIGTERM, SIGINT, etc.)
        
        This is the main entry point for graceful shutdown cleanup.
        """
        logger.warning(
            f"🚨 [GhostProtocol] Worker shutting down: "
            f"signal={sig}, how={how}, exitcode={exitcode}"
        )
        _perform_emergency_cleanup(reason="shutdown")
    
    
    @worker_process_shutdown.connect  
    def on_worker_process_shutdown(sender, pid, exitcode, **kwargs):
        """
        Handle individual worker process shutdown.
        
        Called when a worker process is terminating (in pool mode).
        """
        logger.warning(
            f"🚨 [GhostProtocol] Worker process {pid} shutdown: exitcode={exitcode}"
        )
        _perform_emergency_cleanup(reason="process_shutdown")
    
    
    @task_prerun.connect
    def on_task_prerun(sender, task_id, task, args, kwargs, **_kwargs):
        """
        Track task start for cleanup on interruption.
        
        Stores file_data so we can cleanup S3 if the task is interrupted.
        """
        # Only track file processing tasks
        if sender.name not in ("process_file_task",):
            return
        
        file_data = kwargs.get("file_data", {})
        storage_path = file_data.get("storage_path")
        
        if storage_path:
            _active_tasks[task_id] = {
                "storage_path": storage_path,
                "started_at": __import__("time").time(),
            }
            logger.debug(f"📋 [GhostProtocol] Tracking task {task_id[:8]}... for cleanup")
    
    
    @task_postrun.connect
    def on_task_postrun(sender, task_id, task, args, kwargs, retval, state, **_kwargs):
        """
        Remove task from tracking on completion.
        
        Note: Actual cleanup is done in the task's finally block.
        This just removes tracking.
        """
        if task_id in _active_tasks:
            del _active_tasks[task_id]
            logger.debug(f"✅ [GhostProtocol] Task {task_id[:8]}... completed, removed from tracking")
    
    
    @task_failure.connect
    def on_task_failure(sender, task_id, exception, args, kwargs, traceback, einfo, **_kwargs):
        """
        Handle task failure - ensure cleanup is tracked.
        
        Note: Actual cleanup is done by handle_task_failure callback.
        This is a backup to ensure tracking is updated.
        """
        if task_id in _active_tasks:
            # Cleanup should have been done by handle_task_failure
            # But we keep track in case it wasn't
            task_data = _active_tasks.pop(task_id, None)
            if task_data:
                logger.warning(
                    f"⚠️ [GhostProtocol] Task {task_id[:8]}... failed, "
                    f"removed from tracking (cleanup via handle_task_failure)"
                )


def get_active_task_count() -> int:
    """
    Get count of currently tracked active tasks.
    
    Useful for monitoring and debugging.
    """
    return len(_active_tasks)


def get_active_tasks() -> dict:
    """
    Get dictionary of currently tracked active tasks.
    
    Returns copy to avoid mutation.
    """
    return dict(_active_tasks)


# =============================================================================
# MODULE INITIALIZATION
# =============================================================================

if CELERY_SIGNALS_AVAILABLE:
    logger.info("🔐 [GhostProtocol] Celery signal handlers registered")
else:
    logger.warning(
        "⚠️ [GhostProtocol] Celery signals not available - "
        "relying on atexit handlers for cleanup"
    )


__all__ = [
    "get_active_task_count",
    "get_active_tasks",
    "CELERY_SIGNALS_AVAILABLE",
]
