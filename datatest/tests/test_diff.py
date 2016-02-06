# -*- coding: utf-8 -*-
import re

# Import compatibility layers.
from . import _io as io
from . import _unittest as unittest

from datatest.diff import BaseDifference
from datatest.diff import ExtraItem
from datatest.diff import MissingItem
from datatest.diff import InvalidItem
from datatest.diff import InvalidNumber


class TestBaseDifference(unittest.TestCase):
    def test_repr(self):
        item = BaseDifference('foo')
        self.assertEqual(repr(item), "BaseDifference('foo')")

        item = BaseDifference(item='foo')  # As kwds.
        self.assertEqual(repr(item), "BaseDifference('foo')")

        item = BaseDifference('foo', col4='bar')  # Using kwds for filtering.
        self.assertRegex(repr(item), "BaseDifference\(u?'foo', col4=u?'bar'\)")

    def test_str(self):
        diff = BaseDifference('foo', col4='bar')
        self.assertEqual(str(diff), repr(diff))

    def test_hash(self):
        diff = BaseDifference('foo')
        self.assertIsInstance(hash(diff), int)

    def test_eq(self):
        diff1 = BaseDifference('foo')
        diff2 = BaseDifference('foo')
        self.assertEqual(diff1, diff2)

        diff1 = BaseDifference('foo')
        diff2 = BaseDifference('bar')
        self.assertNotEqual(diff1, diff2)

        diff1 = BaseDifference('foo')
        diff2 = "BaseDifference('foo')"
        self.assertNotEqual(diff1, diff2)

    def test_repr_eval(self):
        diff = BaseDifference('someval')
        self.assertEqual(diff, eval(repr(diff)))  # Test __repr__ eval

        diff = BaseDifference('someval', col4='foo', col5='bar')
        self.assertEqual(diff, eval(repr(diff)))  # Test __repr__ eval


class TestExtraAndMissing(unittest.TestCase):
    def test_subclass(self):
        self.assertTrue(issubclass(ExtraItem, BaseDifference))
        self.assertTrue(issubclass(MissingItem, BaseDifference))


class TestInvalidItem(unittest.TestCase):
    """Test InvalidItem."""
    def test_instantiation(self):
        InvalidItem('foo')
        InvalidItem('foo', expected='FOO')

    def test_repr(self):
        item = InvalidItem('foo')
        self.assertEqual("InvalidItem('foo')", repr(item))

        item = InvalidItem(None)
        self.assertEqual("InvalidItem(None)", repr(item))

        item = InvalidItem(2)
        self.assertEqual("InvalidItem(2)", repr(item))

    def test_expected_handling(self):
        item = InvalidItem('foo', 'FOO')
        self.assertEqual("InvalidItem('foo', 'FOO')", repr(item))

        # QUESTION: How should kwds be handled if keys match item or expected?
        with self.assertRaises(TypeError):
            item = InvalidItem('foo', 'FOO', expected='bar')


class TestInvalidNumber(unittest.TestCase):
    """Test InvalidNumber."""
    def test_instantiation(self):
        InvalidNumber(1, 100)  # Pass without error.

    def test_repr(self):
        diff = InvalidNumber(1, 100)  # Simple.
        self.assertEqual("InvalidNumber(+1, 100)", repr(diff))

        diff = InvalidNumber(-1, 100)  # Simple negative.
        self.assertEqual("InvalidNumber(-1, 100)", repr(diff))

        diff = InvalidNumber(3, 50, col1='a', col2='b')  # Using kwds.
        self.assertRegex(repr(diff), "InvalidNumber\(\+3, 50, col1=u?'a', col2=u?'b'\)")

        with self.assertRaises(ValueError):
            diff = InvalidNumber(0, 100)  # Zero diff.

        with self.assertRaises(ValueError):
            diff = InvalidNumber(None, 100)  # None diff.

        diff = InvalidNumber(1, None, col1='a')  # None reference.
        self.assertRegex(repr(diff), "InvalidNumber\(\+1, None, col1=u?'a'\)")

    def test_str(self):
        diff = InvalidNumber(5, 75, col1='a')
        self.assertEqual(str(diff), repr(diff))

    def test_hash(self):
        diff = InvalidNumber(1, 100, col1='a', col2='b')
        self.assertIsInstance(hash(diff), int)

    def test_eq(self):
        diff1 = InvalidNumber(1, 100)
        diff2 = InvalidNumber(1, 100)
        self.assertEqual(diff1, diff2)

        diff1 = InvalidNumber(1.0, 100.0)
        diff2 = InvalidNumber(1.0, 100.0)
        self.assertEqual(diff1, diff2)

        diff1 = InvalidNumber(1.0, 100)
        diff2 = InvalidNumber(1,   100)
        self.assertEqual(diff1, diff2)

        diff1 = InvalidNumber(1, 100.0)
        diff2 = InvalidNumber(1, 100)
        self.assertEqual(diff1, diff2)

        diff1 = InvalidNumber(1, 100, foo='aaa', bar='bbb')
        diff2 = InvalidNumber(1, 100, bar='bbb', foo='aaa')
        self.assertEqual(diff1, diff2)

        diff1 = InvalidNumber(1, 100)
        diff2 = InvalidNumber(1, 250)
        self.assertNotEqual(diff1, diff2)

        diff1 = InvalidNumber(+1, 100)
        diff2 = "InvalidNumber(+1, 100)"
        self.assertNotEqual(diff1, diff2)

    def test_repr_eval(self):
        diff = InvalidNumber(+1, 100)
        self.assertEqual(diff, eval(repr(diff)))  # Test __repr__ eval

        diff = InvalidNumber(-1, 100, col4='foo', col5='bar')
        self.assertEqual(diff, eval(repr(diff)))  # Test __repr__ eval
