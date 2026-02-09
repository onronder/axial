"""
LLM Factory Service

Centralized factory for instantiating LangChain Chat Models.
Supports multiple providers (OpenAI, Groq) with seamless switching.

PERFORMANCE FIX: Uses singleton/pool pattern to reuse LLM client instances
instead of creating new ones per-request (prevents connection overhead and
potential socket exhaustion under load).

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
import threading

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from core.config import settings

logger = logging.getLogger(__name__)

# Thread-safe client pool for LLM instances
# Key format: (provider, model_name, streaming)
_llm_client_pool: dict[tuple[str, str, bool], BaseChatModel] = {}
_llm_pool_lock = threading.Lock()


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
        max_tokens: int | None = None,
        allow_override: bool = False,
    ) -> tuple[BaseChatModel, dict]:
        """
        Smart Router: Returns (LLM, Metadata)

        Args:
            user_plan: 'free', 'starter', 'pro', 'enterprise'
            user_role: 'admin', 'member', 'viewer'
            requested_tier: 'fast' (Axio Fast) or 'smart' (Axio Pro)

        Returns:
            (llm_instance, metadata_dict)
            metadata example: {"upsell": True, "actual_tier": "fast"}
        """
        metadata = {"upsell": False, "actual_tier": requested_tier}
        plan_code = (user_plan or "free").lower()
        allowed_plans = {
            "free",
            settings.PLAN_STARTER,
            settings.PLAN_PRO,
            settings.PLAN_ENTERPRISE,
            settings.PLAN_ENTERPRISE_SMALL,
            settings.PLAN_ENTERPRISE_MEDIUM,
            settings.PLAN_ENTERPRISE_LARGE,
        }
        if plan_code not in allowed_plans:
            plan_code = "free"

        # --- 1. RESOLVE TIER & ENFORCE LIMITS ---

        target_tier = requested_tier

        # RULE: 'Viewer' role MUST use Fast model (Field Staff constraint)
        if user_role == "viewer":
            if target_tier == settings.MODEL_ALIAS_SMART:
                logger.info("🔒 [LLMFactory] Viewer Role Constraint: Downgrading to Fast")
                target_tier = settings.MODEL_ALIAS_FAST
                metadata["actual_tier"] = "fast"

        # RULE: Free/Starter plans MUST use Fast model
        if plan_code in {"free", settings.PLAN_STARTER}:
            if target_tier == settings.MODEL_ALIAS_SMART:
                logger.info(
                    "🔒 [LLMFactory] Plan Constraint: Downgrading %s to Fast (Upsell Triggered)",
                    plan_code,
                )
                target_tier = settings.MODEL_ALIAS_FAST
                metadata["upsell"] = True
                metadata["actual_tier"] = "fast"

        # --- 2. MAP TIER TO PROVIDER/ID ---

        final_provider = provider
        final_model = model_name
        explicit_override = allow_override and final_provider and final_model

        if not explicit_override:
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
            elif final_provider == "grok":
                llm = LLMFactory._create_grok(final_model, temperature, streaming, max_tokens)
            elif final_provider == "groq":
                llm = LLMFactory._create_groq(final_model, temperature, streaming, max_tokens)
            else:
                raise ValueError(f"Unsupported LLM provider: {final_provider}")

            metadata["provider"] = final_provider
            metadata["model"] = final_model
            return llm, metadata

        except Exception as e:
            logger.error(f"❌ [LLMFactory] Failed to initialize {final_provider}/{final_model}: {e}")
            raise

    # CLIENT POOLING: Create or retrieve pooled LLM instances
    # Temperature and max_tokens are set per-request via model.bind() if needed

    @staticmethod
    def _get_pool_key(provider: str, model_name: str, streaming: bool) -> tuple[str, str, bool]:
        """Generate cache key for client pool."""
        return (provider.lower(), model_name.lower(), streaming)

    @staticmethod
    def _get_pooled_openai(model_name: str, streaming: bool) -> ChatOpenAI:
        """Get or create pooled OpenAI client."""
        pool_key = LLMFactory._get_pool_key("openai", model_name, streaming)

        with _llm_pool_lock:
            if pool_key not in _llm_client_pool:
                logger.info(f"🔧 [LLMFactory] Creating pooled OpenAI client: {model_name} streaming={streaming}")
                _llm_client_pool[pool_key] = ChatOpenAI(
                    model=model_name,
                    temperature=0,  # Default, overridden per-request
                    streaming=streaming,
                    api_key=settings.OPENAI_API_KEY,
                    request_timeout=settings.LLM_REQUEST_TIMEOUT if hasattr(settings, 'LLM_REQUEST_TIMEOUT') else 120,
                )
            return _llm_client_pool[pool_key]

    @staticmethod
    def _get_pooled_grok(model_name: str, streaming: bool) -> ChatOpenAI:
        """Get or create pooled Grok client."""
        if not settings.GROK_API_KEY:
            raise ValueError("GROK_API_KEY not configured.")

        pool_key = LLMFactory._get_pool_key("grok", model_name, streaming)

        with _llm_pool_lock:
            if pool_key not in _llm_client_pool:
                logger.info(f"🔧 [LLMFactory] Creating pooled Grok client: {model_name} streaming={streaming}")
                _llm_client_pool[pool_key] = ChatOpenAI(
                    model=model_name,
                    temperature=0,
                    streaming=streaming,
                    api_key=settings.GROK_API_KEY,
                    base_url=settings.GROK_BASE_URL,
                    request_timeout=settings.LLM_REQUEST_TIMEOUT if hasattr(settings, 'LLM_REQUEST_TIMEOUT') else 120,
                )
            return _llm_client_pool[pool_key]

    @staticmethod
    def _get_pooled_groq(model_name: str, streaming: bool) -> BaseChatModel:
        """Get or create pooled Groq client."""
        try:
            from langchain_groq import ChatGroq
        except ImportError:
            raise ImportError("langchain-groq package not installed")

        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not configured.")

        pool_key = LLMFactory._get_pool_key("groq", model_name, streaming)

        with _llm_pool_lock:
            if pool_key not in _llm_client_pool:
                logger.info(f"🔧 [LLMFactory] Creating pooled Groq client: {model_name} streaming={streaming}")
                _llm_client_pool[pool_key] = ChatGroq(
                    model_name=model_name,
                    temperature=0,
                    api_key=settings.GROQ_API_KEY,
                    streaming=streaming,
                    request_timeout=settings.LLM_REQUEST_TIMEOUT if hasattr(settings, 'LLM_REQUEST_TIMEOUT') else 120,
                )
            return _llm_client_pool[pool_key]

    @staticmethod
    def _create_openai(model_name, temperature, streaming, max_tokens) -> ChatOpenAI:
        """Create OpenAI client with per-request settings using pooled base client."""
        base_client = LLMFactory._get_pooled_openai(model_name, streaming)

        # Use .bind() or create new instance with specific settings
        # For temperature/max_tokens that vary per request, we need to bind
        bind_kwargs = {"temperature": temperature}
        if max_tokens:
            bind_kwargs["max_tokens"] = max_tokens

        # Return bound client with specific temperature/max_tokens
        return base_client.bind(**bind_kwargs) if bind_kwargs else base_client

    @staticmethod
    def _create_grok(model_name, temperature, streaming, max_tokens) -> ChatOpenAI:
        """Create Grok client with per-request settings using pooled base client."""
        base_client = LLMFactory._get_pooled_grok(model_name, streaming)

        bind_kwargs = {"temperature": temperature}
        if max_tokens:
            bind_kwargs["max_tokens"] = max_tokens

        return base_client.bind(**bind_kwargs) if bind_kwargs else base_client

    @staticmethod
    def _create_groq(model_name, temperature, streaming, max_tokens) -> BaseChatModel:
        """Create Groq client with per-request settings using pooled base client."""
        base_client = LLMFactory._get_pooled_groq(model_name, streaming)

        bind_kwargs = {"temperature": temperature}
        if max_tokens:
            bind_kwargs["max_tokens"] = max_tokens

        return base_client.bind(**bind_kwargs) if bind_kwargs else base_client


def get_llm_pool_stats() -> dict[str, int]:
    """Get statistics about the LLM client pool."""
    with _llm_pool_lock:
        return {
            "total_clients": len(_llm_client_pool),
            "clients": list(_llm_client_pool.keys()),
        }


def clear_llm_pool():
    """Clear the LLM client pool (useful for testing or shutdown)."""
    global _llm_client_pool
    with _llm_pool_lock:
        _llm_client_pool.clear()
        logger.info("🧹 [LLMFactory] Cleared LLM client pool")

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
