# -*- coding: utf-8 -*-
import re
from unittest import TestCase as _TestCase  # Originial TestCase, not
                                            # compatibility layer.

# Import compatiblity layers.
from . import _io as io
from . import _unittest as unittest

# Import code to test.
from datatest.case import DataTestCase
from datatest.case import _walk_diff
from datatest import DataAssertionError
from datatest import Extra
from datatest import Missing
from datatest import Invalid
from datatest import Deviation
from datatest import CsvSource


class TestWalkValues(unittest.TestCase):
    def test_list_input(self):
        # Flat.
        generator = _walk_diff([Missing('val1'),
                                Missing('val2')])
        self.assertEqual(list(generator), [Missing('val1'),
                                           Missing('val2')])

        # Nested.
        generator = _walk_diff([Missing('val1'),
                                [Missing('val2')]])
        self.assertEqual(list(generator), [Missing('val1'),
                                           Missing('val2')])

    def test_dict_input(self):
        # Flat dictionary input.
        generator = _walk_diff({'key1': Missing('val1'),
                                'key2': Missing('val2')})
        self.assertEqual(set(generator), set([Missing('val1'),
                                              Missing('val2')]))

        # Nested dictionary input.
        generator = _walk_diff({'key1': Missing('val1'),
                                'key2': {'key3': Missing('baz')}})
        self.assertEqual(set(generator), set([Missing('val1'),
                                              Missing('baz')]))

    def test_unwrapped_input(self):
        generator = _walk_diff(Missing('val1'))
        self.assertEqual(list(generator), [Missing('val1')])

    def test_mixed_input(self):
        # Nested collection of dict, list, and unwrapped items.
        generator = _walk_diff({'key1': Missing('val1'),
                                'key2': [Missing('val2'),
                                         [Missing('val3'),
                                          Missing('val4')]]})
        self.assertEqual(set(generator), set([Missing('val1'),
                                              Missing('val2'),
                                              Missing('val3'),
                                              Missing('val4')]))

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
            generator = _walk_diff([Missing('val1'), ['val2']])
            list(generator)

        # Nested collection of dict, list, and unwrapped items.
        with self.assertRaises(TypeError):
            generator = _walk_diff({'key1': Missing('val1'),
                                    'key2': [Missing('val2'),
                                             [Missing('val3'),
                                              'val4']]})
            list(generator)


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


