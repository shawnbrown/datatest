# -*- coding: utf-8 -*-
from __future__ import absolute_import
from . import _unittest as unittest
from datatest._compatibility.collections.abc import Iterable
from datatest._compatibility.collections.abc import Iterator
from datatest._utils import exhaustible
from datatest._utils import nonstringiter
from datatest import Missing
from datatest import Extra
from datatest import Deviation
from datatest import Invalid
from datatest._required import _build_description
from datatest._required import _wrap_differences
from datatest._required import group_requirement
from datatest._required import required_predicate
from datatest._required import required_set
from datatest._required import required_sequence
from datatest._required import _get_group_requirement
from datatest._required import _data_vs_requirement
from datatest._required import _datadict_vs_requirement
from datatest._required import _datadict_vs_requirementdict
from datatest._required import _normalize_requirement_result
from datatest._required import BaseRequirement
from datatest._required import ItemsRequirement
from datatest._required import GroupRequirement
from datatest._required import RequiredMapping
from datatest._required import RequiredOrder
from datatest._required import RequiredPredicate
from datatest._required import RequiredSet
from datatest._required import get_requirement
from datatest._required import RequiredUnique
from datatest._required import RequiredSubset
from datatest._required import RequiredSuperset
from datatest._required import RequiredApprox
from datatest._required import RequiredOutliers
from datatest._required import RequiredFuzzy
from datatest.difference import NOTFOUND


class TestBuildDescription(unittest.TestCase):
    def test_docstring_messy(self):
        def func(x):
            """  \n  line one  \nline two"""  # <- Deliberately messy
            return False                      #    whitespace, do not
                                              #    change.
        description = _build_description(func)
        self.assertEqual(description, 'line one')

    def test_docstring_whitespace(self):
        def func(x):
            """    \n    """  # <- Docstring is entirely whitespace.
            return False

        description = _build_description(func)
        self.assertEqual(description, 'does not satisfy func()')

    def test_docstring_is_None(self):
        def func(x):
            return False
        description = _build_description(func)
        self.assertEqual(description, 'does not satisfy func()')

    def test_builtin_type(self):
        description = _build_description(float)
        msg = 'should be name in single quotes'
        self.assertEqual(description, "does not satisfy 'float'", msg=msg)

    def test_user_defined_type(self):
        """User-defined classes should use the name in quotes (not the
        docstring).
        """
        class MyClass(object):
            """A dummy class for testing."""
            def __call__(self, *args):
                """Always returns False."""
                return False

            def __repr__(self):
                return '**dummy class**'

        self.assertTrue(MyClass.__doc__, msg='make sure class has docstring')

        description = _build_description(MyClass)
        msg = 'user defined classes should work same as built-in types (name in quotes)'
        self.assertEqual(description, "does not satisfy 'MyClass'", msg=msg)

    def test_lambda_expression(self):
        description = _build_description(lambda x: False)
        msg = 'if object is in angle brackets, should not use quotes'
        self.assertEqual(description, "does not satisfy <lambda>", msg=msg)

    def test_no_docstring_no_name(self):
        """Non-type objects with no name and no docstring should use
        the object's repr().
        """
        description = _build_description('abc')
        self.assertEqual(description, "does not satisfy 'abc'")

        description = _build_description(123)
        self.assertEqual(description, "does not satisfy 123")

        class MyClass(object):
            """A dummy class for testing."""
            def __call__(self, *args):
                """Always returns False."""
                return False

            def __repr__(self):
                return '**dummy class**'

        myinstance = MyClass()  # <- Instance of user-defined class.
        description = _build_description(myinstance)
        self.assertEqual(description, "does not satisfy **dummy class**")


class TestWrapDifferences(unittest.TestCase):
    def test_good_values(self):
        diffs = [Missing(1), Missing(2), Missing(3)]
        wrapped = _wrap_differences(diffs, lambda x: [])
        msg = 'yielding difference objects should work without issue'
        self.assertEqual(list(wrapped), diffs, msg=msg)

    def test_bad_value(self):
        diffs = [Missing(1), Missing(2), 123]
        wrapped = _wrap_differences(diffs, lambda x: [])
        msg = 'yielding a non-difference object should fail with a useful message'
        pattern = ("iterable from group requirement '<lambda>' must "
                   "contain difference objects, got 'int': 123")
        with self.assertRaisesRegex(TypeError, pattern, msg=msg):
            list(wrapped)  # <- Fully evaluate generator.


class TestNormalizeRequirementResult(unittest.TestCase):
    def setUp(self):
        def func(iterable):  # <- A dummy function.
            return None
        self.func = func

    def test_iter_and_description(self):
        result = ([Missing(1)], 'error message')  # <- Iterable and description.
        diffs, desc = _normalize_requirement_result(result, self.func)
        self.assertEqual(list(diffs), [Missing(1)])
        self.assertEqual(desc, 'error message')

    def test_iter_alone(self):
        result = [Missing(1)]  # <- Iterable only, no description.
        diffs, desc = _normalize_requirement_result(result, self.func)
        self.assertEqual(list(diffs), [Missing(1)])
        self.assertEqual(desc, 'does not satisfy func()', msg='gets default description')

    def test_tuple_of_diffs(self):
        """Should not mistake a 2-tuple of difference objects for a
        2-tuple containing an iterable of differences with a string
        description.
        """
        result = (Missing(1), Missing(2))  # <- A 2-tuple of diffs.
        diffs, desc = _normalize_requirement_result(result, self.func)
        self.assertEqual(list(diffs), [Missing(1), Missing(2)])
        self.assertEqual(desc, 'does not satisfy func()', msg='gets default description')

    def test_empty_iter(self):
        """Empty iterable result should be converted to None."""
        result = (iter([]), 'error message')  # <- Empty iterable and description.
        normalized = _normalize_requirement_result(result, self.func)
        self.assertIsNone(normalized)

        result = iter([])  # <- Empty iterable
        normalized = _normalize_requirement_result(result, self.func)
        self.assertIsNone(normalized)

    def test_bad_types(self):
        """Bad return types should trigger TypeError."""
        with self.assertRaisesRegex(TypeError, 'should return .* iterable'):
            result = (Missing(1), 'error message')  # <- Non-iterable and description.
            _normalize_requirement_result(result, self.func)

        with self.assertRaisesRegex(TypeError, 'should return .* iterable'):
            result = None  # <- None only.
            _normalize_requirement_result(result, self.func)

        with self.assertRaisesRegex(TypeError, 'should return .* an iterable and a string'):
            result = (None, 'error message')  # <- None and description
            _normalize_requirement_result(result, self.func)


class TestGroupRequirement(unittest.TestCase):
    def test_group_requirement_flag(self):
        def func(iterable):
            return [Missing(1)], 'error message'

        self.assertFalse(hasattr(func, '_group_requirement'))

        func = group_requirement(func)  # <- Apply decorator.
        self.assertTrue(hasattr(func, '_group_requirement'))
        self.assertTrue(func._group_requirement)

    def test_group_requirement_wrapping(self):
        """Decorating a group requirement should return the original
        object, it should not double-wrap existing group requirements.
        """
        @group_requirement
        def func1(iterable):
            return [Missing(1)], 'error message'

        func2 = group_requirement(func1)

        self.assertIs(func1, func2)


