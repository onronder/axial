"""
Embedding Service

Provides centralized embedding generation using OpenAI's text-embedding-3-small model.
"""

import asyncio
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
    Generate embeddings for a batch of texts with parallel processing.
    
    CRITICAL FIX: Removed @with_retry_sync decorator (was causing async/sync mismatch).
    Retry logic is now applied at the batch level inside this function.
    
    Automatically splits into sub-batches and processes them in parallel
    with rate limiting to respect OpenAI's token limits.
    
    Args:
        texts: List of texts to embed (or any iterable)
        
    Returns:
        List of embedding vectors (or None for empty texts)
    """
    from asyncio import Semaphore
    
    # CRITICAL FIX: Convert generators to list to prevent 'generator has no len()' error
    if not isinstance(texts, list):
        texts = list(texts)
    
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
        
        # PERFORMANCE OPTIMIZATION: Increased batch size for efficiency
        # OpenAI allows up to 2048 embeddings per request
        # 100 chunks provides optimal balance of speed and reliability
        # Reduces API calls by 80% compared to batch size of 20
        BATCH_SIZE = 100
        # Sleep interval to respect rate limits
        SLEEP_INTERVAL = 0.5  # Reduced from 1.0 for faster processing
        
        # Split into batches
        batches = []
        for batch_start in range(0, len(valid_texts), BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, len(valid_texts))
            batches.append(valid_texts[batch_start:batch_end])
        
        # Process batches in parallel with rate limiting
        # Allow 3 concurrent embedding requests
        semaphore = Semaphore(3)
        
        async def process_single_batch(batch_idx, batch_texts):
            """Process single batch with retry and timeout protection."""
            async with semaphore:
                # Import resilience utilities
                from core.resilience import with_retry_async, OPENAI_RETRY_CONFIG, with_timeout, Timeouts
                
                # Wrap embedding call with retry logic
                @with_retry_async(**OPENAI_RETRY_CONFIG)
                async def embed_with_retry():
                    """Embedding call with automatic retry on transient failures."""
                    # Use asyncio.to_thread for Python 3.9+ (better than run_in_executor)
                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError:
                        loop = asyncio.get_event_loop()
                    
                    return await loop.run_in_executor(
                        None,
                        model.embed_documents,
                        batch_texts
                    )
                
                # Apply timeout protection (60s per batch)
                try:
                    embeddings = await with_timeout(
                        embed_with_retry(),
                        timeout_seconds=Timeouts.EMBEDDING_BATCH,
                        operation_name=f"Embedding batch {batch_idx + 1}/{len(batches)}"
                    )
                    logger.info(f"📊 [Embeddings] Processed batch {batch_idx + 1}/{len(batches)}: {len(batch_texts)} texts")
                    
                    # Rate limiting between batches
                    if batch_idx < len(batches) - 1:
                        await asyncio.sleep(SLEEP_INTERVAL)
                    
                    return embeddings
                    
                except asyncio.TimeoutError:
                    logger.error(f"📊 [Embeddings] Batch {batch_idx + 1} timed out after {Timeouts.EMBEDDING_BATCH}s")
                    raise
                except Exception as e:
                    logger.error(f"📊 [Embeddings] Batch {batch_idx + 1} failed after retries: {e}")
                    raise
        
        # Process all batches in parallel
        tasks = [process_single_batch(i, batch) for i, batch in enumerate(batches)]
        batch_results = await asyncio.gather(*tasks)
        
        # Flatten results
        all_embeddings = []
        for batch_emb in batch_results:
            all_embeddings.extend(batch_emb)
        
        # Reconstruct full result list with None for empty texts
        result = [None for _ in texts]
        for i, emb in zip(valid_indices, all_embeddings):
            result[i] = emb
        
        logger.info(f"📊 [Embeddings] Generated {len(valid_texts)} embeddings in {len(batches)} parallel batches")
        return result
        
    except Exception as e:
        logger.error(f"📊 [Embeddings] Batch embedding failed: {e}")
        raise


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

    # OpenAI allows up to 2048 embeddings per request; keep it conservative.
    BATCH_SIZE = 100
    SLEEP_INTERVAL = 0.5

    @with_retry_sync(max_attempts=3)
    def embed_batch(batch_texts: List[str]) -> List[List[float]]:
        return model.embed_documents(batch_texts)

    batches = []
    for batch_start in range(0, len(valid_texts), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(valid_texts))
        batches.append(valid_texts[batch_start:batch_end])

    all_embeddings: List[List[float]] = []
    for batch_idx, batch_texts in enumerate(batches):
        embeddings = embed_batch(batch_texts)
        all_embeddings.extend(embeddings)
        logger.info(
            f"📊 [Embeddings] Processed batch {batch_idx + 1}/{len(batches)}: {len(batch_texts)} texts"
        )

        if batch_idx < len(batches) - 1:
            time.sleep(SLEEP_INTERVAL)

    result: List[Optional[List[float]]] = [None for _ in texts]
    for i, emb in zip(valid_indices, all_embeddings):
        result[i] = emb

    logger.info(
        f"📊 [Embeddings] Generated {len(valid_texts)} embeddings in {len(batches)} batches"
    )
    return result
