import time
from collections import defaultdict
from dataclasses import dataclass, field
from inspect import Signature
from typing import Any, DefaultDict

from caching.types import CacheKeyFunction, Number


@dataclass
class CacheEntry:
    result: Any
    ttl: float
    never_die: bool

    cached_at: float = field(init=False)
    expires_at: float = field(init=False)

    @classmethod
    def time(cls) -> float:
        return time.monotonic()

    def __post_init__(self):
        self.cached_at = self.time()
        self.expires_at = self.cached_at + self.ttl

    def is_expired(self, offset: int = 0) -> bool:
        return self.time() > self.expires_at + offset


def clear_expired_cached_items():
    """Clear expired cached items from the cache bucket."""
    while 1:
        try:
            for cache in CacheBucket._CACHE.values():
                for key, entry in list(cache.items()):
                    if entry.is_expired(10):
                        del cache[key]
        except Exception:
            pass
        finally:
            time.sleep(10)


class CacheBucket:
    _CACHE: DefaultDict[str, dict[str, CacheEntry]] = defaultdict(lambda: dict())

    @classmethod
    def set(
        cls,
        function_id: str,
        cache_key: str,
        result: Any,
        ttl: Number,
        never_die: bool = False,
    ):
        cls._CACHE[function_id][cache_key] = CacheEntry(result, ttl, never_die)

    @classmethod
    def get(cls, function_id: str, cache_key: str, skip_cache: bool) -> CacheEntry | None:
        if skip_cache:
            return None
        if function_id not in cls._CACHE:
            return None
        if entry := cls._CACHE[function_id].get(cache_key):
            if entry.never_die or not entry.is_expired():
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

    @classmethod
    def create_cache_key(
        cls,
        function_signature: Signature,
        cache_key_func: CacheKeyFunction | None,
        ignore_fields: tuple[str, ...],
        args: tuple,
        kwargs: dict,
    ) -> str:
        if not cache_key_func:
            items = tuple(cls.iter_arguments(function_signature, args, kwargs, ignore_fields))
            return str(hash(items))

        cache_key = cache_key_func(args, kwargs)
        try:
            return str(hash(cache_key))
        except TypeError:
            raise Exception(
                "Cache key function must be return an hashable cache key - be carefull with mutable types (list, dict, set) and non built-in types"
            )

    @classmethod
    def iter_arguments(cls, function_signature: Signature, args: tuple, kwargs: dict, ignore_fields: tuple[str, ...]):
        bound = function_signature.bind_partial(*args, **kwargs)
        bound.apply_defaults()

        for name, value in bound.arguments.items():
            if name in ignore_fields:
                continue

            param = function_signature.parameters[name]

            # Positional variable arguments can just be yielded like so
            if param.kind == param.VAR_POSITIONAL:
                yield from value
                continue

            # Keyword variable arguments need to be unpacked from .items()
            if param.kind == param.VAR_KEYWORD:
                yield from value.items()
                continue

            yield name, value