class TestRequiredPredicate(unittest.TestCase):
    def setUp(self):
        isdigit = lambda x: x.isdigit()
        self.requirement = required_predicate(isdigit)

    def test_all_true(self):
        data = iter(['10', '20', '30'])
        result = self.requirement(data)
        self.assertIsNone(result)  # Predicate is true for all, returns None.

    def test_some_false(self):
        """When the predicate returns False, values should be returned as
        Invalid() differences.
        """
        data = ['10', '20', 'XX']
        differences, _ = self.requirement(data)
        self.assertEqual(list(differences), [Invalid('XX')])

    def test_show_expected(self):
        data = ['XX', 'YY']
        requirement = required_predicate('YY', show_expected=True)
        differences, _ = requirement(data)
        self.assertEqual(list(differences), [Invalid('XX', expected='YY')])

    def test_duplicate_false(self):
        """Should return one difference for every false result (including
        duplicates).
        """
        data = ['10', '20', 'XX', 'XX', 'XX']  # <- Multiple XX's.
        differences, _ = self.requirement(data)
        self.assertEqual(list(differences), [Invalid('XX'), Invalid('XX'), Invalid('XX')])

    def test_empty_iterable(self):
        result = self.requirement([])
        self.assertIsNone(result)

    def test_some_false_deviations(self):
        """When the predicate returns False, numeric differences should
        be Deviation() objects not Invalid() objects.
        """
        data = [10, 10, 12]
        requirement = required_predicate(10)

        differences, _ = requirement(data)
        self.assertEqual(list(differences), [Deviation(+2, 10)])

    def test_predicate_error(self):
        """Errors should not be counted as False or otherwise hidden."""
        data = ['10', '20', 'XX', 40]  # <- Predicate assumes string, int has no isdigit().
        differences, _  = self.requirement(data)
        with self.assertRaisesRegex(AttributeError, "no attribute 'isdigit'"):
            list(differences)

    def test_returned_difference(self):
        """When a predicate returns a difference object, it should
        used in place of the default Invalid difference.
        """
        def counts_to_three(x):
            if 1 <= x <= 3:
                return True
            if x == 4:
                return Invalid('4 shalt thou not count')
            return Invalid('{0} is right out'.format(x))

        requirement = required_predicate(counts_to_three)

        data = [1, 2, 3, 4, 5]
        differences, _ = requirement(data)
        expected = [
            Invalid('4 shalt thou not count'),
            Invalid('5 is right out'),
        ]
        self.assertEqual(list(differences), expected)


class TestRequiredSet(unittest.TestCase):
    def setUp(self):
        self.requirement = required_set(set([1, 2, 3]))

    def test_no_difference(self):
        data = iter([1, 2, 3])
        result = self.requirement(data)
        self.assertIsNone(result)  # No difference, returns None.

    def test_missing(self):
        data = iter([1, 2])
        differences, description = self.requirement(data)
        self.assertEqual(list(differences), [Missing(3)])

    def test_extra(self):
        data = iter([1, 2, 3, 4])
        differences, description = self.requirement(data)
        self.assertEqual(list(differences), [Extra(4)])

    def test_repeat_values(self):
        """Repeat values should not result in duplicate differences."""
        data = iter([1, 2, 3, 4, 4, 4])  # <- Multiple 4's.
        differences, description = self.requirement(data)
        self.assertEqual(list(differences), [Extra(4)])  # <- One difference.

    def test_missing_and_extra(self):
        data = iter([1, 3, 4])
        differences, description = self.requirement(data)
        self.assertEqual(list(differences), [Missing(2), Extra(4)])

    def test_empty_iterable(self):
        requirement = required_set(set([1]))
        differences, description = requirement([])
        self.assertEqual(list(differences), [Missing(1)])


class TestRequiredSequence(unittest.TestCase):
    def test_no_difference(self):
        data = ['aaa', 'bbb', 'ccc']
        required = required_sequence(['aaa', 'bbb', 'ccc'])
        self.assertIsNone(required(data))  # No difference, returns None.

    def test_some_missing(self):
        data = ['bbb', 'ddd']
        required = required_sequence(['aaa', 'bbb', 'ccc', 'ddd', 'eee'])
        differences, _ = required(data)
        expected = [
            Missing((0, 'aaa')),
            Missing((1, 'ccc')),
            Missing((2, 'eee')),
        ]
        self.assertEqual(list(differences), expected)

    def test_all_missing(self):
        data = []  # <- Empty!
        required = required_sequence(['aaa', 'bbb'])
        differences, _ = required(data)
        expected = [
            Missing((0, 'aaa')),
            Missing((0, 'bbb')),
        ]
        self.assertEqual(list(differences), expected)

    def test_some_extra(self):
        data = ['aaa', 'bbb', 'ccc', 'ddd', 'eee', 'fff']
        required = required_sequence(['aaa', 'bbb', 'ccc'])
        differences, _ = required(data)
        expected = [
            Extra((3, 'ddd')),
            Extra((4, 'eee')),
            Extra((5, 'fff')),
        ]
        self.assertEqual(list(differences), expected)

    def test_all_extra(self):
        data = ['aaa', 'bbb']
        required = required_sequence([])  # <- Empty!
        differences, _ = required(data)
        expected = [
            Extra((0, 'aaa')),
            Extra((1, 'bbb')),
        ]
        self.assertEqual(list(differences), expected)

    def test_one_missing_and_extra(self):
        data = ['aaa', 'xxx', 'ccc']
        required = required_sequence(['aaa', 'bbb', 'ccc'])
        differences, _ = required(data)
        expected = [
            Missing((1, 'bbb')),
            Extra((1, 'xxx')),
        ]
        self.assertEqual(list(differences), expected)

    def test_some_missing_and_extra(self):
        data = ['aaa', 'xxx', 'ccc', 'yyy', 'zzz']
        required = required_sequence(['aaa', 'bbb', 'ccc', 'ddd', 'eee'])
        differences, _ = required(data)
        expected = [
            Missing((1, 'bbb')),
            Extra((1, 'xxx')),
            Missing((3, 'ddd')),
            Extra((3, 'yyy')),
            Missing((4, 'eee')),
            Extra((4, 'zzz')),
        ]
        self.assertEqual(list(differences), expected)

    def test_some_missing_and_extra_different_lengths(self):
        data = ['aaa', 'xxx', 'eee']
        required = required_sequence(['aaa', 'bbb', 'ccc', 'ddd', 'eee'])
        differences, _ = required(data)
        expected = [
            Missing((1, 'bbb')),
            Extra((1, 'xxx')),
            Missing((2, 'ccc')),
            Missing((2, 'ddd')),
        ]
        self.assertEqual(list(differences), expected)

        data = ['aaa', 'xxx', 'yyy', 'zzz', 'ccc']
        required = required_sequence(['aaa', 'bbb', 'ccc'])
        differences, _ = required(data)
        expected = [
            Missing((1, 'bbb')),
            Extra((1, 'xxx')),
            Extra((2, 'yyy')),
            Extra((3, 'zzz')),
        ]
        self.assertEqual(list(differences), expected)

    def test_numeric_matching(self):
        """When checking sequence order, numeric differences should NOT
        be converted into Deviation objects.
        """
        data = [1, 100, 4, 200, 300]
        required = required_sequence([1, 2, 3, 4, 5])
        differences, _ = required(data)
        expected = [
            Missing((1, 2)),
            Extra((1, 100)),
            Missing((2, 3)),
            Missing((3, 5)),
            Extra((3, 200)),
            Extra((4, 300)),
        ]
        self.assertEqual(list(differences), expected)

    def test_unhashable_objects(self):
        """Should try to compare sequences of unhashable types."""
        data = [{'a': 1}, {'b': 2}, {'c': 3}]
        required = required_sequence([{'a': 1}, {'b': 2}, {'c': 3}])
        result = required(data)
        self.assertIsNone(result)  # No difference, returns None.

        data = [{'a': 1}, {'x': 0}, {'d': 4}, {'y': 5}, {'g': 7}]
        required = required_sequence([{'a': 1}, {'b': 2}, {'c': 3}, {'d': 4}, {'f': 6}])
        differences, _ = required(data)
        expected = [
            Missing((1, {'b': 2})),
            Extra((1, {'x': 0})),
            Missing((2, {'c': 3})),
            Missing((3, {'f': 6})),
            Extra((3, {'y': 5})),
            Extra((4, {'g': 7})),
        ]
        self.assertEqual(list(differences), expected)


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


