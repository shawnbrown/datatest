# -*- coding: utf-8 -*-
"""Test __past__.api06 to assure backwards compatibility with first
development-release API.

.. note:: Because this sub-module works by monkey-patching the global
          ``datatest`` package, these tests should be run in a separate
          process.
"""
from . import _io as io
from . import _unittest as unittest
from .common import MinimalSource

import datatest
from datatest.__past__ import api06  # <- MONKEY PATCH!!!
from datatest.__past__.api07_error import DataError


class TestApiDev1(unittest.TestCase):
    def test_api_dev1(self):
        self.assertTrue(hasattr(datatest.DataTestCase, 'subjectData'))
        self.assertTrue(hasattr(datatest.DataTestCase, 'referenceData'))

        self.assertTrue(hasattr(datatest.DataTestCase, 'assertDataColumns'))
        self.assertTrue(hasattr(datatest.DataTestCase, 'assertDataCount'))
        self.assertTrue(hasattr(datatest.DataTestCase, 'assertDataSum'))
        self.assertTrue(hasattr(datatest.DataTestCase, 'assertDataRegex'))
        self.assertTrue(hasattr(datatest.DataTestCase, 'assertDataNotRegex'))
        self.assertTrue(hasattr(datatest.DataTestCase, 'allowPercentDeviation'))

        self.assertTrue(hasattr(datatest, 'DataAssertionError'))


class TestHelperCase(unittest.TestCase):
    """Helper class for subsequent cases."""
    def _run_one_test(self, case, method):
        audit_case = case(method)
        runner = unittest.TextTestRunner(stream=io.StringIO())
        test_result = runner.run(audit_case)
        self.assertEqual(test_result.testsRun, 1, 'Should one run test.')
        if test_result.errors:
            return test_result.errors[0][1]
        if test_result.failures:
            return test_result.failures[0][1]
        return None


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
        pattern = ("DataError: row counts different than 'total_rows' sums:\n"
                   " xDeviation\(\+1, 4, label1=u?'a'\),\n"
                   " xDeviation\(-1, 3, label1=u?'b'\)")
        self.assertRegex(failure, pattern)


class TestAllowAny_Missing_Extra(TestHelperCase):
    """Behavior for allowAny, allowMissing, and allowExtra was changed.
    These context managers no longer accept an optional *number*
    argument (new usage is `allow_limit()` for these cases).
    """
    def test_passing(self):
        """Pass when observed number is less-than or equal-to allowed number."""
        class _TestClass(datatest.DataTestCase):
            def test_method1(_self):
                with _self.allowAny(3):  # <- allow three
                    differences = [
                        datatest.Extra('foo'),
                        datatest.Missing('bar'),
                        datatest.Invalid('baz'),
                    ]
                    raise DataError('some differences', differences)

            def test_method2(_self):
                with _self.allowAny(4):  # <- allow four
                    differences = [
                        datatest.Extra('foo'),
                        datatest.Missing('bar'),
                        datatest.Invalid('baz'),
                    ]
                    raise DataError('some differences', differences)

            def test_method3(_self):
                with _self.allowAny():  # <- missing required keyword arg!
                    pass

        failure = self._run_one_test(_TestClass, 'test_method1')
        self.assertIsNone(failure)

        failure = self._run_one_test(_TestClass, 'test_method2')
        self.assertIsNone(failure)

        failure = self._run_one_test(_TestClass, 'test_method3')
        self.assertRegex(failure, 'TypeError: requires 1 or more keyword arguments \(0 given\)')

    def test_failing(self):
        """Fail when observed number is greater-than allowed number."""
        class _TestClass(datatest.DataTestCase):
            def test_method(_self):
                with _self.allowAny(2):  # <- allow two
                    differences = [
                        datatest.Missing('foo'),
                        datatest.Missing('bar'),
                        datatest.Missing('baz'),
                    ]
                    raise DataError('some differences', differences)

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataError: expected at most 2 matching differences: some differences:\n"
                   " xMissing[^\n]+\n"
                   " xMissing[^\n]+\n"
                   " xMissing[^\n]+\n$")
        self.assertRegex(failure, pattern)

    def test_filter(self):
        """Fail when observed number is greater-than allowed number."""
        class _TestClass(datatest.DataTestCase):
            def test_passing(_self):
                with _self.allowAny(3, label1='a'):  # <- allow 3 where label1 equals 'a'
                    differences = [
                        datatest.Deviation(-1, 3, label1='a', label2='x'),
                        datatest.Deviation(+1, 4, label1='a', label2='y'),
                        datatest.Deviation(-2, 5, label1='a', label2='z'),
                    ]
                    raise DataError('some differences', differences)

            def test_fail_with_nonmatched(_self):
                with _self.allowAny(label1='a'):  # <- allow unlimited where label1 equals 'a'
                    differences = [
                        datatest.Deviation(-1, 3, label1='a', label2='x'),
                        datatest.Deviation(+1, 4, label1='a', label2='y'),
                        datatest.Deviation(-2, 5, label1='b', label2='z'),  # <- label='b'
                    ]
                    raise DataError('some differences', differences)

        failure = self._run_one_test(_TestClass, 'test_passing')
        self.assertIsNone(failure)

        failure = self._run_one_test(_TestClass, 'test_fail_with_nonmatched')
        pattern = ("DataError: some differences:\n"
                   " xDeviation\(-2, 5, label1=u?'b', label2=u?'z'\)$")
        self.assertRegex(failure, pattern)


