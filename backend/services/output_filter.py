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
    citations_stripped_count: int = 0
    filtered_text: str = ""


class OutputFilter:
    """Scans LLM output for PII and validates citation references."""

    CITATION_PATTERN = re.compile(r"\[(\d+)\]")

    @staticmethod
    def _is_invalid_citation_ref(ref_num: int, source_count: int) -> bool:
        """Return True when a 1-indexed citation falls outside the source range."""
        return ref_num < 1 or ref_num > source_count

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
        for match in self.CITATION_PATTERN.finditer(text):
            ref_num = int(match.group(1))
            if self._is_invalid_citation_ref(ref_num, source_count):
                invalid.append(f"[{ref_num}]")
        return invalid

    def strip_invalid_citations(self, text: str, source_count: int) -> tuple[str, int]:
        """Remove invalid [N] references while preserving valid citations."""
        stripped_count = 0

        def _replace(match: re.Match[str]) -> str:
            nonlocal stripped_count
            ref_num = int(match.group(1))
            if self._is_invalid_citation_ref(ref_num, source_count):
                stripped_count += 1
                return ""
            return match.group(0)

        stripped_text = self.CITATION_PATTERN.sub(_replace, text)
        if stripped_count:
            stripped_text = re.sub(r"[ \t]{2,}", " ", stripped_text)
            stripped_text = re.sub(r" +([,.;:!?])", r"\1", stripped_text)
            stripped_text = stripped_text.rstrip(" \t")
        return stripped_text, stripped_count

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
        citations_stripped_count = 0

        if pii_types:
            is_safe = False
            filtered_text = self.redact_pii(filtered_text)
            logger.warning(
                "[OutputFilter] PII detected in LLM output: %s", pii_types
            )

        if invalid_cites:
            is_safe = False
            filtered_text, citations_stripped_count = self.strip_invalid_citations(
                filtered_text,
                source_count,
            )
            logger.warning(
                "[OutputFilter] Invalid citation references: %s (stripped=%d)",
                invalid_cites,
                citations_stripped_count,
            )

        return OutputFilterResult(
            is_safe=is_safe,
            pii_detected=pii_types,
            invalid_citations=invalid_cites,
            citations_stripped_count=citations_stripped_count,
            filtered_text=filtered_text,
        )


# Singleton
output_filter = OutputFilter()
