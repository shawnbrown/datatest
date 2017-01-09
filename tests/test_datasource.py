# -*- coding: utf-8 -*-
import datetime
import sqlite3
import sys
import textwrap

from . import _unittest as unittest
from datatest.utils.collections import Iterable
from datatest.utils.decimal import Decimal
from datatest.utils import TemporarySqliteTable

from datatest.sources.datasource import DataSource
from datatest.sources.datasource import IterSequence
from datatest.sources.datasource import ResultMapping
from datatest.sources.datasource import _sqlite_sortkey
from datatest.sources.datasource import _validate_call_chain
from datatest.sources.datasource import BaseQuery
from datatest.sources.datasource import DataQuery


class TestValidateCallChain(unittest.TestCase):
    def test_passing(self):
        _validate_call_chain([])
        _validate_call_chain(['foo'])
        _validate_call_chain(['sum', ((), {})])

    def test_container(self):
        with self.assertRaisesRegex(TypeError, "cannot be 'str'"):
            call_chain = 'bad container'
            _validate_call_chain(call_chain)

    def test_type(self):
        regex = "call_chain must be iterable"
        with self.assertRaisesRegex(TypeError, regex):
            call_chain = 123
            _validate_call_chain(call_chain)

    def test_len(self):
        regex = 'expected string or 2-tuple, found 3-tuple'
        with self.assertRaisesRegex(TypeError, regex):
            _validate_call_chain([((), {}, {})])

    def test_first_item(self):
        regex = r"first item must be \*args 'tuple', found 'int'"
        with self.assertRaisesRegex(TypeError, regex):
            _validate_call_chain([(123, {})])

    def test_second_item(self):
        regex = r"second item must be \*\*kwds 'dict', found 'int'"
        with self.assertRaisesRegex(TypeError, regex):
            _validate_call_chain([((), 123)])


class TestBaseQuery(unittest.TestCase):
    def setUp(self):
        class MockSource(object):
            def __repr__(self):
                return '<MockSource object>'

        self.mock_source = MockSource()

    def test_source_only(self):
        source = self.mock_source
        query = BaseQuery(source)  # <- source only (no call chain)

        self.assertIs(query._data_source, source)
        self.assertEqual(query._call_chain, tuple(), 'should be empty')

    def test_source_and_chain(self):
        source = self.mock_source
        chain = ['foo', ((), {})]
        query = BaseQuery(source, chain)

        self.assertIs(query._data_source, source)
        self.assertEqual(query._call_chain, tuple(chain), 'should be tuple, not list')

    def test_map(self):
        source = self.mock_source
        chain = ['foo', ((), {})]
        userfunc = lambda x: str(x).strip()
        query = BaseQuery(source, chain).map(userfunc)

        self.assertIsInstance(query, BaseQuery)

        expected = ('foo', ((), {}), 'map', ((userfunc,), {}))
        self.assertEqual(query._call_chain, expected)

    def test_reduce(self):
        source = self.mock_source
        chain = ['foo', ((), {})]
        userfunc = lambda x, y: x + y
        query = BaseQuery(source, chain).reduce(userfunc)

        self.assertIsInstance(query, BaseQuery)

        expected = ('foo', ((), {}), 'reduce', ((userfunc,), {}))
        self.assertEqual(query._call_chain, expected)

    def test_repr(self):
        source = self.mock_source

        def userfunc(x):
            return str(x).upper()

        # No call chain.
        query = BaseQuery(source)
        expected = """
            BaseQuery(
                data_source=<MockSource object>,
                call_chain=[]
            )
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(repr(query), expected)

        # Call chain with unknown methods.
        query = BaseQuery(source, ['foo', ((), {})])
        expected = """
            BaseQuery(
                data_source=<MockSource object>,
                call_chain=[
                    'foo',
                    ((), {})
                ]
            )
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(repr(query), expected)

        # Call chain with known method.
        query = BaseQuery(source, ['map', ((userfunc,), {})])
        expected = """
            BaseQuery(
                data_source=<MockSource object>,
                call_chain=[
                    'map',
                    ((userfunc,), {})
                ]
            )
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(repr(query), expected)

        # Call chain with multiple known methods.
        call_chain = [
            'map',
            ((userfunc,), {}),
            'reduce',
            ((userfunc,), {}),
        ]
        query = BaseQuery(source, call_chain)
        expected = """
            BaseQuery(
                data_source=<MockSource object>,
                call_chain=[
                    'map',
                    ((userfunc,), {}),
                    'reduce',
                    ((userfunc,), {})
                ]
            )
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(repr(query), expected)

        # Call chain with known method using keyword-args.
        call_chain = [
            'reduce',
            ((), {'function': userfunc}),
        ]
        query = BaseQuery(source, call_chain)
        expected = """
            BaseQuery(
                data_source=<MockSource object>,
                call_chain=[
                    'reduce',
                    ((), {'function': userfunc})
                ]
            )
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(repr(query), expected)

        # Call chain with known and unknown methods.
        call_chain = [
            'map',
            ((userfunc,), {}),
            'blerg',
            ((), {}),
            'map',
            ((userfunc,), {}),
            'reduce',
            ((userfunc,), {}),
        ]
        query = BaseQuery(source, call_chain)
        expected = """
            BaseQuery(
                data_source=<MockSource object>,
                call_chain=[
                    'map',
                    ((userfunc,), {}),
                    'blerg',
                    ((), {}),
                    'map',
                    ((userfunc,), {}),
                    'reduce',
                    ((userfunc,), {})
                ]
            )
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(repr(query), expected)

    def test_getattr(self):
        query = BaseQuery(self.mock_source)

        query = query.foo
        self.assertEqual(query._call_chain, ('foo',))

        query = query.bar
        self.assertEqual(query._call_chain, ('foo', 'bar'))

    def test_call(self):
        query = BaseQuery(self.mock_source)

        query = query.foo()
        expected = (
            'foo', ((), {}),
        )
        self.assertEqual(query._call_chain, expected)

        query = query.bar('BAR')
        expected = (
            'foo', ((), {}),
            'bar', (('BAR',), {})
        )
        self.assertEqual(query._call_chain, expected)

        query = query.baz
        expected = (
            'foo', ((), {}),
            'bar', (('BAR',), {}),
            'baz',
        )
        self.assertEqual(query._call_chain, expected)

        query = query.corge(qux='quux')
        expected = (
            'foo', ((), {}),
            'bar', (('BAR',), {}),
            'baz',
            'corge', ((), {'qux': 'quux'})
        )
        self.assertEqual(query._call_chain, expected)

    def test_eval(self):
        query = BaseQuery('hello world')
        result = query.upper()._eval()
        self.assertIsInstance(result, str, "should be 'str' not a result object")
        self.assertEqual(result, 'HELLO WORLD')

        query = BaseQuery('123')
        result = query.isdigit()._eval()
        self.assertIsInstance(result, bool, "should be 'bool' not a result object")
        self.assertEqual(result, True)


