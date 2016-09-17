# -*- coding: utf-8 -*-
"""Test __past__.api_dev2 to assure backwards compatibility with first
development-release API.

.. note:: Because this sub-module works by monkey-patching the global
          ``datatest`` package, these tests should be run in a separate
          process.
"""
from . import _io as io
from . import _unittest as unittest
import datatest
from datatest.__past__ import api_dev2  # <- MONKEY PATCH!!!


class TestNamesAndAttributes(unittest.TestCase):
    def _run_wrapped_test(self, case, method):
        audit_case = case(method)
        runner = unittest.TextTestRunner(stream=io.StringIO())
        result = runner.run(audit_case)

        error = result.errors[0][1] if result.errors else None
        failure = result.failures[0][1] if result.failures else None
        return error, failure

    def test_names(self):
        """In the 0.7.0 API, the assertEqual() method should be wrapped
        in a datatest.DataTestCase method of the same name.
        """
        # TODO: Add this check once the class has been renamed.
        # Check for DataTestCase name (now TestCase).
        #self.assertTrue(hasattr(datatest, 'DataTestCase'))

        # Check that wrapper exists.
        datatest_eq = datatest.DataTestCase.assertEqual
        unittest_eq = unittest.TestCase.assertEqual
        self.assertIsNot(datatest_eq, unittest_eq)

    def test_assertEqual(self):
        """Test for 0.7.0 assertEqual() wrapper behavior."""
        class _TestWrapper(datatest.DataTestCase):
            def test_method(_self):
                first = set([1, 2, 3])
                second = set([1, 2, 3, 4])
                with self.assertRaises(datatest.DataError) as cm:
                    _self.assertEqual(first, second)  # <- Wrapped method!

                msg = 'In 0.7.0, assertEqual() should raise DataError.'
                _self.assertTrue(isinstance(cm.exception, datatest.DataError), msg)

                diffs = list(cm.exception.differences)
                _self.assertEqual(diffs, [datatest.Missing(4)])

        error, failure = self._run_wrapped_test(_TestWrapper, 'test_method')
        self.assertIsNone(error)
        self.assertIsNone(failure)


if __name__ == '__main__':
    unittest.main()
else:
    raise Exception('This test must be run directly or as a subprocess.')
