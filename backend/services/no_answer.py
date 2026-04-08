"""Deterministic no-answer helpers for low-context RAG requests."""

from typing import Any

NO_ANSWER_MESSAGE = (
    "Dokumanlarda bu soruyla ilgili yeterli bilgi bulunamadi. "
    "Farkli bir arama terimi deneyebilir veya ilgili kaynaklari baglayabilirsiniz."
)


def _doc_score(doc: dict[str, Any]) -> float:
    score = doc.get("vector_score", doc.get("similarity", 0))
    try:
        return float(score)
    except (TypeError, ValueError):
        return 0.0


def should_return_no_answer(docs: list[dict[str, Any]], threshold: float) -> bool:
    """Return True when no retrieved document clears the quality threshold."""
    if not docs:
        return True
    return not any(_doc_score(doc) >= threshold for doc in docs)


def build_no_answer_payload() -> dict[str, Any]:
    """Return the shared no-answer payload for chat responses."""
    return {
        "answer": NO_ANSWER_MESSAGE,
        "sources": [],
    }
