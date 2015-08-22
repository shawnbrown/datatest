# -*- coding: utf-8 -*-
import csv
import os
import sqlite3
import sys
import unittest
import tempfile
import warnings

from datatest.tests import _io as io
from datatest.tests import _unittest as unittest
from datatest.tests.common import MkdtempTestCase

from datatest.datasource import BaseDataSource
from datatest.datasource import SqliteDataSource
from datatest.datasource import CsvDataSource
from datatest.datasource import FilteredDataSource
from datatest.datasource import GroupedDataSource
from datatest.datasource import MappedDataSource
from datatest.datasource import MultiDataSource
from datatest.datasource import UniqueDataSource


class MinimalDataSource(BaseDataSource):
    """Minimal data source implementation for testing."""
    def __init__(self, data, fieldnames):
        self._data = data
        self._fieldnames = fieldnames

    def __repr__(self):
        return self.__class__.__name__

    def columns(self):
        return self._fieldnames

    def slow_iter(self):
        for row in self._data:
            yield dict(zip(self._fieldnames, row))


class TestBaseDataSource(unittest.TestCase):
    fieldnames = ['label1', 'label2', 'value']
    testdata = [['a', 'x', '17'],
                ['a', 'x', '13'],
                ['a', 'y', '20'],
                ['a', 'z', '15'],
                ['b', 'z', '5' ],
                ['b', 'y', '40'],
                ['b', 'x', '25']]

    @staticmethod
    def _make_csv_file(fieldnames, testdata):
        """Build CSV file from source data."""
        init_string = []
        init_string.append(','.join(fieldnames)) # Concat cells into row.
        for row in testdata:
            init_string.append(','.join(row))    # Concat cells into row.
        init_string = '\n'.join(init_string)     # Concat rows into final string.
        return io.StringIO(init_string)

    def setUp(self):
        self.datasource = MinimalDataSource(self.testdata, self.fieldnames)

    def test_for_datasource(self):
        msg = '{0} missing `datasource` attribute.'
        msg = msg.format(self.__class__.__name__)
        self.assertTrue(hasattr(self, 'datasource'), msg)

    def test_slow_iter(self):
        """Test slow iterator."""
        results = self.datasource.slow_iter()

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
        self.assertEqual(results, expected)

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
        results = self.datasource._base_filter_by(testdata, label1='a')
        results = list(results)
        expected = [
            {'label1': 'a', 'label2': 'x', 'value': '17'},
            {'label1': 'a', 'label2': 'x', 'value': '13'},
            {'label1': 'a', 'label2': 'y', 'value': '20'},
            {'label1': 'a', 'label2': 'z', 'value': '15'},
        ]
        self.assertEqual(results, expected)

        # Filter by multiple values (where label2 is 'x' OR 'y').
        results = self.datasource._base_filter_by(testdata, label2=['x', 'y'])
        results = list(results)
        expected = [
            {'label1': 'a', 'label2': 'x', 'value': '17'},
            {'label1': 'a', 'label2': 'x', 'value': '13'},
            {'label1': 'a', 'label2': 'y', 'value': '20'},
            {'label1': 'b', 'label2': 'y', 'value': '40'},
            {'label1': 'b', 'label2': 'x', 'value': '25'},
        ]
        self.assertEqual(results, expected)

        # Filter by multiple columns (where label1 is 'a', label2 is 'x' OR 'y').
        results = self.datasource._base_filter_by(testdata,
                                                  label1='a', label2=['x', 'y'])
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

    def test_sum(self):
        result = self.datasource.sum('value')
        self.assertEqual(result, 135)

        result = self.datasource.sum('value', label1='a')
        self.assertEqual(result, 65)

    def test_count(self):
        result = self.datasource.count()
        self.assertEqual(result, 7)

        result = self.datasource.count(label2='x')
        self.assertEqual(result, 3)

    def test_unique(self):
        # Test single column.
        result = self.datasource.unique('label1')
        expected = [('a',), ('b',)]
        self.assertEqual(list(result), expected)

        # Test multiple columns.
        result = self.datasource.unique('label1', 'label2')
        expected = [
            ('a', 'x'),
            ('a', 'y'),
            ('a', 'z'),
            ('b', 'z'),  # <- ordered (if possible)
            ('b', 'y'),  # <- ordered (if possible)
            ('b', 'x'),  # <- ordered (if possible)
        ]
        self.assertEqual(set(result), set(expected))

        # Test multiple columns with filter.
        result = self.datasource.unique('label1', 'label2', label2=['x', 'y'])
        expected = [('a', 'x'),
                    ('a', 'y'),
                    ('b', 'y'),
                    ('b', 'x')]
        self.assertEqual(set(result), set(expected))

        # Test multiple columns with filter on non-grouped column.
        result = self.datasource.unique('label1', 'value', label2='x')
        expected = [('a', '17'),
                    ('a', '13'),
                    ('b', '25')]
        self.assertEqual(set(result), set(expected))

        # Test when specified column is missing.
        msg = 'Error should reference missing column.'
        with self.assertRaisesRegex(Exception, "label3", msg=msg):
            result = self.datasource.unique('label1', 'label3', label2='x')
            result = list(result)  # Force evaluation of generator items.


