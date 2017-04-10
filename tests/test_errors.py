# -*- coding: utf-8 -*-
import re
from . import _unittest as unittest

from datatest.errors import ValidationErrors
from datatest.errors import DataError
from datatest.errors import Missing
from datatest.errors import Extra
from datatest.errors import Invalid
from datatest.errors import Deviation
from datatest.errors import _get_error
from datatest.errors import NOTFOUND


class MinimalDataError(DataError):
    """FOR TESTING: A minimal subclass of DataError. DataError itself
    is a base class that should not be instantiated directly.
    """
    pass


class TestValidationErrors(unittest.TestCase):
    def test_instantiation(self):
        list_of_errors = [MinimalDataError('A'), MinimalDataError('B')]
        ValidationErrors('invalid data', list_of_errors)  # Pass without error.

        single_error = MinimalDataError('A')
        ValidationErrors('invalid data', single_error)  # Pass without error.

    def test_iteration(self):
        list_of_errors = [MinimalDataError('A'), MinimalDataError('B')]
        errors = ValidationErrors('invalid data', list_of_errors)
        self.assertEqual(list(errors), list_of_errors)

        single_error = MinimalDataError('A')
        errors = ValidationErrors('invalid data', single_error)
        self.assertEqual(list(errors), [single_error])


class TestDataError(unittest.TestCase):
    def test_instantiation(self):
        """DataError is a base class that should not be
        instantiated directly. It should only serve as a
        superclass for more specific errors.
        """
        # Subclass should instantiate normally:
        subclass_instance = MinimalDataError('A')

        regex = 'requires at least 1 argument'
        with self.assertRaisesRegex(TypeError, regex):
            MinimalDataError()

        # Base class should raise error.
        regex = "can't instantiate base class DataError"
        with self.assertRaisesRegex(TypeError, regex):
            base_instance = DataError('A')

    def test_args(self):
        """Args should be tuple of arguments."""
        error = MinimalDataError('A')
        self.assertEqual(error.args, ('A',))

    def test_repr(self):
        error = MinimalDataError('A')
        self.assertEqual(repr(error), "MinimalDataError('A')")

        error = MinimalDataError('A', 'B')
        self.assertEqual(repr(error), "MinimalDataError('A', 'B')")

        error = MinimalDataError('A', None)
        self.assertEqual(repr(error), "MinimalDataError('A', None)")

    def test_string_equal(self):
        first = MinimalDataError('A')
        second = MinimalDataError('A')
        self.assertEqual(first, second)

    def test_nan_equal(self):
        """NaN values should test as equal when part of a data error."""
        first = MinimalDataError(float('nan'))
        second = MinimalDataError(float('nan'))
        self.assertEqual(first, second)

    def test_comparing_different_types(self):
        error = MinimalDataError('X')
        self.assertNotEqual(error, Exception('X'))
        self.assertNotEqual(error, None)
        self.assertNotEqual(error, True)
        self.assertNotEqual(error, False)


class TestSubclassRelationship(unittest.TestCase):
    def test_subclass(self):
        self.assertTrue(issubclass(Extra, DataError))
        self.assertTrue(issubclass(Missing, DataError))
        self.assertTrue(issubclass(Invalid, DataError))
        self.assertTrue(issubclass(Deviation, DataError))


class TestDeviation(unittest.TestCase):
    def test_instantiation(self):
        Deviation(1, 100)  # Pass without error.

        with self.assertRaises(ValueError):
            Deviation(0, 100)  # Deviation should not be zero.

    def test_repr(self):
        diff = Deviation(1, 100)  # Simple positive.
        self.assertEqual(repr(diff), "Deviation(+1, 100)")

        diff = Deviation(-1, 100)  # Simple negative.
        self.assertEqual(repr(diff), "Deviation(-1, 100)")

        diff = Deviation(1, None)  # None reference.
        self.assertEqual(repr(diff), "Deviation(+1, None)")

    def test_empty_value_handling(self):
        """Empty values receive special handling."""
        empty_values = [None, '', float('nan')]

        for x in empty_values:
            Deviation(0, x)   # <- Pass without error.
            Deviation(+5, x)  # <- Pass without error.
            Deviation(x, 0)   # <- Pass without error.
            with self.assertRaises(ValueError):
                Deviation(x, 5)  # <- Must be Deviation(-5, 5)

    def test_zero_value_handling(self):
        """Zero and False should be treated the same."""
        zero_values = [0, 0.0, False]

        for x in zero_values:
            Deviation(+5, x)  # <- Pass without error.
            with self.assertRaises(ValueError):
                Deviation(0, x)
            with self.assertRaises(ValueError):
                Deviation(x, 0)
            with self.assertRaises(ValueError):
                Deviation(x, 5)

    def test_repr_eval(self):
        diff = Deviation(+1, 100)
        self.assertEqual(diff, eval(repr(diff)))

        diff = Deviation(-1, 100)
        self.assertEqual(diff, eval(repr(diff)))


