"""
Best-effort language detection for ingest-time chunk metadata.

Stores ISO 639-1 language codes in document_chunks.language without changing
the active FTS strategy, which remains globally normalized to `simple`.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from core.config import settings

logger = logging.getLogger(__name__)

_MAX_SAMPLE_CHARS = 4000


def _normalize_language_code(value: Any) -> str | None:
    if value is None:
        return None

    code = str(value).strip().lower()
    if not code:
        return None

    if code.startswith("__label__"):
        code = code.removeprefix("__label__")

    code = code.replace("_", "-")
    base_code = code.split("-", 1)[0]
    if len(base_code) == 2 and base_code.isalpha():
        return base_code
    return None


def _coerce_score(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_detection(result: Any) -> tuple[str | None, float | None]:
    if result is None:
        return None, None

    if isinstance(result, list):
        if not result:
            return None, None
        return _extract_detection(result[0])

    if isinstance(result, tuple):
        if len(result) >= 2:
            return _normalize_language_code(result[0]), _coerce_score(result[1])
        if len(result) == 1:
            return _normalize_language_code(result[0]), None
        return None, None

    if isinstance(result, str):
        return _normalize_language_code(result), None

    if isinstance(result, dict):
        language = None
        score = None
        for key in ("lang", "language", "code", "label"):
            if key in result and result[key] is not None:
                language = result[key]
                break
        for key in ("score", "confidence", "prob", "probability"):
            if key in result and result[key] is not None:
                score = result[key]
                break
        return _normalize_language_code(language), _coerce_score(score)

    language = None
    score = None
    for attr in ("lang", "language", "code", "label"):
        value = getattr(result, attr, None)
        if value is not None:
            language = value
            break
    for attr in ("score", "confidence", "prob", "probability"):
        value = getattr(result, attr, None)
        if value is not None:
            score = value
            break
    return _normalize_language_code(language), _coerce_score(score)


@lru_cache(maxsize=1)
def _load_fast_langdetect_module() -> Any | None:
    try:
        import fast_langdetect
    except ImportError:
        logger.warning("Language detection disabled: fast-langdetect is not installed")
        return None

    return fast_langdetect


class LanguageDetector:
    def detect(self, text: str | None) -> str | None:
        if not settings.LANGUAGE_DETECTION_ENABLED:
            return None

        normalized_text = " ".join((text or "").split())
        if len(normalized_text) < settings.LANGUAGE_DETECTION_MIN_CHARS:
            return None

        module = _load_fast_langdetect_module()
        if module is None:
            return None

        sample = normalized_text[:_MAX_SAMPLE_CHARS]

        try:
            result, variant = self._run_detection(module, sample)
        except Exception as exc:
            logger.warning(
                "Language detection failed: error_type=%s text_len=%s",
                type(exc).__name__,
                len(sample),
            )
            return None

        logger.debug(
            "Language detection succeeded via %s (fast-langdetect=%s)",
            variant,
            getattr(module, "__version__", "unknown"),
        )

        language, confidence = _extract_detection(result)
        if language is None:
            return None

        if confidence is not None and confidence < settings.LANGUAGE_DETECTION_MIN_CONFIDENCE:
            return None

        return language

    def _run_detection(self, module: Any, text: str) -> tuple[Any, str]:
        detect_fn = getattr(module, "detect", None)
        if callable(detect_fn):
            call_variants = (
                ("detect(text, model='lite', k=1)", (text,), {"model": "lite", "k": 1}),
                ("detect(text, model='lite')", (text,), {"model": "lite"}),
                ("detect(text, low_memory=True)", (text,), {"low_memory": True}),
                ("detect(text=<text>, model='lite', k=1)", (), {"text": text, "model": "lite", "k": 1}),
                ("detect(text=<text>, model='lite')", (), {"text": text, "model": "lite"}),
                ("detect(text=<text>, low_memory=True)", (), {"text": text, "low_memory": True}),
            )
            for variant_name, args, kwargs in call_variants:
                try:
                    return detect_fn(*args, **kwargs), variant_name
                except TypeError:
                    continue

        detect_langs_fn = getattr(module, "detect_langs", None)
        if callable(detect_langs_fn):
            call_variants = (
                ("detect_langs(text, low_memory=True)", (text,), {"low_memory": True}),
                ("detect_langs(text)", (text,), {}),
                ("detect_langs(text=<text>, low_memory=True)", (), {"text": text, "low_memory": True}),
                ("detect_langs(text=<text>)", (), {"text": text}),
            )
            for variant_name, args, kwargs in call_variants:
                try:
                    return detect_langs_fn(*args, **kwargs), variant_name
                except TypeError:
                    continue

        raise RuntimeError("fast-langdetect does not expose a compatible detect API")


language_detector = LanguageDetector()