class TestSqliteDataSource(TestBaseDataSource):
    def setUp(self):
        tablename = 'testtable'
        connection = sqlite3.connect(':memory:')
        cursor = connection.cursor()
        cursor.execute("CREATE TABLE testtable (label1, label2, value)")
        for values in self.testdata:
            cursor.execute("INSERT INTO testtable VALUES (?, ?, ?)", values)
        connection.commit()

        self.datasource = SqliteDataSource(connection, tablename)

    def test_where_clause(self):
        # No key-word args.
        clause, params = SqliteDataSource._build_where_clause()
        self.assertEqual(clause, '')
        self.assertEqual(params, [])

        # Single condition (where label1 equals 'a').
        clause, params = SqliteDataSource._build_where_clause(label1='a')
        self.assertEqual(clause, 'label1=?')
        self.assertEqual(params, ['a'])

        # Multiple conditions (where label1 equals 'a' AND label2 equals 'x').
        clause, params = SqliteDataSource._build_where_clause(label1='a', label2='x')
        self.assertEqual(clause, 'label1=? AND label2=?')
        self.assertEqual(params, ['a', 'x'])

        # Compound condition (where label1 equals 'a' OR 'b').
        clause, params = SqliteDataSource._build_where_clause(label1=('a', 'b'))
        self.assertEqual(clause, 'label1 IN (?, ?)')
        self.assertEqual(params, ['a', 'b'])

        # Mixed conditions (where label1 equals 'a' OR 'b' AND label2 equals 'x').
        clause, params = SqliteDataSource._build_where_clause(label1=('a', 'b'), label2='x')
        self.assertEqual(clause, 'label1 IN (?, ?) AND label2=?')
        self.assertEqual(params, ['a', 'b', 'x'])

    def test_from_records_assert_unique(self):
        # Pass without error.
        SqliteDataSource._from_records_assert_unique(['foo', 'bar'])

        with self.assertRaises(ValueError):
            SqliteDataSource._from_records_assert_unique(['foo', 'foo'])

    def test_from_records_normalize_column(self):
        result = SqliteDataSource._from_records_normalize_column('foo')
        self.assertEqual('"foo"', result)

        result = SqliteDataSource._from_records_normalize_column('foo bar')
        self.assertEqual('"foo bar"', result)

        result = SqliteDataSource._from_records_normalize_column('foo "bar" baz')
        self.assertEqual('"foo ""bar"" baz"', result)

    def test_from_records_build_insert_statement(self):
        stmnt, param = SqliteDataSource._from_records_build_insert_statement('mytable', ['val1a', 'val2a'])
        self.assertEqual('INSERT INTO mytable VALUES (?, ?)', stmnt)
        self.assertEqual(['val1a', 'val2a'], param)

        with self.assertRaisesRegex(AssertionError, 'must be list or tuple, not str'):
            SqliteDataSource._from_records_build_insert_statement('mytable', 'val1')

    def test_from_records_build_create_statement(self):
        stmnt = SqliteDataSource._from_records_build_create_statement('mytable', ['col1', 'col2'])
        self.assertEqual('CREATE TABLE mytable ("col1", "col2")', stmnt)

    def test_from_records_tuple(self):
        # Test list of tuples.
        columns = ['foo', 'bar', 'baz']
        data = [
            ('a', 'x', '1'),
            ('b', 'y', '2'),
            ('c', 'z', '3'),
        ]
        source = SqliteDataSource.from_records(data, columns)

        expected = [
            {'foo': 'a', 'bar': 'x', 'baz': '1'},
            {'foo': 'b', 'bar': 'y', 'baz': '2'},
            {'foo': 'c', 'bar': 'z', 'baz': '3'},
        ]
        result = source.slow_iter()
        self.assertEqual(expected, list(result))

        # Test too few columns.
        columns = ['foo', 'bar']
        with self.assertRaises(sqlite3.OperationalError):
            source = SqliteDataSource.from_records(data, columns)

        # Test too many columns.
        columns = ['foo', 'bar', 'baz', 'qux']
        with self.assertRaises(sqlite3.OperationalError):
            source = SqliteDataSource.from_records(data, columns)

    def test_from_records_dict(self):
        columns = ['foo', 'bar', 'baz']
        data = [
            {'foo': 'a', 'bar': 'x', 'baz': '1'},
            {'foo': 'b', 'bar': 'y', 'baz': '2'},
            {'foo': 'c', 'bar': 'z', 'baz': '3'},
        ]
        source = SqliteDataSource.from_records(data, columns)

        result = source.slow_iter()
        self.assertEqual(data, list(result))

        # Test too few columns.
        #columns = ['foo', 'bar']
        #with self.assertRaises(AssertionError):
        #    source = SqliteDataSource.from_records(data, columns)

        # Test too many columns.
        columns = ['foo', 'bar', 'baz', 'qux']
        with self.assertRaises(KeyError):
            source = SqliteDataSource.from_records(data, columns)

    def test_from_source(self):
        columns = ['foo', 'bar', 'baz']
        data = [
            ('a', 'x', '1'),
            ('b', 'y', '2'),
            ('c', 'z', '3'),
        ]
        source = MinimalDataSource(data, columns)
        source = SqliteDataSource.from_source(source)

        self.assertIsInstance(source, SqliteDataSource)

        expected = [
            {'foo': 'a', 'bar': 'x', 'baz': '1'},
            {'foo': 'b', 'bar': 'y', 'baz': '2'},
            {'foo': 'c', 'bar': 'z', 'baz': '3'},
        ]
        result = source.slow_iter()
        self.assertEqual(expected, list(result))

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


