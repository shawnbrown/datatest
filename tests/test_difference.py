# -*- coding: utf-8 -*-
import datetime
import decimal
import re
import textwrap
from . import _unittest as unittest

from datatest.differences import (
    BaseDifference,
    Missing,
    Extra,
    Invalid,
    Deviation,
    _make_difference,
    NOVALUE,
)

# FOR TESTING: A minimal subclass of BaseDifference.
# BaseDifference itself should not be instantiated
# directly.
class MinimalDifference(BaseDifference):
    def __init__(self, *args):
        self._args = args

    @property
    def args(self):
        return self._args


class TestBaseDifference(unittest.TestCase):
    def test_instantiation(self):
        """BaseDifference should not be instantiated directly.
        It should only serve as a superclass for more specific
        differences.
        """
        # Subclass should instantiate normally:
        subclass_instance = MinimalDifference('A')

        # Base class should raise error.
        regex = "Can't instantiate abstract class BaseDifference"
        with self.assertRaisesRegex(TypeError, regex):
            base_instance = BaseDifference()

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

        def myfunc(x):
            return True
        diff = MinimalDifference('A', myfunc)
        self.assertEqual(repr(diff), "MinimalDifference('A', myfunc)")

        class MyClass(object):
            pass
        diff = MinimalDifference('A', MyClass)
        self.assertEqual(repr(diff), "MinimalDifference('A', MyClass)")

    def test_numbers_equal(self):
        first = MinimalDifference(1)
        second = MinimalDifference(1.0)
        self.assertEqual(first, second)

        first = MinimalDifference(1)
        second = MinimalDifference(2)
        self.assertNotEqual(first, second)

    def test_string_equal(self):
        first = MinimalDifference('A')
        second = MinimalDifference('A')
        self.assertEqual(first, second)

    def test_nan_equal(self):
        """NaN values should test as equal when part of a difference."""
        first = MinimalDifference(float('nan'))
        second = MinimalDifference(float('nan'))
        self.assertEqual(first, second)

        # NaNs nested in a tuple should also test as equal.
        first = MinimalDifference(('abc', float('nan')))
        second = MinimalDifference(('abc', float('nan')))
        self.assertEqual(first, second)

        # Complex numbers, too.
        first = MinimalDifference(float('nan'))
        second = MinimalDifference(complex(float('nan')))
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


class TestInvalid(unittest.TestCase):
    def test_repr(self):
        diff = Invalid('foo')
        self.assertEqual(repr(diff), "Invalid('foo')")

        diff = Invalid('foo', 'bar')
        self.assertEqual(repr(diff), "Invalid('foo', expected='bar')")

        diff = Invalid('foo', None)
        self.assertEqual(repr(diff), "Invalid('foo', expected=None)")

    def test_repr_with_callables(self):
        def myfunc(x):
            return True

        class MyClass(object):
            pass

        diff = Invalid('foo', myfunc)
        self.assertEqual(repr(diff), "Invalid('foo', expected=myfunc)")

        diff = Invalid('foo', MyClass)
        self.assertEqual(repr(diff), "Invalid('foo', expected=MyClass)")

        diff = Invalid(myfunc, 'bar')
        self.assertEqual(repr(diff), "Invalid(myfunc, expected='bar')")

        diff = Invalid(MyClass, 'bar')
        self.assertEqual(repr(diff), "Invalid(MyClass, expected='bar')")

    def test_same_values(self):
        with self.assertRaises(ValueError):
            Invalid('foo', 'foo')


