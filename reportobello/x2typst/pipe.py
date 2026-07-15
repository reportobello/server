from collections.abc import Callable


def pipe[T](value: T, *args: Callable[[T], T]) -> T:
    acc = value

    for f in args:
        acc = f(acc)

    return acc
