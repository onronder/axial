"""
Smart Router Service

Selects the optimal LLM based on user's subscription plan and query complexity.
Uses centralized plan definitions from core.quotas for strict enforcement.

Model Tier Enforcement:
┌──────────────────┬─────────────┬──────────────────────────────────────┐
│ Model Tier       │ Complexity  │ Model Selection                      │
├──────────────────┼─────────────┼──────────────────────────────────────┤
│ BASIC            │ ANY         │ openai/gpt-4o-mini (ALWAYS)          │
│ HYBRID           │ SIMPLE      │ openai/gpt-4o-mini (speed)           │
│ HYBRID           │ COMPLEX     │ openai/gpt-4o (intelligence)         │
│ PREMIUM          │ ANY         │ openai/gpt-4o (best quality)         │
└──────────────────┴─────────────┴──────────────────────────────────────┘

Usage:
    from services.router import llm_router

    model_config = llm_router.select_model(plan="pro", complexity="COMPLEX")
    # {"provider": "openai", "model": "gpt-4o"}
"""

import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass

from core.config import settings
from core.quotas import get_plan_limits
from core.resilience import openai_breaker

# Refactored to use get_plan_limits exclusively

logger = logging.getLogger(__name__)


@dataclass
class ModelSelection:
    """Result of model selection."""
    provider: str
    model: str
    reason: str


class ComplexityEvaluator:
    """Lightweight intent override for routing."""

    FORCE_PRO_KEYWORDS = ("refactor", "architect", "optimize")

    @classmethod
    def should_force_pro(cls, prompt: str | None) -> bool:
        if not prompt:
            return False
        lowered = prompt.lower()
        for keyword in cls.FORCE_PRO_KEYWORDS:
            if re.search(rf"\\b{re.escape(keyword)}\\b", lowered):
                return True
        return False


class LLMRouter:
    """
    Smart router for selecting the optimal LLM based on:
    - User's subscription plan model tier (standard, premium)
    - Query complexity (SIMPLE, COMPLEX)

    Strategy:
    - STANDARD tier (Free/Starter): ALWAYS use Speed Model (strict cost gate)
    - PREMIUM tier (Pro/Enterprise): Smart routing based on complexity
    """

    # Model configurations
    SPEED_MODEL = {
        "provider": settings.SECONDARY_MODEL_PROVIDER,  # openai
        "model": settings.SECONDARY_MODEL_NAME,  # gpt-4o-mini
    }

    INTELLIGENCE_MODEL = {
        "provider": settings.PRIMARY_MODEL_PROVIDER,  # openai
        "model": settings.PRIMARY_MODEL_NAME,  # gpt-4o
    }

    def __init__(self) -> None:
        self._fallback_index = 0

    def select_model(
        self,
        plan: str,
        complexity: str,
        query_text: str | None = None,
    ) -> ModelSelection:
        """
        Select the optimal model based on plan's model tier and complexity.

        Args:
            plan: User's subscription plan (free, starter, pro, enterprise)
            complexity: Query complexity from guardrails (SIMPLE, COMPLEX)

        Returns:
            ModelSelection with provider, model, and reason
        """
        plan_lower = plan.lower() if plan else "free"
        force_pro = ComplexityEvaluator.should_force_pro(query_text)
        complexity_upper = "COMPLEX" if force_pro else (complexity.upper() if complexity else "SIMPLE")

        # Get model tier from centralized plan configuration
        try:
            limits = get_plan_limits(plan_lower)
            model_tier = limits.model_tier # "standard" or "premium"
        except ValueError:
            # Unknown plan, default to standard (safest)
            logger.warning(f"⚠️ [Router] Unknown plan '{plan_lower}', defaulting to STANDARD tier")
            model_tier = "standard"

        # ================================================================
        # STRICT MODEL TIER ENFORCEMENT
        # ================================================================

        # STANDARD tier: ALWAYS use speed model (no GPT-4o access ever)
        if model_tier == "standard":
            logger.info(f"🚀 [Router] Plan={plan_lower}, Tier=STANDARD → Speed model (strict gate)")
            return ModelSelection(
                provider=self.SPEED_MODEL["provider"],
                model=self.SPEED_MODEL["model"],
                reason="Standard tier uses the fast model for all queries (upgrade for GPT-4o access)"
            )

        # PREMIUM tier: Smart routing or Priority
        # Use simple heuristic for now: Pro/Enterprise get hybrid routing

        if complexity_upper == "SIMPLE":
            logger.info(f"🚀 [Router] Plan={plan_lower}, Tier=PREMIUM, Complexity=SIMPLE → Speed model")
            return ModelSelection(
                provider=self.SPEED_MODEL["provider"],
                model=self.SPEED_MODEL["model"],
                reason="Simple query routed to speed model efficiently"
            )

        # PREMIUM + COMPLEX: Use intelligence model
        logger.info(f"🧠 [Router] Plan={plan_lower}, Tier=PREMIUM, Complexity=COMPLEX → Intelligence model")
        reason = "Complex query routed to GPT-4o for best results"
        if force_pro:
            reason = "Intent keyword forced smart routing"
        return ModelSelection(
            provider=self.INTELLIGENCE_MODEL["provider"],
            model=self.INTELLIGENCE_MODEL["model"],
            reason=reason
        )

    def get_model_for_plan(self, plan: str) -> ModelSelection:
        """
        Get the default model for a plan (for non-RAG responses).

        Args:
            plan: User's subscription plan

        Returns:
            ModelSelection based on plan's model tier
        """
        plan_lower = plan.lower() if plan else "free"

        try:
            limits = get_plan_limits(plan_lower)
            model_tier = limits.model_tier
        except ValueError:
            model_tier = "standard"

        # For non-RAG responses, use speed model unless explicitly Premium-only behavior is desired
        # Generally chat uses select_model, this is a fallback.

        return ModelSelection(
            provider=self.SPEED_MODEL["provider"],
            model=self.SPEED_MODEL["model"],
            reason="Default speed model for responses"
        )

    def is_provider_available(self, provider: str) -> bool:
        """Check circuit-breaker availability for providers."""
        return not (provider == "openai" and openai_breaker.state == "open")

    def _rotate(self, items: Sequence[ModelSelection]) -> list[ModelSelection]:
        if not items:
            return []
        if not settings.LLM_LOAD_BALANCE or len(items) == 1:
            return list(items)
        self._fallback_index = (self._fallback_index + 1) % len(items)
        return list(items[self._fallback_index:] + items[:self._fallback_index])

    def get_fallback_models(self) -> list[ModelSelection]:
        """Return ordered fallback models for failover routing."""
        fallbacks: list[ModelSelection] = []
        if settings.GROK_API_KEY and settings.GROK_MODEL_NAME:
            fallbacks.append(
                ModelSelection(
                    provider="grok",
                    model=settings.GROK_MODEL_NAME,
                    reason="Fallback to Grok (OpenAI-compatible)",
                )
            )
        if settings.GROQ_API_KEY:
            fallbacks.append(
                ModelSelection(
                    provider="groq",
                    model=settings.GROQ_CHAT_MODEL_NAME or settings.GUARDRAIL_MODEL_NAME,
                    reason="Fallback to Groq",
                )
            )
        return self._rotate(fallbacks)

# Singleton instance
llm_router = LLMRouter()
