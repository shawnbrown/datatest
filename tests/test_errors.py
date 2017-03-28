# -*- coding: utf-8 -*-
from . import _unittest as unittest

from datatest.errors import ValidationErrors
from datatest.errors import DataError
from datatest.errors import Missing
from datatest.errors import Extra
from datatest.errors import Invalid
from datatest.errors import Deviation


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

    def test_equal(self):
        first = MinimalDataError('A')
        second = MinimalDataError('A')
        self.assertEqual(first, second)


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
