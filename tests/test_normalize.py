"""Tests for normalization functions."""
from . import _unittest as unittest
from datatest._query.query import DictItems
from datatest._query.query import Result
from datatest.requirements import BaseRequirement
from datatest._utils import IterItems

from datatest._normalize import _normalize_lazy
from datatest._normalize import _normalize_eager
from datatest._normalize import normalize

try:
    import pandas
except ImportError:
    pandas = None

try:
    import numpy
except ImportError:
    numpy = None


class TestNormalizeLazy(unittest.TestCase):
    def test_unchanged(self):
        data = [1, 2, 3]
        self.assertIs(_normalize_lazy(data), data, 'should return original object')

        data = iter([1, 2, 3])
        self.assertIs(_normalize_lazy(data), data, 'should return original object')

        data = Result(iter([1, 2, 3]), evaluation_type=tuple)
        self.assertIs(_normalize_lazy(data), data, 'should return original object')

    def test_requirement(self):
        result = Result(DictItems([('a', 1), ('b', 2)]), evaluation_type=dict)
        normalized = _normalize_lazy(result)
        self.assertIsInstance(normalized, IterItems)

    @unittest.skipIf(not pandas, 'pandas not found')
    def test_normalize_pandas_dataframe(self):
        df = pandas.DataFrame([(1, 'a'), (2, 'b'), (3, 'c')])
        result = _normalize_lazy(df)
        self.assertIsInstance(result, IterItems)
        expected = {0: (1, 'a'), 1: (2, 'b'), 2: (3, 'c')}
        self.assertEqual(dict(result), expected)

        # Single column.
        df = pandas.DataFrame([('x',), ('y',), ('z',)])
        result = _normalize_lazy(df)
        self.assertIsInstance(result, IterItems)
        expected = {0: 'x', 1: 'y', 2: 'z'}
        self.assertEqual(dict(result), expected, 'single column should be unwrapped')

        # Multi-index.
        df = pandas.DataFrame([('x',), ('y',), ('z',)])
        df.index = pandas.MultiIndex.from_tuples([(0, 0), (0, 1), (1, 0)])
        result = _normalize_lazy(df)
        self.assertIsInstance(result, IterItems)
        expected = {(0, 0): 'x', (0, 1): 'y', (1, 0): 'z'}
        self.assertEqual(dict(result), expected, 'multi-index should be tuples')

        # Indexes must contain unique values, no duplicates
        df = pandas.DataFrame([('x',), ('y',), ('z',)])
        df.index = pandas.Index([0, 0, 1])  # <- Duplicate values.
        with self.assertRaises(ValueError):
            _normalize_lazy(df)

    @unittest.skipIf(not pandas, 'pandas not found')
    def test_normalize_pandas_series(self):
        # Simple, implicit index.
        s = pandas.Series(['x', 'y', 'z'])
        result = _normalize_lazy(s)
        self.assertIsInstance(result, pandas.Series)
        self.assertTrue(s.equals(result))

        # Multi-index.
        s = pandas.Series(['x', 'y', 'z'])
        s.index = pandas.MultiIndex.from_tuples([(0, 0), (0, 1), (1, 0)])
        result = _normalize_lazy(s)
        self.assertIsInstance(result, pandas.Series)
        self.assertTrue(s.equals(result))

    @unittest.skipIf(not numpy, 'numpy not found')
    def test_normalize_numpy(self):
        # Two-dimentional array.
        arr = numpy.array([['a', 'x'], ['b', 'y']])
        lazy = _normalize_lazy(arr)
        self.assertIsInstance(lazy, Result)
        self.assertEqual(lazy.fetch(), [('a', 'x'), ('b', 'y')])

        # Two-valued structured array.
        arr = numpy.array([('a', 1), ('b', 2)],
                          dtype=[('one', 'U10'), ('two', 'i4')])
        lazy = _normalize_lazy(arr)
        self.assertIsInstance(lazy, Result)
        self.assertEqual(lazy.fetch(), [('a', 1), ('b', 2)])

        # Two-valued recarray (record array).
        arr = numpy.rec.array([('a', 1), ('b', 2)],
                              dtype=[('one', 'U10'), ('two', 'i4')])
        lazy = _normalize_lazy(arr)
        self.assertIsInstance(lazy, Result)
        self.assertEqual(lazy.fetch(), [('a', 1), ('b', 2)])

        # One-dimentional array.
        arr = numpy.array(['x', 'y', 'z'])
        lazy = _normalize_lazy(arr)
        self.assertIsInstance(lazy, Result)
        self.assertEqual(lazy.fetch(), ['x', 'y', 'z'])

        # Single-valued structured array.
        arr = numpy.array([('x',), ('y',), ('z',)],
                          dtype=[('one', 'U10')])
        lazy = _normalize_lazy(arr)
        self.assertIsInstance(lazy, Result)
        self.assertEqual(lazy.fetch(), ['x', 'y', 'z'])

        # Single-valued recarray (record array).
        arr = numpy.rec.array([('x',), ('y',), ('z',)],
                              dtype=[('one', 'U10')])
        lazy = _normalize_lazy(arr)
        self.assertIsInstance(lazy, Result)
        self.assertEqual(lazy.fetch(), ['x', 'y', 'z'])

        # Three-dimentional array--conversion is not supported.
        arr = numpy.array([[[1, 3], ['a', 'x']], [[2, 4], ['b', 'y']]])
        result = _normalize_lazy(arr)
        self.assertIs(result, arr, msg='unsupported, returns unchanged')


class TestNormalizeEager(unittest.TestCase):
    def test_unchanged(self):
        """For given instances, should return original object."""
        requirement = [1, 2, 3]
        self.assertIs(_normalize_eager(requirement), requirement)

        class MyRequirement(BaseRequirement):
            def __init__(self):
                pass

            def __iter__(self):
                return iter([])

            def check_data():
                return None

        requirement = MyRequirement()
        self.assertIs(_normalize_eager(requirement), requirement)

    def test_exhaustible_type(self):
        with self.assertRaises(TypeError, msg='cannot use generic iter'):
            _normalize_eager(iter([1, 2, 3]))

        output = _normalize_eager(iter([1, 2, 3]), default_type=set)
        self.assertEqual(output, set([1, 2, 3]))

    def test_result_object(self):
        result_obj = Result(iter([1, 2, 3]), evaluation_type=tuple)
        output = _normalize_eager(result_obj)
        self.assertIsInstance(output, tuple)
        self.assertEqual(output, (1, 2, 3))

    def test_iter_items(self):
        items = IterItems(iter([(0, 'x'), (1, 'y'), (2, 'z')]))
        output = _normalize_eager(items)
        self.assertIsInstance(output, dict)
        self.assertEqual(output, {0: 'x', 1: 'y', 2: 'z'})
