# -*- coding: utf-8 -*-
import csv
import os
import sqlite3
import sys
import tempfile
import warnings

# Import compatiblity layers and helpers.
from . import _io as io
from . import _unittest as unittest
from .common import MkdtempTestCase
from datatest._collections import namedtuple
from datatest._decimal import Decimal

# Import related objects.
from datatest.sourceresult import ResultSet
from datatest.sourceresult import ResultMapping

# Import code to test.
from datatest.source import BaseSource
from datatest.source import _TemporarySqliteTable
from datatest.source import SqliteSource
from datatest.source import CsvSource
from datatest.source import MultiSource


def _make_csv_file(fieldnames, datarows):
    """Helper function to make CSV file-like object using *fieldnames*
    (a list of field names) and *datarows* (a list of lists containing
    the row values).
    """
    init_string = []
    init_string.append(','.join(fieldnames)) # Concat cells into row.
    for row in datarows:
        init_string.append(','.join(row))    # Concat cells into row.
    init_string = '\n'.join(init_string)     # Concat rows into final string.
    return io.StringIO(init_string)


class MinimalSource(BaseSource):
    """Minimal data source implementation for testing."""
    def __init__(self, data, fieldnames):
        self._data = data
        self._fieldnames = fieldnames

    def __repr__(self):
        return self.__class__.__name__

    def __iter__(self):
        for row in self._data:
            yield dict(zip(self._fieldnames, row))

    def columns(self):
        return self._fieldnames


