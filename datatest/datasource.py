# -*- coding: utf-8 -*-
import collections
import inspect
import os
import sqlite3
import sys
import warnings
from decimal import Decimal

from datatest._builtins import *
from datatest._unicodecsvreader import UnicodeCsvReader as _UnicodeCsvReader
import datatest._itertools as itertools

#pattern = 'test*.py'
prefix = 'test_'


class BaseDataSource(object):
    """Common base class for all data sources.  Custom sources can be
    created by subclassing BaseDataSource and implementing
    ``__init__()``, ``__repr__()``, ``columns()``, and ``slow_iter()``.
    Optionally, performance can be improved by implementing ``sum()``,
    ``count()``, and ``unique()``.

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

    def columns(self):
        """NotImplemented

        Return a sequence (e.g. a list) of column names.
        """
        return NotImplemented

    def slow_iter(self):
        """NotImplemented

        Return an iterable of dictionary rows (like ``csv.DictReader``).
        """
        return NotImplemented

    def sum(self, column, **filter_by):
        """Return sum of values in *column* (uses ``slow_iter``)."""
        iterable = self._base_filter_by(self.slow_iter(), **filter_by)
        iterable = (x for x in iterable if x)
        return sum(Decimal(x[column]) for x in iterable)

    def count(self, **filter_by):
        """Return count of rows (uses ``slow_iter``)"""
        iterable = self._base_filter_by(self.slow_iter(), **filter_by)
        return sum(1 for x in iterable)

    def unique(self, *column, **filter_by):
        """Return iterable of tuples containing unique *column* values
        (uses ``slow_iter``).
        """
        iterable = self._base_filter_by(self.slow_iter(), **filter_by)  # Filtered rows only.
        fn = lambda row: tuple(row[x] for x in column)
        iterable = (fn(row) for row in iterable)
        seen = set()  # Using "unique_everseen" recipe from itertools.
        seen_add = seen.add
        for element in itertools.filterfalse(seen.__contains__, iterable):
            seen_add(element)
            yield element

    def set(self, column, **filter_by):
        """Convenience function for unwrapping single column results
        from ``unique()`` and returning as a set."""
        return set(x[0] for x in self.unique(column, **filter_by))

    @staticmethod
    def _base_filter_by(iterable, **filter_by):
        """Filter iterable by keywords (column=value, etc.)."""
        mktup = lambda v: (v,) if not isinstance(v, (list, tuple)) else v
        filter_by = dict((k, mktup(v)) for k, v in filter_by.items())
        for row in iterable:
            if all(row[k] in v for k, v in filter_by.items()):
                yield row


class SqliteDataSource(BaseDataSource):
    """Loads *table* data from given SQLite *connection*:
    ::

        conn = sqlite3.connect('mydatabase.sqlite3')
        subjectData = datatest.SqliteDataSource(conn, 'mytable')

    """

    def __init__(self, connection, table):
        """Initialize self."""
        self.__name__ = 'SQLite Table {0!r}'.format(table)
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

    def slow_iter(self):
        """Return iterable of dictionary rows (like csv.DictReader)."""
        cursor = self._connection.cursor()
        cursor.execute('PRAGMA synchronous=OFF')
        cursor.execute('SELECT * FROM ' + self._table)
        column_names = self.columns()
        mkdict = lambda x: dict(zip(column_names, x))
        return (mkdict(row) for row in cursor.fetchall())

    def sum(self, column, **filter_by):
        """Return sum of values in column."""
        select_clause = 'SUM("' + column + '")'
        cursor = self._execute_query(self._table, select_clause, **filter_by)
        return cursor.fetchone()[0]

    def count(self, **filter_by):
        """Return count of rows."""
        cursor = self._execute_query(self._table, 'COUNT(*)', **filter_by)
        return cursor.fetchone()[0]

    def unique(self, *column, **filter_by):
        """Return iterable of tuples of unique column values."""
        all_cols = self.columns()
        not_found = [x for x in column if x not in all_cols]
        if not_found:
            raise KeyError(not_found[0])

        select_clause = ['"{0}"'.format(x) for x in column]
        select_clause = ', '.join(select_clause)
        select_clause = 'DISTINCT {0}'.format(select_clause)
        cursor = self._execute_query(self._table, select_clause, **filter_by)
        return (x for x in cursor)

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
        """Return 'WHERE' clause that implements *filter_by* constraints."""
        clause = []
        params = []
        items = filter_by.items()
        items = sorted(items, key=lambda x: x[0])  # Ordered by key.
        for key, val in items:
            if hasattr(val, '__iter__') and not isinstance(val, str):
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
        testing in many cases.

        Indexes should be added one-be-one to tune a test suite's
        over-all performance.  Creating several indexes before testing
        even begins could lead to worse performance so use them with
        discretion.

        For example:  If you're using "town" to group aggregation
        tests (like ``self.assertValueSum('population', ['town'])``),
        then you might be able to improve performance by adding an index
        for the "town" column::

            subjectData.create_index('town')

        Using two or more columns creates a multi-column index::

            subjectData.create_index('town', 'zipcode')

        Calling the function multiple times will create multiple indexes::

            subjectData.create_index('town')
            subjectData.create_index('zipcode')

        """
        # Build index name.
        whitelist = lambda col: ''.join(x for x in col if x.isalnum())
        idx_name = '_'.join(whitelist(col) for col in columns)
        idx_name = 'idx_{0}_{1}'.format(self._table, idx_name)

        # Build column names.
        col_names = [self._from_records_normalize_column(x) for x in columns]
        col_names = ', '.join(col_names)

        # Prepare statement.
        statement = 'CREATE INDEX IF NOT EXISTS {0} ON {1} ({2})'
        statement = statement.format(idx_name, self._table, col_names)

        # Create index.
        cursor = self._connection.cursor()
        cursor.execute('PRAGMA synchronous=OFF')
        cursor.execute(statement)

    @classmethod
    def from_source(cls, source, in_memory=False):
        """Alternate constructor to load an existing data source:
        ::

            subjectData = datatest.SqliteDataSource.from_source(source)

        """
        data = source.slow_iter()
        columns = source.columns()
        return cls.from_records(data, columns, in_memory)

    @classmethod
    def from_records(cls, data, columns, in_memory=False):
        """Alternate constructor to load an existing collection of
        records.  Loads *data* (an iterable of lists, tuples, or dicts)
        into a new SQLite database with the given *columns*::

            subjectData = datatest.SqliteDataSource.from_records(records, columns)

        """
        # Create database (an empty string denotes use of a temp file).
        sqlite_path = ':memory:' if in_memory else ''
        connection = sqlite3.connect(sqlite_path)

        # Set isolation_level to None for proper transaction handling.
        _isolation_level = connection.isolation_level
        connection.isolation_level = None

        cursor = connection.cursor()
        cursor.execute('PRAGMA synchronous=OFF')  # For faster loading.
        cursor.execute('BEGIN TRANSACTION')
        try:
            table = 'main'
            statement = cls._from_records_build_create_statement(table, columns)
            cursor.execute(statement)

            for row in data:  # Insert all rows.
                if isinstance(row, dict):
                    row = [row[x] for x in columns]
                statement, params = cls._from_records_build_insert_statement(table, row)
                try:
                    cursor.execute(statement, params)
                except Exception as e:
                    exc_cls = e.__class__
                    msg = ('\n'
                           '    row -> %s\n'
                           '    sql -> %s\n'
                           ' params -> %s') % (row, statement, params)
                    msg = str(e).strip() + msg
                    raise exc_cls(msg)
            connection.commit()  # COMMIT TRANSACTION

        except Exception as e:
            connection.rollback()  # ROLLBACK TRANSACTION
            raise e

        finally:
            connection.isolation_level = _isolation_level  # Restore original.

        return cls(connection, table)

    @classmethod
    def _from_records_build_create_statement(cls, table, columns):
        """Return 'CREATE TABLE' statement."""
        cls._from_records_assert_unique(columns)
        columns = [cls._from_records_normalize_column(x) for x in columns]
        return 'CREATE TABLE %s (%s)' % (table, ', '.join(columns))

    @staticmethod
    def _from_records_build_insert_statement(table, row):
        """Return 'INSERT INTO' statement."""
        assert not isinstance(row, str), '`row` must be list or tuple, not str'
        statement = 'INSERT INTO ' + table + ' VALUES (' + ', '.join(['?'] * len(row)) + ')'
        parameters = row
        return statement, parameters

    @staticmethod
    def _from_records_normalize_column(name):
        """Normalize value for use as SQLite column name."""
        name = name.strip()
        name = name.replace('"', '""')  # Escape quotes.
        if name == '':
            name = '_empty_'
        return '"' + name + '"'

    @staticmethod
    def _from_records_assert_unique(lst):
        """Asserts that list of items is unique, raises Exception if not."""
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