class TestCsvDataSource(TestBaseDataSource):
    def setUp(self):
        fh = self._make_csv_file(self.fieldnames, self.testdata)
        self.datasource = CsvDataSource(fh)

    def test_empty_file(self):
        pass
        #file exists but is empty should fail, too!


class TestCsvDataSource_FileHandling(unittest.TestCase):
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
        CsvDataSource(fh)  # Pass without error.

        fh = self._get_filelike(b'label1,label2,value\n'
                                b'a,x,18\n'
                                b'a,x,13\n'
                                b'a,\xc3\xb1,20\n'  # \xc3\xb1 is utf-8 literal for ñ
                                b'a,z,15\n', encoding='utf-8')
        CsvDataSource(fh)  # Pass without error.

        fh = self._get_filelike(b'label1,label2,value\n'
                                b'a,x,18\n'
                                b'a,x,13\n'
                                b'a,\xf1,20\n'  # '\xf1' is iso8859-1 for ñ
                                b'a,z,15\n', encoding='iso8859-1')
        CsvDataSource(fh, encoding='iso8859-1')  # Pass without error.

    def test_bad_filelike_object(self):
        with self.assertRaises(UnicodeDecodeError):
            fh = self._get_filelike(b'label1,label2,value\n'
                                    b'a,x,18\n'
                                    b'a,x,13\n'
                                    b'a,\xf1,20\n'  # '\xf1' is iso8859-1 for ñ, not utf-8!
                                    b'a,z,15\n', encoding='utf-8')
            CsvDataSource(fh, encoding='utf-8')  # Raises exception!