class TestBaseSource(unittest.TestCase):
    fieldnames = ['label1', 'label2', 'value']
    testdata = [['a', 'x', '17'],
                ['a', 'x', '13'],
                ['a', 'y', '20'],
                ['a', 'z', '15'],
                ['b', 'z', '5' ],
                ['b', 'y', '40'],
                ['b', 'x', '25']]
    def setUp(self):
        self.datasource = MinimalSource(self.testdata, self.fieldnames)

    def test_for_datasource(self):
        msg = '{0} missing `datasource` attribute.'
        msg = msg.format(self.__class__.__name__)
        self.assertTrue(hasattr(self, 'datasource'), msg)

    def test_iter(self):
        """Test __iter__."""
        results = [row for row in self.datasource]

        expected = [
            {'label1': 'a', 'label2': 'x', 'value': '17'},
            {'label1': 'a', 'label2': 'x', 'value': '13'},
            {'label1': 'a', 'label2': 'y', 'value': '20'},
            {'label1': 'a', 'label2': 'z', 'value': '15'},
            {'label1': 'b', 'label2': 'z', 'value': '5' },
            {'label1': 'b', 'label2': 'y', 'value': '40'},
            {'label1': 'b', 'label2': 'x', 'value': '25'},
        ]
        self.assertEqual(expected, results)

    def test_filter_iter(self):
        """Test filter iterator."""
        testdata = [
            {'label1': 'a', 'label2': 'x', 'value': '17'},
            {'label1': 'a', 'label2': 'x', 'value': '13'},
            {'label1': 'a', 'label2': 'y', 'value': '20'},
            {'label1': 'a', 'label2': 'z', 'value': '15'},
            {'label1': 'b', 'label2': 'z', 'value': '5' },
            {'label1': 'b', 'label2': 'y', 'value': '40'},
            {'label1': 'b', 'label2': 'x', 'value': '25'},
        ]

        # Filter by single value (where label1 is 'a').
        results = self.datasource._BaseSource__filter_by(label1='a')
        results = list(results)
        expected = [
            {'label1': 'a', 'label2': 'x', 'value': '17'},
            {'label1': 'a', 'label2': 'x', 'value': '13'},
            {'label1': 'a', 'label2': 'y', 'value': '20'},
            {'label1': 'a', 'label2': 'z', 'value': '15'},
        ]
        self.assertEqual(expected, results)

        # Filter by multiple values (where label2 is 'x' OR 'y').
        results = self.datasource._BaseSource__filter_by(label2=['x', 'y'])
        results = list(results)
        expected = [
            {'label1': 'a', 'label2': 'x', 'value': '17'},
            {'label1': 'a', 'label2': 'x', 'value': '13'},
            {'label1': 'a', 'label2': 'y', 'value': '20'},
            {'label1': 'b', 'label2': 'y', 'value': '40'},
            {'label1': 'b', 'label2': 'x', 'value': '25'},
        ]
        self.assertEqual(expected, results)

        # Filter by multiple columns (where label1 is 'a', label2 is 'x' OR 'y').
        results = self.datasource._BaseSource__filter_by(label1='a',
                                                         label2=['x', 'y'])
        results = list(results)
        expected = [
            {'label1': 'a', 'label2': 'x', 'value': '17'},
            {'label1': 'a', 'label2': 'x', 'value': '13'},
            {'label1': 'a', 'label2': 'y', 'value': '20'},
        ]
        self.assertEqual(results, expected)

    def test_columns(self):
        header = self.datasource.columns()
        self.assertEqual(header, ['label1', 'label2', 'value'])

    def test_mapreduce(self):
        mapreduce = self.datasource.mapreduce

        # No keys, single *columns* value.
        self.assertEqual(40, mapreduce(int, max, 'value'))

        # No keys, multiple *columns*.
        mapper = lambda a: (a[0], int(a[1]))
        reducer = lambda x, y: (min(x[0], y[0]), max(x[1], y[1]))
        #tup = namedtuple('tup', ['label1', 'value'])
        #mapper = lambda a: tup(a.label1, int(a.value))
        #reducer = lambda x, y: tup(min(x.label1, y.label1), max(x.value, y.value))
        expected = ('a', 40)
        self.assertEqual(expected, mapreduce(mapper, reducer, ['label1', 'value']))

        # No keys, missing column.
        with self.assertRaises(TypeError):
            self.assertEqual(None, mapreduce(int, max))

        # Single group_by column.
        expected = {'a': 20, 'b': 40}
        self.assertEqual(expected, mapreduce(int, max, 'value', 'label1'))
        self.assertEqual(expected, mapreduce(int, max, 'value', ['label1']))  # 1-item container

        # Two group_by columns.
        expected = {
            ('a', 'x'): 17,
            ('a', 'y'): 20,
            ('a', 'z'): 15,
            ('b', 'z'):  5,
            ('b', 'y'): 40,
            ('b', 'x'): 25,
        }
        self.assertEqual(expected, mapreduce(int, max, 'value', ['label1', 'label2']))

        # Group by with filter.
        expected = {'x': 17, 'y': 20, 'z': 15}
        self.assertEqual(expected, mapreduce(int, max, 'value', 'label2', label1='a'))

        # Attempt to reduce column that does not exist.
        with self.assertRaises(LookupError):
            result = mapreduce(int, max, 'value_x')

        # Tuple argument for mapper.
        mapper = lambda a: (int(a[0]), a[1])
        maxmin = lambda x, y: (max(x[0], y[0]), min(x[1], y[1]))
        expected = {'a': (20, 'x'), 'b': (40, 'x')}
        self.assertEqual(expected, mapreduce(mapper, maxmin, ['value', 'label2'], 'label1'))

        # Namedtuple argument for mapper.
        #mapper = lambda a: (int(a.value), a.label2)  # <- Using namedtuples.
        #maxmin = lambda x, y: (max(x[0], y[0]), min(x[1], y[1]))
        #expected = {'a': (20, 'x'), 'b': (40, 'x')}
        #self.assertEqual(expected, mapreduce(mapper, maxmin, ['value', 'label2'], 'label1'))

        # Tuple argument for reducer.
        maketwo = lambda x: (int(x), int(x))
        maxmin = lambda x, y: (max(x[0], y[0]), min(x[1], y[1]))
        expected = {'a': (20, 13), 'b': (40, 5)}
        self.assertEqual(expected, mapreduce(maketwo, maxmin, 'value', 'label1'))

    def test_reduce(self):
        reduce = self.datasource.reduce

        def maximum(x, y):
            try:
                y = float(y)
            except TypeError:
                return x

            try:
                return max(x, y)
            except TypeError:
                return y

        # No group_by.
        msg = 'when group_by is omitted, should return raw result not a ResultMapping'
        self.assertEqual(40.0, reduce(maximum, 'value'), msg=msg)

        # Callable.
        column = lambda row: row['value']
        self.assertEqual(40.0, reduce(maximum, column), msg=msg)

        # No group_by, missing column.
        with self.assertRaises(TypeError):
            self.assertEqual(None, reduce(maximum))

        # No group_by, callable-column (reimplements count).
        function = lambda x, y: x + y
        column = lambda row: 1
        self.assertEqual(7, reduce(function, column, initializer=0))

        # Single group_by column.
        expected = {'a': 20.0, 'b': 40.0}
        self.assertEqual(expected, reduce(maximum, 'value', 'label1'))
        self.assertEqual(expected, reduce(maximum, 'value', ['label1']))  # 1-item container

        # Two group_by columns.
        expected = {
            ('a', 'x'): 17.0,
            ('a', 'y'): 20.0,
            ('a', 'z'): 15.0,
            ('b', 'z'):  5.0,
            ('b', 'y'): 40.0,
            ('b', 'x'): 25.0,
        }
        self.assertEqual(expected, reduce(maximum, 'value', ['label1', 'label2']))

        # Group by with filter.
        expected = {'x': 17.0, 'y': 20.0, 'z': 15.0}
        self.assertEqual(expected, reduce(maximum, 'value', 'label2', label1='a'))

        # Attempt to reduce column that does not exist.
        with self.assertRaises(LookupError):
            result = reduce(maximum, 'value_x')

    def test_sum(self):
        sum = self.datasource.sum

        self.assertEqual(135, sum('value'))

        expected = {'a': 65, 'b': 70}
        self.assertEqual(expected, sum('value', 'label1'))

        expected = {('a',): 65, ('b',): 70}
        self.assertEqual(expected, sum('value', ['label1']))

        expected = {
            ('a', 'x'): 30,
            ('a', 'y'): 20,
            ('a', 'z'): 15,
            ('b', 'z'): 5,
            ('b', 'y'): 40,
            ('b', 'x'): 25,
        }
        self.assertEqual(expected, sum('value', ['label1', 'label2']))

        expected = {'x': 30, 'y': 20, 'z': 15}
        self.assertEqual(expected, sum('value', 'label2', label1='a'))

        # Test multiple *columns*:

        self.assertEqual((135, 135), sum(['value', 'value']))

        expected = {'x': (30, 30), 'y': (20, 20), 'z': (15, 15)}
        self.assertEqual(expected, sum(['value', 'value'], 'label2', label1='a'))

    def test_count(self):
        count = self.datasource.count

        self.assertEqual(7, count())

        expected = {'a': 4, 'b': 3}
        self.assertEqual(expected, count('label1'))

        expected = {('a',): 4, ('b',): 3}
        self.assertEqual(expected, count(['label1']))

        expected = {
            ('a', 'x'): 2,
            ('a', 'y'): 1,
            ('a', 'z'): 1,
            ('b', 'z'): 1,
            ('b', 'y'): 1,
            ('b', 'x'): 1,
        }
        self.assertEqual(expected, count(['label1', 'label2']))

        expected = {'x': 2, 'y': 1, 'z': 1}
        self.assertEqual(expected, count('label2', label1='a'))

    def test_distinct(self):
        distinct = self.datasource.distinct

        # Test single column.
        expected = ['a', 'b']
        self.assertEqual(expected, distinct('label1'))
        self.assertEqual(expected, distinct(['label1']))

        # Test single column wrapped in iterable (list).
        expected = [('a',), ('b',)]
        self.assertEqual(expected, distinct('label1'))
        self.assertEqual(expected, distinct(['label1']))

        # Test multiple columns.
        expected = [
            ('a', 'x'),
            ('a', 'y'),
            ('a', 'z'),
            ('b', 'z'),  # <- ordered (if possible)
            ('b', 'y'),  # <- ordered (if possible)
            ('b', 'x'),  # <- ordered (if possible)
        ]
        self.assertEqual(expected, distinct(['label1', 'label2']))

        # Test multiple columns with filter.
        expected = [('a', 'x'),
                    ('a', 'y'),
                    ('b', 'y'),
                    ('b', 'x')]
        self.assertEqual(expected, distinct(['label1', 'label2'], label2=['x', 'y']))

        # Test multiple columns with filter on non-grouped column.
        expected = [('a', '17'),
                    ('a', '13'),
                    ('b', '25')]
        self.assertEqual(expected, distinct(['label1', 'value'], label2='x'))

        # Test when specified column is missing.
        msg = 'Error should reference missing column.'
        with self.assertRaisesRegex(Exception, 'label3', msg=msg):
            result = distinct(['label1', 'label3'], label2='x')

    def test_assert_columns_exist(self):
        self.datasource._assert_columns_exist('label1')
        self.datasource._assert_columns_exist(['label1'])
        self.datasource._assert_columns_exist(['label1', 'label2'])

        with self.assertRaisesRegex(LookupError, "'label_x' not in \w+Source"):
            self.datasource._assert_columns_exist('label_x')


