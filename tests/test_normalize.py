"""Tests for normalization functions."""
import sqlite3
from . import _unittest as unittest
from datatest._vendor.squint import Result
from datatest.requirements import BaseRequirement
from datatest._utils import IterItems

from datatest._normalize import TypedIterator
from datatest._normalize import _normalize_lazy
from datatest._normalize import _normalize_eager
from datatest._normalize import normalize

try:
    import squint
except ImportError:
    squint = None

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

        data = TypedIterator(iter([1, 2, 3]), evaltype=tuple)
        self.assertIs(_normalize_lazy(data), data, 'should return original object')

    @unittest.skipIf(not squint, 'squint not found')
    def test_requirement(self):
        result = squint.Result(IterItems([('a', 1), ('b', 2)]), evaltype=dict)
        normalized = _normalize_lazy(result)
        self.assertIsInstance(normalized, IterItems)

    @unittest.skipIf(not squint, 'squint not found')
    def test_normalize_squint_query(self):
        query = squint.Query.from_object([1, 2, 3, 4])
        normalized = _normalize_lazy(query)
        self.assertIsInstance(normalized, squint.Result)
        self.assertEqual(normalized.evaltype, list)

    @unittest.skipIf(not squint, 'squint not found')
    def test_normalize_squint_result(self):
        result = squint.Result(IterItems([('a', 1), ('b', 2)]), evaltype=dict)
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
        self.assertIsInstance(lazy, TypedIterator)
        self.assertEqual(lazy.fetch(), [('a', 'x'), ('b', 'y')])

        # Two-valued structured array.
        arr = numpy.array([('a', 1), ('b', 2)],
                          dtype=[('one', 'U10'), ('two', 'i4')])
        lazy = _normalize_lazy(arr)
        self.assertIsInstance(lazy, TypedIterator)
        self.assertEqual(lazy.fetch(), [('a', 1), ('b', 2)])

        # Two-valued recarray (record array).
        arr = numpy.rec.array([('a', 1), ('b', 2)],
                              dtype=[('one', 'U10'), ('two', 'i4')])
        lazy = _normalize_lazy(arr)
        self.assertIsInstance(lazy, TypedIterator)
        self.assertEqual(lazy.fetch(), [('a', 1), ('b', 2)])

        # One-dimentional array.
        arr = numpy.array(['x', 'y', 'z'])
        lazy = _normalize_lazy(arr)
        self.assertIsInstance(lazy, TypedIterator)
        self.assertEqual(lazy.fetch(), ['x', 'y', 'z'])

        # Single-valued structured array.
        arr = numpy.array([('x',), ('y',), ('z',)],
                          dtype=[('one', 'U10')])
        lazy = _normalize_lazy(arr)
        self.assertIsInstance(lazy, TypedIterator)
        self.assertEqual(lazy.fetch(), ['x', 'y', 'z'])

        # Single-valued recarray (record array).
        arr = numpy.rec.array([('x',), ('y',), ('z',)],
                              dtype=[('one', 'U10')])
        lazy = _normalize_lazy(arr)
        self.assertIsInstance(lazy, TypedIterator)
        self.assertEqual(lazy.fetch(), ['x', 'y', 'z'])

        # Three-dimentional array--conversion is not supported.
        arr = numpy.array([[[1, 3], ['a', 'x']], [[2, 4], ['b', 'y']]])
        result = _normalize_lazy(arr)
        self.assertIs(result, arr, msg='unsupported, returns unchanged')

    def test_normalize_dbapi2_cursor(self):
        conn = sqlite3.connect(':memory:')
        conn.executescript('''
            CREATE TABLE mydata(A, B, C);
            INSERT INTO mydata VALUES('x', 'foo', 20);
            INSERT INTO mydata VALUES('x', 'foo', 30);
            INSERT INTO mydata VALUES('y', 'foo', 10);
            INSERT INTO mydata VALUES('y', 'bar', 20);
            INSERT INTO mydata VALUES('z', 'bar', 10);
            INSERT INTO mydata VALUES('z', 'bar', 10);
        ''')
        cursor = conn.cursor()

        cursor.execute('SELECT A, B FROM mydata;')
        result = _normalize_lazy(cursor)
        self.assertEqual(
            list(result),
            [('x', 'foo'), ('x', 'foo'), ('y', 'foo'),
             ('y', 'bar'), ('z', 'bar'), ('z', 'bar')],
        )

        # Check for single-value record unpacking.
        cursor.execute('SELECT C FROM mydata;')
        result = _normalize_lazy(cursor)
        self.assertEqual(list(result), [20, 30, 10, 20, 10, 10])

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

    @unittest.skipIf(not squint, 'squint not found')
    def test_squint_object(self):
        result_obj = squint.Result(iter([1, 2, 3]), evaltype=tuple)
        output = _normalize_eager(result_obj)
        self.assertIsInstance(output, tuple)
        self.assertEqual(output, (1, 2, 3))

    def test_iter_items(self):
        items = IterItems(iter([(0, 'x'), (1, 'y'), (2, 'z')]))
        output = _normalize_eager(items)
        self.assertIsInstance(output, dict)
        self.assertEqual(output, {0: 'x', 1: 'y', 2: 'z'})
