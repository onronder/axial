"""
Embedding Factory for Multi-Model Routing

This module provides a tiered embedding strategy to optimize cost/performance:
- LOCAL: Free, uses HuggingFace BAAI/bge-small-en-v1.5
- STANDARD: Cheap, uses Mistral Embed (if available)
- PREMIUM: Best quality, uses OpenAI text-embedding-3-small

Usage:
    from core.embeddings import EmbeddingFactory, EmbeddingTier

    # Explicit tier selection
    embeddings = EmbeddingFactory.get_embeddings(EmbeddingTier.LOCAL)

    # Automatic tier selection based on volume and priority
    tier = EmbeddingFactory.auto_select(doc_count=500, priority="normal")
    embeddings = EmbeddingFactory.get_embeddings(tier)
"""

import logging
from enum import Enum

from core.config import settings

logger = logging.getLogger(__name__)

# C1 SAFETY: All vectors in the DB index are vector(1536).
# Any embedding tier producing a different dimension will corrupt search results.
REQUIRED_DIMENSION = 1536


class EmbeddingTier(Enum):
    """Embedding model tiers ordered by cost."""
    LOCAL = "local"       # Free, fast, good quality
    STANDARD = "standard" # Cheap API, great quality
    PREMIUM = "premium"   # Best quality, highest cost


class EmbeddingFactory:
    """
    Factory for creating embedding models based on tier selection.

    Cost Comparison (approx):
    - LOCAL: Free (runs on CPU)
    - STANDARD: ~$0.10 per 1M tokens (Mistral)
    - PREMIUM: ~$0.02 per 1K tokens (OpenAI)
    """

    _cached_local_model = None

    @classmethod
    def get_embeddings(cls, tier: EmbeddingTier = EmbeddingTier.PREMIUM):
        """
        Get an embedding model for the specified tier.

        Args:
            tier: The embedding tier to use

        Returns:
            A LangChain-compatible embedding model
        """
        if tier == EmbeddingTier.LOCAL:
            return cls._get_local_embeddings()
        elif tier == EmbeddingTier.STANDARD:
            return cls._get_standard_embeddings()
        else:
            return cls._get_premium_embeddings()

    @classmethod
    def _get_local_embeddings(cls):
        """
        Get local HuggingFace embeddings (free, runs on CPU).
        Uses BAAI/bge-small-en-v1.5 - a high-quality, compact model.
        """
        # Cache the model to avoid reloading
        if cls._cached_local_model is None:
            try:
                from langchain_community.embeddings import HuggingFaceEmbeddings
                logger.info("🔢 [Embeddings] Loading local model: BAAI/bge-small-en-v1.5")
                cls._cached_local_model = HuggingFaceEmbeddings(
                    model_name="BAAI/bge-small-en-v1.5",
                    model_kwargs={'device': 'cpu'},
                    encode_kwargs={'normalize_embeddings': True}
                )
                logger.info("🔢 [Embeddings] ✅ Local model loaded")
            except ImportError:
                logger.warning("🔢 [Embeddings] HuggingFace not available, falling back to OpenAI")
                return cls._get_premium_embeddings()
        return cls._cached_local_model

    @classmethod
    def _get_standard_embeddings(cls):
        """
        Get standard-tier embeddings (Mistral or fallback to OpenAI).
        """
        mistral_key = getattr(settings, 'MISTRAL_API_KEY', None)

        if mistral_key:
            try:
                from langchain_mistralai import MistralAIEmbeddings
                logger.info("🔢 [Embeddings] Using Mistral Embed (standard tier)")
                return MistralAIEmbeddings(
                    api_key=mistral_key,
                    model="mistral-embed"
                )
            except ImportError:
                logger.warning("🔢 [Embeddings] Mistral SDK not installed, falling back to OpenAI")

        # Fallback to OpenAI if Mistral not available
        logger.info("🔢 [Embeddings] Mistral not configured, using OpenAI (standard tier)")
        return cls._get_premium_embeddings()

    @classmethod
    def _get_premium_embeddings(cls):
        """
        Get premium-tier embeddings (OpenAI text-embedding-3-small).
        """
        from langchain_openai import OpenAIEmbeddings
        logger.info("🔢 [Embeddings] Using OpenAI text-embedding-3-small (premium tier)")
        return OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.OPENAI_API_KEY
        )

    @staticmethod
    def auto_select(
        doc_count: int = 1,
        priority: str = "normal",
        force_local: bool = False
    ) -> EmbeddingTier:
        """
        Automatically select the optimal embedding tier based on context.

        Args:
            doc_count: Number of documents to embed
            priority: "low", "normal", or "high"
            force_local: If True, always use local embeddings

        Returns:
            The recommended EmbeddingTier
        """
        # Determine what the original logic would have selected
        if force_local:
            selected = EmbeddingTier.LOCAL
        elif priority == "high":
            selected = EmbeddingTier.PREMIUM
        elif doc_count > 1000:
            selected = EmbeddingTier.LOCAL
        elif doc_count > 100:
            selected = EmbeddingTier.STANDARD
        else:
            selected = EmbeddingTier.PREMIUM

        # C1 SAFETY: Always return PREMIUM to match DB vector(1536) index
        if selected != EmbeddingTier.PREMIUM:
            dimensions = {
                EmbeddingTier.LOCAL: 384,
                EmbeddingTier.STANDARD: 1024,
                EmbeddingTier.PREMIUM: 1536,
            }
            logger.warning(
                "[Embeddings] auto_select() tried to select %s "
                "(dimension %d), but DB requires %d. Forcing PREMIUM tier.",
                selected.value,
                dimensions.get(selected, 0),
                REQUIRED_DIMENSION,
            )
        return EmbeddingTier.PREMIUM

    @staticmethod
    def get_embedding_dimension(tier: EmbeddingTier) -> int:
        """
        Get the embedding dimension for a given tier.

        Important: All models should output the same dimension for compatibility
        with the vector database. If using mixed models, you may need to
        re-embed documents when switching tiers.
        """
        dimensions = {
            EmbeddingTier.LOCAL: 384,      # bge-small-en-v1.5
            EmbeddingTier.STANDARD: 1024,  # mistral-embed
            EmbeddingTier.PREMIUM: 1536    # text-embedding-3-small
        }
        return dimensions.get(tier, 1536)