class TestIterSequence(unittest.TestCase):
    def test_repr(self):
        iterator = IterSequence([1, 2, 3, 4, 5])
        iterator_repr = repr(iterator)

        expected = 'IterSequence({0})'.format(repr(iterator._iterator))
        self.assertEqual(iterator_repr, expected)

    def test_iter(self):
        iterator = IterSequence([1, 2, 3, 4, 5])

        self.assertIsInstance(iterator, Iterable)
        self.assertEqual(list(iterator), [1, 2, 3, 4, 5])

    def test_map(self):
        iterator = IterSequence([1, 2, 3, 4, 5])
        iterator = iterator.map(lambda x: x * 2)

        self.assertIsInstance(iterator, IterSequence)
        self.assertEqual(list(iterator), [2, 4, 6, 8, 10])

    def test_map_multiple_args(self):
        # Using a function of one argument.
        iterator = IterSequence([(1, 1), (2, 2), (3, 3)])
        function = lambda x: '{0}-{1}'.format(x[0], x[1])
        as_list = list(iterator.map(function))
        self.assertEqual(as_list, ['1-1', '2-2', '3-3'])

        # Using a function of two arguments.
        iterator = IterSequence([(1, 1), (2, 2), (3, 3)])
        function = lambda x, y: '{0}-{1}'.format(x, y)
        as_list = list(iterator.map(function))
        self.assertEqual(as_list, ['1-1', '2-2', '3-3'])

    def test_reduce(self):
        iterator = IterSequence([2, 2, 2, 2, 2])
        multiply = lambda x, y: x * y
        result = iterator.reduce(multiply)
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


