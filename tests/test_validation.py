"""Tests for validation and comparison functions."""
import textwrap
from . import _unittest as unittest
from datatest._compatibility.collections.abc import Iterator

from datatest.difference import BaseDifference
from datatest.difference import Extra
from datatest.difference import Missing
from datatest.difference import Invalid
from datatest.difference import Deviation
from datatest._query.query import DictItems
from datatest._query.query import Result
from datatest._required import group_requirement

from datatest.validation import _normalize_data
from datatest.validation import _normalize_requirement
from datatest.validation import ValidationError
from datatest.validation import _get_group_requirement
from datatest.validation import _data_vs_requirement
from datatest.validation import _datadict_vs_requirement
from datatest.validation import _datadict_vs_requirementdict
from datatest.validation import validate
from datatest.validation import valid

try:
    import pandas
except ImportError:
    pandas = None

try:
    import numpy
except ImportError:
    numpy = None


class TestNormalizeData(unittest.TestCase):
    def test_unchanged(self):
        data = [1, 2, 3]
        self.assertIs(_normalize_data(data), data, 'should return original object')

        data = iter([1, 2, 3])
        self.assertIs(_normalize_data(data), data, 'should return original object')

        data = Result(iter([1, 2, 3]), evaluation_type=tuple)
        self.assertIs(_normalize_data(data), data, 'should return original object')

    @unittest.skipIf(not pandas, 'pandas not found')
    def test_normalize_pandas_dataframe(self):
        df = pandas.DataFrame([(1, 'a'), (2, 'b'), (3, 'c')])
        result = _normalize_data(df)
        self.assertIsInstance(result, DictItems)
        expected = {0: (1, 'a'), 1: (2, 'b'), 2: (3, 'c')}
        self.assertEqual(dict(result), expected)

        # Single column.
        df = pandas.DataFrame([('x',), ('y',), ('z',)])
        result = _normalize_data(df)
        self.assertIsInstance(result, DictItems)
        expected = {0: 'x', 1: 'y', 2: 'z'}
        self.assertEqual(dict(result), expected, 'single column should be unwrapped')

        # Multi-index.
        df = pandas.DataFrame([('x',), ('y',), ('z',)])
        df.index = pandas.MultiIndex.from_tuples([(0, 0), (0, 1), (1, 0)])
        result = _normalize_data(df)
        self.assertIsInstance(result, DictItems)
        expected = {(0, 0): 'x', (0, 1): 'y', (1, 0): 'z'}
        self.assertEqual(dict(result), expected, 'multi-index should be tuples')

        # Indexes must contain unique values, no duplicates
        df = pandas.DataFrame([('x',), ('y',), ('z',)])
        df.index = pandas.Index([0, 0, 1])  # <- Duplicate values.
        with self.assertRaises(ValueError):
            _normalize_data(df)

    @unittest.skipIf(not pandas, 'pandas not found')
    def test_normalize_pandas_series(self):
        s = pandas.Series(['x', 'y', 'z'])
        result = _normalize_data(s)
        self.assertIsInstance(result, DictItems)
        expected = {0: 'x', 1: 'y', 2: 'z'}
        self.assertEqual(dict(result), expected)

        # Multi-index.
        s = pandas.Series(['x', 'y', 'z'])
        s.index = pandas.MultiIndex.from_tuples([(0, 0), (0, 1), (1, 0)])
        result = _normalize_data(s)
        self.assertIsInstance(result, DictItems)
        expected = {(0, 0): 'x', (0, 1): 'y', (1, 0): 'z'}
        self.assertEqual(dict(result), expected, 'multi-index should be tuples')

    @unittest.skipIf(not numpy, 'numpy not found')
    def test_normalize_numpy(self):
        # Two-dimentional array.
        arr = numpy.array([['a', 'x'], ['b', 'y']])
        lazy = _normalize_data(arr)
        self.assertIsInstance(lazy, Result)
        self.assertEqual(lazy.fetch(), [('a', 'x'), ('b', 'y')])

        # Two-valued structured array.
        arr = numpy.array([('a', 1), ('b', 2)],
                          dtype=[('one', 'U10'), ('two', 'i4')])
        lazy = _normalize_data(arr)
        self.assertIsInstance(lazy, Result)
        self.assertEqual(lazy.fetch(), [('a', 1), ('b', 2)])

        # Two-valued recarray (record array).
        arr = numpy.rec.array([('a', 1), ('b', 2)],
                              dtype=[('one', 'U10'), ('two', 'i4')])
        lazy = _normalize_data(arr)
        self.assertIsInstance(lazy, Result)
        self.assertEqual(lazy.fetch(), [('a', 1), ('b', 2)])

        # One-dimentional array.
        arr = numpy.array(['x', 'y', 'z'])
        lazy = _normalize_data(arr)
        self.assertIsInstance(lazy, Result)
        self.assertEqual(lazy.fetch(), ['x', 'y', 'z'])

        # Single-valued structured array.
        arr = numpy.array([('x',), ('y',), ('z',)],
                          dtype=[('one', 'U10')])
        lazy = _normalize_data(arr)
        self.assertIsInstance(lazy, Result)
        self.assertEqual(lazy.fetch(), ['x', 'y', 'z'])

        # Single-valued recarray (record array).
        arr = numpy.rec.array([('x',), ('y',), ('z',)],
                              dtype=[('one', 'U10')])
        lazy = _normalize_data(arr)
        self.assertIsInstance(lazy, Result)
        self.assertEqual(lazy.fetch(), ['x', 'y', 'z'])

        # Three-dimentional array--conversion is not supported.
        arr = numpy.array([[[1, 3], ['a', 'x']], [[2, 4], ['b', 'y']]])
        result = _normalize_data(arr)
        self.assertIs(result, arr, msg='unsupported, returns unchanged')