#######################################################################
# New BaseRequirement and subclass tests.
#######################################################################

def evaluate_items(items):  # <- Test helper.
    """Eagerly evaluate items and return a sorted list of tuples."""
    evaluate = lambda v: list(v) if nonstringiter(v) and exhaustible(v) else v
    return sorted([(k, evaluate(v)) for k, v in items])


class TestBaseRequirement(unittest.TestCase):
    def setUp(self):
        class MinimalRequirement(BaseRequirement):
            def check_data(self, data):
                return [], ''

        self.requirement = MinimalRequirement()

    def test_missing_abstractmethod(self):
        with self.assertRaises(TypeError):
            BaseRequirement()

    def test_verify_difference(self):
        self.assertIsNone(self.requirement._verify_difference(Missing(1)),
                          msg='no explicit return value')

        regex = (r"values returned from MinimalRequirement must be "
                 r"difference objects, got str: 'a string instance'")
        with self.assertRaisesRegex(TypeError, regex):
            self.requirement._verify_difference('a string instance')

    def test_wrap_difference_group(self):
        group = [Missing(1), Missing(2)]
        wrapped = self.requirement._wrap_difference_group(group)
        self.assertEqual(list(wrapped), group)

        group = [Missing(1), 'a string instance']
        wrapped = self.requirement._wrap_difference_group(group)
        with self.assertRaises(TypeError):
            list(wrapped)  # <- Evaluate generator.

    def test_wrap_difference_items(self):
        # Values as single differences.
        items = [('A', Missing(1)), ('B', Missing(2))]
        wrapped = self.requirement._wrap_difference_items(items)
        self.assertEqual(list(wrapped), items)

        items = [('A', Missing(1)), ('B', 'a string instance')]
        wrapped = self.requirement._wrap_difference_items(items)
        with self.assertRaises(TypeError):
            list(wrapped)  # <- Evaluate generator.

        # Values as groups of differences.
        items = [('A', [Missing(1), Missing(2)]),
                 ('B', [Missing(3), Missing(4)])]
        wrapped = self.requirement._wrap_difference_items(items)
        self.assertEqual([(k, list(v)) for k, v in wrapped], items)

        items = [('A', [Missing(1), Missing(2)]),
                 ('B', [Missing(3), 'a string instance'])]
        wrapped = self.requirement._wrap_difference_items(items)
        with self.assertRaises(TypeError):
            evaluate_items(wrapped)  # <- Evaluate generator.

    def test_normalize_iter_and_description(self):
        result = ([Missing(1)], 'error message')  # <- Iterable and description.
        diffs, desc = self.requirement._normalize(result)
        self.assertEqual(list(diffs), [Missing(1)])
        self.assertEqual(desc, 'error message')

    def test_normalize_iter(self):
        result = [Missing(1)]  # <- Iterable only, no description.
        diffs, desc = self.requirement._normalize(result)
        self.assertEqual(list(diffs), [Missing(1)])
        self.assertEqual(desc, 'does not satisfy MinimalRequirement', msg='gets default description')

    def test_normalize_tuple_of_diffs(self):
        """Should not mistake a 2-tuple of difference objects for a
        2-tuple containing an iterable of differences with a string
        description.
        """
        result = (Missing(1), Missing(2))  # <- A 2-tuple of diffs.
        diffs, desc = self.requirement._normalize(result)
        self.assertEqual(list(diffs), [Missing(1), Missing(2)])
        self.assertEqual(desc, 'does not satisfy MinimalRequirement', msg='gets default description')

    def test_normalize_empty_iter(self):
        """Empty iterable result should be converted to None."""
        result = (iter([]), 'error message')  # <- Empty iterable and description.
        normalized = self.requirement._normalize(result)
        self.assertIsNone(normalized)

        result = iter([])  # <- Empty iterable
        normalized = self.requirement._normalize(result)
        self.assertIsNone(normalized)

    def test_normalize_bad_types(self):
        """Bad return types should trigger TypeError."""
        with self.assertRaisesRegex(TypeError, 'should return .* iterable'):
            result = (Missing(1), 'error message')  # <- Non-iterable and description.
            self.requirement._normalize(result)

        with self.assertRaisesRegex(TypeError, 'should return .* iterable'):
            result = None  # <- None only.
            self.requirement._normalize(result)

        with self.assertRaisesRegex(TypeError, 'should return .* an iterable and a string'):
            result = (None, 'error message')  # <- None and description
            self.requirement._normalize(result)


class TestItemsRequirement(unittest.TestCase):
    def setUp(self):
        class RequiredIntValues(ItemsRequirement):
            def check_items(self, items):
                for k, v in items:
                    if not isinstance(v, int):
                        yield k, Invalid(v)

        self.requirement = RequiredIntValues()

    def test_missing_abstractmethod(self):
        with self.assertRaises(TypeError):
            ItemsRequirement()

    def test_check_items(self):
        self.assertIsNone(self.requirement([('A', 1), ('B', 2)]),
                          msg='should return None when data satisfies requirement')

        diff, desc = self.requirement([('A', 1), ('B', 2.0)])
        self.assertEqual(list(diff), [('B', Invalid(2.0))],
                         msg='should return items iterable for values that fail requirement')

    def test_check_data(self):
        diff, desc = self.requirement([('A', 1), ('B', 2.0)])
        self.assertEqual(list(diff), [('B', Invalid(2.0))])

        diff, desc = self.requirement({'A': 1, 'B': 2.0})
        self.assertEqual(list(diff), [('B', Invalid(2.0))])


