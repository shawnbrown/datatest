# -*- coding: utf-8 -*-
import inspect
import re
from unittest import TestCase as _TestCase  # Originial TestCase, not
                                            # compatibility layer.

# Import compatiblity layers.
from . import _io as io
from . import _unittest as unittest
from .common import MinimalSource

# Import code to test.
from datatest.case import DataTestCase
from datatest import DataError
from datatest import CompareSet
#from datatest import CompareDict
from datatest import Extra
from datatest import Missing
from datatest import Invalid
from datatest import Deviation
from datatest import CsvSource

from datatest import allow_only
from datatest import allow_any
from datatest import allow_missing
from datatest import allow_extra
from datatest import allow_limit
from datatest import allow_deviation
from datatest import allow_percent_deviation


class TestHelperCase(unittest.TestCase):
    """Helper class for subsequent cases."""
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


class TestSubclass(TestHelperCase):
    def test_subclass(self):
        """DataTestCase should be a subclass of unittest.TestCase."""
        self.assertTrue(issubclass(DataTestCase, _TestCase))


class TestNoDefaultSubject(TestHelperCase):
    def test_no_subject(self):
        class _TestClass(DataTestCase):
            def test_method1(_self):
                first  = CompareSet([1,2,3])
                second = CompareSet([1,2,3])
                _self.assertEqual(first, second)

            def test_method2(_self):
                required = CompareSet([1,2,3])
                _self.assertSubjectSet(required)

        failure = self._run_one_test(_TestClass, 'test_method1')
        self.assertIsNone(failure)

        failure = self._run_one_test(_TestClass, 'test_method2')
        self.assertRegex(failure, "cannot find 'subject'")


class TestAssertValid(DataTestCase):
    """The assertValid() method should handle all supported validation
    comparisons.  These comparisons are implemented using four separate
    functions (one for each supported *required* type):

    +--------------------------------------------------------------+
    |       Object Comparisons and Returned Difference Type        |
    +-------------------+------------------------------------------+
    |                   |           *required* condition           |
    | *data* under test +------+---------+----------+--------------+
    |                   | set  | mapping | sequence | str or other |
    +===================+======+=========+==========+==============+
    | **set**           | list |         |          | list         |
    +-------------------+------+---------+----------+--------------+
    | **mapping**       | list | dict    |          | dict         |
    +-------------------+------+---------+----------+--------------+
    | **sequence**      | list |         | dict     | dict         |
    +-------------------+------+---------+----------+--------------+
    | **iterable**      | list |         |          | list         |
    +-------------------+------+---------+----------+--------------+
    | **str or other**  |      |         |          | list         |
    +-------------------+------+---------+----------+--------------+

    Currently, this test checks that the appropriate underlying function
    is called given the type of the *required* argument.  For a
    comprehensive test of all underlying functions, see the
    test_compare.py file.
    """
    def test_required_set(self):
        """When *required* is a set, _compare_set() should be called."""
        with self.assertRaises(DataError) as cm:
            required = set([1, 2, 4])
            data = set([1, 2, 3])
            self.assertValid(data, required)

        differences = cm.exception.differences
        self.assertEqual(set(differences), set([Extra(3), Missing(4)]))

    def test_required_mapping(self):
        """When *required* is a mapping, _compare_mapping() should be
        called."""
        with self.assertRaises(DataError) as cm:
            required = {'AAA': 'a', 'BBB': 'b', 'CCC': 'c'}
            data = {'AAA': 'a', 'BBB': 'b', 'DDD': 'd'}
            self.assertValid(data, required)

        differences = cm.exception.differences
        self.assertEqual(differences, {'CCC': Missing('c'), 'DDD': Extra('d')})

    def test_required_sequence(self):
        """When *required* is a sequence, _compare_sequence() should be
        called."""
        with self.assertRaises(DataError) as cm:
            required = ['a', 2, 'c', 4]
            data = ['a', 2, 'x', 3]
            self.assertValid(data, required)

        differences = cm.exception.differences
        self.assertEqual = super(DataTestCase, self).assertEqual
        self.assertEqual(differences, {2: Invalid('x', 'c'), 3: Deviation(-1, 4)})

    def test_required_other(self):
        """When *required* is a string or other object, _compare_other()
        should be called."""
        with self.assertRaises(DataError) as cm:
            required = lambda x: x.isupper()
            data = ['AAA', 'BBB', 'ccc', 'DDD']
            self.assertValid(data, required)

        differences = cm.exception.differences
        self.assertEqual = super(DataTestCase, self).assertEqual
        self.assertEqual(differences, {2: Invalid('ccc')})


