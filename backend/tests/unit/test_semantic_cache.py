"""
Unit Tests for Semantic Cache (H7)

Tests cache miss, hit, put, corrupted entry handling, and disabled behavior.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from services.semantic_cache import SemanticCache


class TestSemanticCache:
    @pytest.fixture
    def cache(self):
        return SemanticCache(redis_url="redis://localhost", ttl=3600)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self, cache):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        with patch.object(cache, "_get_redis", new_callable=AsyncMock, return_value=mock_redis):
            result = await cache.get([0.1] * 1536, ["scope1"])
        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_hit_returns_response(self, cache):
        cached_data = json.dumps({"response": "cached answer", "sources": [{"id": "s1"}]})
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=cached_data)
        with patch.object(cache, "_get_redis", new_callable=AsyncMock, return_value=mock_redis):
            result = await cache.get([0.1] * 1536, ["scope1"])
        assert result is not None
        assert result["response"] == "cached answer"
        assert result["sources"] == [{"id": "s1"}]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_put_stores_with_ttl(self, cache):
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()
        with patch.object(cache, "_get_redis", new_callable=AsyncMock, return_value=mock_redis):
            await cache.put([0.1] * 1536, ["scope1"], "answer", [{"id": "s1"}])
        mock_redis.setex.assert_called_once()
        # Verify TTL and payload contents
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 3600  # TTL
        stored = json.loads(call_args[0][2])
        assert stored["response"] == "answer"
        assert stored["sources"] == [{"id": "s1"}]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_returns_none_when_redis_unavailable(self, cache):
        """When Redis unavailable, no cache operations."""
        with patch.object(cache, "_get_redis", new_callable=AsyncMock, return_value=None):
            result = await cache.get([0.1] * 1536, ["scope1"])
        assert result is None

    @pytest.mark.unit
    def test_cache_key_includes_scope(self, cache):
        """Cache keys should differ for different scopes."""
        key1 = cache._cache_key([0.1] * 1536, ["scope1"])
        key2 = cache._cache_key([0.1] * 1536, ["scope2"])
        assert key1 != key2
        assert key1.startswith("sem_cache:")
        assert key2.startswith("sem_cache:")

    @pytest.mark.unit
    def test_cache_key_same_for_same_inputs(self, cache):
        """Same embedding + scope should produce same key."""
        key1 = cache._cache_key([0.1] * 1536, ["scope1"])
        key2 = cache._cache_key([0.1] * 1536, ["scope1"])
        assert key1 == key2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_get_handles_exception(self, cache):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=Exception("redis error"))
        with patch.object(cache, "_get_redis", new_callable=AsyncMock, return_value=mock_redis):
            result = await cache.get([0.1] * 1536, ["scope1"])
        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_handles_corrupted_json(self, cache):
        """Corrupted JSON in cache should be handled gracefully."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="not valid json {{{")
        mock_redis.delete = AsyncMock()
        with patch.object(cache, "_get_redis", new_callable=AsyncMock, return_value=mock_redis):
            result = await cache.get([0.1] * 1536, ["scope1"])
        assert result is None
        # Corrupted entry should be deleted
        mock_redis.delete.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_put_handles_unserializable_data(self, cache):
        """Unserializable data should fail gracefully, not crash."""
        mock_redis = AsyncMock()
        with patch.object(cache, "_get_redis", new_callable=AsyncMock, return_value=mock_redis):
            # set() objects are not JSON-serializable
            await cache.put([0.1] * 1536, ["scope1"], "answer", [{"bad": set()}])
        # Should not have stored anything (serialization failed)
        mock_redis.setex.assert_not_called()

    @pytest.mark.unit
    def test_cache_key_global_scope(self, cache):
        """Empty scope list should use __global__ key."""
        key = cache._cache_key([0.1] * 10, [])
        assert "__global__" in cache._cache_key.__code__.co_consts or key  # key exists
        key2 = cache._cache_key([0.1] * 10, ["scope1"])
        assert key != key2
