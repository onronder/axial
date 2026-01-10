import pytest

from core.ingestion_utils import require_canonical_provider


def test_require_canonical_provider_requires_value():
    with pytest.raises(ValueError) as exc:
        require_canonical_provider(None)
    assert "provider is required" in str(exc.value)


def test_require_canonical_provider_rejects_deprecated():
    with pytest.raises(ValueError) as exc:
        require_canonical_provider("drive")
    assert "Deprecated provider value" in str(exc.value)


def test_require_canonical_provider_rejects_unsupported():
    with pytest.raises(ValueError) as exc:
        require_canonical_provider("dropbox")
    assert "Unsupported provider value" in str(exc.value)
