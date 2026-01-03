"""
Embedding Service

Provides centralized embedding generation using OpenAI's text-embedding-3-small model.
"""

import logging
import time
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
            api_key=settings.OPENAI_API_KEY,
            request_timeout=60,
            max_retries=2
        )
        logger.info("📊 [Embeddings] Initialized OpenAI embeddings model (text-embedding-3-small)")
    
    return _embeddings_model


@with_retry_sync(max_attempts=3)
def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Generate an embedding vector for a single text string.
    
    Args:
        text: The text to embed
        
    Returns:
        List of floats representing the embedding vector, or None if text is empty.
    """
    if not text or not text.strip():
        logger.warning("📊 [Embeddings] Empty text provided, returning None")
        return None
    
    try:
        model = get_embeddings_model()
        embedding = model.embed_query(text)
        return embedding
    except Exception as e:
        logger.error(f"📊 [Embeddings] Failed to generate embedding: {e}")
        raise


@with_retry_sync(max_attempts=3)
def generate_embeddings_batch(texts: List[str]) -> List[Optional[List[float]]]:
    """
    Generate embeddings for a batch of texts.
    
    Automatically splits into sub-batches to stay under OpenAI's token limits.
    Uses ~300 tokens per chunk estimate, limiting to ~800 chunks per batch
    for safety margin under 300K token limit.
    
    Args:
        texts: List of texts to embed
        
    Returns:
        List of embedding vectors (or None for empty texts)
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
        return [None for _ in texts]
    
    try:
        model = get_embeddings_model()
        
        # PRODUCTION TUNING: Safety First
        # Reduced batch size to prevent exceeding OpenAI's single-request token limit (max_tokens_per_request)
        # Error seen: "Requested 303625 tokens, max 300000" with BATCH_SIZE=500
        BATCH_SIZE = 50
        # Increased sleep to prevent hitting the Tokens Per Minute (TPM) rate limit
        SLEEP_INTERVAL = 2.0
        
        all_embeddings = []
        
        for batch_start in range(0, len(valid_texts), BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, len(valid_texts))
            batch_texts = valid_texts[batch_start:batch_end]
            
            batch_embeddings = model.embed_documents(batch_texts)
            all_embeddings.extend(batch_embeddings)
            
            # Rate Limit Protection: Sleep between batches to respect OpenAI TPM
            if batch_end < len(valid_texts):
                logger.info(f"📊 [Embeddings] Processed batch {batch_start//BATCH_SIZE + 1}: {len(batch_texts)} texts")
                time.sleep(SLEEP_INTERVAL)
        
        # Reconstruct full result list with None for empty texts
        result = [None for _ in texts]
        for i, emb in zip(valid_indices, all_embeddings):
            result[i] = emb
        
        logger.info(f"📊 [Embeddings] Generated {len(valid_texts)} embeddings")
        return result
        
    except Exception as e:
        logger.error(f"📊 [Embeddings] Batch embedding failed: {e}")
        raise