class TestGroupRequirement(unittest.TestCase):
    def setUp(self):
        class RequiredThreePlus(GroupRequirement):
            def check_group(self, group):
                group = list(group)
                if len(group) < 3:
                    diffs = (Invalid(x) for x in group)
                    return diffs, 'requires 3 or more elements'
                return [], ''

        self.requirement = RequiredThreePlus()

    def test_missing_abstractmethod(self):
        with self.assertRaises(TypeError):
            GroupRequirement()

    def test_check_group(self):
        requirement = self.requirement

        diff, desc = requirement.check_group([1, 2, 3])
        self.assertEqual(list(diff), [])
        self.assertEqual(desc, '')

        diff, desc = requirement.check_group([1, 2])
        self.assertEqual(list(diff), [Invalid(1), Invalid(2)])
        self.assertEqual(desc, 'requires 3 or more elements')

    def test_check_items(self):
        data = [('A', [1, 2, 3]), ('B', [4, 5, 6])]
        diff, desc = self.requirement.check_items(data)
        self.assertEqual(diff, [])
        self.assertEqual(desc, '')

        data = [('A', [1, 2, 3]), ('B', [4, 5])]
        diff, desc = self.requirement.check_items(data)
        diff = sorted((k, list(v)) for k, v in diff)
        self.assertEqual(diff, [('B', [Invalid(4), Invalid(5)])])
        self.assertEqual(desc, 'requires 3 or more elements')

    def test_check_items_autowrap(self):
        """Check autowrap behavior."""
        data = [('A', 1)]  # <- 1 is a base element, not a group of elements.

        # With autowrap=True, the 1 should get wrapped in a list and
        # treated as a group.
        diff, desc = self.requirement.check_items(data)  # <- autowrap=True is the default
        diff = sorted((k, v) for k, v in diff)
        self.assertEqual(diff, [('A', Invalid(1))])
        self.assertEqual(desc, 'requires 3 or more elements')

        # With autowrap=False, the 1 used as-is without changes.
        with self.assertRaises(TypeError):
            self.requirement.check_items(data, autowrap=False)

    def test_check_data(self):
        # Test mapping or key/value items.
        data = {'A': [1, 2, 3], 'B': [4, 5], 'C': 6}
        diff, desc = self.requirement.check_data(data)
        diff = sorted((k, list(v) if isinstance(v, Iterable) else v) for k, v in diff)
        self.assertEqual(diff, [('B', [Invalid(4), Invalid(5)]), ('C', Invalid(6))])
        self.assertEqual(desc, 'requires 3 or more elements')

        # Test group.
        data = [4, 5]
        diff, desc = self.requirement.check_data(data)
        self.assertEqual(list(diff), [Invalid(4), Invalid(5)])
        self.assertEqual(desc, 'requires 3 or more elements')

        # Test BaseElement.
        data = 4
        diff, desc = self.requirement.check_data(data)
        self.assertEqual(list(diff), [Invalid(4)])
        self.assertEqual(desc, 'requires 3 or more elements')


class TestRequiredPredicate2(unittest.TestCase):
    def setUp(self):
        def isdigit(x):
            return x.isdigit()
        self.requirement = RequiredPredicate(isdigit)

    def test_all_true(self):
        data = iter(['10', '20', '30'])
        result = self.requirement(data)
        self.assertIsNone(result)  # Predicate is true for all, returns None.

    def test_some_false(self):
        """When the predicate returns False, values should be returned as
        Invalid() differences.
        """
        data = ['10', '20', 'XX']
        diff, desc = self.requirement(data)
        self.assertEqual(list(diff), [Invalid('XX')])
        self.assertEqual(desc, 'does not satisfy isdigit()')

    def test_show_expected(self):
        data = ['XX', 'YY']
        requirement = RequiredPredicate('YY', show_expected=True)
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Invalid('XX', expected='YY')])
        self.assertEqual(desc, "does not satisfy 'YY'")

    def test_duplicate_false(self):
        """Should return one difference for every false result (including
        duplicates).
        """
        data = ['10', '20', 'XX', 'XX', 'XX']  # <- Multiple XX's.
        diff, desc = self.requirement(data)
        self.assertEqual(list(diff), [Invalid('XX'), Invalid('XX'), Invalid('XX')])
        self.assertEqual(desc, 'does not satisfy isdigit()')

    def test_empty_iterable(self):
        result = self.requirement([])
        self.assertIsNone(result)

    def test_some_false_deviations(self):
        """When the predicate returns False, numeric differences should
        be Deviation() objects not Invalid() objects.
        """
        data = [10, 10, 12]
        requirement = RequiredPredicate(10)

        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Deviation(+2, 10)])
        self.assertEqual(desc, 'does not satisfy 10')

    def test_notfound_token(self):
        data = [123, 'abc']
        requirement = RequiredPredicate(NOTFOUND)
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Deviation(+123, None), Extra('abc')])
        #self.assertEqual(desc, 'does not satisfy requirement')

        data = [10, NOTFOUND]
        requirement = RequiredPredicate(10)
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Deviation(-10, 10)])
        self.assertEqual(desc, 'does not satisfy 10')

        data = ['abc', NOTFOUND]
        requirement = RequiredPredicate('abc')
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Missing('abc')])
        self.assertEqual(desc, "does not satisfy 'abc'")

    def test_predicate_error(self):
        """Errors should not be counted as False or otherwise hidden."""
        data = ['10', '20', 'XX', 40]  # <- Predicate assumes string, int has no isdigit().
        diff, desc  = self.requirement(data)
        with self.assertRaisesRegex(AttributeError, "no attribute 'isdigit'"):
            list(diff)

    def test_returned_difference(self):
        """When a predicate returns a difference object, it should
        used in place of the default Invalid difference.
        """
        def counts_to_three(x):
            if 1 <= x <= 3:
                return True
            if x == 4:
                return Invalid('4 shalt thou not count')
            return Invalid('{0} is right out'.format(x))

        requirement = RequiredPredicate(counts_to_three)

        data = [1, 2, 3, 4, 5]
        diff, desc = requirement(data)
        expected = [
            Invalid('4 shalt thou not count'),
            Invalid('5 is right out'),
        ]
        self.assertEqual(list(diff), expected)
        self.assertEqual(desc, 'does not satisfy counts_to_three()')

    def test_items(self):
        def iseven(x):
            return x % 2 == 0
        requirement = RequiredPredicate(iseven)

        data = {'A': [2, 4, 5], 'B': 6, 'C': 7}
        diff, desc = requirement(data)
        expected = [
            ('A', [Invalid(5)]),
            ('C', Invalid(7)),
        ]
        self.assertEqual(evaluate_items(diff), expected)


class TestRequiredSet2(unittest.TestCase):
    def setUp(self):
        self.requirement = RequiredSet(set([1, 2, 3]))

    def test_no_difference(self):
        data = iter([1, 2, 3])
        result = self.requirement(data)
        self.assertIsNone(result)  # No difference, returns None.

    def test_missing(self):
        data = iter([1, 2])
        differences, description = self.requirement(data)
        self.assertEqual(list(differences), [Missing(3)])

    def test_extra(self):
        data = iter([1, 2, 3, 4])
        differences, description = self.requirement(data)
        self.assertEqual(list(differences), [Extra(4)])

    def test_repeat_values(self):
        """Repeat values should not result in duplicate differences."""
        data = iter([1, 2, 3, 4, 4, 4])  # <- Multiple 4's.
        differences, description = self.requirement(data)
        self.assertEqual(list(differences), [Extra(4)])  # <- One difference.

    def test_missing_and_extra(self):
        data = iter([1, 3, 4])
        differences, description = self.requirement(data)
        self.assertEqual(list(differences), [Missing(2), Extra(4)])

    def test_empty_iterable(self):
        requirement = RequiredSet(set([1]))
        differences, description = requirement([])
        self.assertEqual(list(differences), [Missing(1)])


