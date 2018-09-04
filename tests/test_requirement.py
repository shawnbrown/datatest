# -*- coding: utf-8 -*-
from __future__ import absolute_import
from . import _unittest as unittest
from datatest import Missing
from datatest import Extra
from datatest import Invalid
from datatest._requirement import Requirement
from datatest._requirement import SetRequirement


class TestRequirement(unittest.TestCase):
    def test_incomplete_subclass(self):
        """Instantiation should fail if abstract members are not defined."""
        class IncompleteSubclass(Requirement):
            pass

        regex = "Can't instantiate abstract class"
        with self.assertRaisesRegex(TypeError, regex):
            requirement = IncompleteSubclass()

    def test_bad_filterfalse(self):
        """Should raise error if filterfalse() does not return an iterable
        of differences.
        """
        class BadFilterfalse(Requirement):
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
        class RequiredValue(Requirement):
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


class TestSetRequirement(unittest.TestCase):
    def setUp(self):
        self.requirement = SetRequirement(set([1, 2, 3]))

    def test_no_difference(self):
        data = iter([1, 2, 3])
        result = self.requirement(data)
        self.assertIsNone(result)  # No difference, returns None.

    def test_missing(self):
        data = iter([1, 2])
        result = self.requirement(data)
        self.assertEqual(list(result), [Missing(3)])

    def test_extra(self):
        data = iter([1, 2, 3, 4])
        result = self.requirement(data)
        self.assertEqual(list(result), [Extra(4)])

    def test_repeat_values(self):
        """Repeat values should not result in duplicate differences."""
        data = iter([1, 2, 3, 4, 4, 4])  # <- Multiple 4's.
        result = self.requirement(data)
        self.assertEqual(list(result), [Extra(4)])

    def test_missing_and_extra(self):
        data = iter([1, 3, 4])
        result = self.requirement(data)

        result = list(result)
        self.assertEqual(len(result), 2)
        self.assertIn(Missing(2), result)
        self.assertIn(Extra(4), result)

    def test_empty_iterable(self):
        requirement = SetRequirement(set([1]))
        result = requirement([])
        self.assertEqual(list(result), [Missing(1)])
