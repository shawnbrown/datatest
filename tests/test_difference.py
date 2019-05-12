# -*- coding: utf-8 -*-
import re
import textwrap
from . import _unittest as unittest

from datatest.difference import BaseDifference
from datatest.difference import Missing
from datatest.difference import Extra
from datatest.difference import Invalid
from datatest.difference import Deviation
from datatest.difference import _make_difference
from datatest.difference import NOVALUE


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

    def test_zero_and_empty_value_handling(self):
        """Empty values receive special handling."""
        # Expected 0 (pass without error).
        Deviation(+5, 0)
        Deviation(-5, 0)
        Deviation(None, 0)
        Deviation('', 0)
        Deviation(float('nan'), 0)
        with self.assertRaises(ValueError):
            Deviation(0, 0)

        # Expected empty value (pass without error).
        Deviation(0, None)
        Deviation(5, None)
        Deviation(0, '')
        Deviation(5, '')

        # Expected numeric value (pass without error).
        Deviation(+1, 5)
        Deviation(-1, 5)
        Deviation(float('nan'), 5)

        # Expected non-zero, with empty or zero deviation.
        with self.assertRaises(ValueError):
            Deviation(0, 5)
        with self.assertRaises(ValueError):
            Deviation(None, 5)
        with self.assertRaises(ValueError):
            Deviation('', 5)

        # Expected NaN.
        with self.assertRaises(ValueError):  # When the expected value
            Deviation(0, float('nan'))       # is not a number, it is
        with self.assertRaises(ValueError):  # not possible to compute
            Deviation(5, float('nan'))       # a numeric difference.

    def test_repr_eval(self):
        diff = Deviation(+1, 100)
        self.assertEqual(diff, eval(repr(diff)))

        diff = Deviation(-1, 100)
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

    def test_novalue_comparisons(self):
        diff = _make_difference('a', NOVALUE)
        self.assertEqual(diff, Extra('a'))

        diff = _make_difference(NOVALUE, 'b')
        self.assertEqual(diff, Missing('b'))

        # For numeric comparisons, NOVALUE behaves like None.
        diff = _make_difference(5, NOVALUE)
        self.assertEqual(diff, Deviation(+5, None))

        diff = _make_difference(0, NOVALUE)
        self.assertEqual(diff, Deviation(0, None))

        diff = _make_difference(NOVALUE, 6)
        self.assertEqual(diff, Deviation(-6, 6))  # <- Asymmetric behavior
                                                  #    (see None vs numeric)!

        diff = _make_difference(NOVALUE, 0)
        self.assertEqual(diff, Deviation(None, 0))

    def test_show_expected(self):
        """If requirement is common it should be omitted from Invalid
        difference (but not from Deviation differences).
        """
        diff = _make_difference('a', 6, show_expected=True)
        self.assertEqual(diff, Invalid('a', expected=6))

        diff = _make_difference('a', 6, show_expected=False)
        self.assertEqual(diff, Invalid('a'))

        diff = _make_difference(NOVALUE, 6, show_expected=False)
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
