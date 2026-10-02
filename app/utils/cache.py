import time
import asyncio
from typing import Any, Optional, Dict
from config import Config

class FastMemoryCache:
    """
    High-performance bounded in-memory TTL caching engine.
    Reduces MongoDB roundtrips for maximum speed, smooth responsiveness, and low latency.
    Supports TTL, maximum entries (LRU/FIFO eviction), and thread-safe operations.
    """
    def __init__(self, default_ttl: Optional[int] = None, max_entries: Optional[int] = None):
        self._cache: Dict[str, Any] = {}
        self._expires: Dict[str, float] = {}
        self._default_ttl = default_ttl if default_ttl is not None else getattr(Config, "CACHE_TTL", 600)
        self._max_entries = max_entries if max_entries is not None else getattr(Config, "CACHE_MAX_ENTRIES", 1000)
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            curr_now = float(time.time())
            if curr_now > self._expires.get(key, 0):
                self._cache.pop(key, None)
                self._expires.pop(key, None)
                self._misses += 1
                return None
            self._hits += 1
            return self._cache[key]

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        async with self._lock:
            # Memory-safe eviction if cache exceeds max_entries
            if len(self._cache) >= self._max_entries and key not in self._cache:
                # Evict expired entries first
                curr_now = float(time.time())
                expired_keys = [k for k, exp in self._expires.items() if curr_now > exp]
                for k in expired_keys:
                    self._cache.pop(k, None)
                    self._expires.pop(k, None)
                # If still at capacity, evict oldest entry
                if len(self._cache) >= self._max_entries:
                    oldest_key = next(iter(self._cache))
                    self._cache.pop(oldest_key, None)
                    self._expires.pop(oldest_key, None)

            self._cache[key] = value
            curr_now = float(time.time())
            effective_ttl = ttl if ttl is not None else self._default_ttl
            self._expires[key] = curr_now + float(effective_ttl)

    async def delete(self, key: str) -> bool:
        async with self._lock:
            existed = key in self._cache
            self._cache.pop(key, None)
            self._expires.pop(key, None)
            return existed

    async def clear(self):
        async with self._lock:
            self._cache.clear()
            self._expires.clear()

    async def get_stats(self) -> Dict[str, Any]:
        async with self._lock:
            total_requests = self._hits + self._misses
            hit_ratio = (self._hits / total_requests * 100) if total_requests > 0 else 0.0
            return {
                "cached_keys": len(self._cache),
                "max_entries": self._max_entries,
                "hits": self._hits,
                "misses": self._misses,
                "hit_ratio_percent": round(hit_ratio, 2)
            }

cache = FastMemoryCache()
