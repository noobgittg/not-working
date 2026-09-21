import time
import asyncio
from typing import Any, Optional, Dict

class FastMemoryCache:
    def __init__(self, default_ttl: int = 600):
        self._cache: Dict[str, Any] = {}
        self._expires: Dict[str, float] = {}
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key not in self._cache:
                return None
            if time.time() > self._expires.get(key, 0):
                self._cache.pop(key, None)
                self._expires.pop(key, None)
                return None
            return self._cache[key]

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        async with self._lock:
            self._cache[key] = value
            self._expires[key] = time.time() + (ttl if ttl is not None else self._default_ttl)

    async def delete(self, key: str):
        async with self._lock:
            self._cache.pop(key, None)
            self._expires.pop(key, None)

    async def clear(self):
        async with self._lock:
            self._cache.clear()
            self._expires.clear()

cache = FastMemoryCache()
