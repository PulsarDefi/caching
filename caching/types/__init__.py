from typing import Any, Callable, Hashable, TypeAlias, TypedDict, TypeVar, Union

Number: TypeAlias = Union[int, float]
CacheKeyFunction: TypeAlias = Callable[[tuple, dict], Hashable]

F = TypeVar("F", bound=Callable[..., Any])


class CacheKwargs(TypedDict, total=False):
    """
    ### Description
    This type can be used in conjuction with `Unpack` to provide static type
    checking for the parameters added by the `@cache()` decorator.

    This type is completely optional and `skip_cache` will work regardless
    of what static type checkers complain about.

    ### Example
    ```
    @cache()
    def function_with_cache(**_: Unpack[CacheKwargs]): ...

    # pylance/pyright should not complain
    function_with_cache(skip_cache=True)
    ```

    ### Notes
    Prior to Python 3.11, `Unpack` is only available with typing_extensions
    """

    skip_cache: bool
