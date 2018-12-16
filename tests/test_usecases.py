# -*- coding: utf-8 -*-
"""A handful of integration tests to check for idiomatic use cases
that we want make sure are as convinient as possible for users.
"""
from . import _unittest as unittest
import datatest


class TestNamespaces(unittest.TestCase):
    def test_root_namespace(self):
        """Make sure important objects are in root namespace
        for easy access.
        """
        # Core objects.
        self.assertTrue(hasattr(datatest, 'validate'))
        self.assertTrue(hasattr(datatest, 'allowed'))
        self.assertTrue(hasattr(datatest, 'group_requirement'))

        # Error and difference objects.
        self.assertTrue(hasattr(datatest, 'ValidationError'))
        self.assertTrue(hasattr(datatest, 'Missing'))
        self.assertTrue(hasattr(datatest, 'Extra'))
        self.assertTrue(hasattr(datatest, 'Deviation'))
        self.assertTrue(hasattr(datatest, 'Invalid'))

        # Data handling support.
        self.assertTrue(hasattr(datatest, 'working_directory'))
        self.assertTrue(hasattr(datatest, 'get_reader'))
        self.assertTrue(hasattr(datatest, 'Selector'))
        self.assertTrue(hasattr(datatest, 'ProxyGroup'))

        # Unittest-style support.
        self.assertTrue(hasattr(datatest, 'DataTestCase'))
        self.assertTrue(hasattr(datatest, 'main'))
        self.assertTrue(hasattr(datatest, 'mandatory'))
        self.assertTrue(hasattr(datatest, 'skip'))
        self.assertTrue(hasattr(datatest, 'skipIf'))
        self.assertTrue(hasattr(datatest, 'skipUnless'))


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


class TestValidateIdioms(unittest.TestCase):
    def test_concise_reference_testing(self):
        """Should be able to use a two-item ProxyGroup to easily
        compare results by unpacking the ProxyGroup directly in to
        the validate() function call.
        """
        compare = datatest.ProxyGroup(['foo', 'FOO'])
        datatest.validate(*compare.lower())

    def test_mappings_of_sequences(self):
        """Should be able to compare mappings of sequences and
        allow differences across keys (e.g., with allowed.extra()
        and allowed.missing()).
        """
        # Pull objects into local name space to improve readability.
        validate = datatest.validation.validate
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
