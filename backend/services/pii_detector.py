"""
PII Detector for Ingestion Pipeline (M4)

Lightweight PII scanner that runs during document ingestion.
Tags chunks containing PII with metadata so the output filter (C2)
can prioritize scanning those chunks at query time.

Usage:
    from services.pii_detector import detect_pii

    result = detect_pii("My SSN is 123-45-6789")
    if result.types:
        chunk_metadata["has_pii"] = True
        chunk_metadata["pii_types"] = result.types
"""

import logging
from dataclasses import dataclass, field

from core.pii_patterns import PII_PATTERNS

logger = logging.getLogger(__name__)


@dataclass
class PiiDetectionResult:
    """Result of PII scanning."""
    has_pii: bool = False
    types: list[str] = field(default_factory=list)


def detect_pii(text: str | None) -> PiiDetectionResult:
    """Scan text for PII patterns.

    Args:
        text: Content to scan (None and empty string return clean result)

    Returns:
        PiiDetectionResult with detected PII types
    """
    if not text:
        return PiiDetectionResult()

    detected: list[str] = []
    for pii_type, pattern in PII_PATTERNS.items():
        if pattern.search(text):
            detected.append(pii_type)

    if detected:
        logger.debug("[PII] Detected PII types: %s", detected)

    return PiiDetectionResult(
        has_pii=bool(detected),
        types=detected,
    )
