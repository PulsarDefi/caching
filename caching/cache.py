import time
import inspect
import asyncio
import functools
import threading
from typing import Any, Callable, TypeVar, cast


F = TypeVar("F", bound=Callable[..., Any])

_CACHE: dict[int, dict[str, tuple[float, Any]]] = {}
_SYNC_LOCKS: dict[int, dict[str, threading.Lock]] = {}
_ASYNC_LOCKS: dict[int, dict[str, asyncio.Lock]] = {}


def fetch_from_cache(func_id: int, cache_key: str, ttl: int) -> tuple[float, Any] | None:
    if func_id not in _CACHE:
        return None
    if entry := _CACHE[func_id].get(cache_key):
        timestamp, result = entry
        if time.time() < timestamp + ttl:
            return result
    return None


# Create cache key from arguments
def create_cache_key(*args: Any, **kwargs: Any) -> str:
    # Sort kwargs to ensure consistent key
    sorted_kwargs = sorted(kwargs.items())
    return str(hash((args, tuple(sorted_kwargs))))


def cached(ttl: int = 300, never_die: bool = False) -> Callable[[F], F]:
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

    def decorator(func: F) -> F:
        func_id = id(func)

        if func_id not in _CACHE:
            _CACHE[func_id] = {}

        # Handle async functions
        if inspect.iscoroutinefunction(func):
            # Initialize async locks for this function
            if func_id not in _ASYNC_LOCKS:
                _ASYNC_LOCKS[func_id] = {}

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                cache_key = create_cache_key(*args, **kwargs)

                # Create lock for this specific args combination if it doesn't exist
                if cache_key not in _ASYNC_LOCKS[func_id]:
                    _ASYNC_LOCKS[func_id][cache_key] = asyncio.Lock()

                # Check cache before acquiring lock (optimization)
                if cache_entry := fetch_from_cache(func_id, cache_key, ttl):
                    return cache_entry

                # Acquire lock to ensure only one call executes the function
                async with _ASYNC_LOCKS[func_id][cache_key]:
                    # Check cache again after acquiring lock
                    if cache_entry := fetch_from_cache(func_id, cache_key, ttl):
                        return cache_entry

                    # Execute function if no valid cache entry
                    result = await func(*args, **kwargs)
                    _CACHE[func_id][cache_key] = (time.time(), result)
                    return result

            return cast(F, async_wrapper)

        # Handle synchronous functions - using threading.Lock, not asyncio
        else:
            # Initialize sync locks for this function
            if func_id not in _SYNC_LOCKS:
                _SYNC_LOCKS[func_id] = {}

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                cache_key = create_cache_key(*args, **kwargs)

                # Create lock for this specific args combination if it doesn't exist
                if cache_key not in _SYNC_LOCKS[func_id]:
                    _SYNC_LOCKS[func_id][cache_key] = threading.Lock()

                # Check cache before acquiring lock (optimization)
                if cache_entry := fetch_from_cache(func_id, cache_key, ttl):
                    return cache_entry

                # Use threading.Lock for synchronous functions
                with _SYNC_LOCKS[func_id][cache_key]:
                    # Check cache again after acquiring lock
                    if cache_entry := fetch_from_cache(func_id, cache_key, ttl):
                        return cache_entry

                    # Execute function if no valid cache entry
                    result = func(*args, **kwargs)
                    _CACHE[func_id][cache_key] = (time.time(), result)
                    return result

            return cast(F, sync_wrapper)

    return decorator
