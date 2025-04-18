import time
import threading
import functools
from typing import Callable
from dataclasses import dataclass

from caching.config import logger
from caching.types import Number
from caching.bucket import CacheBucket
from caching._sync.lock import _SYNC_LOCKS

_NEVER_DIE_THREAD: threading.Thread | None = None
_NEVER_DIE_LOCK: threading.Lock = threading.Lock()
_NEVER_DIE_REGISTRY: list["NeverDieCacheEntry"] = []
_NEVER_DIE_CACHE_THREADS: dict[str, threading.Thread] = {}


@dataclass
class NeverDieCacheEntry:
    function: Callable
    ttl: Number
    args: tuple
    kwargs: dict

    @property
    def id(self):
        return id(self.function)

    @functools.cached_property
    def cache_key(self):
        return CacheBucket.create_cache_key(*self.args, **self.kwargs)


def _run_function_and_cache(entry: NeverDieCacheEntry):
    """Run a function and cache its result"""
    with _SYNC_LOCKS[entry.id][entry.cache_key]:
        try:
            result = entry.function(*entry.args, *entry.kwargs)
            CacheBucket.set(entry.id, entry.cache_key, result)
        except:
            logger.debug(f"Exception caching {entry.function.__qualname__}", exc_info=True)


def _thread_is_not_running(cache_key: str) -> bool:
    return cache_key not in _NEVER_DIE_CACHE_THREADS or not _NEVER_DIE_CACHE_THREADS[cache_key].is_alive()


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
                if not CacheBucket.is_cache_expired(entry.id, entry.cache_key, entry.ttl):
                    continue
                if _thread_is_not_running(entry.cache_key):
                    thread = threading.Thread(target=_run_function_and_cache, args=(entry,), daemon=True)
                    thread.start()
                    _NEVER_DIE_CACHE_THREADS[entry.cache_key] = thread
        finally:
            time.sleep(0.1)
            _clear_dead_threads()


def _start_never_die_thread():
    """Start the background thread if it's not already running"""
    global _NEVER_DIE_THREAD
    with _NEVER_DIE_LOCK:
        if _NEVER_DIE_THREAD and _NEVER_DIE_THREAD.is_alive():
            return
        _NEVER_DIE_THREAD = threading.Thread(target=_refresh_never_die_caches, daemon=True)
        _NEVER_DIE_THREAD.start()


def register_never_die_function(func: Callable, ttl: Number, args: tuple, kwargs: dict) -> None:
    """Register a function for never_die cache refreshing"""
    with _NEVER_DIE_LOCK:
        entry = NeverDieCacheEntry(func, ttl, args, kwargs)
        if entry not in _NEVER_DIE_REGISTRY:
            _NEVER_DIE_REGISTRY.append(entry)
    _start_never_die_thread()
