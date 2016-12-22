# -*- coding: utf-8 -*-
import datetime
import sqlite3
import sys

from . import _unittest as unittest
from datatest.utils.collections import Iterable
from datatest.utils.decimal import Decimal
from datatest.utils import TemporarySqliteTable

from datatest.sources.datasource import DataSource
from datatest.sources.datasource import ResultSequence
from datatest.sources.datasource import _sqlite_sortkey


class TestResultSequence(unittest.TestCase):
    def test_repr(self):
        sequence = ResultSequence([1, 2, 3, 4, 5])
        sequence_repr = repr(sequence)

        expected = 'ResultSequence([1, 2, 3, 4, 5])'
        self.assertEqual(sequence_repr, expected)

    def test_iter(self):
        sequence = ResultSequence([1, 2, 3, 4, 5])

        as_iter = iter(sequence)
        self.assertIsInstance(as_iter, Iterable)

        as_list = [x for x in sequence]
        self.assertEqual(as_list, [1, 2, 3, 4, 5])

    def test_map(self):
        sequence = ResultSequence([1, 2, 3, 4, 5])

        sequence = sequence.map(lambda x: x * 2)
        self.assertIsInstance(sequence, ResultSequence)

        as_list = list(sequence)
        self.assertEqual(as_list, [2, 4, 6, 8, 10])

    def test_map_multiple_args(self):
        sequence = ResultSequence([(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)])

        # Using a function of one argument.
        function = lambda x: '{0}-{1}'.format(x[0], x[1])
        as_list = list(sequence.map(function))
        self.assertEqual(as_list, ['1-1', '2-2', '3-3', '4-4', '5-5'])

        # Using a function of two arguments.
        function = lambda x, y: '{0}-{1}'.format(x, y)
        as_list = list(sequence.map(function))
        self.assertEqual(as_list, ['1-1', '2-2', '3-3', '4-4', '5-5'])

    def test_reduce(self):
        sequence = ResultSequence([2, 2, 2, 2, 2])
        multiply = lambda x, y: x * y
        result = sequence.reduce(multiply)
        self.assertEqual(result, 32)


class SqliteHelper(unittest.TestCase):
    """Helper class for testing DataSource parity with SQLite behavior."""
    @staticmethod
    def sqlite3_aggregate(function_name, values):
        """Test SQLite3 aggregation function on list of values."""
        assert function_name in ('AVG', 'COUNT', 'GROUP_CONCAT', 'MAX', 'MIN', 'SUM', 'TOTAL')
        values = [[x] for x in values]  # Wrap as single-column rows.
        temptable = TemporarySqliteTable(values, ['values'])

        cursor = temptable.connection.cursor()
        table = temptable.name
        query = 'SELECT {0}("values") FROM {1}'.format(function_name, table)
        cursor.execute(query)

        result = cursor.fetchall()[0][0]
        cursor.close()
        return result


