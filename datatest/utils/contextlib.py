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