class TestRequiredOrder2(unittest.TestCase):
    def test_no_difference(self):
        data = ['aaa', 'bbb', 'ccc']
        required = RequiredOrder(['aaa', 'bbb', 'ccc'])
        self.assertIsNone(required(data))  # No difference, returns None.

    def test_some_missing(self):
        data = ['bbb', 'ddd']
        required = RequiredOrder(['aaa', 'bbb', 'ccc', 'ddd', 'eee'])
        differences, _ = required(data)
        expected = [
            Missing((0, 'aaa')),
            Missing((1, 'ccc')),
            Missing((2, 'eee')),
        ]
        self.assertEqual(list(differences), expected)

    def test_all_missing(self):
        data = []  # <- Empty!
        required = RequiredOrder(['aaa', 'bbb'])
        differences, _ = required(data)
        expected = [
            Missing((0, 'aaa')),
            Missing((0, 'bbb')),
        ]
        self.assertEqual(list(differences), expected)

    def test_some_extra(self):
        data = ['aaa', 'bbb', 'ccc', 'ddd', 'eee', 'fff']
        required = RequiredOrder(['aaa', 'bbb', 'ccc'])
        differences, _ = required(data)
        expected = [
            Extra((3, 'ddd')),
            Extra((4, 'eee')),
            Extra((5, 'fff')),
        ]
        self.assertEqual(list(differences), expected)

    def test_all_extra(self):
        data = ['aaa', 'bbb']
        required = RequiredOrder([])  # <- Empty!
        differences, _ = required(data)
        expected = [
            Extra((0, 'aaa')),
            Extra((1, 'bbb')),
        ]
        self.assertEqual(list(differences), expected)

    def test_one_missing_and_extra(self):
        data = ['aaa', 'xxx', 'ccc']
        required = RequiredOrder(['aaa', 'bbb', 'ccc'])
        differences, _ = required(data)
        expected = [
            Missing((1, 'bbb')),
            Extra((1, 'xxx')),
        ]
        self.assertEqual(list(differences), expected)

    def test_some_missing_and_extra(self):
        data = ['aaa', 'xxx', 'ccc', 'yyy', 'zzz']
        required = RequiredOrder(['aaa', 'bbb', 'ccc', 'ddd', 'eee'])
        differences, _ = required(data)
        expected = [
            Missing((1, 'bbb')),
            Extra((1, 'xxx')),
            Missing((3, 'ddd')),
            Extra((3, 'yyy')),
            Missing((4, 'eee')),
            Extra((4, 'zzz')),
        ]
        self.assertEqual(list(differences), expected)

    def test_some_missing_and_extra_different_lengths(self):
        data = ['aaa', 'xxx', 'eee']
        required = RequiredOrder(['aaa', 'bbb', 'ccc', 'ddd', 'eee'])
        differences, _ = required(data)
        expected = [
            Missing((1, 'bbb')),
            Extra((1, 'xxx')),
            Missing((2, 'ccc')),
            Missing((2, 'ddd')),
        ]
        self.assertEqual(list(differences), expected)

        data = ['aaa', 'xxx', 'yyy', 'zzz', 'ccc']
        required = RequiredOrder(['aaa', 'bbb', 'ccc'])
        differences, _ = required(data)
        expected = [
            Missing((1, 'bbb')),
            Extra((1, 'xxx')),
            Extra((2, 'yyy')),
            Extra((3, 'zzz')),
        ]
        self.assertEqual(list(differences), expected)

    def test_numeric_matching(self):
        """When checking element order, numeric differences should NOT
        be converted into Deviation objects.
        """
        data = [1, 100, 4, 200, 300]
        required = RequiredOrder([1, 2, 3, 4, 5])
        differences, _ = required(data)
        expected = [
            Missing((1, 2)),
            Extra((1, 100)),
            Missing((2, 3)),
            Missing((3, 5)),
            Extra((3, 200)),
            Extra((4, 300)),
        ]
        self.assertEqual(list(differences), expected)

    def test_unhashable_objects(self):
        """Should try to compare sequences of unhashable types."""
        data = [{'a': 1}, {'b': 2}, {'c': 3}]
        required = RequiredOrder([{'a': 1}, {'b': 2}, {'c': 3}])
        result = required(data)
        self.assertIsNone(result)  # No difference, returns None.

        data = [{'a': 1}, {'x': 0}, {'d': 4}, {'y': 5}, {'g': 7}]
        required = RequiredOrder([{'a': 1}, {'b': 2}, {'c': 3}, {'d': 4}, {'f': 6}])
        differences, _ = required(data)
        expected = [
            Missing((1, {'b': 2})),
            Extra((1, {'x': 0})),
            Missing((2, {'c': 3})),
            Missing((3, {'f': 6})),
            Extra((3, {'y': 5})),
            Extra((4, {'g': 7})),
        ]
        self.assertEqual(list(differences), expected)


