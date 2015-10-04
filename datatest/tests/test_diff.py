# -*- coding: utf-8 -*-
import re

# Import compatibility layers.
from . import _io as io
from . import _unittest as unittest

from datatest.diff import DiffBase

from datatest.diff import _ColumnBase
from datatest.diff import ExtraColumn
from datatest.diff import MissingColumn

from datatest.diff import _ValueBase
from datatest.diff import ExtraValue
from datatest.diff import MissingValue
from datatest.diff import InvalidNumber


class TestDiffBase(unittest.TestCase):
    def test_init_error(self):
        with self.assertRaises(NotImplementedError):
            DiffBase()  # Calls __init__.

    def test_repr_error(self):
        class MockDiff(DiffBase):
            def __init__(self):
                pass  # Knock-out __init__.

        mocked = MockDiff()
        with self.assertRaises(NotImplementedError):
            mocked.__repr__()

    def test_minimal(self):
        class MinimalSubclass(DiffBase):
            def __init__(self, diff):
                self.diff = diff

            def __repr__(self):
                return 'MinimalSubclass({0})'.format(self.diff)

        minimal = MinimalSubclass(3)
        self.assertEqual(repr(minimal), 'MinimalSubclass(3)')  # Test __repr__
        self.assertEqual(repr(minimal), str(minimal))  # Test __repr__ and __str__
        self.assertIsInstance(hash(minimal), int)
        self.assertEqual(minimal, MinimalSubclass(3))  # Test __eq__
        self.assertEqual(minimal, eval(repr(minimal)))  # Test __repr__ eval


class TestColumnDiffs(unittest.TestCase):
    """Test _ColumnBase, ExtraColumn, and MissingColumn."""
    def test_repr(self):
        diff = _ColumnBase('col3')
        self.assertEqual(repr(diff), "_ColumnBase('col3')")

    def test_str(self):
        diff = _ColumnBase('col3')
        self.assertEqual(str(diff), repr(diff))

    def test_hash(self):
        diff = _ColumnBase('col3')
        self.assertIsInstance(hash(diff), int)

    def test_eq(self):
        diff1 = _ColumnBase('col1')
        diff2 = _ColumnBase('col1')
        self.assertEqual(diff1, diff2)

        diff1 = _ColumnBase('col1')
        diff2 = _ColumnBase('col2')
        self.assertNotEqual(diff1, diff2)

        diff1 = _ColumnBase('col1')
        diff2 = "_ColumnBase('col1')"
        self.assertNotEqual(diff1, diff2)

    def test_subclass(self):
        self.assertTrue(issubclass(ExtraColumn, _ColumnBase))
        self.assertTrue(issubclass(MissingColumn, _ColumnBase))

    def test_repr_eval(self):
        diff = _ColumnBase('col3')
        self.assertEqual(diff, eval(repr(diff)))  # Test __repr__ eval


class TestValueDiffs(unittest.TestCase):
    """Test _BaseDiffValue, ExtraValue, and MissingValue."""
    def test_repr(self):
        diff = _ValueBase('foo')
        self.assertEqual(repr(diff), "_ValueBase('foo')")

        diff = _ValueBase(diff='foo')  # As kwds.
        self.assertEqual(repr(diff), "_ValueBase('foo')")

        diff = _ValueBase('foo', col4='bar')  # Using kwds for filtering.
        self.assertRegex(repr(diff), "_ValueBase\(u?'foo', col4=u?'bar'\)")

    def test_str(self):
        diff = _ValueBase('foo', col4='bar')
        self.assertEqual(str(diff), repr(diff))

    def test_hash(self):
        diff = _ValueBase('foo')
        self.assertIsInstance(hash(diff), int)

    def test_eq(self):
        diff1 = _ValueBase('foo')
        diff2 = _ValueBase('foo')
        self.assertEqual(diff1, diff2)

        diff1 = _ValueBase('foo')
        diff2 = _ValueBase('bar')
        self.assertNotEqual(diff1, diff2)

        diff1 = _ValueBase('foo')
        diff2 = "_ValueBase('foo')"
        self.assertNotEqual(diff1, diff2)

    def test_subclass(self):
        self.assertTrue(issubclass(ExtraValue, _ValueBase))
        self.assertTrue(issubclass(MissingValue, _ValueBase))

    def test_repr_eval(self):
        diff = _ValueBase('someval')
        self.assertEqual(diff, eval(repr(diff)))  # Test __repr__ eval

        diff = _ValueBase('someval', col4='foo', col5='bar')
        self.assertEqual(diff, eval(repr(diff)))  # Test __repr__ eval


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
