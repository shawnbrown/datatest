# -*- coding: utf-8 -*-
import sqlite3

from ..utils.builtins import *
from ..utils import decimal
from ..dataaccess.sqltemp import TemporarySqliteTable
from ..utils.misc import _is_nscontainer

from ..compare import CompareDict
from ..compare import CompareSet

from .base import BaseSource


sqlite3.register_adapter(decimal.Decimal, float)


class SqliteBase(BaseSource):
    """Base class four SqliteSource and CsvSource (not intended to be
    instantiated directly).
    """
    def __new__(cls, *args, **kwds):
        if cls is SqliteBase:
            msg = 'cannot instantiate SqliteBase directly - make a subclass'
            raise NotImplementedError(msg)
        return super(SqliteBase, cls).__new__(cls)

    def __init__(self, connection, table):
        """Initialize self."""
        self._connection = connection
        self._table = table

    def __repr__(self):
        """Return a string representation of the data source."""
        cls_name = self.__class__.__name__
        conn_name = str(self._connection)
        tbl_name = self._table
        return '{0}({1}, table={2!r})'.format(cls_name, conn_name, tbl_name)

    def columns(self):
        """Return list of column names."""
        cursor = self._connection.cursor()
        cursor.execute('PRAGMA table_info(' + self._table + ')')
        return [x[1] for x in cursor.fetchall()]

    def __iter__(self):
        """Return iterable of dictionary rows (like csv.DictReader)."""
        cursor = self._connection.cursor()
        cursor.execute('SELECT * FROM ' + self._table)

        column_names = self.columns()
        dict_row = lambda x: dict(zip(column_names, x))
        return (dict_row(row) for row in cursor.fetchall())

    def filter_rows(self, **kwds):
        if kwds:
            cursor = self._connection.cursor()
            cursor = self._execute_query(self._table, '*', **kwds)  # <- applies filter
            column_names = self.columns()
            dict_row = lambda row: dict(zip(column_names, row))
            return (dict_row(row) for row in cursor)
        return self.__iter__()

    def distinct(self, columns, **kwds_filter):
        """Return iterable of tuples containing distinct *columns*
        values.
        """
        if not _is_nscontainer(columns):
            columns = (columns,)
        self._assert_columns_exist(columns)
        select_clause = [self._normalize_column(x) for x in columns]
        select_clause = ', '.join(select_clause)
        select_clause = 'DISTINCT ' + select_clause

        cursor = self._execute_query(self._table, select_clause, **kwds_filter)
        return CompareSet(cursor)

    def sum(self, column, keys=None, **kwds_filter):
        """Returns :class:`CompareDict` containing sums of *column*
        values grouped by *keys*.
        """
        self._assert_columns_exist(column)
        column = self._normalize_column(column)
        sql_functions = 'SUM({0})'.format(column)
        return self._sql_aggregate(sql_functions, keys, **kwds_filter)

    def count(self, column, keys=None, **kwds_filter):
        """Returns :class:`CompareDict` containing count of non-empty
        *column* values grouped by *keys*.
        """
        self._assert_columns_exist(column)
        sql_function = "SUM(CASE COALESCE({0}, '') WHEN '' THEN 0 ELSE 1 END)"
        sql_function = sql_function.format(self._normalize_column(column))
        return self._sql_aggregate(sql_function, keys, **kwds_filter)

    def _sql_aggregate(self, sql_function, keys=None, **kwds_filter):
        """Aggregates values using SQL function select--e.g.,
        'COUNT(*)', 'SUM(col1)', etc.
        """
        # TODO: _sql_aggregate has grown messy after a handful of
        # iterations look to refactor it in the future to improve
        # maintainability.
        if not _is_nscontainer(sql_function):
            sql_function = (sql_function,)

        if keys == None:
            sql_function = ', '.join(sql_function)
            cursor = self._execute_query(self._table, sql_function, **kwds_filter)
            result = cursor.fetchone()
            if len(result) == 1:
                return result[0]
            return result  # <- EXIT!

        if not _is_nscontainer(keys):
            keys = (keys,)
        group_clause = [self._normalize_column(x) for x in keys]
        group_clause = ', '.join(group_clause)

        select_clause = '{0}, {1}'.format(group_clause, ', '.join(sql_function))
        trailing_clause = 'GROUP BY ' + group_clause

        cursor = self._execute_query(self._table, select_clause, trailing_clause, **kwds_filter)
        pos = len(sql_function)
        iterable = ((row[:-pos], getvals(row)) for row in cursor)
        if pos > 1:
            # Gets values by slicing (i.e., row[-pos:]).
            iterable = ((row[:-pos], row[-pos:]) for row in cursor)
        else:
            # Gets value by index (i.e., row[-pos]).
            iterable = ((row[:-pos], row[-pos]) for row in cursor)
        return CompareDict(iterable, keys)

    def mapreduce(self, mapper, reducer, columns, keys=None, **kwds_filter):
        obj = super(SqliteBase, self)  # 2.x compatible calling convention.
        return obj.mapreduce(mapper, reducer, columns, keys, **kwds_filter)
        # SqliteBase doesn't implement its own mapreduce() optimization.
        # A generalized, SQL optimization could do little more than the
        # already-optmized filter_rows() method.  Since the super-class'
        # mapreduce() already uses filter_rows() internally, a separate
        # optimization is unnecessary.

    def _execute_query(self, table, select_clause, trailing_clause=None, **kwds_filter):
        """Execute query and return cursor object."""
        try:
            stmnt, params = self._build_query(self._table, select_clause, **kwds_filter)
            if trailing_clause:
                stmnt += '\n' + trailing_clause
            cursor = self._connection.cursor()
            cursor.execute('PRAGMA synchronous=OFF')
            #print(stmnt, params)
            cursor.execute(stmnt, params)
        except Exception as e:
            exc_cls = e.__class__
            msg = '%s\n  query: %s\n  params: %r' % (e, stmnt, params)
            raise exc_cls(msg)
        return cursor

    @classmethod
    def _build_query(cls, table, select_clause, **kwds_filter):
        """Return 'SELECT' query."""
        query = 'SELECT ' + select_clause + ' FROM ' + table
        where_clause, params = cls._build_where_clause(**kwds_filter)
        if where_clause:
            query = query + ' WHERE ' + where_clause
        return query, params

    @staticmethod
    def _build_where_clause(**kwds_filter):
        """Return 'WHERE' clause that implements *kwds_filter*
        constraints.
        """
        clause = []
        params = []
        items = kwds_filter.items()
        items = sorted(items, key=lambda x: x[0])  # Ordered by key.
        for key, val in items:
            if _is_nscontainer(val):
                clause.append(key + ' IN (%s)' % (', '.join('?' * len(val))))
                for x in val:
                    params.append(x)
            else:
                clause.append(key + '=?')
                params.append(val)

        clause = ' AND '.join(clause) if clause else ''
        return clause, params

    def create_index(self, *columns):
        """Create an index for specified columns---can speed up testing
        in some cases.

        See :meth:`SqliteSource.create_index` for more details.
        """
        self._assert_columns_exist(columns)

        # Build index name.
        whitelist = lambda col: ''.join(x for x in col if x.isalnum())
        idx_name = '_'.join(whitelist(col) for col in columns)
        idx_name = 'idx_{0}_{1}'.format(self._table, idx_name)

        # Build column names.
        col_names = [self._normalize_column(x) for x in columns]
        col_names = ', '.join(col_names)

        # Prepare statement.
        statement = 'CREATE INDEX IF NOT EXISTS {0} ON {1} ({2})'
        statement = statement.format(idx_name, self._table, col_names)

        # Create index.
        cursor = self._connection.cursor()
        cursor.execute('PRAGMA synchronous=OFF')
        cursor.execute(statement)

    @staticmethod
    def _normalize_column(column):
        """Normalize value for use as SQLite column name."""
        if not isinstance(column, str):
            msg = "expected column of type 'str', got {0!r} instead"
            raise TypeError(msg.format(column.__class__.__name__))
        column = column.strip()
        column = column.replace('"', '""')  # Escape quotes.
        if column == '':
            column = '_empty_'
        return '"' + column + '"'


