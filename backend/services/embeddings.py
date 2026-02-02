"""
Embedding Service

Provides centralized embedding generation using OpenAI's text-embedding-3-small model.

THREAD SAFETY FIX (Issue #14): The global _embeddings_model was initialized without
a lock, causing potential double-initialization under concurrent startup.
Now uses threading.Lock for thread-safe lazy initialization.
"""

import logging
import random
import time
import threading
from typing import List, Optional, Sequence
from langchain_openai import OpenAIEmbeddings
from core.config import settings
from core.resilience import with_retry_sync
from services.quotas import get_plan_max_tpm
try:
    from core.metrics import embeddings_generated, operation_duration, retry_failure
except Exception:
    embeddings_generated = None
    operation_duration = None
    retry_failure = None

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


class _TpmRegulator:
    """Simple per-plan token-per-minute regulator to cap cost exposure."""

    def __init__(self) -> None:
        self._state = {}

    def throttle(self, plan_code: str, tokens: int, max_tpm: Optional[int]) -> None:
        if not max_tpm or max_tpm <= 0 or tokens <= 0:
            return

        now = time.time()
        state = self._state.get(plan_code)
        if not state or now >= state["reset_at"]:
            state = {"tokens": 0, "reset_at": now + 60}
            self._state[plan_code] = state

        if state["tokens"] + tokens > max_tpm:
            sleep_seconds = max(0.0, state["reset_at"] - now)
            if sleep_seconds > 0:
                logger.info(
                    "⏱️ [Embeddings] Throttling embedding for Plan %s: Sleeping %.2fs (max_tpm=%s)",
                    plan_code,
                    sleep_seconds,
                    max_tpm,
                )
                time.sleep(sleep_seconds)
            now = time.time()
            state["tokens"] = 0
            state["reset_at"] = now + 60

        state["tokens"] += min(tokens, max_tpm)


_TPM_REGULATOR = _TpmRegulator()

# Thread-safe singleton embeddings model instance (Issue #14)
_embeddings_model: Optional[OpenAIEmbeddings] = None
_embeddings_lock = threading.Lock()


def get_embeddings_model() -> OpenAIEmbeddings:
    """
    Get or create the singleton OpenAI embeddings model.
    Uses text-embedding-3-small for cost efficiency.

    THREAD SAFETY FIX (Issue #14): Uses double-checked locking pattern
    to prevent race condition during concurrent initialization.
    """
    global _embeddings_model

    # Fast path: already initialized
    if _embeddings_model is not None:
        return _embeddings_model

    # Slow path: acquire lock and initialize
    with _embeddings_lock:
        # Double-check after acquiring lock
        if _embeddings_model is None:
            _embeddings_model = OpenAIEmbeddings(
                model="text-embedding-3-small",
                api_key=settings.OPENAI_API_KEY,
                request_timeout=60,
                max_retries=2
            )
            logger.info("📊 [Embeddings] Initialized OpenAI embeddings model (text-embedding-3-small)")

    return _embeddings_model


def reset_embeddings_model() -> None:
    """
    Reset the embeddings model singleton (useful for testing or config changes).
    """
    global _embeddings_model
    with _embeddings_lock:
        _embeddings_model = None
        logger.info("📊 [Embeddings] Reset embeddings model singleton")


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


async def generate_embeddings_batch(
    texts: List[str],
    token_counts: Optional[Sequence[int]] = None,
    max_tokens_per_batch: Optional[int] = None,
    plan_code: Optional[str] = None,
) -> List[Optional[List[float]]]:
    """
    Async-compatible wrapper for legacy callers.

    This intentionally delegates to the synchronous implementation to avoid
    any event-loop usage inside workers while keeping async call sites intact.
    """
    return generate_embeddings_batch_sync(
        texts,
        token_counts=token_counts,
        max_tokens_per_batch=max_tokens_per_batch,
        plan_code=plan_code,
    )


def _estimate_token_count(text: str) -> int:
    if not text:
        return 1
    return max(1, len(text) // 4)


def _build_batches(
    texts: Sequence[str],
    token_counts: Optional[Sequence[int]],
    batch_size: int,
    max_tokens_per_batch: Optional[int],
) -> List[List[str]]:
    if not texts:
        return []

    if not token_counts or not max_tokens_per_batch or max_tokens_per_batch <= 0:
        return [list(texts[i:i + batch_size]) for i in range(0, len(texts), batch_size)]

    batches: List[List[str]] = []
    current: List[str] = []
    current_tokens = 0

    for text, tokens in zip(texts, token_counts):
        token_budget = tokens if tokens and tokens > 0 else _estimate_token_count(text)

        if token_budget > max_tokens_per_batch:
            if current:
                batches.append(current)
                current = []
                current_tokens = 0
            batches.append([text])
            continue

        if current and (current_tokens + token_budget > max_tokens_per_batch or len(current) >= batch_size):
            batches.append(current)
            current = [text]
            current_tokens = token_budget
        else:
            current.append(text)
            current_tokens += token_budget

    if current:
        batches.append(current)

    return batches


def generate_embeddings_batch_sync(
    texts: List[str],
    token_counts: Optional[Sequence[int]] = None,
    max_tokens_per_batch: Optional[int] = None,
    plan_code: Optional[str] = None,
) -> List[Optional[List[float]]]:
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
    max_tokens = max_tokens_per_batch or settings.EMBEDDING_MAX_TOKENS_PER_REQUEST

    valid_token_counts: Optional[List[int]] = None
    if token_counts and len(token_counts) == len(texts):
        valid_token_counts = [token_counts[i] for i in valid_indices]
    elif max_tokens and max_tokens > 0:
        valid_token_counts = [_estimate_token_count(text) for text in valid_texts]

    @with_retry_sync(max_attempts=3, min_wait=2, max_wait=10, use_retryable=True, jitter=True)
    def embed_batch(batch_texts: List[str]) -> List[List[float]]:
        return model.embed_documents(batch_texts)

    batches = _build_batches(valid_texts, valid_token_counts, batch_size, max_tokens)
    plan_label = (plan_code or settings.PLAN_STARTER).lower()
    plan_max_tpm = get_plan_max_tpm(plan_code)

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
        # Pre-batch TPM throttle (cost safety valve)
        tokens_in_batch = sum(_estimate_token_count(text) for text in batch_texts)
        _TPM_REGULATOR.throttle(plan_label, tokens_in_batch, plan_max_tpm)

        batch_start = time.perf_counter()
        try:
            embeddings = embed_batch(batch_texts)
        except Exception as exc:
            error_batches += 1
            if is_rate_limit_error(exc):
                rate_limit_hits += 1
                _EMBEDDING_THROTTLE.record_rate_limit()
            if retry_failure:
                retry_failure.labels("openai", "embedding_batch").inc()
            logger.error(
                f"📊 [Embeddings] Batch {batch_idx + 1}/{len(batches)} failed: {exc}"
            )
            raise

        batch_duration = time.perf_counter() - batch_start
        total_duration += batch_duration
        _EMBEDDING_THROTTLE.record_success()

        all_embeddings.extend(embeddings)
        rate = len(batch_texts) / batch_duration if batch_duration > 0 else 0.0
        if operation_duration:
            operation_duration.labels("embedding_batch").observe(batch_duration)
        if embeddings_generated:
            embeddings_generated.inc(len(batch_texts))
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