class TestResultSequenceSum(SqliteHelper):
    """The ResultSequence's sum() method should behave the same as
    SQLite's SUM function.

    See SQLite docs for more details:
        https://www.sqlite.org/lang_aggfunc.html
    """
    def test_numeric(self):
        """Sum numeric values of different types (int, float, Decimal)."""
        values = [10, 10.0, Decimal('10')]

        result = self.sqlite3_aggregate('SUM', values)
        self.assertEqual(result, 30)

        result = ResultSequence(values).sum()
        self.assertEqual(result, 30)

    def test_strings(self):
        """Sum strings--cast as float, internally."""
        values = ['10', '10', '10']

        result = self.sqlite3_aggregate('SUM', values)
        self.assertEqual(result, 30)

        result = ResultSequence(values).sum()
        self.assertEqual(result, 30)

    def test_some_empty(self):
        """Sum list containing empty values."""
        values = [None, '10', '', '10']

        result = self.sqlite3_aggregate('SUM', values)
        self.assertEqual(result, 20)

        result = ResultSequence(values).sum()
        self.assertEqual(result, 20)

    def test_some_nonnumeric(self):
        """Sum list containing some non-numeric strings."""
        values = ['10', 'AAA', '10', '-5']

        result = self.sqlite3_aggregate('SUM', values)
        self.assertEqual(result, 15)

        result = ResultSequence(values).sum()
        self.assertEqual(result, 15)

    def test_all_nonnumeric(self):
        """Sum list containing some non-numeric strings."""
        values = ['AAA', 'BBB', 'CCC']

        result = self.sqlite3_aggregate('SUM', values)
        self.assertEqual(result, 0)

        result = ResultSequence(values).sum()
        self.assertEqual(result, 0)

    def test_none_or_emptystring(self):
        values = [None, None, '']

        result = self.sqlite3_aggregate('SUM', values)
        self.assertEqual(result, 0)

        result = ResultSequence(values).sum()
        self.assertEqual(result, 0)

    def test_all_none(self):
        values = [None, None, None]

        result = self.sqlite3_aggregate('SUM', values)
        self.assertEqual(result, None)

        result = ResultSequence(values).sum()
        self.assertEqual(result, None)


class TestResultSequenceAvg(SqliteHelper):
    """The ResultSequence's avg() method should behave the same as
    SQLite's AVG function.

    See SQLite docs for more details:
        https://www.sqlite.org/lang_aggfunc.html
    """
    def test_numeric(self):
        """Sum numeric values of different types (int, float, Decimal)."""
        values = [0, 6.0, Decimal('9')]

        result = self.sqlite3_aggregate('AVG', values)
        self.assertEqual(result, 5)

        result = ResultSequence(values).avg()
        self.assertEqual(result, 5)

    def test_strings(self):
        """Average strings--cast as float, internally."""
        values = ['0', '6.0', '9']

        result = self.sqlite3_aggregate('AVG', values)
        self.assertEqual(result, 5)

        result = ResultSequence(values).avg()
        self.assertEqual(result, 5)

    def test_some_empty(self):
        """Sum list containing empty values."""
        values = ['', 3, 9]  # SQLite AVG coerces empty string to 0.0.

        result = self.sqlite3_aggregate('AVG', values)
        self.assertEqual(result, 4.0)

        result = ResultSequence(values).avg()
        self.assertEqual(result, 4.0)

    def test_some_none(self):
        """Sum list containing empty values."""
        values = [None, 3, 9]  # SQLite AVG skips NULL values.

        result = self.sqlite3_aggregate('AVG', values)
        self.assertEqual(result, 6.0)

        result = ResultSequence(values).avg()
        self.assertEqual(result, 6.0)

    def test_some_nonnumeric(self):
        """Sum list containing some non-numeric strings."""
        values = ['AAA', '3', '9']  # SQLite coerces invalid strings to 0.0.

        result = self.sqlite3_aggregate('AVG', values)
        self.assertEqual(result, 4.0)

        result = ResultSequence(values).avg()
        self.assertEqual(result, 4.0)

    def test_all_nonnumeric(self):
        """Sum list containing some non-numeric strings."""
        values = ['AAA', 'BBB', 'CCC']

        result = self.sqlite3_aggregate('AVG', values)
        self.assertEqual(result, 0)

        result = ResultSequence(values).avg()
        self.assertEqual(result, 0)

    def test_none_or_emptystring(self):
        values = [None, None, '']

        result = self.sqlite3_aggregate('AVG', values)
        self.assertEqual(result, 0)

        result = ResultSequence(values).avg()
        self.assertEqual(result, 0)

    def test_all_none(self):
        values = [None, None, None]

        result = self.sqlite3_aggregate('AVG', values)
        self.assertEqual(result, None)

        result = ResultSequence(values).avg()
        self.assertEqual(result, None)


