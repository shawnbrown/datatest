# -*- coding: utf-8 -*-
import datatest.tests._io as io
import datatest.tests._unittest as unittest  # Compatibility layer

from unittest import TestCase as _TestCase  # Orig TestCase, not
                                            # compatibility layer.

from datatest.case import DataTestCase
from datatest.case import DataAssertionError
from datatest.case import _walk_diff

from datatest import ExtraColumn
from datatest import ExtraValue
from datatest import ExtraSum
from datatest import MissingColumn
from datatest import MissingValue
from datatest import MissingSum
from datatest import CsvDataSource


class TestWalkValues(unittest.TestCase):
    def test_list_input(self):
        # Flat.
        generator = _walk_diff([MissingValue('val1'),
                                MissingValue('val2')])
        self.assertEqual(list(generator), [MissingValue('val1'),
                                           MissingValue('val2')])

        # Nested.
        generator = _walk_diff([MissingValue('val1'),
                                [MissingValue('val2')]])
        self.assertEqual(list(generator), [MissingValue('val1'),
                                           MissingValue('val2')])

    def test_dict_input(self):
        # Flat dictionary input.
        generator = _walk_diff({'key1': MissingValue('val1'),
                                'key2': MissingValue('val2')})
        self.assertEqual(set(generator), set([MissingValue('val1'),
                                              MissingValue('val2')]))

        # Nested dictionary input.
        generator = _walk_diff({'key1': MissingValue('val1'),
                                'key2': {'key3': MissingValue('baz')}})
        self.assertEqual(set(generator), set([MissingValue('val1'),
                                              MissingValue('baz')]))

    def test_unwrapped_input(self):
        generator = _walk_diff(MissingValue('val1'))
        self.assertEqual(list(generator), [MissingValue('val1')])

    def test_mixed_input(self):
        # Nested collection of dict, list, and unwrapped items.
        generator = _walk_diff({'key1': MissingValue('val1'),
                                'key2': [MissingValue('val2'),
                                         [MissingValue('val3'),
                                          MissingValue('val4')]]})
        self.assertEqual(set(generator), set([MissingValue('val1'),
                                              MissingValue('val2'),
                                              MissingValue('val3'),
                                              MissingValue('val4')]))

    def test_nondiff_items(self):
        # Flat list.
        with self.assertRaises(TypeError):
            generator = _walk_diff(['val1', 'val2'])
            list(generator)

        # Flat dict.
        with self.assertRaises(TypeError):
            generator = _walk_diff({'key1': 'val1', 'key2': 'val2'})
            list(generator)

        # Nested list.
        with self.assertRaises(TypeError):
            generator = _walk_diff([MissingValue('val1'), ['val2']])
            list(generator)

        # Nested collection of dict, list, and unwrapped items.
        with self.assertRaises(TypeError):
            generator = _walk_diff({'key1': MissingValue('val1'),
                                    'key2': [MissingValue('val2'),
                                             [MissingValue('val3'),
                                              'val4']]})
            list(generator)


class TestDataAssertionError(unittest.TestCase):
    def test_subclass(self):
        self.assertTrue(issubclass(DataAssertionError, AssertionError))

    def test_instantiation(self):
        DataAssertionError('column names', MissingColumn('foo'))
        DataAssertionError('column names', [MissingColumn('foo')])
        DataAssertionError('column names', {'Explanation here.': MissingColumn('foo')})
        DataAssertionError('column names', {'Explanation here.': [MissingColumn('foo')]})

        with self.assertRaises(ValueError, msg='Empty error should raise exception.'):
            DataAssertionError(msg='', diff={})

    def test_repr(self):
        error = DataAssertionError('different columns', [MissingColumn('foo')])
        pattern = "DataAssertionError: different columns:\n MissingColumn('foo')"
        self.assertEqual(repr(error), pattern)

        error = DataAssertionError('different columns', MissingColumn('foo'))
        pattern = "DataAssertionError: different columns:\n MissingColumn('foo')"
        self.assertEqual(repr(error), pattern)

        # Test pprint lists.
        error = DataAssertionError('different columns', [MissingColumn('foo'),
                                                         MissingColumn('bar')])
        pattern = ("DataAssertionError: different columns:\n"
                   " MissingColumn('foo'),\n"
                   " MissingColumn('bar')")
        self.assertEqual(repr(error), pattern)

        # Test dictionary with nested list.
        error = DataAssertionError('different columns', {'Omitted': [MissingColumn('foo'),
                                                                     MissingColumn('bar'),
                                                                     MissingColumn('baz')]})
        pattern = ("DataAssertionError: different columns:\n"
                   " 'Omitted': [MissingColumn('foo'),\n"
                   "             MissingColumn('bar'),\n"
                   "             MissingColumn('baz')]")
        self.assertEqual(repr(error), pattern)


