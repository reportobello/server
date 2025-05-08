from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def pipe(value: T, *args: Callable[[T], T]) -> T:
    acc = value

    for f in args:
        acc = f(acc)

    return acc
