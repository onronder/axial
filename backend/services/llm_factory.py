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
        provider: str,
        model_name: str,
        temperature: float = 0,
        streaming: bool = False,
        max_tokens: Optional[int] = None,
    ) -> BaseChatModel:
        """
        Returns a configured LangChain Chat Model.
        
        Args:
            provider: 'openai' or 'groq'
            model_name: Specific model identifier (e.g., 'gpt-4o', 'llama-3.3-70b-versatile')
            temperature: Creativity level (default 0 for factual RAG)
            streaming: Enable streaming output
            max_tokens: Optional max tokens limit
            
        Returns:
            Configured BaseChatModel instance
            
        Raises:
            ValueError: If provider is unsupported or API key is missing
        """
        try:
            if provider == "openai":
                return LLMFactory._create_openai(model_name, temperature, streaming, max_tokens)
            
            elif provider == "groq":
                return LLMFactory._create_groq(model_name, temperature, streaming, max_tokens)
            
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")

        except Exception as e:
            logger.error(f"❌ [LLMFactory] Failed to initialize {provider}/{model_name}: {e}")
            raise

    @staticmethod
    def _create_openai(
        model_name: str,
        temperature: float,
        streaming: bool,
        max_tokens: Optional[int]
    ) -> ChatOpenAI:
        """Create OpenAI chat model."""
        kwargs = {
            "model": model_name,
            "temperature": temperature,
            "streaming": streaming,
            "api_key": settings.OPENAI_API_KEY,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
            
        return ChatOpenAI(**kwargs)

    @staticmethod
    def _create_groq(
        model_name: str,
        temperature: float,
        streaming: bool,
        max_tokens: Optional[int]
    ) -> BaseChatModel:
        """Create Groq chat model (Llama 3.x via Groq Cloud)."""
        # Lazy import to avoid errors if groq not installed
        try:
            from langchain_groq import ChatGroq
        except ImportError:
            logger.error("❌ [LLMFactory] langchain-groq not installed. Run: pip install langchain-groq")
            raise ImportError("langchain-groq package not installed")
        
        if not settings.GROQ_API_KEY:
            logger.error("❌ [LLMFactory] GROQ_API_KEY not configured")
            raise ValueError("GROQ_API_KEY not configured. Add it to .env file.")
        
        kwargs = {
            "model_name": model_name,
            "temperature": temperature,
            "api_key": settings.GROQ_API_KEY,
            "streaming": streaming,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
            
        return ChatGroq(**kwargs)

    @staticmethod
    def get_primary_model(streaming: bool = False, temperature: float = 0) -> BaseChatModel:
        """Convenience method for primary model (GPT-4o by default)."""
        return LLMFactory.get_model(
            provider=settings.PRIMARY_MODEL_PROVIDER,
            model_name=settings.PRIMARY_MODEL_NAME,
            temperature=temperature,
            streaming=streaming,
        )

    @staticmethod
    def get_secondary_model(streaming: bool = False, temperature: float = 0) -> BaseChatModel:
        """Convenience method for secondary model (Groq Llama by default)."""
        return LLMFactory.get_model(
            provider=settings.SECONDARY_MODEL_PROVIDER,
            model_name=settings.SECONDARY_MODEL_NAME,
            temperature=temperature,
            streaming=streaming,
        )

    @staticmethod
    def get_guardrail_model(streaming: bool = False, temperature: float = 0) -> BaseChatModel:
        """Convenience method for guardrail model (fast validation checks)."""
        return LLMFactory.get_model(
            provider=settings.GUARDRAIL_MODEL_PROVIDER,
            model_name=settings.GUARDRAIL_MODEL_NAME,
            temperature=temperature,
            streaming=streaming,
        )