class CsvDataSource(BaseDataSource):
    """Loads CSV data from *file* (path or file-like object):
    ::

        subjectData = datatest.CsvDataSource('mydata.csv')

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

        # Populate database.
        if encoding:
            with _UnicodeCsvReader(file, encoding=encoding) as reader:
                columns = next(reader)  # Header row.
                self._source = SqliteDataSource.from_records(reader, columns)

        else:
            try:
                with _UnicodeCsvReader(file, encoding='utf-8') as reader:
                    columns = next(reader)  # Header row.
                    self._source = SqliteDataSource.from_records(reader, columns)

            except UnicodeDecodeError:
                with _UnicodeCsvReader(file, encoding='iso8859-1') as reader:
                    columns = next(reader)  # Header row.
                    self._source = SqliteDataSource.from_records(reader, columns)

                try:
                    filename = os.path.basename(file)
                except AttributeError:
                    filename = repr(file)
                msg = ('\nData in file {0!r} does not appear to be encoded '
                       'as UTF-8 (used ISO-8859-1 as fallback). To assure '
                       'correct operation, please specify a text encoding.')
                warnings.warn(msg.format(filename))

    def __repr__(self):
        """Return a string representation of the data source."""
        cls_name = self.__class__.__name__
        src_file = self._file_repr
        return '{0}({1})'.format(cls_name, src_file)

    def columns(self):
        """Return list of column names."""
        return self._source.columns()

    def slow_iter(self):
        """Return iterable of dictionary rows (like csv.DictReader)."""
        return self._source.slow_iter()

    def sum(self, column, **filter_by):
        """Return sum of values in column."""
        return self._source.sum(column, **filter_by)

    def count(self, **filter_by):
        """Return count of rows."""
        return self._source.count(**filter_by)

    def unique(self, *column, **filter_by):
        """Return iterable of tuples of unique column values."""
        return self._source.unique(*column, **filter_by)

    def set(self, column, **filter_by):
        """Convenience function for unwrapping single column results
        from ``unique()`` and returning as a set."""
        return self._source.set(column, **filter_by)

    def create_index(self, *columns):
        """Creating an index for certain columns can speed up data
        testing in many cases.

        See :meth:`SqliteDataSource.create_index
        <datatest.SqliteDataSource.create_index>` for more details.

        """
        self._source.create_index(*columns)


class FilteredDataSource(BaseDataSource):
    """A wrapper class to filter for those records of *source* for which
    *function* returns true. If *function* is ``None``, the identity
    function is assumed, that is, it filters for records of *source*
    which contain at least one value that evaluates as true.

    The following example filters the original data source to records
    for which the "foo" column contains positive numeric values::

        def is_positive(dict_row):
            val = dict_row['foo']
            return int(val) > 0

        orig_src = datatest.CsvDataSource('mydata.csv')
        subjectData = datatest.FilteredDataSource(is_positive, orig_src)

    The original source is stored in the ``__wrapped__`` attribute.

    """

    def __init__(self, function, source):
        msg = 'Sources must be derived from BaseDataSource'
        assert isinstance(source, BaseDataSource), msg

        if function is None:
            function = lambda row: any(row.values())  # Identity function.
            function.__name__ = '<identity function>'

        self._function = function
        self.__wrapped__ = source

    def __repr__(self):
        cls_name = self.__class__.__name__
        fun_name = self._function.__name__
        src_name = self.__wrapped__
        return '{0}({1}, {2})'.format(cls_name, fun_name, src_name)

    def columns(self):
        return self.__wrapped__.columns()

    def slow_iter(self):
        return (x for x in self.__wrapped__.slow_iter() if self._function(x))


#class MappedDataSource(BaseDataSource):


class MultiDataSource(BaseDataSource):
    """A wrapper class that allows multiple data sources to be treated
    as a single, composite data source::

        subjectData = datatest.MultiDataSource(
            datatest.CsvDataSource('file1.csv'),
            datatest.CsvDataSource('file2.csv'),
            datatest.CsvDataSource('file3.csv')
        )

    The original sources are stored in the ``__wrapped__`` attribute.

    """

    def __init__(self, *sources):
        """Initialize self."""
        for source in sources:
            msg = 'Sources must be derived from BaseDataSource'
            assert isinstance(source, BaseDataSource), msg
        self.__wrapped__ = sources

    def __repr__(self):
        """Return a string representation of the data source."""
        cls_name = self.__class__.__name__
        src_names = [repr(src) for src in self.__wrapped__]  # Get reprs.
        src_names = ['    ' + src for src in src_names]      # Prefix with 4 spaces.
        src_names = ',\n'.join(src_names)                    # Join w/ comma & new-line.
        return '{0}(\n{1}\n)'.format(cls_name, src_names)

    def slow_iter(self):
        """Return iterable of dictionary rows (like csv.DictReader)."""
        columns = self.columns()
        for source in self.__wrapped__:
            for row in source.slow_iter():
                yield dict((col, row.get(col, '')) for col in columns)

    def columns(self):
        """Return sequence or collection of column names."""
        columns = []
        for source in self.__wrapped__:
            for col in source.columns():
                if col not in columns:
                    columns.append(col)  # TODO: Look at improving order!
        return columns

    @staticmethod
    def _normalize_unique(allcols, subcols, unique):
        if tuple(allcols) == tuple(subcols):
            return unique  # <- EXIT!

        def fn(row):
            row = dict(zip(subcols, row))
            return tuple(row.get(col, '') for col in allcols)
        return (fn(row) for row in unique)

    @staticmethod
    def _filtered_call(source, method, *column, **filter_by):
        subcols = source.columns()
        column = [x for x in column if x in subcols]
        if any(v != '' for k, v in filter_by.items() if k not in subcols):
            return None  # <- EXIT!
        sub_filter = dict((k, v) for k, v in filter_by.items() if k in subcols)
        fn = getattr(source, method)
        return fn(*column, **sub_filter)

    def unique(self, *column, **filter_by):
        """Return iterable of unique values in column."""
        all_cols = self.columns()
        not_found = [x for x in column if x not in all_cols]
        if not_found:
            raise KeyError(not_found[0])

        result = []
        for source in self.__wrapped__:
            source_columns = source.columns()
            sub_col = [col for col in column if col in source_columns]
            if sub_col:
                sub_result = self._filtered_call(source, 'unique', *sub_col, **filter_by)
                if sub_result:
                    sub_result = self._normalize_unique(column, sub_col, sub_result)
                    result.append(sub_result)
            else:
                result.append([('',) * len(column)])

        result = itertools.chain(*result)

        seen = set()  # Using "unique_everseen" recipe from itertools.
        seen_add = seen.add
        for element in itertools.filterfalse(seen.__contains__, result):
            seen_add(element)
            yield element

    def sum(self, column, **filter_by):
        """Return sum of values in column."""
        if column not in self.columns():
            msg = 'No sub-source contains {0!r} column.'.format(column)
            raise Exception(msg)

        total_result = 0
        for source in self.__wrapped__:
            if column in source.columns():
                result = self._filtered_call(source, 'sum', column, **filter_by)
                if result:
                    total_result += result

        return total_result

    def count(self, **filter_by):
        """Return count of rows."""
        total_result = 0
        for source in self.__wrapped__:
            result = self._filtered_call(source, 'count', **filter_by)
            if result:
                total_result += result

        return total_result


class UniqueDataSource(BaseDataSource):
    """A wrapper class to filter *source* for unique values in the given
    list of *columns*.

    The following example accesses the unique "state" and "county"
    values contained in the original source::

        orig_src = datatest.CsvDataSource('mydata.csv')
        subjectData = UniqueDataSource(orig_src, ['state', 'county'])

    The original source is stored in the ``__wrapped__`` attribute.

    """

    def __init__(self, source, columns):
        msg = 'Sources must be derived from BaseDataSource'
        assert isinstance(source, BaseDataSource), msg
        self.__wrapped__ = source
        self._columns = columns

    def __repr__(self):
        cls_name = self.__class__.__name__
        src_name = self.__wrapped__
        col_name = repr(self._columns)
        return '{0}({1}, {2})'.format(cls_name, src_name, col_name)

    def columns(self):
        return self._columns

    def slow_iter(self):
        columns = self._columns
        for row in self.__wrapped__.unique(*columns):
            yield dict(zip(columns, row))


#DefaultDataSource = CsvDataSource