class TestIterSequenceSum(SqliteHelper):
    """The IterSequence's sum() method should behave the same as
    SQLite's SUM function.

    See SQLite docs for more details:
        https://www.sqlite.org/lang_aggfunc.html
    """
    def test_numeric(self):
        """Test numeric values of different types (int, float, Decimal)."""
        values = [10, 10.0, Decimal('10')]

        result = self.sqlite3_aggregate('SUM', values)
        self.assertEqual(result, 30)

        result = IterSequence(values).sum()
        self.assertEqual(result, 30)

    def test_strings(self):
        """Test strings that coerce to numeric values."""
        values = ['10', '10', '10']

        result = self.sqlite3_aggregate('SUM', values)
        self.assertEqual(result, 30)

        result = IterSequence(values).sum()
        self.assertEqual(result, 30)

    def test_some_empty(self):
        """Test empty string handling."""
        values = [None, '10', '', '10']

        result = self.sqlite3_aggregate('SUM', values)
        self.assertEqual(result, 20)

        result = IterSequence(values).sum()
        self.assertEqual(result, 20)

    def test_some_nonnumeric(self):
        """Test strings that do not look like numbers."""
        values = ['10', 'AAA', '10', '-5']

        result = self.sqlite3_aggregate('SUM', values)
        self.assertEqual(result, 15)

        result = IterSequence(values).sum()
        self.assertEqual(result, 15)

    def test_all_nonnumeric(self):
        """Average list containing all non-numeric strings."""
        values = ['AAA', 'BBB', 'CCC']

        result = self.sqlite3_aggregate('SUM', values)
        self.assertEqual(result, 0)

        result = IterSequence(values).sum()
        self.assertEqual(result, 0)

    def test_some_none(self):
        """Test None value handling."""
        values = [None, 10, 10]  # SQLite SUM skips NULL values.

        result = self.sqlite3_aggregate('SUM', values)
        self.assertEqual(result, 20)

        result = IterSequence(values).sum()
        self.assertEqual(result, 20)

    def test_none_or_emptystring(self):
        """Test all None or empty string handling."""
        values = [None, None, '']

        result = self.sqlite3_aggregate('SUM', values)
        self.assertEqual(result, 0)

        result = IterSequence(values).sum()
        self.assertEqual(result, 0)

    def test_all_none(self):
        """Test all None handling."""
        values = [None, None, None]

        result = self.sqlite3_aggregate('SUM', values)
        self.assertEqual(result, None)

        result = IterSequence(values).sum()
        self.assertEqual(result, None)


class TestIterSequenceAvg(SqliteHelper):
    """The IterSequence's avg() method should behave the same as
    SQLite's AVG function.

    See SQLite docs for more details:
        https://www.sqlite.org/lang_aggfunc.html
    """
    def test_numeric(self):
        """Test numeric values of different types (int, float, Decimal)."""
        values = [0, 6.0, Decimal('9')]

        result = self.sqlite3_aggregate('AVG', values)
        self.assertEqual(result, 5)

        result = IterSequence(values).avg()
        self.assertEqual(result, 5)

    def test_strings(self):
        """Test strings that coerce to numeric values."""
        values = ['0', '6.0', '9']

        result = self.sqlite3_aggregate('AVG', values)
        self.assertEqual(result, 5)

        result = IterSequence(values).avg()
        self.assertEqual(result, 5)

    def test_some_empty(self):
        """Test empty string handling."""
        values = ['', 3, 9]  # SQLite AVG coerces empty string to 0.0.

        result = self.sqlite3_aggregate('AVG', values)
        self.assertEqual(result, 4.0)

        result = IterSequence(values).avg()
        self.assertEqual(result, 4.0)

    def test_some_nonnumeric(self):
        """Test strings that do not look like numbers."""
        values = ['AAA', '3', '9']  # SQLite coerces invalid strings to 0.0.

        result = self.sqlite3_aggregate('AVG', values)
        self.assertEqual(result, 4.0)

        result = IterSequence(values).avg()
        self.assertEqual(result, 4.0)

    def test_all_nonnumeric(self):
        """Average list containing all non-numeric strings."""
        values = ['AAA', 'BBB', 'CCC']

        result = self.sqlite3_aggregate('AVG', values)
        self.assertEqual(result, 0)

        result = IterSequence(values).avg()
        self.assertEqual(result, 0)

    def test_some_none(self):
        """Test None value handling."""
        values = [None, 3, 9]  # SQLite AVG skips NULL values.

        result = self.sqlite3_aggregate('AVG', values)
        self.assertEqual(result, 6.0)

        result = IterSequence(values).avg()
        self.assertEqual(result, 6.0)

    def test_none_or_emptystring(self):
        """Test all None or empty string handling."""
        values = [None, None, '']

        result = self.sqlite3_aggregate('AVG', values)
        self.assertEqual(result, 0)

        result = IterSequence(values).avg()
        self.assertEqual(result, 0)

    def test_all_none(self):
        """Test all None handling."""
        values = [None, None, None]

        result = self.sqlite3_aggregate('AVG', values)
        self.assertEqual(result, None)

        result = IterSequence(values).avg()
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