class TestSqliteSortkey(unittest.TestCase):
    """Text _sqlite_sortkey() behavior--should match SQLite sort behavior
    for supported cases.
    """
    def test_sqlite_blob(self):
        """Confirm SQLite blob-type handling."""
        # Create in-memory database.
        connection = sqlite3.connect(':memory:')
        cursor = connection.cursor()
        cursor.execute('CREATE TABLE testtable(testcolumn BLOB);')

        # Make blob and insert into database.
        blob_in = sqlite3.Binary(b'blob contents')
        insert_stmnt = "INSERT INTO testtable (testcolumn) VALUES(?)"
        cursor.execute(insert_stmnt, (sqlite3.Binary(blob_in),))
        connection.commit()

        # Fetch and unpack blob result.
        cursor.execute("SELECT * FROM testtable")
        blob_out = cursor.fetchall()[0][0]

        if sys.version_info[0] >= 3:
            sqlite3_blob_type = bytes
        else:
            sqlite3_blob_type = sqlite3.Binary
        self.assertIsInstance(blob_out, sqlite3_blob_type)

    def test_null_key(self):
        self.assertEqual(_sqlite_sortkey(None), (0, 0))

    def test_numeric_key(self):
        self.assertEqual(_sqlite_sortkey(5), (1, 5))
        self.assertEqual(_sqlite_sortkey(2.0), (1, 2.0))
        self.assertEqual(_sqlite_sortkey(Decimal(50)), (1, Decimal(50)))

    def test_text_key(self):
        self.assertEqual(_sqlite_sortkey('A'), (2, 'A'))

    def test_blob_key(self):
        blob = sqlite3.Binary( b'other value')
        self.assertEqual(_sqlite_sortkey(blob), (3, blob))

    def test_other_key(self):
        list_value = ['other', 'value']
        self.assertEqual(_sqlite_sortkey(list_value), (4, list_value))

        dict_value = {'other': 'value'}
        self.assertEqual(_sqlite_sortkey(dict_value), (4, dict_value))

        date_value = datetime.datetime(2014, 2, 14, 9, 30)  # YYYY-MM-DD HH:MM:SS.mmmmmm
        self.assertEqual(_sqlite_sortkey(date_value), (4, date_value))

    def test_mixed_type_sort(self):
        blob = sqlite3.Binary(b'aaa')
        unordered = ['-5', blob, -5, 'N', Decimal(1), 'n', 0, '', None, 1.5]
        expected_order = [None, -5, 0, Decimal(1), 1.5, '', '-5', 'N', 'n', blob]

        # Build SQLite table of unordered values.
        values = [[x] for x in unordered]  # Wrap as single-column rows.
        temptable = TemporarySqliteTable(values, ['values'])
        cursor = temptable.connection.cursor()
        table = temptable.name

        # Query SQLite using ORDER BY.
        query = 'SELECT "values" FROM {0} ORDER BY "values"'.format(table)
        cursor.execute(query)
        sqlite_order = [x[0] for x in cursor.fetchall()]
        cursor.close()

        # Check that SQLite order matches expected order.
        self.assertEqual(sqlite_order, expected_order)

        # Check that _sqlite_sortkey() order matches SQLite order.
        sortkey_order = sorted(unordered, key=_sqlite_sortkey)
        self.assertEqual(sortkey_order, sqlite_order)


