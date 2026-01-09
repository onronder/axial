"""
Ingestion normalization helpers.

Keeps provider/source_type naming consistent across APIs, workers, and UI.
"""

from __future__ import annotations

from typing import Optional


_PROVIDER_ALIASES = {
    "drive": "google_drive",
    "google-drive": "google_drive",
    "gdrive": "google_drive",
    "file": "file_upload",
    "upload": "file_upload",
    "file_upload": "file_upload",
    "file-upload": "file_upload",
    "google_drive": "google_drive",
    "notion": "notion",
    "web": "web",
}


def normalize_provider(value: Optional[str]) -> Optional[str]:
    """
    Normalize provider names to canonical values used in DB and jobs.
    """
    if value is None:
        return None
    normalized = value.strip().lower().replace(" ", "_")
    return _PROVIDER_ALIASES.get(normalized, normalized)


def normalize_source_type(value: Optional[str]) -> Optional[str]:
    """
    Normalize document source_type values to canonical values.
    """
    return normalize_provider(value)