class TestCsvDataSource_ActualFileHandling(MkdtempTestCase):
    def test_utf8(self):
        with open('utf8file.csv', 'wb') as fh:
            filecontents = (b'label1,label2,value\n'
                            b'a,x,18\n'
                            b'a,x,13\n'
                            b'a,\xc3\xb1,20\n'  # \xc3\xb1 is utf-8 literal for ñ
                            b'a,z,15\n')
            fh.write(filecontents)
            abspath = os.path.abspath(fh.name)

        CsvDataSource(abspath)  # Pass without error.

        CsvDataSource(abspath, encoding='utf-8')  # Pass without error.

        msg = 'If wrong encoding is specified, should raise exception.'
        with self.assertRaises(UnicodeDecodeError, msg=msg):
            CsvDataSource(abspath, encoding='ascii')

    def test_iso88591(self):
        with open('iso88591file.csv', 'wb') as fh:
            filecontents = (b'label1,label2,value\n'
                            b'a,x,18\n'
                            b'a,x,13\n'
                            b'a,\xf1,20\n'  # '\xf1' is iso8859-1 for ñ, not utf-8!
                            b'a,z,15\n')
            fh.write(filecontents)
            abspath = os.path.abspath(fh.name)

        CsvDataSource(abspath, encoding='iso8859-1')  # Pass without error.

        msg = ('When encoding us unspecified, tries UTF-8 first then '
               'fallsback to ISO-8859-1 and raises a Warning.')
        with self.assertWarns(UserWarning, msg=msg):
            CsvDataSource(abspath)

        msg = 'If wrong encoding is specified, should raise exception.'
        with self.assertRaises(UnicodeDecodeError, msg=msg):
            CsvDataSource(abspath, encoding='utf-8')

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
            CsvDataSource(fh, encoding='utf-8')  # Pass without error.

        with self.assertRaises(Exception):
            with open(filename, incorrect_mode) as fh:
                CsvDataSource(fh, encoding='utf-8')  # Raise exception.


class TestFilteredDataSource(TestBaseDataSource):
    def setUp(self):
        self.orig_src = MinimalDataSource(self.testdata, self.fieldnames)
        self.datasource = FilteredDataSource(None, self.orig_src)

    def test_filter(self):
        not_y = lambda row: row['label2'] != 'y'
        self.datasource = FilteredDataSource(not_y, self.orig_src)

        expected = [
            {'label1': 'a', 'label2': 'x', 'value': '17'},
            {'label1': 'a', 'label2': 'x', 'value': '13'},
            {'label1': 'a', 'label2': 'z', 'value': '15'},
            {'label1': 'b', 'label2': 'z', 'value': '5'},
            {'label1': 'b', 'label2': 'x', 'value': '25'},
        ]
        result = self.datasource.slow_iter()
        self.assertEqual(expected, list(result))

    def test_repr(self):
        def not_y(row):
            return row['label2'] != 'y'
        src = FilteredDataSource(not_y, self.orig_src)
        self.assertTrue(repr(src).startswith('FilteredDataSource(not_y, '))


class TestUniqueDataSource(TestBaseDataSource):
    def setUp(self):
        self.minimal_source = MinimalDataSource(self.testdata, self.fieldnames)
        self.datasource = UniqueDataSource(self.minimal_source, self.fieldnames)

    def test_unique(self):
        # Two columns.
        datasource = UniqueDataSource(self.minimal_source, ['label1', 'label2'])
        expected = [
            {'label1': 'a', 'label2': 'x'},
            {'label1': 'a', 'label2': 'y'},
            {'label1': 'a', 'label2': 'z'},
            {'label1': 'b', 'label2': 'z'},
            {'label1': 'b', 'label2': 'y'},
            {'label1': 'b', 'label2': 'x'}
        ]
        result = datasource.slow_iter()
        self.assertEqual(expected, list(result))

        # One column.
        datasource = UniqueDataSource(self.minimal_source, ['label2'])
        expected = [
            {'label2': 'x'},
            {'label2': 'y'},
            {'label2': 'z'},
        ]
        result = datasource.slow_iter()
        self.assertEqual(expected, list(result))

    def test_repr(self):
        src = UniqueDataSource(self.minimal_source, ['label1', 'label2'])
        self.assertTrue(repr(src).startswith('UniqueDataSource('))
        self.assertTrue(repr(src).endswith(", ['label1', 'label2'])"))


