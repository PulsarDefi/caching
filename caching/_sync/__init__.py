import threading
import functools
from collections import defaultdict
from typing import DefaultDict, Any, cast

from caching.types import Number, F
from caching.bucket import CacheBucket

_SYNC_LOCKS: DefaultDict[int, DefaultDict[str, threading.Lock]] = defaultdict(lambda: defaultdict(threading.Lock))


def sync_decorator(function: F, ttl: Number) -> F:
    function_id = id(function)

    @functools.wraps(function)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        cache_key = CacheBucket.create_cache_key(*args, **kwargs)

        if cache_entry := CacheBucket.get(function_id, cache_key, ttl):
            return cache_entry[1]

        with _SYNC_LOCKS[function_id][cache_key]:
            if cache_entry := CacheBucket.get(function_id, cache_key, ttl):
                return cache_entry[1]

            result = function(*args, **kwargs)
            CacheBucket.set(function_id, cache_key, result)
            return result

    return cast(F, sync_wrapper)
