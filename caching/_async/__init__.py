import functools
import inspect
from typing import Any, cast, Callable, Hashable

from caching.types import Number, F
from caching.bucket import CacheBucket
from caching._async.lock import _ASYNC_LOCKS
from caching.utils.functions import get_function_id


def async_decorator(
    function: F,
    ttl: Number,
    never_die: bool = False,
    key_func: Callable[[tuple, dict], str] | None = None,
    ignore: tuple[str, ...] = (),
) -> F:
    from caching.features.never_die import register_never_die_function

    function_id = get_function_id(function)
    sig = inspect.signature(function)  # to map args→param names

    def _default_key(a: tuple, kw: dict) -> str:
        bound = sig.bind_partial(*a, **kw)
        bound.apply_defaults()
        items = tuple((name, value) for name, value in bound.arguments.items() if name not in ignore)
        return str(hash(items))

    make_key = key_func or _default_key

    @functools.wraps(function)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        skip_cache = kwargs.pop("skip_cache", False)
        cache_key = make_key(args, kwargs)
        if not isinstance(cache_key, str):
            cache_key = str(hash(cache_key))

        if never_die:
            register_never_die_function(function, ttl, args, kwargs)
        if cache_entry := CacheBucket.get(function_id, cache_key, ttl, skip_cache):
            return cache_entry[1]

        async with _ASYNC_LOCKS[function_id][cache_key]:
            if cache_entry := CacheBucket.get(function_id, cache_key, ttl, skip_cache):
                return cache_entry[1]

            result = await function(*args, **kwargs)
            CacheBucket.set(function_id, cache_key, result)
            return result

    return cast(F, async_wrapper)
