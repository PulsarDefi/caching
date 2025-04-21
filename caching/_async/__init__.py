import functools
from typing import Any, cast

from caching.types import Number, F
from caching.bucket import CacheBucket
from caching._async.lock import _ASYNC_LOCKS


def async_decorator(function: F, ttl: Number, never_die: bool = False) -> F:
    from caching.features.never_die import register_never_die_function

    function_id = id(function)

    @functools.wraps(function)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        cache_key = CacheBucket.create_cache_key(*args, **kwargs)

        if never_die:
            register_never_die_function(function, ttl, args, kwargs)

        if cache_entry := CacheBucket.get(function_id, cache_key, ttl):
            return cache_entry[1]

        async with _ASYNC_LOCKS[function_id][cache_key]:
            if cache_entry := CacheBucket.get(function_id, cache_key, ttl):
                return cache_entry[1]

            result = await function(*args, **kwargs)
            CacheBucket.set(function_id, cache_key, result)
            return result

    return cast(F, async_wrapper)
