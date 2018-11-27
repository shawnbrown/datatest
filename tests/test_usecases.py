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
        datatest.validate2(a.fieldnames, set(a.fieldnames))

        # A case we want to optimize.
        with datatest.allowed.specific(datatest.Extra('C')):
            datatest.validate2(a.fieldnames, set(b.fieldnames))

    def test_compare_rows(self):
        """Should be able to compare rows by calling a selector by
        its own fieldnames.
        """
        a = self.selector_a
        b = self.selector_b

        # A case we want to optimize.
        datatest.validate2(a(a.fieldnames), a(a.fieldnames))

        # A case we want to optimize (using ordered intersection of fieldnames).
        common_fields = tuple(x for x in a.fieldnames if x in b.fieldnames)
        datatest.validate2(a(common_fields), b(common_fields))


class TestValidateIdioms(unittest.TestCase):
    def test_concise_reference_testing(self):
        """Should be able to use a two-item ProxyGroup to easily
        compare results by unpacking the ProxyGroup directly in to
        the validate() function call.
        """
        compare = datatest.ProxyGroup(['foo', 'FOO'])
        datatest.validate2(*compare.lower())

    def test_mappings_of_sequences(self):
        """Should be able to compare mappings of sequences and
        allow differences across keys (e.g., with allowed.extra()
        and allowed.missing()).
        """
        # Pull objects into local name space to improve readability.
        validate = datatest.validation.validate2
        allowed = datatest.allowed
        ValidationError = datatest.ValidationError
        Missing = datatest.Missing
        Extra = datatest.Extra

        requirement = ['a', 'b', 'c']

        data = {
            'foo': ['a', 'x', 'c'],       # -> [Missing((1, 'b')), Extra((1, 'x'))]
            'bar': ['a', 'b'],            # -> [Missing((2, 'c'))]
            'baz': ['a', 'b', 'c', 'd'],  # -> [Extra((3, 'd'))]
        }

        expected_extras = allowed.specific({
            'foo': [Extra((1, 'x'))],
            'baz': [Extra((3, 'd'))],
        })
        with allowed.missing() | expected_extras:
            validate(data, requirement)
