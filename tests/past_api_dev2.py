# -*- coding: utf-8 -*-
"""Test __past__.api_dev2 to assure backwards compatibility with first
development-release API.

.. note:: Because this sub-module works by monkey-patching the global
          ``datatest`` package, these tests should be run in a separate
          process.
"""
import re
from . import _io as io
from . import _unittest as unittest
from datatest.utils.decimal import Decimal

from .common import MinimalSource
import datatest
from datatest.__past__ import api_dev2  # <- MONKEY PATCH!!!

from datatest.error import DataError
from datatest import Missing
from datatest import Extra
from datatest import Invalid
from datatest import Deviation
from datatest.sources.csv import CsvSource
from datatest import DataTestCase
from datatest.compare import CompareSet
from datatest import allow_iter
from datatest import allow_each
from datatest import allow_any
from datatest import allow_only
from datatest import allow_limit
from datatest import allow_missing
from datatest import allow_extra
from datatest import allow_deviation
from datatest import allow_percent_deviation


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
                with self.assertRaises(DataError) as cm:
                    _self.assertEqual(first, second)  # <- Wrapped method!

                msg = 'In 0.7.0, assertEqual() should raise DataError.'
                _self.assertTrue(isinstance(cm.exception, DataError), msg)

                diffs = list(cm.exception.differences)
                _self.assertEqual(diffs, [datatest.Missing(4)])

        error, failure = self._run_wrapped_test(_TestWrapper, 'test_method')
        self.assertIsNone(error)
        self.assertIsNone(failure)


class TestAssertEqual(datatest.DataTestCase):
    """Test behavior of wrapped assertEqual() method."""
    def test_compareset_v_compareset_fail(self):
        with self.assertRaises(DataError) as cm:
            first  = CompareSet([1,2,3,4,5,6,7])
            second = CompareSet([1,2,3,4,5,6])
            self.assertEqual(first, second)

        differences = cm.exception.differences
        super(DataTestCase, self).assertEqual(differences, [Extra(7)])

    def test_compareset_v_set_fail(self):
        with self.assertRaises(DataError) as cm:
            first  = CompareSet([1,2,3,4,5,6,7])
            second = set([1,2,3,4,5,6])
            self.assertEqual(first, second)

        differences = cm.exception.differences
        super(DataTestCase, self).assertEqual(differences, [Extra(7)])

    def test_compareset_v_callable_fail(self):
        with self.assertRaises(DataError) as cm:
            first  = CompareSet([1,2,3,4,5,6,7])
            second = lambda x: x <= 6
            self.assertEqual(first, second)

        differences = cm.exception.differences
        super(DataTestCase, self).assertEqual(differences, [Invalid(7)])

    def test_compareset_v_callable_pass(self):
        first  = CompareSet([1,2,3,4,5,6,7])
        second = lambda x: x < 10
        self.assertEqual(first, second)

    def test_set_v_set_fail(self):
        with self.assertRaises(DataError) as cm:
            first  = set([1,2,3,4,5,6,7])
            second = set([1,2,3,4,5,6])
            self.assertEqual(first, second)

        differences = cm.exception.differences
        super(DataTestCase, self).assertEqual(differences, [Extra(7)])

    def test_dict_v_dict_membership_fail(self):
        with self.assertRaises(DataError) as cm:
            first  = {'foo': 'AAA', 'bar': 'BBB'}
            second = {'foo': 'AAA', 'bar': 'BBB', 'baz': 'CCC'}
            self.assertEqual(first, second)

        differences = cm.exception.differences
        super(DataTestCase, self).assertEqual(differences, [Missing('CCC', _0='baz')])

    def test_dict_v_dict_numeric_fail(self):
        with self.assertRaises(DataError) as cm:
            first  = {'foo': 1, 'bar': 2, 'baz': 2}
            second = {'foo': 1, 'bar': 2, 'baz': 3}
            self.assertEqual(first, second)

        differences = cm.exception.differences
        super(DataTestCase, self).assertEqual(differences, [Deviation(-1, 3, _0='baz')])

    def test_int_v_set_fail(self):
        with self.assertRaises(DataError) as cm:
            first  = 4
            second = set([4, 7])
            self.assertEqual(first, second)

        differences = cm.exception.differences
        super(DataTestCase, self).assertEqual(differences, [Missing(7)])

    def test_str_v_set_fail(self):
        with self.assertRaises(DataError) as cm:
            first  = 'foo'
            second = set(['foo', 'bar'])
            self.assertEqual(first, second)

        differences = cm.exception.differences
        super(DataTestCase, self).assertEqual(differences, [Missing('bar')])


class TestNormalizeReference(datatest.DataTestCase):
    def setUp(self):
        self.reference = MinimalSource([
            ('label1', 'value'),
            ('a', '65'),
            ('b', '70'),
        ])

        self.subject = MinimalSource([
            ('label1', 'label2', 'value'),
            ('a', 'x', '17'),
            ('a', 'x', '13'),
            ('a', 'y', '20'),
            ('a', 'z', '15'),
            ('b', 'z',  '5'),
            ('b', 'y', '40'),
            ('b', 'x', '25'),
        ])

    def test_normalize_set(self):
        original = set(['x', 'y', 'z'])
        normalized = self._normalize_required(original, 'distinct', 'label2')
        self.assertIs(original, normalized)  # Should return original unchanged.

    def test_alternate_reference_source(self):
        altsrc = MinimalSource([
            ('label1', 'value'),
            ('c', '75'),
            ('d', '80'),
        ])
        normalized = self._normalize_required(altsrc, 'distinct', 'label1')
        self.assertEqual(set(['c', 'd']), normalized)


