# -*- coding: utf-8 -*-
"""Test __past__.api_dev1 to assure backwards compatibility with first
development-release API.

.. note:: Because this sub-module works by monkey-patching the global
          ``datatest`` package, these tests should be run in a separate
          process.
"""
from . import _io as io
from . import _unittest as unittest
from .common import MinimalSource

import datatest
from datatest.__past__ import api_dev1  # <- MONKEY PATCH!!!


class TestApiDev1(unittest.TestCase):
    def test_api_dev1(self):
        self.assertTrue(hasattr(datatest.DataTestCase, 'subjectData'))
        self.assertTrue(hasattr(datatest.DataTestCase, 'referenceData'))

        self.assertTrue(hasattr(datatest.DataTestCase, 'assertDataColumns'))
        self.assertTrue(hasattr(datatest.DataTestCase, 'assertDataCount'))
        self.assertTrue(hasattr(datatest.DataTestCase, 'assertDataSum'))
        self.assertTrue(hasattr(datatest.DataTestCase, 'assertDataRegex'))
        self.assertTrue(hasattr(datatest.DataTestCase, 'assertDataNotRegex'))


class TestAssertDataCount(unittest.TestCase):
    """The assertDataCount() method was removed from DataTestCase."""
    def setUp(self):
        self.src1_totals = MinimalSource([
            ('label1', 'label2', 'total_rows'),
            ('a', 'x', '2'),
            ('a', 'y', '1'),
            ('a', 'z', '1'),
            ('b', 'x', '3'),
        ])

        self.src1_records = MinimalSource([
            ('label1', 'label2', 'total_rows'),
            ('a', 'x', '1'),
            ('a', 'x', '1'),
            ('a', 'y', '1'),
            ('a', 'z', '1'),
            ('b', 'x', '1'),
            ('b', 'x', '1'),
            ('b', 'x', '1'),
        ])

        self.src2_records = MinimalSource([
            ('label1', 'label2', 'total_rows'),
            ('a', 'x', '1'),
            ('a', 'x', '1'),
            ('a', 'x', '1'),  # <- one extra "a,x" row (compared to src1)
            ('a', 'y', '1'),
            ('a', 'z', '1'),
            ('b', 'x', '1'),
            ('b', 'x', '1'),
            #('b', 'x', '1'),  # <-one missing "b,x" row (compared to src1)
        ])

    def _run_one_test(self, case, method):
        suite = unittest.TestSuite()
        audit_case = case(method)
        runner = unittest.TextTestRunner(stream=io.StringIO())
        test_result = runner.run(audit_case)
        self.assertEqual(test_result.testsRun, 1, 'Should one run test.')
        if test_result.errors:
            return test_result.errors[0][1]
        if test_result.failures:
            return test_result.failures[0][1]
        return None

    def test_passing_case(self):
        """Subject counts match reference sums, test should pass."""
        class _TestClass(datatest.DataTestCase):
            def setUp(_self):
                _self.subject = self.src1_records
                _self.reference = self.src1_totals

            def test_method(_self):
                _self.assertDataCount('total_rows', ['label1'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_missing_column(self):
        class _TestClass(datatest.DataTestCase):
            def setUp(_self):
                _self.reference = self.src1_totals
                _self.subject = self.src1_records

            def test_method(_self):
                _self.assertDataCount('bad_col_name', ['label1'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "(KeyError|LookupError): u?'bad_col_name'"
        self.assertRegex(failure, pattern)

    def test_failing_case(self):
        """Counts do not match, test should fail."""
        class _TestClass(datatest.DataTestCase):
            def setUp(_self):
                _self.reference = self.src1_totals
                _self.subject = self.src2_records  # <- src1 != src2

            def test_method(_self):
                required = {'a': 4, 'b': 3}
                _self.assertDataCount('total_rows', ['label1'], required)  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataAssertionError: row counts different than 'total_rows' sums:\n"
                   " Deviation\(\+1, 4, label1=u?'a'\),\n"
                   " Deviation\(-1, 3, label1=u?'b'\)")
        self.assertRegex(failure, pattern)


if __name__ == '__main__':
    unittest.main()
else:
    raise Exception('This test must be run directly or as a subprocess.')
