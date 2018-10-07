# -*- coding: utf-8 -*-
from __future__ import absolute_import
from . import _unittest as unittest
from datatest import Missing
from datatest import Extra
from datatest import Deviation
from datatest import Invalid
from datatest._predicate import Predicate
from datatest._required import Required
from datatest._required import RequiredPredicate
from datatest._required import RequiredSet


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