class TestNormalizeRequirement(unittest.TestCase):
    def test_unchanged(self):
        requirement = [1, 2, 3]
        self.assertIs(_normalize_requirement(requirement), requirement,
            msg='should return original object')

    def test_bad_type(self):
        with self.assertRaises(TypeError, msg='cannot use generic iter'):
            _normalize_requirement(iter([1, 2, 3]))

    def test_result_object(self):
        result_obj = Result(iter([1, 2, 3]), evaluation_type=tuple)
        output = _normalize_requirement(result_obj)
        self.assertIsInstance(output, tuple)
        self.assertEqual(output, (1, 2, 3))

    def test_dict_items(self):
        items = DictItems(iter([(0, 'x'), (1, 'y'), (2, 'z')]))
        output = _normalize_requirement(items)
        self.assertIsInstance(output, dict)
        self.assertEqual(output, {0: 'x', 1: 'y', 2: 'z'})


# FOR TESTING: A minimal subclass of BaseDifference.
# BaseDifference itself should not be instantiated
# directly.
class MinimalDifference(BaseDifference):
    @property
    def args(self):
        return BaseDifference.args.fget(self)


class TestValidationError(unittest.TestCase):
    def test_error_list(self):
        error_list = [MinimalDifference('A'), MinimalDifference('B')]

        err = ValidationError(error_list)
        self.assertEqual(err.differences, error_list)

    def test_error_iter(self):
        error_list = [MinimalDifference('A'), MinimalDifference('B')]
        error_iter = iter(error_list)

        err = ValidationError(error_iter)
        self.assertEqual(err.differences, error_list, 'iterable should be converted to list')

    def test_error_dict(self):
        error_dict = {'a': MinimalDifference('A'), 'b': MinimalDifference('B')}

        err = ValidationError(error_dict)
        self.assertEqual(err.differences, error_dict)

    def test_error_iteritems(self):
        error_dict = {'a': MinimalDifference('A'), 'b': MinimalDifference('B')}
        error_iteritems = getattr(error_dict, 'iteritems', error_dict.items)()

        err = ValidationError(error_iteritems)
        self.assertEqual(err.differences, error_dict)

    def test_single_diff(self):
        single_diff = MinimalDifference('A')
        err = ValidationError(single_diff)
        self.assertEqual(err.differences, [single_diff])

    def test_bad_args(self):
        with self.assertRaises(TypeError, msg='must be iterable'):
            bad_arg = object()
            ValidationError(bad_arg, 'invalid data')

    def test_str_method(self):
        # Assert basic format and trailing comma.
        err = ValidationError([MinimalDifference('A')], 'invalid data')
        expected = """
            invalid data (1 difference): [
                MinimalDifference('A'),
            ]
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(str(err), expected)

        # Assert without description.
        err = ValidationError([MinimalDifference('A')])  # <- No description!
        expected = """
            1 difference: [
                MinimalDifference('A'),
            ]
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(str(err), expected)

        # Assert "no cacheing"--objects that inhereit from some
        # Exceptions can cache their str--but ValidationError should
        # not do this.
        err._differences = [MinimalDifference('B')]
        err._description = 'changed'
        updated = textwrap.dedent("""
            changed (1 difference): [
                MinimalDifference('B'),
            ]
        """).strip()
        self.assertEqual(str(err), updated)

        # Assert dict format and trailing comma.
        err = ValidationError({'x': MinimalDifference('A'),
                               'y': MinimalDifference('B')},
                              'invalid data')
        regex = textwrap.dedent(r"""
            invalid data \(2 differences\): \{
                '[xy]': MinimalDifference\('[AB]'\),
                '[xy]': MinimalDifference\('[AB]'\),
            \}
        """).strip()
        self.assertRegex(str(err), regex)  # <- Using regex because dict order
                                           #    can not be assumed for Python
                                           #    versions 3.5 and earlier.

    def test_str_sorting(self):
        """Check that string shows differences sorted by arguments."""
        self.maxDiff = None

        # Check sorting of non-mapping container.
        err = ValidationError([MinimalDifference('Z', 'Z'),
                               MinimalDifference('Z'),
                               MinimalDifference(1, 'C'),
                               MinimalDifference('B', 'C'),
                               MinimalDifference('A'),
                               MinimalDifference(1.5),
                               MinimalDifference(True),
                               MinimalDifference(0),
                               MinimalDifference(None)])
        expected = """
            9 differences: [
                MinimalDifference(None),
                MinimalDifference(0),
                MinimalDifference(True),
                MinimalDifference(1, 'C'),
                MinimalDifference(1.5),
                MinimalDifference('A'),
                MinimalDifference('B', 'C'),
                MinimalDifference('Z'),
                MinimalDifference('Z', 'Z'),
            ]
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(str(err), expected)

        # Make sure that all differences are being sorted (not just
        # those being displayed).
        err._should_truncate = lambda lines, chars: lines > 4
        expected = """
            9 differences: [
                MinimalDifference(None),
                MinimalDifference(0),
                MinimalDifference(True),
                MinimalDifference(1, 'C'),
                ...
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(str(err), expected)

        # Check sorting of non-mapping container.
        err = ValidationError(
            {
                ('C', 3): [MinimalDifference('Z', 3), MinimalDifference(1, 2)],
                ('A', 'C'): MinimalDifference('A'),
                'A': [MinimalDifference('C'), MinimalDifference(1)],
                2: [MinimalDifference('B'), MinimalDifference('A')],
                1: MinimalDifference('A'),
                (None, 4): MinimalDifference('A'),
            },
            'description string'
        )
        expected = """
            description string (6 differences): {
                1: MinimalDifference('A'),
                2: [MinimalDifference('A'), MinimalDifference('B')],
                'A': [MinimalDifference(1), MinimalDifference('C')],
                (None, 4): MinimalDifference('A'),
                ('A', 'C'): MinimalDifference('A'),
                ('C', 3): [MinimalDifference(1, 2), MinimalDifference('Z', 3)],
            }
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(str(err), expected)

    def test_str_truncation(self):
        # Assert optional truncation behavior.
        err = ValidationError([MinimalDifference('A'),
                               MinimalDifference('B'),
                               MinimalDifference('C'),],
                              'invalid data')
        self.assertIsNone(err._should_truncate)
        self.assertIsNone(err._truncation_notice)
        no_truncation = """
            invalid data (3 differences): [
                MinimalDifference('A'),
                MinimalDifference('B'),
                MinimalDifference('C'),
            ]
        """
        no_truncation = textwrap.dedent(no_truncation).strip()
        self.assertEqual(str(err), no_truncation)

        # Truncate without notice.
        err._should_truncate = lambda line_count, char_count: char_count > 35
        err._truncation_notice = None
        truncation_witout_notice = """
            invalid data (3 differences): [
                MinimalDifference('A'),
                ...
        """
        truncation_witout_notice = textwrap.dedent(truncation_witout_notice).strip()
        self.assertEqual(str(err), truncation_witout_notice)

        # Truncate and use truncation notice.
        err._should_truncate = lambda line_count, char_count: char_count > 35
        err._truncation_notice = 'Message truncated.'
        truncation_plus_notice = """
            invalid data (3 differences): [
                MinimalDifference('A'),
                ...

            Message truncated.
        """
        truncation_plus_notice = textwrap.dedent(truncation_plus_notice).strip()
        self.assertEqual(str(err), truncation_plus_notice)

    def test_repr(self):
        err = ValidationError([MinimalDifference('A')])  # <- No description.
        expected = "ValidationError([MinimalDifference('A')])"
        self.assertEqual(repr(err), expected)

        err = ValidationError([MinimalDifference('A')], 'description string')
        expected = "ValidationError([MinimalDifference('A')], 'description string')"
        self.assertEqual(repr(err), expected)

        # Objects that inhereit from some Exceptions can cache their
        # repr--but ValidationError should not do this.
        err._differences = [MinimalDifference('B')]
        err._description = 'changed'
        self.assertNotEqual(repr(err), expected, 'exception should not cache repr')

        updated = "ValidationError([MinimalDifference('B')], 'changed')"
        self.assertEqual(repr(err), updated)

    def test_module_property(self):
        """Module property should be 'datatest' so that testing
        frameworks display the error as 'datatest.ValidationError'.

        By default, instances would be displayed as
        'datatest.validation.ValidationError' but this awkwardly
        long and the submodule name--'validation'--is not needed
        because the class is imported into datatest's root namespace.
        """
        import datatest
        msg = "should be in datatest's root namespace"
        self.assertIs(ValidationError, datatest.ValidationError)

        msg = "should be set to 'datatest' to shorten display name"
        self.assertEqual('datatest', ValidationError.__module__)

    def test_args(self):
        err = ValidationError([MinimalDifference('A')], 'invalid data')
        self.assertEqual(err.args, ([MinimalDifference('A')], 'invalid data'))

        err = ValidationError([MinimalDifference('A')])
        self.assertEqual(err.args, ([MinimalDifference('A')], None))


class TestValidationIntegration(unittest.TestCase):
    def test_valid(self):
        a = set([1, 2, 3])
        b = set([2, 3, 4])

        self.assertTrue(valid(a, a))

        self.assertFalse(valid(a, b))

    def test_validate(self):
        a = set([1, 2, 3])
        b = set([2, 3, 4])

        self.assertIsNone(validate(a, a))

        with self.assertRaises(ValidationError):
            validate(a, b)


class TestGetGroupRequirement(unittest.TestCase):
    def test_set(self):
        requirement = _get_group_requirement(set(['foo']))
        self.assertTrue(requirement._group_requirement)

    def test_predicate(self):
        requirement = _get_group_requirement('foo')
        self.assertTrue(requirement._group_requirement)

        requirement = _get_group_requirement('bar', show_expected=True)
        self.assertTrue(requirement._group_requirement)

    def test_sequence(self):  # For base-item sequences.
        requirement = _get_group_requirement(['foo'])
        self.assertTrue(requirement._group_requirement)

    def test_already_requirement(self):
        """If the requirement is already a group requirement, then the
        original object should be returned.
        """
        requirement1 = _get_group_requirement('foo')
        requirement2 = _get_group_requirement(requirement1)
        self.assertIs(requirement1, requirement2)


class TestDataVsRequirement(unittest.TestCase):
    def test_set_against_container(self):
        requirement = set(['foo'])

        result = _data_vs_requirement(['foo', 'foo'], requirement)
        self.assertIsNone(result)

        differences, _ = _data_vs_requirement(['foo', 'bar'], requirement)
        self.assertEqual(list(differences), [Extra('bar')])

    def test_set_against_single_item(self):
        requirement = set(['foo'])
        result = _data_vs_requirement('foo', requirement)
        self.assertIsNone(result)

        requirement = set(['foo', 'bar'])
        differences, _ = _data_vs_requirement('bar', requirement)
        self.assertEqual(differences, Missing('foo'), msg='should not be in container')

        requirement = set(['foo'])
        differences, _ = _data_vs_requirement('bar', requirement)
        differences = list(differences)
        self.assertEqual(len(differences), 2, msg='expects container if multiple diffs')
        self.assertIn(Missing('foo'), differences)
        self.assertIn(Extra('bar'), differences)

    def test_predicate_against_container(self):
        requirement = 'foo'
        result = _data_vs_requirement(['foo', 'foo'], requirement)
        self.assertIsNone(result)

        requirement = 'foo'
        differences, _ = _data_vs_requirement(['foo', 'bar'], requirement)
        self.assertEqual(list(differences), [Invalid('bar')], msg='should be iterable of diffs')

        requirement = 10
        differences, _ = _data_vs_requirement([10, 12], requirement)
        self.assertEqual(list(differences), [Deviation(+2, 10)], msg='should be iterable of diffs')

        requirement = (1, 'j')
        differences, _ = _data_vs_requirement([(1, 'x'), (1, 'j')], requirement)
        self.assertEqual(list(differences), [Invalid((1, 'x'))], msg='should be iterable of diffs and no "expected"')

    def test_predicate_against_single_item(self):
        requirement = 'foo'
        result = _data_vs_requirement('foo', requirement)
        self.assertIsNone(result)

        requirement = 'foo'
        differences, _ = _data_vs_requirement('bar', requirement)
        self.assertEqual(differences, Invalid('bar', expected='foo'), msg='should have no container and include "expected"')

        requirement = 10
        differences, _ = _data_vs_requirement(12, requirement)
        self.assertEqual(differences, Deviation(+2, 10), msg='should have no container')

        requirement = (1, 'j')
        differences, _ = _data_vs_requirement((1, 'x'), requirement)
        self.assertEqual(differences, Invalid((1, 'x'), expected=(1, 'j')), msg='should have no container and include "expected"')

    def test_description_message(self):
        # Requirement returns differences and description.
        @group_requirement
        def require1(iterable):
            return [Invalid('bar')], 'some message'

        _, description = _data_vs_requirement('bar', require1)
        self.assertEqual(description, 'some message')

        # Requirement returns differences only, should get default description.
        @group_requirement
        def require2(iterable):
            return [Invalid('bar')]

        _, description = _data_vs_requirement('bar', require2)
        self.assertEqual(description, 'does not satisfy require2()')


class TestDatadictVsRequirement(unittest.TestCase):
    @staticmethod
    def evaluate_generators(dic):
        new_dic = dict()
        for k, v in dic.items():
            new_dic[k] = list(v) if isinstance(v, Iterator) else v
        return new_dic

    def test_no_differences(self):
        # Set membership.
        data = {'a': ['x', 'y'], 'b': ['x', 'y'],}
        requirement = set(['x', 'y'])
        result = _datadict_vs_requirement(data, requirement)
        self.assertIsNone(result)

        # Equality of single value.
        data = {'a': 'x', 'b': 'x'}
        requirement = 'x'
        result = _datadict_vs_requirement(data, requirement)
        self.assertIsNone(result)

    def test_set_membership(self):
        data = {'a': ['x', 'x'], 'b': ['x', 'y', 'z']}
        requirement = set(['x', 'y'])
        differences, description = _datadict_vs_requirement(data, requirement)
        differences = self.evaluate_generators(differences)
        expected = {'a': [Missing('y')], 'b': [Extra('z')]}
        self.assertEqual(differences, expected)
        self.assertEqual(description, 'does not satisfy set membership')

    def test_predicate_with_single_item_values(self):
        data = {'a': 'x', 'b': 10, 'c': 9}
        requirement = 9
        differences, description = _datadict_vs_requirement(data, requirement)
        expected = {'a': Invalid('x'), 'b': Deviation(+1, 9)}
        self.assertEqual(differences, expected)

    def test_predicate_with_lists_of_values(self):
        data = {'a': ['x', 'j'], 'b': [10, 9], 'c': [9, 9]}
        requirement = 9
        differences, description = _datadict_vs_requirement(data, requirement)
        differences = self.evaluate_generators(differences)
        expected = {'a': [Invalid('x'), Invalid('j')], 'b': [Deviation(+1, 9)]}
        self.assertEqual(differences, expected)

    def test_tuple_with_single_item_values(self):
        data = {'a': ('x', 1.0), 'b': ('y', 2), 'c': ('x', 3)}
        required = ('x', int)
        differences, description = _datadict_vs_requirement(data, required)
        expected = {'a': Invalid(('x', 1.0)), 'b': Invalid(('y', 2))}
        self.assertEqual(differences, expected)

    def test_tuple_with_lists_of_values(self):
        data = {'a': [('x', 1.0), ('x', 1)], 'b': [('y', 2), ('x', 3)]}
        required = ('x', int)
        differences, description = _datadict_vs_requirement(data, required)
        differences = self.evaluate_generators(differences)
        expected = {'a': [Invalid(('x', 1.0))], 'b': [Invalid(('y', 2))]}
        self.assertEqual(differences, expected)

    def test_description_message(self):
        data = {'a': 'bar', 'b': ['bar', 'bar']}

        # When message is the same for all items, use provided message.
        @group_requirement
        def requirement1(iterable):
            iterable = list(iterable)
            return [Invalid('bar')], 'got some items'

        _, description = _datadict_vs_requirement(data, requirement1)
        self.assertEqual(description, 'got some items')

        # When messages are different, description should be None.
        @group_requirement
        def requirement2(iterable):
            iterable = list(iterable)
            return [Invalid('bar')], 'got {0} items'.format(len(iterable))

        _, description = _datadict_vs_requirement(data, requirement2)
        self.assertIsNone(description)


class TestDatadictVsRequirementdict(unittest.TestCase):
    """Calling _apply_mapping_to_mapping() should run the appropriate
    comparison function (internally) for each value-group and
    return the results as an iterable of key-value items.
    """
    @staticmethod
    def evaluate_generators(dic):
        new_dic = dict()
        for k, v in dic.items():
            new_dic[k] = list(v) if isinstance(v, Iterator) else v
        return new_dic

    def test_no_differences(self):
        # Set membership.
        data = {'a': ['x', 'y']}
        result = _datadict_vs_requirementdict(data, {'a': set(['x', 'y'])})
        self.assertIsNone(result)

        # Equality of single values.
        data = {'a': 'x', 'b': 'y'}
        result = _datadict_vs_requirementdict(data, {'a': 'x', 'b': 'y'})
        self.assertIsNone(result)

    def test_bad_data_type(self):
        not_a_mapping = 'abc'
        a_mapping = {'a': 'abc'}

        with self.assertRaises(TypeError):
            _datadict_vs_requirementdict(not_a_mapping, a_mapping)

    def test_set_membership_differences(self):
        differences, _ = _datadict_vs_requirementdict(
            {'a': ['x', 'x'], 'b': ['x', 'y', 'z']},
            {'a': set(['x', 'y']), 'b': set(['x', 'y'])},
        )
        differences = self.evaluate_generators(differences)
        expected = {'a': [Missing('y')], 'b': [Extra('z')]}
        self.assertEqual(differences, expected)

    def test_equality_of_single_values(self):
        differences, _ = _datadict_vs_requirementdict(
            data={'a': 'x', 'b': 10},
            requirement={'a': 'j', 'b': 9},
        )
        expected = {'a': Invalid('x', expected='j'), 'b': Deviation(+1, 9)}
        self.assertEqual(differences, expected)

        differences, _ = _datadict_vs_requirementdict(
            data={'a': 'x', 'b': 10, 'c': 10},
            requirement={'a': 'j', 'b': 'k', 'c': 9},
        )
        expected = {'a': Invalid('x', 'j'), 'b': Invalid(10, 'k'), 'c': Deviation(+1, 9)}
        self.assertEqual(differences, expected)

    def test_equality_of_multiple_values(self):
        differences, _ = _datadict_vs_requirementdict(
            data={'a': ['x', 'j'], 'b': [10, 9]},
            requirement={'a': 'j', 'b': 9},
        )
        differences = self.evaluate_generators(differences)
        expected = {'a': [Invalid('x')], 'b': [Deviation(+1, 9)]}
        self.assertEqual(differences, expected)

    def test_equality_of_single_tuples(self):
        differences, _ = _datadict_vs_requirementdict(
            data={'a': (1, 'x'), 'b': (9, 10)},
            requirement={'a': (1, 'j'), 'b': (9, 9)},
        )
        expected = {'a': Invalid((1, 'x'), expected=(1, 'j')),
                    'b': Invalid((9, 10), expected=(9, 9))}
        self.assertEqual(differences, expected)

    def test_equality_of_multiple_tuples(self):
        differences, _ = _datadict_vs_requirementdict(
            data={'a': [(1, 'j'), (1, 'x')], 'b': [(9, 9), (9, 10)]},
            requirement={'a': (1, 'j'), 'b': (9, 9)},
        )
        differences = self.evaluate_generators(differences)
        expected = {'a': [Invalid((1, 'x'))],
                    'b': [Invalid((9, 10))]}
        self.assertEqual(differences, expected)

    def test_missing_keys(self):
        # Equality of multiple values, missing key with single item.
        differences, _ = _datadict_vs_requirementdict(
            data={'a': ['x', 'j'], 'b': [10, 9]},
            requirement={'a': 'j', 'b': 9, 'c': 'z'},
        )
        differences = self.evaluate_generators(differences)
        expected = {'a': [Invalid('x')], 'b': [Deviation(+1, 9)], 'c': Missing('z')}
        self.assertEqual(differences, expected)

        # Equality of multiple values, missing key with single item.
        differences, _ = _datadict_vs_requirementdict(
            data={'a': ['x', 'j'], 'b': [10, 9], 'c': 'z'},
            requirement={'a': 'j', 'b': 9},
        )
        differences = self.evaluate_generators(differences)
        expected = {'a': [Invalid('x')], 'b': [Deviation(+1, 9)], 'c': Extra('z')}
        self.assertEqual(differences, expected)

        # Missing key, set membership.
        differences, _ = _datadict_vs_requirementdict(
            data={'a': 'x'},
            requirement={'a': 'x', 'b': set(['z'])},
        )
        differences = self.evaluate_generators(differences)
        expected = {'b': [Missing('z')]}
        self.assertEqual(differences, expected)

    def test_mismatched_keys(self):
        # Mapping of single-items (BaseElement objects).
        differences, _ = _datadict_vs_requirementdict(
            data={'a': ('abc', 1), 'c': ('abc', 2.0)},
            requirement={'a': ('abc', int), 'b': ('abc', float)},
        )
        expected = {
            'b': Missing(('abc', float)),
            'c': Extra(('abc', 2.0)),
        }
        self.assertEqual(differences, expected)

        # Mapping of containers (lists of BaseElement objects).
        differences, _ = _datadict_vs_requirementdict(
            data={
                'a': [('abc', 1), ('abc', 2)],
                'c': [('abc', 1.0), ('abc', 2.0)],
            },
            requirement={'a': ('abc', int), 'b': ('abc', float)},
        )
        differences = self.evaluate_generators(differences)
        expected = {
            'c': [Extra(('abc', 1.0)), Extra(('abc', 2.0))],
            'b': Missing(('abc', float)),
        }
        self.assertEqual(differences, expected)

    def test_empty_vs_nonempty_values(self):
        empty = {}
        nonempty = {'a': set(['x'])}

        result = _datadict_vs_requirementdict(empty, empty)
        self.assertIsNone(result)

        differences, _ = _datadict_vs_requirementdict(nonempty, empty)
        differences = self.evaluate_generators(differences)
        self.assertEqual(differences, {'a': [Extra('x')]})

        differences, _ = _datadict_vs_requirementdict(empty, nonempty)
        differences = self.evaluate_generators(differences)
        self.assertEqual(differences, {'a': [Missing('x')]})

    def test_description_message(self):
        data = {'a': 'bar', 'b': ['bar', 'bar']}

        @group_requirement
        def func1(iterable):
            return [Invalid('bar')], 'some message'

        @group_requirement
        def func2(iterable):
            return [Invalid('bar')], 'some other message'

        # When message is same for all items, use provided message.
        requirement1 = {'a': func1, 'b': func1}
        _, description = _datadict_vs_requirementdict(data, requirement1)
        self.assertEqual(description, 'some message')

        # When messages are different, description should be None.
        requirement2 = {'a': func1, 'b': func2}
        _, description = _datadict_vs_requirementdict(data, requirement2)
        self.assertIsNone(description)


class TestValidate(unittest.TestCase):
    """An integration test to check behavior of validate() function."""
    def test_required_vs_data_passing(self):
        """Single requirement to BaseElement or non-mapping
        container of data.
        """
        data = ('abc', 1)  # A single base element.
        requirement = ('abc', int)
        self.assertIsNone(validate(data, requirement))

        data = [('abc', 1), ('abc', 2)]  # Non-mapping container of base elements.
        requirement = ('abc', int)
        self.assertIsNone(validate(data, requirement))

    def test_required_vs_data_failing(self):
        """Apply single requirement to BaseElement or non-mapping
        container of data.
        """
        with self.assertRaises(ValidationError) as cm:
            data = ('abc', 1.0)  # A single base element.
            requirement = ('abc', int)
            validate(data, requirement)
        differences = cm.exception.differences
        self.assertEqual(differences, [Invalid(('abc', 1.0), ('abc', int))])

        with self.assertRaises(ValidationError) as cm:
            data = [('abc', 1.0), ('xyz', 2)]  # Non-mapping container of base elements.
            requirement = ('abc', int)
            validate(data, requirement)
        differences = cm.exception.differences
        self.assertEqual(differences, [Invalid(('abc', 1.0)), Invalid(('xyz', 2))])

    def test_required_vs_mapping_passing(self):
        data = {'a': ('abc', 1), 'b': ('abc', 2)}  # Mapping of base-elements.
        requirement = ('abc', int)
        self.assertIsNone(validate(data, requirement))

        data = {'a': [1, 2], 'b': [3, 4]}  # Mapping of containers.
        requirement = int
        self.assertIsNone(validate(data, requirement))

    def test_required_vs_mapping_failing(self):
        with self.assertRaises(ValidationError) as cm:
            data = {'a': ('abc', 1.0), 'b': ('xyz', 2)}  # Mapping of base-elements.
            requirement = ('abc', int)
            validate(data, requirement)
        differences = cm.exception.differences
        self.assertEqual(differences, {'a': Invalid(('abc', 1.0)), 'b': Invalid(('xyz', 2))})

        with self.assertRaises(ValidationError) as cm:
            data = {'a': [1, 2.0], 'b': [3.0, 4]}  # Mapping of containers.
            validate(data, int)
        differences = cm.exception.differences
        self.assertEqual(differences, {'a': [Invalid(2.0)], 'b': [Invalid(3.0)]})

    def test_mapping_vs_mapping_passing(self):
        data = {'a': ('abc', 1), 'b': ('abc', 2.0)}  # Mapping of base-elements.
        requirement = {'a': ('abc', int), 'b': ('abc', float)}  # Mapping of requirements.
        self.assertIsNone(validate(data, requirement))

        data = {'a': [('abc', 1), ('abc', 2)],
                'b': [('abc', 1.0), ('abc', 2.0)]}  # Mapping of containers.
        requirement = {'a': ('abc', int), 'b': ('abc', float)}  # Mapping of requirements.
        self.assertIsNone(validate(data, requirement))

    def test_mapping_vs_mapping_failing(self):
        with self.assertRaises(ValidationError) as cm:
            data = {'a': ('abc', 1.0), 'b': ('xyz', 2.0)}  # Mapping of base-elements.
            requirement = {'a': ('abc', int), 'b': ('abc', float)}  # Mapping of requirements.
            validate(data, requirement)
        actual = cm.exception.differences
        expected = {
            'a': Invalid(('abc', 1.0), ('abc', int)),
            'b': Invalid(('xyz', 2.0), ('abc', float)),
        }
        self.assertEqual(actual, expected)

        with self.assertRaises(ValidationError) as cm:
            data = {'a': [('abc', 1.0), ('abc', 2)],
                    'b': [('abc', 1.0), ('xyz', 2.0)]}  # Mapping of containers.
            requirement = {'a': ('abc', int), 'b': ('abc', float)}  # Mapping of requirements.
            validate(data, requirement)
        actual = cm.exception.differences
        expected = {
            'a': [Invalid(('abc', 1.0))],
            'b': [Invalid(('xyz', 2.0))],
        }
        self.assertEqual(actual, expected)