class TestTemporarySqliteTable(unittest.TestCase):
    def test_assert_unique(self):
        # Pass without error.
        _TemporarySqliteTable._assert_unique(['foo', 'bar'])

        with self.assertRaises(ValueError):
            _TemporarySqliteTable._assert_unique(['foo', 'foo'])

    def test_normalize_column(self):
        result = _TemporarySqliteTable._normalize_column('foo')
        self.assertEqual('"foo"', result)

        result = _TemporarySqliteTable._normalize_column('foo bar')
        self.assertEqual('"foo bar"', result)

        result = _TemporarySqliteTable._normalize_column('foo "bar" baz')
        self.assertEqual('"foo ""bar"" baz"', result)

    def test_create_table_statement(self):
        stmnt = _TemporarySqliteTable._create_table_statement('mytable', ['col1', 'col2'])
        self.assertEqual('CREATE TEMPORARY TABLE mytable ("col1", "col2")', stmnt)

    def test_insert_into_statement(self):
        stmnt, param = _TemporarySqliteTable._insert_into_statement('mytable', ['val1a', 'val2a'])
        self.assertEqual('INSERT INTO mytable VALUES (?, ?)', stmnt)
        self.assertEqual(['val1a', 'val2a'], param)

        with self.assertRaisesRegex(AssertionError, 'must be non-string container'):
            _TemporarySqliteTable._insert_into_statement('mytable', 'val1')

    def test_make_new_table(self):
        tablename = _TemporarySqliteTable._make_new_table(existing=[])
        self.assertEqual(tablename, 'tbl0')

        tablename = _TemporarySqliteTable._make_new_table(existing=['tbl0', 'foo'])
        self.assertEqual(tablename, 'tbl1')

        tablename = _TemporarySqliteTable._make_new_table(existing=['tbl0', 'foo', 'tbl1'])
        self.assertEqual(tablename, 'tbl2')

    def test_connection(self):
        cols = ('COL_A', 'COL_B')
        data = [
            ('1A', '1B'),
            ('2A', '2B')
        ]

        instance_x = _TemporarySqliteTable(data, cols)
        instance_y = _TemporarySqliteTable(data, cols)
        msg = 'Unless otherwise specified, instances should share the same connection.'
        self.assertIs(instance_x.connection, instance_y.connection)

        connection = sqlite3.connect(':memory:')
        instance_z = _TemporarySqliteTable(data, cols, connection)
        msg = 'When specified, an alternative connection should be used.'
        self.assertIs(connection, instance_z.connection)
        self.assertIsNot(instance_x.connection, instance_z.connection)

    def test_init_with_tuple(self):
        # Test list of tuples.
        columns = ['foo', 'bar', 'baz']
        data = [
            ('a', 'x', '1'),
            ('b', 'y', '2'),
            ('c', 'z', '3'),
        ]
        temptable = _TemporarySqliteTable(data, columns)

        self.assertEqual(temptable.columns, columns)

        cursor = temptable.connection.cursor()
        cursor.execute('SELECT * FROM ' + temptable.name)
        result = list(cursor)
        self.assertEqual(data, result)

        # Test too few columns.
        columns = ['foo', 'bar']
        with self.assertRaises(sqlite3.OperationalError):
            temptable = _TemporarySqliteTable(data, columns)

        # Test too many columns.
        columns = ['foo', 'bar', 'baz', 'qux']
        with self.assertRaises(sqlite3.OperationalError):
            temptable = _TemporarySqliteTable(data, columns)

    def test_init_with_dict(self):
        data = [
            {'foo': 'a', 'bar': 'x', 'baz': '1'},
            {'foo': 'b', 'bar': 'y', 'baz': '2'},
            {'foo': 'c', 'bar': 'z', 'baz': '3'},
        ]

        # Test basics.
        columns = ['foo', 'bar', 'baz']
        temptable = _TemporarySqliteTable(data, columns)
        cursor = temptable._connection.cursor()
        cursor.execute('SELECT * FROM {0}'.format(temptable.name))
        expected = [
            ('a', 'x', '1'),
            ('b', 'y', '2'),
            ('c', 'z', '3'),
        ]
        self.assertEqual(expected, list(cursor))

        # Test same data with different column order.
        columns = ['baz', 'foo', 'bar']
        temptable = _TemporarySqliteTable(data, columns)
        cursor = temptable._connection.cursor()
        cursor.execute('SELECT * FROM {0}'.format(temptable.name))
        expected = [
            ('1', 'a', 'x'),
            ('2', 'b', 'y'),
            ('3', 'c', 'z'),
        ]
        self.assertEqual(expected, list(cursor))

        # Test too few columns (should this fail?)
        #columns = ['foo', 'bar']
        #with self.assertRaises(AssertionError):
        #    temptable = _TemporarySqliteTable(data, columns)

        # Test too many columns.
        columns = ['foo', 'bar', 'baz', 'qux']
        with self.assertRaises(KeyError):
            temptable = _TemporarySqliteTable(data, columns)

        # Wrong column names (but correct number of them).
        columns = ['qux', 'quux', 'corge']
        with self.assertRaises(KeyError):
            temptable = _TemporarySqliteTable(data, columns)

    def test_init_without_columns_arg(self):
        data_dict = [
            {'foo': 'a', 'bar': 'x', 'baz': '1'},
            {'foo': 'b', 'bar': 'y', 'baz': '2'},
            {'foo': 'c', 'bar': 'z', 'baz': '3'},
        ]

        # Iterable of dict-rows.
        temptable = _TemporarySqliteTable(data_dict)
        cursor = temptable._connection.cursor()
        cursor.execute('SELECT * FROM {0}'.format(temptable.name))
        expected = [
            ('x', '1', 'a'),
            ('y', '2', 'b'),
            ('z', '3', 'c'),
        ]
        self.assertEqual(expected, list(cursor))

        # Iterable of namedtuple-rows.
        ntup = namedtuple('ntup', ['foo', 'bar', 'baz'])
        data_namedtuple = [
            ntup('a', 'x', '1'),
            ntup('b', 'y', '2'),
            ntup('c', 'z', '3'),
        ]
        temptable = _TemporarySqliteTable(data_namedtuple)
        cursor = temptable._connection.cursor()
        cursor.execute('SELECT * FROM {0}'.format(temptable.name))
        expected = [
            ('a', 'x', '1'),
            ('b', 'y', '2'),
            ('c', 'z', '3'),
        ]
        self.assertEqual(expected, list(cursor))

        # Type that doesn't support omitted columns (should raise TypeError).
        data_tuple = [('a', 'x', '1'), ('b', 'y', '2'), ('c', 'z', '3')]
        regex = ('columns argument can only be omitted if data '
                 'contains dict-rows or namedtuple-rows')
        with self.assertRaisesRegex(TypeError, regex):
            temptable = _TemporarySqliteTable(data_tuple)


