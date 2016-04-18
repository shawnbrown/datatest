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

# Import related objects.
from datatest.compare import CompareSet
from datatest.compare import CompareDict
from datatest.utils import TemporarySqliteTable

# Import code to test.
from datatest.source import BaseSource
from datatest.source import SqliteSource
from datatest.source import CsvSource
from datatest.source import _FilterValueError
from datatest.source import AdapterSource
from datatest.source import MultiSource


def _make_csv_file(fieldnames, datarows):
    """Helper function to make CSV file-like object using *fieldnames*
    (a list of field names) and *datarows* (a list of lists containing
    the row values).
    """
    init_string = []
    init_string.append(','.join(fieldnames)) # Concat cells into row.
    for row in datarows:
        row = [str(cell) for cell in row]
        init_string.append(','.join(row))    # Concat cells into row.
    init_string = '\n'.join(init_string)     # Concat rows into final string.
    return io.StringIO(init_string)


class MinimalSource(BaseSource):
    """Minimal data source implementation for testing."""
    def __init__(self, data, fieldnames):
        self._data = data
        self._fieldnames = fieldnames

    def __repr__(self):
        return self.__class__.__name__ + '(<data>, <fieldnames>)'

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

    def test_filter_rows(self):
        """Test filter iterator."""
        # Filter by single value (where label1 is 'a').
        results = self.datasource.filter_rows(label1='a')
        results = list(results)
        expected = [
            {'label1': 'a', 'label2': 'x', 'value': '17'},
            {'label1': 'a', 'label2': 'x', 'value': '13'},
            {'label1': 'a', 'label2': 'y', 'value': '20'},
            {'label1': 'a', 'label2': 'z', 'value': '15'},
        ]
        self.assertEqual(expected, results)

        # Filter by multiple values (where label2 is 'x' OR 'y').
        results = self.datasource.filter_rows(label2=['x', 'y'])
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
        results = self.datasource.filter_rows(label1='a', label2=['x', 'y'])
        results = list(results)
        expected = [
            {'label1': 'a', 'label2': 'x', 'value': '17'},
            {'label1': 'a', 'label2': 'x', 'value': '13'},
            {'label1': 'a', 'label2': 'y', 'value': '20'},
        ]
        self.assertEqual(expected, results)

        # Call with no filter kewords at all.
        results = self.datasource.filter_rows()  # <- Should return all rows.
        results = list(results)
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
        mapper = lambda a: (int(a[0]), str(a[1]))
        maxmin = lambda x, y: (min(x[0], y[0]), max(x[1], y[1]))
        expected = {'a': (13, 'z'), 'b': (5, 'z')}
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

        # Test multiple/non-string column (not valid).
        with self.assertRaises((TypeError, ValueError)):
            sum(['value', 'value'])

        with self.assertRaises((TypeError, ValueError)):
            sum(['value', 'value'], 'label2', label1='a')

    def test_count(self):
        count = self.datasource.count

        self.assertEqual(7, count('label1'))

        expected = {'a': 4, 'b': 3}
        self.assertEqual(expected, count('label1', 'label1'))

        expected = {('a',): 4, ('b',): 3}
        self.assertEqual(expected, count('label1', ['label1']))

        expected = {
            ('a', 'x'): 2,
            ('a', 'y'): 1,
            ('a', 'z'): 1,
            ('b', 'z'): 1,
            ('b', 'y'): 1,
            ('b', 'x'): 1,
        }
        self.assertEqual(expected, count('label1', ['label1', 'label2']))
        expected = {'x': 2, 'y': 1, 'z': 1}
        self.assertEqual(expected, count('label2', 'label2', label1='a'))

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


