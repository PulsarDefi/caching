import inspect
from typing import Callable

from caching.types import Number, F
from caching._sync import sync_decorator
from caching._async import async_decorator


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
        return sync_decorator(function, ttl, never_die)

    return decorator