class TestRequiredMapping(unittest.TestCase):
    def test_instantiation(self):
        # Should pass without error.
        some_dict = {'a': 'abc'}
        requirement = RequiredMapping(some_dict)
        requirement = RequiredMapping(some_dict.items())

        with self.assertRaises(ValueError):
            requirement = RequiredMapping('abc')

    def test_bad_data_type(self):
        requirement = RequiredMapping({'a': 'abc'})
        with self.assertRaises(ValueError):
            requirement('abc')

    def test_equality_of_single_elements(self):
        requirement = RequiredMapping({'a': 'j', 'b': 'k', 'c': 9})
        diff, desc = requirement({'a': 'x', 'b': 10, 'c': 10})
        expected = {'a': Invalid('x', 'j'), 'b': Invalid(10, 'k'), 'c': Deviation(+1, 9)}
        self.assertEqual(dict(diff), expected)
        self.assertEqual(desc, 'does not satisfy mapping requirements')

        # Test that tuples are also treated as single-elements.
        requirement = RequiredMapping({'a': (1, 'j'), 'b': (9, 9)})
        diff, desc = requirement({'a': (1, 'x'), 'b': (9, 10)})
        expected = {'a': Invalid((1, 'x'), expected=(1, 'j')),
                    'b': Invalid((9, 10), expected=(9, 9))}
        self.assertEqual(dict(diff), expected)
        self.assertEqual(desc, 'does not satisfy mapping requirements')

        # Test custom difference handling.
        def func1(x):
            return True if x == 'foo' else Invalid('bar')

        def func2(x):
            return True if x == 'foo' else Invalid('baz')

        requirement = RequiredMapping({'a': func1, 'b': func2})
        diff, desc = requirement({'a': 'qux', 'b': 'quux'})
        expected = {'a': Invalid('bar'), 'b': Invalid('baz')}
        self.assertEqual(dict(diff), expected)
        self.assertEqual(desc, 'does not satisfy mapping requirements')

    def test_equality_of_multiple_elements(self):
        requirement = RequiredMapping({'a': 'j', 'b': 9})
        diff, desc = requirement({'a': ['x', 'j'], 'b': [10, 9]})
        expected = [
            ('a', [Invalid('x')]),
            ('b', [Deviation(+1, 9)]),
        ]
        self.assertEqual(evaluate_items(diff), expected)
        self.assertEqual(desc, 'does not satisfy mapping requirements')

        # Test groups of tuple elements.
        requirement = RequiredMapping({'a': (1, 'j'), 'b': (9, 9)})
        diff, desc = requirement({'a': [(1, 'j'), (1, 'x')], 'b': [(9, 9), (9, 10)]})
        expected = [
            ('a', [Invalid((1, 'x'))]),
            ('b', [Invalid((9, 10))]),
        ]
        self.assertEqual(evaluate_items(diff), expected)
        self.assertEqual(desc, 'does not satisfy mapping requirements')

    def test_set_membership_differences(self):
        requirement = RequiredMapping({'a': set(['x', 'y']), 'b': set(['x', 'y'])})
        diff, desc = requirement({'a': ['x', 'x'], 'b': ['x', 'y', 'z']})
        expected = [
            ('a', [Missing('y')]),
            ('b', [Extra('z')]),
        ]
        self.assertEqual(evaluate_items(diff), expected)
        self.assertEqual(desc, 'does not satisfy set membership')

        requirement = RequiredMapping({'a': set(['x', 'y'])})
        diff, desc = requirement({'a': 'x'})
        expected = [
            ('a', Missing('y')),
        ]
        self.assertEqual(evaluate_items(diff), expected)
        self.assertEqual(desc, 'does not satisfy set membership')

    def test_mismatched_keys(self):
        # Required keys missing from data.
        requirement = RequiredMapping({
            'a': 'j',
            'b': 9,
            'c': 'x',
            'd': set(['y']),
        })
        diff, desc = requirement({'a': 'j'})
        expected = [
            ('b', Deviation(-9, 9)),
            ('c', Missing('x')),
            ('d', [Missing('y')]),
        ]
        self.assertEqual(evaluate_items(diff), expected)
        self.assertEqual(desc, 'does not satisfy mapping requirements')

        # Extra keys unexpectedly found in data.
        requirement = RequiredMapping({'a': 'j'})
        diff, desc = requirement({
            'a': 'j',
            'b': 9,
            'c': [10, 11],
            'd': 'x',
            'e': set(['y']),
        })
        expected = [
            ('b', Deviation(+9, None)),
            ('c', [Deviation(+10, None), Deviation(+11, None)]),
            ('d', Extra('x')),
            ('e', [Extra('y')]),
        ]
        self.assertEqual(evaluate_items(diff), expected)
        self.assertEqual(desc, 'does not satisfy mapping requirements')

    def test_empty_vs_nonempty_values(self):
        empty = dict()
        nonempty = {'a': set(['x'])}
        required_empty = RequiredMapping(empty)
        required_nonempty = RequiredMapping(nonempty)

        self.assertIsNone(required_empty(empty))

        diff, desc = required_empty(nonempty)
        expected = [
            ('a', [Extra('x')]),
        ]
        self.assertEqual(evaluate_items(diff), expected)

        diff, desc = required_nonempty(empty)
        expected = [
            ('a', [Missing('x')]),
        ]
        self.assertEqual(evaluate_items(diff), expected)

    def test_custom_requirements(self):
        class MyRequirement(GroupRequirement):
            def check_group(self, group):
                return [Invalid('foo')], 'my message'

        requirement = RequiredMapping({'a': MyRequirement()})
        diff, desc = requirement({'a': 1})  # <- Single-element value.
        expected = [
            ('a', Invalid('foo')),
        ]
        self.assertEqual(evaluate_items(diff), expected)
        self.assertEqual(desc, 'my message')

        requirement = RequiredMapping({'a': MyRequirement()})
        diff, desc = requirement({'a': [1, 2, 3]})  # <- List of values.
        expected = [
            ('a', [Invalid('foo')]),
        ]
        self.assertEqual(evaluate_items(diff), expected)
        self.assertEqual(desc, 'my message')

    def test_abstract_factory(self):
        """Test *abstract_factory* argument and method."""
        def custom_factory(value):
            if isinstance(value, str):
                return RequiredSet  # <- Treat str as set of characters.
            return None

        req_dict = {
            'A': 'xy',   # <- Passed to RequiredSet
            'B': 'xyz',  # <- Passed to RequiredSet
            'C': 123,    # <- Passed to RequiredPredicate (via auto-detect
                         #    when custom_factory() returns None)
        }
        requirement = RequiredMapping(req_dict, abstract_factory=custom_factory)

        data = {'A': ['x', 'y', 'y'], 'B': ['x', 'y'], 'C': [123, 123]}
        diff, desc = requirement(data)
        expected = [
            ('B', [Missing('z')]),
        ]
        self.assertEqual(evaluate_items(diff), expected)
        self.assertEqual(desc, 'does not satisfy set membership')

    def test_integration(self):
        requirement = RequiredMapping({
            'a': 'x',
            'b': 'y',
            'c': 1,
            'd': 2,
            'e': ('abc', int),
            'f': ('def', float),
            'g': set(['a']),
            'h': set(['d', 'e', 'f']),
            'i': [1],
            'j': [4, 5, 6],
        })

        # No differences.
        data = {
            'a': 'x',
            'b': ['y', 'y'],
            'c': 1,
            'd': iter([2, 2]),
            'e': ('abc', 1),
            'f': [('def', 1.0), ('def', 2.0)],
            'g': 'a',
            'h': ['d', 'e', 'f'],
            'i': 1,
            'j': [4, 5, 6],
        }
        self.assertIsNone(requirement(data))

        # Variety of differences.
        data = {
            'a': 'y',
            'b': ['x', 'y'],
            'c': 2,
            'd': [1, 2],
            'e': ('abc', 1.0),
            'f': [('def', 2)],
            'g': 'b',
            'h': ['e', 'f', 'g'],
            'i': 2,
            'j': [5, 6, 7],
        }
        diff, desc = requirement(data)

        expected = {
            'a': Invalid('y', expected='x'),
            'b': [Invalid('x')],
            'c': Deviation(+1, 1),
            'd': [Deviation(-1, 2)],
            'e': Invalid(('abc', 1.0), expected=('abc', int)),
            'f': [Invalid(('def', 2))],
            'g': [Missing('a'), Extra('b')],
            'h': [Missing('d'), Extra('g')],
            'i': [Missing((0, 1)), Extra((0, 2))],
            'j': [Missing((0, 4)), Extra((2, 7))],
        }
        self.assertEqual(dict(evaluate_items(diff)), expected)

    def test_description_message(self):
        # Test same message (set membership message).
        requirement = RequiredMapping({'a': set(['x']), 'b': set(['y'])})
        _, desc = requirement({'a': ['x', 'y'], 'b': ['y', 'z']})
        self.assertEqual(desc, 'does not satisfy set membership')

        # Test different messages--uses default instead.
        requirement = RequiredMapping({'a': set(['x']), 'b': 'y'})
        _, desc = requirement({'a': ['x', 'y'], 'b': ['y', 'z']})
        self.assertEqual(desc, 'does not satisfy mapping requirements')