class TestDataSourceCount(unittest.TestCase):
    """Test count() method with the following data set:

        label1  label2  value
        ------  ------  -----
        'a'     'x'     '17'
        'a'     'x'     '13'
        'a'     'y'     '20'
        'a'     ''      '15'
        'b'     'z'     '5'
        'b'     'y'     '40'
        'b'     'x'     '25'
        'b'     None    '0'
        'b'     ''      '1'
    """
    fieldnames = ['label1', 'label2', 'value']
    testdata = [
        ['a', 'x', '17'],
        ['a', 'x', '13'],
        ['a', 'y', '20'],
        ['a', '',  '15'],
        ['b', 'z', '5' ],
        ['b', 'y', '40'],
        ['b', 'x', '25'],
        ['b', None, '0'],
        ['b', '', '1'],
    ]
    def setUp(self):
        """Define self.datasource (base version uses MinimalSource)."""
        self.datasource = MinimalSource(self.testdata, self.fieldnames)

    def test_count(self):
        count = self.datasource.count

        self.assertEqual(9, count('label1'))

        expected = {'a': 4, 'b': 5}
        result = count('label1', ['label1'])
        self.assertEqual(expected, result)

        expected = {'a': 3, 'b': 3}  # Counts only truthy values (not '' or None).
        result = count('label2', ['label1'])
        self.assertEqual(expected, result)

        expected = {
            ('a', 'x'): 2,
            ('a', 'y'): 1,
            ('a', ''): 1,
            ('b', 'z'): 1,
            ('b', 'y'): 1,
            ('b', 'x'): 1,
            ('b', None): 1,
            ('b', ''): 1,
        }
        result = count('label1', ['label1', 'label2'])
        self.assertEqual(expected, result)

        expected = {'x': 2, 'y': 1, '': 1}
        result = count('label1', 'label2', label1='a')
        self.assertEqual(expected, result)


class TestSqliteSourceCount(TestDataSourceCount):
    def setUp(self):
        tablename = 'testtable'
        connection = sqlite3.connect(':memory:')
        cursor = connection.cursor()
        cursor.execute("CREATE TABLE testtable (label1, label2, value)")
        for values in self.testdata:
            cursor.execute("INSERT INTO testtable VALUES (?, ?, ?)", values)
        connection.commit()

        self.datasource = SqliteSource(connection, tablename)


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
        """Test from_records method (wrapper for TemporarySqliteTable class)."""
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


