import time
import logging
import threading
import functools
from collections import defaultdict
from typing import DefaultDict, Any, cast, Tuple, Callable

from caching.types import Number, F
from caching.bucket import CacheBucket

_SYNC_LOCKS: DefaultDict[int, DefaultDict[str, threading.Lock]] = defaultdict(lambda: defaultdict(threading.Lock))

_NEVER_DIE_THREAD = None
_NEVER_DIE_LOCK = threading.Lock()
_NEVER_DIE_STOP_EVENT = threading.Event()
_NEVER_DIE_REGISTRY: list["NeverDieCacheEntry"] = []
_NEVER_DIE_CACHE_THREADS: dict[str, threading.Thread] = {}

from dataclasses import dataclass


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


def run_function_and_cache(entry: NeverDieCacheEntry):
    """Run a function and cache its result"""
    with _SYNC_LOCKS[entry.id][entry.cache_key]:
        try:
            print(f"[LOOP_CACHING] {entry.function.__name__} with args {entry.args} and kwargs {entry.kwargs}")
            result = entry.function(*entry.args, *entry.kwargs)
            CacheBucket.set(entry.id, entry.cache_key, result)
        except:
            logging.debug(f"Error caching {entry.function.__qualname__}", exc_info=True)


def thread_is_not_running(cache_key: str) -> bool:
    return cache_key not in _NEVER_DIE_CACHE_THREADS or not _NEVER_DIE_CACHE_THREADS[cache_key].is_alive()


def _refresh_never_die_caches():
    """Background thread function that periodically refreshes never_die cache entries"""
    while not _NEVER_DIE_STOP_EVENT.is_set():
        try:
            for entry in list(_NEVER_DIE_REGISTRY):
                if not CacheBucket.is_cache_expired(entry.id, entry.cache_key, entry.ttl):
                    continue
                if thread_is_not_running(entry.cache_key):
                    thread = threading.Thread(target=run_function_and_cache, args=(entry,), daemon=True)
                    thread.start()
                    _NEVER_DIE_CACHE_THREADS[entry.cache_key] = thread
        finally:
            time.sleep(0.1)
            for cache_key, thread in list(_NEVER_DIE_CACHE_THREADS.items()):
                if not thread.is_alive():
                    del _NEVER_DIE_CACHE_THREADS[cache_key]


def start_never_die_thread():
    """Start the background thread if it's not already running"""
    global _NEVER_DIE_THREAD
    with _NEVER_DIE_LOCK:
        if _NEVER_DIE_THREAD is None or not _NEVER_DIE_THREAD.is_alive():
            _NEVER_DIE_STOP_EVENT.clear()
            _NEVER_DIE_THREAD = threading.Thread(
                target=_refresh_never_die_caches, daemon=True, name="never_die_cache_refresh"
            )
            _NEVER_DIE_THREAD.start()


def _register_never_die_function(func: Callable, ttl: Number, args: Tuple, kwargs: dict) -> None:
    """Register a function for never_die cache refreshing"""
    with _NEVER_DIE_LOCK:
        entry = NeverDieCacheEntry(func, ttl, args, kwargs)
        if entry not in _NEVER_DIE_REGISTRY:
            _NEVER_DIE_REGISTRY.append(entry)
    start_never_die_thread()


def sync_decorator(function: F, ttl: Number, never_die: bool = False) -> F:
    function_id = id(function)

    @functools.wraps(function)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        cache_key = CacheBucket.create_cache_key(*args, **kwargs)

        if never_die:
            _register_never_die_function(function, ttl, args, kwargs)

        if cache_entry := CacheBucket.get(function_id, cache_key, ttl):
            return cache_entry[1]

        with _SYNC_LOCKS[function_id][cache_key]:
            if cache_entry := CacheBucket.get(function_id, cache_key, ttl):
                return cache_entry[1]

            print(f"[NORMAL_CACHING] {function.__name__} with args {args} and kwargs {kwargs}")
            result = function(*args, **kwargs)
            CacheBucket.set(function_id, cache_key, result)
            return result

    return cast(F, sync_wrapper)
