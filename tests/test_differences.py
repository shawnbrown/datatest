# -*- coding: utf-8 -*-
import re

# Import compatibility layers.
from . import _io as io
from . import _unittest as unittest

from datatest.differences import BaseDifference
from datatest.differences import Extra
from datatest.differences import Missing
from datatest.differences import Invalid
from datatest.differences import Deviation


class TestBaseDifference(unittest.TestCase):
    def setUp(self):
        class MinimalDifference(BaseDifference):    # Create subclass because
            pass                                    # BaseDifference cannot be
        self.MinimalDifference = MinimalDifference  # instantiated directly.

    def test_repr(self):
        item = self.MinimalDifference('foo')
        self.assertEqual(repr(item), "MinimalDifference('foo')")

        item = self.MinimalDifference(value='foo')  # As kwds.
        self.assertEqual(repr(item), "MinimalDifference('foo')")

        item = self.MinimalDifference('foo', col4='bar')  # Using kwds for filtering.
        self.assertRegex(repr(item), "MinimalDifference\(u?'foo', col4=u?'bar'\)")

    def test_str(self):
        diff = self.MinimalDifference('foo', col4='bar')
        self.assertEqual(str(diff), repr(diff))

    def test_hash(self):
        diff = self.MinimalDifference('foo')
        self.assertIsInstance(hash(diff), int)

    def test_eq(self):
        diff1 = self.MinimalDifference('foo')
        diff2 = self.MinimalDifference('foo')
        self.assertEqual(diff1, diff2)

        diff1 = self.MinimalDifference('foo')
        diff2 = self.MinimalDifference('bar')
        self.assertNotEqual(diff1, diff2)

        class OtherDifference(BaseDifference):
            pass
        diff1 = OtherDifference('foo')
        diff2 = self.MinimalDifference('foo')
        self.assertNotEqual(diff1, diff2)

    def test_repr_eval(self):
        MinimalDifference = self.MinimalDifference

        diff = MinimalDifference('someval')
        self.assertEqual(diff, eval(repr(diff)))  # Test __repr__ eval

        diff = MinimalDifference('someval', col4='foo', col5='bar')
        self.assertEqual(diff, eval(repr(diff)))  # Test __repr__ eval


class TestExtraAndMissing(unittest.TestCase):
    def test_subclass(self):
        self.assertTrue(issubclass(Extra, BaseDifference))
        self.assertTrue(issubclass(Missing, BaseDifference))


class TestInvalid(unittest.TestCase):
    """Test Invalid."""
    def test_instantiation(self):
        Invalid('foo')
        Invalid('foo', expected='FOO')

    def test_repr(self):
        item = Invalid('foo')
        self.assertEqual("Invalid('foo')", repr(item))

        item = Invalid(None)
        self.assertEqual("Invalid(None)", repr(item))

        item = Invalid(2)
        self.assertEqual("Invalid(2)", repr(item))

    def test_expected_handling(self):
        item = Invalid('foo', 'FOO')
        self.assertEqual("Invalid('foo', 'FOO')", repr(item))

        # QUESTION: How should kwds be handled if keys match item or expected?
        with self.assertRaises(TypeError):
            item = Invalid('foo', 'FOO', required='bar')


class TestDeviation(unittest.TestCase):
    """Test Deviation."""
    def test_instantiation(self):
        Deviation(1, 100)  # Pass without error.

    def test_repr(self):
        diff = Deviation(1, 100)  # Simple.
        self.assertEqual("Deviation(+1, 100)", repr(diff))

        diff = Deviation(-1, 100)  # Simple negative.
        self.assertEqual("Deviation(-1, 100)", repr(diff))

        diff = Deviation(3, 50, col1='a', col2='b')  # Using kwds.
        self.assertRegex(repr(diff), "Deviation\(\+3, 50, col1=u?'a', col2=u?'b'\)")

        diff = Deviation(1, None, col1='a')  # None reference.
        self.assertRegex(repr(diff), "Deviation\(\+1, None, col1=u?'a'\)")

    def test_empty_value_handling(self):
        with self.assertRaises(ValueError):
            Deviation(0, 100)  # Zero diff.

        Deviation(0, None)
        Deviation(+5, None)
        Deviation(None, 0)
        with self.assertRaises(ValueError):
            Deviation(None, 5)  # Should be Deviation(-5, 5)

        Deviation(0, '')
        Deviation(+5, '')
        Deviation('', 0)
        with self.assertRaises(ValueError):
            Deviation('', 5)  # Should be Deviation(-5, 5)

        Deviation(0, float('nan'))
        Deviation(+5, float('nan'))
        Deviation(float('nan'), 0)
        with self.assertRaises(ValueError):
            Deviation(float('nan'), 5)  # Should be Deviation(-5, 5)

        with self.assertRaises(ValueError):
            Deviation(0, 1)  # Just no.

        # False is treated the same as zero.
        Deviation(+5, 0)
        Deviation(+5, False)

        with self.assertRaises(ValueError):
            Deviation(0, 0)

        with self.assertRaises(ValueError):
            Deviation(0, False)

        with self.assertRaises(ValueError):
            Deviation(False, 0)

        with self.assertRaises(ValueError):
            Deviation(False, 5)  # Should be Deviation(-5, 5)

    def test_str(self):
        diff = Deviation(5, 75, col1='a')
        self.assertEqual(str(diff), repr(diff))

    def test_hash(self):
        diff = Deviation(1, 100, col1='a', col2='b')
        self.assertIsInstance(hash(diff), int)

    def test_eq(self):
        diff1 = Deviation(1, 100)
        diff2 = Deviation(1, 100)
        self.assertEqual(diff1, diff2)

        diff1 = Deviation(1.0, 100.0)
        diff2 = Deviation(1.0, 100.0)
        self.assertEqual(diff1, diff2)

        diff1 = Deviation(1.0, 100)
        diff2 = Deviation(1,   100)
        self.assertEqual(diff1, diff2)

        diff1 = Deviation(1, 100.0)
        diff2 = Deviation(1, 100)
        self.assertEqual(diff1, diff2)

        diff1 = Deviation(1, 100, foo='aaa', bar='bbb')
        diff2 = Deviation(1, 100, bar='bbb', foo='aaa')
        self.assertEqual(diff1, diff2)

        diff1 = Deviation(1, 100)
        diff2 = Deviation(1, 250)
        self.assertNotEqual(diff1, diff2)

        diff1 = Deviation(+1, 100)
        diff2 = "Deviation(+1, 100)"
        self.assertNotEqual(diff1, diff2)

    def test_repr_eval(self):
        diff = Deviation(+1, 100)
        self.assertEqual(diff, eval(repr(diff)))  # Test __repr__ eval

        diff = Deviation(-1, 100, col4='foo', col5='bar')
        self.assertEqual(diff, eval(repr(diff)))  # Test __repr__ eval
