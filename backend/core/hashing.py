"""
Hashing utilities for ingestion idempotency.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import BinaryIO


def compute_sha256_stream(source: bytes | str | Path | BinaryIO, chunk_size: int = 1024 * 1024) -> str:
    """
    Compute SHA-256 for bytes, file path, or file-like stream using chunked reads.
    """
    hasher = hashlib.sha256()

    if isinstance(source, (str, Path)):
        with open(source, "rb") as fh:
            for chunk in iter(lambda: fh.read(chunk_size), b""):
                hasher.update(chunk)
    elif isinstance(source, (bytes, bytearray)):
        hasher.update(source)
    else:
        # assume file-like
        while True:
            chunk = source.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)

    return hasher.hexdigest()


def compute_content_hash(content: bytes) -> str:
    """Return a SHA-256 hex digest for the provided content bytes (kept for compatibility)."""
    return compute_sha256_stream(content)
