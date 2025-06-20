from caching.types import F


def get_function_id(function: F) -> str:
    """
    Returns the unique identifier for the function, which is a combination of its module and qualified name.
    """
    return f"{function.__module__}.{function.__qualname__}"
