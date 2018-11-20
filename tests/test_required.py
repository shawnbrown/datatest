# -*- coding: utf-8 -*-
from __future__ import absolute_import
from . import _unittest as unittest
from datatest._compatibility.collections.abc import Iterator
from datatest import Missing
from datatest import Extra
from datatest import Deviation
from datatest import Invalid
from datatest._predicate import Predicate
from datatest._required import FailureInfo
from datatest._required import _wrap_differences
from datatest._required import group_requirement
from datatest._required import required_set
from datatest._required import Required
from datatest._required import RequiredPredicate
from datatest._required import RequiredSet
from datatest._required import RequiredSequence


class TestFailureInfo(unittest.TestCase):
    def test_iterator(self):
        msg = 'should be iterator'
        failure_info = FailureInfo([Missing(1)])
        self.assertIsInstance(failure_info, Iterator)

        msg = 'when iterated over, should return same differences'
        differences = [Missing(1), Missing(2)]
        failure_info = FailureInfo(differences)
        self.assertEqual(list(failure_info), differences)

        msg = 'single difference should be wrapped as a single-item iterator'
        info = FailureInfo(Missing(1))
        self.assertEqual(list(info), [Missing(1)], msg=msg)

    def test_message(self):
        failure_info = FailureInfo([Missing(1)])  # <- No message, uses default.
        self.assertEqual(failure_info.message, 'does not satisfy requirement')

        custom_message = 'custom failure message'
        failure_info = FailureInfo([Missing(1)], custom_message)
        self.assertEqual(failure_info.message, custom_message)

    def test_bad_argument(self):
        with self.assertRaisesRegex(TypeError, 'should be a non-string iterable'):
            FailureInfo('abc')

    def test_type_check_message(self):
        failure_info = FailureInfo([Missing(1), Missing(2), 123])
        msg = 'yielding a non-difference object should fail with a useful message'
        with self.assertRaisesRegex(TypeError, 'must contain difference objects', msg=msg):
            list(failure_info)  # <- Fully evaluate iterator.

    def test_empty_attr(self):
        failure_info = FailureInfo([Missing(1)])
        self.assertFalse(failure_info.empty)

        failure_info = FailureInfo(iter([]))
        self.assertTrue(failure_info.empty)

        failure_info = FailureInfo([Missing(1)])
        self.assertFalse(failure_info.empty)
        list(failure_info)
        self.assertTrue(failure_info.empty, msg='if exhausted, should become True')

        failure_info = FailureInfo([Missing(1)], 'failure message')
        with self.assertRaises(AttributeError, msg='should be read only'):
            failure_info.empty = False


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
        self.assertEqual(desc, 'does not satisfy requirement', msg='default description')

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
        self.assertEqual(desc, 'does not satisfy requirement')

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


class TestRequiredSet2(unittest.TestCase):
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


class TestRequirement(unittest.TestCase):
    def test_incomplete_subclass(self):
        """Instantiation should fail if abstract members are not defined."""
        class IncompleteSubclass(Required):
            pass

        regex = "Can't instantiate abstract class"
        with self.assertRaisesRegex(TypeError, regex):
            requirement = IncompleteSubclass()

    def test_bad_filterfalse(self):
        """Should raise error if filterfalse() does not return an iterable
        of differences.
        """
        class BadFilterfalse(Required):
            @property
            def msg(self):
                return 'requirement message'

            def filterfalse(self, iterable):
                return [
                    Invalid('abc'),
                    Invalid('def'),
                    'ghi',  # <- Not a difference object!
                ]

        requirement = BadFilterfalse()

        regex = 'must contain difference objects'
        with self.assertRaisesRegex(TypeError, regex):
            result = requirement([])
            list(result)

    def test_simple_subclass(self):
        """Test basic subclass behavior."""
        class RequiredValue(Required):
            def __init__(self, value):
                self.value = value

            @property
            def msg(self):
                return 'require {0!r}'.format(self.value)

            def filterfalse(self, iterable):
                return (Invalid(x) for x in iterable if x != self.value)

        requirement = RequiredValue('abc')

        result = requirement(['abc', 'def', 'ghi'])
        self.assertEqual(list(result), [Invalid('def'), Invalid('ghi')])

        result = requirement(['abc', 'abc', 'abc'])
        self.assertIsNone(result)


