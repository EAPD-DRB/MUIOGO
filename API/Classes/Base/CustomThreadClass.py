"""Thread subclass that captures return values and propagates exceptions."""

import sys
from collections.abc import Callable, Iterable, Mapping
from threading import Thread
from typing import Any, Optional, Tuple

# mypy does not expose Thread._target etc. – silence with type: ignore below.


class CustomThread(Thread):
    """A ``Thread`` subclass that stores target return values.

    After calling :meth:`join`, the caller can obtain the value
    returned by the *target* callable. If the target raised an
    exception, :meth:`join` re-raises it in the calling thread.

    Attributes:
        _return: Return value from the target callable.
        _exc_info: Captured ``sys.exc_info()`` triple when the target raises.
    """

    def __init__(
        self,
        group: None = None,
        target: Optional[Callable[..., Any]] = None,
        name: Optional[str] = None,
        args: Iterable[Any] = (),
        kwargs: Optional[Mapping[str, Any]] = None,
        Verbose: Optional[Any] = None,
    ) -> None:
        """Initialise a ``CustomThread``.

        Args:
            group: Reserved for future extension (must be *None*).
            target: Callable to be invoked in the new thread.
            name: Thread name.
            args: Positional arguments for *target*.
            kwargs: Keyword arguments for *target*.
            Verbose: Unused; kept for backward compatibility.
        """
        if kwargs is None:
            kwargs = {}
        Thread.__init__(self, group, target, name, args, kwargs)
        self._return: Any = None
        self._exc_info: Optional[Tuple[Any, ...]] = None  # captures exception if thread crashes

    def run(self) -> None:
        """Execute the target callable and store its return value.

        If the target raises, the exception info is captured so it can
        be re-raised in :meth:`join`.
        """
        if self._target is not None:  # type: ignore[attr-defined]
            try:
                self._return = self._target(*self._args, **self._kwargs)  # type: ignore[attr-defined]
            except Exception:
                self._exc_info = sys.exc_info()

    def join(self, timeout: Optional[float] = None) -> Any:
        """Wait for the thread to finish and return its result.

        Args:
            timeout: Maximum seconds to wait (``None`` waits forever).

        Returns:
            The value returned by the target callable.

        Raises:
            Exception: Re-raises any exception that occurred in the thread.
        """
        Thread.join(self, timeout=timeout)
        if self._exc_info is not None:
            raise self._exc_info[1].with_traceback(self._exc_info[2])
        return self._return