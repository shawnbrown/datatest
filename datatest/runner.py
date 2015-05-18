"""Running tests"""

import inspect
import unittest
import warnings


class DataTestRunner(unittest.TextTestRunner):
    """A data test runner (wraps unittest.TextTestRunner) that displays
    results in textual form.
    """
    def run(self, test):
        """Run the given tests in order of line number from source file."""
        test = _sort_tests(test)
        return unittest.TextTestRunner.run(self, test)


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
