"""
Caching utilities for the MCP server
"""
import json
import hashlib
from typing import Any, Optional, Callable
from datetime import datetime, timedelta
from functools import wraps
import asyncio

from ..config import settings
from .logger import get_logger


logger = get_logger(__name__)


class InMemoryCache:
    """Simple in-memory cache with TTL support"""
    
    def __init__(self, default_ttl: int = 3600):
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self.default_ttl = default_ttl
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        async with self._lock:
            if key not in self._cache:
                return None
            
            value, expiry = self._cache[key]
            
            if datetime.now() > expiry:
                del self._cache[key]
                return None
            
            return value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL"""
        async with self._lock:
            expiry = datetime.now() + timedelta(seconds=ttl or self.default_ttl)
            self._cache[key] = (value, expiry)
    
    async def delete(self, key: str) -> None:
        """Delete value from cache"""
        async with self._lock:
            self._cache.pop(key, None)
    
    async def clear(self) -> None:
        """Clear all cache"""
        async with self._lock:
            self._cache.clear()
    
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
            
            return len(expired_keys)
    
    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics"""
        return {
            "total_entries": len(self._cache),
            "default_ttl": self.default_ttl,
        }


class CacheManager:
    """Centralized cache management"""
    
    def __init__(self):
        self._cache = InMemoryCache(default_ttl=settings.cache_ttl)
        logger.info(f"Cache initialized with TTL: {settings.cache_ttl}s")
    
    def _generate_key(self, prefix: str, *args: Any, **kwargs: Any) -> str:
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
    
    def cached(
        self,
        prefix: str,
        ttl: Optional[int] = None,
        key_func: Optional[Callable] = None
    ):
        """Decorator to cache function results"""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any):
                # Generate cache key
                if key_func:
                    cache_key = f"{prefix}:{key_func(*args, **kwargs)}"
                else:
                    cache_key = self._generate_key(prefix, *args, **kwargs)
                
                # Try to get from cache
                cached_value = await self.get(cache_key)
                if cached_value is not None:
                    return cached_value
                
                # Call function and cache result
                result = await func(*args, **kwargs)
                await self.set(cache_key, result, ttl)
                
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
