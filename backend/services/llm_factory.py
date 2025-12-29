"""
LLM Factory Service

Centralized factory for instantiating LangChain Chat Models.
Supports multiple providers (OpenAI, Groq) with seamless switching.

Usage:
    from services.llm_factory import LLMFactory
    from core.config import settings
    
    # Get primary model (GPT-4o)
    llm = LLMFactory.get_model(
        provider=settings.PRIMARY_MODEL_PROVIDER,
        model_name=settings.PRIMARY_MODEL_NAME
    )
    
    # Get fast model (Groq Llama)
    fast_llm = LLMFactory.get_model(
        provider=settings.SECONDARY_MODEL_PROVIDER,
        model_name=settings.SECONDARY_MODEL_NAME
    )
"""

import logging
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel
from core.config import settings

logger = logging.getLogger(__name__)


class LLMFactory:
    """
    Factory class to instantiate LLM models based on provider configuration.
    
    Supported Providers:
    - openai: GPT-4o, GPT-3.5-turbo, etc.
    - groq: Llama 3.3 70B, Llama 3.1 8B (ultra-fast inference)
    
    Example:
        llm = LLMFactory.get_model("openai", "gpt-4o", streaming=True)
    """

    @staticmethod
    def get_model(
        provider: str = None, # Legacy: inferred from tier if None
        model_name: str = None, # Legacy: inferred from tier if None
        user_plan: str = "free",
        user_role: str = "member",
        requested_tier: str = "fast", # "fast" or "smart"
        temperature: float = 0,
        streaming: bool = False,
        max_tokens: Optional[int] = None,
    ) -> tuple[BaseChatModel, dict]:
        """
        Smart Router: Returns (LLM, Metadata)
        
        Args:
            user_plan: 'free'/'starter', 'pro', 'enterprise'
            user_role: 'admin', 'member', 'viewer'
            requested_tier: 'fast' (Axio Fast) or 'smart' (Axio Pro)
            
        Returns:
            (llm_instance, metadata_dict)
            metadata example: {"upsell": True, "actual_tier": "fast"}
        """
        metadata = {"upsell": False, "actual_tier": requested_tier}
        
        # --- 1. RESOLVE TIER & ENFORCE LIMITS ---
        
        target_tier = requested_tier
        
        # RULE: 'Viewer' role MUST use Fast model (Field Staff constraint)
        if user_role == "viewer":
            if target_tier == settings.MODEL_ALIAS_SMART:
                logger.info(f"🔒 [LLMFactory] Viewer Role Constraint: Downgrading to Fast")
                target_tier = settings.MODEL_ALIAS_FAST
                metadata["actual_tier"] = "fast"
        
        # RULE: 'Starter'/'Free' plan MUST use Fast model
        if user_plan in ["free", "starter"]:
            if target_tier == settings.MODEL_ALIAS_SMART:
                logger.info(f"🔒 [LLMFactory] Plan Constraint: Downgrading {user_plan} to Fast (Upsell Triggered)")
                target_tier = settings.MODEL_ALIAS_FAST
                metadata["upsell"] = True
                metadata["actual_tier"] = "fast"
                
        # --- 2. MAP TIER TO PROVIDER/ID ---
        
        final_provider = provider
        final_model = model_name
        
        if target_tier == settings.MODEL_ALIAS_FAST:
            final_provider = settings.SECONDARY_MODEL_PROVIDER
            final_model = settings.SECONDARY_MODEL_NAME
        elif target_tier == settings.MODEL_ALIAS_SMART:
            final_provider = settings.PRIMARY_MODEL_PROVIDER
            final_model = settings.PRIMARY_MODEL_NAME
        else:
            # Fallback if specific model requested directly (Legacy support)
            if not final_provider or not final_model:
                # Default to Fast if unknown
                final_provider = settings.SECONDARY_MODEL_PROVIDER 
                final_model = settings.SECONDARY_MODEL_NAME

        # --- 3. INSTANTIATE ---
        
        try:
            if final_provider == "openai":
                llm = LLMFactory._create_openai(final_model, temperature, streaming, max_tokens)
            elif final_provider == "groq":
                llm = LLMFactory._create_groq(final_model, temperature, streaming, max_tokens)
            else:
                raise ValueError(f"Unsupported LLM provider: {final_provider}")
                
            return llm, metadata

        except Exception as e:
            logger.error(f"❌ [LLMFactory] Failed to initialize {final_provider}/{final_model}: {e}")
            raise
            
    # _create_openai and _create_groq methods remain unchanged...
    @staticmethod
    def _create_openai(model_name, temperature, streaming, max_tokens) -> ChatOpenAI:
        kwargs = {"model": model_name, "temperature": temperature, "streaming": streaming, "api_key": settings.OPENAI_API_KEY}
        if max_tokens: kwargs["max_tokens"] = max_tokens
        return ChatOpenAI(**kwargs)

    @staticmethod
    def _create_groq(model_name, temperature, streaming, max_tokens) -> BaseChatModel:
        try:
            from langchain_groq import ChatGroq
        except ImportError:
            raise ImportError("langchain-groq package not installed")
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not configured.")
        kwargs = {"model_name": model_name, "temperature": temperature, "api_key": settings.GROQ_API_KEY, "streaming": streaming}
        if max_tokens: kwargs["max_tokens"] = max_tokens
        return ChatGroq(**kwargs)

    # Convenience methods updated to use new signature if needed, or removed if obsolete.
    # We will keep them for backward compatibility but redirecting to get_model is safer.
    @staticmethod
    def get_primary_model(streaming: bool = False) -> BaseChatModel:
        llm, _ = LLMFactory.get_model(requested_tier=settings.MODEL_ALIAS_SMART, user_plan="pro", streaming=streaming)
        return llm

    @staticmethod
    def get_secondary_model(streaming: bool = False) -> BaseChatModel:
        llm, _ = LLMFactory.get_model(requested_tier=settings.MODEL_ALIAS_FAST, user_plan="pro", streaming=streaming)
        return llm

    @staticmethod
    def get_guardrail_model(streaming: bool = False, temperature: float = 0) -> BaseChatModel:
        # Guardrail always uses the specifically configured guardrail model, ignoring tiers
        return LLMFactory._create_groq(settings.GUARDRAIL_MODEL_NAME, temperature, streaming, None)
