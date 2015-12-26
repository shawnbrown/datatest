"""Running tests"""
import inspect
import os
import re
import sys
import unittest
import warnings

from ._functools import wraps
from .case import DataAssertionError

try:
    from unittest import TextTestResult
except ImportError:
    from unittest import _TextTestResult as TextTestResult


# @required: A decorator for test classes or methods that must pass before
# subsequent tests will run.  When a "required" test fails, DataTestRunner
# will immediately stop (this behavior is similar to the "--failfast" command
# line argument).
def required(test_item):
    """Mark the test as required.  If the test fails when ran, DataTestRunner
    will stop.

    """
    test_item.__datatest_required__ = True
    return test_item


class DataTestResult(TextTestResult):
    """A datatest result class that can print formatted text results to
    a stream.

    Used by DataTestRunner.

    """
    def __init__(self, stream=None, descriptions=None, verbosity=None, ignore=False):
        self.ignore = ignore
        TextTestResult.__init__(self, stream, descriptions, verbosity)

    def _stop_if_required(self, test):
        """Stop test runner if the given *test* is required or is a member of
        a class that is required.

        This method checks for a __datatest_required__ property in a test
        class or test method--tests are marked as "required" using the
        @required decorator.  If the property is found and is True, then
        stop() is called to halt the test suite.

        """
        if self.ignore:
            return  # <- If we're ignoring the 'required' flag, then EXIT!

        required_class = getattr(test, '__datatest_required__', False)
        if not required_class:
            test_method_name = getattr(test, '_testMethodName')
            test_method = getattr(test, test_method_name)
            required_method = getattr(test_method, '__datatest_required__', False)

        if required_class or required_method:
            self.stop()  # <- sets "self.shouldStop = True"

    def addError(self, test, err):
        """Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info().
        """
        self._stop_if_required(test)
        TextTestResult.addError(self, test, err)

    def addFailure(self, test, err):
        """Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info().
        """
        self._stop_if_required(test)

        if err[0] == DataAssertionError:
            exctype, value, tb = err          # Unpack tuple.
            tb = HideInternalStackFrames(tb)  # Hide internal frames.
            value._verbose = self.showAll     # Set verbose flag (True/False).
            err = (exctype, value, tb)        # Repack tuple.

        TextTestResult.addFailure(self, test, err)

    def addUnexpectedSuccess(self, test):
        """Called when a test was expected to fail, but succeed."""
        self._stop_if_required(test)
        if hasattr(self, 'addUnexpectedSuccess'):
            TextTestResult.addUnexpectedSuccess(self, test)


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


class DataTestRunner(unittest.TextTestRunner):
    """A data test runner (wraps unittest.TextTestRunner) that displays
    results in textual form.
    """
    resultclass = DataTestResult

    def __init__(self, stream=None, descriptions=True, verbosity=1,
                 failfast=False, buffer=False, resultclass=None, ignore=False):
        if stream is None:
            stream = sys.stderr
        self.ignore = ignore
        unittest.TextTestRunner.__init__(self,
                                         stream=stream,
                                         descriptions=descriptions,
                                         verbosity=verbosity,
                                         failfast=failfast,
                                         buffer=buffer,
                                         resultclass=resultclass)

    def _makeResult(self):
        return self.resultclass(self.stream, self.descriptions, self.verbosity, self.ignore)
        #return self.resultclass(self.stream, self.descriptions, self.verbosity)

    def run(self, test):
        """Run the given tests in order of line number from source file."""
        test = _sort_tests(test)  # Sort tests by line number.

        # Get test modules.
        modules = []
        for one_test in test._tests:
            mod = _get_module(one_test)
            if mod not in modules:
                modules.append(mod)

        # Build banner output from file names and docstrings.
        docstrings = []
        for mod in modules:
            docstrings.append(mod.__file__)
            doc = mod.__doc__
            if doc and self.verbosity > 1:
                docstrings.append('')
                docstrings.append(doc.rstrip().lstrip('\n'))
                docstrings.append('')
        docstrings = '\n'.join(docstrings)

        # Write module docstrings, run tests.
        separator = '=' * 70
        self.stream.writeln(separator)
        self.stream.writeln(docstrings)
        return unittest.TextTestRunner.run(self, test)


# Fix stderr redirect behavior inherited from older versions of unittest (see
# issue 10786 <http://bugs.python.org/issue10786>).
if sys.version_info[:2] in [(3, 1), (2, 6)]:  # 3.1 and 2.6
    def __init__(self, stream=None, descriptions=1, verbosity=1, ignore=False):
        if stream is None:
            stream = sys.stderr
        self.ignore = ignore
        unittest.TextTestRunner.__init__(self,
                                         stream=stream,
                                         descriptions=descriptions,
                                         verbosity=verbosity)
    DataTestRunner.__init__ = __init__


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


def _get_module(one_test):
    """Accepts a single test, returns module name."""
    method = getattr(one_test, one_test._testMethodName)
    while hasattr(method, '_wrapped'):  # If object is wrapped with a
        method = method._wrapped        # decorator, unwrap it.
    return sys.modules[method.__module__]
