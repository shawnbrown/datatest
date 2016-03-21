# -*- coding: utf-8 -*-
import functools
import inspect
import os
import sqlite3
import sys
import warnings

from ._builtins import *
from ._collections import Counter
from ._collections import Iterable
from ._decimal import Decimal
from ._unicodecsvreader import UnicodeCsvReader as _UnicodeCsvReader
from . import _itertools as itertools

from .sourceresult import ResultMapping
from .sourceresult import ResultSet
from .sourceresult import _is_nscontainer

#pattern = 'test*.py'
prefix = 'test_'

sqlite3.register_adapter(Decimal, str)


class BaseSource(object):
    """Common base class for all data sources.  Custom sources can be
    created by subclassing BaseSource and implementing ``__init__()``,
    ``__repr__()``, ``__iter__()``, and ``columns()``.  Optionally,
    performance can be improved by implementing ``distinct()``,
    ``sum()``, ``count()``, and ``reduce()``.

    """

    def __init__(self):
        """NotImplemented

        Initialize self.
        """
        return NotImplemented

    def __repr__(self):
        """NotImplemented

        Return a string representation of the data source.
        """
        return NotImplemented

    def __iter__(self):
        """NotImplemented

        Return an iterable of dictionary rows (like ``csv.DictReader``).
        """
        return NotImplemented

    def columns(self):
        """NotImplemented

        Return list of column names.
        """
        return NotImplemented

    def distinct(self, column, **filter_by):
        """Return iterable of tuples containing distinct *column*
        values (uses slow ``__iter__``).
        """
        if not _is_nscontainer(column):
            column = (column,)
        self._assert_columns_exist(column)
        iterable = self.__filter_by(**filter_by)  # Filtered rows only.
        iterable = (tuple(row[c] for c in column) for row in iterable)
        return ResultSet(iterable)

    def sum(self, column, keys=None, **filter_by):
        """Returns sum of *column* grouped by *keys* as ResultMapping
        (uses ``reduce`` method).
        """
        func = lambda x, y: (x + Decimal(y)) if y else x
        init = Decimal(0)
        return self.reduce(func, column, keys, init, **filter_by)

    def count(self, keys=None, **filter_by):
        """Returns count of *column* grouped by *keys* as ResultMapping
        (uses ``reduce`` method).
        """
        func = lambda x, y: x + y
        column = lambda row: 1  # Column mapped to int value 1.
        init = 0
        return self.reduce(func, column, keys, init, **filter_by)

    def reduce(self, function, column, keys=None, initializer=None, **filter_by):
        """Apply *function* of two arguments cumulatively to the values
        in *column*, from left to right, so as to reduce the iterable
        to a single value (uses slow ``__iter__``).  If *column* is a
        string, the values are passed to *function* unchanged.  But if
        *column* is, itself, a function, it should accept a single
        dict-row and return a single value.  If *keys* is omitted, the
        raw result is returned, otherwise returns a ResultMapping
        object.
        """
        if not callable(column):
            self._assert_columns_exist(column)
            get_value = lambda row: row[column]
        else:
            get_value = column

        iterable = self.__filter_by(**filter_by)  # Uses slow __iter__().

        if not keys:
            vals = (get_value(row) for row in iterable)
            return functools.reduce(function, vals, initializer)  # <- EXIT!

        if not _is_nscontainer(keys):
            keys = (keys,)
        self._assert_columns_exist(keys)

        result = {}                                # Do not remove this loop
        for row in iterable:                       # without a good reason!
            key = tuple(row[x] for x in keys)      # Accumulating with a dict
            x = result.get(key, initializer)       # is more memory efficient
            y = get_value(row)                     # than using sorted() plus
            result[key] = function(x, y)           # itertools.groupby() plus
                                                   # functools.reduce().
        return ResultMapping(result, keys)

    def __filter_by(self, **filter_by):
        """Filter data by keywords, returns iterable.  E.g., where
        column1=value1, column2=value2, etc. (uses slow ``__iter__``).
        """
        mktup = lambda v: (v,) if not _is_nscontainer(v) else v
        filter_by = dict((k, mktup(v)) for k, v in filter_by.items())
        for row in self.__iter__():
            if all(row[k] in v for k, v in filter_by.items()):
                yield row

    def _assert_columns_exist(self, columns):
        """Asserts that given columns are present in data source,
        raises LookupError if columns are missing.
        """
        if not _is_nscontainer(columns):
            columns = (columns,)
        self_cols = self.columns()
        is_missing = lambda col: col not in self_cols
        missing = [c for c in columns if is_missing(c)]
        if missing:
            missing = ', '.join(repr(x) for x in missing)
            msg = '{0} not in {1}'.format(missing, self.__repr__())
            raise LookupError(msg)


