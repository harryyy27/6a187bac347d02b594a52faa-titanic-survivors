"""Reusable timeout wrapper/decorator for test functions.

Runs the wrapped test in a background thread and raises ``TimeoutError``
(naming the test, its file, and its starting line) if it does not finish
within the timeout. Supports both bare-decorator and parameterized usage:

    @testWrapperTimeout
    def test_something():
        ...

    @testWrapperTimeout(timeout=5)
    def test_something_else():
        ...
"""
from __future__ import annotations

import functools
import os
import threading
from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

DEFAULT_TIMEOUT_SECONDS = 10


def _make_wrapper(func: F, timeout: float) -> F:
    filename = os.path.abspath(func.__code__.co_filename)
    lineno = func.__code__.co_firstlineno
    name = func.__name__

    @functools.wraps(func)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        result: dict[str, Any] = {}
        error: dict[str, BaseException] = {}

        def target() -> None:
            try:
                result["value"] = func(*args, **kwargs)
            except BaseException as exc:  # noqa: BLE001
                error["value"] = exc

        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout)

        if thread.is_alive():
            raise TimeoutError(
                f"Test '{name}' in file '{filename}' (starting at line {lineno}) "
                f"exceeded timeout of {timeout} seconds"
            )

        if "value" in error:
            raise error["value"]

        return result.get("value")

    return wrapped  # type: ignore[return-value]


def testWrapperTimeout(func: F | None = None, *, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> Any:
    """Decorator enforcing a timeout on a test function.

    Usable directly (``@testWrapperTimeout``) or parameterized
    (``@testWrapperTimeout(timeout=5)``).
    """
    if func is not None:
        return _make_wrapper(func, DEFAULT_TIMEOUT_SECONDS)

    def decorator(inner_func: F) -> F:
        return _make_wrapper(inner_func, timeout)

    return decorator


# Its name matches pytest's default `test*` discovery pattern, so importing
# it into a test module would otherwise make pytest collect the decorator
# itself as a bogus test item. Mark it explicitly as not a test.
testWrapperTimeout.__test__ = False  # type: ignore[attr-defined]