class TestHelperCase(unittest.TestCase):
    """Helper class for subsequent cases."""
    def _run_one_test(self, case, method):
        suite = unittest.TestSuite()
        audit_case = case(method)
        runner = unittest.TextTestRunner(stream=io.StringIO())
        test_result = runner.run(audit_case)
        self.assertEqual(test_result.testsRun, 1, 'Should one run test.')
        if test_result.errors:
            msg = 'Test contains error.\n'
            raise AssertionError(msg + test_result.errors[0][1])
        if test_result.failures:
            return test_result.failures[0][1]
        return None


class TestSubclass(TestHelperCase):
    def test_subclass(self):
        """DataTestCase should be a subclass of unittest.TestCase."""
        self.assertTrue(issubclass(DataTestCase, _TestCase))


class TestDataSum(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label1,value\n'
                          'a,65\n'
                          'b,70\n')
        self.src1_totals = CsvDataSource(_fh)

        _fh = io.StringIO('label1,label2,value\n'
                          'a,x,17\n'
                          'a,x,13\n'
                          'a,y,20\n'
                          'a,z,15\n'
                          'b,z,5\n'
                          'b,y,40\n'
                          'b,x,25\n')
        self.src1_records = CsvDataSource(_fh)

        _fh = io.StringIO('label1,label2,value\n'
                          'a,x,18\n'  # <- off by +1 (compared to src1)
                          'a,x,13\n'
                          'a,y,20\n'
                          'a,z,15\n'
                          'b,z,4\n'   # <- off by -1 (compared to src1)
                          'b,y,40\n'
                          'b,x,25\n')
        self.src2_records = CsvDataSource(_fh)

    def test_passing_case(self):
        """Sums are equal, test should pass."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.src1_totals
                _self.subjectData = self.src1_records

            def test_method(_self):
                _self.assertValueSum('value', ['label1'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_failing_case(self):
        """Sums are unequal, test should fail."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.src1_totals
                _self.subjectData = self.src2_records  # <- src1 != src2

            def test_method(_self):
                _self.assertValueSum('value', ['label1'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataAssertionError: different 'value' sums:\n"
                   " ExtraSum\(\+1, 65, label1=u?'a'\),\n"
                   " MissingSum\(-1, 70, label1=u?'b'\)")
        self.assertRegex(failure, pattern)


class TestColumnsSet(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label1,value\n'
                          'a,65\n'
                          'b,70\n')
        self.trusted = CsvDataSource(_fh)

    def test_same(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                same_as_trusted = io.StringIO('label1,value\n'
                                              'a,6\n'
                                              'b,7\n')
                _self.subjectData = CsvDataSource(same_as_trusted)

            def test_method(_self):
                _self.assertColumnSet()  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_extra(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                too_many = io.StringIO('label1,label2,value\n'
                                       'a,x,6\n'
                                       'b,y,7\n')
                _self.subjectData = CsvDataSource(too_many)

            def test_method(_self):
                _self.assertColumnSet()  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "different column names:\n ExtraColumn\(u?'label2'\)"
        self.assertRegex(failure, pattern)

    def test_missing(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                too_few = io.StringIO('label1\n'
                                      'a\n'
                                      'b\n')
                _self.subjectData = CsvDataSource(too_few)

            def test_method(_self):
                _self.assertColumnSet()  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "different column names:\n MissingColumn\(u?'value'\)"
        self.assertRegex(failure, pattern)


class TestColumnSubset(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label1,value\n'
                          'a,65\n'
                          'b,70\n')
        self.trusted = CsvDataSource(_fh)

    def test_same(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                same_as_trusted = io.StringIO('label1,value\n'
                                              'a,6\n'
                                              'b,7\n')
                _self.subjectData = CsvDataSource(same_as_trusted)

            def test_method(_self):
                _self.assertColumnSubset()  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_pass(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                subset_of_trusted = io.StringIO('label1\n'
                                                'a\n'
                                                'b\n')
                _self.subjectData = CsvDataSource(subset_of_trusted)

            def test_method(_self):
                _self.assertColumnSubset()  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_fail(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                superset_of_trusted = io.StringIO('label1,label2,value\n'
                                                  'a,x,6\n'
                                                  'b,y,7\n')
                _self.subjectData = CsvDataSource(superset_of_trusted)

            def test_method(_self):
                _self.assertColumnSubset()  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "different column names:\n ExtraColumn\(u?'label2'\)"
        self.assertRegex(failure, pattern)


class TestColumnSuperset(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label1,value\n'
                          'a,65\n'
                          'b,70\n')
        self.trusted = CsvDataSource(_fh)

    def test_equal(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                same_as_trusted = io.StringIO('label1,value\n'
                                              'a,6\n'
                                              'b,7\n')
                _self.subjectData = CsvDataSource(same_as_trusted)

            def test_method(_self):
                _self.assertColumnSuperset()  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_pass(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                superset_of_trusted = io.StringIO('label1,label2,value\n'
                                                  'a,x,6\n'
                                                  'b,y,7\n')
                _self.subjectData = CsvDataSource(superset_of_trusted)

            def test_method(_self):
                _self.assertColumnSuperset()  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_fail(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                subset_of_trusted = io.StringIO('label1\n'
                                                'a\n'
                                                'b\n')
                _self.subjectData = CsvDataSource(subset_of_trusted)

            def test_method(_self):
                _self.assertColumnSuperset()  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "different column names:\n MissingColumn\(u?'value'\)"
        self.assertRegex(failure, pattern)


class TestValueSet(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label\n'
                          'a\n'
                          'b\n'
                          'c\n')
        self.trusted = CsvDataSource(_fh)

    def test_same(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                same_as_trusted = io.StringIO('label\n'
                                              'a\n'
                                              'b\n'
                                              'c\n')
                _self.subjectData = CsvDataSource(same_as_trusted)

            def test_method(_self):
                _self.assertValueSet('label')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_missing(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                same_as_trusted = io.StringIO('label\n'
                                              'a\n'
                                              'b\n')
                _self.subjectData = CsvDataSource(same_as_trusted)

            def test_method(_self):
                _self.assertValueSet('label')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "different 'label' values:\n MissingValue\(u?'c'\)"
        self.assertRegex(failure, pattern)

    def test_extra(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                same_as_trusted = io.StringIO('label\n'
                                              'a\n'
                                              'b\n'
                                              'c\n'
                                              'd\n')
                _self.subjectData = CsvDataSource(same_as_trusted)

            def test_method(_self):
                _self.assertValueSet('label')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "different 'label' values:\n ExtraValue\(u?'d'\)"
        self.assertRegex(failure, pattern)


class TestDataSubset(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label\n'
                          'a\n'
                          'b\n'
                          'c\n')
        self.trusted = CsvDataSource(_fh)

    def test_same(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                same_as_trusted = io.StringIO('label\n'
                                              'a\n'
                                              'b\n'
                                              'c\n')
                _self.subjectData = CsvDataSource(same_as_trusted)

            def test_method(_self):
                _self.assertValueSubset('label')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_pass(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                subset_of_trusted = io.StringIO('label\n'
                                                'a\n'
                                                'b\n')
                _self.subjectData = CsvDataSource(subset_of_trusted)

            def test_method(_self):
                _self.assertValueSubset('label')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_fail(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                superset_of_trusted = io.StringIO('label\n'
                                                  'a\n'
                                                  'b\n'
                                                  'c\n'
                                                  'd\n')
                _self.subjectData = CsvDataSource(superset_of_trusted)

            def test_method(_self):
                _self.assertValueSubset('label')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "different 'label' values:\n ExtraValue\(u?'d'\)"
        self.assertRegex(failure, pattern)


class TestDataSuperset(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label\n'
                          'a\n'
                          'b\n'
                          'c\n')
        self.trusted = CsvDataSource(_fh)

    def test_same(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                same_as_trusted = io.StringIO('label\n'
                                              'a\n'
                                              'b\n'
                                              'c\n')
                _self.subjectData = CsvDataSource(same_as_trusted)

            def test_method(_self):
                _self.assertValueSuperset('label')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_pass(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                superset_of_trusted = io.StringIO('label\n'
                                                  'a\n'
                                                  'b\n'
                                                  'c\n'
                                                  'd\n')
                _self.subjectData = CsvDataSource(superset_of_trusted)

            def test_method(_self):
                _self.assertValueSuperset('label')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_fail(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                subset_of_trusted = io.StringIO('label\n'
                                                'a\n'
                                                'b\n')
                _self.subjectData = CsvDataSource(subset_of_trusted)

            def test_method(_self):
                _self.assertValueSuperset('label')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "different 'label' values:\n MissingValue\(u?'c'\)"
        self.assertRegex(failure, pattern)


class TestAcceptDifference(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label1,value\n'
                          'a,65\n'
                          'b,70\n')
        self.trusted = CsvDataSource(_fh)

        _fh = io.StringIO('label1,label2,value\n'
                          'a,x,18\n'  # <- off by +1
                          'a,x,13\n'
                          'a,y,20\n'
                          'a,z,15\n'
                          'b,z,4\n'   # <- off by -1
                          'b,y,40\n'
                          'b,x,25\n')
        self.bad_subject = CsvDataSource(_fh)

    def test_accept_list(self):
        """Test should pass with expected difference."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                _self.subjectData = self.bad_subject

            def test_method(_self):
                diff = [
                    ExtraSum(+1, 65, label1='a'),
                    MissingSum(-1, 70, label1='b'),
                ]
                with _self.acceptDifference(diff):
                    _self.assertValueSum('value', ['label1'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_accept_dict(self):
        """Test should pass with expected difference."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                _self.subjectData = self.bad_subject

            def test_method(_self):
                diff = {
                    'One extra.': ExtraSum(+1, 65, label1='a'),
                    'One missing.': MissingSum(-1, 70, label1='b'),
                }
                with _self.acceptDifference(diff):
                    _self.assertValueSum('value', ['label1'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_accept_mixed_types(self):
        """Test should pass with expected difference."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                _self.subjectData = self.bad_subject

            def test_method(_self):
                diff = {
                    'Omitted': [ExtraSum(+1, 65, label1='a'),
                                MissingSum(-1, 70, label1='b')]
                }
                with _self.acceptDifference(diff):
                    _self.assertValueSum('value', ['label1'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_accepted_and_unaccepted_differences(self):
        """Unaccepted differences should fail first."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                _self.subjectData = self.bad_subject

            def test_method(_self):
                diff = [
                    MissingSum(-1, 70, label1='b'),
                    ExtraSum(+2, 65, label1='a'),
                ]
                with _self.acceptDifference(diff):
                    _self.assertValueSum('value', ['label1'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "different 'value' sums:\n ExtraSum\(\+1, 65, label1=u?'a'\)"
        self.assertRegex(failure, pattern)

    def test_accepted_not_found(self):
        """If accepted differences not found, raise exception."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                _self.subjectData = self.bad_subject

            def test_method(_self):
                diff = [
                    MissingSum(-1, 70, label1='b'),
                    ExtraSum(+1, 65, label1='a'),
                    ExtraSum(+2, 65, label1='a')
                ]
                with _self.acceptDifference(diff):
                    _self.assertValueSum('value', ['label1'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("different 'value' sums, accepted difference not found:\n"
                   " ExtraSum\(\+2, 65, label1=u?'a'\)")
        self.assertRegex(failure, pattern)


class TestAcceptTolerance(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label1,value\n'
                          'a,65\n'
                          'b,70\n')
        self.trusted = CsvDataSource(_fh)

        _fh = io.StringIO('label1,label2,value\n'
                          'a,x,20\n'  # <- off by +3
                          'a,x,13\n'
                          'a,y,20\n'
                          'a,z,15\n'
                          'b,z,4\n'   # <- off by -1
                          'b,y,40\n'
                          'b,x,25\n')
        self.bad_subject = CsvDataSource(_fh)

    def test_absolute_tolerance(self):
        """If accepted differences not found, raise exception."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                _self.subjectData = self.bad_subject

            def test_method(_self):
                with _self.acceptTolerance(3):  # <- test tolerance
                    _self.assertValueSum('value', ['label1'])

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_absolute_tolerance_keyword(self):
        """If accepted differences not found, raise exception."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                _self.subjectData = self.bad_subject

            def test_method(_self):
                with _self.acceptTolerance(absolute=3):  # <- test tolerance
                    _self.assertValueSum('value', ['label1'])

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_inadequate_absolute_tolerance(self):
        """Given tolerance of 2, ExtraSum(+3) should still be raised."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                _self.subjectData = self.bad_subject

            def test_method(_self):
                with _self.acceptTolerance(2):  # <- test tolerance
                    _self.assertValueSum('value', ['label1'])

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataAssertionError: different u?'value' sums:\n"
                   " ExtraSum\(\+3, 65, label1=u?'a'\)")
        self.assertRegex(failure, pattern)

    def test_percent_tolerance(self):
        """If accepted differences not found, raise exception."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                _self.subjectData = self.bad_subject

            def test_method(_self):
                with _self.acceptTolerance(percent=0.05):  # <- test tolerance
                    _self.assertValueSum('value', ['label1'])

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_inadequate_percent_tolerance(self):
        """If accepted differences not found, raise exception."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                _self.subjectData = self.bad_subject

            def test_method(_self):
                with _self.acceptTolerance(percent=0.03):  # <- test tolerance
                    _self.assertValueSum('value', ['label1'])

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataAssertionError: different u?'value' sums:\n"
                   " ExtraSum\(\+3, 65, label1=u?'a'\)")
        self.assertRegex(failure, pattern)

    def test_tolerance_error(self):
        """Tolerance must throw error if invalid parameters."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                _self.subjectData = self.bad_subject

            def test_method(_self):
                with _self.acceptTolerance(3, percent=0.03):  # <- test tolerance
                    _self.assertValueSum('value', ['label1'])

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ('AssertionError: Must provide absolute or percent '
                   'tolerance \(but not both\).')
        self.assertRegex(failure, pattern)


class TestNestedAcceptBlocks(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label1,value\n'
                          'a,65\n'
                          'b,70\n')
        self.trusted = CsvDataSource(_fh)

        _fh = io.StringIO('label1,label2,value\n'
                          'a,x,20\n'  # <- off by +3
                          'a,x,13\n'
                          'a,y,20\n'
                          'a,z,15\n'
                          'b,z,4\n'   # <- off by -1
                          'b,y,40\n'
                          'b,x,25\n')
        self.bad_subject = CsvDataSource(_fh)

    def test_tolerance_in_difference(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                _self.subjectData = self.bad_subject

            def test_method(_self):
                with _self.acceptDifference(ExtraSum(+3, 65, label1='a')):
                    with _self.acceptTolerance(2):  # <- test tolerance
                        _self.assertValueSum('value', ['label1'])

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_difference_in_tolerance(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.trustedData = self.trusted
                _self.subjectData = self.bad_subject

            def test_method(_self):
                with _self.acceptTolerance(2):  # <- test tolerance
                    with _self.acceptDifference(ExtraSum(+3, 65, label1='a')):
                        _self.assertValueSum('value', ['label1'])

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

