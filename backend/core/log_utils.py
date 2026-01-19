"""
Ghost Protocol: Privacy-Safe Logging Utilities

This module provides utilities for logging file operations without exposing
sensitive information like filenames. Per Ghost Protocol requirements, we use:
- file_hash: First 8 characters of content hash
- job_id: Processing job identifier  
- task_id: Celery task identifier
- doc_id: Document UUID

NEVER log actual filenames in production as they may contain sensitive info.
"""

import hashlib
from typing import Optional


def safe_file_ref(
    filename: Optional[str] = None,
    file_hash: Optional[str] = None,
    job_id: Optional[str] = None,
    doc_id: Optional[str] = None,
) -> str:
    """
    Generate a privacy-safe file reference for logging.
    
    Priority order:
    1. file_hash (most specific, privacy-safe)
    2. doc_id (database reference)
    3. job_id (processing context)
    4. Hashed filename (fallback - hashes the filename itself)
    
    Args:
        filename: Original filename (will be hashed, never logged directly)
        file_hash: Content hash if available
        job_id: Processing job ID
        doc_id: Document database ID
        
    Returns:
        Privacy-safe reference string like "file:abc12345" or "job:xyz789"
    """
    if file_hash:
        # Use first 8 chars of content hash
        return f"file:{file_hash[:8]}"
    
    if doc_id:
        # Use first 8 chars of doc UUID
        return f"doc:{str(doc_id)[:8]}"
    
    if job_id:
        # Use first 8 chars of job UUID
        return f"job:{str(job_id)[:8]}"
    
    if filename:
        # Hash the filename itself as last resort
        # This allows correlation without exposing the actual name
        name_hash = hashlib.sha256(filename.encode()).hexdigest()[:8]
        return f"ref:{name_hash}"
    
    return "ref:unknown"


def safe_file_context(
    filename: Optional[str] = None,
    file_hash: Optional[str] = None,
    job_id: Optional[str] = None,
    doc_id: Optional[str] = None,
    task_id: Optional[str] = None,
    **extra: str,
) -> str:
    """
    Generate a privacy-safe context string for logging with multiple identifiers.
    
    Example output: "file:abc12345 job:xyz789 task:def456"
    
    Args:
        filename: Original filename (will be hashed)
        file_hash: Content hash if available
        job_id: Processing job ID
        doc_id: Document database ID
        task_id: Celery task ID
        **extra: Additional key=value pairs to include
        
    Returns:
        Space-separated context string
    """
    parts = []
    
    if file_hash:
        parts.append(f"file:{file_hash[:8]}")
    elif filename:
        name_hash = hashlib.sha256(filename.encode()).hexdigest()[:8]
        parts.append(f"ref:{name_hash}")
    
    if doc_id:
        parts.append(f"doc:{str(doc_id)[:8]}")
    
    if job_id:
        parts.append(f"job:{str(job_id)[:8]}")
    
    if task_id:
        parts.append(f"task:{str(task_id)[:8]}")
    
    for key, value in extra.items():
        if value:
            parts.append(f"{key}:{str(value)[:12]}")
    
    return " ".join(parts) if parts else "ctx:unknown"


def safe_size_desc(size_bytes: int) -> str:
    """
    Generate a human-readable size description.
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        Human-readable size like "1.5 MB" or "256 KB"
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


# Type alias for file extension (safe to log)
def safe_extension(filename: Optional[str]) -> str:
    """
    Extract file extension safely (extensions are not sensitive).
    
    Args:
        filename: Original filename
        
    Returns:
        Lowercase extension like ".pdf" or "unknown"
    """
    if not filename:
        return "unknown"
    
    if "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()
        # Limit length to prevent abuse
        return f".{ext[:10]}" if ext else "unknown"
    
    return "no-ext"