class Test_get_error(unittest.TestCase):
    def test_numeric_vs_numeric(self):
        diff = _get_error(5, 6)
        self.assertEqual(diff, Deviation(-1, 6))

    def test_numeric_vs_none(self):
        diff = _get_error(5, None)
        self.assertEqual(diff, Deviation(+5, None))

        diff = _get_error(0, None)
        self.assertEqual(diff, Deviation(+0, None))

    def test_none_vs_numeric(self):
        diff = _get_error(None, 6)                # For None vs non-zero,
        self.assertEqual(diff, Deviation(-6, 6))  # difference is calculated
                                                  # as 0 - other.

        diff = _get_error(None, 0)                  # For None vs zero,
        self.assertEqual(diff, Deviation(None, 0))  # difference remains None.

    def test_object_vs_object(self):
        """Non-numeric comparisons return Invalid type."""
        diff = _get_error('a', 'b')
        self.assertEqual(diff, Invalid('a', 'b'))

        diff = _get_error(5, 'b')
        self.assertEqual(diff, Invalid(5, 'b'))

        diff = _get_error('a', 6)
        self.assertEqual(diff, Invalid('a', 6))

        diff = _get_error(float('nan'), 6)
        self.assertEqual(diff, Invalid(float('nan'), 6))

        diff = _get_error(5, float('nan'))
        self.assertEqual(diff, Invalid(5, float('nan')))

        fn = lambda x: True
        diff = _get_error('a', fn)
        self.assertEqual(diff, Invalid('a', fn))

        regex = re.compile('^test$')
        diff = _get_error('a', regex)
        self.assertEqual(diff, Invalid('a', re.compile('^test$')))

    def test_notfound_comparisons(self):
        diff = _get_error('a', NOTFOUND)
        self.assertEqual(diff, Extra('a'))

        diff = _get_error(NOTFOUND, 'b')
        self.assertEqual(diff, Missing('b'))

        # For numeric comparisons, NOTFOUND behaves like None.
        diff = _get_error(5, NOTFOUND)
        self.assertEqual(diff, Deviation(+5, None))

        diff = _get_error(0, NOTFOUND)
        self.assertEqual(diff, Deviation(0, None))

        diff = _get_error(NOTFOUND, 6)
        self.assertEqual(diff, Deviation(-6, 6))  # <- Assymetric behavior
                                                  #    (see None vs numeric)!

        diff = _get_error(NOTFOUND, 0)
        self.assertEqual(diff, Deviation(None, 0))

    def test_show_expected(self):
        """If requirement is common it should be omitted from Invalid
        difference (but not from Deviation differences).
        """
        diff = _get_error('a', 6, show_expected=True)
        self.assertEqual(diff, Invalid('a', expected=6))

        diff = _get_error('a', 6, show_expected=False)
        self.assertEqual(diff, Invalid('a'))

        diff = _get_error(NOTFOUND, 6, show_expected=False)
        self.assertEqual(diff, Deviation(-6, 6))

    def test_same(self):
        """The _get_error() function returns differences for objects
        that are KNOWN TO BE DIFFERENT--it does not test for differences
        itself.
        """
        diff = _get_error('a', 'a')
        self.assertEqual(diff, Invalid('a', 'a'))

        diff = _get_error(None, None)
        self.assertEqual(diff, Invalid(None, None))