class TestIterSequenceMaxAndMin(unittest.TestCase):
    """Should match SQLite MAX() and MIN() aggregation behavior.

    See SQLite docs for full details:

        https://www.sqlite.org/lang_aggfunc.html
    """
    def test_max(self):
        result = IterSequence([None, 10, 20, 30]).max()
        self.assertEqual(result, 30)

        result = IterSequence([None, 10, '20', 30]).max()
        self.assertEqual(result, '20')

        blob_10 = sqlite3.Binary(b'10')
        result = IterSequence([None, blob_10, '20', 30]).max()
        self.assertEqual(result, blob_10)

    def test_max_null_handling(self):
        """Should return None if and only if there are non-None values
        in the group.
        """
        result = IterSequence([None, None]).max()
        self.assertEqual(result, None)

        result = IterSequence([]).max()
        self.assertEqual(result, None)

    def test_min(self):
        blob_30 = sqlite3.Binary(b'30')
        blob_20 = sqlite3.Binary(b'20')
        blob_10 = sqlite3.Binary(b'10')
        blob_empty = sqlite3.Binary(b'')

        result = IterSequence([blob_30, blob_20, blob_10, blob_empty]).min()
        self.assertEqual(result, blob_empty)

        result = IterSequence([blob_30, blob_20, '10', blob_empty]).min()
        self.assertEqual(result, '10')

        result = IterSequence([blob_30, 20, '10', blob_empty]).min()
        self.assertEqual(result, 20)

    def test_min_null_handling(self):
        """The minimum value is the first non-None value that would
        appear in when sorted in _sqlite_sortkey() order.

        Should return None if and only if there are non-None values
        in the group.
        """
        result = IterSequence([None, 20, '10', sqlite3.Binary(b'')]).min()
        self.assertEqual(result, 20)  # Since 20 is non-None, it is returned.

        result = IterSequence([None, None, None, None]).min()
        self.assertEqual(result, None)


class TestResultMapping(unittest.TestCase):
    def test_repr(self):
        sequence = ResultMapping({'a': [1, 2, 3, 4, 5]})
        sequence_repr = repr(sequence)
        expected = "ResultMapping({'a': [1, 2, 3, 4, 5]})"
        self.assertEqual(sequence_repr, expected)

    def test_map(self):
        mapping = ResultMapping({'a': [1, 2, 3, 4, 5]})

        mapping = mapping.map(lambda x: x * 2)
        self.assertIsInstance(mapping, ResultMapping)

        result_a = list(mapping['a'])
        self.assertEqual(result_a, [2, 4, 6, 8, 10])

    def test_map_multiple_args(self):
        mapping = ResultMapping({'a': [(1, 1), (2, 2), (3, 3)]})
        expected = ResultMapping({'a': ['1-1', '2-2', '3-3']})

        # Using a function of one argument.
        function = lambda x: '{0}-{1}'.format(x[0], x[1])
        result = mapping.map(function)
        result_a = list(result['a'])
        self.assertEqual(result_a, ['1-1', '2-2', '3-3'])

        # Using a function of two arguments.
        function = lambda x, y: '{0}-{1}'.format(x, y)
        result = mapping.map(function)
        result_a = list(result['a'])
        self.assertEqual(result_a, ['1-1', '2-2', '3-3'])

    def test_sum(self):
        mapping = ResultMapping({'a': [1, 2, 3, 4, 5]})

        mapping = mapping.sum()
        self.assertIsInstance(mapping, ResultMapping)

        expected = ResultMapping({'a': 15})
        self.assertEqual(mapping, expected)

    def test_reduce(self):
        mapping = ResultMapping({'a': [2, 2, 2, 2, 2]})
        multiply = lambda x, y: x * y
        result = mapping.reduce(multiply)
        self.assertEqual(result, ResultMapping({'a': 32}))


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
        result = self.source.select('label1')
        self.assertIsInstance(result, IterSequence)
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

        result = self.source.select('label1', 'label2')
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

        result = self.source.select({'label1': 'value'})
        expected = {
            'a': ['17', '13', '20', '15'],
            'b': ['5', '40', '25'],
        }
        self.assertEqual(result, expected)

        result = self.source.select({'label1': ('label2', 'value')})
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

        result = self.source.select({('label1', 'label2'): 'value'})
        expected = {
            ('a', 'x'): ['17', '13'],
            ('a', 'y'): ['20'],
            ('a', 'z'): ['15'],
            ('b', 'z'): ['5'],
            ('b', 'y'): ['40'],
            ('b', 'x'): ['25'],
        }
        self.assertEqual(result, expected)

        result = self.source.select({('label1', 'label2'): ('label2', 'value')})
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
        regex = "{'label2': 'value'} not in DataSource"
        with self.assertRaisesRegex(LookupError, regex, msg=msg):
            self.source.select({'label1': {'label2': 'value'}})

    def test_call(self):
        result = self.source('label1')
        self.assertIsInstance(result, DataQuery)

        result = list(result.eval())
        expected = ['a', 'a', 'a', 'a', 'b', 'b', 'b']
        self.assertEqual(result, expected)

        result = self.source({'label1': 'label2'})
        self.assertIsInstance(result, DataQuery)

        result = dict(result.eval())
        expected = {
            'a': ['x', 'x', 'y', 'z'],
            'b': ['z', 'y', 'x'],
        }
        self.assertEqual(result, expected)
