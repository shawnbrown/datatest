# -*- coding: utf-8 -*-
"""A handful of integration tests to check for idiomatic use cases
that we want make sure are as convinient as possible for users.
"""
from . import _unittest as unittest
import math
import datatest

try:
    import squint
except ImportError:
    squint = None

try:
    import pandas
except ImportError:
    pandas = None

try:
    import numpy
except ImportError:
    numpy = None

# Remove for datatest version 0.9.8.
import warnings
warnings.filterwarnings('ignore', message='subset and superset warning')


class TestNamespaces(unittest.TestCase):
    def test_root_namespace(self):
        """Make sure important objects are in root namespace
        for easy access.
        """
        # Core objects.
        self.assertTrue(hasattr(datatest, 'validate'))
        self.assertTrue(hasattr(datatest, 'accepted'))

        # Internal sub-module.
        self.assertTrue(hasattr(datatest, 'requirements'))

        # Error and difference objects.
        self.assertTrue(hasattr(datatest, 'ValidationError'))
        self.assertTrue(hasattr(datatest, 'Missing'))
        self.assertTrue(hasattr(datatest, 'Extra'))
        self.assertTrue(hasattr(datatest, 'Deviation'))
        self.assertTrue(hasattr(datatest, 'Invalid'))

        # Data handling support.
        self.assertTrue(hasattr(datatest, 'working_directory'))
        self.assertTrue(hasattr(datatest, 'get_reader'))
        self.assertTrue(hasattr(datatest, 'Select'))
        self.assertTrue(hasattr(datatest, 'RepeatingContainer'))

        # Unittest-style support.
        self.assertTrue(hasattr(datatest, 'DataTestCase'))
        self.assertTrue(hasattr(datatest, 'main'))
        self.assertTrue(hasattr(datatest, 'mandatory'))
        self.assertTrue(hasattr(datatest, 'skip'))
        self.assertTrue(hasattr(datatest, 'skipIf'))
        self.assertTrue(hasattr(datatest, 'skipUnless'))

    def test_pytest_flag(self):
        """Pytest should not try to rewrite the datatest module itself.

        If Pytest does try to rewrite datatest, it will give a warning
        in cases where datatest is imported before asserting rewriting
        begins. But there's no reason to rewrite datatest in the first
        place so pytest shouldn't even be trying this.

        See "PYTEST_DONT_REWRITE" in the Pytest documentation:

            https://docs.pytest.org/latest/reference.html
        """
        self.assertIn('PYTEST_DONT_REWRITE', datatest.__doc__)


