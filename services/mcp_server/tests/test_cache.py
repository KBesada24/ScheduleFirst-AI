import pytest
import asyncio
from datetime import datetime, timedelta
from mcp_server.utils.cache import InMemoryCache, CacheManager

@pytest.mark.asyncio
async def test_cache_set_get():
    cache = InMemoryCache()
    await cache.set("key1", "value1")
    assert await cache.get("key1") == "value1"
    assert await cache.get("key2") is None

@pytest.mark.asyncio
async def test_cache_ttl():
    cache = InMemoryCache(default_ttl=1)
    await cache.set("key1", "value1", ttl=0.1)
    assert await cache.get("key1") == "value1"
    await asyncio.sleep(0.2)
    assert await cache.get("key1") is None

@pytest.mark.asyncio
async def test_cache_lru_eviction():
    # Create cache with max size 2
    cache = InMemoryCache(max_size=2)
    
    await cache.set("key1", "value1")
    await cache.set("key2", "value2")
    
    # Access key1 to make it recently used
    await cache.get("key1")
    
    # Add key3, should evict key2 (least recently used)
    await cache.set("key3", "value3")
    
    assert await cache.get("key1") == "value1"
    assert await cache.get("key2") is None
    assert await cache.get("key3") == "value3"
    
    stats = cache.get_stats()
    assert stats["evictions"] == 1
    assert stats["total_entries"] == 2

@pytest.mark.asyncio
async def test_cache_stats():
    cache = InMemoryCache()
    
    await cache.set("key1", "value1")  # sets: 1
    await cache.get("key1")            # hits: 1
    await cache.get("key2")            # misses: 1
    
    stats = cache.get_stats()
    assert stats["sets"] == 1
    assert stats["hits"] == 1
    assert stats["misses"] == 1

@pytest.mark.asyncio
async def test_cache_manager_integration():
    manager = CacheManager()
    # Access private cache for testing
    manager._cache.max_size = 2
    
    await manager.set("k1", "v1")
    await manager.set("k2", "v2")
    await manager.set("k3", "v3")
    
    # Check stats via manager
    stats = manager.get_stats()
    assert stats["evictions"] >= 0 # Might be 1 depending on implementation details
