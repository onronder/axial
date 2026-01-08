"""
Hashing utilities for ingestion idempotency.
"""

from __future__ import annotations

import hashlib


def compute_content_hash(content: bytes) -> str:
    """Return a SHA-256 hex digest for the provided content bytes."""
    return hashlib.sha256(content).hexdigest()
