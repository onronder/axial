"""
Smart Router Service

Selects the optimal LLM based on user's subscription plan and query complexity.

Decision Matrix:
┌──────────────────┬─────────────┬──────────────────────────────────────┐
│ Plan             │ Complexity  │ Model Selection                      │
├──────────────────┼─────────────┼──────────────────────────────────────┤
│ free / starter   │ ANY         │ groq/llama-3.3-70b-versatile (speed) │
│ pro / enterprise │ SIMPLE      │ groq/llama-3.3-70b-versatile (speed) │
│ pro / enterprise │ COMPLEX     │ openai/gpt-4o (intelligence)         │
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
    - User's subscription plan (free, starter, pro, enterprise)
    - Query complexity (SIMPLE, COMPLEX)
    
    Strategy:
    - Free/Starter users: Always use fast Groq model (cost optimization)
    - Pro/Enterprise users: Use GPT-4o for complex queries (intelligence optimization)
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
    
    # Plans that get premium model access
    PREMIUM_PLANS = {"pro", "enterprise"}
    
    def select_model(
        self,
        plan: str,
        complexity: str
    ) -> ModelSelection:
        """
        Select the optimal model based on plan and complexity.
        
        Args:
            plan: User's subscription plan (free, starter, pro, enterprise)
            complexity: Query complexity from guardrails (SIMPLE, COMPLEX)
            
        Returns:
            ModelSelection with provider, model, and reason
        """
        plan_lower = plan.lower() if plan else "free"
        complexity_upper = complexity.upper() if complexity else "SIMPLE"
        
        # Free/Starter: Always use speed model
        if plan_lower not in self.PREMIUM_PLANS:
            logger.info(f"🚀 [Router] Plan={plan_lower} → Speed model (cost optimization)")
            return ModelSelection(
                provider=self.SPEED_MODEL["provider"],
                model=self.SPEED_MODEL["model"],
                reason=f"Free/Starter plan uses optimized speed model"
            )
        
        # Pro/Enterprise + SIMPLE: Use speed model
        if complexity_upper == "SIMPLE":
            logger.info(f"🚀 [Router] Plan={plan_lower}, Complexity=SIMPLE → Speed model")
            return ModelSelection(
                provider=self.SPEED_MODEL["provider"],
                model=self.SPEED_MODEL["model"],
                reason=f"Simple query routed to speed model"
            )
        
        # Pro/Enterprise + COMPLEX: Use intelligence model
        logger.info(f"🧠 [Router] Plan={plan_lower}, Complexity=COMPLEX → Intelligence model")
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
            ModelSelection with speed model (always for direct responses)
        """
        return ModelSelection(
            provider=self.SPEED_MODEL["provider"],
            model=self.SPEED_MODEL["model"],
            reason="Direct response uses speed model"
        )


# Singleton instance
llm_router = LLMRouter()