class TestAssertSubjectColumns(datatest.DataTestCase):
    def setUp(self):
        data = [('label1', 'value'),
                ('a', '6'),
                ('b', '7')]
        self.subject = MinimalSource(data)

    def test_required_set(self):
        required_set = set(['label1', 'value'])
        self.assertSubjectColumns(required=required_set)  # <- test assert

    def test_required_source(self):
        data = [('label1', 'value'),
                ('a', '6'),
                ('b', '7')]
        required_source = MinimalSource(data)
        self.assertSubjectColumns(required=required_source)  # <- test assert

    def test_required_function(self):
        def lowercase(x):  # <- Helper function!!!
            return x == x.lower()
        self.assertSubjectColumns(required=lowercase)  # <- test assert

    def test_using_reference(self):
        data = [('label1', 'value'),
                ('a', '6'),
                ('b', '7')]
        self.subject = MinimalSource(data)
        self.reference = MinimalSource(data)
        self.assertSubjectColumns()  # <- test assert

    def test_extra(self):
        data = [('label1', 'label2', 'value'),
                ('a', 'x', '6'),
                ('b', 'y', '7')]
        self.subject = MinimalSource(data)

        with self.assertRaises(DataError) as cm:
            required_set = set(['label1', 'value'])
            self.assertSubjectColumns(required=required_set)  # <- test assert

        differences = cm.exception.differences
        self.assertEqual(set(differences), set([Extra('label2')]))

    def test_missing(self):
        data = [('label1',),
                ('a',),
                ('b',)]
        self.subject = MinimalSource(data)

        with self.assertRaises(DataError) as cm:
            required_set = set(['label1', 'value'])
            self.assertSubjectColumns(required=required_set)  # <- test assert

        differences = cm.exception.differences
        self.assertEqual(set(differences), set([Missing('value')]))

    def test_invalid(self):
        data = [('LABEL1', 'value'),
                ('a', '6'),
                ('b', '7')]
        self.subject = MinimalSource(data)

        with self.assertRaises(DataError) as cm:
            def lowercase(x):  # <- Helper function!!!
                return x == x.lower()
            self.assertSubjectColumns(required=lowercase)  # <- test assert

        differences = cm.exception.differences
        self.assertEqual(set(differences), set([Invalid('LABEL1')]))


class TestNoDefaultSubject(datatest.DataTestCase):
    def test_no_subject(self):
        required = CompareSet([1,2,3])
        with self.assertRaisesRegex(NameError, "cannot find 'subject'"):
            self.assertSubjectSet(required)


class TestAssertSubjectSet(datatest.DataTestCase):
    def setUp(self):
        data = [('label1', 'label2'),
                ('a', 'x'),
                ('b', 'y'),
                ('c', 'z')]
        self.subject = MinimalSource(data)

    def test_collections(self):
        # Should all pass without error.
        required = set(['a', 'b', 'c'])
        self.assertSubjectSet('label1', required)  # <- test set

        required = ['a', 'b', 'c']
        self.assertSubjectSet('label1', required)  # <- test list

        required = iter(['a', 'b', 'c'])
        self.assertSubjectSet('label1', required)  # <- test iterator

        required = (x for x in ['a', 'b', 'c'])
        self.assertSubjectSet('label1', required)  # <- test generator

    def test_callable(self):
        # Should pass without error.
        required = lambda x: x in ['a', 'b', 'c']
        self.assertSubjectSet('label1', required)  # <- test callable

        # Multiple args. Should pass without error
        required = lambda x, y: x in ['a', 'b', 'c'] and y in ['x', 'y', 'z']
        self.assertSubjectSet(['label1', 'label2'], required)  # <- test callable

    def test_same(self):
        self.reference = self.subject
        self.assertSubjectSet('label1')  # <- test implicit reference

    def test_same_using_reference_from_argument(self):
        required = set(['a', 'b', 'c'])
        self.assertSubjectSet('label1', required)  # <- test using arg

    def test_same_group_using_reference_from_argument(self):
        required = set([('a', 'x'), ('b', 'y'), ('c', 'z')])
        self.assertSubjectSet(['label1', 'label2'], required)  # <- test using arg

    def test_missing(self):
        ref = [
            ('label1', 'label2'),
            ('a', 'x'),
            ('b', 'y'),
            ('c', 'z'),
            ('d', '#'),  # <- Reference has one additional item.
        ]
        self.reference = MinimalSource(ref)

        with self.assertRaises(DataError) as cm:
            self.assertSubjectSet('label1')

        differences = cm.exception.differences
        self.assertEqual(differences, [Missing('d')])

    def test_extra(self):
        ref = [
            ('label1', 'label2'),
            ('a', 'x'),
            ('b', 'y'),
            #('c', 'z'), <- Intentionally omitted.
        ]
        self.reference = MinimalSource(ref)

        with self.assertRaises(DataError) as cm:
            self.assertSubjectSet('label1')

        differences = cm.exception.differences
        self.assertEqual(differences, [Extra('c')])

    def test_invalid(self):
        with self.assertRaises(DataError) as cm:
            required = lambda x: x in ('a', 'b')
            self.assertSubjectSet('label1', required)

        differences = cm.exception.differences
        self.assertEqual(differences, [Invalid('c')])

    def test_same_group(self):
        self.reference = self.subject
        self.assertSubjectSet(['label1', 'label2'])

    def test_missing_group(self):
        ref = [
            ('label1', 'label2'),
            ('a', 'x'),
            ('b', 'y'),
            ('c', 'z'),
            ('d', '#'),  # <- Reference has one additional item.
        ]
        self.reference = MinimalSource(ref)

        with self.assertRaises(DataError) as cm:
            self.assertSubjectSet(['label1', 'label2'])

        differences = cm.exception.differences
        super(DataTestCase, self).assertEqual(differences, [Missing(('d', '#'))])