class TestSqliteSource(TestBaseSource):
    def setUp(self):
        tablename = 'testtable'
        connection = sqlite3.connect(':memory:')
        cursor = connection.cursor()
        cursor.execute("CREATE TABLE testtable (label1, label2, value)")
        for values in self.testdata:
            cursor.execute("INSERT INTO testtable VALUES (?, ?, ?)", values)
        connection.commit()

        self.datasource = SqliteSource(connection, tablename)

    def test_where_clause(self):
        # No key-word args.
        clause, params = SqliteSource._build_where_clause()
        self.assertEqual(clause, '')
        self.assertEqual(params, [])

        # Single condition (where label1 equals 'a').
        clause, params = SqliteSource._build_where_clause(label1='a')
        self.assertEqual(clause, 'label1=?')
        self.assertEqual(params, ['a'])

        # Multiple conditions (where label1 equals 'a' AND label2 equals 'x').
        clause, params = SqliteSource._build_where_clause(label1='a', label2='x')
        self.assertEqual(clause, 'label1=? AND label2=?')
        self.assertEqual(params, ['a', 'x'])

        # Compound condition (where label1 equals 'a' OR 'b').
        clause, params = SqliteSource._build_where_clause(label1=('a', 'b'))
        self.assertEqual(clause, 'label1 IN (?, ?)')
        self.assertEqual(params, ['a', 'b'])

        # Mixed conditions (where label1 equals 'a' OR 'b' AND label2 equals 'x').
        clause, params = SqliteSource._build_where_clause(label1=('a', 'b'), label2='x')
        self.assertEqual(clause, 'label1 IN (?, ?) AND label2=?')
        self.assertEqual(params, ['a', 'b', 'x'])

    def test_normalize_column(self):
        result = SqliteSource._normalize_column('foo')
        self.assertEqual('"foo"', result)

        result = SqliteSource._normalize_column('foo bar')
        self.assertEqual('"foo bar"', result)

        result = SqliteSource._normalize_column('foo "bar" baz')
        self.assertEqual('"foo ""bar"" baz"', result)

    def test_from_records(self):
        """Test from_records method (wrapper for _TemporarySqliteTable class)."""
        # Test tuples.
        columns = ['foo', 'bar', 'baz']
        data = [
            ('a', 'x', '1'),
            ('b', 'y', '2'),
            ('c', 'z', '3'),
        ]
        source = SqliteSource.from_records(data, columns)

        expected = [
            {'foo': 'a', 'bar': 'x', 'baz': '1'},
            {'foo': 'b', 'bar': 'y', 'baz': '2'},
            {'foo': 'c', 'bar': 'z', 'baz': '3'},
        ]
        self.assertEqual(expected, list(source))

        # Test dict.
        columns = ['foo', 'bar', 'baz']
        data = [
            {'foo': 'a', 'bar': 'x', 'baz': '1'},
            {'foo': 'b', 'bar': 'y', 'baz': '2'},
            {'foo': 'c', 'bar': 'z', 'baz': '3'},
        ]
        source = SqliteSource.from_records(data, columns)
        self.assertEqual(data, list(source))

        # Test omitted *columns* argument.
        data_dict = [
            {'foo': 'a', 'bar': 'x', 'baz': '1'},
            {'foo': 'b', 'bar': 'y', 'baz': '2'},
            {'foo': 'c', 'bar': 'z', 'baz': '3'},
        ]
        source = SqliteSource.from_records(data_dict)
        self.assertEqual(data_dict, list(source))

    def test_create_index(self):
        cursor = self.datasource._connection.cursor()

        # There should be no indexes initially.
        cursor.execute("PRAGMA INDEX_LIST('testtable')")
        self.assertEqual(cursor.fetchall(), [])

        # Add single-column index.
        self.datasource.create_index('label1')  # <- CREATE INDEX!
        cursor.execute("PRAGMA INDEX_LIST('testtable')")
        results = [tup[1] for tup in cursor.fetchall()]
        self.assertEqual(results, ['idx_testtable_label1'])

        # Add multi-column index.
        self.datasource.create_index('label2', 'value')  # <- CREATE INDEX!
        cursor.execute("PRAGMA INDEX_LIST('testtable')")
        results = sorted(tup[1] for tup in cursor.fetchall())
        self.assertEqual(results, ['idx_testtable_label1', 'idx_testtable_label2_value'])

        # Duplicate of first, single-column index should have no effect.
        self.datasource.create_index('label1')  # <- CREATE INDEX!
        cursor.execute("PRAGMA INDEX_LIST('testtable')")
        results = sorted(tup[1] for tup in cursor.fetchall())
        self.assertEqual(results, ['idx_testtable_label1', 'idx_testtable_label2_value'])


