# -*- coding: utf-8 -*-
import re

# Import compatibility layers.
from . import _io as io
from . import _unittest as unittest

from datatest.__past__.api07_diffs import xBaseDifference
from datatest.__past__.api07_diffs import xExtra
from datatest.__past__.api07_diffs import xMissing
from datatest.__past__.api07_diffs import xInvalid
from datatest.__past__.api07_diffs import xDeviation
from datatest.__past__.api07_diffs import _xNOTFOUND
from datatest.__past__.api07_diffs import _xgetdiff


class TestBaseDifference(unittest.TestCase):
    def setUp(self):
        class MinimalDifference(xBaseDifference):   # Create subclass because
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

        class OtherDifference(xBaseDifference):
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
        self.assertTrue(issubclass(xExtra, xBaseDifference))
        self.assertTrue(issubclass(xMissing, xBaseDifference))


class TestInvalid(unittest.TestCase):
    """Test xInvalid."""
    def test_instantiation(self):
        xInvalid('foo')
        xInvalid('foo', expected='FOO')

    def test_repr(self):
        item = xInvalid('foo')
        self.assertEqual("xInvalid('foo')", repr(item))

        item = xInvalid(None)
        self.assertEqual("xInvalid(None)", repr(item))

        item = xInvalid(2)
        self.assertEqual("xInvalid(2)", repr(item))

    def test_expected_handling(self):
        item = xInvalid('foo', 'FOO')
        self.assertEqual("xInvalid('foo', 'FOO')", repr(item))

        # QUESTION: How should kwds be handled if keys match item or expected?
        with self.assertRaises(TypeError):
            item = xInvalid('foo', 'FOO', required='bar')


class TestDeviation(unittest.TestCase):
    """Test xDeviation."""
    def test_instantiation(self):
        xDeviation(1, 100)  # Pass without error.

    def test_repr(self):
        diff = xDeviation(1, 100)  # Simple.
        self.assertEqual("xDeviation(+1, 100)", repr(diff))

        diff = xDeviation(-1, 100)  # Simple negative.
        self.assertEqual("xDeviation(-1, 100)", repr(diff))

        diff = xDeviation(3, 50, col1='a', col2='b')  # Using kwds.
        self.assertRegex(repr(diff), "xDeviation\(\+3, 50, col1=u?'a', col2=u?'b'\)")

        diff = xDeviation(1, None, col1='a')  # None reference.
        self.assertRegex(repr(diff), "xDeviation\(\+1, None, col1=u?'a'\)")

    def test_empty_value_handling(self):
        with self.assertRaises(ValueError):
            xDeviation(0, 100)  # Zero diff.

        xDeviation(0, None)
        xDeviation(+5, None)
        xDeviation(None, 0)
        with self.assertRaises(ValueError):
            xDeviation(None, 5)  # Should be xDeviation(-5, 5)

        xDeviation(0, '')
        xDeviation(+5, '')
        xDeviation('', 0)
        with self.assertRaises(ValueError):
            xDeviation('', 5)  # Should be xDeviation(-5, 5)

        xDeviation(0, float('nan'))
        xDeviation(+5, float('nan'))
        xDeviation(float('nan'), 0)
        with self.assertRaises(ValueError):
            xDeviation(float('nan'), 5)  # Should be xDeviation(-5, 5)

        with self.assertRaises(ValueError):
            xDeviation(0, 1)  # Just no.

        # False is treated the same as zero.
        xDeviation(+5, 0)
        xDeviation(+5, False)

        with self.assertRaises(ValueError):
            xDeviation(0, 0)

        with self.assertRaises(ValueError):
            xDeviation(0, False)

        with self.assertRaises(ValueError):
            xDeviation(False, 0)

        with self.assertRaises(ValueError):
            xDeviation(False, 5)  # Should be xDeviation(-5, 5)

    def test_str(self):
        diff = xDeviation(5, 75, col1='a')
        self.assertEqual(str(diff), repr(diff))

    def test_hash(self):
        diff = xDeviation(1, 100, col1='a', col2='b')
        self.assertIsInstance(hash(diff), int)

    def test_eq(self):
        diff1 = xDeviation(1, 100)
        diff2 = xDeviation(1, 100)
        self.assertEqual(diff1, diff2)

        diff1 = xDeviation(1.0, 100.0)
        diff2 = xDeviation(1.0, 100.0)
        self.assertEqual(diff1, diff2)

        diff1 = xDeviation(1.0, 100)
        diff2 = xDeviation(1,   100)
        self.assertEqual(diff1, diff2)

        diff1 = xDeviation(1, 100.0)
        diff2 = xDeviation(1, 100)
        self.assertEqual(diff1, diff2)

        diff1 = xDeviation(1, 100, foo='aaa', bar='bbb')
        diff2 = xDeviation(1, 100, bar='bbb', foo='aaa')
        self.assertEqual(diff1, diff2)

        diff1 = xDeviation(1, 100)
        diff2 = xDeviation(1, 250)
        self.assertNotEqual(diff1, diff2)

        diff1 = xDeviation(+1, 100)
        diff2 = "xDeviation(+1, 100)"
        self.assertNotEqual(diff1, diff2)

    def test_repr_eval(self):
        diff = xDeviation(+1, 100)
        self.assertEqual(diff, eval(repr(diff)))  # Test __repr__ eval

        diff = xDeviation(-1, 100, col4='foo', col5='bar')
        self.assertEqual(diff, eval(repr(diff)))  # Test __repr__ eval


