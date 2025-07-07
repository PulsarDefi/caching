import functools
from typing import Any, cast

from caching.types import Number, F
from caching.bucket import CacheBucket
from caching._sync.lock import _SYNC_LOCKS
from caching.utils.functions import get_function_id


def sync_decorator(function: F, ttl: Number, never_die: bool = False) -> F:
    from caching.features.never_die import register_never_die_function

    function_id = get_function_id(function)

    @functools.wraps(function)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        skip_cache = kwargs.pop("skip_cache", False)
        cache_key = CacheBucket.create_cache_key(*args, **kwargs)

        if never_die:
            register_never_die_function(function, ttl, args, kwargs)
        if cache_entry := CacheBucket.get(function_id, cache_key, skip_cache):
            return cache_entry.result

        with _SYNC_LOCKS[function_id][cache_key]:
            if cache_entry := CacheBucket.get(function_id, cache_key, skip_cache):
                return cache_entry.result

            result = function(*args, **kwargs)
            CacheBucket.set(function_id, cache_key, result, ttl)
            return result

    return cast(F, sync_wrapper)