class TestRequiredPredicate(unittest.TestCase):
    def setUp(self):
        isdigit = lambda x: x.isdigit()
        self.requirement = RequiredPredicate(isdigit)

    def test_all_true(self):
        data = iter(['10', '20', '30'])
        result = self.requirement(data)
        self.assertIsNone(result)  # Predicat is true for all, returns None.

    def test_some_false(self):
        """When the predicate returns False, values should be returned as
        Invalid() differences.
        """
        data = ['10', '20', 'XX']
        result = self.requirement(data)
        self.assertEqual(list(result), [Invalid('XX')])

    def test_show_expected(self):
        data = ['XX', 'YY']
        requirement = RequiredPredicate('YY')
        result = requirement(data, show_expected=True)
        self.assertEqual(list(result), [Invalid('XX', expected='YY')])

    def test_duplicate_false(self):
        """Should return one difference for every false result (including
        duplicates).
        """
        data = ['10', '20', 'XX', 'XX', 'XX']  # <- Multiple XX's.
        result = self.requirement(data)
        self.assertEqual(list(result), [Invalid('XX'), Invalid('XX'), Invalid('XX')])

    def test_empty_iterable(self):
        result = self.requirement([])
        self.assertIsNone(result)

    def test_some_false_deviations(self):
        """When the predicate returns False, values should be returned as
        Invalid() differences.
        """
        data = [10, 10, 12]
        requirement = RequiredPredicate(10)

        result = requirement(data)
        self.assertEqual(list(result), [Deviation(+2, 10)])

    def test_predicate_error(self):
        """Errors should not be counted as False or otherwise hidden."""
        data = ['10', '20', 'XX', 40]  # <- Predicate assumes string, int has no isdigit().
        result = self.requirement(data)
        with self.assertRaisesRegex(AttributeError, "no attribute 'isdigit'"):
            list(result)

    def test_predicate_class(self):
        """The "predicate" property should be a proper Predicate class,
        not simply a function.
        """
        isdigit = lambda x: x.isdigit()

        requirement = RequiredPredicate(isdigit)
        self.assertIsInstance(requirement.predicate, Predicate)

        requirement = RequiredPredicate(Predicate(isdigit))
        self.assertIsInstance(requirement.predicate, Predicate)

    def test_returned_difference(self):
        """When a predicate returns a difference object, it should used in
        place of the default Invalid difference.
        """
        def func(x):
            if 1 <= x <= 3:
                return True
            if x == 4:
                return Invalid('four shalt thou not count')
            if x == 5:
                return Invalid('five is right out')
            return False

        requirement = RequiredPredicate(func)

        data = [1, 2, 3, 4, 5, 6]
        result = requirement(data)
        expected = [
            Invalid('four shalt thou not count'),
            Invalid('five is right out'),
            Invalid(6),
        ]
        self.assertEqual(list(result), expected)


class TestRequiredSet(unittest.TestCase):
    def setUp(self):
        self.required = RequiredSet(set([1, 2, 3]))

    def test_no_difference(self):
        data = iter([1, 2, 3])
        result = self.required(data)
        self.assertIsNone(result)  # No difference, returns None.

    def test_missing(self):
        data = iter([1, 2])
        result = self.required(data)
        self.assertEqual(list(result), [Missing(3)])

    def test_extra(self):
        data = iter([1, 2, 3, 4])
        result = self.required(data)
        self.assertEqual(list(result), [Extra(4)])

    def test_repeat_values(self):
        """Repeat values should not result in duplicate differences."""
        data = iter([1, 2, 3, 4, 4, 4])  # <- Multiple 4's.
        result = self.required(data)
        self.assertEqual(list(result), [Extra(4)])

    def test_missing_and_extra(self):
        data = iter([1, 3, 4])
        result = self.required(data)

        result = list(result)
        self.assertEqual(len(result), 2)
        self.assertIn(Missing(2), result)
        self.assertIn(Extra(4), result)

    def test_empty_iterable(self):
        required = RequiredSet(set([1]))
        result = required([])
        self.assertEqual(list(result), [Missing(1)])