class TestGetRequirement(unittest.TestCase):
    def test_set(self):
        requirement = get_requirement(set(['foo', 'bar', 'baz']))
        self.assertIsInstance(requirement, RequiredSet)

    def test_order(self):
        requirement = get_requirement(['foo', 'bar', 'baz'])
        self.assertIsInstance(requirement, RequiredOrder)

    def test_predicate(self):
        requirement = get_requirement(123)
        self.assertIsInstance(requirement, RequiredPredicate)

        requirement = get_requirement('foo')
        self.assertIsInstance(requirement, RequiredPredicate)

        requirement = get_requirement(('foo', 'bar', 'baz'))
        self.assertIsInstance(requirement, RequiredPredicate)

    def test_mapping(self):
        requirement = get_requirement({'foo': 1, 'bar': 2, 'baz': 3})
        self.assertIsInstance(requirement, RequiredMapping)

    def test_existing_requirement(self):
        existing_requirement = RequiredPredicate('foo')
        requirement = get_requirement(existing_requirement)
        self.assertIs(requirement, existing_requirement)


class TestRequiredUnique(unittest.TestCase):
    def setUp(self):
        self.requirement = RequiredUnique()

    def test_element_group(self):
        data = [1, 2, 3]
        self.assertIsNone(self.requirement(data))  # No duplicates.

        data = [1, 2, 2, 3, 3, 3]
        diff, desc = self.requirement(data)
        self.assertEqual(list(diff), [Extra(2), Extra(3), Extra(3)])
        self.assertRegex(desc, 'should be unique')

    def test_mapping_of_element_groups(self):
        data = {'a': [1, 2, 3], 'b': [1, 2, 3], 'c': [1, 2, 3]}
        self.assertIsNone(self.requirement(data))  # No duplicates.

        data = {'a': [1], 'b': [2, 2], 'c': [3, 3, 3]}
        diff, desc = self.requirement(data)
        expected = [
            ('b', [Extra(2)]),
            ('c', [Extra(3), Extra(3)]),
        ]
        self.assertEqual(evaluate_items(diff), expected)
        self.assertRegex(desc, 'should be unique')

    def test_single_element_handling(self):
        """RequiredUnique can not operate directly on base elements."""
        with self.assertRaises(ValueError):
            self.requirement((1, 2))

        with self.assertRaises(ValueError):
            self.requirement({'a': (1, 2)})


class TestRequiredSubset(unittest.TestCase):
    def test_element_group(self):
        data = [1, 2, 3]
        requirement = RequiredSubset(set([1, 2]))
        self.assertIsNone(requirement(data))

        data = [1, 2]
        requirement = RequiredSubset(set([1, 2, 3, 4]))
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Missing(3), Missing(4)])
        self.assertRegex(desc, 'must contain all')

    def test_data_mapping(self):
        requirement = RequiredSubset(set([1, 2, 3]))

        data = {'a': [1, 2, 3], 'b': [1, 2, 3], 'c': [1, 2, 3]}
        self.assertIsNone(requirement(data))

        data = {'a': [1, 2], 'b': [1, 2, 3], 'c': [1, 2, 3, 4]}
        diff, desc = requirement(data)
        expected = [
            ('a', [Missing(3)]),
        ]
        self.assertEqual(evaluate_items(diff), expected)
        self.assertRegex(desc, 'must contain all')

    def test_single_element_handling(self):
        requirement = RequiredSubset(set([1, 2]))

        diff, desc = requirement(1)
        self.assertEqual(list(diff), [Missing(2)])

        diff, desc = requirement((3, 4))  # <- Tuple is single element.
        diff = sorted(diff, key=lambda x: x.args)
        self.assertEqual(diff, [Missing(1), Missing(2)])


class TestRequiredSuperset(unittest.TestCase):
    def test_element_group(self):
        data = [1, 2]
        requirement = RequiredSuperset(set([1, 2, 3]))
        self.assertIsNone(requirement(data))

        data = [1, 2, 3, 4]
        requirement = RequiredSuperset(set([1, 2]))
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Extra(3), Extra(4)])
        self.assertRegex(desc, 'may contain only')

    def test_data_mapping(self):
        requirement = RequiredSuperset(set([1, 2, 3]))

        data = {'a': [1, 2, 3], 'b': [1, 2], 'c': [1]}
        self.assertIsNone(requirement(data))

        data = {'a': [1, 2], 'b': [1, 2, 3], 'c': [1, 2, 3, 4]}
        diff, desc = requirement(data)
        expected = [
            ('c', [Extra(4)]),
        ]
        self.assertEqual(evaluate_items(diff), expected)
        self.assertRegex(desc, 'may contain only')

    def test_single_element_handling(self):
        requirement = RequiredSuperset(set([1, 2]))

        diff, desc = requirement(3)
        self.assertEqual(list(diff), [Extra(3)])

        diff, desc = requirement((3, 4))  # <- Tuple is single element.
        diff = sorted(diff, key=lambda x: x.args)
        self.assertEqual(diff, [Extra((3, 4))])


class TestRequiredApprox(unittest.TestCase):
    def test_passing_default(self):
        requirement = RequiredApprox(10)

        data = [10.00000001, 10.00000002, 10.00000003]
        result = requirement(data)
        self.assertIsNone(result)  # True for all, returns None.

    def test_some_false(self):
        """Numeric differences beyond the approximate range should
        create Deviation differences.
        """
        requirement = RequiredApprox(10)

        # Using check_group() method internally.
        data = [10.00000001, 10.00000002, 9.5]
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Deviation(-0.5, 10)])
        self.assertEqual(desc, 'not equal within 7 decimal places')

        # Using check_group() method with single item.
        data = 9.5
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Deviation(-0.5, 10)])
        self.assertEqual(desc, 'not equal within 7 decimal places')

        # Using check_items() method internally.
        data = {'A': 10.00000001, 'B': 9.5, 'C': [9.5, 10.00000001]}
        diff, desc = requirement(data)
        expected = [
            ('B', Deviation(-0.5, 10)),
            ('C', [Deviation(-0.5, 10)]),
        ]
        self.assertEqual(evaluate_items(diff), expected)
        self.assertEqual(desc, 'not equal within 7 decimal places')

    def test_tuple_comparison(self):
        """Should work on numeric elements within tuples."""
        data = [(0.50390625, 'abc'), (0.4921875, 'abc'), (0.5, 'xyz')]

        requirement = RequiredApprox((0.5, 'abc'), places=2)
        diff, desc = requirement(data)

        self.assertEqual(list(diff), [Invalid((0.4921875, 'abc')), Invalid((0.5, 'xyz'))])
        self.assertEqual(desc, 'not equal within 2 decimal places')

    def test_specified_places(self):
        requirement = RequiredApprox(0.5, places=2)

        data = [0.50390625, 0.49609375, 0.4921875]

        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Deviation(-0.0078125, 0.5)])
        self.assertEqual(desc, 'not equal within 2 decimal places')

    def test_specified_delta(self):
        requirement = RequiredApprox(10, delta=3)

        data = [10, 7, 13, 13.0625]
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Deviation(+3.0625, 10)])
        self.assertEqual(desc, 'not equal within delta of 3')

    def test_nonnumeric_data(self):
        """Non-numeric differences should create Invalid() differences."""
        requirement = RequiredApprox(10)

        data = [10.00000001, 10.00000002, 'abc']

        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Invalid('abc')])
        self.assertEqual(desc, 'not equal within 7 decimal places')

    def test_show_expected(self):
        requirement = RequiredApprox(10, show_expected=True)

        data = [10.00000001, 10.00000002, 'abc']

        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Invalid('abc', expected=10)])
        self.assertEqual(desc, 'not equal within 7 decimal places')

    def test_duplicate_false(self):
        """Should return one difference for every false result (including
        duplicates).
        """
        requirement = RequiredApprox(10)

        data = [10.00000001, 9.5, 9.5]  # <- Multiple 9.5's.

        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Deviation(-0.5, 10), Deviation(-0.5, 10)])
        self.assertEqual(desc, 'not equal within 7 decimal places')

    def test_empty_iterable(self):
        requirement = RequiredApprox(10)
        result = requirement([])
        self.assertIsNone(result)

    def test_nonnumeric_baseelement(self):
        """Non-numeric base elements should have normal predicate behavior."""
        requirement = RequiredApprox('abc')

        self.assertIsNone(requirement('abc'))

        diff, desc = requirement('xxx')
        self.assertEqual(list(diff), [Invalid('xxx')])

    def test_notfound_token(self):
        data = [10.00000001, NOTFOUND]
        requirement = RequiredApprox(10)
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Deviation(-10, 10)])
        self.assertEqual(desc, 'not equal within 7 decimal places')