class TestMultiDataSource(TestBaseDataSource):
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

        source1 = MinimalDataSource(testdata1, fieldnames1)
        source2 = MinimalDataSource(testdata2, fieldnames2)
        self.datasource = MultiDataSource(source1, source2)


class TestMixedMultiDataSource(TestBaseDataSource):
    """Test MultiDataSource with sub-sources of different types."""
    def setUp(self):
        fieldnames1 = ['label1', 'label2', 'value']
        testdata1 = [['a', 'x', '17'],
                     ['a', 'x', '13'],
                     ['a', 'y', '20'],
                     ['a', 'z', '15']]
        minimal_source = MinimalDataSource(testdata1, fieldnames1)

        fieldnames2 = ['label1', 'label2', 'value']
        testdata2 = [['b', 'z', '5' ],
                     ['b', 'y', '40'],
                     ['b', 'x', '25']]
        fh = self._make_csv_file(fieldnames2, testdata2)
        csv_source = CsvDataSource(fh)

        self.datasource = MultiDataSource(minimal_source, csv_source)


class TestMultiDataSourceDifferentColumns(unittest.TestCase):
    """Test MultiDataSource with sub-sources that use different columns."""
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

        subsrc1 = MinimalDataSource(testdata1, fieldnames1)
        subsrc2 = MinimalDataSource(testdata2, fieldnames2)
        self.datasource = MultiDataSource(subsrc1, subsrc2)

    def test_combined_columns(self):
        expected = ['label1', 'label2', 'value', 'label3', 'other_value']
        result = self.datasource.columns()
        self.assertSetEqual(set(expected), set(result))

    def test_unique_method(self):
        # Selected column exists in all sub-sources.
        expected = [('a',), ('b',)]
        result = self.datasource.unique('label1')
        self.assertEqual(expected, list(result))

        # Selected column exists in only one sub-source.
        expected = [('x',), ('y',), ('z',), ('',)]
        result = self.datasource.unique('label2')
        msg = ("Should include empty string as subsrc2 doesn't have "
               "the specified column.")
        self.assertEqual(expected, list(result), msg)

        # 1st in all sources, 2nd in only one sub-source.
        expected = [('a', 'x'),
                    ('a', 'y'),
                    ('b', 'z'),
                    ('a', ''),
                    ('b', '')]
        result = self.datasource.unique('label1', 'label2')
        self.assertEqual(expected, list(result), msg)

        # 1st in all sources, 2nd in only one sub-source, 3rd in none.
        with self.assertRaises(Exception):
            result = self.datasource.unique('label1', 'label2', 'label4')
            list(result)

    def test_kwds_filter(self):
        # Filtered value spans sub-sources.
        expected = [('17',), ('13',), ('20',), ('15',)]
        result = self.datasource.unique('value', label1='a')
        self.assertEqual(expected, list(result))

        # Filter column exists in only one sub-source.
        expected = [('17',), ('13',)]
        result = self.datasource.unique('value', label1='a', label2='x')
        self.assertEqual(expected, list(result))


