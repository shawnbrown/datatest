# -*- coding: utf-8 -*-
"""A handful of integration tests to check for idiomatic use cases
that we want make sure are as convinient as possible for users.
"""
from . import _unittest as unittest
import datatest


class TestSelectorIdioms(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.selector_a = datatest.Selector([
            ['A', 'B', 'C'],
            ['x', 1, 100],
            ['y', 2, 200],
            ['z', 3, 300],
        ])
        cls.selector_b = datatest.Selector([
            ['A', 'B'],
            ['x', 1],
            ['y', 2],
            ['z', 3],
        ])

    def setUp(self):
        if not hasattr(unittest.TestCase, 'setUpClass'):
            self.setUpClass()  # setUpClass() is new in Python 2.7 and 3.2

    def test_compare_fieldnames(self):
        """Should be able to compare ``fieldnames`` between Selectors
        by simply casting the *requirement* as a set and comparing it
        directly against the ``fieldnames`` parameter of the other
        Selector.
        """
        a = self.selector_a
        b = self.selector_b

        # A case we want to optimize.
        datatest.validate(a.fieldnames, set(a.fieldnames))

        # A case we want to optimize.
        with datatest.allowed.specific(datatest.Extra('C')):
            datatest.validate(a.fieldnames, set(b.fieldnames))

    def test_compare_rows(self):
        """Should be able to compare rows by calling a selector by
        its own fieldnames.
        """
        a = self.selector_a
        b = self.selector_b

        # A case we want to optimize.
        datatest.validate(a(a.fieldnames), a(a.fieldnames))

        # A case we want to optimize (using ordered intersection of fieldnames).
        common_fields = tuple(x for x in a.fieldnames if x in b.fieldnames)
        datatest.validate(a(common_fields), b(common_fields))

    def test_concise_reference_testing(self):
        """Should be able to use grouping object to query and then compare
        the results with sequence unpacking.
        """
        compare = datatest.ProxyGroup([self.selector_a, self.selector_b])
        datatest.validate(*compare({'A': 'B'}))


class TestSpecialPredicateHandling(unittest.TestCase):
    def test_returned_difference(self):
        """When the Predicate class wraps a callable object
        the resut should be considered false if the callable
        returns a difference object.

        NOTE: This test is located in this file to make sure that the
        behavior is not reverted--if we ever re-vendor the predicate
        sub-module with a newer version, we need to make sure that
        this use case is not forgotten about.
        """
        def true_or_difference(x):
            return x == 'foo' or datatest.Missing(x)

        predicate = datatest._predicate.Predicate(true_or_difference)
        self.assertTrue(predicate('foo'))
        self.assertFalse(predicate('bar'))