@unittest.skipUnless(squint, 'requires squint')
class TestSquintIdioms(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.select_a = squint.Select([
            ['A', 'B', 'C'],
            ['x', 1, 100],
            ['y', 2, 200],
            ['z', 3, 300],
        ])
        cls.select_b = squint.Select([
            ['A', 'B'],
            ['x', 1],
            ['y', 2],
            ['z', 3],
        ])

    def setUp(self):
        if not hasattr(unittest.TestCase, 'setUpClass'):
            self.setUpClass()  # setUpClass() is new in Python 2.7 and 3.2

    def test_compare_fieldnames(self):
        """Should be able to compare ``fieldnames`` between Selects
        by simply casting the *requirement* as a set and comparing it
        directly against the ``fieldnames`` parameter of the other
        Select.
        """
        a = self.select_a
        b = self.select_b

        # A case we want to optimize.
        datatest.validate(a.fieldnames, set(a.fieldnames))

        # A case we want to optimize.
        with datatest.accepted(datatest.Extra('C')):
            datatest.validate(a.fieldnames, set(b.fieldnames))

    def test_compare_rows(self):
        """Should be able to compare rows by calling a Select using
        its own fieldnames.
        """
        a = self.select_a
        b = self.select_b

        # A case we want to optimize.
        datatest.validate(a(a.fieldnames), a(a.fieldnames))

        # A case we want to optimize (using ordered intersection of fieldnames).
        common_fields = tuple(x for x in a.fieldnames if x in b.fieldnames)
        datatest.validate(a(common_fields), b(common_fields))


class TestValidateIdioms(unittest.TestCase):
    def test_concise_reference_testing(self):
        """Should be able to use a two-item RepeatingContainer to
        easily compare results by unpacking the RepeatingContainer
        directly in to the validate() function call.
        """
        compare = datatest.RepeatingContainer(['foo', 'FOO'])
        datatest.validate(*compare.lower())

    def test_mapping_of_sequences_for_order(self):
        """Should be able to compare mapping of sequences for order and
        accept differences across keys (e.g., with accepted.extra() and
        accepted.missing()).
        """
        # Pull objects into local name space to improve readability.
        validate = datatest.validation.validate
        accepted = datatest.accepted
        ValidationError = datatest.ValidationError
        Missing = datatest.Missing
        Extra = datatest.Extra

        requirement = ['a', 'b', 'c']

        data = {
            'foo': ['a', 'x', 'c'],       # -> [Missing((1, 'b')), Extra((1, 'x'))]
            'bar': ['a', 'b'],            # -> [Missing((2, 'c'))]
            'baz': ['a', 'b', 'c', 'd'],  # -> [Extra((3, 'd'))]
        }

        expected_extras = accepted({
            'foo': [Extra((1, 'x'))],
            'baz': [Extra((3, 'd'))],
        })
        with accepted(Missing) | expected_extras:
            validate.order(data, requirement)

    def test_enumerate_to_dict(self):
        """Enumerations should be interpreted as mappings before validation."""
        validate = datatest.validate
        ValidationError = datatest.ValidationError
        Invalid = datatest.Invalid
        Missing = datatest.Missing

        with self.assertRaises(ValidationError) as cm:
            data = ['a', 'b', 'x', 'd']
            requirement = ['a', 'b', 'c', 'd', 'e']
            validate(enumerate(data), enumerate(requirement))

        differences = cm.exception.differences
        expected = {
            2: Invalid('x', expected='c'),
            4: Missing('e'),
        }
        self.assertEqual(differences, expected)


class TestNanHandling(unittest.TestCase):
    def test_accepting_builtin(self):
        data = ['a', 'a', 'b', 'b', float('nan')]

        with datatest.accepted(datatest.Invalid(float('nan'))):
            datatest.validate(data, str)

        with datatest.accepted(datatest.Extra(float('nan'))):
            datatest.validate(data, set(['a', 'b']))

        with datatest.accepted.args(float('nan')):
            datatest.validate(data, set(['a', 'b']))

    @unittest.skipUnless(pandas and numpy, 'requires pandas and numpy')
    def test_accepting_pandas_numpy(self):
        data = pandas.Series([1, 1, 2, 2, numpy.float64('nan')], dtype='float64')

        with datatest.accepted(datatest.Extra(numpy.float64('nan'))):
            datatest.validate(data, set([1.0, 2.0]))

        with datatest.accepted(datatest.Extra(numpy.nan)):
            datatest.validate(data, set([1.0, 2.0]))

        with datatest.accepted(datatest.Extra(float('nan'))):
            datatest.validate(data, set([1.0, 2.0]))

    def test_validating_builtin(self):
        """NaN values do not compare as equal, to use them for set membership
        or other types of validation, replace the NaN with a token that can
        be tested for equality, membership, etc.
        """
        nantoken = type(
            'nantoken',
            (object,),
            {'__repr__': (lambda x: '<nantoken>')},
        )()
        data = ['a', 'a', 'b', 'b', float('nan')]

        def nan_to_token(x):
            try:
                return nantoken if math.isnan(x) else x
            except TypeError:
                return x

        data = [nan_to_token(x) for x in data]
        datatest.validate.superset(data, set(['a', 'b', nantoken]))

    @unittest.skipUnless(pandas and numpy, 'requires pandas and numpy')
    def test_validating_pandas_numpy(self):
        # While the following example works for 'object' dtypes but
        # the pattern should be avoided because it is not reliable
        # when working with other dtypes. DO NOT use it in practice:
        #
        #    data = pandas.Series(['a', 'a', 'b', 'b', numpy.nan], dtype='object')
        #    datatest.validate.superset(data, set(['a', 'b', numpy.nan]))

        # A more reliable method is to replace NaNs with a token value.
        data = pandas.Series([1, 1, 2, 2, numpy.float64('nan')], dtype='float64')

        nantoken = type(
            'nantoken',
            (object,),
            {'__repr__': (lambda x: '<nantoken>')},
        )()
        data = data.fillna(nantoken)  # <- Normalized!
        datatest.validate.superset(data, set([1, 2, nantoken]))
