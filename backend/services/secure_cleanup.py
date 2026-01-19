"""
Secure Cleanup Service - Ghost Protocol

Provides forensic-grade file cleanup for Zero-Retention architecture:
- Cryptographic overwrite before file deletion (prevents recovery)
- Smart buffering (RAM vs secure temp file based on size)
- Signal handlers for crash-safe cleanup (dead man's switch)
- S3 staging file removal

Security Level: Military-Grade (DoD 5220.22-M optional)

Usage:
    from services.secure_cleanup import (
        secure_wipe,
        SecureTempFile,
        SmartBuffer,
        cleanup_staging_file,
    )
    
    # Secure temp file with auto-wipe
    with SecureTempFile(suffix=".pdf") as path:
        with open(path, 'wb') as f:
            f.write(content)
        # Process file...
    # File is cryptographically wiped here
    
    # Smart buffer (RAM or disk based on size)
    with SmartBuffer(content, filename="doc.pdf") as buffer:
        if buffer.is_ram_backed:
            process_stream(buffer.get_stream())
        else:
            process_file(buffer.path)
    # Cleanup handled automatically
"""

import atexit
import io
import logging
import os
import signal
import tempfile
import threading
import time
from contextlib import contextmanager
from typing import BinaryIO, Optional, Set

from core.config import settings

logger = logging.getLogger(__name__)

# =============================================================================
# METRICS INTEGRATION
# =============================================================================
# Import metrics with graceful fallback for environments without prometheus

try:
    from core.metrics import (
        secure_wipe_total,
        secure_wipe_duration,
        smart_buffer_allocations,
        smart_buffer_size,
        s3_cleanup_total,
        emergency_cleanup_triggered,
        METRICS_ENABLED,
    )
except ImportError:
    METRICS_ENABLED = False
    # Create dummy metrics for when prometheus is not available
    class _DummyMetric:
        def labels(self, *args, **kwargs): return self
        def inc(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
    secure_wipe_total = _DummyMetric()
    secure_wipe_duration = _DummyMetric()
    smart_buffer_allocations = _DummyMetric()
    smart_buffer_size = _DummyMetric()
    s3_cleanup_total = _DummyMetric()
    emergency_cleanup_triggered = _DummyMetric()


# =============================================================================
# GLOBAL TEMP FILE TRACKING (Dead Man's Switch)
# =============================================================================
# Track all temporary files created by Ghost Protocol so they can be
# emergency-wiped if the process crashes or receives SIGTERM.

_tracked_temp_files: Set[str] = set()
_tracking_lock = threading.Lock()


def _register_temp_file(path: str) -> None:
    """
    Track a temp file for emergency cleanup.
    
    Args:
        path: Absolute path to the temp file
    """
    with _tracking_lock:
        _tracked_temp_files.add(path)


def _unregister_temp_file(path: str) -> None:
    """
    Remove a temp file from tracking after successful cleanup.
    
    Args:
        path: Absolute path to the temp file
    """
    with _tracking_lock:
        _tracked_temp_files.discard(path)


def _emergency_cleanup(trigger: str = "atexit") -> None:
    """
    Emergency cleanup handler - wipes all tracked temp files.
    
    Called automatically on:
    - SIGTERM (container shutdown)
    - SIGINT (Ctrl+C)
    - Process exit (atexit)
    
    This is the "dead man's switch" that ensures no sensitive data
    remains on disk even if the process crashes.
    
    Args:
        trigger: What triggered the cleanup (for metrics)
    """
    with _tracking_lock:
        files_to_clean = list(_tracked_temp_files)
    
    if files_to_clean:
        logger.warning(
            f"🚨 [GhostProtocol] Emergency cleanup: "
            f"{len(files_to_clean)} tracked file(s)"
        )
        emergency_cleanup_triggered.labels(trigger=trigger).inc()
        
        for path in files_to_clean:
            try:
                secure_wipe(path, _skip_metrics=True)  # Avoid double-counting
            except Exception as e:
                # Last resort: try regular delete
                logger.error(
                    f"🚨 [GhostProtocol] Emergency wipe failed for {path}: {e}"
                )
                try:
                    if os.path.exists(path):
                        os.unlink(path)
                except Exception:
                    pass


def _signal_handler(signum: int, frame) -> None:
    """
    Signal handler for graceful shutdown with cleanup.
    
    Intercepts SIGTERM/SIGINT, performs emergency cleanup,
    then re-raises the signal for normal termination.
    """
    sig_name = signal.Signals(signum).name if hasattr(signal, 'Signals') else str(signum)
    logger.warning(
        f"🚨 [GhostProtocol] Received {sig_name}, "
        f"initiating emergency cleanup"
    )
    _emergency_cleanup(trigger=sig_name.lower())
    
    # Re-raise signal to allow normal termination
    signal.signal(signum, signal.SIG_DFL)
    os.kill(os.getpid(), signum)


# Register cleanup handlers at module load time
atexit.register(lambda: _emergency_cleanup(trigger="atexit"))

# Only register signal handlers in main thread
# (Celery workers have their own signal handling)
try:
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)
except ValueError:
    # Cannot set signal handlers outside main thread
    # This is expected in Celery workers - they handle signals differently
    pass


