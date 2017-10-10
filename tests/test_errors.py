# -*- coding: utf-8 -*-
import re
import textwrap
from . import _unittest as unittest

from datatest.validation import ValidationError
from datatest.errors import BaseDifference
from datatest.errors import Missing
from datatest.errors import Extra
from datatest.errors import Invalid
from datatest.errors import Deviation
from datatest.errors import _make_difference
from datatest.errors import NOTFOUND


# FOR TESTING: A minimal subclass of BaseDifference.
# BaseDifference itself should not be instantiated
# directly.
class MinimalDifference(BaseDifference):
    pass


class TestBaseDifference(unittest.TestCase):
    def test_instantiation(self):
        """BaseDifference should not be instantiated directly.
        It should only serve as a superclass for more specific
        differences.
        """
        # Subclass should instantiate normally:
        subclass_instance = MinimalDifference('A')

        regex = 'requires at least 1 argument'
        with self.assertRaisesRegex(TypeError, regex):
            MinimalDifference()

        # Base class should raise error.
        regex = "Can't instantiate abstract class BaseDifference"
        with self.assertRaisesRegex(TypeError, regex):
            base_instance = BaseDifference('A')

    def test_args(self):
        """Args should be tuple of arguments."""
        diff = MinimalDifference('A')
        self.assertEqual(diff.args, ('A',))

    def test_repr(self):
        diff = MinimalDifference('A')
        self.assertEqual(repr(diff), "MinimalDifference('A')")

        diff = MinimalDifference('A', 'B')
        self.assertEqual(repr(diff), "MinimalDifference('A', 'B')")

        diff = MinimalDifference('A', None)
        self.assertEqual(repr(diff), "MinimalDifference('A', None)")

    def test_string_equal(self):
        first = MinimalDifference('A')
        second = MinimalDifference('A')
        self.assertEqual(first, second)

    def test_nan_equal(self):
        """NaN values should test as equal when part of a difference."""
        first = MinimalDifference(float('nan'))
        second = MinimalDifference(float('nan'))
        self.assertEqual(first, second)

    def test_comparing_different_types(self):
        diff = MinimalDifference('X')
        self.assertNotEqual(diff, Exception('X'))
        self.assertNotEqual(diff, None)
        self.assertNotEqual(diff, True)
        self.assertNotEqual(diff, False)


class TestSubclassRelationship(unittest.TestCase):
    def test_subclass(self):
        self.assertTrue(issubclass(Extra, BaseDifference))
        self.assertTrue(issubclass(Missing, BaseDifference))
        self.assertTrue(issubclass(Invalid, BaseDifference))
        self.assertTrue(issubclass(Deviation, BaseDifference))


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


class TestMakeDifference(unittest.TestCase):
    def test_numeric_vs_numeric(self):
        diff = _make_difference(5, 6)
        self.assertEqual(diff, Deviation(-1, 6))

    def test_numeric_vs_none(self):
        diff = _make_difference(5, None)
        self.assertEqual(diff, Deviation(+5, None))

        diff = _make_difference(0, None)
        self.assertEqual(diff, Deviation(+0, None))

    def test_none_vs_numeric(self):
        diff = _make_difference(None, 6)          # For None vs non-zero,
        self.assertEqual(diff, Deviation(-6, 6))  # difference is calculated
                                                  # as 0 - other.

        diff = _make_difference(None, 0)            # For None vs zero,
        self.assertEqual(diff, Deviation(None, 0))  # difference remains None.

    def test_object_vs_object(self):
        """Non-numeric comparisons return Invalid type."""
        diff = _make_difference('a', 'b')
        self.assertEqual(diff, Invalid('a', 'b'))

        diff = _make_difference(5, 'b')
        self.assertEqual(diff, Invalid(5, 'b'))

        diff = _make_difference('a', 6)
        self.assertEqual(diff, Invalid('a', 6))

        diff = _make_difference(float('nan'), 6)
        self.assertEqual(diff, Invalid(float('nan'), 6))

        diff = _make_difference(5, float('nan'))
        self.assertEqual(diff, Invalid(5, float('nan')))

        fn = lambda x: True
        diff = _make_difference('a', fn)
        self.assertEqual(diff, Invalid('a', fn))

        regex = re.compile('^test$')
        diff = _make_difference('a', regex)
        self.assertEqual(diff, Invalid('a', re.compile('^test$')))

    def test_notfound_comparisons(self):
        diff = _make_difference('a', NOTFOUND)
        self.assertEqual(diff, Extra('a'))

        diff = _make_difference(NOTFOUND, 'b')
        self.assertEqual(diff, Missing('b'))

        # For numeric comparisons, NOTFOUND behaves like None.
        diff = _make_difference(5, NOTFOUND)
        self.assertEqual(diff, Deviation(+5, None))

        diff = _make_difference(0, NOTFOUND)
        self.assertEqual(diff, Deviation(0, None))

        diff = _make_difference(NOTFOUND, 6)
        self.assertEqual(diff, Deviation(-6, 6))  # <- Asymmetric behavior
                                                  #    (see None vs numeric)!

        diff = _make_difference(NOTFOUND, 0)
        self.assertEqual(diff, Deviation(None, 0))

    def test_show_expected(self):
        """If requirement is common it should be omitted from Invalid
        difference (but not from Deviation differences).
        """
        diff = _make_difference('a', 6, show_expected=True)
        self.assertEqual(diff, Invalid('a', expected=6))

        diff = _make_difference('a', 6, show_expected=False)
        self.assertEqual(diff, Invalid('a'))

        diff = _make_difference(NOTFOUND, 6, show_expected=False)
        self.assertEqual(diff, Deviation(-6, 6))

    def test_same(self):
        """The _make_difference() function returns differences for
        objects that are KNOWN TO BE DIFFERENT--it does not test
        for differences itself.
        """
        diff = _make_difference('a', 'a')
        self.assertEqual(diff, Invalid('a', 'a'))

        diff = _make_difference(None, None)
        self.assertEqual(diff, Invalid(None, None))
