"""
Semantic Cache for RAG Responses (H7)

Redis-backed cache that matches queries by embedding similarity + scope.
Avoids redundant LLM calls for semantically identical questions.

Cache key is built from a quantized embedding hash + tenant/scope isolation
inputs. Two queries only hit the same cache entry when they share:
- organization_id
- selected scope set
- effective allowed scope set
- quantized embedding hash

Usage:
    from services.semantic_cache import semantic_cache

    cached = await semantic_cache.get(query_vector, scope_ids, organization_id)
    if cached:
        return cached

    # ... generate response ...
    await semantic_cache.put(
        query_vector,
        scope_ids,
        organization_id,
        response=response,
        sources=sources,
    )
"""

import asyncio
import hashlib
import json
import logging
from typing import Any

from core.config import settings

logger = logging.getLogger(__name__)


class SemanticCache:
    """Redis-backed semantic cache for RAG responses."""

    def __init__(
        self,
        redis_url: str | None = None,
        ttl: int = 3600,
    ):
        self.redis_url = redis_url or getattr(settings, "REDIS_URL", None)
        self.ttl = ttl
        self._redis = None
        self._redis_lock = asyncio.Lock()

    async def _get_redis(self):
        """Lazy-init async Redis connection with lock to prevent race conditions."""
        if self._redis is not None:
            return self._redis

        async with self._redis_lock:
            # Double-check after acquiring lock
            if self._redis is not None:
                return self._redis
            try:
                import redis.asyncio as aioredis

                self._redis = aioredis.from_url(
                    self.redis_url, decode_responses=True
                )
            except Exception as e:
                logger.warning("[SemanticCache] Redis unavailable: %s", e)
                return None
        return self._redis

    @staticmethod
    def _scope_fragment(
        scope_ids: list[str] | None,
        *,
        unrestricted_marker: str,
        empty_marker: str,
    ) -> str:
        """Serialize scope lists while distinguishing unrestricted from empty."""
        if scope_ids is None:
            return unrestricted_marker
        if not scope_ids:
            return empty_marker
        return "|".join(sorted(scope_ids))

    def _cache_key(
        self,
        query_embedding: list[float],
        scope_ids: list[str] | None,
        organization_id: str,
        allowed_scopes: list[str] | None = None,
    ) -> str:
        """Build a cache key from embedding hash + tenant/effective scopes.

        Uses full embedding (quantized to 4 decimal places) for high-fidelity
        matching, with SHA-256 (full 64-char hex) to avoid hash collisions.
        """
        quantized = [round(v, 4) for v in query_embedding]
        org_key = organization_id or "__unknown_org__"
        scope_key = self._scope_fragment(
            scope_ids,
            unrestricted_marker="__global__",
            empty_marker="__global__",
        )
        allowed_key = self._scope_fragment(
            allowed_scopes,
            unrestricted_marker="__all__",
            empty_marker="__none__",
        )
        raw = f"{org_key}:{allowed_key}:{scope_key}:{quantized}"
        return f"sem_cache:{hashlib.sha256(raw.encode()).hexdigest()}"

    async def get(
        self,
        query_embedding: list[float],
        scope_ids: list[str] | None,
        organization_id: str,
        allowed_scopes: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Check cache for semantically similar query."""
        try:
            r = await self._get_redis()
            if r is None:
                return None

            key = self._cache_key(
                query_embedding,
                scope_ids,
                organization_id,
                allowed_scopes,
            )
            data = await r.get(key)
            if data:
                try:
                    parsed = json.loads(data)
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning("[SemanticCache] Corrupted cache entry at %s: %s", key[:20], e)
                    # Delete corrupted entry
                    try:
                        await r.delete(key)
                    except Exception:
                        pass
                    return None
                logger.info("[SemanticCache] Cache HIT for key %s", key[:20])
                return parsed

            logger.debug("[SemanticCache] Cache MISS for key %s", key[:20])
            return None
        except Exception as e:
            logger.warning("[SemanticCache] Get error: %s", e)
            return None

    async def put(
        self,
        query_embedding: list[float],
        scope_ids: list[str] | None,
        organization_id: str,
        *,
        response: str,
        sources: list[dict[str, Any]],
        faithfulness_warning: str | None = None,
        allowed_scopes: list[str] | None = None,
    ) -> None:
        """Store response in cache keyed by embedding + scope."""
        try:
            r = await self._get_redis()
            if r is None:
                return

            key = self._cache_key(
                query_embedding,
                scope_ids,
                organization_id,
                allowed_scopes,
            )
            try:
                payload = json.dumps(
                    {
                        "response": response,
                        "sources": sources,
                        "faithfulness_warning": faithfulness_warning,
                    }
                )
            except (TypeError, ValueError) as e:
                logger.warning("[SemanticCache] Failed to serialize cache payload: %s", e)
                return
            await r.setex(key, self.ttl, payload)
            logger.debug("[SemanticCache] Stored response at key %s", key[:20])
        except Exception as e:
            logger.warning("[SemanticCache] Put error: %s", e)


# Singleton with config defaults
semantic_cache = SemanticCache(
    ttl=getattr(settings, "SEMANTIC_CACHE_TTL", 3600),
)