class TestGroupedDataSource(TestBaseDataSource):
    def setUp(self):
        self.minimal_source = MinimalDataSource(self.testdata, self.fieldnames)
        self.datasource = GroupedDataSource(self.minimal_source, self.fieldnames)

    def test_grouped_no_aggregate(self):
        # Two columns, no aggregate.
        datasource = GroupedDataSource(self.minimal_source, ['label1', 'label2'])
        expected = [
            {'label1': 'a', 'label2': 'x'},
            {'label1': 'a', 'label2': 'y'},
            {'label1': 'a', 'label2': 'z'},
            {'label1': 'b', 'label2': 'z'},
            {'label1': 'b', 'label2': 'y'},
            {'label1': 'b', 'label2': 'x'}
        ]
        result = datasource.slow_iter()
        self.assertEqual(expected, list(result))

        # One column, no aggregate.
        datasource = GroupedDataSource(self.minimal_source, ['label2'])
        expected = [
            {'label2': 'x'},
            {'label2': 'y'},
            {'label2': 'z'},
        ]
        result = datasource.slow_iter()
        self.assertEqual(expected, list(result))

    def test_repr(self):
        # Test with aggregate.
        agg = lambda grp: sum(float(x) for x in grp)
        src = GroupedDataSource(self.minimal_source, ['label1', 'label2'], agg)
        self.assertTrue(repr(src).startswith('GroupedDataSource('))
        self.assertTrue(repr(src).endswith(", ['label1', 'label2'], <lambda>)"))

        # Test without aggregate.
        src = GroupedDataSource(self.minimal_source, ['label1', 'label2'])
        self.assertTrue(repr(src).startswith('GroupedDataSource('))
        self.assertTrue(repr(src).endswith(", ['label1', 'label2'])"))

    def test_grouped_with_aggregate(self):
        # Group by 'label1' and 'label2'.
        def totalpop(group):
            values = [float(row['value']) for row in group]
            return {'total': sum(values)}
        datasource = GroupedDataSource(self.minimal_source,
                                       ['label1', 'label2'],
                                       aggregate=totalpop)

        expected = [
            {'label1': 'a', 'label2': 'x', 'total': 30},  # <- 17 + 13
            {'label1': 'a', 'label2': 'y', 'total': 20},
            {'label1': 'a', 'label2': 'z', 'total': 15},
            {'label1': 'b', 'label2': 'z', 'total': 5 },
            {'label1': 'b', 'label2': 'y', 'total': 40},
            {'label1': 'b', 'label2': 'x', 'total': 25},
        ]
        result = datasource.slow_iter()
        self.assertEqual(expected, list(result))

        # Group by 'label1' only.
        fn = lambda grp: {'value': sum(float(row['value']) for row in grp)}
        datasource = GroupedDataSource(self.minimal_source,
                                       ['label1'],
                                       aggregate=fn)

        expected = [
            {'label1': 'a', 'value': 65.0},
            {'label1': 'b', 'value': 70.0},
        ]
        result = datasource.slow_iter()
        self.assertEqual(expected, list(result))


class TestMappedDataSource(TestBaseDataSource):
    def setUp(self):
        self.fieldnames = ['label1', 'label2', 'value_a', 'value_b']
        self.testdata = [
            ['a', 'x', '17', '23'],
            ['a', 'x', '13', '12'],
            ['a', 'y', '20', '30'],
            ['a', 'z', '15', '15'],
            ['b', 'z',  '5', '11'],
            ['b', 'y', '40', '24'],
            ['b', 'x', '25', '39'],
        ]
        self.minimal_source = MinimalDataSource(self.testdata, self.fieldnames)

        fn = lambda row: {
            'label1': row['label1'],
            'label2': row['label2'],
            'value':  row['value_a'],  # <- 'value_a' mapped to 'value'
        }
        self.datasource = MappedDataSource(self.minimal_source, fn)

    def test_mapped_basic(self):
        def fn(row):
            value_a = float(row['value_a']) if row['value_a'] else 0.0
            value_b = float(row['value_b']) if row['value_b'] else 0.0

            if value_a != None and value_b != None:
                pct = value_a / (value_a + value_b)
            else:
                pct = None

            dic = {
                'label1': row['label1'],
                'label2': row['label2'],
                'percent_a': pct
            }
            return dic

        datasource = MappedDataSource(self.minimal_source, fn)
        result = datasource.slow_iter()

        expected = [
            {'label1': 'a', 'label2': 'x', 'percent_a': 0.425},
            {'label1': 'a', 'label2': 'x', 'percent_a': 0.52},
            {'label1': 'a', 'label2': 'y', 'percent_a': 0.4},
            {'label1': 'a', 'label2': 'z', 'percent_a': 0.5},
            {'label1': 'b', 'label2': 'z', 'percent_a': 0.3125},
            {'label1': 'b', 'label2': 'y', 'percent_a': 0.625},
            {'label1': 'b', 'label2': 'x', 'percent_a': 0.390625},
        ]
        self.assertEqual(list(result), expected)

