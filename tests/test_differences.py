# -*- coding: utf-8 -*-
import re

# Import compatibility layers.
from . import _io as io
from . import _unittest as unittest

from datatest.differences import DataAssertionError
from datatest.differences import BaseDifference
from datatest.differences import Extra
from datatest.differences import Missing
from datatest.differences import Invalid
from datatest.differences import Deviation


class TestDataAssertionError(unittest.TestCase):
    def test_subclass(self):
        self.assertTrue(issubclass(DataAssertionError, AssertionError))

    def test_instantiation(self):
        DataAssertionError('column names', Missing('foo'))
        DataAssertionError('column names', [Missing('foo')])
        DataAssertionError('column names', {'Explanation here.': Missing('foo')})
        DataAssertionError('column names', {'Explanation here.': [Missing('foo')]})

        with self.assertRaises(ValueError, msg='Empty error should raise exception.'):
            DataAssertionError(msg='', diff={})

    def test_repr(self):
        error = DataAssertionError('different columns', [Missing('foo')])
        pattern = "DataAssertionError: different columns:\n Missing('foo')"
        self.assertEqual(repr(error), pattern)

        error = DataAssertionError('different columns', Missing('foo'))
        pattern = "DataAssertionError: different columns:\n Missing('foo')"
        self.assertEqual(repr(error), pattern)

        # Test pprint lists.
        error = DataAssertionError('different columns', [Missing('foo'),
                                                         Missing('bar')])
        pattern = ("DataAssertionError: different columns:\n"
                   " Missing('foo'),\n"
                   " Missing('bar')")
        self.assertEqual(repr(error), pattern)

        # Test dictionary with nested list.
        error = DataAssertionError('different columns', {'Omitted': [Missing('foo'),
                                                                     Missing('bar'),
                                                                     Missing('baz')]})
        pattern = ("DataAssertionError: different columns:\n"
                   " 'Omitted': [Missing('foo'),\n"
                   "             Missing('bar'),\n"
                   "             Missing('baz')]")
        self.assertEqual(repr(error), pattern)

    def test_verbose_repr(self):
        reference = 'reference-data-source'
        subject = 'subject-data-source'
        error = DataAssertionError('different columns', [Missing('foo')], reference, subject)
        error._verbose = True  # <- Set verbose flag, here!

        pattern = ("DataAssertionError: different columns:\n"
                   " Missing('foo')\n"
                   "\n"
                   "REFERENCE DATA:\n"
                   "reference-data-source\n"
                   "SUBJECT DATA:\n"
                   "subject-data-source")
        self.assertEqual(repr(error), pattern)


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
            item = Invalid('foo', 'FOO', expected='bar')


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

        with self.assertRaises(ValueError):
            diff = Deviation(0, 100)  # Zero diff.

        with self.assertRaises(ValueError):
            diff = Deviation(None, 100)  # None diff.

        diff = Deviation(1, None, col1='a')  # None reference.
        self.assertRegex(repr(diff), "Deviation\(\+1, None, col1=u?'a'\)")

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
