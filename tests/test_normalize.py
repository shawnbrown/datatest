"""Tests for normalization functions."""
import sqlite3
from . import _unittest as unittest
from datatest._vendor.squint import Query
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


class TestNormalizeLazyUnchanged(unittest.TestCase):
    """Test objects that should be returned unchanged."""
    def test_nonexhaustible_iterable(self):
        data = [1, 2, 3]
        self.assertIs(_normalize_lazy(data), data)

        data = (1, 2, 3)
        self.assertIs(_normalize_lazy(data), data)

    def test_exhaustible_iterator(self):
        data = iter([1, 2, 3])
        self.assertIs(_normalize_lazy(data), data)

    def test_typediterator(self):
        data = TypedIterator(iter([1, 2, 3]), evaltype=tuple)
        self.assertIs(_normalize_lazy(data), data)


@unittest.skipIf(not squint, 'squint not found')
class TestNormalizeLazySquint(unittest.TestCase):
    """Test squint package's `Result` and `Query` objects."""
    def test_sequence_result(self):
        result_object = squint.Result([1, 2, 3, 4], evaltype=list)
        normalized = _normalize_lazy(result_object)
        self.assertIs(normalized, result_object, msg='should return original object')

    def test_iteritems_result(self):
        result_object = squint.Result(IterItems([('a', 1), ('b', 2)]), evaltype=dict)
        normalized = _normalize_lazy(result_object)
        self.assertIsInstance(normalized, IterItems)

    def test_query(self):
        query_object = squint.Query.from_object([1, 2, 3, 4])
        normalized = _normalize_lazy(query_object)
        self.assertIsInstance(normalized, squint.Result)
        self.assertEqual(normalized.evaltype, list)


class TestNormalizeLazyResultAndQuery(unittest.TestCase):
    """Test deprecated `Result` and `Query` objects."""
    def test_sequence_result(self):
        with self.assertWarns(DeprecationWarning):
            result_object = Result([1, 2, 3, 4], evaluation_type=list)
        normalized = _normalize_lazy(result_object)
        self.assertIs(normalized, result_object, msg='should return original object')

    def test_iteritems_result(self):
        with self.assertWarns(DeprecationWarning):
            result_object = Result(IterItems([('a', 1), ('b', 2)]), evaluation_type=dict)
        normalized = _normalize_lazy(result_object)
        self.assertIsInstance(normalized, IterItems)

    def test_query(self):
        with self.assertWarns(DeprecationWarning):
            query_object = Query.from_object([1, 2, 3, 4])
        normalized = _normalize_lazy(query_object)
        self.assertIsInstance(normalized, Result)
        self.assertEqual(normalized.evaluation_type, list)


@unittest.skipIf(not pandas, 'pandas not found')
class TestNormalizeLazyPandas(unittest.TestCase):
    def test_dataframe_with_rangeindex(self):
        """DataFrames using a RangeIndex should be treated as sequences."""
        data = [(1, 'a'), (2, 'b'), (3, 'c')]
        df = pandas.DataFrame(data)  # Pandas auto-assigns a RangeIndex.
        result = _normalize_lazy(df)

        self.assertEqual(list(data), data)

    def test_dataframe_with_otherindex(self):
        """DataFrames using other index types should be treated as mappings."""
        data = [(1, 'a'), (2, 'b'), (3, 'c')]
        df = pandas.DataFrame(data, index=[0, 1, 2])  # Defines an Int64Index.
        result = _normalize_lazy(df)

        expected = {0: (1, 'a'), 1: (2, 'b'), 2: (3, 'c')}
        self.assertIsInstance(result, IterItems)
        self.assertEqual(dict(result), expected)

    def test_dataframe_multiple_columns(self):
        data = [(1, 'a'), (2, 'b'), (3, 'c')]

        # RangeIndex index
        df = pandas.DataFrame(data)
        result = _normalize_lazy(df)
        self.assertEqual(list(result), data)

        # Int64Index index
        df = pandas.DataFrame(data, index=[0, 1, 2])
        result = _normalize_lazy(df)
        self.assertIsInstance(result, IterItems)
        expected = {0: (1, 'a'), 1: (2, 'b'), 2: (3, 'c')}
        self.assertEqual(dict(result), expected)

    def test_dataframe_single_column(self):
        """Single column DataFrame values should be unwrapped."""
        data = [('x',), ('y',), ('z',)]

        # RangeIndex index
        df = pandas.DataFrame(data)
        result = _normalize_lazy(df)
        self.assertEqual(list(result), ['x', 'y', 'z'])

        # Int64Index index
        df = pandas.DataFrame(data, index=[0, 1, 2])
        result = _normalize_lazy(df)
        self.assertIsInstance(result, IterItems)
        expected = {0: 'x', 1: 'y', 2: 'z'}
        self.assertEqual(dict(result), expected)

    def test_dataframe_multiindex(self):
        """Multi-index values should be tuples."""
        df = pandas.DataFrame(
            data=[('x',), ('y',), ('z',)],
            index=pandas.MultiIndex.from_tuples([(0, 0), (0, 1), (1, 0)]),
        )
        result = _normalize_lazy(df)
        self.assertIsInstance(result, IterItems)
        expected = {(0, 0): 'x', (0, 1): 'y', (1, 0): 'z'}
        self.assertEqual(dict(result), expected)

    def test_dataframe_index_error(self):
        """Indexes must contain unique values, no duplicates."""
        df = pandas.DataFrame([('x',), ('y',), ('z',)], index=[0, 0, 1])
        with self.assertRaises(ValueError):
            _normalize_lazy(df)

    @unittest.skip('skipped while changing behavior')
    def test_series_with_rangeindex(self):
        """Series using a RangeIndex should be treated as sequences."""
        data = ['x', 'y', 'z']
        s = pandas.Series(data)  # Pandas auto-assigns a RangeIndex.
        result = _normalize_lazy(s)

        self.assertEqual(list(data), data)

    @unittest.skip('skipped while changing behavior')
    def test_series_with_otherindex(self):
        """Series using other index types should be treated as mappings."""
        data = ['x', 'y', 'z']
        s = pandas.Series(data, index=[0, 1, 2])  # Defines an Int64Index.
        result = _normalize_lazy(s)

        expected = {0: 'x', 1: 'y', 2: 'z'}
        self.assertIsInstance(result, IterItems)
        self.assertEqual(dict(result), expected)

    @unittest.skip('skipped while changing behavior')
    def test_series_multiindex(self):
        """Multi-index values should be tuples."""
        s = pandas.Series(
            data=['x', 'y', 'z'],
            index=pandas.MultiIndex.from_tuples([(0, 0), (0, 1), (1, 0)]),
        )
        result = _normalize_lazy(s)
        self.assertIsInstance(result, IterItems)
        expected = {(0, 0): 'x', (0, 1): 'y', (1, 0): 'z'}
        self.assertEqual(dict(result), expected)

    @unittest.skip('skipped while changing behavior')
    def test_series_index_error(self):
        """Indexes must contain unique values, no duplicates."""
        s = pandas.Series(['x', 'y', 'z'], index=[0, 0, 1])
        with self.assertRaises(ValueError):
            _normalize_lazy(s)


