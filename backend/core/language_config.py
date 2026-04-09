"""
Shared ISO 639-1 to PostgreSQL regconfig mapping.

This module is the single source of truth for per-language FTS configuration.
Unsupported or missing languages fall back to the `simple` regconfig.
"""

from __future__ import annotations

LANG_TO_REGCONFIG: dict[str, str] = {
    "ar": "arabic",
    "hy": "armenian",
    "eu": "basque",
    "ca": "catalan",
    "da": "danish",
    "nl": "dutch",
    "en": "english",
    "fi": "finnish",
    "fr": "french",
    "de": "german",
    "el": "greek",
    "hi": "hindi",
    "hu": "hungarian",
    "id": "indonesian",
    "ga": "irish",
    "it": "italian",
    "lt": "lithuanian",
    "ne": "nepali",
    "no": "norwegian",
    "pt": "portuguese",
    "ro": "romanian",
    "ru": "russian",
    "sr": "serbian",
    "es": "spanish",
    "sv": "swedish",
    "ta": "tamil",
    "tr": "turkish",
    "yi": "yiddish",
}

DEFAULT_REGCONFIG = "simple"


def get_regconfig(lang_code: str | None) -> str:
    """Map an ISO 639-1 language code to a PostgreSQL regconfig name."""
    if not isinstance(lang_code, str):
        return DEFAULT_REGCONFIG
    normalized = lang_code.strip().lower()
    if not normalized:
        return DEFAULT_REGCONFIG
    return LANG_TO_REGCONFIG.get(normalized, DEFAULT_REGCONFIG)