class TestAdapterSource(unittest.TestCase):
    def setUp(self):
        self.fieldnames = ['col1', 'col2', 'col3']
        self.data = [['a', 'x', '17'],
                     ['a', 'x', '13'],
                     ['a', 'y', '20'],
                     ['a', 'z', '15']]
        self.source = MinimalSource(self.data, self.fieldnames)

    def test_repr(self):
        interface = [('a', 'col1'), ('b', 'col2'), ('c', 'col3')]
        adapted = AdapterSource(self.source, interface)
        required = ("AdapterSource(MinimalSource(<data>, <fieldnames>), "
                    "[('a', 'col1'), ('b', 'col2'), ('c', 'col3')])")
        self.assertEqual(required, repr(adapted))

    def test_unwrap_columns(self):
        interface = [('a', 'col1'), ('b', 'col2'), ('c', 'col3'), ('d', None)]
        adapted = AdapterSource(self.source, interface)
        unwrap_columns = adapted._unwrap_columns

        self.assertEqual('col1', unwrap_columns('a'))
        self.assertEqual(('col1', 'col2'), unwrap_columns(['a', 'b']))
        self.assertEqual(None, unwrap_columns('d'))
        with self.assertRaises(KeyError):
            unwrap_columns('col1')  # <- This is a hidden, adaptee column
                                    #    not a visible adapter column.

    def test_rewrap_columns(self):
        interface = [('a', 'col1'), ('b', 'col2'), ('c', 'col3'), ('d', None)]
        adapted = AdapterSource(self.source, interface)
        rewrap_columns = adapted._rewrap_columns

        self.assertEqual('a', rewrap_columns('col1'))
        self.assertEqual(('a', 'b'), rewrap_columns(['col1', 'col2']))
        self.assertEqual(None, rewrap_columns([]))
        self.assertEqual(None, rewrap_columns(None))
        with self.assertRaises(KeyError):
            rewrap_columns('c')

    def test_unwrap_filter(self):
        interface = [('a', 'col1'), ('b', 'col2'), ('c', 'col3'), ('d', None)]
        adapted = AdapterSource(self.source, interface)
        unwrap_filter = adapted._unwrap_filter

        self.assertEqual({'col1': 'foo'}, unwrap_filter({'a': 'foo'}))
        self.assertEqual({'col1': 'foo', 'col2': 'bar'}, unwrap_filter({'a': 'foo', 'b': 'bar'}))
        self.assertEqual({}, unwrap_filter({}))
        with self.assertRaises(_FilterValueError):
            unwrap_filter({'a': 'foo', 'd': 'baz'})  # <- d='baz' cannot be converted
                                                     #    because there is no adaptee
                                                     #    column mapped to 'd'.

        # It is possible, however, to filter 'd' to an empty string (the
        # default *missing* value.)
        self.assertEqual({'col1': 'foo'}, unwrap_filter({'a': 'foo', 'd': ''}))

    def test_rebuild_compareset(self):
        interface = [('a', 'col1'), ('b', 'col2'), ('c', 'col3'), ('d', None)]
        adapted = AdapterSource(self.source, interface)
        rebuild_compareset = adapted._rebuild_compareset

        # Rebuild one column result as two column result.
        orig = CompareSet(['x', 'y', 'z'])
        result = rebuild_compareset(orig, 'b', ['b', 'd'])
        expected = CompareSet([('x', ''), ('y', ''), ('z', '')])
        self.assertEqual(expected, result)

        # Rebuild two column result to three column with missing column in the middle.
        orig = CompareSet([('x1', 'x2'), ('y1', 'y2'), ('z1', 'z2')])
        result = rebuild_compareset(orig, ['b', 'c'], ['b', 'd', 'c'])
        expected = CompareSet([('x1', '', 'x2'), ('y1', '', 'y2'), ('z1', '', 'z2')])
        self.assertEqual(expected, result)

    def test_rebuild_comparedict(self):
        interface = [('a', 'col1'), ('b', 'col2'), ('c', 'col3'), ('d', None)]
        adapted = AdapterSource(self.source, interface)
        rebuild_comparedict = adapted._rebuild_comparedict

        # Rebuild single key result as two key result.
        orig = CompareDict({'x': 1, 'y': 2, 'z': 3}, key_names='a')
        result = rebuild_comparedict(orig, 'c', 'c', 'a', ['a', 'b'], missing_col='')
        expected = CompareDict({('x', ''): 1,
                                ('y', ''): 2,
                                ('z', ''): 3},
                               key_names=['a', 'b'])
        self.assertEqual(expected, result)

        # Rebuild two key result as three key result.
        orig = CompareDict({('x', 'x'): 1, ('y', 'y'): 2, ('z', 'z'): 3}, key_names=['a', 'c'])
        result = rebuild_comparedict(orig, 'c', 'c', ['a', 'b'], ['a', 'd', 'b'], missing_col='')
        expected = CompareDict({('x', '', 'x'): 1,
                                ('y', '', 'y'): 2,
                                ('z', '', 'z'): 3},
                               key_names=['a', 'd', 'b'])
        self.assertEqual(expected, result)

        # Rebuild single value tuple result as two value result.
        orig = CompareDict({'x': (1,), 'y': (2,), 'z': (3,)}, key_names='a')
        result = rebuild_comparedict(orig, 'c', ['c', 'd'], 'a', 'a', missing_col='')
        expected = CompareDict({'x': (1, ''),
                                'y': (2, ''),
                                'z': (3, '')},
                               key_names='a')
        self.assertEqual(expected, result)

        # Rebuild single value result as two value result.
        if True:
            orig = CompareDict({'x': 1, 'y': 2, 'z': 3}, key_names='a')
            result = rebuild_comparedict(orig, 'c', ['c', 'd'], 'a', 'a', missing_col='')
            expected = CompareDict({'x': (1, ''),
                                    'y': (2, ''),
                                    'z': (3, '')},
                                   key_names=['c', 'd'])
            self.assertEqual(expected, result)

        # Rebuild two column result as three column result.
        orig = CompareDict({'x': (1, 2), 'y': (2, 4), 'z': (3, 6)}, key_names='a')
        result = rebuild_comparedict(orig, ['b', 'c'], ['b', 'd', 'c'],
                                       'a', 'a', missing_col='empty')
        expected = CompareDict({'x': (1, 'empty', 2),
                                'y': (2, 'empty', 4),
                                'z': (3, 'empty', 6)},
                               key_names='a')
        self.assertEqual(expected, result)

        # Rebuild two key and two column result as three key and three column result.
        orig = CompareDict({('x', 'x'): (1, 2),
                            ('y', 'y'): (2, 4),
                            ('z', 'z'): (3, 6)},
                            key_names=['a', 'c'])
        result = rebuild_comparedict(orig,
                                       ['b', 'c'], ['b', 'd', 'c'],
                                       ['a', 'b'], ['a', 'd', 'b'],
                                       missing_col='empty')
        expected = CompareDict({('x', '', 'x'): (1, 'empty', 2),
                                  ('y', '', 'y'): (2, 'empty', 4),
                                  ('z', '', 'z'): (3, 'empty', 6)},
                                 key_names=['a', 'd', 'b'])
        self.assertEqual(expected, result)

    def test_columns(self):
        # Test original.
        self.assertEqual(['col1', 'col2', 'col3'], self.source.columns())

        # Reorder columns.
        interface = [
            ('col3', 'col3'),
            ('col2', 'col2'),
            ('col1', 'col1'),
        ]
        adapted = AdapterSource(self.source, interface)
        self.assertEqual(['col3', 'col2', 'col1'], adapted.columns())

        # Rename columns.
        interface = [
            ('a', 'col1'),
            ('b', 'col2'),
            ('c', 'col3'),
        ]
        adapted = AdapterSource(self.source, interface)
        self.assertEqual(['a', 'b', 'c'], adapted.columns())

        # Remove column.
        interface = [
            ('col1', 'col1'),
            ('col2', 'col2'),
            # Column 'col3' not included!
        ]
        adapted = AdapterSource(self.source, interface)
        self.assertEqual(['col1', 'col2'], adapted.columns())

        # Add new column.
        interface = [
            ('a', 'col1'),
            ('b', 'col2'),
            ('c', 'col3'),
            ('d', None),  # <- New column, no corresponding original!
        ]
        adapted = AdapterSource(self.source, interface)
        self.assertEqual(['a', 'b', 'c', 'd'], adapted.columns())

        # Raise error if old name is not in original source.
        interface = [
            ('a', 'bad_column'),  # <- 'bad_column' not in original!
            ('b', 'col2'),
            ('c', 'col3'),
        ]
        with self.assertRaises(KeyError):
            adapted = AdapterSource(self.source, interface)

    def test_iter(self):
        interface = [('two', 'col2'), ('three', 'col3'), ('four', None)]
        adapted = AdapterSource(self.source, interface)
        expected = [
            {'two': 'x', 'three': '17', 'four': ''},
            {'two': 'x', 'three': '13', 'four': ''},
            {'two': 'y', 'three': '20', 'four': ''},
            {'two': 'z', 'three': '15', 'four': ''},
        ]
        result = list(adapted.__iter__())
        self.assertEqual(expected, result)

    def test_distinct(self):
        # Basic usage.
        interface = [('one', 'col1'), ('two', 'col2'), ('three', 'col3')]
        adapted = AdapterSource(self.source, interface)
        required = set(['x', 'y', 'z'])
        self.assertEqual(required, adapted.distinct('two'))

        # Adapter column mapped to None.
        interface = [('two', 'col2'), ('four', None)]
        adapted = AdapterSource(self.source, interface)

        required = set([('x', ''), ('y', ''), ('z', '')])
        self.assertEqual(required, adapted.distinct(['two', 'four']))

        required = set([('', 'x'), ('', 'y'), ('', 'z')])
        self.assertEqual(required, adapted.distinct(['four', 'two']))

        required = set([''])
        self.assertEqual(required, adapted.distinct('four'))

        required = set([('', '')])
        self.assertEqual(required, adapted.distinct(['four', 'four']))

        # Filter on renamed column.
        interface = [('one', 'col1'), ('two', 'col2'), ('three', 'col3')]
        adapted = AdapterSource(self.source, interface)
        required = set(['17', '13'])
        self.assertEqual(required, adapted.distinct('three', two='x'))

        # Filter on column mapped to None.
        interface = [('three', 'col3'), ('four', None)]
        adapted = AdapterSource(self.source, interface)

        required = set()
        self.assertEqual(required, adapted.distinct('three', four='x'))

        required = set(['17', '13', '20', '15'])
        self.assertEqual(required, adapted.distinct('three', four=''))

        # Unknown column.
        interface = [('one', 'col1'), ('two', 'col2')]
        adapted = AdapterSource(self.source, interface)
        required = set(['x', 'y', 'z'])
        with self.assertRaises(KeyError):
            adapted.distinct('three')

    def test_sum(self):
        # Basic usage (no group-by keys).
        interface = [('one', 'col1'), ('two', 'col2'), ('three', 'col3')]
        adapted = AdapterSource(self.source, interface)
        self.assertEqual(65, adapted.sum('three'))

        # No group-by keys, filter to missing column.
        interface = [('one', 'col1'), ('two', 'col2'), ('three', 'col3'), ('four', None)]
        adapted = AdapterSource(self.source, interface)
        self.assertEqual(0, adapted.sum('three', four='xyz'))

        # Grouped by column 'two'.
        result = adapted.sum('three', 'two')
        self.assertEqual({'x': 30, 'y': 20, 'z': 15}, result)
        self.assertEqual(['two'], list(result.key_names))

        # Grouped by column mapped to None.
        interface = [('two', 'col2'), ('three', 'col3'), ('four', None)]
        adapted = AdapterSource(self.source, interface)
        result = adapted.sum('three', ['two', 'four'])
        expected = {('x', ''): 30, ('y', ''): 20, ('z', ''): 15}
        self.assertEqual(expected, result)

        # Sum over column mapped to None.
        interface = [('two', 'col2'), ('three', 'col3'), ('four', None)]
        adapted = AdapterSource(self.source, interface)
        result = adapted.sum('four', 'two')
        expected = {'x': 0, 'y': 0, 'z': 0}
        self.assertEqual(expected, result)

        # Grouped by and summed over column mapped to None.
        interface = [('two', 'col2'), ('three', 'col3'), ('four', None)]
        adapted = AdapterSource(self.source, interface)
        with self.assertRaises(ValueError):
            adapted.sum(['three', 'four'], 'two')

        # Grouped by and summed over column mapped to None using alternate missing.
        interface = [('one', 'col1'), ('two', 'col2'), ('three', 'col3'), ('four', None), ('five', None)]
        adapted = AdapterSource(self.source, interface, missing='EMPTY')
        result = adapted.sum('four', 'one')  # <- Key on existing column.
        expected = {'a': 0}
        self.assertEqual(expected, result)
        result = adapted.sum('four', 'five')  # <- Key on missing column.
        expected = {'EMPTY': 0}
        self.assertEqual(expected, result)

        # Summed over column mapped to None and nothing else.
        interface = [('two', 'col2'), ('three', 'col3'), ('four', None)]
        adapted = AdapterSource(self.source, interface)
        result = adapted.sum('four', 'two')
        expected = {'x': 0, 'y': 0, 'z': 0}
        self.assertEqual(expected, result)

class TestAdapterSourceBasics(TestBaseSource):
    def setUp(self):
        fieldnames = ['col1', 'col2', 'col3']
        source = MinimalSource(self.testdata, fieldnames)
        interface = [
            ('label1', 'col1'),
            ('label2', 'col2'),
            ('value', 'col3'),
        ]
        self.datasource = AdapterSource(source, interface)


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
        self.assertEqual(expected, source.count('label1', 'label1'))

        expected = {'a': 1}
        self.assertEqual(expected, source.count('label1', 'label1', label2='x'))


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