@unittest.skipIf(not numpy, 'numpy not found')
class TestNormalizeLazyNumpy(unittest.TestCase):
    def test_two_dimentional_array(self):
        arr = numpy.array([['a', 'x'], ['b', 'y']])
        lazy = _normalize_lazy(arr)
        self.assertIsInstance(lazy, TypedIterator)
        self.assertEqual(lazy.fetch(), [('a', 'x'), ('b', 'y')])

    def test_two_valued_structured_array(self):
        arr = numpy.array([('a', 1), ('b', 2)],
                          dtype=[('one', 'U10'), ('two', 'i4')])
        lazy = _normalize_lazy(arr)
        self.assertIsInstance(lazy, TypedIterator)
        self.assertEqual(lazy.fetch(), [('a', 1), ('b', 2)])

    def test_two_valued_recarray_array(self):  # record array
        arr = numpy.rec.array([('a', 1), ('b', 2)],
                              dtype=[('one', 'U10'), ('two', 'i4')])
        lazy = _normalize_lazy(arr)
        self.assertIsInstance(lazy, TypedIterator)
        self.assertEqual(lazy.fetch(), [('a', 1), ('b', 2)])

    def test_one_dimentional_array(self):
        arr = numpy.array(['x', 'y', 'z'])
        lazy = _normalize_lazy(arr)
        self.assertIsInstance(lazy, TypedIterator)
        self.assertEqual(lazy.fetch(), ['x', 'y', 'z'])

    def test_single_valued_structured_array(self):
        arr = numpy.array([('x',), ('y',), ('z',)],
                          dtype=[('one', 'U10')])
        lazy = _normalize_lazy(arr)
        self.assertIsInstance(lazy, TypedIterator)
        self.assertEqual(lazy.fetch(), ['x', 'y', 'z'])

    def test_single_valued_recarray_array(self):  # record array
        arr = numpy.rec.array([('x',), ('y',), ('z',)],
                              dtype=[('one', 'U10')])
        lazy = _normalize_lazy(arr)
        self.assertIsInstance(lazy, TypedIterator)
        self.assertEqual(lazy.fetch(), ['x', 'y', 'z'])

    def test_three_dimentional_array(self):
        """Three-dimentional array normalization is not supported."""
        arr = numpy.array([[[1, 3], ['a', 'x']], [[2, 4], ['b', 'y']]])
        result = _normalize_lazy(arr)
        self.assertIs(result, arr, msg='unsupported, returns unchanged')


class TestNormalizeLazyDBAPI2Cursor(unittest.TestCase):
    def setUp(self):
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
        self.cursor = conn.cursor()

    def test_multiple_coumns(self):
        self.cursor.execute('SELECT A, B FROM mydata;')
        result = _normalize_lazy(self.cursor)
        self.assertEqual(
            list(result),
            [('x', 'foo'), ('x', 'foo'), ('y', 'foo'),
             ('y', 'bar'), ('z', 'bar'), ('z', 'bar')],
        )

    def test_single_column(self):
        """Single column selections should be unwrapped."""
        self.cursor.execute('SELECT C FROM mydata;')
        result = _normalize_lazy(self.cursor)
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

    def test_deprecated_result_object(self):
        with self.assertWarns(DeprecationWarning):
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