class TestSubjectSum(datatest.DataTestCase):
    def setUp(self):
        self.src1_totals = MinimalSource([
            ('label1', 'value'),
            ('a', '65'),
            ('b', '70'),
        ])

        self.src1_records = MinimalSource([
            ('label1', 'label2', 'value'),
            ('a', 'x', '17'),
            ('a', 'x', '13'),
            ('a', 'y', '20'),
            ('a', 'z', '15'),
            ('b', 'z',  '5'),
            ('b', 'y', '40'),
            ('b', 'x', '25'),
        ])

        self.src2_records = MinimalSource([
            ('label1', 'label2', 'value'),
            ('a', 'x', '18'),  # <- off by +1 (compared to src1)
            ('a', 'x', '13'),
            ('a', 'y', '20'),
            ('a', 'z', '15'),
            ('b', 'z',  '4'),  # <- off by -1 (compared to src1)
            ('b', 'y', '40'),
            ('b', 'x', '25'),
        ])

    def test_passing_explicit_dict(self):
        self.subject = self.src1_records

        required = {'a': 65, 'b': 70}
        self.assertSubjectSum('value', ['label1'], required)

    def test_passing_explicit_callable(self):
        self.subject = self.src1_records

        required = lambda x: x in (65, 70)
        self.assertSubjectSum('value', ['label1'], required)

    def test_passing_implicit_reference(self):
        self.subject = self.src1_records
        self.reference = self.src1_totals

        self.assertSubjectSum('value', ['label1'])

    def test_failing_explicit_dict(self):
        self.subject = self.src2_records  # <- src1 != src2

        with self.assertRaises(DataError) as cm:
            required = {'a': 65, 'b': 70}
            self.assertSubjectSum('value', ['label1'], required)

        differences = cm.exception.differences
        expected = [Deviation(+1, 65, label1='a'),
                    Deviation(-1, 70, label1='b')]
        super(DataTestCase, self).assertEqual(set(differences), set(expected))

    def test_failing_explicit_callable(self):
        self.subject = self.src2_records

        with self.assertRaises(DataError) as cm:
            required = lambda x: x in (65, 70)
            self.assertSubjectSum('value', ['label1'], required)

        differences = cm.exception.differences
        expected = [Invalid(Decimal(66), label1='a'),
                    Invalid(Decimal(69), label1='b')]
        #expected = [Invalid(66, label1='a'),
        #            Invalid(69, label1='b')]
        super(DataTestCase, self).assertEqual(set(differences), set(expected))

    def test_failing_implicit_reference(self):
        self.subject = self.src2_records  # <- src1 != src2
        self.reference = self.src1_totals

        with self.assertRaises(DataError) as cm:
            self.assertSubjectSum('value', ['label1'])

        differences = cm.exception.differences
        expected = [Deviation(+1, 65, label1='a'),
                    Deviation(-1, 70, label1='b')]
        super(DataTestCase, self).assertEqual(set(differences), set(expected))


class TestAssertSubjectSumGroupsAndFilters(datatest.DataTestCase):
    def setUp(self):
        self.subject = MinimalSource([
            ('label1', 'label2', 'label3', 'value'),
            ('a', 'x', 'foo', '18'),
            ('a', 'x', 'bar', '13'),
            ('a', 'y', 'foo', '11'),
            ('a', 'y', 'bar', '10'),
            ('a', 'z', 'foo',  '5'),
            ('a', 'z', 'bar', '10'),
            ('b', 'z', 'baz',  '4'),
            ('b', 'y', 'bar', '39'),
            ('b', 'x', 'foo', '25'),
        ])

        self.reference = MinimalSource([
            ('label1', 'label2', 'value'),
            ('a', 'x', '18'),
            ('a', 'x', '13'),
            ('a', 'y', '20'),
            ('a', 'z', '15'),
            ('b', 'z',  '4'),
            ('b', 'y', '40'),
            ('b', 'x', '25'),
        ])

    def test_group_and_filter(self):
        """Only groupby fields should appear in diff errors
        (kwds-filters should be omitted).
        """
        with self.assertRaises(DataError) as cm:
            self.assertSubjectSum('value', ['label1'], label2='y')

        differences = cm.exception.differences
        expected = [Deviation(+1, 20, label1='a'),
                    Deviation(-1, 40, label1='b')]
        super(DataTestCase, self).assertEqual(set(differences), set(expected))


