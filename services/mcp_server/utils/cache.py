"""
Caching utilities for the MCP server.
Provides in-memory LRU cache with TTL, statistics, and warming support.
"""
import json
import hashlib
from typing import Any, Optional, Callable, List, Dict
from datetime import datetime, timedelta
from functools import wraps
import asyncio

from ..config import settings
from .logger import get_logger


logger = get_logger(__name__)


class InMemoryCache:
    """Simple in-memory cache with TTL and LRU support"""
    
    def __init__(self, default_ttl: int = 3600, max_size: int = 1000):
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self._access_order: list[str] = []  # Track access order for LRU
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._lock = asyncio.Lock()
        
        # Statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "sets": 0
        }
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        async with self._lock:
            if key not in self._cache:
                self._stats["misses"] += 1
                return None
            
            value, expiry = self._cache[key]
            
            if datetime.now() > expiry:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                self._stats["misses"] += 1
                return None
            
            # Update access order (move to end)
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            
            self._stats["hits"] += 1
            return value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL"""
        async with self._lock:
            # Check size limit and evict if needed
            if len(self._cache) >= self.max_size and key not in self._cache:
                await self._evict_lru()
            
            expiry = datetime.now() + timedelta(seconds=ttl or self.default_ttl)
            self._cache[key] = (value, expiry)
            
            # Update access order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            
            self._stats["sets"] += 1
            
    async def _evict_lru(self) -> None:
        """Evict least recently used item"""
        if not self._access_order:
            return
            
        lru_key = self._access_order.pop(0)
        if lru_key in self._cache:
            del self._cache[lru_key]
            self._stats["evictions"] += 1
            logger.debug(f"Evicted LRU key: {lru_key}")
    
    async def delete(self, key: str) -> None:
        """Delete value from cache"""
        async with self._lock:
            self._cache.pop(key, None)
            if key in self._access_order:
                self._access_order.remove(key)
    
    async def clear(self) -> None:
        """Clear all cache"""
        async with self._lock:
            self._cache.clear()
            self._access_order.clear()
    
    async def cleanup_expired(self) -> int:
        """Remove expired entries and return count"""
        async with self._lock:
            now = datetime.now()
            expired_keys = [
                key for key, (_, expiry) in self._cache.items()
                if now > expiry
            ]
            
            for key in expired_keys:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
            
            return len(expired_keys)
    
    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics"""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0.0
        
        return {
            "total_entries": len(self._cache),
            "max_size": self.max_size,
            "default_ttl": self.default_ttl,
            "hit_rate": round(hit_rate, 2),
            **self._stats
        }


class CacheManager:
    """Centralized cache management with warming support"""
    
    def __init__(self):
        self._cache = InMemoryCache(
            default_ttl=settings.cache_ttl,
            max_size=settings.cache_max_size
        )
        self._warming_in_progress = False
        self._warm_callbacks: List[Callable] = []
        logger.info(f"Cache initialized with TTL: {settings.cache_ttl}s, max_size: {settings.cache_max_size}")
    
    def generate_key(self, prefix: str, *args: Any, **kwargs: Any) -> str:
        """Generate cache key from function arguments"""
        key_data = {
            "args": args,
            "kwargs": kwargs,
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        return f"{prefix}:{key_hash}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get from cache"""
        value = await self._cache.get(key)
        if value is not None:
            logger.debug(f"Cache hit: {key}")
        else:
            logger.debug(f"Cache miss: {key}")
        return value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set in cache"""
        await self._cache.set(key, value, ttl)
        logger.debug(f"Cache set: {key} (TTL: {ttl or settings.cache_ttl}s)")
    
    async def delete(self, key: str) -> None:
        """Delete from cache"""
        await self._cache.delete(key)
        logger.debug(f"Cache delete: {key}")
    
    async def clear(self) -> None:
        """Clear all cache"""
        await self._cache.clear()
        logger.info("Cache cleared")
    
    async def cleanup(self) -> int:
        """Cleanup expired entries"""
        count = await self._cache.cleanup_expired()
        if count > 0:
            logger.info(f"Cleaned up {count} expired cache entries")
        return count
        
    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics"""
        return self._cache.get_stats()
    
    def register_warm_callback(self, callback: Callable) -> None:
        """Register a callback to be called during cache warming"""
        self._warm_callbacks.append(callback)
        logger.debug(f"Registered cache warming callback: {callback.__name__}")
    
    async def warm_cache(self) -> Dict[str, Any]:
        """
        Pre-populate cache with common data.
        Calls all registered warming callbacks.
        Returns summary of warming results.
        """
        if self._warming_in_progress:
            logger.warning("Cache warming already in progress, skipping")
            return {"status": "skipped", "reason": "already_in_progress"}
        
        self._warming_in_progress = True
        results = {
            "status": "completed",
            "started_at": datetime.utcnow().isoformat(),
            "callbacks_executed": 0,
            "total_entries_added": 0,
            "errors": [],
        }
        
        try:
            logger.info(f"Starting cache warming with {len(self._warm_callbacks)} callbacks")
            
            for callback in self._warm_callbacks:
                try:
                    entries_added = await callback()
                    results["callbacks_executed"] += 1
                    results["total_entries_added"] += entries_added or 0
                    logger.info(f"Cache warming callback '{callback.__name__}' added {entries_added or 0} entries")
                except Exception as e:
                    error_msg = f"Cache warming callback '{callback.__name__}' failed: {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            results["completed_at"] = datetime.utcnow().isoformat()
            logger.info(
                f"Cache warming completed: {results['callbacks_executed']} callbacks, "
                f"{results['total_entries_added']} entries added"
            )
            
        finally:
            self._warming_in_progress = False
        
        return results
    
    def get_ttl_for_entity(self, entity_type: str) -> int:
        """Get the appropriate TTL for an entity type"""
        ttl_map = {
            "courses": settings.cache_ttl_courses,
            "professors": settings.cache_ttl_professors,
            "reviews": settings.cache_ttl_reviews,
            "schedules": settings.cache_ttl_schedules,
        }
        return ttl_map.get(entity_type, settings.cache_ttl)
    
    def cached(
        self,
        prefix: str,
        ttl: Optional[int] = None,
        key_func: Optional[Callable] = None,
        entity_type: Optional[str] = None
    ):
        """Decorator to cache function results"""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any):
                # Generate cache key
                if key_func:
                    cache_key = f"{prefix}:{key_func(*args, **kwargs)}"
                else:
                    cache_key = self.generate_key(prefix, *args, **kwargs)
                
                # Try to get from cache
                cached_value = await self.get(cache_key)
                if cached_value is not None:
                    return cached_value
                
                # Determine TTL
                effective_ttl = ttl
                if effective_ttl is None and entity_type:
                    effective_ttl = self.get_ttl_for_entity(entity_type)
                
                # Call function and cache result
                result = await func(*args, **kwargs)
                await self.set(cache_key, result, effective_ttl)
                
                return result
            
            return wrapper
        return decorator


# Singleton instance
cache_manager = CacheManager()


# Periodic cleanup task
async def start_cache_cleanup_task():
    """Background task to cleanup expired cache entries"""
    while True:
        await asyncio.sleep(3600)  # Run every hour
        try:
            await cache_manager.cleanup()
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
