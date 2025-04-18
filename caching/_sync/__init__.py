import functools
from typing import Any, cast

from caching.types import Number, F
from caching.bucket import CacheBucket
from caching._sync.lock import _SYNC_LOCKS
from caching._sync.features.never_die import register_never_die_function


def sync_decorator(function: F, ttl: Number, never_die: bool = False) -> F:
    function_id = id(function)

    @functools.wraps(function)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        cache_key = CacheBucket.create_cache_key(*args, **kwargs)

        if never_die:
            register_never_die_function(function, ttl, args, kwargs)

        if cache_entry := CacheBucket.get(function_id, cache_key, ttl):
            return cache_entry[1]

        with _SYNC_LOCKS[function_id][cache_key]:
            if cache_entry := CacheBucket.get(function_id, cache_key, ttl):
                return cache_entry[1]

            print(f"[NORMAL_CACHING] {function.__name__} with args {args} and kwargs {kwargs}")
            result = function(*args, **kwargs)
            CacheBucket.set(function_id, cache_key, result)
            return result

    return cast(F, sync_wrapper)
