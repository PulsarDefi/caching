import asyncio
import pytest
from caching.cache import cache
from itertools import count

TTL = 1
_global_counter = count()


@pytest.fixture()
def function_with_cache():

    @cache(ttl=TTL)
    async def async_cached_function(arg=None) -> int:
        """Return a unique value on each real function call"""
        return next(_global_counter)

    return async_cached_function


@pytest.mark.asyncio
async def test_basic_async_caching(function_with_cache):
    result1 = await function_with_cache()
    result2 = await function_with_cache()

    assert result1 == result2


@pytest.mark.asyncio
async def test_cache_expiration(function_with_cache):
    result1 = await function_with_cache()
    await asyncio.sleep(TTL + 0.1)  # wait for cache expiration
    result2 = await function_with_cache()

    assert result1 != result2


@pytest.mark.asyncio
async def test_concurrent_access(function_with_cache):
    tasks = [function_with_cache() for _ in range(5)]
    results = await asyncio.gather(*tasks)

    first_result = results[0]
    assert all(r == first_result for r in results)


@pytest.mark.asyncio
async def test_different_arguments(function_with_cache):
    result1 = await function_with_cache()
    result2 = await function_with_cache("different")

    assert result1 != result2

    result3 = await function_with_cache()

    assert result1 == result3


@pytest.mark.asyncio
async def test_separate_cache_keys(function_with_cache):
    result1 = await function_with_cache("key1")
    result2 = await function_with_cache("key2")

    assert result1 != result2

    result1_again = await function_with_cache("key1")
    result2_again = await function_with_cache("key2")

    assert result1 == result1_again
    assert result2 == result2_again
