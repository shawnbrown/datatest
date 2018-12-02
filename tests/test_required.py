# -*- coding: utf-8 -*-
from __future__ import absolute_import
from . import _unittest as unittest
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


class TestGroupRequirement(unittest.TestCase):
    def test_group_requirement_flag(self):
        def func(iterable):
            return [Missing(1)], 'error message'

        self.assertFalse(hasattr(func, '_group_requirement'))

        func = group_requirement(func)  # <- Apply decorator.
        self.assertTrue(hasattr(func, '_group_requirement'))
        self.assertTrue(func._group_requirement)

    def test_iter_and_description(self):
        @group_requirement
        def func(iterable):
            return [Missing(1)], 'error message'  # <- Returns iterable and description.

        diffs, desc = func([1, 2, 3])
        self.assertEqual(list(diffs), [Missing(1)])
        self.assertEqual(desc, 'error message')

    def test_iter_alone(self):
        @group_requirement
        def func(iterable):
            return [Missing(1)]  # <- Returns iterable only, no description.

        diffs, desc = func([1, 2, 3])
        self.assertEqual(list(diffs), [Missing(1)])
        self.assertIsNone(desc)

    def test_tuple_of_diffs(self):
        """Should not mistake a 2-tuple of difference objects for a
        2-tuple containing an iterable of differences with a string
        description.
        """
        @group_requirement
        def func(iterable):
            return (Missing(1), Missing(2))  # <- Returns 2-tuple of diffs.

        diffs, desc = func([1, 2, 3])
        self.assertEqual(list(diffs), [Missing(1), Missing(2)])
        self.assertIsNone(desc)

    def test_empty_iter(self):
        """Empty iterable result should be converted to None."""
        @group_requirement
        def func(iterable):
            return iter([]), 'error message'  # <- Empty iterable and description.
        self.assertIsNone(func([1, 2, 3]))

        @group_requirement
        def func(iterable):
            return iter([])  # <- Empty iterable.
        self.assertIsNone(func([1, 2, 3]))

    def test_bad_types(self):
        """Bad return types should trigger TypeError."""
        with self.assertRaisesRegex(TypeError, 'should return .* iterable'):
            @group_requirement
            def func(iterable):
                return Missing(1), 'error message'
            func([1, 2, 3])

        with self.assertRaisesRegex(TypeError, 'should return .* iterable'):
            @group_requirement
            def func(iterable):
                return None  # <- Returns None
            func([1, 2, 3])

        with self.assertRaisesRegex(TypeError, 'should return .* an iterable and a string'):
            @group_requirement
            def func(iterable):
                return None, 'error message'  # <- Returns None and description.
            func([1, 2, 3])

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
        """When the predicate returns False, values should be returned as
        Invalid() differences.
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
