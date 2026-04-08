"""
Post-generation faithfulness guard for RAG responses.

This module checks whether the model answer is supported by the retrieved
document excerpts. It is deliberately fail-open: chat responses must not fail
just because the judge model is unavailable or returns malformed JSON.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass, field
from typing import Any

from core.config import settings
from services.guardrails import guardrail_service

logger = logging.getLogger(__name__)

FAITHFULNESS_PROMPT = """You are a strict faithfulness checker for a RAG system.
Your job is to compare the ANSWER against the SOURCE EXCERPTS and determine
whether the answer makes claims that are unsupported, contradicted, or overly
specific relative to the sources.

Rules:
- Judge only against the SOURCE EXCERPTS below.
- Ignore style, tone, and harmless paraphrasing.
- Mark faithful=true only when the answer is fully supported by the sources.
- If there are unsupported claims, set faithful=false.
- score must be a number between 0 and 1 where 1.0 means fully supported.
- unsupported_claims must be a short array of the most important unsupported claims.
- Respond with JSON only.

SOURCE EXCERPTS:
{context}

ANSWER:
{answer}

Return JSON:
{{
  "faithful": true,
  "score": 1.0,
  "unsupported_claims": [],
  "reason": "short explanation"
}}
"""


@dataclass
class FaithfulnessResult:
    """Normalized result of the post-generation faithfulness check."""

    checked: bool = False
    faithful: bool = True
    score: float = 0.5
    unsupported_claims: list[str] = field(default_factory=list)
    reason: str | None = None
    warning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FaithfulnessGuard:
    """Thin wrapper around the shared guardrail model for answer support checks."""

    def __init__(self) -> None:
        self.timeout_seconds = float(getattr(settings, "FAITHFULNESS_GUARD_TIMEOUT", 10))
        self.threshold = float(getattr(settings, "FAITHFULNESS_GUARD_THRESHOLD", 0.65))
        self.max_docs = int(getattr(settings, "FAITHFULNESS_GUARD_MAX_DOCS", 5))
        self.max_excerpt_chars = int(getattr(settings, "FAITHFULNESS_GUARD_MAX_EXCERPT_CHARS", 900))
        self.max_answer_chars = int(getattr(settings, "FAITHFULNESS_GUARD_MAX_ANSWER_CHARS", 1800))

    def _build_context(self, docs: list[dict[str, Any]]) -> str:
        excerpts: list[str] = []
        for idx, doc in enumerate(docs[: self.max_docs], start=1):
            content = (doc.get("content", "") or "").strip()
            if not content:
                continue
            title = doc.get("title") or (doc.get("metadata") or {}).get("title") or f"Document {idx}"
            excerpts.append(f"[{idx}] {title}\n{content[: self.max_excerpt_chars]}")
        return "\n\n---\n\n".join(excerpts)

    def _normalize(self, data: dict[str, Any]) -> FaithfulnessResult:
        faithful = bool(data.get("faithful", True))
        score_raw = data.get("score", 0.5)
        try:
            score = max(0.0, min(1.0, float(score_raw)))
        except (TypeError, ValueError):
            score = 0.5

        unsupported_raw = data.get("unsupported_claims") or []
        if isinstance(unsupported_raw, list):
            unsupported_claims = [str(item).strip() for item in unsupported_raw if str(item).strip()]
        else:
            unsupported_claims = []

        reason = data.get("reason")
        if reason is not None:
            reason = str(reason).strip() or None

        warning = None
        if not faithful or score < self.threshold:
            warning = (
                "Some parts of this answer may not be fully supported by the retrieved sources."
            )

        return FaithfulnessResult(
            checked=True,
            faithful=faithful,
            score=score,
            unsupported_claims=unsupported_claims,
            reason=reason,
            warning=warning,
        )

    async def check(
        self,
        *,
        answer: str,
        docs: list[dict[str, Any]],
    ) -> FaithfulnessResult:
        """Check whether the generated answer is supported by retrieved docs."""
        if not getattr(settings, "FAITHFULNESS_GUARD_ENABLED", True):
            return FaithfulnessResult()

        context = self._build_context(docs)
        if not context or not (answer or "").strip():
            return FaithfulnessResult()

        prompt = FAITHFULNESS_PROMPT.format(
            context=context,
            answer=(answer or "").strip()[: self.max_answer_chars],
        )

        try:
            raw = await asyncio.wait_for(
                guardrail_service.run_json_prompt(prompt),
                timeout=self.timeout_seconds,
            )
            if not isinstance(raw, dict):
                logger.warning("[Faithfulness] Guardrail JSON runner returned non-dict payload")
                return FaithfulnessResult()
            result = self._normalize(raw)
            if result.warning:
                logger.warning(
                    "[Faithfulness] Unsupported answer detected score=%.2f claims=%s",
                    result.score,
                    result.unsupported_claims[:3],
                )
            return result
        except Exception as e:
            logger.warning("[Faithfulness] Check failed, failing open: %s", e)
            return FaithfulnessResult(checked=True)


faithfulness_guard = FaithfulnessGuard()