class TestDeviation(unittest.TestCase):
    def test_instantiation(self):
        Deviation(1, 100)  # Pass without error.

        with self.assertRaises(ValueError):
            Deviation(0, 100)  # Deviation should not be zero.

    def test_nonquantitative(self):
        with self.assertRaises(TypeError):
            Deviation(set([3]), set([1, 2]))

    def test_repr(self):
        diff = Deviation(1, 100)  # Simple positive.
        self.assertEqual(repr(diff), "Deviation(+1, 100)")

        diff = Deviation(-1, 100)  # Simple negative.
        self.assertEqual(repr(diff), "Deviation(-1, 100)")

        diff = Deviation(float('nan'), 100)  # None reference.
        self.assertEqual(repr(diff), "Deviation(float('nan'), 100)")

    def test_zero_and_empty_value_handling(self):
        """Empty values receive special handling."""
        # Expected 0 (pass without error).
        Deviation(+5, 0)
        Deviation(-5, 0)
        Deviation(float('nan'), 0)
        with self.assertRaises(ValueError):
            Deviation(0, 0)

        # Expected numeric value (pass without error).
        Deviation(+1, 5)
        Deviation(-1, 5)
        Deviation(float('nan'), 5)

        # Expected non-zero, with empty or zero deviation.
        with self.assertRaises(ValueError):
            Deviation(0, 5)

        with self.assertRaises(TypeError):
            Deviation(None, 5)

        with self.assertRaises(TypeError):
            Deviation('', 5)

        with self.assertRaises(TypeError):
            Deviation(5, None)

        with self.assertRaises(TypeError):
            Deviation(5, '')

        # NaN handling.
        Deviation(float('nan'), 0)
        Deviation(0, float('nan'))

    def test_repr_eval(self):
        diff = Deviation(+1, 100)
        self.assertEqual(diff, eval(repr(diff)))

        diff = Deviation(-1, 100)
        self.assertEqual(diff, eval(repr(diff)))

        diff = Deviation(float('nan'), 100)
        self.assertEqual(diff, eval(repr(diff)))


class TestImmutability(unittest.TestCase):
    """Differences should act like an immutable objects."""
    def test_missing(self):
        diff = Missing('foo')

        with self.assertRaises(AttributeError):
            diff.attr = ('bar',)

        with self.assertRaises(AttributeError):
            diff.new_attribute = 'baz'

    def test_extra(self):
        diff = Extra('foo')

        with self.assertRaises(AttributeError):
            diff.attr = ('bar',)

        with self.assertRaises(AttributeError):
            diff.new_attribute = 'baz'

    def test_invalid(self):
        diff = Invalid('foo')

        with self.assertRaises(AttributeError):
            diff.expected = 'bar'

        with self.assertRaises(AttributeError):
            diff.new_attribute = 'baz'

    def test_deviation(self):
        diff = Deviation(+1, 100)

        with self.assertRaises(AttributeError):
            diff.expected = 101

        with self.assertRaises(AttributeError):
            diff.new_attribute = 202


class TestHashability(unittest.TestCase):
    """Built-in differences should be hashable (in the same way that
    tuples are).
    """
    def test_hashable(self):
        """Differences with hashable *args should be hashable."""
        # Following should all pass without error.
        hash(Missing('foo'))
        hash(Extra('bar'))
        hash(Invalid('baz'))
        hash(Invalid('baz', 'qux'))
        hash(Deviation(-1, 10))

    def test_unhashable_contents(self):
        """The hash behavior of differences should act like tuples do.
        When a difference's contents are unhashable, the difference
        itself becomes unhashable too.
        """
        with self.assertRaises(TypeError):
            hash(Missing(['foo']))

        with self.assertRaises(TypeError):
            hash(Extra(['bar']))

        with self.assertRaises(TypeError):
            hash(Invalid(['baz']))

        with self.assertRaises(TypeError):
            hash(Invalid('baz', ['qux']))


