import time
from dataclasses import dataclass
from collections import defaultdict
from typing import Any, DefaultDict

from caching.types import Number


@dataclass
class CacheEntry:
    result: Any
    cached_at: float
    expires_at: float

    def is_expired(self) -> bool:
        return time.time() > self.expires_at


def clear_expired_cached_items():
    """Clear expired cached items from the cache bucket."""
    while 1:
        try:
            for _, cache in CacheBucket._CACHE.items():
                for key, entry in list(cache.items()):
                    if entry.is_expired():
                        del cache[key]
        except Exception:
            pass
        finally:
            time.sleep(10)


class CacheBucket:
    _CACHE: DefaultDict[str, dict[str, CacheEntry]] = defaultdict(lambda: dict())

    @classmethod
    def set(cls, function_id: str, cache_key: str, result: Any, ttl: Number):
        current_time = time.time()
        cls._CACHE[function_id][cache_key] = CacheEntry(result, current_time, current_time + ttl)

    @classmethod
    def get(cls, function_id: str, cache_key: str, skip_cache: bool) -> CacheEntry | None:
        if skip_cache:
            return None
        if function_id not in cls._CACHE:
            return None
        if entry := cls._CACHE[function_id].get(cache_key):
            if not entry.is_expired():
                return entry
        return None

    @classmethod
    def is_cache_expired(cls, function_id: str, cache_key: str) -> bool:
        if function_id not in cls._CACHE:
            return True
        if cache_key not in cls._CACHE[function_id]:
            return True

        entry = cls._CACHE[function_id][cache_key]
        return entry.is_expired()

    @classmethod
    def clear(cls):
        cls._CACHE.clear()

    @staticmethod
    def create_cache_key(*args: Any, **kwargs: Any) -> str:
        # Sort kwargs to ensure consistent key
        sorted_kwargs = sorted(kwargs.items())
        return str(hash((args, tuple(sorted_kwargs))))