class TestCsvSource(TestBaseSource):
    def setUp(self):
        fh = _make_csv_file(self.fieldnames, self.testdata)
        self.datasource = CsvSource(fh)

    def test_empty_file(self):
        pass
        #file exists but is empty should fail, too!


class TestCsvSource_FileHandling(unittest.TestCase):
    @staticmethod
    def _get_filelike(string, encoding=None):
        """Return file-like stream object."""
        filelike = io.BytesIO(string)
        if encoding and sys.version >= '3':
            filelike = io.TextIOWrapper(filelike, encoding=encoding)
        return filelike

    def test_filelike_object(self):
        fh = self._get_filelike(b'label1,label2,value\n'
                                b'a,x,18\n'
                                b'a,x,13\n'
                                b'a,y,20\n'
                                b'a,z,15\n', encoding='ascii')
        CsvSource(fh)  # Pass without error.

        fh = self._get_filelike(b'label1,label2,value\n'
                                b'a,x,18\n'
                                b'a,x,13\n'
                                b'a,\xc3\xb1,20\n'  # \xc3\xb1 is utf-8 literal for ñ
                                b'a,z,15\n', encoding='utf-8')
        CsvSource(fh)  # Pass without error.

        fh = self._get_filelike(b'label1,label2,value\n'
                                b'a,x,18\n'
                                b'a,x,13\n'
                                b'a,\xf1,20\n'  # '\xf1' is iso8859-1 for ñ
                                b'a,z,15\n', encoding='iso8859-1')
        CsvSource(fh, encoding='iso8859-1')  # Pass without error.

    def test_bad_filelike_object(self):
        with self.assertRaises(UnicodeDecodeError):
            fh = self._get_filelike(b'label1,label2,value\n'
                                    b'a,x,18\n'
                                    b'a,x,13\n'
                                    b'a,\xf1,20\n'  # '\xf1' is iso8859-1 for ñ, not utf-8!
                                    b'a,z,15\n', encoding='utf-8')
            CsvSource(fh, encoding='utf-8')  # Raises exception!


