from typing import TypeAlias, TypeVar, Union, Any, Callable

Number: TypeAlias = Union[int, float]
F = TypeVar("F", bound=Callable[..., Any])
