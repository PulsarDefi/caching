import functools
from typing import Any, cast, Callable, Hashable

from caching.types import Number, F
from caching.bucket import CacheBucket
from caching._async.lock import _ASYNC_LOCKS
from caching.utils.functions import get_function_id


def async_decorator(
    function: F,
    ttl: Number,
    never_die: bool = False,
    key_func: Callable[[tuple, dict], Hashable] | None = None,
    ignore_fields: tuple[str, ...] = (),
) -> F:
    if key_func is not None and ignore_fields:
        raise Exception(f"Either {key_func} or {ignore_fields} should be provided")

    from caching.features.never_die import register_never_die_function

    function_id = get_function_id(function)

    @functools.wraps(function)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        skip_cache = kwargs.pop("skip_cache", False)
        cache_key = CacheBucket.create_cache_key(function, key_func, ignore_fields, *args, **kwargs)

        if never_die:
            register_never_die_function(function, ttl, args, kwargs, key_func, ignore_fields)
        if cache_entry := CacheBucket.get(function_id, cache_key, skip_cache):
            return cache_entry.result

        async with _ASYNC_LOCKS[function_id][cache_key]:
            if cache_entry := CacheBucket.get(function_id, cache_key, skip_cache):
                return cache_entry.result

            result = await function(*args, **kwargs)
            CacheBucket.set(function_id, cache_key, result, ttl)
            return result

    return cast(F, async_wrapper)