class TestCsvSource_ActualFileHandling(MkdtempTestCase):
    def test_utf8(self):
        with open('utf8file.csv', 'wb') as fh:
            filecontents = (b'label1,label2,value\n'
                            b'a,x,18\n'
                            b'a,x,13\n'
                            b'a,\xc3\xb1,20\n'  # \xc3\xb1 is utf-8 literal for ñ
                            b'a,z,15\n')
            fh.write(filecontents)
            abspath = os.path.abspath(fh.name)

        CsvSource(abspath)  # Pass without error.

        CsvSource(abspath, encoding='utf-8')  # Pass without error.

        msg = 'If wrong encoding is specified, should raise exception.'
        with self.assertRaises(UnicodeDecodeError, msg=msg):
            CsvSource(abspath, encoding='ascii')

    def test_iso88591(self):
        with open('iso88591file.csv', 'wb') as fh:
            filecontents = (b'label1,label2,value\n'
                            b'a,x,18\n'
                            b'a,x,13\n'
                            b'a,\xf1,20\n'  # '\xf1' is iso8859-1 for ñ, not utf-8!
                            b'a,z,15\n')
            fh.write(filecontents)
            abspath = os.path.abspath(fh.name)

        CsvSource(abspath, encoding='iso8859-1')  # Pass without error.

        msg = ('When encoding us unspecified, tries UTF-8 first then '
               'fallsback to ISO-8859-1 and raises a Warning.')
        with self.assertWarns(UserWarning, msg=msg):
            CsvSource(abspath)

        msg = 'If wrong encoding is specified, should raise exception.'
        with self.assertRaises(UnicodeDecodeError, msg=msg):
            CsvSource(abspath, encoding='utf-8')

    def test_file_handle(self):
        if sys.version_info[0] > 2:
            correct_mode = 'rt'  # Python 3, requires text-mode.
            incorrect_mode = 'rb'
        else:
            correct_mode = 'rb'  # Python 2, requires binary-mode.
            incorrect_mode = 'rt'

        filename = 'utf8file.csv'
        with open(filename, 'wb') as fh:
            filecontents = (b'label1,label2,value\n'
                            b'a,x,18\n'
                            b'a,x,13\n'
                            b'a,\xc3\xb1,20\n'  # \xc3\xb1 is utf-8 literal for ñ
                            b'a,z,15\n')
            fh.write(filecontents)

        with open(filename, correct_mode) as fh:
            CsvSource(fh, encoding='utf-8')  # Pass without error.

        with self.assertRaises(Exception):
            with open(filename, incorrect_mode) as fh:
                CsvSource(fh, encoding='utf-8')  # Raise exception.