class TestRequiredSequence(unittest.TestCase):
    def test_no_difference(self):
        data = ['aaa', 'bbb', 'ccc']
        required = RequiredSequence(['aaa', 'bbb', 'ccc'])
        self.assertIsNone(required(data))  # No difference, returns None.

    def test_some_missing(self):
        data = ['bbb', 'ddd']
        required = RequiredSequence(['aaa', 'bbb', 'ccc', 'ddd', 'eee'])
        result = required(data)
        expected = [
            Missing((0, 'aaa')),
            Missing((1, 'ccc')),
            Missing((2, 'eee')),
        ]
        self.assertEqual(list(result), expected)

    def test_all_missing(self):
        data = []  # <- Empty!
        required = RequiredSequence(['aaa', 'bbb'])
        result = required(data)
        expected = [
            Missing((0, 'aaa')),
            Missing((0, 'bbb')),
        ]
        self.assertEqual(list(result), expected)

    def test_some_extra(self):
        data = ['aaa', 'bbb', 'ccc', 'ddd', 'eee', 'fff']
        required = RequiredSequence(['aaa', 'bbb', 'ccc'])
        result = required(data)
        expected = [
            Extra((3, 'ddd')),
            Extra((4, 'eee')),
            Extra((5, 'fff')),
        ]
        self.assertEqual(list(result), expected)

    def test_all_extra(self):
        data = ['aaa', 'bbb']
        required = RequiredSequence([])  # <- Empty!
        result = required(data)
        expected = [
            Extra((0, 'aaa')),
            Extra((1, 'bbb')),
        ]
        self.assertEqual(list(result), expected)

    def test_one_missing_and_extra(self):
        data = ['aaa', 'xxx', 'ccc']
        required = RequiredSequence(['aaa', 'bbb', 'ccc'])
        result = required(data)
        expected = [
            Missing((1, 'bbb')),
            Extra((1, 'xxx')),
        ]
        self.assertEqual(list(result), expected)

    def test_some_missing_and_extra(self):
        data = ['aaa', 'xxx', 'ccc', 'yyy', 'zzz']
        required = RequiredSequence(['aaa', 'bbb', 'ccc', 'ddd', 'eee'])
        result = required(data)
        expected = [
            Missing((1, 'bbb')),
            Extra((1, 'xxx')),
            Missing((3, 'ddd')),
            Extra((3, 'yyy')),
            Missing((4, 'eee')),
            Extra((4, 'zzz')),
        ]
        self.assertEqual(list(result), expected)

    def test_some_missing_and_extra_different_lengths(self):
        data = ['aaa', 'xxx', 'eee']
        required = RequiredSequence(['aaa', 'bbb', 'ccc', 'ddd', 'eee'])
        result = required(data)
        expected = [
            Missing((1, 'bbb')),
            Extra((1, 'xxx')),
            Missing((2, 'ccc')),
            Missing((2, 'ddd')),
        ]
        self.assertEqual(list(result), expected)

        data = ['aaa', 'xxx', 'yyy', 'zzz', 'ccc']
        required = RequiredSequence(['aaa', 'bbb', 'ccc'])
        result = required(data)
        expected = [
            Missing((1, 'bbb')),
            Extra((1, 'xxx')),
            Extra((2, 'yyy')),
            Extra((3, 'zzz')),
        ]
        self.assertEqual(list(result), expected)

    def test_numeric_matching(self):
        """When checking sequence order, numeric differences should NOT
        be converted into Deviation objects.
        """
        data = [1, 100, 4, 200, 300]
        required = RequiredSequence([1, 2, 3, 4, 5])
        result = required(data)
        expected = [
            Missing((1, 2)),
            Extra((1, 100)),
            Missing((2, 3)),
            Missing((3, 5)),
            Extra((3, 200)),
            Extra((4, 300)),
        ]
        self.assertEqual(list(result), expected)

    def test_unhashable_objects(self):
        """Should try to compare sequences of unhashable types."""
        data = [{'a': 1}, {'b': 2}, {'c': 3}]
        required = RequiredSequence([{'a': 1}, {'b': 2}, {'c': 3}])
        result = required(data)
        self.assertIsNone(result)  # No difference, returns None.

        data = [{'a': 1}, {'x': 0}, {'d': 4}, {'y': 5}, {'g': 7}]
        required = RequiredSequence([{'a': 1}, {'b': 2}, {'c': 3}, {'d': 4}, {'f': 6}])
        result = required(data)
        expected = [
            Missing((1, {'b': 2})),
            Extra((1, {'x': 0})),
            Missing((2, {'c': 3})),
            Missing((3, {'f': 6})),
            Extra((3, {'y': 5})),
            Extra((4, {'g': 7})),
        ]
        self.assertEqual(list(result), expected)