class TestNormalizeReference(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label1,value\n'
                          'a,65\n'
                          'b,70\n')
        self.test_reference = CsvSource(_fh, in_memory=True)

        _fh = io.StringIO('label1,label2,value\n'
                          'a,x,17\n'
                          'a,x,13\n'
                          'a,y,20\n'
                          'a,z,15\n'
                          'b,z,5\n'
                          'b,y,40\n'
                          'b,x,25\n')
        self.test_subject = CsvSource(_fh, in_memory=True)

    def test_normalize_reference(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.test_reference
                _self.subjectData = self.test_subject

            def test_method(_self):  # Dummy method for instantiation.
                pass

        instance = _TestClass('test_method')

        #original = set(['x', 'y', 'z'])
        #normalized = instance._normalize_reference(None, 'distinct', 'label2')
        #self.assertIsNot(original, normalized)
        #self.assertEqual(original, normalized)

        # Set object should return unchanged.
        original = set(['x', 'y', 'z'])
        normalized = instance._normalize_reference(original, 'distinct', 'label2')
        self.assertIs(original, normalized)

        # Alternate reference source.
        _fh = io.StringIO('label1,value\n'
                          'c,75\n'
                          'd,80\n')
        altsrc = CsvSource(_fh, in_memory=True)
        normalized = instance._normalize_reference(altsrc, 'distinct', 'label1')
        self.assertEqual(set(['c', 'd']), normalized)


class TestDataSum(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label1,value\n'
                          'a,65\n'
                          'b,70\n')
        self.src1_totals = CsvSource(_fh, in_memory=True)

        _fh = io.StringIO('label1,label2,value\n'
                          'a,x,17\n'
                          'a,x,13\n'
                          'a,y,20\n'
                          'a,z,15\n'
                          'b,z,5\n'
                          'b,y,40\n'
                          'b,x,25\n')
        self.src1_records = CsvSource(_fh, in_memory=True)

        _fh = io.StringIO('label1,label2,value\n'
                          'a,x,18\n'  # <- off by +1 (compared to src1)
                          'a,x,13\n'
                          'a,y,20\n'
                          'a,z,15\n'
                          'b,z,4\n'   # <- off by -1 (compared to src1)
                          'b,y,40\n'
                          'b,x,25\n')
        self.src2_records = CsvSource(_fh, in_memory=True)

    def test_passing_case(self):
        """Sums are equal, test should pass."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.src1_totals
                _self.subjectData = self.src1_records

            def test_method(_self):
                _self.assertDataSum('value', ['label1'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_failing_case(self):
        """Sums are unequal, test should fail."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.src1_totals
                _self.subjectData = self.src2_records  # <- src1 != src2

            def test_method(_self):
                _self.assertDataSum('value', ['label1'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataAssertionError: different 'value' sums:\n"
                   " Deviation\(\+1, 65, label1=u?'a'\),\n"
                   " Deviation\(-1, 70, label1=u?'b'\)")
        self.assertRegex(failure, pattern)


class TestAssertDataSumGroupsAndFilters(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label1,label2,value\n'
                          'a,x,18\n'  # <- off by +1 (compared to src1)
                          'a,x,13\n'
                          'a,y,20\n'
                          'a,z,15\n'
                          'b,z,4\n'   # <- off by -1 (compared to src1)
                          'b,y,40\n'
                          'b,x,25\n')
        self.src3_totals = CsvSource(_fh, in_memory=True)  # src3_totals == src2_records

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
        self.src3_records = CsvSource(_fh, in_memory=True)

    def test_group_and_filter(self):
        """Only groupby fields should appear in diff errors (kwds-filters should be omitted)."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.src3_totals
                _self.subjectData = self.src3_records  # <- src1 != src2

            def test_method(_self):
                _self.assertDataSum('value', ['label1'], label2='y')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataAssertionError: different 'value' sums:\n"
                   " Deviation\(\+1, 20, label1=u?'a'\),\n"
                   " Deviation\(-1, 40, label1=u?'b'\)")
        self.assertRegex(failure, pattern)



class TestAssertDataCount(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label1,label2,total_rows\n'
                          'a,x,2\n'
                          'a,y,1\n'
                          'a,z,1\n'
                          'b,x,3\n')
        self.src1_totals = CsvSource(_fh, in_memory=True)

        _fh = io.StringIO('label1,label2\n'
                          'a,x\n'
                          'a,x\n'
                          'a,y\n'
                          'a,z\n'
                          'b,x\n'
                          'b,x\n'
                          'b,x\n')
        self.src1_records = CsvSource(_fh, in_memory=True)

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
        self.src2_records = CsvSource(_fh, in_memory=True)

    def test_passing_case(self):
        """Subject counts match reference sums, test should pass."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.src1_totals
                _self.subjectData = self.src1_records

            def test_method(_self):
                _self.assertDataCount('total_rows', ['label1'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_missing_column(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.src1_totals
                _self.subjectData = self.src1_records

            def test_method(_self):
                _self.assertDataCount('bad_col_name', ['label1'])  # <- test assert

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
                _self.assertDataCount('total_rows', ['label1'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataAssertionError: row counts different than 'total_rows' sums:\n"
                   " Deviation\(\+1, 4, label1=u?'a'\),\n"
                   " Deviation\(-1, 3, label1=u?'b'\)")
        self.assertRegex(failure, pattern)


class TestAssertDataColumns(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label1,value\n'
                          'a,65\n'
                          'b,70\n')
        self.reference = CsvSource(_fh, in_memory=True)

    def test_pass(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference  # <- referenceData!
                same_as_reference = io.StringIO('label1,value\n'
                                                'a,6\n'
                                                'b,7\n')
                _self.subjectData = CsvSource(same_as_reference, in_memory=True)

            def test_method(_self):
                _self.assertDataColumns()  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_pass_using_set_arg_reference(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                #_self.referenceData =   <- Not defined!
                subject = io.StringIO('label1,value\n'
                                      'a,6\n'
                                      'b,7\n')
                _self.subjectData = CsvSource(subject, in_memory=True)

            def test_method(_self):
                reference_set = set(['label1', 'value'])
                _self.assertDataColumns(ref=reference_set)  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_pass_using_source_arg_reference(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                #_self.referenceData =   <- Not defined!
                subject = io.StringIO('label1,value\n'
                                      'a,6\n'
                                      'b,7\n')
                _self.subjectData = CsvSource(subject, in_memory=True)

            def test_method(_self):
                reference = io.StringIO('label1,value\n'
                                        'a,6\n'
                                        'b,7\n')
                ref_source = CsvSource(reference, in_memory=True)
                _self.assertDataColumns(ref=ref_source)  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_extra(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                too_many = io.StringIO('label1,label2,value\n'
                                       'a,x,6\n'
                                       'b,y,7\n')
                _self.subjectData = CsvSource(too_many, in_memory=True)

            def test_method(_self):
                _self.assertDataColumns()  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "different column names:\n Extra\(u?'label2'\)"
        self.assertRegex(failure, pattern)

    def test_missing(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                too_few = io.StringIO('label1\n'
                                      'a\n'
                                      'b\n')
                _self.subjectData = CsvSource(too_few, in_memory=True)

            def test_method(_self):
                _self.assertDataColumns()  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "different column names:\n Missing\(u?'value'\)"
        self.assertRegex(failure, pattern)


class TestAssertDataSet(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label,label2\n'
                          'a,x\n'
                          'b,y\n'
                          'c,z\n')
        self.data_source = CsvSource(_fh, in_memory=True)

    def test_collection(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.subjectData = self.data_source

            def test_set(_self):
                required = set(['a', 'b', 'c'])
                _self.assertDataSet('label', required)  # <- test assert

            def test_list(_self):
                required = ['a', 'b', 'c']
                _self.assertDataSet('label', required)  # <- test assert

            def test_iterator(_self):
                required = iter(['a', 'b', 'c'])
                _self.assertDataSet('label', required)  # <- test assert

            def test_generator(_self):
                required = (x for x in ['a', 'b', 'c'])
                _self.assertDataSet('label', required)  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_set')
        self.assertIsNone(failure)

        failure = self._run_one_test(_TestClass, 'test_list')
        self.assertIsNone(failure)

        failure = self._run_one_test(_TestClass, 'test_iterator')
        self.assertIsNone(failure)

        failure = self._run_one_test(_TestClass, 'test_generator')
        self.assertIsNone(failure)

    def test_callable(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.subjectData = self.data_source

            def test_method(_self):
                required = lambda x: x in ['a', 'b', 'c']
                _self.assertDataSet('label', required)  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

        # Multiple args
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.subjectData = self.data_source

            def test_method(_self):
                required = lambda x, y: x in ['a', 'b', 'c'] and y in ['x', 'y', 'z']
                _self.assertDataSet(['label', 'label2'], required)  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_same(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.data_source
                same_as_reference = io.StringIO('label\n'
                                                'a\n'
                                                'b\n'
                                                'c\n')
                _self.subjectData = CsvSource(same_as_reference, in_memory=True)

            def test_method(_self):
                _self.assertDataSet('label')  # <- test assert

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
                _self.subjectData = CsvSource(same_as_reference, in_memory=True)

            def test_method(_self):
                required = set(['a', 'b', 'c'])
                _self.assertDataSet('label', required)  # <- test assert

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
                _self.subjectData = CsvSource(same_as_reference, in_memory=True)

            def test_method(_self):
                required = set([('a', 'x'), ('b', 'y'), ('c', 'z')])
                _self.assertDataSet(['label1', 'label2'], required)  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_missing(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.data_source
                same_as_reference = io.StringIO('label\n'
                                                'a\n'
                                                'b\n')
                _self.subjectData = CsvSource(same_as_reference, in_memory=True)

            def test_method(_self):
                _self.assertDataSet('label')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "different 'label' values:\n Missing\(u?'c'\)"
        self.assertRegex(failure, pattern)

    def test_extra(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.data_source
                same_as_reference = io.StringIO('label\n'
                                                'a\n'
                                                'b\n'
                                                'c\n'
                                                'd\n')
                _self.subjectData = CsvSource(same_as_reference, in_memory=True)

            def test_method(_self):
                _self.assertDataSet('label')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "different 'label' values:\n Extra\(u?'d'\)"
        self.assertRegex(failure, pattern)

    def test_same_group(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.data_source
                same_as_reference = io.StringIO('label,label2\n'
                                                'a,x\n'
                                                'b,y\n'
                                                'c,z\n')
                _self.subjectData = CsvSource(same_as_reference, in_memory=True)

            def test_method(_self):
                _self.assertDataSet(['label', 'label2'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_missing_group(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.data_source
                same_as_reference = io.StringIO('label,label2\n'
                                                'a,x\n'
                                                'c,z\n')
                _self.subjectData = CsvSource(same_as_reference, in_memory=True)

            def test_method(_self):
                _self.assertDataSet(['label', 'label2'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "different \[u?'label', u?'label2'\] values:\n Missing\(\(u?'b', u?'y'\)\)"
        self.assertRegex(failure, pattern)


class TestAssertDataRegexAndNotDataRegex(TestHelperCase):
    def setUp(self):
        self.source = io.StringIO('label1,label2\n'
                                  '0aaa,001\n'
                                  'b9bb,2\n'
                                  ' ccc,003\n')

    def test_regex_passing(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.subjectData = CsvSource(self.source, in_memory=True)

            def test_method(_self):
                _self.assertDataRegex('label1', '\w\w')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_regex_failing(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.subjectData = CsvSource(self.source, in_memory=True)

            def test_method(_self):
                _self.assertDataRegex('label2', '\d\d\d')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "non-matching 'label2' values:\n Invalid\(u?'2'\)"
        self.assertRegex(failure, pattern)

    def test_regex_precompiled(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.subjectData = CsvSource(self.source, in_memory=True)

            def test_method(_self):
                regex = re.compile('[ABC]$', re.IGNORECASE)  # <- pre-compiled
                _self.assertDataRegex('label1', regex)  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_not_regex_passing(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.subjectData = CsvSource(self.source, in_memory=True)

            def test_method(_self):
                _self.assertDataNotRegex('label1', '\d\d\d')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_not_regex_failing(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.subjectData = CsvSource(self.source, in_memory=True)

            def test_method(_self):
                _self.assertDataNotRegex('label2', '^\d{1,2}$')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "matching 'label2' values:\n Invalid\(u?'2'\)"
        self.assertRegex(failure, pattern)

    def test_not_regex_precompiled(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.subjectData = CsvSource(self.source, in_memory=True)

            def test_method(_self):
                regex = re.compile('^[ABC]')  # <- pre-compiled
                _self.assertDataNotRegex('label1', regex)  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)


class TestAllowSpecified(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label1,value\n'
                          'a,65\n'
                          'b,70\n')
        self.reference = CsvSource(_fh, in_memory=True)

        _fh = io.StringIO('label1,label2,value\n'
                          'a,x,18\n'  # <- off by +1
                          'a,x,13\n'
                          'a,y,20\n'
                          'a,z,15\n'
                          'b,z,4\n'   # <- off by -1
                          'b,y,40\n'
                          'b,x,25\n')
        self.bad_subject = CsvSource(_fh, in_memory=True)

    def test_accept_list(self):
        """Test should pass with expected difference."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                _self.subjectData = self.bad_subject

            def test_method(_self):
                diff = [
                    Deviation(+1, 65, label1='a'),
                    Deviation(-1, 70, label1='b'),
                ]
                with _self.allowSpecified(diff):
                    _self.assertDataSum('value', ['label1'])  # <- test assert

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
                    'One extra.': Deviation(+1, 65, label1='a'),
                    'One missing.': Deviation(-1, 70, label1='b'),
                }
                with _self.allowSpecified(diff):
                    _self.assertDataSum('value', ['label1'])  # <- test assert

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
                    'Omitted': [Deviation(+1, 65, label1='a'),
                                Deviation(-1, 70, label1='b')]
                }
                with _self.allowSpecified(diff):
                    _self.assertDataSum('value', ['label1'])  # <- test assert

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
                    Deviation(-1, 70, label1='b'),
                    Deviation(+2, 65, label1='a'),
                ]
                with _self.allowSpecified(diff):
                    _self.assertDataSum('value', ['label1'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "different 'value' sums:\n Deviation\(\+1, 65, label1=u?'a'\)"
        self.assertRegex(failure, pattern)

    def test_accepted_not_found_with_diff(self):
        """If accepted differences not found, raise exception."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                _self.subjectData = self.bad_subject

            def test_method(_self):
                diff = [
                    Deviation(-1, 70, label1='b'),
                    Deviation(+1, 65, label1='a'),
                    Deviation(+2, 65, label1='a')
                ]
                with _self.allowSpecified(diff):
                    _self.assertDataSum('value', ['label1'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("Allowed difference not found:\n"
                   " Deviation\(\+2, 65, label1=u?'a'\)")
        self.assertRegex(failure, pattern)

    def test_accepted_not_found_without_diff(self):
        """If accepted differences not found and no diff at all, raise exception."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                _self.subjectData = self.reference

            def test_method(_self):
                diff = Deviation(+2, 65, label1='a')
                with _self.allowSpecified(diff):
                    _self.assertDataSum('value', ['label1'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataAssertionError: Allowed difference not found:\n"
                   " Deviation\(\+2, 65, label1=u?'a'\)")
        self.assertRegex(failure, pattern)


class TestAllowUnspecified(TestHelperCase):
    def test_passing(self):
        """Pass when observed number is less-than or equal-to allowed number."""
        class _TestClass(DataTestCase):
            def test_method1(_self):
                with _self.allowUnspecified(3):  # <- allow three
                    differences = [
                        Missing('foo'),
                        Missing('bar'),
                        Missing('baz'),
                    ]
                    raise DataAssertionError('some differences', differences)

            def test_method2(_self):
                with _self.allowUnspecified(4):  # <- allow four
                    differences = [
                        Missing('foo'),
                        Missing('bar'),
                        Missing('baz'),
                    ]
                    raise DataAssertionError('some differences', differences)

        failure = self._run_one_test(_TestClass, 'test_method1')
        self.assertIsNone(failure)

        failure = self._run_one_test(_TestClass, 'test_method2')
        self.assertIsNone(failure)

    def test_failing(self):
        """Fail when observed number is greater-than allowed number."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = None
                _self.subjectData = None

            def test_method(_self):
                with _self.allowUnspecified(2):  # <- allow two
                    differences = [
                        Missing('foo'),
                        Missing('bar'),
                        Missing('baz'),
                    ]
                    raise DataAssertionError('some differences', differences)

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataAssertionError: expected at most 2 differences, got 3: some differences:\n"
                   " Missing[^\n]+\n"
                   " Missing[^\n]+\n"
                   " Missing[^\n]+\n$")
        self.assertRegex(failure, pattern)


class TestAllowMissing(TestHelperCase):
    def test_passing(self):
        """Pass when the only differences found are Missing differences."""
        class _TestClass(DataTestCase):
            def test_method1(_self):
                with _self.allowMissing():  # <- allow Missing differences
                    differences = [
                        Missing('foo'),
                        Missing('bar'),
                        Missing('baz'),
                    ]
                    raise DataAssertionError('some differences', differences)

            def test_method2(_self):
                with _self.allowMissing():  # <- also pass with zero difference
                    pass

        failure = self._run_one_test(_TestClass, 'test_method1')
        self.assertIsNone(failure)

        failure = self._run_one_test(_TestClass, 'test_method2')
        self.assertIsNone(failure)

    def test_failing(self):
        """Fail with non-Missing differences."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = None
                _self.subjectData = None

            def test_method(_self):
                with _self.allowMissing():
                    differences = [
                        Missing('foo'),
                        Extra('bar'),
                        Extra('baz'),
                    ]
                    raise DataAssertionError('some differences', differences)

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataAssertionError: some differences:\n"
                   " Extra[^\n]+\n"
                   " Extra[^\n]+\n$")
        self.assertRegex(failure, pattern)


class TestAllowExtra(TestHelperCase):
    def test_passing(self):
        """Pass when the only differences found are Extra differences."""
        class _TestClass(DataTestCase):
            def test_method1(_self):
                with _self.allowExtra():  # <- allow Extra differences
                    differences = [
                        Extra('foo'),
                        Extra('bar'),
                        Extra('baz'),
                    ]
                    raise DataAssertionError('some differences', differences)

            def test_method2(_self):
                with _self.allowExtra():  # <- also pass with zero difference
                    pass

        failure = self._run_one_test(_TestClass, 'test_method1')
        self.assertIsNone(failure)

        failure = self._run_one_test(_TestClass, 'test_method2')
        self.assertIsNone(failure)

    def test_failing(self):
        """Fail with non-Extra differences."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = None
                _self.subjectData = None

            def test_method(_self):
                with _self.allowExtra():
                    differences = [
                        Extra('foo'),
                        Missing('bar'),
                        Missing('baz'),
                    ]
                    raise DataAssertionError('some differences', differences)

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataAssertionError: some differences:\n"
                   " Missing[^\n]+\n"
                   " Missing[^\n]+\n$")
        self.assertRegex(failure, pattern)


class TestAllowDeviation(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label1,value\n'
                          'a,65\n'
                          'b,70\n')
        self.reference = CsvSource(_fh, in_memory=True)

        _fh = io.StringIO('label1,label2,value\n'
                          'a,x,20\n'  # <- off by +3
                          'a,x,13\n'
                          'a,y,20\n'
                          'a,z,15\n'
                          'b,z,4\n'   # <- off by -1
                          'b,y,40\n'
                          'b,x,25\n')
        self.bad_subject = CsvSource(_fh, in_memory=True)

    def test_absolute_tolerance(self):
        """If accepted differences not found, raise exception."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                _self.subjectData = self.bad_subject

            def test_method(_self):
                with _self.allowDeviation(3):  # <- test tolerance
                    _self.assertDataSum('value', ['label1'])

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_absolute_tolerance_with_filter(self):
        """Using filter label1='a', Deviation(...label1='b') should be raised."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                _self.subjectData = self.bad_subject

            def test_method(_self):
                with _self.allowDeviation(3, label1='a'):  # <- Allow label1='a' only.
                    _self.assertDataSum('value', ['label1'])

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataAssertionError: different u?'value' sums:\n"
                   " Deviation\(-1, 70, label1=u?'b'\)")
        self.assertRegex(failure, pattern)


        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                _self.subjectData = self.bad_subject

            def test_method(_self):
                with _self.allowDeviation(3, label1=['a', 'b']):  # <- Filter to 'a' or 'b' only.
                    _self.assertDataSum('value', ['label1'])

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_inadequate_absolute_tolerance(self):
        """Given tolerance of 2, Deviation(+3) should still be raised."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                _self.subjectData = self.bad_subject

            def test_method(_self):
                with _self.allowDeviation(2):  # <- test tolerance
                    _self.assertDataSum('value', ['label1'])

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataAssertionError: different u?'value' sums:\n"
                   " Deviation\(\+3, 65, label1=u?'a'\)")
        self.assertRegex(failure, pattern)

    def test_tolerance_error(self):
        """Must throw error if tolerance is invalid."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                _self.subjectData = self.bad_subject

            def test_method(_self):
                with _self.allowDeviation(-5):  # <- invalid
                    _self.assertDataSum('value', ['label1'])

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
    #            with _self.allowDeviation(3):  # <- test tolerance
    #                _self.assertDataSum('value', ['label1'])
    #
    #    failure = self._run_one_test(_TestClass, 'test_method')
    #    pattern = 'no errors...'
    #    self.assertRegex(failure, pattern)


class TestAllowDeviationUpper(TestHelperCase):
    def test_passing(self):
        """If accepted differences not found, raise exception."""
        class _TestClass(DataTestCase):
            def test_method(_self):
                with _self.allowDeviationUpper(3):  # <- Allow deviation of 0 to +3
                    differences = [
                        Deviation(+1, 10, column1='foo'),
                        Deviation(0, 10, column1='bar'),
                        Deviation(+3, 10, column1='baz'),
                    ]
                    raise DataAssertionError('some differences', differences)

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_over_deviation(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = None
                _self.subjectData = None

            def test_method(_self):
                with _self.allowDeviationUpper(3):  # <- Allow deviation of 0 to +3
                    differences = [
                        Deviation(+2, 10, column1='foo'),
                        Deviation(+3, 10, column1='bar'),
                        Deviation(+4, 10, column1='baz'),
                    ]
                    raise DataAssertionError('some differences', differences)

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataAssertionError: some differences:\n"
                   " Deviation\(\+4, 10, column1=u?'baz'\)")
        self.assertRegex(failure, pattern)

    def test_under_zero(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = None
                _self.subjectData = None

            def test_method(_self):
                with _self.allowDeviationUpper(3):  # <- Allow deviation of 0 to +3
                    differences = [
                        Deviation(+2, 10, column1='foo'),
                        Deviation(+3, 10, column1='bar'),
                        Deviation(-1, 10, column1='baz'),
                    ]
                    raise DataAssertionError('some differences', differences)

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataAssertionError: some differences:\n"
                   " Deviation\(-1, 10, column1=u?'baz'\)\n")
        self.assertRegex(failure, pattern)

class TestAllowDeviationLower(TestHelperCase):
    def test_passing(self):
        """If accepted differences not found, raise exception."""
        class _TestClass(DataTestCase):
            def test_method(_self):
                with _self.allowDeviationLower(-3):  # <- Allow deviation of -3 to 0
                    differences = [
                        Deviation(-1, 10, column1='foo'),
                        Deviation(0, 10, column1='bar'),
                        Deviation(-3, 10, column1='baz'),
                    ]
                    raise DataAssertionError('some differences', differences)

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_under_deviation(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = None
                _self.subjectData = None

            def test_method(_self):
                with _self.allowDeviationLower(-3):  # <- Allow deviation of 0 to +3
                    differences = [
                        Deviation(-2, 10, column1='foo'),
                        Deviation(-3, 10, column1='bar'),
                        Deviation(-4, 10, column1='baz'),
                    ]
                    raise DataAssertionError('some differences', differences)

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataAssertionError: some differences:\n"
                   " Deviation\(-4, 10, column1=u?'baz'\)")
        self.assertRegex(failure, pattern)

    def test_over_zero(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = None
                _self.subjectData = None

            def test_method(_self):
                with _self.allowDeviationLower(-3):  # <- Allow deviation of 0 to +3
                    differences = [
                        Deviation(-2, 10, column1='foo'),
                        Deviation(-3, 10, column1='bar'),
                        Deviation(+1, 10, column1='baz'),
                    ]
                    raise DataAssertionError('some differences', differences)

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataAssertionError: some differences:\n"
                   " Deviation\(\+1, 10, column1=u?'baz'\)\n")
        self.assertRegex(failure, pattern)


class TestAllowPercentDeviation(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label1,value\n'
                          'a,65\n'
                          'b,70\n')
        self.reference = CsvSource(_fh, in_memory=True)

        _fh = io.StringIO('label1,label2,value\n'
                          'a,x,20\n'  # <- off by +3
                          'a,x,13\n'
                          'a,y,20\n'
                          'a,z,15\n'
                          'b,z,4\n'   # <- off by -1
                          'b,y,40\n'
                          'b,x,25\n')
        self.bad_subject = CsvSource(_fh, in_memory=True)

    def test_percent_tolerance(self):
        """If accepted differences not found, raise exception."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                _self.subjectData = self.bad_subject

            def test_method(_self):
                with _self.allowPercentDeviation(0.05):  # <- test tolerance
                    _self.assertDataSum('value', ['label1'])

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_with_filter(self):
        """If accepted differences not found, raise exception."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                _self.subjectData = self.bad_subject

            def test_method(_self):
                with _self.allowPercentDeviation(0.05, label1='a'):  # <- Allow label1='a' only.
                    _self.assertDataSum('value', ['label1'])

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataAssertionError: different u?'value' sums:\n"
                   " Deviation\(-1, 70, label1=u?'b'\)")
        self.assertRegex(failure, pattern)

    def test_inadequate_tolerance(self):
        """If accepted differences not found, raise exception."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                _self.subjectData = self.bad_subject

            def test_method(_self):
                with _self.allowPercentDeviation(0.03):  # <- test tolerance
                    _self.assertDataSum('value', ['label1'])

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataAssertionError: different u?'value' sums:\n"
                   " Deviation\(\+3, 65, label1=u?'a'\)")
        self.assertRegex(failure, pattern)

    def test_error(self):
        """Tolerance must throw error if invalid parameter."""
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                _self.subjectData = self.bad_subject

            def test_method(_self):
                with _self.allowPercentDeviation(1.1):  # <- invalid
                    _self.assertDataSum('value', ['label1'])

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ('AssertionError: Percent tolerance must be between 0 and 1.')
        self.assertRegex(failure, pattern)

    def test_zero_denominator(self):
        """Test for divide-by-zero condition."""
        _fh1 = io.StringIO('label1,value\n'
                          'a,65\n'
                          'b,70\n')
        subject = CsvSource(_fh1, in_memory=True)

        _fh2 = io.StringIO('label1,value\n'
                          'a,64\n'
                          'b,0\n')
        reference = CsvSource(_fh2, in_memory=True)

        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = reference
                _self.subjectData = subject

            def test_method(_self):
                with _self.allowPercentDeviation(0.03):  # <- test tolerance
                    _self.assertDataSum('value', ['label1'])

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataAssertionError: different u?'value' sums:\n"
                   " Deviation\(\+70, 0, label1=u?'b'\)")
        self.assertRegex(failure, pattern)


class TestNestedAllowances(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label1,value\n'
                          'a,65\n'
                          'b,70\n')
        self.reference = CsvSource(_fh, in_memory=True)

        _fh = io.StringIO('label1,label2,value\n'
                          'a,x,20\n'  # <- off by +3
                          'a,x,13\n'
                          'a,y,20\n'
                          'a,z,15\n'
                          'b,z,4\n'   # <- off by -1
                          'b,y,40\n'
                          'b,x,25\n')
        self.bad_subject = CsvSource(_fh, in_memory=True)

    def test_tolerance_in_difference(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                _self.subjectData = self.bad_subject

            def test_method(_self):
                with _self.allowSpecified(Deviation(+3, 65, label1='a')):
                    with _self.allowDeviation(2):  # <- test tolerance
                        _self.assertDataSum('value', ['label1'])

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_difference_in_tolerance(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                _self.subjectData = self.bad_subject

            def test_method(_self):
                with _self.allowDeviation(2):  # <- test tolerance
                    with _self.allowSpecified(Deviation(+3, 65, label1='a')):
                        _self.assertDataSum('value', ['label1'])

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_difference_not_found_in_tolerance(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.referenceData = self.reference
                _self.subjectData = self.bad_subject

            def test_method(_self):
                with _self.allowSpecified(Deviation(+10, 999, label1='a')):
                    with _self.allowDeviation(3):
                        _self.assertDataSum('value', ['label1'])

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataAssertionError: Allowed difference not found:\n"
                   " Deviation\(\+10, 999, label1=u?'a'\)")
        self.assertRegex(failure, pattern)