class TestMultiSource(TestBaseSource):
    def setUp(self):
        fieldnames1 = ['label1', 'label2', 'value']
        testdata1 = [['a', 'x', '17'],
                     ['a', 'x', '13'],
                     ['a', 'y', '20'],
                     ['a', 'z', '15']]

        fieldnames2 = ['label1', 'label2', 'value']
        testdata2 = [['b', 'z', '5' ],
                     ['b', 'y', '40'],
                     ['b', 'x', '25']]

        source1 = MinimalSource(testdata1, fieldnames1)
        source2 = MinimalSource(testdata2, fieldnames2)
        self.datasource = MultiSource(source1, source2)

    def test_sum_heterogeneous_columns(self):
        testdata1 = [['a', 'x', '1'],
                     ['a', 'y', '1']]
        src1 = MinimalSource(testdata1, ['label1', 'label2', 'value'])

        testdata2 = [['a', '5', '1'],
                     ['b', '5', '1'],
                     ['b', '5', '1']]
        src2 = MinimalSource(testdata2, ['label1', 'altval', 'value'])
        source = MultiSource(src1, src2)

        self.assertEqual(5, source.sum('value'))

        expected = {'a': 3, 'b': 2}
        self.assertEqual(expected, source.sum('value', 'label1'))

        expected = {'a': 5, 'b': 10}
        self.assertEqual(expected, source.sum('altval', 'label1'))

        expected = {'a': 1}
        self.assertEqual(expected, source.sum('value', 'label1', label2='x'))

    def test_count_heterogeneous_columns(self):
        testdata1 = [['a', 'x', '2'],
                     ['a', 'y', '2']]
        src1 = MinimalSource(testdata1, ['label1', 'label2', 'value'])

        testdata2 = [['a', '5', '2'],
                     ['b', '5', '2'],
                     ['b', '5', '2']]
        src2 = MinimalSource(testdata2, ['label1', 'altval', 'value'])
        source = MultiSource(src1, src2)

        expected = {'a': 3, 'b': 2}
        self.assertEqual(expected, source.count('label1'))

        expected = {'a': 1}
        self.assertEqual(expected, source.count('label1', label2='x'))


class TestMixedMultiSource(TestBaseSource):
    """Test MultiSource with sub-sources of different types."""
    def setUp(self):
        fieldnames1 = ['label1', 'label2', 'value']
        testdata1 = [['a', 'x', '17'],
                     ['a', 'x', '13'],
                     ['a', 'y', '20'],
                     ['a', 'z', '15']]
        minimal_source = MinimalSource(testdata1, fieldnames1)

        fieldnames2 = ['label1', 'label2', 'value']
        testdata2 = [['b', 'z', '5' ],
                     ['b', 'y', '40'],
                     ['b', 'x', '25']]
        fh = _make_csv_file(fieldnames2, testdata2)
        csv_source = CsvSource(fh)

        self.datasource = MultiSource(minimal_source, csv_source)


class TestMultiSourceDifferentColumns(unittest.TestCase):
    """Test MultiSource with sub-sources that use different columns."""
    def setUp(self):
        fieldnames1 = ['label1', 'label2', 'value']
        testdata1 = [['a',            'x',    '17'],
                     ['a',            'x',    '13'],
                     ['a',            'y',    '20'],
                     ['b',            'z',     '5']]

        fieldnames2 = ['label1', 'label3', 'value', 'other_value']
        testdata2 = [['a',          'zzz',    '15',           '3'],
                     ['b',          'yyy',     '4',            ''],
                     ['b',          'xxx',     '2',           '2']]

        subsrc1 = MinimalSource(testdata1, fieldnames1)
        subsrc2 = MinimalSource(testdata2, fieldnames2)
        self.datasource = MultiSource(subsrc1, subsrc2)

    def test_combined_columns(self):
        expected = ['label1', 'label2', 'value', 'label3', 'other_value']
        result = self.datasource.columns()
        self.assertSetEqual(set(expected), set(result))

    def test_kwds_filter(self):
        # Filtered value spans sub-sources.
        expected = ['17', '13', '20', '15']
        result = self.datasource.distinct('value', label1='a')
        self.assertEqual(expected, result)

        # Filter column exists in only one sub-source.
        expected = ['17', '13']
        result = self.datasource.distinct('value', label1='a', label2='x')
        self.assertEqual(expected, result)


