import asyncio
import time as time_module
from collections import OrderedDict
from typing import Any, Optional

from config import Config


class FastMemoryCache:
    def __init__(self, default_ttl: int = 600, max_entries: int = 2000):
        self._default_ttl = max(1, int(default_ttl))
        self._max_entries = max(100, int(max_entries))
        self._data: "OrderedDict[str, Any]" = OrderedDict()
        self._expires: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        now = time_module.monotonic()
        async with self._lock:
            expires = self._expires.get(key, 0.0)
            if expires <= now:
                self._data.pop(key, None)
                self._expires.pop(key, None)
                return None
            value = self._data.get(key)
            if value is None:
                return None
            self._data.move_to_end(key)
            return value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ttl_value = self._default_ttl if ttl is None else max(1, int(ttl))
        async with self._lock:
            self._data[key] = value
            self._data.move_to_end(key)
            self._expires[key] = time_module.monotonic() + ttl_value
            while len(self._data) > self._max_entries:
                old_key, _ = self._data.popitem(last=False)
                self._expires.pop(old_key, None)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._data.pop(key, None)
            self._expires.pop(key, None)

    async def clear(self) -> None:
        async with self._lock:
            self._data.clear()
            self._expires.clear()

    async def size(self) -> int:
        async with self._lock:
            return len(self._data)


cache = FastMemoryCache(
    default_ttl=Config.CACHE_TTL,
    max_entries=int(__import__("os").environ.get("CACHE_MAX_ENTRIES", "2000")),
)
