# -*- coding: utf-8 -*-
import re
import datatest.tests._io as io
#import datatest.tests._unittest as unittest  # Compatibility layer
import unittest
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

    def test_verbose_repr(self):
        reference = 'reference-data-source'
        subject = 'subject-data-source'
        error = DataAssertionError('different columns', [MissingColumn('foo')], reference, subject)
        error._verbose = True  # <- Set verbose flag, here!

        pattern = ("DataAssertionError: different columns:\n"
                   " MissingColumn('foo')\n"
                   "\n"
                   "REFERENCE DATA:\n"
                   "reference-data-source\n"
                   "SUBJECT DATA:\n"
                   "subject-data-source")
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


class TestValueSum(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label1,value\n'
                          'a,65\n'
                          'b,70\n')
        self.src1_totals = CsvDataSource(_fh, in_memory=True)

        _fh = io.StringIO('label1,label2,value\n'
                          'a,x,17\n'
                          'a,x,13\n'
                          'a,y,20\n'
                          'a,z,15\n'
                          'b,z,5\n'
                          'b,y,40\n'
                          'b,x,25\n')
        self.src1_records = CsvDataSource(_fh, in_memory=True)

        _fh = io.StringIO('label1,label2,value\n'
                          'a,x,18\n'  # <- off by +1 (compared to src1)
                          'a,x,13\n'
                          'a,y,20\n'
                          'a,z,15\n'
                          'b,z,4\n'   # <- off by -1 (compared to src1)
                          'b,y,40\n'
                          'b,x,25\n')
        self.src2_records = CsvDataSource(_fh, in_memory=True)

    def test_passing_case(self):
        """Sums are equal, test should pass."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.src1_totals
                _self.subjectData = self.src1_records

            def test_method(_self):
                _self.assertValueSum('value', ['label1'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_failing_case(self):
        """Sums are unequal, test should fail."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.src1_totals
                _self.subjectData = self.src2_records  # <- src1 != src2

            def test_method(_self):
                _self.assertValueSum('value', ['label1'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataAssertionError: different 'value' sums:\n"
                   " ExtraSum\(\+1, 65, label1=u?'a'\),\n"
                   " MissingSum\(-1, 70, label1=u?'b'\)")
        self.assertRegex(failure, pattern)


class TestValueSumGroupsAndFilters(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label1,label2,value\n'
                          'a,x,18\n'  # <- off by +1 (compared to src1)
                          'a,x,13\n'
                          'a,y,20\n'
                          'a,z,15\n'
                          'b,z,4\n'   # <- off by -1 (compared to src1)
                          'b,y,40\n'
                          'b,x,25\n')
        self.src3_totals = CsvDataSource(_fh, in_memory=True)  # src3_totals == src2_records

        _fh = io.StringIO('label1,label2,label3,value\n'
                          'a,x,foo,18\n'
                          'a,x,bar,13\n'
                          'a,y,foo,11\n'  # <- off by +1 (compared to src3)
                          'a,y,bar,10\n'
                          'a,z,foo,5\n'
                          'a,z,bar,10\n'
                          'b,z,baz,4\n'
                          'b,y,bar,39\n'   # <- off by -1 (compared to src3)
                          'b,x,foo,25\n')
        self.src3_records = CsvDataSource(_fh, in_memory=True)

    def test_group_and_filter(self):
        """Only groupby fields should appear in diff errors (kwds-filters should be omitted)."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.src3_totals
                _self.subjectData = self.src3_records  # <- src1 != src2

            def test_method(_self):
                _self.assertValueSum('value', ['label1'], label2='y')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataAssertionError: different 'value' sums:\n"
                   " ExtraSum\(\+1, 20, label1=u?'a'\),\n"
                   " MissingSum\(-1, 40, label1=u?'b'\)")
        self.assertRegex(failure, pattern)



class TestValueCount(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label1,label2,total_rows\n'
                          'a,x,2\n'
                          'a,y,1\n'
                          'a,z,1\n'
                          'b,x,3\n')
        self.src1_totals = CsvDataSource(_fh, in_memory=True)

        _fh = io.StringIO('label1,label2\n'
                          'a,x\n'
                          'a,x\n'
                          'a,y\n'
                          'a,z\n'
                          'b,x\n'
                          'b,x\n'
                          'b,x\n')
        self.src1_records = CsvDataSource(_fh, in_memory=True)

        _fh = io.StringIO(
            'label1,label2\n'
            'a,x\n'
            'a,x\n'
            'a,x\n'  # <- one extra "a,x" row (compared to src1)
            'a,y\n'
            'a,z\n'
            'b,x\n'
            'b,x\n'
            #'b,x\n'  # <-one missing "b,x" row (compared to src1)
         )
        self.src2_records = CsvDataSource(_fh, in_memory=True)

    def test_passing_case(self):
        """Subject counts match reference sums, test should pass."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.src1_totals
                _self.subjectData = self.src1_records

            def test_method(_self):
                _self.assertValueCount('total_rows', ['label1'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_missing_column(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.src1_totals
                _self.subjectData = self.src1_records

            def test_method(_self):
                _self.assertValueCount('bad_col_name', ['label1'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "no column named u?'bad_col_name'"
        self.assertRegex(failure, pattern)

    def test_failing_case(self):
        """Counts do not match, test should fail."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.src1_totals
                _self.subjectData = self.src2_records  # <- src1 != src2

            def test_method(_self):
                _self.assertValueCount('total_rows', ['label1'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataAssertionError: row counts different than 'total_rows' sums:\n"
                   " ExtraSum\(\+1, 4, label1=u?'a'\),\n"
                   " MissingSum\(-1, 3, label1=u?'b'\)")
        self.assertRegex(failure, pattern)


class TestColumnsSet(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label1,value\n'
                          'a,65\n'
                          'b,70\n')
        self.reference = CsvDataSource(_fh, in_memory=True)

    def test_pass(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference  # <- referenceData!
                same_as_reference = io.StringIO('label1,value\n'
                                                'a,6\n'
                                                'b,7\n')
                _self.subjectData = CsvDataSource(same_as_reference, in_memory=True)

            def test_method(_self):
                _self.assertColumnSet()  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_pass_using_reference_from_argument(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                #_self.referenceData =   <- Not defined!
                subject = io.StringIO('label1,value\n'
                                      'a,6\n'
                                      'b,7\n')
                _self.subjectData = CsvDataSource(subject, in_memory=True)

            def test_method(_self):
                reference_set = set(['label1', 'value'])
                _self.assertColumnSet(ref=reference_set)  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_extra(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                too_many = io.StringIO('label1,label2,value\n'
                                       'a,x,6\n'
                                       'b,y,7\n')
                _self.subjectData = CsvDataSource(too_many, in_memory=True)

            def test_method(_self):
                _self.assertColumnSet()  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "different column names:\n ExtraColumn\(u?'label2'\)"
        self.assertRegex(failure, pattern)

    def test_missing(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                too_few = io.StringIO('label1\n'
                                      'a\n'
                                      'b\n')
                _self.subjectData = CsvDataSource(too_few, in_memory=True)

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
        self.reference = CsvDataSource(_fh, in_memory=True)

    def test_same(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                same_as_reference = io.StringIO('label1,value\n'
                                                'a,6\n'
                                                'b,7\n')
                _self.subjectData = CsvDataSource(same_as_reference, in_memory=True)

            def test_method(_self):
                _self.assertColumnSubset()  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_pass(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                subset_of_reference = io.StringIO('label1\n'
                                                  'a\n'
                                                  'b\n')
                _self.subjectData = CsvDataSource(subset_of_reference, in_memory=True)

            def test_method(_self):
                _self.assertColumnSubset()  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_pass_using_reference_from_argument(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                #_self.referenceData =   <- Not defined!
                subset_of_reference = io.StringIO('label1\n'
                                                  'a\n'
                                                  'b\n')
                _self.subjectData = CsvDataSource(subset_of_reference, in_memory=True)

            def test_method(_self):
                reference_set = set(['label1', 'value'])
                _self.assertColumnSubset(reference_set)  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_fail(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                superset_of_reference = io.StringIO('label1,label2,value\n'
                                                    'a,x,6\n'
                                                    'b,y,7\n')
                _self.subjectData = CsvDataSource(superset_of_reference, in_memory=True)

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
        self.reference = CsvDataSource(_fh, in_memory=True)

    def test_equal(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                same_as_reference = io.StringIO('label1,value\n'
                                                'a,6\n'
                                                'b,7\n')
                _self.subjectData = CsvDataSource(same_as_reference, in_memory=True)

            def test_method(_self):
                _self.assertColumnSuperset()  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_pass(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                superset_of_reference = io.StringIO('label1,label2,value\n'
                                                    'a,x,6\n'
                                                    'b,y,7\n')
                _self.subjectData = CsvDataSource(superset_of_reference, in_memory=True)

            def test_method(_self):
                _self.assertColumnSuperset()  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_pass_using_reference_from_argument(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                #_self.referenceData =   <- Not defined!
                superset_of_reference = io.StringIO('label1,label2,value\n'
                                                    'a,x,6\n'
                                                    'b,y,7\n')
                _self.subjectData = CsvDataSource(superset_of_reference, in_memory=True)

            def test_method(_self):
                reference_set = set(['label1', 'value'])
                _self.assertColumnSuperset(reference_set)  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_fail(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                subset_of_reference = io.StringIO('label1\n'
                                                  'a\n'
                                                  'b\n')
                _self.subjectData = CsvDataSource(subset_of_reference, in_memory=True)

            def test_method(_self):
                _self.assertColumnSuperset()  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "different column names:\n MissingColumn\(u?'value'\)"
        self.assertRegex(failure, pattern)


class TestValueSet(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label,label2\n'
                          'a,x\n'
                          'b,y\n'
                          'c,z\n')
        self.reference = CsvDataSource(_fh, in_memory=True)

    def test_same(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                same_as_reference = io.StringIO('label\n'
                                                'a\n'
                                                'b\n'
                                                'c\n')
                _self.subjectData = CsvDataSource(same_as_reference, in_memory=True)

            def test_method(_self):
                _self.assertValueSet('label')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_same_using_reference_from_argument(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                #_self.referenceData =   <- Not defined!
                same_as_reference = io.StringIO('label\n'
                                                'a\n'
                                                'b\n'
                                                'c\n')
                _self.subjectData = CsvDataSource(same_as_reference, in_memory=True)

            def test_method(_self):
                reference_set = set(['a', 'b', 'c'])
                _self.assertValueSet('label', ref=reference_set)  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_same_group_using_reference_from_argument(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                #_self.referenceData =   <- Not defined!
                same_as_reference = io.StringIO('label1,label2\n'
                                                'a,x\n'
                                                'b,y\n'
                                                'c,z\n')
                _self.subjectData = CsvDataSource(same_as_reference, in_memory=True)

            def test_method(_self):
                reference_set = set([('a', 'x'), ('b', 'y'), ('c', 'z')])
                _self.assertValueSet(['label1', 'label2'], ref=reference_set)  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_missing(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                same_as_reference = io.StringIO('label\n'
                                                'a\n'
                                                'b\n')
                _self.subjectData = CsvDataSource(same_as_reference, in_memory=True)

            def test_method(_self):
                _self.assertValueSet('label')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "different 'label' values:\n MissingValue\(u?'c'\)"
        self.assertRegex(failure, pattern)

    def test_extra(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                same_as_reference = io.StringIO('label\n'
                                                'a\n'
                                                'b\n'
                                                'c\n'
                                                'd\n')
                _self.subjectData = CsvDataSource(same_as_reference, in_memory=True)

            def test_method(_self):
                _self.assertValueSet('label')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "different 'label' values:\n ExtraValue\(u?'d'\)"
        self.assertRegex(failure, pattern)

    def test_same_group(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                same_as_reference = io.StringIO('label,label2\n'
                                                'a,x\n'
                                                'b,y\n'
                                                'c,z\n')
                _self.subjectData = CsvDataSource(same_as_reference, in_memory=True)

            def test_method(_self):
                _self.assertValueSet(['label', 'label2'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_missing_group(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                same_as_reference = io.StringIO('label,label2\n'
                                                'a,x\n'
                                                'c,z\n')
                _self.subjectData = CsvDataSource(same_as_reference, in_memory=True)

            def test_method(_self):
                _self.assertValueSet(['label', 'label2'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "different \[u?'label', u?'label2'\] values:\n MissingValue\(\(u?'b', u?'y'\)\)"
        self.assertRegex(failure, pattern)


class TestValueSubset(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label\n'
                          'a\n'
                          'b\n'
                          'c\n')
        self.reference = CsvDataSource(_fh, in_memory=True)

    def test_same(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                same_as_reference = io.StringIO('label\n'
                                                'a\n'
                                                'b\n'
                                                'c\n')
                _self.subjectData = CsvDataSource(same_as_reference, in_memory=True)

            def test_method(_self):
                _self.assertValueSubset('label')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_pass(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                subset_of_reference = io.StringIO('label\n'
                                                'a\n'
                                                'b\n')
                _self.subjectData = CsvDataSource(subset_of_reference, in_memory=True)

            def test_method(_self):
                _self.assertValueSubset('label')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_pass_using_reference_from_argument(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                #_self.referenceData =   <- Not defined!
                subset_of_reference = io.StringIO('label\n'
                                                  'a\n'
                                                  'b\n')
                _self.subjectData = CsvDataSource(subset_of_reference, in_memory=True)

            def test_method(_self):
                reference_set = set(['a', 'b', 'c'])
                _self.assertValueSubset('label', reference_set)  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_fail(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                superset_of_reference = io.StringIO('label\n'
                                                    'a\n'
                                                    'b\n'
                                                    'c\n'
                                                    'd\n')
                _self.subjectData = CsvDataSource(superset_of_reference, in_memory=True)

            def test_method(_self):
                _self.assertValueSubset('label')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "different 'label' values:\n ExtraValue\(u?'d'\)"
        self.assertRegex(failure, pattern)


class TestValueSuperset(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label\n'
                          'a\n'
                          'b\n'
                          'c\n')
        self.reference = CsvDataSource(_fh, in_memory=True)

    def test_same(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                same_as_reference = io.StringIO('label\n'
                                                'a\n'
                                                'b\n'
                                                'c\n')
                _self.subjectData = CsvDataSource(same_as_reference, in_memory=True)

            def test_method(_self):
                _self.assertValueSuperset('label')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_pass(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                superset_of_reference = io.StringIO('label\n'
                                                    'a\n'
                                                    'b\n'
                                                    'c\n'
                                                    'd\n')
                _self.subjectData = CsvDataSource(superset_of_reference, in_memory=True)

            def test_method(_self):
                _self.assertValueSuperset('label')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_pass_using_reference_from_argument(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                #_self.referenceData =   <- Not defined!
                superset_of_reference = io.StringIO('label\n'
                                                    'a\n'
                                                    'b\n'
                                                    'c\n'
                                                    'd\n')
                _self.subjectData = CsvDataSource(superset_of_reference, in_memory=True)

            def test_method(_self):
                reference_set = set(['a', 'b', 'c'])
                _self.assertValueSuperset('label', ref=reference_set)  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_fail(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                subset_of_reference = io.StringIO('label\n'
                                                  'a\n'
                                                  'b\n')
                _self.subjectData = CsvDataSource(subset_of_reference, in_memory=True)

            def test_method(_self):
                _self.assertValueSuperset('label')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "different 'label' values:\n MissingValue\(u?'c'\)"
        self.assertRegex(failure, pattern)


class TestValueRegexAndValueNotRegex(TestHelperCase):
    def setUp(self):
        self.source = io.StringIO('label1,label2\n'
                                  '0aaa,001\n'
                                  'b9bb,2\n'
                                  ' ccc,003\n')

    def test_regex_passing(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.subjectData = CsvDataSource(self.source, in_memory=True)

            def test_method(_self):
                _self.assertValueRegex('label1', '\w\w')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_regex_failing(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.subjectData = CsvDataSource(self.source, in_memory=True)

            def test_method(_self):
                _self.assertValueRegex('label2', '\d\d\d')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "non-matching 'label2' values:\n ExtraValue\(u?'2'\)"
        self.assertRegex(failure, pattern)

    def test_regex_precompiled(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.subjectData = CsvDataSource(self.source, in_memory=True)

            def test_method(_self):
                regex = re.compile('[ABC]$', re.IGNORECASE)  # <- pre-compiled
                _self.assertValueRegex('label1', regex)  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_not_regex_passing(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.subjectData = CsvDataSource(self.source, in_memory=True)

            def test_method(_self):
                _self.assertValueNotRegex('label1', '\d\d\d')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_not_regex_failing(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.subjectData = CsvDataSource(self.source, in_memory=True)

            def test_method(_self):
                _self.assertValueNotRegex('label2', '^\d{1,2}$')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "matching 'label2' values:\n ExtraValue\(u?'2'\)"
        self.assertRegex(failure, pattern)

    def test_not_regex_precompiled(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.subjectData = CsvDataSource(self.source, in_memory=True)

            def test_method(_self):
                regex = re.compile('^[ABC]')  # <- pre-compiled
                _self.assertValueNotRegex('label1', regex)  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

class TestAcceptDifference(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label1,value\n'
                          'a,65\n'
                          'b,70\n')
        self.reference = CsvDataSource(_fh, in_memory=True)

        _fh = io.StringIO('label1,label2,value\n'
                          'a,x,18\n'  # <- off by +1
                          'a,x,13\n'
                          'a,y,20\n'
                          'a,z,15\n'
                          'b,z,4\n'   # <- off by -1
                          'b,y,40\n'
                          'b,x,25\n')
        self.bad_subject = CsvDataSource(_fh, in_memory=True)

    def test_accept_list(self):
        """Test should pass with expected difference."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
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
                _self.referenceData = self.reference
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
                _self.referenceData = self.reference
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
                _self.referenceData = self.reference
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

    def test_accepted_not_found_with_diff(self):
        """If accepted differences not found, raise exception."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
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

    def test_accepted_not_found_without_diff(self):
        """If accepted differences not found and no diff at all, raise exception."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                _self.subjectData = self.reference

            def test_method(_self):
                diff = ExtraSum(+2, 65, label1='a')
                with _self.acceptDifference(diff):
                    _self.assertValueSum('value', ['label1'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataAssertionError: No error raised, accepted difference not found:\n"
                   " ExtraSum\(\+2, 65, label1=u?'a'\)")
        self.assertRegex(failure, pattern)


class TestAcceptTolerance(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label1,value\n'
                          'a,65\n'
                          'b,70\n')
        self.reference = CsvDataSource(_fh, in_memory=True)

        _fh = io.StringIO('label1,label2,value\n'
                          'a,x,20\n'  # <- off by +3
                          'a,x,13\n'
                          'a,y,20\n'
                          'a,z,15\n'
                          'b,z,4\n'   # <- off by -1
                          'b,y,40\n'
                          'b,x,25\n')
        self.bad_subject = CsvDataSource(_fh, in_memory=True)

    def test_absolute_tolerance(self):
        """If accepted differences not found, raise exception."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
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
                _self.referenceData = self.reference
                _self.subjectData = self.bad_subject

            def test_method(_self):
                with _self.acceptTolerance(3):  # <- test tolerance
                    _self.assertValueSum('value', ['label1'])

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_inadequate_absolute_tolerance(self):
        """Given tolerance of 2, ExtraSum(+3) should still be raised."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                _self.subjectData = self.bad_subject

            def test_method(_self):
                with _self.acceptTolerance(2):  # <- test tolerance
                    _self.assertValueSum('value', ['label1'])

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataAssertionError: different u?'value' sums:\n"
                   " ExtraSum\(\+3, 65, label1=u?'a'\)")
        self.assertRegex(failure, pattern)

    def test_tolerance_error(self):
        """Must throw error if tolerance is invalid."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                _self.subjectData = self.bad_subject

            def test_method(_self):
                with _self.acceptTolerance(-5):  # <- invalid
                    _self.assertValueSum('value', ['label1'])

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = 'Tolerance cannot be defined with a negative number.'
        self.assertRegex(failure, pattern)

    # QUESTION: Should tolerances raise an error if there are no
    #           observed differences or if the maximum oberved
    #           difference is less than the acceptable tolerance?
    #
    #def test_tolerance_with_no_raised_difference(self):
    #    """If accepted differences not found, raise exception."""
    #    class _TestClass(DataTestCase):
    #        def setUp(_self):
    #            _self.referenceData = self.reference
    #            _self.subjectData = self.reference
    #
    #        def test_method(_self):
    #            with _self.acceptTolerance(3):  # <- test tolerance
    #                _self.assertValueSum('value', ['label1'])
    #
    #    failure = self._run_one_test(_TestClass, 'test_method')
    #    pattern = 'no errors...'
    #    self.assertRegex(failure, pattern)


class TestAcceptPercentTolerance(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label1,value\n'
                          'a,65\n'
                          'b,70\n')
        self.reference = CsvDataSource(_fh, in_memory=True)

        _fh = io.StringIO('label1,label2,value\n'
                          'a,x,20\n'  # <- off by +3
                          'a,x,13\n'
                          'a,y,20\n'
                          'a,z,15\n'
                          'b,z,4\n'   # <- off by -1
                          'b,y,40\n'
                          'b,x,25\n')
        self.bad_subject = CsvDataSource(_fh, in_memory=True)

    def test_percent_tolerance(self):
        """If accepted differences not found, raise exception."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                _self.subjectData = self.bad_subject

            def test_method(_self):
                with _self.acceptPercentTolerance(0.05):  # <- test tolerance
                    _self.assertValueSum('value', ['label1'])

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_inadequate_percent_tolerance(self):
        """If accepted differences not found, raise exception."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                _self.subjectData = self.bad_subject

            def test_method(_self):
                with _self.acceptPercentTolerance(0.03):  # <- test tolerance
                    _self.assertValueSum('value', ['label1'])

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataAssertionError: different u?'value' sums:\n"
                   " ExtraSum\(\+3, 65, label1=u?'a'\)")
        self.assertRegex(failure, pattern)

    def test_tolerance_error(self):
        """Tolerance must throw error if invalid parameter."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                _self.subjectData = self.bad_subject

            def test_method(_self):
                with _self.acceptPercentTolerance(1.1):  # <- invalid
                    _self.assertValueSum('value', ['label1'])

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ('AssertionError: Percent tolerance must be between 0 and 1.')
        self.assertRegex(failure, pattern)


class TestNestedAcceptBlocks(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label1,value\n'
                          'a,65\n'
                          'b,70\n')
        self.reference = CsvDataSource(_fh, in_memory=True)

        _fh = io.StringIO('label1,label2,value\n'
                          'a,x,20\n'  # <- off by +3
                          'a,x,13\n'
                          'a,y,20\n'
                          'a,z,15\n'
                          'b,z,4\n'   # <- off by -1
                          'b,y,40\n'
                          'b,x,25\n')
        self.bad_subject = CsvDataSource(_fh, in_memory=True)

    def test_tolerance_in_difference(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
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
                _self.referenceData = self.reference
                _self.subjectData = self.bad_subject

            def test_method(_self):
                with _self.acceptTolerance(2):  # <- test tolerance
                    with _self.acceptDifference(ExtraSum(+3, 65, label1='a')):
                        _self.assertValueSum('value', ['label1'])

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_difference_not_found_in_tolerance(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                _self.subjectData = self.bad_subject

            def test_method(_self):
                with _self.acceptDifference(ExtraSum(+10, 999, label1='a')):
                    with _self.acceptTolerance(3):
                        _self.assertValueSum('value', ['label1'])

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataAssertionError: No error raised, accepted difference not found:\n"
                   " ExtraSum\(\+10, 999, label1=u?'a'\)")
        self.assertRegex(failure, pattern)

