import time
import asyncio
import threading
import functools
import inspect
from typing import Callable, Hashable
from dataclasses import dataclass
from asyncio import AbstractEventLoop
from concurrent.futures import Future as ConcurrentFuture

from caching.config import logger
from caching.types import Number
from caching.bucket import CacheBucket
from caching._sync.lock import _SYNC_LOCKS
from caching._async.lock import _ASYNC_LOCKS
from caching.utils.functions import get_function_id


_NEVER_DIE_THREAD: threading.Thread | None = None
_NEVER_DIE_LOCK: threading.Lock = threading.Lock()
_NEVER_DIE_REGISTRY: list["NeverDieCacheEntry"] = []
_NEVER_DIE_CACHE_THREADS: dict[str, threading.Thread] = {}
_NEVER_DIE_CACHE_FUTURES: dict[str, ConcurrentFuture] = {}


@dataclass
class NeverDieCacheEntry:
    function: Callable
    ttl: Number
    args: tuple
    kwargs: dict
    cache_key_func: Callable
    ignore_fields: tuple[str, ...]
    loop: AbstractEventLoop | None

    @functools.cached_property
    def id(self) -> str:
        return get_function_id(self.function)

    @functools.cached_property
    def cache_key(self) -> str:
        function_signature = inspect.signature(self.function)
        return CacheBucket.create_cache_key(
            function_signature, self.cache_key_func, self.ignore_fields, *self.args, **self.kwargs
        )

    def __eq__(self, other: "NeverDieCacheEntry") -> bool:
        if not isinstance(other, NeverDieCacheEntry):
            return False
        return self.id == other.id and self.cache_key == other.cache_key

    def __hash__(self) -> int:
        return hash((self.id, self.cache_key))


def _run_sync_function_and_cache(entry: NeverDieCacheEntry):
    """Run a function and cache its result"""
    with _SYNC_LOCKS[entry.id][entry.cache_key]:
        try:
            result = entry.function(*entry.args, *entry.kwargs)
            CacheBucket.set(entry.id, entry.cache_key, result, entry.ttl)
        except:
            logger.debug(f"Exception caching {entry.function.__qualname__}", exc_info=True)


async def _run_async_function_and_cache(entry: NeverDieCacheEntry):
    """Run a function and cache its result"""
    async with _ASYNC_LOCKS[entry.id][entry.cache_key]:
        try:
            result = await entry.function(*entry.args, **entry.kwargs)
            CacheBucket.set(entry.id, entry.cache_key, result, entry.ttl)
        except:
            logger.debug(f"Exception caching {entry.function.__qualname__}", exc_info=True)


def _cache_is_being_set(entry: NeverDieCacheEntry) -> bool:
    if entry.loop:
        return entry.cache_key in _NEVER_DIE_CACHE_FUTURES and not _NEVER_DIE_CACHE_FUTURES[entry.cache_key].done()
    return entry.cache_key in _NEVER_DIE_CACHE_THREADS and _NEVER_DIE_CACHE_THREADS[entry.cache_key].is_alive()


def _clear_dead_futures():
    """Clear dead futures from the cache future registry"""
    for cache_key, thread in list(_NEVER_DIE_CACHE_FUTURES.items()):
        if thread.done():
            del _NEVER_DIE_CACHE_FUTURES[cache_key]


def _clear_dead_threads():
    """Clear dead threads from the cache thread registry"""
    for cache_key, thread in list(_NEVER_DIE_CACHE_THREADS.items()):
        if not thread.is_alive():
            del _NEVER_DIE_CACHE_THREADS[cache_key]


def _refresh_never_die_caches():
    """Background thread function that periodically refreshes never_die cache entries"""
    while True:
        try:
            for entry in list(_NEVER_DIE_REGISTRY):
                if not CacheBucket.is_cache_expired(entry.id, entry.cache_key):
                    continue
                if _cache_is_being_set(entry):
                    continue

                if entry.loop:  # async
                    if entry.loop.is_closed():
                        logger.debug(f"Loop is closed for {entry.function.__qualname__}, skipping future creation")
                        continue
                    try:
                        coroutine = _run_async_function_and_cache(entry)
                        future = asyncio.run_coroutine_threadsafe(coroutine, entry.loop)
                    except RuntimeError:
                        coroutine.close()
                        logger.debug(f"Loop is closed for {entry.function.__qualname__}, skipping future creation")
                        continue
                    _NEVER_DIE_CACHE_FUTURES[entry.cache_key] = future
                    continue
                thread = threading.Thread(target=_run_sync_function_and_cache, args=(entry,), daemon=True)
                thread.start()
                _NEVER_DIE_CACHE_THREADS[entry.cache_key] = thread
        finally:
            time.sleep(0.1)
            _clear_dead_futures()
            _clear_dead_threads()


def _start_never_die_thread():
    """Start the background thread if it's not already running"""
    global _NEVER_DIE_THREAD
    with _NEVER_DIE_LOCK:
        if _NEVER_DIE_THREAD and _NEVER_DIE_THREAD.is_alive():
            return
        _NEVER_DIE_THREAD = threading.Thread(target=_refresh_never_die_caches, daemon=True)
        _NEVER_DIE_THREAD.start()


def register_never_die_function(
    function: Callable,
    ttl: Number,
    args: tuple,
    kwargs: dict,
    cache_key_func: Callable[[tuple, dict], Hashable] | None,
    ignore_fields: tuple[str, ...],
) -> None:
    """Register a function for never_die cache refreshing"""
    is_async = inspect.iscoroutinefunction(function)

    entry = NeverDieCacheEntry(
        function, ttl, args, kwargs, cache_key_func, ignore_fields, asyncio.get_event_loop() if is_async else None
    )

    with _NEVER_DIE_LOCK:
        if entry not in _NEVER_DIE_REGISTRY:
            _NEVER_DIE_REGISTRY.append(entry)

    _start_never_die_thread()