class TestAllowMissing(TestHelperCase):
    def test_class_restriction(self):
        """Non-Missing differences should fail."""
        class _TestClass(datatest.DataTestCase):
            def test_method1(_self):
                with _self.allowMissing(3):
                    differences = [
                        datatest.Missing('foo'),
                        datatest.Extra('bar'),
                        datatest.Extra('baz'),
                    ]
                    raise DataError('some differences', differences)

            def test_method2(_self):
                with _self.allowMissing():  # <- Allow unlimited.
                    differences = [
                        datatest.Missing('foo'),
                        datatest.Extra('bar'),
                        datatest.Extra('baz'),
                    ]
                    raise DataError('some differences', differences)

        failure = self._run_one_test(_TestClass, 'test_method1')
        pattern = ("DataError: some differences:\n"
                   " xExtra[^\n]+\n"
                   " xExtra[^\n]+\n$")
        self.assertRegex(failure, pattern)

        failure = self._run_one_test(_TestClass, 'test_method2')
        pattern = ("DataError: some differences:\n"
                   " xExtra[^\n]+\n"
                   " xExtra[^\n]+\n$")
        self.assertRegex(failure, pattern)


class TestAllowExtra(TestHelperCase):
    def test_class_restriction(self):
        """Non-Extra differences should fail."""
        class _TestClass(datatest.DataTestCase):
            def test_method1(_self):
                with _self.allowExtra(3):
                    differences = [
                        datatest.Extra('foo'),
                        datatest.Missing('bar'),
                        datatest.Missing('baz'),
                    ]
                    raise DataError('some differences', differences)

            def test_method2(_self):
                with _self.allowExtra():  # <- allow unlimited number.
                    differences = [
                        datatest.Extra('foo'),
                        datatest.Missing('bar'),
                        datatest.Missing('baz'),
                    ]
                    raise DataError('some differences', differences)

        failure = self._run_one_test(_TestClass, 'test_method1')
        pattern = ("DataError: some differences:\n"
                   " xMissing[^\n]+\n"
                   " xMissing[^\n]+\n$")
        self.assertRegex(failure, pattern)

        failure = self._run_one_test(_TestClass, 'test_method2')
        pattern = ("DataError: some differences:\n"
                   " xMissing[^\n]+\n"
                   " xMissing[^\n]+\n$")
        self.assertRegex(failure, pattern)


if __name__ == '__main__':
    unittest.main()
else:
    raise Exception('This test must be run directly or as a subprocess.')
