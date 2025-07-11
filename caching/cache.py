import inspect
import threading
from typing import Callable, Hashable

from caching.types import Number, F
from caching._sync import sync_decorator
from caching._async import async_decorator
from caching.bucket import clear_expired_cached_items

_CACHE_CLEAR_THREAD: threading.Thread | None = None
_CACHE_CLEAR_LOCK: threading.Lock = threading.Lock()


def _start_cache_clear_thread():
    """This is to avoid memory leaks by clearing expired cache items periodically."""
    global _CACHE_CLEAR_THREAD
    with _CACHE_CLEAR_LOCK:
        if _CACHE_CLEAR_THREAD and _CACHE_CLEAR_THREAD.is_alive():
            return
        _CACHE_CLEAR_THREAD = threading.Thread(target=clear_expired_cached_items, daemon=True)
        _CACHE_CLEAR_THREAD.start()


def cache(
    ttl: Number = 300,
    never_die: bool = False,
    cache_key_func: Callable[[tuple, dict], Hashable] | None = None,
    ignore_fields: tuple[str, ...] = (),
) -> Callable[[F], F]:
    """
    A decorator that caches function results based on function id and arguments.
    Only allows one entry to the main function, making subsequent calls with the same arguments
    wait for the first call to complete and use its cached result.

    Args:
        ttl: Time to live for cached items in seconds, defaults to 5 minutes
        never_die: If True, the cache will never expire and will be recalculated based on the ttl
        cache_key_func: custom cache key function, used for more complex cache scenarios
        ignore_fields: tuple of strings with the function params that we want to ignore when creating the cache key

    Features:
        - Works for both sync and async functions
        - Only allows one execution at a time per function+args
        - Makes subsequent calls wait for the first call to complete
    """

    if cache_key_func and ignore_fields:
        raise Exception("Either cache_key_func or ignore_fields can be provided, but not both")

    _start_cache_clear_thread()

    def decorator(function: F) -> F:
        if inspect.iscoroutinefunction(function):
            return async_decorator(function, ttl, never_die, cache_key_func, ignore_fields)
        return sync_decorator(function, ttl, never_die, cache_key_func, ignore_fields)

    return decorator
