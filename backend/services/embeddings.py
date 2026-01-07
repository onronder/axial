"""
Embedding Service

Provides centralized embedding generation using OpenAI's text-embedding-3-small model.
"""

import logging
import random
import time
from typing import List, Optional
from langchain_openai import OpenAIEmbeddings
from core.config import settings
from core.resilience import with_retry_sync

logger = logging.getLogger(__name__)


class _EmbeddingThrottle:
    """Adaptive throttle for embedding batches."""

    def __init__(self) -> None:
        self._rate_limit_backoff = 0.0

    def record_rate_limit(self) -> None:
        self._rate_limit_backoff = min(
            settings.EMBEDDING_RATE_LIMIT_BACKOFF_MAX,
            self._rate_limit_backoff + settings.EMBEDDING_RATE_LIMIT_BACKOFF_STEP,
        )

    def record_success(self) -> None:
        self._rate_limit_backoff = max(
            0.0,
            self._rate_limit_backoff - settings.EMBEDDING_RATE_LIMIT_DECAY,
        )

    def compute_sleep(self, base_sleep: float, batch_duration: float) -> float:
        adaptive_extra = min(
            settings.EMBEDDING_ADAPTIVE_MAX_SLEEP,
            batch_duration * settings.EMBEDDING_ADAPTIVE_LATENCY_FACTOR,
        )
        sleep_seconds = base_sleep + adaptive_extra + self._rate_limit_backoff
        if sleep_seconds <= 0:
            return 0.0
        jitter = random.uniform(0.0, min(0.5, sleep_seconds * 0.25))
        return sleep_seconds + jitter


_EMBEDDING_THROTTLE = _EmbeddingThrottle()

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


@with_retry_sync(max_attempts=3, min_wait=2, max_wait=10, use_retryable=True, jitter=True)
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

    @with_retry_sync(max_attempts=3, min_wait=2, max_wait=10, use_retryable=True, jitter=True)
    def embed_batch(batch_texts: List[str]) -> List[List[float]]:
        return model.embed_documents(batch_texts)

    batches = []
    for batch_start in range(0, len(valid_texts), batch_size):
        batch_end = min(batch_start + batch_size, len(valid_texts))
        batches.append(valid_texts[batch_start:batch_end])

    all_embeddings: List[List[float]] = []
    total_duration = 0.0
    rate_limit_hits = 0
    error_batches = 0

    def is_rate_limit_error(exc: Exception) -> bool:
        try:
            from openai import RateLimitError
            if isinstance(exc, RateLimitError):
                return True
        except Exception:
            pass

        status_code = getattr(exc, "status_code", None)
        response = getattr(exc, "response", None)
        if status_code is None and response is not None:
            status_code = getattr(response, "status_code", None)
        return status_code == 429

    for batch_idx, batch_texts in enumerate(batches):
        batch_start = time.perf_counter()
        try:
            embeddings = embed_batch(batch_texts)
        except Exception as exc:
            error_batches += 1
            if is_rate_limit_error(exc):
                rate_limit_hits += 1
                _EMBEDDING_THROTTLE.record_rate_limit()
            logger.error(
                f"📊 [Embeddings] Batch {batch_idx + 1}/{len(batches)} failed: {exc}"
            )
            raise

        batch_duration = time.perf_counter() - batch_start
        total_duration += batch_duration
        _EMBEDDING_THROTTLE.record_success()

        all_embeddings.extend(embeddings)
        rate = len(batch_texts) / batch_duration if batch_duration > 0 else 0.0
        logger.info(
            "📊 [Embeddings] Batch %s/%s: %s texts in %.2fs (%.1f/sec)",
            batch_idx + 1,
            len(batches),
            len(batch_texts),
            batch_duration,
            rate,
        )

        if batch_idx < len(batches) - 1:
            sleep_seconds = _EMBEDDING_THROTTLE.compute_sleep(sleep_interval, batch_duration)
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

    result: List[Optional[List[float]]] = [None for _ in texts]
    for i, emb in zip(valid_indices, all_embeddings):
        result[i] = emb

    avg_rate = len(valid_texts) / total_duration if total_duration > 0 else 0.0
    logger.info(
        "📊 [Embeddings] Generated %s embeddings in %s batches (%.1f/sec, rate_limit_hits=%s, error_batches=%s)",
        len(valid_texts),
        len(batches),
        avg_rate,
        rate_limit_hits,
        error_batches,
    )
    return result
