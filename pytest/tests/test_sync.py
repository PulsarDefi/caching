import time
import pytest
from caching.cache import cache
from itertools import count

TTL = 0.1
_global_counter = count()


@pytest.fixture()
def function_with_cache():

    @cache(ttl=TTL)
    def sync_cached_function(arg=None) -> int:
        """Return a unique value on each real function call"""
        return next(_global_counter)

    return sync_cached_function


def test_basic_sync_caching(function_with_cache):
    result1 = function_with_cache()
    result2 = function_with_cache()

    assert result1 == result2


def test_cache_expiration(function_with_cache):
    result1 = function_with_cache()
    time.sleep(TTL + 0.1)  # wait for cache expiration
    result2 = function_with_cache()

    assert result1 != result2


def test_different_arguments(function_with_cache):
    result1 = function_with_cache()
    result2 = function_with_cache("different")

    assert result1 != result2

    result3 = function_with_cache()

    assert result1 == result3


def test_separate_cache_keys(function_with_cache):
    result1 = function_with_cache("key1")
    result2 = function_with_cache("key2")

    assert result1 != result2

    result1_again = function_with_cache("key1")
    result2_again = function_with_cache("key2")

    assert result1 == result1_again
    assert result2 == result2_again
