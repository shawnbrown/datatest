"""Running tests"""
import inspect
import os
import re
import unittest
import warnings
from datatest import DataAssertionError

try:
    from unittest import TextTestResult
except ImportError:
    from unittest import _TextTestResult as TextTestResult


class HideInternalStackFrames(object):
    """Wrapper for traceback to hide extraneous stack frames that
    originate from within the datatest module itself.

    Without this wrapper, tracebacks will contain frames from
    "datatest/case.py":

        Traceback (most recent call last):
          File "test_my_data.py", line 43, in test_codes
            self.assertValueSet('column1')
          File "datatest/case.py", line 274, in assertValueSet
            self.fail(msg, extra+missing)
          File "datatest/case.py", line 170, in fail
            raise DataAssertionError(msg, diff)
        datatest.case.DataAssertionError: different 'column1' values:
         ExtraValue('foo'),
         ExtraValue('bar')

    A wrapped version hides these internal frames:

        Traceback (most recent call last):
          File "test_my_data.py", line 43, in test_codes
            self.assertValueSet('column1')
        datatest.case.DataAssertionError: different 'column1' values:
         ExtraValue('foo'),
         ExtraValue('bar')

    """
    def __init__(self, tb):
        self._tb = tb

    def __getattr__(self, name):
        return getattr(self._tb, name)

    @property
    def tb_next(self):
        # Check remaining traceback frames.
        are_internal = []
        frame = self._tb.tb_next
        while frame:
            is_internal = '__datatest' in frame.tb_frame.f_globals
            are_internal.append(is_internal)
            frame = frame.tb_next

        # Truncate if all remaining are internal, else return next frame.
        if all(are_internal):
            return None
        return self.__class__(self._tb.tb_next)


class DataTestResult(TextTestResult):
    def addFailure(self, test, err):
        if err[0] == DataAssertionError:
            exctype, value, tb = err
            tb = HideInternalStackFrames(tb)  # <- HIDES INTERNALS!!!
            err = (exctype, value, tb)

        TextTestResult.addFailure(self, test, err)


def _sort_key(test):
    """Accepts test method, returns module name and line number."""
    method = getattr(test, test._testMethodName)
    while hasattr(method, '_wrapped'):  # If object is wrapped with a
        method = method._wrapped        # decorator, unwrap it.

    try:
        lineno = inspect.getsourcelines(method)[1]
    except IOError:
        warnings.warn('Unable to sort {0}'.format(method))
        lineno = 0
    return (method.__module__, lineno)


def _sort_tests(suite, key=_sort_key):
    """Return suite of tests sorted by line number."""
    def flatten(ste):
        for tst in ste:
            if isinstance(tst, unittest.TestSuite):
                for sub in flatten(tst):
                    yield sub
            else:
                yield tst
    flattened = flatten(suite)
    flattened = sorted(flattened, key=key)
    return unittest.TestSuite(flattened)


class DataTestRunner(unittest.TextTestRunner):
    """A data test runner (wraps unittest.TextTestRunner) that displays
    results in textual form.
    """
    resultclass = DataTestResult

    def run(self, test):
        """Run the given tests in order of line number from source file."""
        #self.stream.writeln("RUNNING DATA TESTS:")  # !!! TODO: Replace with docstring?
        test = _sort_tests(test)
        return unittest.TextTestRunner.run(self, test)
