"""compatibility layer for contextlib (Python standard library)"""
from __future__ import absolute_import
from contextlib import *


try:
    redirect_stderr  # New in 3.5
except NameError:
    # Adapted from Python 3.5 Standard Library.
    import sys as _sys
    class _RedirectStream:
        _stream = None

        def __init__(self, new_target):
            self._new_target = new_target
            self._old_targets = []

        def __enter__(self):
            self._old_targets.append(getattr(_sys, self._stream))
            setattr(_sys, self._stream, self._new_target)
            return self._new_target

        def __exit__(self, exctype, excinst, exctb):
            setattr(_sys, self._stream, self._old_targets.pop())

    class redirect_stderr(_RedirectStream):
        """Context manager for temporarily redirecting stderr to
        another file.
        """
        _stream = 'stderr'


try:
    redirect_stdout  # New in 3.4
except NameError:
    class redirect_stdout(_RedirectStream):
        """Context manager for temporarily redirecting stdout to
        another file.

            # How to send help() to stderr
            with redirect_stdout(sys.stderr):
                help(dir)

            # How to write help() to a file
            with open('help.txt', 'w') as f:
                with redirect_stdout(f):
                    help(pow)
        """
        _stream = 'stdout'
