import time
import inspect
import asyncio
import functools
import threading
from collections import defaultdict
from typing import Any, Callable, TypeVar, DefaultDict, TypeAlias, Union, cast

Number: TypeAlias = Union[int, float]


F = TypeVar("F", bound=Callable[..., Any])

_CACHE: DefaultDict[int, dict[str, tuple[float, Any]]] = defaultdict(lambda: dict())
_SYNC_LOCKS: DefaultDict[int, DefaultDict[str, threading.Lock]] = defaultdict(lambda: defaultdict(threading.Lock))
_ASYNC_LOCKS: DefaultDict[int, DefaultDict[str, asyncio.Lock]] = defaultdict(lambda: defaultdict(asyncio.Lock))


def fetch_from_cache(function_id: int, cache_key: str, ttl: Number) -> tuple[float, Any] | None:
    if function_id not in _CACHE:
        return None
    if entry := _CACHE[function_id].get(cache_key):
        timestamp, _ = entry
        if time.time() < timestamp + ttl:
            return entry
    return None


def create_cache_key(*args: Any, **kwargs: Any) -> str:
    # Sort kwargs to ensure consistent key
    sorted_kwargs = sorted(kwargs.items())
    return str(hash((args, tuple(sorted_kwargs))))


def cache_result(function_id: int, cache_key: str, result: Any):
    _CACHE[function_id][cache_key] = (time.time(), result)


def async_decorator(function: F, ttl: Number) -> F:
    function_id = id(function)

    @functools.wraps(function)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        cache_key = create_cache_key(*args, **kwargs)

        if cache_entry := fetch_from_cache(function_id, cache_key, ttl):
            return cache_entry[1]

        async with _ASYNC_LOCKS[function_id][cache_key]:
            if cache_entry := fetch_from_cache(function_id, cache_key, ttl):
                return cache_entry[1]

            result = await function(*args, **kwargs)
            cache_result(function_id, cache_key, result)
            return result

    return cast(F, async_wrapper)


def sync_decorator(function: F, ttl: Number) -> F:
    function_id = id(function)

    @functools.wraps(function)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        cache_key = create_cache_key(*args, **kwargs)

        if cache_entry := fetch_from_cache(function_id, cache_key, ttl):
            return cache_entry[1]

        with _SYNC_LOCKS[function_id][cache_key]:
            if cache_entry := fetch_from_cache(function_id, cache_key, ttl):
                return cache_entry[1]

            result = function(*args, **kwargs)
            cache_result(function_id, cache_key, result)
            return result

    return cast(F, sync_wrapper)


def cache(ttl: Number = 300, never_die: bool = False) -> Callable[[F], F]:
    """
    A decorator that caches function results based on function id and arguments.
    Only allows one entry to the main function, making subsequent calls with the same arguments
    wait for the first call to complete and use its cached result.

    Args:
        ttl: Time to live for cached items in seconds, defaults to 5 minutes
        never_die: If True, the cache will never expire and will be recalculated based on the ttl

    Features:
        - Works for both sync and async functions
        - Only allows one execution at a time per function+args
        - Makes subsequent calls wait for the first call to complete
    """

    def decorator(function: F) -> F:
        if inspect.iscoroutinefunction(function):
            return async_decorator(function, ttl)
        return sync_decorator(function, ttl)

    return decorator
