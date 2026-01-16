"""
Ingestion normalization helpers.

Keeps provider/source_type naming consistent across APIs, workers, and UI.
"""

from __future__ import annotations

from typing import Optional

from core.scopes import CANONICAL_PROVIDER_BY_ALIAS, SCOPE_PREFIX_BY_PROVIDER, canonicalize_provider

KNOWN_PROVIDER_ALIASES = set(SCOPE_PREFIX_BY_PROVIDER.keys())


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
    if normalized in CANONICAL_PROVIDER_BY_ALIAS:
        raise ValueError(f"Deprecated provider value: {normalized}")
    from connectors import CONNECTORS
    supported = set(CONNECTORS.keys())
    if normalized not in supported:
        if normalized in KNOWN_PROVIDER_ALIASES:
            raise ValueError(f"Deprecated provider value: {normalized}")
        raise ValueError(f"Unsupported provider value: {normalized}")
    return normalized


def normalize_source_type(value: Optional[str]) -> Optional[str]:
    """
    Normalize document source_type values to canonical values.
    """
    return canonicalize_provider(value)


def canonicalize_provider_name(value: Optional[str]) -> Optional[str]:
    """
    Normalize provider names and coerce known aliases to canonical providers.
    """
    return canonicalize_provider(value)
