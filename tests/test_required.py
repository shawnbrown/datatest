# -*- coding: utf-8 -*-
from __future__ import absolute_import
from . import _unittest as unittest
from datatest import Missing
from datatest import Extra
from datatest import Deviation
from datatest import Invalid
from datatest._predicate import Predicate
from datatest._required import FailureInfo
from datatest._required import Required
from datatest._required import RequiredPredicate
from datatest._required import RequiredSet
from datatest._required import RequiredSequence


class TestFailureInfo(unittest.TestCase):
    def test_init(self):
        differences = [Missing(1)]
        message = 'failure message'

        # Standard initialization.
        info = FailureInfo(differences, message)
        self.assertEqual(list(info.differences), differences)
        self.assertEqual(info.message, message)

        # Default message.
        info = FailureInfo(differences)  # <- No message provided.
        self.assertEqual(list(info.differences), differences)
        self.assertEqual(info.message, 'does not satisfy requirement')

        # A single difference, not wrapped in container.
        info = FailureInfo(Missing(1))
        self.assertEqual(list(info.differences), [Missing(1)])

        # Bad argument type.
        with self.assertRaisesRegex(TypeError, 'should be a non-string iterable'):
            FailureInfo(123)

        # Iterator of differences (consumable).
        iterator = iter(differences)
        info = FailureInfo(iterator, message)
        self.assertEqual(list(info.differences), differences)
        self.assertEqual(info.message, message)

    def test_wrap_differences(self):
        diffs = [Missing(1), Missing(2), Missing(3)]
        wrapped = FailureInfo._wrap_differences(diffs)
        msg = 'yielding difference objects should work without issue'
        self.assertEqual(list(wrapped), diffs, msg=msg)

        diffs = [Missing(1), Missing(2), 123]
        wrapped = FailureInfo._wrap_differences(diffs)
        msg = 'yielding a non-difference object should fail with a useful message'
        with self.assertRaisesRegex(TypeError, 'must contain difference objects', msg=msg):
            list(wrapped)  # <- Fully evaluate generator.

    def test_empty_attribute(self):
        info = FailureInfo([Missing(1)], 'failure message')
        self.assertFalse(info.empty)

        info = FailureInfo([], 'failure message')
        self.assertTrue(info.empty)

        info = FailureInfo([Missing(1)], 'failure message')
        with self.assertRaises(AttributeError, msg='should be read only'):
            info.empty = False


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
