import time
from caching import cache

print("Testing never_die feature")


# Test function with never_die=True
@cache(ttl=5, never_die=True)
def expensive_operation(value):
    print(f"Executing expensive_operation({value})")
    time.sleep(2)  # Simulate expensive operation
    return f"Result for {value} at {time.time()}"


# Test function with regular cache
@cache(ttl=5)
def regular_operation(value):
    print(f"Executing regular_operation({value})")
    time.sleep(1)  # Simulate expensive operation
    return f"Regular result for {value} at {time.time()}"


print("\n--- Initial calls ---")
# Call both functions initially
result1 = expensive_operation("test1")
print(f"First call result: {result1}")

regular_result = regular_operation("regular")
print(f"Regular call result: {regular_result}")

print("\n--- Immediate second calls (both from cache) ---")
# Both should be served from cache
result2 = expensive_operation("test1")
print(f"Second call result: {result2}")

regular_result2 = regular_operation("regular")
print(f"Regular second call result: {regular_result2}")

print("\n--- Waiting for regular cache to expire (6 seconds) ---")
# Wait for TTL to expire
time.sleep(6)

print("\n--- After waiting, regular cache should expire, never_die should auto-refresh ---")
# This should be a fresh call for regular_operation
regular_result3 = regular_operation("regular")
print(f"Regular call after TTL: {regular_result3}")

# The never_die function should have auto-refreshed in the background
# and should return the cached value (which might be fresh)
result3 = expensive_operation("test1")
print(f"Third call result: {result3}")

print("\n--- Wait briefly to show background refresh happening ---")
time.sleep(2)

print("\n--- Another call to test auto-refresh ---")
result4 = expensive_operation("test1")
print(f"Fourth call result: {result4}")

# Let's demonstrate with a different parameter too
print("\n--- Call with different param ---")
other_result = expensive_operation("test2")
print(f"Different param result: {other_result}")

print("\nTest completed. Check the execution messages to see when functions actually ran.")

time.sleep(30)
