import time
from inspect import Signature
from dataclasses import dataclass
from collections import defaultdict
from typing import Any, DefaultDict, Callable, Hashable

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
    def create_cache_key(
        function_signature: Signature,
        cache_key_func: Callable[[tuple, dict], Hashable] | None,
        ignore_fields: tuple[str, ...],
        *args: Any,
        **kwargs: Any,
    ) -> str:
        if cache_key_func:
            cache_key = cache_key_func(args, kwargs)
            if not isinstance(cache_key, Hashable):
                raise Exception(
                    "Cache key function must be return an hashable cache key - be carefull with mutable types (list, dict, set) and non built-in types"
                )

            return str(hash(cache_key))

        bound = function_signature.bind_partial(*args, **kwargs)
        bound.apply_defaults()
        items = tuple((name, value) for name, value in bound.arguments.items() if name not in ignore_fields)
        return str(hash(items))
