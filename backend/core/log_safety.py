"""
Helpers for logging sensitive user input without exposing raw content.
"""

from __future__ import annotations

import hashlib


def query_fingerprint(text: str | None) -> str:
    normalized = text or ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]


def describe_query(text: str | None) -> str:
    normalized = text or ""
    return f"len={len(normalized)} sha={query_fingerprint(normalized)}"


def query_log_fields(text: str | None) -> dict[str, str | int]:
    normalized = text or ""
    return {
        "query_len": len(normalized),
        "query_hash": query_fingerprint(normalized),
    }
