import time
from collections import defaultdict
from typing import Any, DefaultDict

from caching.types import Number


class CacheBucket:
    _CACHE: DefaultDict[int, dict[str, tuple[float, Any]]] = defaultdict(lambda: dict())

    @classmethod
    def set(cls, function_id: int, cache_key: str, result: Any):
        cls._CACHE[function_id][cache_key] = (time.time(), result)

    @classmethod
    def get(cls, function_id: int, key: str, ttl: Number):
        if function_id not in cls._CACHE:
            return None
        if entry := cls._CACHE[function_id].get(key):
            timestamp, _ = entry
            if time.time() < timestamp + ttl:
                return entry
        return None

    @classmethod
    def clear(cls):
        cls._CACHE.clear()

    @staticmethod
    def create_cache_key(*args: Any, **kwargs: Any) -> str:
        # Sort kwargs to ensure consistent key
        sorted_kwargs = sorted(kwargs.items())
        return str(hash((args, tuple(sorted_kwargs))))
