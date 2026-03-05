import sys
from collections.abc import Callable, Iterable, Mapping
from threading import Thread
from typing import Any


class CustomThread(Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}, Verbose=None):
        Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None
        self._exc_info = None  # captures exception if thread crashes

    def run(self):
        if self._target is not None:
            try:
                self._return = self._target(*self._args, **self._kwargs)
            except Exception:
                self._exc_info = sys.exc_info()

    def join(self):
        Thread.join(self)
        if self._exc_info is not None:
            raise self._exc_info[1].with_traceback(self._exc_info[2])
        return self._return