class TestFunctionSignature(DataTestCase):
    """In addition to its normal *data/requirement* signature, the
    assertValid() method also supports a *function* signature.

    When calling assertValid() with a function of one argument, the
    function is used to get the data and requirement from the test
    case's subject and reference sources.
    """
    def setUp(self):
        self.subject = MinimalSource(data=[['AAA', 1], ['BBB', 2], ['CCC', 3]],
                                     fieldnames=['col1', 'col2'])
        self.reference = MinimalSource(data=[['AAA', 1], ['BBB', 2], ['CCC', 3]],
                                       fieldnames=['col1', 'col2'])

    def test_function(self):
        def function(src):
            return src.sum('col2')

        self.assertValid(function)

    def test_lambda(self):
        function = lambda src: src.sum('col2')
        self.assertValid(function)

    def test_msg(self):
        def function(src):
            return src.sum('col2')

        self.assertValid(function, 'test message')  # As positional argument.

        self.assertValid(function, msg='test message')  # As keyword argument.


class TestAssertEqual(TestHelperCase):
    @unittest.skip('Waiting until assertEqual() is migrated to __past__.')
    def test_method_identity(self):
        """The datatest.TestCase class should NOT wrap the assertEqual()
        method of its superclass.
        """
        datatest_assertEqual = DataTestCase.assertEqual
        unittest_assertEqual = unittest.TestCase.assertEqual
        self.assertIs(datatest_assertEqual, unittest_assertEqual)

    def testAssertEqual(self):
        class _TestClass(DataTestCase):
            def test_method1(_self):
                first  = CompareSet([1,2,3,4,5,6,7])
                second = CompareSet([1,2,3,4,5,6])
                _self.assertEqual(first, second)

            def test_method2(_self):
                first  = CompareSet([1,2,3,4,5,6,7])
                second = set([1,2,3,4,5,6])  # <- Built-in set type!!!
                _self.assertEqual(first, second)

            def test_method3(_self):
                first  = CompareSet([1,2,3,4,5,6,7])
                second = lambda x: x <= 6  # <- callable
                _self.assertEqual(first, second)

            def test_method4(_self):
                first  = CompareSet([1,2,3,4,5,6,7])
                second = lambda x: x < 10  # <- callable
                _self.assertEqual(first, second)

        pattern = r"first object does not match second object:\n Extra\(7\)"

        failure = self._run_one_test(_TestClass, 'test_method1')
        self.assertRegex(failure, pattern)

        failure = self._run_one_test(_TestClass, 'test_method2')
        self.assertRegex(failure, pattern)

        pattern = r"first object contains invalid items:\n Invalid\(7\)"
        failure = self._run_one_test(_TestClass, 'test_method3')
        self.assertRegex(failure, pattern)

        failure = self._run_one_test(_TestClass, 'test_method4')
        self.assertIsNone(failure)

    def test_set_dict(self):
        class _TestClass(DataTestCase):
            def test_method1(_self):
                first  = set([1,2,3,4,5,6,7])
                second = set([1,2,3,4,5,6])
                _self.assertEqual(first, second)

            def test_method2(_self):
                first  = {'foo': 'AAA', 'bar': 'BBB'}
                second = {'foo': 'AAA', 'bar': 'BBB', 'baz': 'CCC'}
                _self.assertEqual(first, second)

            def test_method3(_self):
                first  = {'foo': 1, 'bar': 2, 'baz': 2}
                second = {'foo': 1, 'bar': 2, 'baz': 3}
                _self.assertEqual(first, second)

        pattern = r"first object does not match second object:\n Extra\(7\)"
        failure = self._run_one_test(_TestClass, 'test_method1')
        self.assertRegex(failure, pattern)

        pattern = r"first object does not match second object:\n Missing\('CCC', _0=u?'baz'\)"
        failure = self._run_one_test(_TestClass, 'test_method2')
        self.assertRegex(failure, pattern)

        pattern = r"first object does not match second object:\n Deviation\(-1, 3, _0=u?'baz'\)"
        failure = self._run_one_test(_TestClass, 'test_method3')
        self.assertRegex(failure, pattern)

    def test_int_str(self):
        class _TestClass(DataTestCase):
            def test_method1(_self):
                first  = 4
                second = set([4, 7])
                _self.assertEqual(first, second)

            def test_method3(_self):
                first  = 'foo'
                second = set(['foo', 'bar'])
                _self.assertEqual(first, second)

        pattern = r"first object does not match second object:\n Missing\(7\)"
        failure = self._run_one_test(_TestClass, 'test_method1')
        self.assertRegex(failure, pattern)

        pattern = r"first object does not match second object:\n Missing\('bar'\)"
        failure = self._run_one_test(_TestClass, 'test_method3')
        self.assertRegex(failure, pattern)


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

    def test_normalize_required(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.reference = self.test_reference
                _self.subject = self.test_subject

            def test_method(_self):  # Dummy method for instantiation.
                pass

        instance = _TestClass('test_method')

        #original = set(['x', 'y', 'z'])
        #normalized = instance._normalize_required(None, 'distinct', 'label2')
        #self.assertIsNot(original, normalized)
        #self.assertEqual(original, normalized)

        # Set object should return unchanged.
        original = set(['x', 'y', 'z'])
        normalized = instance._normalize_required(original, 'distinct', 'label2')
        self.assertIs(original, normalized)

        # Alternate reference source.
        _fh = io.StringIO('label1,value\n'
                          'c,75\n'
                          'd,80\n')
        altsrc = CsvSource(_fh, in_memory=True)
        normalized = instance._normalize_required(altsrc, 'distinct', 'label1')
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
        # Test using required dict.
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.subject = self.src1_records

            def test_method(_self):
                required = {'a': 65, 'b': 70}
                _self.assertSubjectSum('value', ['label1'], required)  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

        # Test using reference.
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.reference = self.src1_totals
                _self.subject = self.src1_records

            def test_method(_self):
                _self.assertSubjectSum('value', ['label1'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

        # Test using callable.
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.reference = self.src1_totals
                _self.subject = self.src1_records

            def test_method(_self):
                required = lambda x: x in (65, 70)
                _self.assertSubjectSum('value', ['label1'], required)  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_failing_case(self):
        """Sums are unequal, test should fail."""
        # Test using required dict.
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.subject = self.src2_records  # <- src1 != src2

            def test_method(_self):
                required = {'a': 65, 'b': 70}
                _self.assertSubjectSum('value', ['label1'], required)  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataError: different 'value' sums:\n"
                   " Deviation\(\+1, 65, label1=u?'a'\),\n"
                   " Deviation\(-1, 70, label1=u?'b'\)")
        self.assertRegex(failure, pattern)

        # Test using reference.
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.reference = self.src1_totals
                _self.subject = self.src2_records  # <- src1 != src2

            def test_method(_self):
                _self.assertSubjectSum('value', ['label1'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataError: different 'value' sums:\n"
                   " Deviation\(\+1, 65, label1=u?'a'\),\n"
                   " Deviation\(-1, 70, label1=u?'b'\)")
        self.assertRegex(failure, pattern)

        # Test using callable.
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.subject = self.src2_records  # <- src1 != src2

            def test_method(_self):
                required = lambda x: x in (65, 70)
                _self.assertSubjectSum('value', ['label1'], required)  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataError: different 'value' sums:\n"
                   " Invalid\(66, label1=u?'a'\),\n"
                   " Invalid\(69, label1=u?'b'\)")
        #pattern = ("DataError: different 'value' sums:\n"
        #           " Invalid\(Decimal\('66'\), label1=u?'a'\),\n"
        #           " Invalid\(Decimal\('69'\), label1=u?'b'\)")
        self.assertRegex(failure, pattern)


class TestAssertSubjectSumGroupsAndFilters(TestHelperCase):
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
                _self.reference = self.src3_totals
                _self.subject = self.src3_records  # <- src1 != src2

            def test_method(_self):
                _self.assertSubjectSum('value', ['label1'], label2='y')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = ("DataError: different 'value' sums:\n"
                   " Deviation\(\+1, 20, label1=u?'a'\),\n"
                   " Deviation\(-1, 40, label1=u?'b'\)")
        self.assertRegex(failure, pattern)


class TestAssertSubjectSet(TestHelperCase):
    def setUp(self):
        _fh = io.StringIO('label,label2\n'
                          'a,x\n'
                          'b,y\n'
                          'c,z\n')
        self.data_source = CsvSource(_fh, in_memory=True)

    def test_collection(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.subject = self.data_source

            def test_set(_self):
                required = set(['a', 'b', 'c'])
                _self.assertSubjectSet('label', required)  # <- test assert

            def test_list(_self):
                required = ['a', 'b', 'c']
                _self.assertSubjectSet('label', required)  # <- test assert

            def test_iterator(_self):
                required = iter(['a', 'b', 'c'])
                _self.assertSubjectSet('label', required)  # <- test assert

            def test_generator(_self):
                required = (x for x in ['a', 'b', 'c'])
                _self.assertSubjectSet('label', required)  # <- test assert

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
                _self.subject = self.data_source

            def test_method(_self):
                required = lambda x: x in ['a', 'b', 'c']
                _self.assertSubjectSet('label', required)  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

        # Multiple args
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.subject = self.data_source

            def test_method(_self):
                required = lambda x, y: x in ['a', 'b', 'c'] and y in ['x', 'y', 'z']
                _self.assertSubjectSet(['label', 'label2'], required)  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_same(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.reference = self.data_source
                same_as_reference = io.StringIO('label\n'
                                                'a\n'
                                                'b\n'
                                                'c\n')
                _self.subject = CsvSource(same_as_reference, in_memory=True)

            def test_method(_self):
                _self.assertSubjectSet('label')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_same_using_reference_from_argument(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                #_self.reference =   <- intentionally omitted
                same_as_reference = io.StringIO('label\n'
                                                'a\n'
                                                'b\n'
                                                'c\n')
                _self.subject = CsvSource(same_as_reference, in_memory=True)

            def test_method(_self):
                required = set(['a', 'b', 'c'])
                _self.assertSubjectSet('label', required)  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_same_group_using_reference_from_argument(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                #_self.reference =   <- intentionally omitted
                same_as_reference = io.StringIO('label1,label2\n'
                                                'a,x\n'
                                                'b,y\n'
                                                'c,z\n')
                _self.subject = CsvSource(same_as_reference, in_memory=True)

            def test_method(_self):
                required = set([('a', 'x'), ('b', 'y'), ('c', 'z')])
                _self.assertSubjectSet(['label1', 'label2'], required)  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_missing(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.reference = self.data_source
                same_as_reference = io.StringIO('label\n'
                                                'a\n'
                                                'b\n')
                _self.subject = CsvSource(same_as_reference, in_memory=True)

            def test_method(_self):
                _self.assertSubjectSet('label')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "different 'label' values:\n Missing\(u?'c'\)"
        self.assertRegex(failure, pattern)

    def test_extra(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.reference = self.data_source
                same_as_reference = io.StringIO('label\n'
                                                'a\n'
                                                'b\n'
                                                'c\n'
                                                'd\n')
                _self.subject = CsvSource(same_as_reference, in_memory=True)

            def test_method(_self):
                _self.assertSubjectSet('label')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "different 'label' values:\n Extra\(u?'d'\)"
        self.assertRegex(failure, pattern)

    def test_invalid(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.subject = self.data_source

            def test_method(_self):
                required = lambda x: x in ('a', 'b')
                _self.assertSubjectSet('label', required)  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "different 'label' values:\n Invalid\(u?'c'\)"
        self.assertRegex(failure, pattern)

    def test_same_group(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.reference = self.data_source
                same_as_reference = io.StringIO('label,label2\n'
                                                'a,x\n'
                                                'b,y\n'
                                                'c,z\n')
                _self.subject = CsvSource(same_as_reference, in_memory=True)

            def test_method(_self):
                _self.assertSubjectSet(['label', 'label2'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_missing_group(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.reference = self.data_source
                same_as_reference = io.StringIO('label,label2\n'
                                                'a,x\n'
                                                'c,z\n')
                _self.subject = CsvSource(same_as_reference, in_memory=True)

            def test_method(_self):
                _self.assertSubjectSet(['label', 'label2'])  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "different \[u?'label', u?'label2'\] values:\n Missing\(\(u?'b', u?'y'\)\)"
        self.assertRegex(failure, pattern)


class TestAssertSubjectUnique(TestHelperCase):
    def test_required_set(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                data = [
                    ('label1', 'label2'),
                    ('a', 'x'),
                    ('b', 'y'),
                    ('c', 'z'),
                    ('d', 'z'),
                    ('e', 'z'),
                    ('f', 'z'),
                ]
                _self.subject = MinimalSource(data)

            def test_method1(_self):
                _self.assertSubjectUnique('label1')  # <- test assert

            def test_method2(_self):
                _self.assertSubjectUnique(['label1', 'label2'])  # <- test assert

            def test_method3(_self):
                _self.assertSubjectUnique('label2')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method1')
        self.assertIsNone(failure)

        failure = self._run_one_test(_TestClass, 'test_method2')
        self.assertIsNone(failure)

        failure = self._run_one_test(_TestClass, 'test_method3')
        pattern = "values in 'label2' are not unique:\n Extra\('z'\)"
        self.assertRegex(failure, pattern)


class TestAssertSubjectRegexAndNotDataRegex(TestHelperCase):
    def setUp(self):
        self.source = io.StringIO('label1,label2\n'
                                  '0aaa,001\n'
                                  'b9bb,2\n'
                                  ' ccc,003\n')

    def test_regex_passing(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.subject = CsvSource(self.source, in_memory=True)

            def test_method(_self):
                _self.assertSubjectRegex('label1', '\w\w')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_regex_failing(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.subject = CsvSource(self.source, in_memory=True)

            def test_method(_self):
                _self.assertSubjectRegex('label2', '\d\d\d')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "non-matching 'label2' values:\n Invalid\(u?'2'\)"
        self.assertRegex(failure, pattern)

    def test_regex_precompiled(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.subject = CsvSource(self.source, in_memory=True)

            def test_method(_self):
                regex = re.compile('[ABC]$', re.IGNORECASE)  # <- pre-compiled
                _self.assertSubjectRegex('label1', regex)  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_not_regex_passing(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.subject = CsvSource(self.source, in_memory=True)

            def test_method(_self):
                _self.assertSubjectNotRegex('label1', '\d\d\d')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)

    def test_not_regex_failing(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.subject = CsvSource(self.source, in_memory=True)

            def test_method(_self):
                _self.assertSubjectNotRegex('label2', '^\d{1,2}$')  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        pattern = "matching 'label2' values:\n Invalid\(u?'2'\)"
        self.assertRegex(failure, pattern)

    def test_not_regex_precompiled(self):
        class _TestClass(DataTestCase):
            def setUp(_self):
                _self.subject = CsvSource(self.source, in_memory=True)

            def test_method(_self):
                regex = re.compile('^[ABC]')  # <- pre-compiled
                _self.assertSubjectNotRegex('label1', regex)  # <- test assert

        failure = self._run_one_test(_TestClass, 'test_method')
        self.assertIsNone(failure)


class TestAllowanceWrappers(unittest.TestCase):
    """Test method wrappers for allowance context managers."""
    def setUp(self):
        class DummyCase(DataTestCase):
            def runTest(self):
                pass
        self.case = DummyCase()

    def test_allowOnly(self):
        cm = self.case.allowOnly([Missing('foo')])
        self.assertTrue(isinstance(cm, allow_only))

    def test_allowAny(self):
        cm = self.case.allowAny(foo='aaa')
        self.assertTrue(isinstance(cm, allow_any))

    def test_allowMissing(self):
        cm = self.case.allowMissing()
        self.assertTrue(isinstance(cm, allow_missing))

    def test_allowExtra(self):
        cm = self.case.allowExtra()
        self.assertTrue(isinstance(cm, allow_extra))

    def test_allowLimit(self):
        cm = self.case.allowLimit(10)
        self.assertTrue(isinstance(cm, allow_limit))

    def test_allowDeviation(self):
        cm = self.case.allowDeviation(5)
        self.assertTrue(isinstance(cm, allow_deviation))

    def test_allowPercentDeviation(self):
        result = self.case.allowPercentDeviation(5)
        self.assertTrue(isinstance(result, allow_percent_deviation))