class TestRequiredOutliers(unittest.TestCase):
    def test_passing(self):
        data = [12, 5, 8, 5, 7, 15]
        requirement = RequiredOutliers(data)
        result = requirement(data)
        self.assertIsNone(result)  # True for all, returns None.

    def test_failing_group(self):
        data = [12, 5, 8, 37, 5, 7, 15]  # <- 37 is an outlier
        requirement = RequiredOutliers(data)
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Deviation(+2.1875, 34.8125)])

    def test_zero_or_one_value(self):
        data = []  # <- Zero values.
        requirement = RequiredOutliers(data)
        result = requirement(data)
        self.assertIsNone(result)  # Can have no outliers.

        data = [42]  # <- One value.
        requirement = RequiredOutliers(data)
        result = requirement(data)
        self.assertIsNone(result)  # Can have no outliers.

    def test_nonnumeric_requirement(self):
        requirement = [12, 5, 8, 'abc', 5, 7, 15]  # <- 'abc' not valid input
        with self.assertRaises(TypeError):
            RequiredOutliers(requirement)

    def test_nonnumeric_data(self):
        requirement = RequiredOutliers([12, 5, 8, 5, 7, 15])
        data = [12, 5, 8, 'abc', 5, 7, 15]  # <- 'abc' not comparable
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Invalid('abc')])

    def test_failing_mapping(self):
        data = {
            'A': [12, 5, 8, 37, 5, 7, 15],  # <- 37 is an outlier
            'B': [83, 75, 78, 50, 76, 89],  # <- 50 is an outlier
        }
        requirement = RequiredOutliers(data)

        diff, desc = requirement(data)
        expected = [
            ('A', [Deviation(+2.1875, 34.8125)]),
            ('B', [Deviation(-7.375, 57.375)]),
        ]
        self.assertEqual(evaluate_items(diff), expected)


class TestRequiredFuzzy(unittest.TestCase):
    def test_all_true(self):
        data = iter(['abx', 'aby', 'abz'])
        requirement = RequiredFuzzy('abc')
        result = requirement(data)
        self.assertIsNone(result)  # True for all elements, returns None.

    def test_some_false(self):
        """When the fuzzy predicate returns False, values should be
        returned as Invalid() differences.
        """
        data = ['abx', 'aby', 'xyz']

        requirement = RequiredFuzzy('abc')
        diff, desc = requirement(data)

        self.assertEqual(list(diff), [Invalid('xyz')])
        self.assertEqual(desc, "does not satisfy 'abc', fuzzy matching at ratio 0.6 or greater")

    def test_cutoff(self):
        data = ['aaaaa', 'aaaax', 'aaaxx', 'xxxxx']

        requirement = RequiredFuzzy('aaaaa', cutoff=0.6)
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Invalid('xxxxx')])
        self.assertEqual(desc, "does not satisfy 'aaaaa', fuzzy matching at ratio 0.6 or greater")

        requirement = RequiredFuzzy('aaaaa', cutoff=0.8)
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Invalid('aaaxx'), Invalid('xxxxx')])
        self.assertEqual(desc, "does not satisfy 'aaaaa', fuzzy matching at ratio 0.8 or greater")

    def test_tuple_comparison(self):
        """Should work on string elements within tuples."""
        data = [(1, 'abx'), (2, 'abx'), (1, 'xyz')]

        requirement = RequiredFuzzy((1, 'abc'))
        diff, desc = requirement(data)

        self.assertEqual(list(diff), [Invalid((2, 'abx')), Invalid((1, 'xyz'))])
        self.assertEqual(desc, "does not satisfy (1, 'abc'), fuzzy matching at ratio 0.6 or greater")

    def test_show_expected(self):
        data = ['abx', 'aby', 'xyz']

        requirement = RequiredFuzzy('abc', show_expected=True)
        diff, desc = requirement(data)

        self.assertEqual(list(diff), [Invalid('xyz', expected='abc')])
        self.assertEqual(desc, "does not satisfy 'abc', fuzzy matching at ratio 0.6 or greater")

    def test_empty_iterable(self):
        requirement = RequiredFuzzy('abc')
        result = requirement([])
        self.assertIsNone(result)

    def test_nonstring_value(self):
        """When the RequiredFuzzy is given non-string values, the normal
        predicate differences should be returned (e.g., Deviation, for
        numeric comparisons).
        """
        data = [10, 10, 12]
        requirement = RequiredFuzzy(10)

        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Deviation(+2, 10)])
        self.assertEqual(desc, 'does not satisfy 10, fuzzy matching at ratio 0.6 or greater')

    def test_notfound_token(self):
        data = [123, 'abc']
        requirement = RequiredFuzzy(NOTFOUND)
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Deviation(+123, None), Extra('abc')])

        data = [10, NOTFOUND]
        requirement = RequiredFuzzy(10)
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Deviation(-10, 10)])
        self.assertEqual(desc, 'does not satisfy 10, fuzzy matching at ratio 0.6 or greater')

        data = ['abc', NOTFOUND]
        requirement = RequiredFuzzy('abc')
        diff, desc = requirement(data)
        self.assertEqual(list(diff), [Missing('abc')])
        self.assertEqual(desc, "does not satisfy 'abc', fuzzy matching at ratio 0.6 or greater")

    def test_items(self):
        requirement = RequiredFuzzy('abc')

        data = {'A': ['abx', 'abx', 'xxx'], 'B': 'abc', 'C': 'yyy'}
        diff, desc = requirement(data)
        expected = [
            ('A', [Invalid('xxx')]),
            ('C', Invalid('yyy')),
        ]
        self.assertEqual(evaluate_items(diff), expected)
