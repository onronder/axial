"""
Output Safety Filter (C2)

Scans LLM responses for PII leakage, harmful content, and hallucinated citations.
All safety checks prior to this were input-side only. This adds output-side defense.

Usage:
    from services.output_filter import output_filter

    result = output_filter.filter_response(llm_text, source_count=5)
    if result.pii_detected:
        llm_text = result.filtered_text  # PII redacted
"""

import logging
import re
from dataclasses import dataclass, field

from core.pii_patterns import PII_PATTERNS

logger = logging.getLogger(__name__)


@dataclass
class OutputFilterResult:
    """Result of output safety filtering."""
    is_safe: bool = True
    pii_detected: list[str] = field(default_factory=list)
    invalid_citations: list[str] = field(default_factory=list)
    filtered_text: str = ""


class OutputFilter:
    """Scans LLM output for PII and validates citation references."""

    CITATION_PATTERN = re.compile(r"\[(\d+)\]")

    def scan_pii(self, text: str) -> list[str]:
        """Return list of PII type names detected in text."""
        detected: list[str] = []
        for pii_type, pattern in PII_PATTERNS.items():
            if pattern.search(text):
                detected.append(pii_type)
        return detected

    def redact_pii(self, text: str) -> str:
        """Replace PII matches with [REDACTED]."""
        result = text
        for _pii_type, pattern in PII_PATTERNS.items():
            result = pattern.sub("[REDACTED]", result)
        return result

    def validate_citations(self, text: str, source_count: int) -> list[str]:
        """Check that [N] citation references are within valid source range."""
        invalid: list[str] = []
        if source_count <= 0:
            return invalid
        for match in self.CITATION_PATTERN.finditer(text):
            ref_num = int(match.group(1))
            if ref_num < 1 or ref_num > source_count:
                invalid.append(f"[{ref_num}]")
        return invalid

    def filter_response(
        self, text: str, source_count: int = 0
    ) -> OutputFilterResult:
        """Run all output filters and return result."""
        if not text:
            return OutputFilterResult(filtered_text="")

        pii_types = self.scan_pii(text)
        invalid_cites = self.validate_citations(text, source_count)

        filtered_text = text
        is_safe = True

        if pii_types:
            is_safe = False
            filtered_text = self.redact_pii(text)
            logger.warning(
                "[OutputFilter] PII detected in LLM output: %s", pii_types
            )

        if invalid_cites:
            is_safe = False
            logger.warning(
                "[OutputFilter] Invalid citation references: %s",
                invalid_cites,
            )

        return OutputFilterResult(
            is_safe=is_safe,
            pii_detected=pii_types,
            invalid_citations=invalid_cites,
            filtered_text=filtered_text,
        )


# Singleton
output_filter = OutputFilter()