class TestResultSequenceMaxAndMin(unittest.TestCase):
    def test_max(self):
        result = ResultSequence([None, 10, 20, 30]).max()
        self.assertEqual(result, 30)

        result = ResultSequence([None, 10, '20', 30]).max()
        self.assertEqual(result, '20')

        blob_10 = sqlite3.Binary(b'10')
        result = ResultSequence([None, blob_10, '20', 30]).max()
        self.assertEqual(result, blob_10)

        result = ResultSequence([None, None, None, None]).max()
        self.assertEqual(result, None)

    def test_min(self):
        blob_30 = sqlite3.Binary(b'30')
        blob_20 = sqlite3.Binary(b'20')
        blob_10 = sqlite3.Binary(b'10')
        blob_empty = sqlite3.Binary(b'')

        result = ResultSequence([blob_30, blob_20, blob_10, blob_empty]).min()
        self.assertEqual(result, blob_empty)

        result = ResultSequence([blob_30, blob_20, '10', blob_empty]).min()
        self.assertEqual(result, '10')

        result = ResultSequence([blob_30, 20, '10', blob_empty]).min()
        self.assertEqual(result, 20)

        result = ResultSequence([None, 20, '10', blob_empty]).min()
        self.assertEqual(result, None)


class TestDataSourceBasics(unittest.TestCase):
    def setUp(self):
        columns = ['label1', 'label2', 'value']
        data = [['a', 'x', '17'],
                ['a', 'x', '13'],
                ['a', 'y', '20'],
                ['a', 'z', '15'],
                ['b', 'z', '5' ],
                ['b', 'y', '40'],
                ['b', 'x', '25']]
        self.source = DataSource(data, columns)

    def test_columns(self):
        expected = ['label1', 'label2', 'value']
        self.assertEqual(self.source.columns(), expected)

    def test_iter(self):
        """Test __iter__."""
        result = [row for row in self.source]
        expected = [
            {'label1': 'a', 'label2': 'x', 'value': '17'},
            {'label1': 'a', 'label2': 'x', 'value': '13'},
            {'label1': 'a', 'label2': 'y', 'value': '20'},
            {'label1': 'a', 'label2': 'z', 'value': '15'},
            {'label1': 'b', 'label2': 'z', 'value': '5' },
            {'label1': 'b', 'label2': 'y', 'value': '40'},
            {'label1': 'b', 'label2': 'x', 'value': '25'},
        ]
        self.assertEqual(expected, result)

    def test_select(self):
        result = self.source('label1')
        expected = [
            'a',
            'a',
            'a',
            'a',
            'b',
            'b',
            'b',
        ]
        self.assertEqual(list(result), expected)

        result = self.source('label1', 'label2')
        expected = [
            ('a', 'x'),
            ('a', 'x'),
            ('a', 'y'),
            ('a', 'z'),
            ('b', 'z'),
            ('b', 'y'),
            ('b', 'x'),
        ]
        self.assertEqual(list(result), expected)

        result = self.source(['label1'], 'value')
        expected = {
            'a': [
                '17',
                '13',
                '20',
                '15',
            ],
            'b': [
                '5',
                '40',
                '25',
            ],
        }
        self.assertEqual(result, expected)

        result = self.source(['label1'], 'label2', 'value')
        expected = {
            'a': [
                ('x', '17'),
                ('x', '13'),
                ('y', '20'),
                ('z', '15'),
            ],
            'b': [
                ('z', '5'),
                ('y', '40'),
                ('x', '25'),
            ],
        }
        self.assertEqual(result, expected)

        result = self.source(['label1', 'label2'], 'value')
        expected = {
            ('a', 'x'): ['17', '13'],
            ('a', 'y'): ['20'],
            ('a', 'z'): ['15'],
            ('b', 'z'): ['5'],
            ('b', 'y'): ['40'],
            ('b', 'x'): ['25'],
        }
        self.assertEqual(result, expected)

        result = self.source(['label1', 'label2'], 'label2', 'value')
        expected = {
            ('a', 'x'): [('x', '17'), ('x', '13')],
            ('a', 'y'): [('y', '20')],
            ('a', 'z'): [('z', '15')],
            ('b', 'z'): [('z', '5')],
            ('b', 'y'): [('y', '40')],
            ('b', 'x'): [('x', '25')],
        }
        self.assertEqual(result, expected)

        msg = 'Support for nested dictionaries removed (for now).'
        with self.assertRaises(Exception, msg=msg):
            self.source(['label1'], ['label2'], 'value')