# Custom data source template example:
#
#    class MyCustomSource(SqliteSource)
#        def __init__(self, customsource):
#            ...prepare data and columns from customsource...
#            temptable = _TemporarySqliteTable(data, columns)
#            self._tempsqlite = temptable
#            SqliteSource.__init__(self, temptable.connection, temptable.name)


class _TemporarySqliteTable(object):
    """Creates a temporary SQLite table and inserts given data."""
    __shared_connection = sqlite3.connect('')  # Default connection shared by instances.

    def __init__(self, data, columns=None, connection=None):
        """Initialize self."""
        if not columns:
            data = iter(data)
            first_row = next(data)
            if hasattr(first_row, 'keys'):  # Dict-like rows.
                columns = first_row.keys()
                columns = tuple(sorted(columns))
            elif hasattr(first_row, '_fields'):  # Namedtuple-like rows.
                columns = first_row._fields
            else:
                msg = ('columns argument can only be omitted if data '
                       'contains dict-rows or namedtuple-rows')
                raise TypeError(msg)
            data = itertools.chain([first_row], data)  # Rebuild original.

        if not connection:
            connection = self.__shared_connection

        # Create table and load data.
        _isolation_level = connection.isolation_level  # <- Isolation_level gets
        connection.isolation_level = None              #    None for transactions.
        cursor = connection.cursor()
        cursor.execute('PRAGMA synchronous=OFF')  # For faster loading.
        cursor.execute('BEGIN TRANSACTION')
        try:
            existing_tables = self._get_existing_tables(cursor)
            table = self._make_new_table(existing_tables)
            statement = self._create_table_statement(table, columns)
            cursor.execute(statement)
            self._insert_data(cursor, table, data, columns)
            connection.commit()  # COMMIT TRANSACTION

        except Exception as e:
            connection.rollback()  # ROLLBACK TRANSACTION
            if isinstance(e, UnicodeDecodeError):
                e.reason += '\n{0}'.format(statement)
                raise e
            raise e.__class__('{0}\n{1}'.format(e, statement))

        finally:
            # Restore original connection attributes.
            connection.isolation_level = _isolation_level
            cursor.execute('PRAGMA synchronous=ON')

            # Assign class properties.
            self._connection = connection
            self._name = table
            self._columns = columns

    @property
    def connection(self):
        """Database connection in which temporary table exists."""
        return self._connection

    @property
    def name(self):
        """Name of temporary table."""
        return self._name

    @property
    def columns(self):
        """Column names used in temporary table."""
        return self._columns

    def drop(self):
        """Drops temporary table from database."""
        cursor = self.connection.cursor()
        cursor.execute('DROP TABLE IF EXISTS ' + self.name)

    @staticmethod
    def _get_existing_tables(cursor):
        """Takes sqlite3 *cursor*, returns existing temporary table names."""
        #cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        cursor.execute("SELECT name FROM sqlite_temp_master WHERE type='table'")
        return [x[0] for x in cursor]

    @staticmethod
    def _make_new_table(existing):
        """Takes a list of *existing* table names and returns a new, unique
        table name (tbl0, tbl1, tbl2, etc.)."""
        prefix = 'tbl'
        numbers = [x[len(prefix):] for x in existing if x.startswith(prefix)]
        numbers = [int(x) for x in numbers if x.isdigit()]
        if numbers:
            table_num = max(numbers) + 1
        else:
            table_num = 0
        return prefix + str(table_num)

    @classmethod
    def _create_table_statement(cls, table, columns):
        """Return 'CREATE TEMPORARY TABLE' statement."""
        cls._assert_unique(columns)
        columns = [cls._normalize_column(x) for x in columns]
        #return 'CREATE TABLE %s (%s)' % (table, ', '.join(columns))
        return 'CREATE TEMPORARY TABLE %s (%s)' % (table, ', '.join(columns))

    @classmethod
    def _insert_data(cls, cursor, table, data, columns):
        for row in data:  # Insert all rows.
            if isinstance(row, dict):
                row = tuple(row[x] for x in columns)
            statement, params = cls._insert_into_statement(table, row)
            try:
                cursor.execute(statement, params)
                #TODO!!!: Look at using execute_many() for faster loading.
            except Exception as e:
                exc_cls = e.__class__
                msg = ('\n'
                       '    row -> %s\n'
                       '    sql -> %s\n'
                       ' params -> %s') % (row, statement, params)
                msg = str(e).strip() + msg
                raise exc_cls(msg)

    @staticmethod
    def _insert_into_statement(table, row):
        """Return 'INSERT INTO' statement."""
        assert not isinstance(row, str), "row must be non-string container"
        statement = 'INSERT INTO ' + table + ' VALUES (' + ', '.join(['?'] * len(row)) + ')'
        parameters = row
        return statement, parameters

    @staticmethod
    def _normalize_column(name):
        """Normalize value for use as SQLite column name."""
        name = name.strip()
        name = name.replace('"', '""')  # Escape quotes.
        if name == '':
            name = '_empty_'
        return '"' + name + '"'

    @staticmethod
    def _assert_unique(lst):
        """Asserts that list of items is unique, raises Exception if
        not.
        """
        values = []
        duplicates = []
        for x in lst:
            if x in values:
                if x not in duplicates:
                    duplicates.append(x)
            else:
                values.append(x)

        if duplicates:
            raise ValueError('Duplicate values: ' + ', '.join(duplicates))


