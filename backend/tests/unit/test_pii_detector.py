"""
Unit Tests for PII Detector (M4)

Tests PII detection at ingestion time.
"""

import pytest

from services.pii_detector import detect_pii


@pytest.mark.unit
def test_pii_detector_flags_ssn():
    result = detect_pii("My SSN is 123-45-6789")
    assert "ssn" in result.types
    assert result.has_pii is True


@pytest.mark.unit
def test_pii_detector_clean_text():
    result = detect_pii("Normal technical documentation about Python")
    assert len(result.types) == 0
    assert result.has_pii is False


@pytest.mark.unit
def test_pii_detector_flags_credit_card():
    result = detect_pii("Card number: 4111-1111-1111-1111")
    assert "credit_card" in result.types
    assert result.has_pii is True


@pytest.mark.unit
def test_pii_detector_flags_email():
    result = detect_pii("Contact us at support@example.com")
    assert "email" in result.types
    assert result.has_pii is True


@pytest.mark.unit
def test_pii_detector_flags_phone():
    result = detect_pii("Call us at (555) 123-4567")
    assert "phone_us" in result.types
    assert result.has_pii is True


@pytest.mark.unit
def test_pii_detector_empty_text():
    result = detect_pii("")
    assert result.has_pii is False
    assert len(result.types) == 0


@pytest.mark.unit
def test_pii_detector_none_text():
    result = detect_pii(None)
    assert result.has_pii is False
    assert len(result.types) == 0


@pytest.mark.unit
def test_pii_detector_multiple_types():
    result = detect_pii("SSN 123-45-6789 and email test@example.com")
    assert "ssn" in result.types
    assert "email" in result.types
    assert len(result.types) >= 2
    assert result.has_pii is True


@pytest.mark.unit
def test_pii_detector_whitespace_only():
    result = detect_pii("   ")
    assert result.has_pii is False
    assert len(result.types) == 0