class TestAssertSubjectRegexAndNotDataRegex(datatest.DataTestCase):
    def setUp(self):
        self.subject = MinimalSource([
            ('label1', 'label2'),
            ('0aaa', '001'),
            ('b9bb',   '2'),
            (' ccc', '003'),
        ])

    def test_regex_passing(self):
        self.assertSubjectRegex('label1', '\w\w')  # Should pass without error.

    def test_regex_failing(self):
        with self.assertRaises(DataError) as cm:
            self.assertSubjectRegex('label2', '\d\d\d')

        differences = cm.exception.differences
        super(DataTestCase, self).assertEqual(differences, [Invalid('2')])

    def test_regex_precompiled(self):
        regex = re.compile('[ABC]$', re.IGNORECASE)
        self.assertSubjectRegex('label1', regex)

    def test_not_regex_passing(self):
        self.assertSubjectNotRegex('label1', '\d\d\d')

    def test_not_regex_failing(self):
        with self.assertRaises(DataError) as cm:
            self.assertSubjectNotRegex('label2', '^\d{1,2}$')

        differences = cm.exception.differences
        super(DataTestCase, self).assertEqual(differences, [Invalid('2')])

    def test_not_regex_precompiled(self):
        regex = re.compile('^[ABC]')  # <- pre-compiled
        self.assertSubjectNotRegex('label1', regex)


class TestAssertSubjectUnique(datatest.DataTestCase):
    def setUp(self):
        self.subject = MinimalSource([
            ('label1', 'label2'),
            ('a', 'x'),
            ('b', 'y'),
            ('c', 'z'),
            ('d', 'z'),
            ('e', 'z'),
            ('f', 'z'),
        ])

    def test_single_column(self):
        self.assertSubjectUnique('label1')

    def test_multiple_columns(self):
        self.assertSubjectUnique(['label1', 'label2'])

    def test_duplicates(self):
        with self.assertRaises(DataError) as cm:
            self.assertSubjectUnique('label2')

        differences = cm.exception.differences
        super(DataTestCase, self).assertEqual(differences, [Extra('z')])


########################################################################
# Test allowances from datatest.allow sub-package.
########################################################################
class TestAllowIter(unittest.TestCase):
    def test_function_all_bad(self):
        function = lambda iterable: iterable  # <- Rejects everything.
        in_diffs = [
            Extra('foo'),
            Extra('bar'),
        ]
        with self.assertRaises(DataError) as cm:
            with allow_iter(function, 'example allowance'):
                raise DataError('example error', in_diffs)

        rejected = cm.exception.differences
        self.assertEqual(rejected, in_diffs)

    def test_function_all_ok(self):
        function = lambda iterable: list()  # <- Accepts everything.

        with allow_iter(function, 'example allowance'):
            raise DataError('example error', [Missing('foo'), Missing('bar')])

    def test_function_some_ok(self):
        function = lambda iterable: (x for x in iterable if x.value != 'bar')
        in_diffs = [
            Missing('foo'),
            Missing('bar'),
        ]
        with self.assertRaises(DataError) as cm:
            with allow_iter(function, 'example allowance'):
                raise DataError('example error', in_diffs)

        rejected = list(cm.exception.differences)
        self.assertEqual(rejected, [Missing('foo')])

    def test_kwds_all_bad(self):
        function = lambda iterable: list()  # <- Accepts everything.
        in_diffs = [
            Missing('foo', aaa='x', bbb='y'),
            Missing('bar', aaa='x', bbb='z'),
        ]
        with self.assertRaises(DataError) as cm:
            # Using keyword bbb='j' should reject all in_diffs.
            with allow_iter(function, 'example allowance', bbb='j'):
                raise DataError('example error', in_diffs)

        rejected = list(cm.exception.differences)
        self.assertEqual(rejected, in_diffs)

    def test_kwds_all_ok(self):
        function = lambda iterable: list()  # <- Accepts everything.
        in_diffs = [
            Missing('foo', aaa='x', bbb='y'),
            Missing('bar', aaa='x', bbb='z'),
        ]
        # Using keyword aaa='x' should accept all in_diffs.
        with allow_iter(function, 'example allowance', aaa='x'):
            raise DataError('example error', in_diffs)

        # Using keyword bbb=['y', 'z'] should also accept all in_diffs.
        with allow_iter(function, 'example allowance', bbb=['y', 'z']):
            raise DataError('example error', in_diffs)

    def test_kwds_some_ok(self):
        function = lambda iterable: list()  # <- Accepts everything.
        in_diffs = [
            Missing('foo', aaa='x', bbb='y'),
            Missing('bar', aaa='x', bbb='z'),
        ]
        with self.assertRaises(DataError) as cm:
            # Keyword bbb='y' should reject second in_diffs element.
            with allow_iter(function, 'example allowance', bbb='y'):
                raise DataError('example error', in_diffs)

        rejected = list(cm.exception.differences)
        self.assertEqual(rejected, [Missing('bar', aaa='x', bbb='z')])

    def test_no_exception(self):
        function = lambda iterable: list()  # <- Accepts everything.

        with self.assertRaises(AssertionError) as cm:
            with allow_iter(function):
                pass  # No exceptions raised

        exc = cm.exception
        self.assertEqual('No differences found: <lambda>', str(exc))