class Test_getdiff(unittest.TestCase):
    def test_numeric_vs_numeric(self):
        diff = _xgetdiff(5, 6)
        self.assertEqual(diff, xDeviation(-1, 6))

    def test_numeric_vs_none(self):
        diff = _xgetdiff(5, None)
        self.assertEqual(diff, xDeviation(+5, None))

        diff = _xgetdiff(0, None)
        self.assertEqual(diff, xDeviation(+0, None))

    def test_none_vs_numeric(self):
        diff = _xgetdiff(None, 6)                   # For None vs non-zero,
        self.assertEqual(diff, xDeviation(-6, 6))  # difference is calculated
                                                   # as 0 - other.

        diff = _xgetdiff(None, 0)                     # For None vs zero,
        self.assertEqual(diff, xDeviation(None, 0))  # difference remains None.

    def test_object_vs_object(self):
        """Non-numeric comparisons return xInvalid type."""
        diff = _xgetdiff('a', 'b')
        self.assertEqual(diff, xInvalid('a', 'b'))

        diff = _xgetdiff(5, 'b')
        self.assertEqual(diff, xInvalid(5, 'b'))

        diff = _xgetdiff('a', 6)
        self.assertEqual(diff, xInvalid('a', 6))

        diff = _xgetdiff(float('nan'), 6)
        self.assertEqual(diff, xInvalid(float('nan'), 6))

        diff = _xgetdiff(5, float('nan'))
        self.assertEqual(diff, xInvalid(5, float('nan')))

        fn = lambda x: True
        diff = _xgetdiff('a', fn)
        self.assertEqual(diff, xInvalid('a', fn))

        regex = re.compile('^test$')
        diff = _xgetdiff('a', regex)
        self.assertEqual(diff, xInvalid('a', re.compile('^test$')))

    def test_notfound_comparisons(self):
        diff = _xgetdiff('a', _xNOTFOUND)
        self.assertEqual(diff, xExtra('a'))

        diff = _xgetdiff(_xNOTFOUND, 'b')
        self.assertEqual(diff, xMissing('b'))

        # For numeric comparisons, _xNOTFOUND behaves like None.
        diff = _xgetdiff(5, _xNOTFOUND)
        self.assertEqual(diff, xDeviation(+5, None))

        diff = _xgetdiff(0, _xNOTFOUND)
        self.assertEqual(diff, xDeviation(0, None))

        diff = _xgetdiff(_xNOTFOUND, 6)
        self.assertEqual(diff, xDeviation(-6, 6))  # <- Assymetric behavior
                                                   #    (see None vs numeric)!

        diff = _xgetdiff(_xNOTFOUND, 0)
        self.assertEqual(diff, xDeviation(None, 0))

    def test_keywords(self):
        """Keywords should be passed to diff objet."""
        diff = _xgetdiff(5, 6, col1='AAA')
        self.assertEqual(diff, xDeviation(-1, 6, col1='AAA'))

        diff = _xgetdiff('a', 6, col1='AAA')
        self.assertEqual(diff, xInvalid('a', 6, col1='AAA'))

        diff = _xgetdiff(_xNOTFOUND, 6, col1='AAA')
        self.assertEqual(diff, xDeviation(-6, 6, col1='AAA'))

    def test_is_common(self):
        """If requirement is common it should be omitted from xInvalid
        difference (but not from xDeviation differences).
        """
        diff = _xgetdiff('a', 6, is_common=True)
        self.assertEqual(diff, xInvalid('a'))

        diff = _xgetdiff(_xNOTFOUND, 6, is_common=True)
        self.assertEqual(diff, xDeviation(-6, 6))

    def test_same(self):
        """The _xgetdiff() function returns differences for objects that
        are KNOWN TO BE DIFFERENT--it does not test for differences
        itself.
        """
        diff = _xgetdiff('a', 'a')
        self.assertEqual(diff, xInvalid('a', 'a'))

        diff = _xgetdiff(None, None)
        self.assertEqual(diff, xInvalid(None, None))