# =============================================================================
# SECURE WIPE
# =============================================================================

def secure_wipe(path: str, passes: Optional[int] = None, _skip_metrics: bool = False) -> bool:
    """
    Securely wipe a file using cryptographic overwrite.
    
    Overwrites file contents with random data before unlinking.
    This prevents forensic recovery of sensitive document content.
    
    Algorithm:
    1. Get file size
    2. For each pass: overwrite entire file with os.urandom
    3. Flush and fsync to ensure writes hit disk
    4. Unlink the file
    
    Args:
        path: Absolute path to file to wipe
        passes: Number of overwrite passes (default from settings.SECURE_WIPE_PASSES)
                1 = fast (single pass), 3 = DoD 5220.22-M compliant
        _skip_metrics: Internal flag to avoid double-counting in emergency cleanup
        
    Returns:
        True if wipe succeeded, False if file didn't exist
        
    Example:
        >>> secure_wipe("/tmp/sensitive_doc.pdf")
        True
    """
    if not path or not os.path.exists(path):
        _unregister_temp_file(path)
        if not _skip_metrics:
            secure_wipe_total.labels(result="not_found").inc()
        return False
    
    passes = passes if passes is not None else getattr(settings, 'SECURE_WIPE_PASSES', 1)
    passes = max(1, passes)  # Ensure at least 1 pass
    start_time = time.time()
    
    try:
        file_size = os.path.getsize(path)
        
        if file_size > 0:
            # Overwrite with random data
            with open(path, 'r+b') as f:
                for pass_num in range(passes):
                    f.seek(0)
                    # Write random data in chunks to handle large files
                    # without consuming excessive memory
                    remaining = file_size
                    chunk_size = 1024 * 1024  # 1MB chunks
                    while remaining > 0:
                        write_size = min(chunk_size, remaining)
                        f.write(os.urandom(write_size))
                        remaining -= write_size
                    f.flush()
                    os.fsync(f.fileno())  # Force write to physical disk
        
        # Finally unlink
        os.unlink(path)
        _unregister_temp_file(path)
        
        # Track metrics
        if not _skip_metrics:
            duration = time.time() - start_time
            secure_wipe_total.labels(result="success").inc()
            secure_wipe_duration.labels(passes=str(passes)).observe(duration)
        
        logger.debug(
            f"🗑️ [GhostProtocol] Secure wiped: {os.path.basename(path)} "
            f"({passes} pass{'es' if passes > 1 else ''})"
        )
        return True
        
    except PermissionError as e:
        logger.error(f"❌ [GhostProtocol] Permission denied wiping {path}: {e}")
        _unregister_temp_file(path)
        if not _skip_metrics:
            secure_wipe_total.labels(result="failure").inc()
        return False
    except Exception as e:
        logger.error(f"❌ [GhostProtocol] Secure wipe failed for {path}: {e}")
        # Best effort: try regular delete
        try:
            if os.path.exists(path):
                os.unlink(path)
            _unregister_temp_file(path)
        except Exception:
            pass
        if not _skip_metrics:
            secure_wipe_total.labels(result="failure").inc()
        return False