class TestAllowOnly(unittest.TestCase):
    """Test allow_only() behavior."""
    def test_allow_some(self):
        with self.assertRaises(DataError) as cm:
            with allow_only(Extra('xxx'), 'example allowance'):
                raise DataError('example error', [Extra('xxx'), Missing('yyy')])

        result_str = str(cm.exception)
        self.assertEqual("example allowance: example error:\n Missing('yyy')", result_str)

        result_diffs = list(cm.exception.differences)
        self.assertEqual([Missing('yyy')], result_diffs)

    def test_not_found(self):
        with self.assertRaises(DataError) as cm:
            with allow_only([Extra('xxx'), Missing('yyy')]):
                raise DataError('example error', [Extra('xxx')])

        result_str = str(cm.exception)
        self.assertTrue(result_str.startswith('Allowed difference not found'))

        result_diffs = list(cm.exception.differences)
        self.assertEqual([Missing('yyy')], result_diffs)

    def test_allow_all(self):
        differences = [Missing('xxx'), Extra('yyy')]
        with allow_only(differences):
            raise DataError('example error', [Missing('xxx'), Extra('yyy')])

        # Order of differences should not matter!
        differences = [Extra('yyy'), Missing('xxx')]
        with allow_only(differences):
            raise DataError('example error', reversed(differences))

    def test_allow_one_but_find_duplicate(self):
        with self.assertRaises(DataError) as cm:
            with allow_only(Extra('xxx')):
                raise DataError('example error', [Extra('xxx'), Extra('xxx')])

        result_string = str(cm.exception)
        self.assertEqual("example error:\n Extra('xxx')", result_string)

    def test_allow_duplicate_but_find_only_one(self):
        with self.assertRaises(DataError) as cm:
            with allow_only([Extra('xxx'), Extra('xxx')]):
                raise DataError('example error', [Extra('xxx')])

        result_string = str(cm.exception)
        self.assertEqual("Allowed difference not found:\n Extra('xxx')", result_string)

    def test_no_exception(self):
        with self.assertRaises(AssertionError) as cm:
            with allow_only([Missing('xxx')]):
                pass  # No exceptions raised

        exc = cm.exception
        self.assertEqual('No differences found: allow_only', str(exc))

    def test_walk_list(self):
        flat_list = [Missing('val1'), Missing('val2')]
        nested_list = [[Missing('val1')], [Missing('val2')]]
        irregular_list = [[[Missing('val1')]], [Missing('val2')]]

        result = allow_only._walk_diff(flat_list)
        self.assertEqual(flat_list, list(result))

        result = allow_only._walk_diff(nested_list)
        self.assertEqual(flat_list, list(result))

        result = allow_only._walk_diff(irregular_list)
        self.assertEqual(flat_list, list(result))

    def test_walk_dict(self):
        values_set = set([
            Missing('xxx'),
            Missing('yyy'),
        ])
        flat_dict = {
            'key1': Missing('xxx'),
            'key2': Missing('yyy'),
        }
        nested_dict = {
            'key1': {
                'key2': Missing('xxx'),
            },
            'key3': {
                'key4': Missing('yyy'),
            },
        }
        irregular_dict = {
            'key1': Missing('xxx'),
            'key2': {
                'key3': {
                    'key4': Missing('yyy'),
                },
            },
        }

        result = allow_only._walk_diff(flat_dict)
        self.assertEqual(values_set, set(result))

        result = allow_only._walk_diff(nested_dict)
        self.assertEqual(values_set, set(result))

        result = allow_only._walk_diff(irregular_dict)
        self.assertEqual(values_set, set(result))

    def test_walk_single_element(self):
        result = allow_only._walk_diff(Missing('xxx'))  # <- Not wrapped in container.
        self.assertEqual([Missing('xxx')], list(result))

    def test_walk_mixed_types(self):
        values_set = set([
            Missing('alpha'),
            Missing('bravo'),
            Missing('charlie'),
            Missing('delta'),
        ])
        irregular_collection = {
            'key1': Missing('alpha'),
            'key2': [
                Missing('bravo'),
                [
                    Missing('charlie'),
                    Missing('delta'),
                ],
            ],
        }
        result = allow_only._walk_diff(irregular_collection)
        self.assertEqual(values_set, set(result))

    def test_walk_nondiff_items(self):
        flat_list = ['xxx', 'yyy']
        with self.assertRaises(TypeError):
            list(allow_only._walk_diff(flat_list))

        flat_dict = {'key1': 'xxx', 'key2': 'yyy'}
        with self.assertRaises(TypeError):
            list(allow_only._walk_diff(flat_dict))

        nested_list = [Missing('xxx'), ['yyy']]
        with self.assertRaises(TypeError):
            list(allow_only._walk_diff(nested_list))

        irregular_collection = {
            'key1': Missing('xxx'),
            'key2': [
                Missing('yyy'),
                [
                    Missing('zzz'),
                    'qux',
                ],
            ],
        }
        with self.assertRaises(TypeError):
            list(allow_only._walk_diff(irregular_collection))


