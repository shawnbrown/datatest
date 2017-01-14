# -*- coding: utf-8 -*-
import datetime
import sqlite3
import sys
import textwrap

from . import _unittest as unittest
from datatest.utils.collections import Iterator
from datatest.utils.decimal import Decimal
from datatest.utils import TemporarySqliteTable

from datatest.sources.datasource import DataSource
from datatest.sources.datasource import DataResult
from datatest.sources.datasource import _sqlite_sum
from datatest.sources.datasource import _sqlite_avg
from datatest.sources.datasource import _sqlite_sortkey
from datatest.sources.datasource import _sqlite_min
from datatest.sources.datasource import _sqlite_max
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
    def test_source_only(self):
        source = 'hello_world'
        query = BaseQuery(source)  # <- source only (no call chain)

        self.assertIs(query._data_source, source)
        self.assertEqual(query._call_chain, tuple(), 'should be empty')

    def test_source_and_chain(self):
        source = 'hello_world'
        chain = ['replace', (('_', ' '), {})]
        query = BaseQuery(source, chain)

        self.assertIs(query._data_source, source)
        self.assertEqual(query._call_chain, tuple(chain), 'should be tuple, not list')

    def test_map(self):
        source = 'hello_world'
        chain = ['replace', (('_', ' '), {})]
        userfunc = lambda x: str(x).strip()
        query = BaseQuery(source, chain).map(userfunc)

        self.assertIsInstance(query, BaseQuery)

        expected = ('replace', (('_', ' '), {}), 'map', ((userfunc,), {}))
        self.assertEqual(query._call_chain, expected)

    def test_reduce(self):
        source = 'hello_world'
        chain = ['foo', ((), {})]
        userfunc = lambda x, y: x + y
        query = BaseQuery(source, chain).reduce(userfunc)

        self.assertIsInstance(query, BaseQuery)

        expected = ('foo', ((), {}), 'reduce', ((userfunc,), {}))
        self.assertEqual(query._call_chain, expected)

    def test_repr(self):
        source = 'hello_world'

        def userfunc(x):
            return str(x).upper()

        # No call chain.
        query = BaseQuery(source)
        expected = """
            <class 'datatest.BaseQuery'>
            Source: 'hello_world'
            Query: <empty>
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(repr(query), expected)

        # Call chain with single method.
        query = BaseQuery(source, ['replace', (('_', ' '), {})])
        expected = """
            <class 'datatest.BaseQuery'>
            Source: 'hello_world'
            Query:
            | replace('_', ' ')
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(repr(query), expected)

        # Call chain with multiple methods.
        call_chain = [
            'replace',
            (('_', ' '), {}),
            'title',
            ((), {}),
        ]
        query = BaseQuery(source, call_chain)
        expected = """
            <class 'datatest.BaseQuery'>
            Source: 'hello_world'
            Query:
            | replace('_', ' ')
              | title()
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(repr(query), expected)

        # Call chain with method using keyword-args.
        call_chain = [
            'some_unknown_method',
            ((), {'function': userfunc}),
        ]
        query = BaseQuery(source, call_chain)
        expected = """
            <class 'datatest.BaseQuery'>
            Source: 'hello_world'
            Query:
            | some_unknown_method(function=userfunc)
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(repr(query), expected)

        # Check nesting
        call_chain = [
            'replace',
            (('_', ' '), {}),
            'title',
            ((), {}),
            'center',
            ((25,), {}),
        ]
        query = BaseQuery(source, call_chain)
        expected = """
            <class 'datatest.BaseQuery'>
            Source: 'hello_world'
            Query:
            | replace('_', ' ')
              | title()
                | center(25)
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(repr(query), expected)

    def test_getattr(self):
        query = BaseQuery('hello_world')

        query = query.replace
        self.assertEqual(query._call_chain, ('replace',))

        query = query.unknown_property
        self.assertEqual(query._call_chain, ('replace', 'unknown_property'))

    def test_call(self):
        query = BaseQuery('hello_world')

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
        query = BaseQuery('hello_world').upper()
        self.assertEqual(query._eval(), 'HELLO_WORLD')

        query = BaseQuery('AAA123').isdigit()
        self.assertIs(query._eval(), False)

        query = BaseQuery('AAA123').replace('A', '').isdigit()
        self.assertIs(query._eval(), True)


class TestDataQuery(unittest.TestCase):
    def setUp(self):
        self.source = source = DataSource([
            {'label1': 'a', 'label2': 'x', 'value': '17'},
            {'label1': 'a', 'label2': 'x', 'value': '13'},
            {'label1': 'a', 'label2': 'y', 'value': '20'},
            {'label1': 'a', 'label2': 'z', 'value': '15'},
            {'label1': 'b', 'label2': 'z', 'value':  '5'},
            {'label1': 'b', 'label2': 'y', 'value': '40'},
            {'label1': 'b', 'label2': 'x', 'value': '25'},
        ])

    def test_type(self):
        query = DataQuery(self.source)
        self.assertIsInstance(query, BaseQuery)


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


class TestSqliteSum(SqliteHelper):
    """The _sqlite_sum() method should behave the same as
    SQLite's SUM function.

    See SQLite docs for more details:
        https://www.sqlite.org/lang_aggfunc.html
    """
    def test_numeric(self):
        """Test numeric values of different types (int, float, Decimal)."""
        values = [10, 10.0, Decimal('10')]

        result = self.sqlite3_aggregate('SUM', values)
        self.assertEqual(result, 30)

        result = _sqlite_sum(values)
        self.assertEqual(result, 30)

    def test_strings(self):
        """Test strings that coerce to numeric values."""
        values = ['10', '10', '10']

        result = self.sqlite3_aggregate('SUM', values)
        self.assertEqual(result, 30)

        result = _sqlite_sum(values)
        self.assertEqual(result, 30)

    def test_some_empty(self):
        """Test empty string handling."""
        values = [None, '10', '', '10']

        result = self.sqlite3_aggregate('SUM', values)
        self.assertEqual(result, 20)

        result = _sqlite_sum(values)
        self.assertEqual(result, 20)

    def test_some_nonnumeric(self):
        """Test strings that do not look like numbers."""
        values = ['10', 'AAA', '10', '-5']

        result = self.sqlite3_aggregate('SUM', values)
        self.assertEqual(result, 15)

        result = _sqlite_sum(values)
        self.assertEqual(result, 15)

    def test_all_nonnumeric(self):
        """Average list containing all non-numeric strings."""
        values = ['AAA', 'BBB', 'CCC']

        result = self.sqlite3_aggregate('SUM', values)
        self.assertEqual(result, 0)

        result = _sqlite_sum(values)
        self.assertEqual(result, 0)

    def test_some_none(self):
        """Test None value handling."""
        values = [None, 10, 10]  # SQLite SUM skips NULL values.

        result = self.sqlite3_aggregate('SUM', values)
        self.assertEqual(result, 20)

        result = _sqlite_sum(values)
        self.assertEqual(result, 20)

    def test_none_or_emptystring(self):
        """Test all None or empty string handling."""
        values = [None, None, '']

        result = self.sqlite3_aggregate('SUM', values)
        self.assertEqual(result, 0)

        result = _sqlite_sum(values)
        self.assertEqual(result, 0)

    def test_all_none(self):
        """Test all None handling."""
        values = [None, None, None]

        result = self.sqlite3_aggregate('SUM', values)
        self.assertEqual(result, None)

        result = _sqlite_sum(values)
        self.assertEqual(result, None)


class TestSqliteAvg(SqliteHelper):
    """The _sqlite_avg() method should behave the same as
    SQLite's AVG function.

    See SQLite docs for more details:
        https://www.sqlite.org/lang_aggfunc.html
    """
    def test_numeric(self):
        """Test numeric values of different types (int, float, Decimal)."""
        values = [0, 6.0, Decimal('9')]

        result = self.sqlite3_aggregate('AVG', values)
        self.assertEqual(result, 5)

        result = _sqlite_avg(values)
        self.assertEqual(result, 5)

    def test_strings(self):
        """Test strings that coerce to numeric values."""
        values = ['0', '6.0', '9']

        result = self.sqlite3_aggregate('AVG', values)
        self.assertEqual(result, 5)

        result = _sqlite_avg(values)
        self.assertEqual(result, 5)

    def test_some_empty(self):
        """Test empty string handling."""
        values = ['', 3, 9]  # SQLite AVG coerces empty string to 0.0.

        result = self.sqlite3_aggregate('AVG', values)
        self.assertEqual(result, 4.0)

        result = _sqlite_avg(values)
        self.assertEqual(result, 4.0)

    def test_some_nonnumeric(self):
        """Test strings that do not look like numbers."""
        values = ['AAA', '3', '9']  # SQLite coerces invalid strings to 0.0.

        result = self.sqlite3_aggregate('AVG', values)
        self.assertEqual(result, 4.0)

        result = _sqlite_avg(values)
        self.assertEqual(result, 4.0)

    def test_all_nonnumeric(self):
        """Average list containing all non-numeric strings."""
        values = ['AAA', 'BBB', 'CCC']

        result = self.sqlite3_aggregate('AVG', values)
        self.assertEqual(result, 0)

        result = _sqlite_avg(values)
        self.assertEqual(result, 0)

    def test_some_none(self):
        """Test None value handling."""
        values = [None, 3, 9]  # SQLite AVG skips NULL values.

        result = self.sqlite3_aggregate('AVG', values)
        self.assertEqual(result, 6.0)

        result = _sqlite_avg(values)
        self.assertEqual(result, 6.0)

    def test_none_or_emptystring(self):
        """Test all None or empty string handling."""
        values = [None, None, '']

        result = self.sqlite3_aggregate('AVG', values)
        self.assertEqual(result, 0)

        result = _sqlite_avg(values)
        self.assertEqual(result, 0)

    def test_all_none(self):
        """Test all None handling."""
        values = [None, None, None]

        result = self.sqlite3_aggregate('AVG', values)
        self.assertEqual(result, None)

        result = _sqlite_avg(values)
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


class TestSqliteMaxAndMin(unittest.TestCase):
    """Should match SQLite MAX() and MIN() aggregation behavior.

    See SQLite docs for full details:

        https://www.sqlite.org/lang_aggfunc.html
    """
    def test_max(self):
        result = _sqlite_max([None, 10, 20, 30])
        self.assertEqual(result, 30)

        result = _sqlite_max([None, 10, '20', 30])
        self.assertEqual(result, '20')

        blob_10 = sqlite3.Binary(b'10')
        result = _sqlite_max([None, blob_10, '20', 30])
        self.assertEqual(result, blob_10)

    def test_max_null_handling(self):
        """Should return None if and only if there are non-None values
        in the group.
        """
        result = _sqlite_max([None, None])
        self.assertEqual(result, None)

        result = _sqlite_max([])
        self.assertEqual(result, None)

    def test_min(self):
        blob_30 = sqlite3.Binary(b'30')
        blob_20 = sqlite3.Binary(b'20')
        blob_10 = sqlite3.Binary(b'10')
        blob_empty = sqlite3.Binary(b'')

        result = _sqlite_min([blob_30, blob_20, blob_10, blob_empty])
        self.assertEqual(result, blob_empty)

        result = _sqlite_min([blob_30, blob_20, '10', blob_empty])
        self.assertEqual(result, '10')

        result = _sqlite_min([blob_30, 20, '10', blob_empty])
        self.assertEqual(result, 20)

    def test_min_null_handling(self):
        """The minimum value is the first non-None value that would
        appear in when sorted in _sqlite_sortkey() order.

        Should return None if and only if there are non-None values
        in the group.
        """
        result = _sqlite_min([None, 20, '10', sqlite3.Binary(b'')])
        self.assertEqual(result, 20)  # Since 20 is non-None, it is returned.

        result = _sqlite_min([None, None, None, None])
        self.assertEqual(result, None)


class TestDataResult(unittest.TestCase):
    def test_type(self):
        result = DataResult([('a', 1), ('b', 2), ('c', 3)], dict)
        self.assertIsInstance(result, Iterator)
        self.assertIsInstance(result.eval(), dict)

    def test_eval_to_list(self):
        result = DataResult([1, 2, 3], evaluates_to=list)
        self.assertEqual(result.eval(), [1, 2, 3])

    def test_eval_to_set(self):
        result = DataResult([1, 2, 3], evaluates_to=set)
        self.assertEqual(result.eval(), set([1, 2, 3]))

    def test_eval_to_dict(self):
        items = DataResult(
            [
                ('a', DataResult([1, 2, 3], evaluates_to=list)),
                ('b', DataResult([2, 4, 6], evaluates_to=list)),
                ('c', DataResult([3, 6, 9], evaluates_to=list)),
            ],
            evaluates_to=dict
        )
        expected = {
            'a': [1, 2, 3],
            'b': [2, 4, 6],
            'c': [3, 6, 9],
        }
        self.assertEqual(items.eval(), expected)

    def test_map(self):
        items = DataResult([('a', 1), ('b', 2), ('c', 3)], evaluates_to=dict)
        items = items.map(lambda x: x * 2)
        self.assertEqual(dict(items), {'a': 2, 'b': 4, 'c': 6})

        items = DataResult(
            [
                ('a', DataResult([1, 2, 3], evaluates_to=list)),
                ('b', DataResult([2, 4, 6], evaluates_to=list)),
                ('c', DataResult([3, 6, 9], evaluates_to=list)),
            ],
            evaluates_to=dict
        )
        items = items.map(lambda x: x * 3)
        items = dict((k, list(v)) for k, v in items)

        expected = {
            'a': [3, 6, 9],
            'b': [6, 12, 18],
            'c': [9, 18, 27],
        }
        self.assertEqual(items, expected)

    def test_reduce(self):
        items = DataResult([1, 2, 3], evaluates_to=list)
        items = items.reduce(lambda x, y: x + y)
        self.assertEqual(items, 6)

        items = DataResult(
            [
                ('a', DataResult([1, 1, 1], evaluates_to=list)),
                ('b', DataResult([2, 2, 2], evaluates_to=list)),
                ('c', DataResult([3, 3, 3], evaluates_to=list)),
            ],
            evaluates_to=dict
        )
        items = items.reduce(lambda x, y: x + y)
        self.assertEqual(dict(items), {'a': 3, 'b': 6, 'c': 9})

    def test_sqlite_aggregate(self):
        items = DataResult([1, 2, 3], evaluates_to=list)
        items = items._sqlite_aggregate('sum', _sqlite_sum)
        self.assertEqual(items, 6)

        items = DataResult([('a', DataResult([1, 1, 1], evaluates_to=list)),
                            ('b', DataResult([2, 2, 2], evaluates_to=list)),
                            ('c', DataResult([3, 3, 3], evaluates_to=list))],
                           evaluates_to=dict)
        items = items._sqlite_aggregate('sum', _sqlite_sum)
        self.assertEqual(dict(items), {'a': 3, 'b': 6, 'c': 9})


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
        result = self.source._select('label1')
        self.assertIsInstance(result, DataResult)
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

        result = self.source._select('label1', 'label2')
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

        result = self.source._select({'label1': 'value'})
        expected = {
            'a': ['17', '13', '20', '15'],
            'b': ['5', '40', '25'],
        }
        self.assertEqual(result.eval(), expected)

        result = self.source._select({'label1': ('label2', 'value')})
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
        self.assertEqual(result.eval(), expected)

        result = self.source._select({('label1', 'label2'): 'value'})
        expected = {
            ('a', 'x'): ['17', '13'],
            ('a', 'y'): ['20'],
            ('a', 'z'): ['15'],
            ('b', 'z'): ['5'],
            ('b', 'y'): ['40'],
            ('b', 'x'): ['25'],
        }
        self.assertEqual(result.eval(), expected)

        result = self.source._select({('label1', 'label2'): ('label2', 'value')})
        expected = {
            ('a', 'x'): [('x', '17'), ('x', '13')],
            ('a', 'y'): [('y', '20')],
            ('a', 'z'): [('z', '15')],
            ('b', 'z'): [('z', '5')],
            ('b', 'y'): [('y', '40')],
            ('b', 'x'): [('x', '25')],
        }
        self.assertEqual(result.eval(), expected)

        msg = 'Support for nested dictionaries removed (for now).'
        regex = "{'label2': 'value'} not in DataSource"
        with self.assertRaisesRegex(LookupError, regex, msg=msg):
            self.source._select({'label1': {'label2': 'value'}})

        arg_dict = {'label1': 'value'}
        result = self.source._select(arg_dict)
        self.assertEqual(arg_dict, {'label1': 'value'}, 'should not alter arg_dict')

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
