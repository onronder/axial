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


async def generate_embeddings_batch(texts: List[str]) -> List[Optional[List[float]]]:
    """
    Async-compatible wrapper for legacy callers.

    This intentionally delegates to the synchronous implementation to avoid
    any event-loop usage inside workers while keeping async call sites intact.
    """
    return generate_embeddings_batch_sync(texts)


def generate_embeddings_batch_sync(texts: List[str]) -> List[Optional[List[float]]]:
    """
    Synchronous batch embeddings helper.

    Intentionally avoids asyncio/event loops so it can run safely inside
    Celery workers (gevent or prefork) without cross-loop errors.
    """
    # CRITICAL: Convert generators to list to prevent 'generator has no len()' error
    if not isinstance(texts, list):
        texts = list(texts)

    if not texts:
        return []

    # Filter out empty texts and track indices
    valid_texts: List[str] = []
    valid_indices: List[int] = []
    for i, text in enumerate(texts):
        if text and text.strip():
            valid_texts.append(text)
            valid_indices.append(i)

    if not valid_texts:
        return [None for _ in texts]

    model = get_embeddings_model()

    # OpenAI allows up to 2048 embeddings per request; keep a safe cap.
    batch_size = max(1, min(settings.EMBEDDING_BATCH_SIZE, 1000))
    sleep_interval = max(0.0, settings.EMBEDDING_SLEEP_INTERVAL)

    @with_retry_sync(max_attempts=3)
    def embed_batch(batch_texts: List[str]) -> List[List[float]]:
        return model.embed_documents(batch_texts)

    batches = []
    for batch_start in range(0, len(valid_texts), batch_size):
        batch_end = min(batch_start + batch_size, len(valid_texts))
        batches.append(valid_texts[batch_start:batch_end])

    all_embeddings: List[List[float]] = []
    for batch_idx, batch_texts in enumerate(batches):
        embeddings = embed_batch(batch_texts)
        all_embeddings.extend(embeddings)
        logger.info(
            f"📊 [Embeddings] Processed batch {batch_idx + 1}/{len(batches)}: {len(batch_texts)} texts"
        )

        if batch_idx < len(batches) - 1 and sleep_interval > 0:
            time.sleep(sleep_interval)

    result: List[Optional[List[float]]] = [None for _ in texts]
    for i, emb in zip(valid_indices, all_embeddings):
        result[i] = emb

    logger.info(
        f"📊 [Embeddings] Generated {len(valid_texts)} embeddings in {len(batches)} batches"
    )
    return result