class TestAllowLimit(unittest.TestCase):
    """Test allow_limit() behavior."""
    def test_allow_some(self):
        differences = [Extra('xxx'), Missing('yyy')]

        with self.assertRaises(DataError) as cm:
            with allow_limit(1):  # <- Allows only 1 but there are 2!
                raise DataError('example error', differences)

        rejected = list(cm.exception.differences)
        self.assertEqual(differences, rejected)

    def test_allow_all(self):
        with allow_limit(2):  # <- Allows 2 and there are only 2.
            raise DataError('example error', [Missing('xxx'), Missing('yyy')])

        with allow_limit(3):  # <- Allows 3 and there are only 2.
            raise DataError('example error', [Missing('xxx'), Missing('yyy')])

    def test_kwds(self):
        diff_set = set([
            Missing('xxx', aaa='foo'),
            Missing('yyy', aaa='bar'),
            Extra('zzz', aaa='foo'),
        ])

        with self.assertRaises(DataError) as cm:
            # Allows 2 with aaa='foo' and there are two (only aaa='bar' is rejected).
            with allow_limit(2, 'example allowance', aaa='foo'):
                raise DataError('example error', diff_set)
        rejected = set(cm.exception.differences)
        self.assertEqual(rejected, set([Missing('yyy', aaa='bar')]))

        with self.assertRaises(DataError) as cm:
            # Allows 1 with aaa='foo' but there are 2 (all are rejected)!
            with allow_limit(1, 'example allowance', aaa='foo'):
                raise DataError('example error', diff_set)
        rejected = set(cm.exception.differences)
        self.assertEqual(rejected, diff_set)

    def test_no_exception(self):
        with self.assertRaises(AssertionError) as cm:
            with allow_limit(2):
                pass  # No exceptions raised

        exc = cm.exception
        self.assertEqual('No differences found: expected at most 2 matching differences', str(exc))


class TestAllowExtra(unittest.TestCase):
    """Test allow_extra() behavior."""
    def test_allow_some(self):
        differences = [Extra('xxx'), Missing('yyy')]

        with self.assertRaises(DataError) as cm:
            with allow_extra():
                raise DataError('example error', differences)

        rejected = list(cm.exception.differences)
        self.assertEqual(rejected, [Missing('yyy')])

    def test_allow_all(self):
        with allow_extra():
            raise DataError('example error', [Extra('xxx'), Extra('yyy')])

    def test_kwds(self):
        in_diffs = [
            Extra('xxx', aaa='foo'),
            Extra('yyy', aaa='bar'),
            Missing('zzz', aaa='foo'),
        ]
        with self.assertRaises(DataError) as cm:
            with allow_extra('example allowance', aaa='foo'):
                raise DataError('example error', in_diffs)

        rejected = list(cm.exception.differences)
        self.assertEqual(rejected, [Extra('yyy', aaa='bar'), Missing('zzz', aaa='foo')])

    def test_no_exception(self):
        with self.assertRaises(AssertionError) as cm:
            with allow_extra():
                pass  # No exceptions raised

        exc = cm.exception
        self.assertEqual('No differences found: allow_extra', str(exc))


class TestAllowMissing(unittest.TestCase):
    """Test allow_missing() behavior."""
    def test_allow_some(self):
        differences = [Extra('xxx'), Missing('yyy')]

        with self.assertRaises(DataError) as cm:
            with allow_missing():
                raise DataError('example error', differences)

        rejected = list(cm.exception.differences)
        self.assertEqual(rejected, [Extra('xxx')])

    def test_allow_all(self):
        with allow_missing():
            raise DataError('example error', [Missing('xxx'), Missing('yyy')])

    def test_kwds(self):
        in_diffs = [
            Missing('xxx', aaa='foo'),
            Missing('yyy', aaa='bar'),
            Extra('zzz', aaa='foo'),
        ]
        with self.assertRaises(DataError) as cm:
            with allow_missing('example allowance', aaa='foo'):
                raise DataError('example error', in_diffs)

        rejected = list(cm.exception.differences)
        self.assertEqual(rejected, [Missing('yyy', aaa='bar'), Extra('zzz', aaa='foo')])

    def test_no_exception(self):
        with self.assertRaises(AssertionError) as cm:
            with allow_missing():
                pass  # No exceptions raised

        exc = cm.exception
        self.assertEqual('No differences found: allow_missing', str(exc))


