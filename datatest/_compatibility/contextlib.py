"""compatibility layer for contextlib (Python standard library)"""
from __future__ import absolute_import
from contextlib import *
from . import functools


try:
    ContextDecorator  # New in Python 3.2
except NameError:
    # Adapted from Python 3.6 standard libary.
    class ContextDecorator(object):
        def _recreate_cm(self):  # The `_recreate_cm` method is a private
            return self          # interface for _GeneratorContextManager.
                                 # See issue #11647 for details.

        def __call__(self, func):
            @functools.wraps(func)
            def inner(*args, **kwds):
                with self._recreate_cm():
                    return func(*args, **kwds)
            return inner


try:
    suppress  # New in Python 3.4
except NameError:
    # Adapted from Python 3.6 standard libary.
    class suppress(object):
        """Context manager to suppress specified exceptions."""
        def __init__(self, *exceptions):
            self._exceptions = exceptions

        def __enter__(self):
            pass

        def __exit__(self, exctype, excinst, exctb):
            return exctype is not None and issubclass(exctype, self._exceptions)
