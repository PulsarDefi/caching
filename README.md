# Python Caching Library

A simple and robust caching library for Python functions, supporting both synchronous and asynchronous code.

## Features

- Cache function results based on function ID and arguments
- Supports both synchronous and asynchronous functions
- Thread-safe locking to prevent duplicate calculations
- Configurable Time-To-Live (TTL) for cached items
- "Never Die" mode for functions that should keep cache refreshed automatically

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/caching.git
cd caching

# Install the package
pip install -e .
```

## Usage

### Basic Usage

```python
from caching import cache

# Cache function results for 5 minutes (default)
@cache()
def expensive_calculation(a, b):
    # Some expensive operation
    return a + b

# Cache with custom TTL (1 hour)
@cache(ttl=3600)
def another_calculation(a, b, c):
    # Some expensive operation
    return a * b * c
```

### Never Die Cache

The `never_die` feature ensures that cached values never expire by automatically refreshing them in the background:

```python
# Cache with never_die (automatic refresh)
@cache(ttl=300, never_die=True)
def critical_operation(user_id):
    # Expensive operation that should always be available from cache
    return fetch_data_from_database(user_id)
```

**How Never Die Works:**

1. When a function with `never_die=True` is first called, the result is cached
2. A background thread monitors all `never_die` functions
3. Before the cache expires (at 90% of TTL), the function is automatically called again
4. The cache is updated with the new result
5. If the refresh operation fails, the existing cached value is preserved
6. Clients always get fast response times by reading from cache

**Benefits:**

- Cache is always "warm" and ready to serve
- No user request ever has to wait for the expensive operation
- If backend services go down temporarily, the last successful result is still available
- Perfect for critical operations where latency must be minimized

## Testing

Run the test script to see the `never_die` feature in action:

```bash
python -m caching.test_never_die
```

## License

MIT
