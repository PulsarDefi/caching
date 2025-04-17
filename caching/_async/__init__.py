import asyncio
import functools
from collections import defaultdict
from typing import DefaultDict, Any, cast

from caching.types import Number, F
from caching.bucket import CacheBucket

_ASYNC_LOCKS: DefaultDict[int, DefaultDict[str, asyncio.Lock]] = defaultdict(lambda: defaultdict(asyncio.Lock))


def async_decorator(function: F, ttl: Number) -> F:
    function_id = id(function)

    @functools.wraps(function)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        cache_key = CacheBucket.create_cache_key(*args, **kwargs)

        if cache_entry := CacheBucket.get(function_id, cache_key, ttl):
            return cache_entry[1]

        async with _ASYNC_LOCKS[function_id][cache_key]:
            if cache_entry := CacheBucket.get(function_id, cache_key, ttl):
                return cache_entry[1]

            result = await function(*args, **kwargs)
            CacheBucket.set(function_id, cache_key, result)
            return result

    return cast(F, async_wrapper)