# TODO!!!: Explore the idea of formalizing __filter_by functionality.


class _SqliteSource(BaseSource):
    """Base class four SqliteSource and CsvSource (not intended to be
    instantiated directly.)

    """
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

    def __iter__(self):
        """Return iterable of dictionary rows (like csv.DictReader)."""
        cursor = self._connection.cursor()
        cursor.execute('SELECT * FROM ' + self._table)
        column_names = self.columns()
        mkdict = lambda x: dict(zip(column_names, x))
        return (mkdict(row) for row in cursor.fetchall())

    def columns(self):
        """Return list of column names."""
        cursor = self._connection.cursor()
        cursor.execute('PRAGMA table_info(' + self._table + ')')
        return [x[1] for x in cursor.fetchall()]

    def distinct(self, column, **filter_by):
        """Return iterable of tuples containing distinct *column*
        values.
        """
        if not _is_nscontainer(column):
            column = (column,)
        self._assert_columns_exist(column)
        select_clause = [self._normalize_column(x) for x in column]
        select_clause = ', '.join(select_clause)
        select_clause = 'DISTINCT ' + select_clause

        cursor = self._execute_query(self._table, select_clause, **filter_by)
        return ResultSet(cursor)

    def sum(self, column, keys=None, **filter_by):
        """Returns sum of *column* grouped by *keys* as
        ResultMapping.
        """
        self._assert_columns_exist(column)
        column = self._normalize_column(column)
        sql_function = 'SUM({0})'.format(column)
        return self._sql_aggregate(sql_function, keys, **filter_by)

    def count(self, keys=None, **filter_by):
        """Returns count of *column* grouped by *keys* as
        ResultMapping.
        """
        return self._sql_aggregate('COUNT(*)', keys, **filter_by)

    def _sql_aggregate(self, sql_function, keys=None, **filter_by):
        """Aggregates values using SQL function select--e.g.,
        'COUNT(*)', 'SUM(col1)', etc.
        """
        if keys == None:
            cursor = self._execute_query(self._table, sql_function, **filter_by)
            return cursor.fetchone()[0]  # <- EXIT!

        if not _is_nscontainer(keys):
            keys = (keys,)
        group_clause = [self._normalize_column(x) for x in keys]
        group_clause = ', '.join(group_clause)

        select_clause = '{0}, {1}'.format(group_clause, sql_function)
        trailing_clause = 'GROUP BY ' + group_clause

        cursor = self._execute_query(self._table, select_clause, trailing_clause, **filter_by)
        iterable = ((row[:-1], row[-1]) for row in cursor)
        return ResultMapping(iterable, keys)

    def reduce(self, function, column, keys=None, initializer=None, **filter_by):
        """Apply *function* of two arguments cumulatively to the values
        in *column*, from left to right, so as to reduce the iterable
        to a single value.  If *column* is a string, the values are
        passed to *function* unchanged.  But if *column* is, itself, a
        function, it should accept a single dict-row and return a
        single value.  If *keys* is omitted, the raw result is
        returned, otherwise returns a ResultMapping object.
        """
        if not callable(column):
            self._assert_columns_exist(column)
            get_values = lambda itrbl: (row[column] for row in itrbl)
        else:
            get_values = lambda itrbl: (column(row) for row in itrbl)
        apply = lambda cur: functools.reduce(function, get_values(cur), initializer)

        val_keys = self.columns()
        dict_rows = lambda itrbl: (dict(zip(val_keys, vals)) for vals in itrbl)

        if keys:
            if not _is_nscontainer(keys):
                keys = (keys,)
            self._assert_columns_exist(keys)

            order_by = tuple(self._normalize_column(x) for x in keys)
            order_by = ', '.join(order_by)
            order_by = 'ORDER BY {0}'.format(order_by)
            cursor = self._execute_query(self._table, '*', order_by, **filter_by)
            cursor = dict_rows(cursor)

            keyfn = lambda row: tuple(row[key] for key in keys)
            grouped = itertools.groupby(cursor, key=keyfn)
            result = ((key, apply(vals)) for key, vals in grouped)
            result = ResultMapping(result, keys)

            # TODO: Check to see which is faster with lots of groups.
            #result = {}
            #groups = self.distinct(keys, **filter_by)
            #for group in groups:
            #    subfilter_by = dict(zip(keys, group))
            #    subfilter_by.update(filter_by)
            #    cursor = self._execute_query(self._table, '*', **subfilter_by)
            #    cursor = dict_rows(cursor)
            #    result[group] = apply(cursor)
            #    result = ResultMapping(result, keys)
        else:
            cursor = self._execute_query(self._table, '*', **filter_by)
            cursor = dict_rows(cursor)
            result = apply(cursor)
        return result

    def _execute_query(self, table, select_clause, trailing_clause=None, **filter_by):
        """Execute query and return cursor object."""
        try:
            stmnt, params = self._build_query(self._table, select_clause, **filter_by)
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
    def _build_query(cls, table, select_clause, **filter_by):
        """Return 'SELECT' query."""
        query = 'SELECT ' + select_clause + ' FROM ' + table
        where_clause, params = cls._build_where_clause(**filter_by)
        if where_clause:
            query = query + ' WHERE ' + where_clause
        return query, params

    @staticmethod
    def _build_where_clause(**filter_by):
        """Return 'WHERE' clause that implements *filter_by*
        constraints.
        """
        clause = []
        params = []
        items = filter_by.items()
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
        """Creating an index for certain columns can speed up data
        testing in some cases.

        See :meth:`SqliteSource.create_index
        <datatest.SqliteSource.create_index>` for more details.
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
    def _normalize_column(name):
        """Normalize value for use as SQLite column name."""
        name = name.strip()
        name = name.replace('"', '""')  # Escape quotes.
        if name == '':
            name = '_empty_'
        return '"' + name + '"'


class SqliteSource(_SqliteSource):
    """Loads *table* data from given SQLite *connection*:
    ::

        conn = sqlite3.connect('mydatabase.sqlite3')
        subjectData = datatest.SqliteSource(conn, 'mytable')

    """
    @classmethod
    def from_records(cls, data, columns=None):
        """Alternate constructor to load an existing collection of
        records.  Loads *data* (an iterable of lists, tuples, or dicts)
        into a new SQLite database with the given *columns*::

            subjectData = datatest.SqliteSource.from_records(records, columns)

        The *columns* argument can be omitted if *data* contains
        ``dict`` or ``namedtuple`` records::

            dict_rows = [
                { ... },
                { ... },
            ]
            subjectData = datatest.SqliteSource.from_records(dict_rows)

        """
        temptable = _TemporarySqliteTable(data, columns)
        return cls(temptable.connection, temptable.name)

    def create_index(self, *columns):
        """Creating an index for certain columns can speed up data
        testing in some cases.

        Indexes should be added one-by-one to tune a test suite's
        over-all performance.  Creating several indexes before testing
        even begins could lead to worse performance so use them with
        discretion.

        For example:  If you're using "town" to group aggregation
        tests (like ``self.assertDataSum('population', ['town'])``),
        then you might be able to improve performance by adding an
        index for the "town" column::

            subjectData.create_index('town')

        Using two or more columns creates a multi-column index::

            subjectData.create_index('town', 'zipcode')

        Calling the function multiple times will create multiple
        indexes::

            subjectData.create_index('town')
            subjectData.create_index('zipcode')

        """
        # Calling super() with older convention to support Python 2.7 & 2.6.
        super(self.__class__, self).create_index(*columns)


class CsvSource(_SqliteSource):
    """Loads CSV data from *file* (path or file-like object):
    ::

        subjectData = datatest.CsvSource('mydata.csv')

    """
    def __init__(self, file, encoding=None, in_memory=False):
        """Initialize self."""
        self._file_repr = repr(file)

        # If *file* is relative path, uses directory of calling file as base.
        if isinstance(file, str) and not os.path.isabs(file):
            calling_frame = sys._getframe(1)
            calling_file = inspect.getfile(calling_frame)
            base_path = os.path.dirname(calling_file)
            file = os.path.join(base_path, file)
            file = os.path.normpath(file)

        # Create temporary SQLite table object.
        if encoding:
            with _UnicodeCsvReader(file, encoding=encoding) as reader:
                columns = next(reader)  # Header row.
                temptable = _TemporarySqliteTable(reader, columns)
        else:
            try:
                with _UnicodeCsvReader(file, encoding='utf-8') as reader:
                    columns = next(reader)  # Header row.
                    temptable = _TemporarySqliteTable(reader, columns)

            except UnicodeDecodeError:
                with _UnicodeCsvReader(file, encoding='iso8859-1') as reader:
                    columns = next(reader)  # Header row.
                    temptable = _TemporarySqliteTable(reader, columns)

                # Prepare message and raise as warning.
                try:
                    filename = os.path.basename(file)
                except AttributeError:
                    filename = repr(file)
                msg = ('\nData in file {0!r} does not appear to be encoded '
                       'as UTF-8 (used ISO-8859-1 as fallback). To assure '
                       'correct operation, please specify a text encoding.')
                warnings.warn(msg.format(filename))

        # Calling super() with older convention to support Python 2.7 & 2.6.
        super(self.__class__, self).__init__(temptable.connection, temptable.name)

    def __repr__(self):
        """Return a string representation of the data source."""
        cls_name = self.__class__.__name__
        src_file = self._file_repr
        return '{0}({1})'.format(cls_name, src_file)


class MultiSource(BaseSource):
    """A wrapper class that allows multiple data sources to be treated
    as a single, composite data source::

        subjectData = datatest.MultiSource(
            datatest.CsvSource('file1.csv'),
            datatest.CsvSource('file2.csv'),
            datatest.CsvSource('file3.csv')
        )

    The original sources are stored in the ``__wrapped__`` attribute.

    """

    def __init__(self, *sources):
        """Initialize self."""
        for source in sources:
            msg = 'Sources must be derived from BaseSource'
            assert isinstance(source, BaseSource), msg
        self.__wrapped__ = sources

    def __repr__(self):
        """Return a string representation of the data source."""
        cls_name = self.__class__.__name__
        src_names = [repr(src) for src in self.__wrapped__]  # Get reprs.
        src_names = ['    ' + src for src in src_names]      # Prefix with 4 spaces.
        src_names = ',\n'.join(src_names)                    # Join w/ comma & new-line.
        return '{0}(\n{1}\n)'.format(cls_name, src_names)

    def __iter__(self):
        """Return iterable of dictionary rows (like csv.DictReader)."""
        columns = self.columns()
        for source in self.__wrapped__:
            for row in source.__iter__():
                yield dict((col, row.get(col, '')) for col in columns)

    def columns(self):
        """Return list of column names."""
        all_columns = []
        for source in self.__wrapped__:
            for c in source.columns():
                if c not in all_columns:
                    all_columns.append(c)
        return all_columns

    @staticmethod
    def _filtered_call(source, method, *column, **filter_by):
        subcols = source.columns()
        column = [x for x in column if x in subcols]
        if any(v != '' for k, v in filter_by.items() if k not in subcols):
            return None  # <- EXIT!
        sub_filter = dict((k, v) for k, v in filter_by.items() if k in subcols)
        fn = getattr(source, method)
        return fn(*column, **sub_filter)

    def distinct(self, column, **filter_by):
        """Return iterable of tuples containing distinct *column*
        values.
        """
        if not _is_nscontainer(column):
            column = (column,)

        self._assert_columns_exist(column)  # Must be in at least one sub-source.

        results = []
        for subsrc in self.__wrapped__:
            subsrc_columns = subsrc.columns()
            subfltr = self._make_sub_filter(subsrc_columns, **filter_by)
            if subfltr is not None:
                subcol = [x for x in column if x in subsrc_columns]
                if subcol:
                    subres = subsrc.distinct(subcol, **subfltr)
                    subres = self._normalize_result(subres, subcol, column)
                    results.append(subres)
                else:
                    if subfltr != {}:
                        tst = subsrc.distinct(subfltr.keys(), **subfltr)
                        if tst:
                            empty_row = ('',) * len(column)
                            subres = ResultSet([empty_row])
                            results.append(subres)
                    else:
                        # If subsrc contains at least 1 item, then
                        # add an empty row to the result list.  If
                        # subsrc is completely empty, then don't add
                        # anything.
                        iterable = iter(subsrc)
                        try:
                            next(iterable)
                            subres = ResultSet([tuple(['']) * len(column)])
                            results.append(subres)
                        except StopIteration:
                            pass

        results = itertools.chain(*results)
        return ResultSet(results)

    def sum(self, column, keys=None, **filter_by):
        """Return sum of values in *column* grouped by *keys*."""
        self._assert_columns_exist(column)

        if keys is None:
            total = 0
            for subsrc in self.__wrapped__:
                subsrc_columns = subsrc.columns()
                if column in subsrc_columns:
                    subfltr = self._make_sub_filter(subsrc_columns, **filter_by)
                    if subfltr is not None:
                        total = total + subsrc.sum(column, **subfltr)
            return total
        else:
            if not _is_nscontainer(keys):
                keys = (keys,)

            counter = Counter()
            for subsrc in self.__wrapped__:
                subsrc_columns = subsrc.columns()
                if column in subsrc_columns:
                    subfltr = self._make_sub_filter(subsrc_columns, **filter_by)
                    if subfltr is not None:
                        subgrp = [x for x in keys if x in subsrc_columns]
                        subres = subsrc.sum(column, subgrp, **subfltr)
                        subres = self._normalize_result(subres, subgrp, keys)
                        for k, v in subres.items():
                            counter[k] += v
            return ResultMapping(counter, keys)

    def reduce(self, function, column, keys=None, initializer=None, **filter_by):
        """Apply *function* of two arguments cumulatively to the values
        in *column*, from left to right, so as to reduce the iterable
        to a single value.  If *column* is a string, the values are
        passed to *function* unchanged.  But if *column* is, itself, a
        function, it should accept a single dict-row and return a
        single value.  If *keys* is omitted, the raw result is
        returned, otherwise returns a ResultMapping object.
        """
        if not callable(column):
            self._assert_columns_exist(column)

        if keys is None:
            results = []
            for subsrc in self.__wrapped__:
                subsrc_columns = subsrc.columns()
                subfltr = self._make_sub_filter(subsrc_columns, **filter_by)
                if subfltr is not None:
                    try:
                        result = subsrc.reduce(function, column, keys, initializer, **filter_by)
                        results.append(result)
                    except LookupError:
                        pass
            return functools.reduce(function, results, initializer)
        else:
            if not _is_nscontainer(keys):
                keys = (keys,)
            self._assert_columns_exist(keys)
            results = {}
            for subsrc in self.__wrapped__:
                subsrc_columns = subsrc.columns()
                subfltr = self._make_sub_filter(subsrc_columns, **filter_by)
                if subfltr is not None:
                    try:
                        subgrp = [x for x in keys if x in subsrc_columns]
                        subres = subsrc.reduce(function, column, subgrp, initializer, **subfltr)
                        subres = self._normalize_result(subres, subgrp, keys)
                        for key, y in subres.items():
                            x = results.get(key, initializer)
                            results[key] = function(x, y)
                    except LookupError:
                        pass
            return ResultMapping(results, keys)

    @staticmethod
    def _make_sub_filter(columns, **filter_by):
        """."""
        subcols = columns
        missing = [k for k in filter_by if k not in subcols]
        if any(filter_by[k] != '' for k in missing):
            return None  # <- EXIT!
        subfltr = dict((k, v) for k, v in filter_by.items() if k in subcols)
        return subfltr

    @staticmethod
    def _normalize_result(result_obj, orig_cols, targ_cols):
        """."""
        if list(orig_cols) == list(targ_cols):
            return result_obj  # If columns are same, return result unchanged.

        if not _is_nscontainer(orig_cols):
            orig_cols = (orig_cols,)

        if not all(x in targ_cols for x in orig_cols):
            raise ValueError('Target columns must include all original columns.')

        def normalize(orig):
            orig_dict = dict(zip(orig_cols, orig))
            return tuple(orig_dict.get(col, '') for col in targ_cols)

        if isinstance(result_obj, ResultSet):
            normalized = ResultSet(normalize(v) for v in result_obj)
        elif isinstance(result_obj, ResultMapping):
            item_gen = ((normalize(k), v) for k, v in result_obj.items())
            normalized = ResultMapping(item_gen, key_names=targ_cols)
        else:
            raise ValueError('Result object must be ResultSet or ResultMapping.')

        return normalized


#DefaultDataSource = CsvSource
