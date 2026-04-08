from types import SimpleNamespace

import services.language_detector as language_detector_module
from core.config import settings
from services.language_detector import LanguageDetector


def _set_language_detector_defaults(monkeypatch):
    monkeypatch.setattr(settings, "LANGUAGE_DETECTION_ENABLED", True)
    monkeypatch.setattr(settings, "LANGUAGE_DETECTION_MIN_CHARS", 30)
    monkeypatch.setattr(settings, "LANGUAGE_DETECTION_MIN_CONFIDENCE", 0.60)
    language_detector_module._load_fast_langdetect_module.cache_clear()


def test_detect_returns_iso_639_1_code(monkeypatch):
    _set_language_detector_defaults(monkeypatch)
    monkeypatch.setattr(
        language_detector_module,
        "_load_fast_langdetect_module",
        lambda: SimpleNamespace(detect=lambda *args, **kwargs: {"lang": "tr", "score": 0.99}),
    )

    detector = LanguageDetector()

    assert detector.detect("Merhaba dunya bu yeterince uzun bir metindir.") == "tr"


def test_detect_normalizes_regional_code(monkeypatch):
    _set_language_detector_defaults(monkeypatch)
    monkeypatch.setattr(
        language_detector_module,
        "_load_fast_langdetect_module",
        lambda: SimpleNamespace(detect=lambda *args, **kwargs: {"lang": "pt-BR", "score": 0.95}),
    )

    detector = LanguageDetector()

    assert detector.detect("Ola mundo este texto e suficientemente longo.") == "pt"


def test_detect_returns_none_when_disabled(monkeypatch):
    _set_language_detector_defaults(monkeypatch)
    monkeypatch.setattr(settings, "LANGUAGE_DETECTION_ENABLED", False)

    detector = LanguageDetector()

    assert detector.detect("This text should never reach the detector path.") is None


def test_detect_returns_none_for_short_text(monkeypatch):
    _set_language_detector_defaults(monkeypatch)

    detector = LanguageDetector()

    assert detector.detect("too short") is None


def test_detect_returns_none_for_low_confidence(monkeypatch):
    _set_language_detector_defaults(monkeypatch)
    monkeypatch.setattr(
        language_detector_module,
        "_load_fast_langdetect_module",
        lambda: SimpleNamespace(detect=lambda *args, **kwargs: {"lang": "en", "score": 0.42}),
    )

    detector = LanguageDetector()

    assert detector.detect("This sample is long enough but intentionally low confidence.") is None


def test_detect_returns_none_when_package_missing(monkeypatch):
    _set_language_detector_defaults(monkeypatch)
    monkeypatch.setattr(language_detector_module, "_load_fast_langdetect_module", lambda: None)

    detector = LanguageDetector()

    assert detector.detect("This sample is long enough for a normal detection call.") is None


def test_detect_returns_none_when_detector_raises(monkeypatch):
    _set_language_detector_defaults(monkeypatch)

    def _raise(*args, **kwargs):
        raise RuntimeError("detector boom")

    monkeypatch.setattr(
        language_detector_module,
        "_load_fast_langdetect_module",
        lambda: SimpleNamespace(detect=_raise),
    )

    detector = LanguageDetector()

    assert detector.detect("This sample is long enough to exercise the exception path.") is None


def test_detect_falls_back_to_detect_langs(monkeypatch):
    _set_language_detector_defaults(monkeypatch)
    monkeypatch.setattr(
        language_detector_module,
        "_load_fast_langdetect_module",
        lambda: SimpleNamespace(detect_langs=lambda *args, **kwargs: [{"lang": "de", "score": 0.88}]),
    )

    detector = LanguageDetector()

    assert detector.detect("Hallo welt dieser text ist lang genug fuer die erkennung.") == "de"