class TestAllowDeviation(unittest.TestCase):
    """Test allow_deviation() behavior."""
    def test_tolerance_syntax(self):
        differences = [
            Deviation(-1, 10, label='aaa'),
            Deviation(+3, 10, label='bbb'),  # <- Not in allowed range.
        ]
        with self.assertRaises(DataError) as cm:
            with allow_deviation(2, 'example allowance'):  # <- Allows +/- 2.
                raise DataError('example error', differences)

        result_string = str(cm.exception)
        self.assertTrue(result_string.startswith('example allowance: example error'))

        result_diffs = list(cm.exception.differences)
        self.assertEqual([Deviation(+3, 10, label='bbb')], result_diffs)

    def test_lowerupper_syntax(self):
        differences = [
            Deviation(-1, 10, label='aaa'),  # <- Not in allowed range.
            Deviation(+3, 10, label='bbb'),
        ]
        with self.assertRaises(DataError) as cm:
            with allow_deviation(0, 3, 'example allowance'):  # <- Allows from 0 to 3.
                raise DataError('example error', differences)

        result_string = str(cm.exception)
        self.assertTrue(result_string.startswith('example allowance: example error'))

        result_diffs = list(cm.exception.differences)
        self.assertEqual([Deviation(-1, 10, label='aaa')], result_diffs)

    def test_single_value_allowance(self):
        differences = [
            Deviation(+2.9, 10, label='aaa'),  # <- Not allowed.
            Deviation(+3.0, 10, label='bbb'),
            Deviation(+3.0, 5, label='ccc'),
            Deviation(+3.1, 10, label='ddd'),  # <- Not allowed.
        ]
        with self.assertRaises(DataError) as cm:
            with allow_deviation(3, 3):  # <- Allows +3 only.
                raise DataError('example error', differences)

        result_diffs = set(cm.exception.differences)
        expected_diffs = set([
            Deviation(+2.9, 10, label='aaa'),
            Deviation(+3.1, 10, label='ddd'),
        ])
        self.assertEqual(expected_diffs, result_diffs)

    def test_kwds_handling(self):
        differences = [
            Deviation(-1, 10, label='aaa'),
            Deviation(+2, 10, label='aaa'),
            Deviation(+2, 10, label='bbb'),
            Deviation(+3, 10, label='aaa'),
        ]
        with self.assertRaises(DataError) as cm:
            with allow_deviation(2, 'example allowance', label='aaa'):  # <- Allows +/- 2.
                raise DataError('example error', differences)

        result_set = set(cm.exception.differences)
        expected_set = set([
            Deviation(+2, 10, label='bbb'),  # <- Keyword value not 'aaa'.
            Deviation(+3, 10, label='aaa'),  # <- Not in allowed range.
        ])
        self.assertEqual(expected_set, result_set)

    def test_invalid_tolerance(self):
        with self.assertRaises(AssertionError) as cm:
            with allow_deviation(-5):  # <- invalid
                pass
        exc = str(cm.exception)
        self.assertTrue(exc.startswith('tolerance should not be negative'))

    def test_empty_value_handling(self):
        # Test NoneType.
        with allow_deviation(0):  # <- Pass without failure.
            raise DataError('example error', [Deviation(None, 0)])

        with allow_deviation(0):  # <- Pass without failure.
            raise DataError('example error', [Deviation(0, None)])

        # Test empty string.
        with allow_deviation(0):  # <- Pass without failure.
            raise DataError('example error', [Deviation('', 0)])

        with allow_deviation(0):  # <- Pass without failure.
            raise DataError('example error', [Deviation(0, '')])

        # Test NaN (not a number) values.
        with self.assertRaises(DataError):  # <- NaN values should not be caught!
            with allow_deviation(0):
                raise DataError('example error', [Deviation(float('nan'), 0)])

        with self.assertRaises(DataError):  # <- NaN values should not be caught!
            with allow_deviation(0):
                raise DataError('example error', [Deviation(0, float('nan'))])


class TestAllowPercentDeviation(unittest.TestCase):
    """Test allow_percent_deviation() behavior."""
    def test_tolerance_syntax(self):
        differences = [
            Deviation(-1, 10, label='aaa'),
            Deviation(+3, 10, label='bbb'),  # <- Not in allowed range.
        ]
        with self.assertRaises(DataError) as cm:
            with allow_percent_deviation(0.2, 'example allowance'):  # <- Allows +/- 20%.
                raise DataError('example error', differences)

        result_string = str(cm.exception)
        self.assertTrue(result_string.startswith('example allowance: example error'))

        result_diffs = list(cm.exception.differences)
        self.assertEqual([Deviation(+3, 10, label='bbb')], result_diffs)

    def test_lowerupper_syntax(self):
        differences = [
            Deviation(-1, 10, label='aaa'),  # <- Not in allowed range.
            Deviation(+3, 10, label='bbb'),
        ]
        with self.assertRaises(DataError) as cm:
            with allow_percent_deviation(0.0, 0.3, 'example allowance'):  # <- Allows from 0 to 30%.
                raise DataError('example error', differences)

        result_string = str(cm.exception)
        self.assertTrue(result_string.startswith('example allowance: example error'))

        result_diffs = list(cm.exception.differences)
        self.assertEqual([Deviation(-1, 10, label='aaa')], result_diffs)

    def test_single_value_allowance(self):
        differences = [
            Deviation(+2.9, 10, label='aaa'),  # <- Not allowed.
            Deviation(+3.0, 10, label='bbb'),
            Deviation(+6.0, 20, label='ccc'),
            Deviation(+3.1, 10, label='ddd'),  # <- Not allowed.
        ]
        with self.assertRaises(DataError) as cm:
            with allow_percent_deviation(0.3, 0.3):  # <- Allows +30% only.
                raise DataError('example error', differences)

        result_diffs = set(cm.exception.differences)
        expected_diffs = set([
            Deviation(+2.9, 10, label='aaa'),
            Deviation(+3.1, 10, label='ddd'),
        ])
        self.assertEqual(expected_diffs, result_diffs)

    def test_kwds_handling(self):
        differences = [
            Deviation(-1, 10, label='aaa'),
            Deviation(+2, 10, label='aaa'),
            Deviation(+2, 10, label='bbb'),
            Deviation(+3, 10, label='aaa'),
        ]
        with self.assertRaises(DataError) as cm:
            with allow_percent_deviation(0.2, 'example allowance', label='aaa'):  # <- Allows +/- 20%.
                raise DataError('example error', differences)

        result_set = set(cm.exception.differences)
        expected_set = set([
            Deviation(+2, 10, label='bbb'),  # <- Keyword value not 'aaa'.
            Deviation(+3, 10, label='aaa'),  # <- Not in allowed range.
        ])
        self.assertEqual(expected_set, result_set)

    def test_invalid_tolerance(self):
        with self.assertRaises(AssertionError) as cm:
            with allow_percent_deviation(-0.5):  # <- invalid
                pass
        exc = str(cm.exception)
        self.assertTrue(exc.startswith('tolerance should not be negative'))

    def test_empty_value_handling(self):
        # Test NoneType.
        with allow_percent_deviation(0):  # <- Pass without failure.
            raise DataError('example error', [Deviation(None, 0)])

        with allow_percent_deviation(0):  # <- Pass without failure.
            raise DataError('example error', [Deviation(0, None)])

        # Test empty string.
        with allow_percent_deviation(0):  # <- Pass without failure.
            raise DataError('example error', [Deviation('', 0)])

        with allow_percent_deviation(0):  # <- Pass without failure.
            raise DataError('example error', [Deviation(0, '')])

        # Test NaN (not a number) values.
        with self.assertRaises(DataError):  # <- NaN values should not be caught!
            with allow_percent_deviation(0):
                raise DataError('example error', [Deviation(float('nan'), 0)])

        with self.assertRaises(DataError):  # <- NaN values should not be caught!
            with allow_percent_deviation(0):
                raise DataError('example error', [Deviation(0, float('nan'))])