# =============================================================================
# SECURE TEMP FILE CONTEXT MANAGER
# =============================================================================

@contextmanager
def SecureTempFile(
    suffix: str = "",
    prefix: str = "axio_",
    dir: Optional[str] = None
):
    """
    Context manager for secure temporary files.
    
    Creates a temp file that is automatically and cryptographically wiped
    when the context exits (even on exceptions). The file is also tracked
    for emergency cleanup if the process crashes.
    
    Args:
        suffix: File suffix (e.g., ".pdf", ".docx")
        prefix: File prefix (default: "axio_")
        dir: Directory for temp file (default: system temp dir)
        
    Yields:
        str: Absolute path to the temporary file
        
    Example:
        with SecureTempFile(suffix=".pdf") as path:
            with open(path, 'wb') as f:
                f.write(pdf_content)
            result = parse_pdf(path)
        # File is securely wiped here, even if parse_pdf raises
    """
    fd = None
    path = None
    
    try:
        fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir)
        os.close(fd)  # Close the file descriptor, caller will open as needed
        _register_temp_file(path)
        logger.debug(f"📁 [GhostProtocol] Created secure temp: {os.path.basename(path)}")
        yield path
    finally:
        if path:
            secure_wipe(path)


# =============================================================================
# SMART BUFFER (RAM vs Disk Decision)
# =============================================================================

class SmartBuffer:
    """
    Intelligent buffer that chooses RAM or disk based on content size.
    
    Decision logic:
    - Small files (< MAX_RAM_PROCESS_LIMIT): Kept in RAM as BytesIO (fast)
    - Large files (>= MAX_RAM_PROCESS_LIMIT): Written to SecureTempFile (OOM-safe)
    
    This prevents OOM crashes on large files while keeping small files fast.
    All disk-backed storage is cryptographically wiped on cleanup.
    
    Attributes:
        is_ram_backed: True if content is in RAM, False if on disk
        path: File path (only if disk-backed, otherwise None)
        
    Example:
        with SmartBuffer(file_content, filename="report.pdf") as buffer:
            if buffer.is_ram_backed:
                # Process in memory
                stream = buffer.get_stream()
            else:
                # Process from disk
                path = buffer.path
    """
    
    def __init__(
        self, 
        content: bytes,
        filename: str = "unknown",
        threshold: Optional[int] = None
    ):
        """
        Initialize SmartBuffer with content.
        
        Args:
            content: File content as bytes
            filename: Original filename (used for temp file suffix)
            threshold: Size threshold in bytes (default from settings.MAX_RAM_PROCESS_LIMIT)
        """
        self._threshold = (
            threshold 
            if threshold is not None 
            else getattr(settings, 'MAX_RAM_PROCESS_LIMIT', 10 * 1024 * 1024)
        )
        self._content = content
        self._filename = filename
        self._size = len(content)
        self._is_ram = self._size < self._threshold
        self._temp_path: Optional[str] = None
        self._closed = False
        
        # Track allocation type
        backing_type = "ram" if self._is_ram else "disk"
        smart_buffer_allocations.labels(backing=backing_type).inc()
        smart_buffer_size.labels(backing=backing_type).observe(self._size)
        
        if not self._is_ram:
            # Large file: write to secure temp file
            suffix = os.path.splitext(filename)[1] or ".bin"
            fd, self._temp_path = tempfile.mkstemp(suffix=suffix, prefix="axio_smart_")
            os.close(fd)
            _register_temp_file(self._temp_path)
            with open(self._temp_path, 'wb') as f:
                f.write(content)
            # Privacy: don't log filename, only size
            logger.debug(
                f"📁 [SmartBuffer] Large file ({self._size:,} bytes) → disk"
            )
        else:
            logger.debug(
                f"💨 [SmartBuffer] Small file ({self._size:,} bytes) → RAM"
            )
    
    @property
    def is_ram_backed(self) -> bool:
        """True if content is in RAM, False if on disk."""
        return self._is_ram
    
    @property
    def path(self) -> Optional[str]:
        """
        Get file path for disk-backed buffers.
        
        Returns None if content is RAM-backed.
        For RAM-backed content, use write_to_temp() if a path is required.
        """
        return self._temp_path
    
    def get_bytes(self) -> bytes:
        """
        Get content as bytes.
        
        Works for both RAM and disk-backed buffers.
        
        Returns:
            File content as bytes
        """
        if self._is_ram:
            return self._content
        else:
            with open(self._temp_path, 'rb') as f:
                return f.read()
    
    def get_stream(self) -> BinaryIO:
        """
        Get content as a file-like stream.
        
        Returns:
            File-like object for reading content.
            For RAM: BytesIO (can be read multiple times after seek(0))
            For disk: File handle (must be closed by caller)
        """
        if self._is_ram:
            return io.BytesIO(self._content)
        else:
            return open(self._temp_path, 'rb')
    
    def write_to_temp(self, suffix: Optional[str] = None) -> str:
        """
        Write content to a new temp file.
        
        Use this when a parser requires a file path but content is RAM-backed.
        The temp file is tracked for emergency cleanup.
        
        IMPORTANT: Caller must call secure_wipe() on the returned path
        when done, or use it within a context manager.
        
        Args:
            suffix: File suffix (default: extracted from filename)
            
        Returns:
            Absolute path to temp file
        """
        suffix = suffix or os.path.splitext(self._filename)[1] or ".bin"
        fd, path = tempfile.mkstemp(suffix=suffix, prefix="axio_parser_")
        os.close(fd)
        _register_temp_file(path)
        
        if self._is_ram:
            with open(path, 'wb') as f:
                f.write(self._content)
        else:
            # Copy from our temp file
            import shutil
            shutil.copy2(self._temp_path, path)
        
        return path
    
    def cleanup(self) -> None:
        """
        Cleanup any disk-backed storage.
        
        Called automatically when used as context manager or on garbage collection.
        Safe to call multiple times.
        """
        if self._closed:
            return
        self._closed = True
        
        if self._temp_path:
            secure_wipe(self._temp_path)
            self._temp_path = None
        
        # Clear RAM content reference
        self._content = b''
    
    def __enter__(self) -> 'SmartBuffer':
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.cleanup()
        return False  # Don't suppress exceptions
    
    def __del__(self):
        """Ensure cleanup on garbage collection."""
        self.cleanup()