class SqliteSource(SqliteBase):
    """Loads *table* data from given SQLite *connection*:
    ::

        conn = sqlite3.connect('mydatabase.sqlite3')
        subject = datatest.SqliteSource(conn, 'mytable')
    """
    @classmethod
    def from_records(cls, data, columns=None):
        """Alternate constructor to load an existing collection of
        records into a tempoarary SQLite database.  Loads *data* (an
        iterable of lists, tuples, or dicts) into a temporary table
        using the named *columns*::

            records = [
                ('a', 'x'),
                ('b', 'y'),
                ('c', 'z'),
                ...
            ]
            subject = datatest.SqliteSource.from_records(records, ['col1', 'col2'])

        The *columns* argument can be omitted if *data* is a collection
        of dictionary or namedtuple records::

            dict_rows = [
                {'col1': 'a', 'col2': 'x'},
                {'col1': 'b', 'col2': 'y'},
                {'col1': 'c', 'col2': 'z'},
                ...
            ]
            subject = datatest.SqliteSource.from_records(dict_rows)
        """
        temptable = TemporarySqliteTable(data, columns)
        return cls(temptable.connection, temptable.name)

    def create_index(self, *columns):
        """Create an index for specified columns---can speed up testing
        in some cases.

        Indexes should be added one-by-one to tune a test suite's
        over-all performance.  Creating several indexes before testing
        even begins could lead to worse performance so use them with
        discretion.

        An example:  If you're using "town" to group aggregation tests
        (like ``self.assertSubjectSum('population', ['town'])``), then
        you might be able to improve performance by adding an index for
        the "town" column::

            subject.create_index('town')

        Using two or more columns creates a multi-column index::

            subject.create_index('town', 'zipcode')

        Calling the function multiple times will create multiple
        indexes::

            subject.create_index('town')
            subject.create_index('zipcode')
        """
        # Calling super() with older convention to support Python 2.7 & 2.6.
        super(SqliteSource, self).create_index(*columns)
