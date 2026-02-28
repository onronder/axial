"""
Unit Tests for Output Safety Filter (C2)

Tests PII detection, redaction, citation validation, and clean passthrough.
"""

import pytest

from services.output_filter import OutputFilter, OutputFilterResult


class TestOutputFilter:
    @pytest.fixture
    def f(self):
        return OutputFilter()

    @pytest.mark.unit
    def test_detects_ssn(self, f):
        result = f.filter_response("SSN is 123-45-6789", source_count=0)
        assert "ssn" in result.pii_detected
        assert result.is_safe is False

    @pytest.mark.unit
    def test_detects_credit_card(self, f):
        result = f.filter_response("Card: 4111-1111-1111-1111", source_count=0)
        assert "credit_card" in result.pii_detected
        assert result.is_safe is False

    @pytest.mark.unit
    def test_redacts_pii_from_text(self, f):
        result = f.filter_response("SSN is 123-45-6789", source_count=0)
        assert "123-45-6789" not in result.filtered_text
        assert "[REDACTED]" in result.filtered_text
        assert "SSN is " in result.filtered_text  # surrounding text preserved

    @pytest.mark.unit
    def test_validates_citations_within_range(self, f):
        result = f.filter_response("See [1] and [2]", source_count=3)
        assert len(result.invalid_citations) == 0
        assert result.is_safe is True

    @pytest.mark.unit
    def test_detects_invalid_citation_references(self, f):
        result = f.filter_response("See [5]", source_count=3)
        assert "[5]" in result.invalid_citations
        assert result.is_safe is False

    @pytest.mark.unit
    def test_clean_text_passes_through(self, f):
        result = f.filter_response("Normal response text", source_count=0)
        assert result.is_safe is True
        assert result.filtered_text == "Normal response text"
        assert result.pii_detected == []
        assert result.invalid_citations == []

    @pytest.mark.unit
    def test_detects_phone_number(self, f):
        result = f.filter_response("Call (555) 123-4567", source_count=0)
        assert "phone_us" in result.pii_detected
        assert result.is_safe is False

    @pytest.mark.unit
    def test_detects_email(self, f):
        result = f.filter_response("Contact john@example.com", source_count=0)
        assert "email" in result.pii_detected
        assert result.is_safe is False

    @pytest.mark.unit
    def test_empty_text_returns_safe(self, f):
        result = f.filter_response("", source_count=0)
        assert result.is_safe is True
        assert result.filtered_text == ""
        assert result.pii_detected == []

    @pytest.mark.unit
    def test_multiple_pii_types_detected(self, f):
        result = f.filter_response(
            "SSN 123-45-6789 and email user@example.com", source_count=0
        )
        assert "ssn" in result.pii_detected
        assert "email" in result.pii_detected
        assert len(result.pii_detected) >= 2
        assert result.is_safe is False
        # Verify both are redacted
        assert "123-45-6789" not in result.filtered_text
        assert "user@example.com" not in result.filtered_text

    @pytest.mark.unit
    def test_citation_zero_source_count_skips_validation(self, f):
        result = f.filter_response("See [1] and [2]", source_count=0)
        assert len(result.invalid_citations) == 0

    @pytest.mark.unit
    def test_citation_boundary_valid(self, f):
        """Citation [1] with source_count=1 is valid."""
        result = f.filter_response("See [1]", source_count=1)
        assert len(result.invalid_citations) == 0

    @pytest.mark.unit
    def test_citation_zero_ref_invalid(self, f):
        """Citation [0] is always invalid (1-indexed)."""
        result = f.filter_response("See [0]", source_count=3)
        assert "[0]" in result.invalid_citations

    @pytest.mark.unit
    def test_redact_preserves_non_pii_text(self, f):
        text = "The answer is 42. Contact support@example.com for help."
        result = f.filter_response(text, source_count=0)
        assert "The answer is 42." in result.filtered_text
        assert "for help." in result.filtered_text
        assert "support@example.com" not in result.filtered_text