class TestMakeDifference(unittest.TestCase):
    def test_numeric_vs_numeric(self):
        diff = _make_difference(5, 6)
        self.assertEqual(diff, Deviation(-1, 6))

    def test_decimal_vs_float(self):
        diff = _make_difference(decimal.Decimal('5'), 6.0)
        self.assertEqual(diff, Invalid(decimal.Decimal('5'), expected=6.0))

    def test_datetime_vs_datetime(self):
        diff = _make_difference(
            datetime.datetime(1989, 2, 24, hour=10, minute=30),
            datetime.datetime(1989, 2, 24, hour=11, minute=30),
        )

        self.assertEqual(
            diff,
            Deviation(
                datetime.timedelta(hours=-1),
                datetime.datetime(1989, 2, 24, hour=11, minute=30),
            ),
        )

    def test_numeric_vs_none(self):
        diff = _make_difference(5, None)
        self.assertEqual(diff, Invalid(5, None))

        diff = _make_difference(0, None)
        self.assertEqual(diff, Invalid(0, None))

    def test_none_vs_numeric(self):
        diff = _make_difference(None, 6)
        self.assertEqual(diff, Invalid(None, 6))

        diff = _make_difference(None, 0)
        self.assertEqual(diff, Invalid(None, 0))

    def test_object_vs_object(self):
        """Non-numeric comparisons return Invalid type."""
        diff = _make_difference('a', 'b')
        self.assertEqual(diff, Invalid('a', 'b'))

        diff = _make_difference(5, 'b')
        self.assertEqual(diff, Invalid(5, 'b'))

        diff = _make_difference('a', 6)
        self.assertEqual(diff, Invalid('a', 6))

        diff = _make_difference(float('nan'), 6)
        self.assertEqual(diff, Deviation(float('nan'), 6))

        diff = _make_difference(5, float('nan'))
        self.assertEqual(diff, Deviation(float('nan'), float('nan')))

        fn = lambda x: True
        diff = _make_difference('a', fn)
        self.assertEqual(diff, Invalid('a', fn))

        regex = re.compile('^test$')
        diff = _make_difference('a', regex)
        self.assertEqual(diff, Invalid('a', re.compile('^test$')))

    def test_boolean_comparisons(self):
        """Boolean differences should not be treated quantitatively."""
        diff = _make_difference(False, True)
        self.assertIs(diff.invalid, False)
        self.assertIs(diff.expected, True)

        diff = _make_difference(True, False)
        self.assertIs(diff.invalid, True)
        self.assertIs(diff.expected, False)

        diff = _make_difference(0, True)
        self.assertEqual(diff.invalid, 0)
        self.assertIsNot(diff.invalid, False)
        self.assertIs(diff.expected, True)

        diff = _make_difference(1, False)
        self.assertEqual(diff.invalid, 1)
        self.assertIsNot(diff.invalid, True)
        self.assertIs(diff.expected, False)

        diff = _make_difference(False, 1)
        self.assertIs(diff.invalid, False)
        self.assertEqual(diff.expected, 1)
        self.assertIsNot(diff.expected, True)

        diff = _make_difference(True, 0)
        self.assertIs(diff.invalid, True)
        self.assertEqual(diff.expected, 0)
        self.assertIsNot(diff.expected, False)

    def test_novalue_comparisons(self):
        diff = _make_difference('a', NOVALUE)
        self.assertEqual(diff, Extra('a'))

        diff = _make_difference(5, NOVALUE)
        self.assertEqual(diff, Extra(5))

        diff = _make_difference(0, NOVALUE)
        self.assertEqual(diff, Extra(0))

        diff = _make_difference(NOVALUE, 'a')
        self.assertEqual(diff, Missing('a'))

        diff = _make_difference(NOVALUE, 5)
        self.assertEqual(diff, Missing(5))

        diff = _make_difference(NOVALUE, 0)
        self.assertEqual(diff, Missing(0))

    def test_show_expected(self):
        """If requirement is common it should be omitted from Invalid
        difference (but not from Deviation differences).
        """
        diff = _make_difference('a', 6, show_expected=True)
        self.assertEqual(diff, Invalid('a', expected=6))

        diff = _make_difference('a', 6, show_expected=False)
        self.assertEqual(diff, Invalid('a'))

        # Show expected should not effect Missing, Extra, or Deviation:

        diff = _make_difference(NOVALUE, 6, show_expected=True)
        self.assertEqual(diff, Missing(6))

        diff = _make_difference(NOVALUE, 6, show_expected=False)
        self.assertEqual(diff, Missing(6))

        diff = _make_difference(6, NOVALUE, show_expected=True)
        self.assertEqual(diff, Extra(6))

        diff = _make_difference(6, NOVALUE, show_expected=False)
        self.assertEqual(diff, Extra(6))

        diff = _make_difference(1, 2, show_expected=True)
        self.assertEqual(diff, Deviation(-1, 2))

        diff = _make_difference(1, 2, show_expected=False)
        self.assertEqual(diff, Deviation(-1, 2))

    def test_same(self):
        with self.assertRaises(ValueError):
            diff = _make_difference('a', 'a')

        with self.assertRaises(ValueError):
            diff = _make_difference(None, None)

        # NaN should work though.
        _make_difference(float('nan'), float('nan'))
