"""
Smart Router Service

Selects the optimal LLM based on user's subscription plan and query complexity.
Uses centralized plan definitions from core.quotas for strict enforcement.

Model Tier Enforcement:
┌──────────────────┬─────────────┬──────────────────────────────────────┐
│ Model Tier       │ Complexity  │ Model Selection                      │
├──────────────────┼─────────────┼──────────────────────────────────────┤
│ BASIC            │ ANY         │ groq/llama-3.3-70b-versatile (ALWAYS)│
│ HYBRID           │ SIMPLE      │ groq/llama-3.3-70b-versatile (speed) │
│ HYBRID           │ COMPLEX     │ openai/gpt-4o (intelligence)         │
│ PREMIUM          │ ANY         │ openai/gpt-4o (best quality)         │
└──────────────────┴─────────────┴──────────────────────────────────────┘

Usage:
    from services.router import llm_router
    
    model_config = llm_router.select_model(plan="pro", complexity="COMPLEX")
    # {"provider": "openai", "model": "gpt-4o"}
"""

import logging
from dataclasses import dataclass
from typing import Literal

from core.config import settings
from core.quotas import get_plan_limits

logger = logging.getLogger(__name__)


@dataclass
class ModelSelection:
    """Result of model selection."""
    provider: str
    model: str
    reason: str


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
        "provider": settings.SECONDARY_MODEL_PROVIDER,  # groq
        "model": settings.SECONDARY_MODEL_NAME,  # llama-3.3-70b-versatile
    }
    
    INTELLIGENCE_MODEL = {
        "provider": settings.PRIMARY_MODEL_PROVIDER,  # openai
        "model": settings.PRIMARY_MODEL_NAME,  # gpt-4o
    }
    
    def select_model(
        self,
        plan: str,
        complexity: str
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
        complexity_upper = complexity.upper() if complexity else "SIMPLE"
        
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
                reason=f"Standard tier uses Llama-3 for all queries (upgrade for GPT-4o access)"
            )
        
        # PREMIUM tier: Smart routing or Priority
        # Use simple heuristic for now: Pro/Enterprise get hybrid routing
        
        if complexity_upper == "SIMPLE":
            logger.info(f"🚀 [Router] Plan={plan_lower}, Tier=PREMIUM, Complexity=SIMPLE → Speed model")
            return ModelSelection(
                provider=self.SPEED_MODEL["provider"],
                model=self.SPEED_MODEL["model"],
                reason=f"Simple query routed to speed model efficiently"
            )
        
        # PREMIUM + COMPLEX: Use intelligence model
        logger.info(f"🧠 [Router] Plan={plan_lower}, Tier=PREMIUM, Complexity=COMPLEX → Intelligence model")
        return ModelSelection(
            provider=self.INTELLIGENCE_MODEL["provider"],
            model=self.INTELLIGENCE_MODEL["model"],
            reason=f"Complex query routed to GPT-4o for best results"
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
    
# Singleton instance
llm_router = LLMRouter()