class TestMultiSourceDifferentColumns2(unittest.TestCase):
    """Test MultiSource with sub-sources that use different columns."""
    def setUp(self):
        fieldnames1 = ['label1', 'label2', 'value']
        testdata1 = [['a',            'x',    '17'],
                     ['a',            'x',    '13'],
                     ['a',            'y',    '20'],
                     ['b',            'z',     '5']]

        fieldnames2 = ['label1', 'label3', 'value', 'other_value']
        testdata2 = [['a',          'zzz',    '15',           '3'],
                     ['b',          'yyy',     '4',           '0'],
                     ['b',          'xxx',     '2',           '2']]

        subsrc1 = MinimalSource(testdata1, fieldnames1)
        subsrc2 = MinimalSource(testdata2, fieldnames2)
        self.datasource = MultiSource(subsrc1, subsrc2)

    def test_distinct_missing_columns(self):
        distinct = self.datasource.distinct

        expected = ['', '3', '0', '2']
        self.assertEqual(expected, distinct('other_value'))
        self.assertEqual(expected, distinct(['other_value']))

        expected = [('',), ('3',), ('0',), ('2',)]
        self.assertEqual(expected, distinct('other_value'))
        self.assertEqual(expected, distinct(['other_value']))

        expected = ['3']
        self.assertEqual(expected, distinct('other_value', label3='zzz'))

        expected = ['']
        self.assertEqual(expected, distinct('other_value', label3=''))

        expected = ['']
        self.assertEqual(expected, distinct('other_value', label2='x'))

        expected = [('a', 'x'), ('a', 'y'), ('b', 'z'), ('a', ''), ('b', '')]
        self.assertEqual(expected, distinct(['label1', 'label2']))

    def test_make_sub_filter(self):
        make_sub_filter = self.datasource._make_sub_filter

        filter_by = {'foo': 'a', 'bar': ''}
        self.assertEqual({'foo': 'a'}, make_sub_filter(['foo'], **filter_by))

        filter_by = {'foo': 'a', 'bar': ''}
        self.assertEqual({'foo': 'a'}, make_sub_filter(['foo', 'baz'], **filter_by))

        filter_by = {'qux': '', 'quux': ''}
        self.assertEqual({}, make_sub_filter(['foo', 'bar'], **filter_by))

        filter_by = {'foo': 'a', 'bar': 'b'}
        self.assertIsNone(make_sub_filter(['foo', 'baz'], **filter_by))

    def test_normalize_resultset(self):
        normalize_result = self.datasource._normalize_result

        result = ResultSet([('a', 'x'), ('b', 'y'), ('c', 'z')])

        # Append empty column.
        expected = ResultSet([('a', 'x', ''), ('b', 'y', ''), ('c', 'z', '')])
        self.assertEqual(expected, normalize_result(result, ['foo', 'bar'], ['foo', 'bar', 'baz']))

        # Insert empty column into middle.
        expected = ResultSet([('a', '', 'x'), ('b', '', 'y'), ('c', '', 'z')])
        self.assertEqual(expected, normalize_result(result, ['foo', 'bar'], ['foo', 'baz', 'bar']))

        # Insert empty column, reorder existing columns.
        expected = ResultSet([('x', '', 'a'), ('y', '', 'b'), ('z', '', 'c')])
        self.assertEqual(expected, normalize_result(result, ['foo', 'bar'], ['bar', 'baz', 'foo']))

        # Test error condition.
        with self.assertRaises(Exception):
            normalized = normalize_result(result, ['foo', 'bar'], ['bar'])

        # Single-item set, insert empty columns.
        result = ResultSet(['a', 'b', 'c'])
        expected = ResultSet([('', 'a', ''), ('', 'b', ''), ('', 'c', '')])
        self.assertEqual(expected, normalize_result(result, 'foo', ['qux', 'foo', 'corge']))

    def test_normalize_resultmapping(self):
        """."""
        normalize_result = self.datasource._normalize_result

        result = ResultMapping({('a', 'x'): 1, ('b', 'y'): 2, ('c', 'z'): 3}, key_names=['foo', 'bar'])

        # Append empty column.
        expected = ResultMapping({('a', 'x', ''): 1,
                                  ('b', 'y', ''): 2,
                                  ('c', 'z', ''): 3},
                                 key_names=['foo', 'bar', 'baz'])
        self.assertEqual(expected, normalize_result(result, ['foo', 'bar'], ['foo', 'bar', 'baz']))

        # Insert empty column into middle.
        expected = ResultMapping({('a', '', 'x'): 1,
                                  ('b', '', 'y'): 2,
                                  ('c', '', 'z'): 3},
                                 key_names=['foo', 'bar', 'baz'])
        self.assertEqual(expected, normalize_result(result, ['foo', 'bar'], ['foo', 'baz', 'bar']))

        # Insert empty column, reorder existing columns.
        expected = ResultMapping({('x', '', 'a'): 1,
                                  ('y', '', 'b'): 2,
                                  ('z', '', 'c'): 3},
                                 key_names=['foo', 'bar', 'baz'])
        self.assertEqual(expected, normalize_result(result, ['foo', 'bar'], ['bar', 'baz', 'foo']))

        # Test error condition.
        with self.assertRaises(Exception):
            normalized = normalize_result(result, ['foo', 'bar'], ['bar'])

        # Single-item key, insert empty columns.
        result = ResultMapping({('a',): 1, ('b',): 2, ('c',): 3}, key_names='foo')
        expected = ResultMapping({('', 'a', ''): 1, ('', 'b', ''): 2, ('', 'c', ''): 3}, key_names=['qux', 'foo', 'corge'])
        self.assertEqual(expected, normalize_result(result, ['foo'], ['qux', 'foo', 'corge']))

        # String key, insert empty columns.
        result = ResultMapping({'a': 1, 'b': 2, 'c': 3}, key_names='foo')
        expected = ResultMapping({('', 'a', ''): 1, ('', 'b', ''): 2, ('', 'c', ''): 3}, key_names=['qux', 'foo', 'corge'])
        self.assertEqual(expected, normalize_result(result, ['foo'], ['qux', 'foo', 'corge']))
