"""
Ingestion normalization helpers.

Keeps provider/source_type naming consistent across APIs, workers, and UI.
"""

from __future__ import annotations

from typing import Optional


DEPRECATED_PROVIDERS = {"file", "drive", "upload"}


def normalize_provider(value: Optional[str]) -> Optional[str]:
    """
    Normalize provider names to canonical values used in DB and jobs.
    """
    if value is None:
        return None
    normalized = value.strip().lower()
    normalized = normalized.replace(" ", "_").replace("-", "_")
    return normalized


def require_canonical_provider(value: Optional[str]) -> str:
    """
    Normalize provider names and reject deprecated aliases at API boundaries.
    """
    normalized = normalize_provider(value)
    if not normalized:
        raise ValueError("provider is required")
    if normalized in DEPRECATED_PROVIDERS:
        raise ValueError(f"Deprecated provider value: {normalized}")
    from connectors import CONNECTORS
    supported = set(CONNECTORS.keys())
    if normalized not in supported:
        raise ValueError(f"Unsupported provider value: {normalized}")
    return normalized


def normalize_source_type(value: Optional[str]) -> Optional[str]:
    """
    Normalize document source_type values to canonical values.
    """
    return normalize_provider(value)