# =============================================================================
# S3 STAGING FILE CLEANUP
# =============================================================================

def cleanup_staging_file(
    storage_path: str, 
    bucket: str = "ephemeral-staging"
) -> bool:
    """
    Delete a file from Supabase Storage staging bucket.
    
    Called after file processing to remove the original uploaded file.
    Must be called in BOTH success AND failure paths to ensure
    zero-retention compliance.
    
    Args:
        storage_path: Path within the bucket (e.g., "uploads/user_id/hash/file.pdf")
        bucket: Storage bucket name (default: "ephemeral-staging")
        
    Returns:
        True if deletion succeeded, False otherwise
        
    Example:
        >>> cleanup_staging_file("uploads/abc123/def456/secret.pdf")
        True
    """
    if not storage_path:
        return False
    
    try:
        from core.db import get_supabase
        supabase = get_supabase()
        supabase.storage.from_(bucket).remove([storage_path])
        
        # Track success metric
        s3_cleanup_total.labels(result="success").inc()
        
        # Log only hash portion for privacy (no filename or user info)
        path_parts = storage_path.split("/")
        if len(path_parts) >= 2:
            # Just show partial hash for debugging without leaking info
            path_hash = path_parts[-2][:8] if len(path_parts[-2]) > 8 else "..."
        else:
            path_hash = "..."
        
        logger.info(
            f"🗑️ [GhostProtocol] Removed staging file: .../{path_hash}/..."
        )
        return True
        
    except Exception as e:
        s3_cleanup_total.labels(result="failure").inc()
        logger.error(f"❌ [GhostProtocol] Failed to remove staging file: {e}")
        return False


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    'secure_wipe',
    'SecureTempFile',
    'SmartBuffer',
    'cleanup_staging_file',
    # For testing
    '_tracked_temp_files',
    '_register_temp_file',
    '_unregister_temp_file',
    '_emergency_cleanup',
]
