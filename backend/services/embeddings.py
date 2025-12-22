"""
Embedding Service

Provides centralized embedding generation using OpenAI's text-embedding-3-small model.
"""

import logging
from typing import List, Optional
from langchain_openai import OpenAIEmbeddings
from core.config import settings
from core.resilience import with_retry_sync

logger = logging.getLogger(__name__)

# Singleton embeddings model instance
_embeddings_model: Optional[OpenAIEmbeddings] = None


def get_embeddings_model() -> OpenAIEmbeddings:
    """
    Get or create the singleton OpenAI embeddings model.
    Uses text-embedding-3-small for cost efficiency.
    """
    global _embeddings_model
    
    if _embeddings_model is None:
        _embeddings_model = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.OPENAI_API_KEY
        )
        logger.info("📊 [Embeddings] Initialized OpenAI embeddings model (text-embedding-3-small)")
    
    return _embeddings_model


@with_retry_sync(max_attempts=3)
def generate_embedding(text: str) -> List[float]:
    """
    Generate an embedding vector for a single text string.
    
    Args:
        text: The text to embed
        
    Returns:
        List of floats representing the embedding vector (1536 dimensions)
        
    Raises:
        Exception: If embedding generation fails after retries
    """
    if not text or not text.strip():
        logger.warning("📊 [Embeddings] Empty text provided, returning zero vector")
        return [0.0] * 1536  # Return zero vector for empty text
    
    try:
        model = get_embeddings_model()
        embedding = model.embed_query(text)
        return embedding
    except Exception as e:
        logger.error(f"📊 [Embeddings] Failed to generate embedding: {e}")
        raise


@with_retry_sync(max_attempts=3)
def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a batch of texts.
    More efficient than calling generate_embedding in a loop.
    
    Args:
        texts: List of texts to embed
        
    Returns:
        List of embedding vectors
    """
    if not texts:
        return []
    
    # Filter out empty texts and track indices
    valid_texts = []
    valid_indices = []
    for i, text in enumerate(texts):
        if text and text.strip():
            valid_texts.append(text)
            valid_indices.append(i)
    
    if not valid_texts:
        return [[0.0] * 1536 for _ in texts]
    
    try:
        model = get_embeddings_model()
        embeddings = model.embed_documents(valid_texts)
        
        # Reconstruct full result list with zero vectors for empty texts
        result = [[0.0] * 1536 for _ in texts]
        for i, emb in zip(valid_indices, embeddings):
            result[i] = emb
        
        logger.info(f"📊 [Embeddings] Generated {len(valid_texts)} embeddings")
        return result
        
    except Exception as e:
        logger.error(f"📊 [Embeddings] Batch embedding failed: {e}")
        raise