class TestAllowAny(unittest.TestCase):
    """Test allow_any() behavior."""
    def test_kwds(self):
        in_diffs = [
            Extra('xxx', aaa='foo'),
            Extra('yyy', aaa='bar'),
            Missing('zzz', aaa='foo'),
        ]
        with self.assertRaises(DataError) as cm:
            with allow_any('example allowance', aaa='foo'):
                raise DataError('example error', in_diffs)

        rejected = list(cm.exception.differences)
        self.assertEqual(rejected, [Extra('yyy', aaa='bar')])

    def test_no_kwds(self):
        in_diffs = [
            Extra('xxx', aaa='foo'),
            Extra('yyy', aaa='bar'),
        ]
        with self.assertRaises(TypeError) as cm:
            with allow_any('example allowance'):  # <- Missing keyword argument!
                raise DataError('example error', in_diffs)

        result = cm.exception
        expected = 'requires 1 or more keyword arguments (0 given)'
        self.assertEqual(expected, str(result))

    def test_no_exception(self):
        with self.assertRaises(AssertionError) as cm:
            with allow_any(foo='bar'):
                pass  # No exceptions raised

        exc = cm.exception
        self.assertEqual('No differences found: allow_any', str(exc))


class TestAllowEach(unittest.TestCase):
    """Using allow_each() requires an element-wise function."""
    def test_allow_some(self):
        function = lambda x: x.value == 'bar'
        in_diffs = [
            Missing('foo'),
            Missing('bar'),
        ]
        with self.assertRaises(DataError) as cm:
            with allow_each(function, 'example allowance'):
                raise DataError('example error', in_diffs)

        rejected = list(cm.exception.differences)
        self.assertEqual(rejected, [Missing('foo')])

    def test_allow_all(self):
        function = lambda x: isinstance(x, Missing)  # <- Allow only missing.

        with allow_each(function, 'example allowance'):
            raise DataError('example error', [Missing('xxx'), Missing('yyy')])

    def test_kwds(self):
        function = lambda x: True  # <- Accepts everything.
        in_diffs = [
            Missing('foo', aaa='x', bbb='y'),
            Missing('bar', aaa='x', bbb='z'),
        ]
        with self.assertRaises(DataError) as cm:
            # Keyword bbb='y' should reject second in_diffs element.
            with allow_each(function, 'example allowance', bbb='y'):
                raise DataError('example error', in_diffs)

        rejected = list(cm.exception.differences)
        self.assertEqual(rejected, [Missing('bar', aaa='x', bbb='z')])

    def test_no_exception(self):
        function = lambda x: False  # <- Rejects everything.

        with self.assertRaises(AssertionError) as cm:
            with allow_each(function):
                pass  # No exceptions raised

        exc = cm.exception
        self.assertEqual('No differences found: <lambda>', str(exc))


class TestNestedAllowances(unittest.TestCase):
    def test_nested_allowances(self):
        """A quick integration test to make sure allowances nest as
        required.
        """
        with allow_only(Deviation(-4,  70, label1='b')):  # <- specified diff only
            with allow_deviation(3):                      # <- tolerance of +/- 3
                with allow_percent_deviation(0.02):       # <- tolerance of +/- 2%
                    differences = [
                        Deviation(+3,  65, label1='a'),
                        Deviation(-4,  70, label1='b'),
                        Deviation(+5, 250, label1='c'),
                    ]
                    raise DataError('example error', differences)


if __name__ == '__main__':
    unittest.main()
else:
    raise Exception('This test must be run directly or as a subprocess.')
