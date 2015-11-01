# -*- coding: utf-8 -*-
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

from .queryresult import ResultMapping
from .queryresult import ResultSet

#pattern = 'test*.py'
prefix = 'test_'

sqlite3.register_adapter(Decimal, str)


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

        Return list of column names.
        """
        return NotImplemented

    def slow_iter(self):
        """NotImplemented

        Return an iterable of dictionary rows (like ``csv.DictReader``).
        """
        return NotImplemented

    def sum(self, column, **filter_by):
        """Return sum of values in *column* (uses ``slow_iter``).  This method
        is deprecated and will be removed.

        """
        iterable = self.__filter_by(self.slow_iter(), **filter_by)
        iterable = (x[column] for x in iterable)
        make_decimal = lambda x: Decimal(x) if x else Decimal('0')
        return sum(make_decimal(x) for x in iterable)

    def sum2(self, column, group_by=None, **filter_by):
        """Return sum of values in *column* (uses ``aggregate``)."""
        fn = lambda iterable: sum(Decimal(x) for x in iterable if x)
        return self.aggregate(fn, column, group_by, **filter_by)

    def count2(self, group_by=None, **filter_by):
        """Return count of rows (uses ``aggregate``)."""
        function = lambda iterable: sum(1 for x in iterable if x)

        iterable = self.__filter_by(self.slow_iter(), **filter_by)

        if group_by == None:
            return function(1 for row in iterable)  # <- EXIT!    # <- REPLACE WITH SUM

        if isinstance(group_by, str):
            keyfn = lambda row: row[group_by]
        else:
            keyfn = lambda row: tuple(row[x] for x in group_by)
        iterable = sorted(iterable, key=keyfn)
        fn = lambda g: function(1 for row in g)                   # <- REPLACE WITH SUM
        iterable = ((k, fn(g)) for k, g in itertools.groupby(iterable, keyfn))
        return ResultMapping(iterable, group_by)

    def aggregate(self, function, column, group_by=None, **filter_by):
        """Aggregates values in the given *column* (uses ``slow_iter``).
        If group_by is omitted, the result is returned as-is, otherwise
        returns a ResultMapping object.  The *function* should take an
        iterable and return a single summary value.

        """
        iterable = self.__filter_by(self.slow_iter(), **filter_by)

        if group_by == None:
            return function(row[column] for row in iterable)  # <- EXIT!

        if isinstance(group_by, str):
            keyfn = lambda row: row[group_by]
        else:
            keyfn = lambda row: tuple(row[x] for x in group_by)
        iterable = sorted(iterable, key=keyfn)
        fn = lambda g: function(row[column] for row in g)
        iterable = ((k, fn(g)) for k, g in itertools.groupby(iterable, keyfn))
        return ResultMapping(iterable, group_by)

    def count(self, **filter_by):
        """Return count of rows (uses ``slow_iter``)"""
        iterable = self.__filter_by(self.slow_iter(), **filter_by)
        return sum(1 for x in iterable)

    def unique(self, *column, **filter_by):
        """Return iterable of tuples containing unique *column* values
        (uses ``slow_iter``).
        """
        iterable = self.__filter_by(self.slow_iter(), **filter_by)  # Filtered rows only.
        fn = lambda row: tuple(row[x] for x in column)
        iterable = (fn(row) for row in iterable)
        seen = set()  # Using "unique_everseen" recipe from itertools.
        seen_add = seen.add
        for element in itertools.filterfalse(seen.__contains__, iterable):
            seen_add(element)
            yield element

    def distinct(self, column, **filter_by):
        """Return iterable of tuples containing distinct *column* values
        (uses ``slow_iter``).
        """
        iterable = self.__filter_by(self.slow_iter(), **filter_by)  # Filtered rows only.

        if isinstance(column, str) or not isinstance(column, Iterable):
            iterable = (row[column] for row in iterable)
        else:
            iterable = (tuple(row[c] for c in column) for row in iterable)

        return ResultSet(iterable)

    def set(self, column, **filter_by):
        """Convenience function for unwrapping single column results
        from ``unique()`` and returning as a set.  This method is
        deprecated and will be removed.

        """
        #return set(x[0] for x in self.unique(column, **filter_by))
        return self.distinct(column, **filter_by)

    @staticmethod
    def __filter_by(iterable, **filter_by):
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

    def sum2(self, column, group_by=None, **filter_by):
        """Return sum of values in *column*."""
        if group_by == None:
            column = self._from_records_normalize_column(column)
            select_clause = 'SUM({0})'.format(column)
            cursor = self._execute_query(self._table, select_clause, **filter_by)
            return cursor.fetchone()[0]  # <- EXIT!

        if isinstance(group_by, str):
            group_clause = self._from_records_normalize_column(group_by)
        else:
            group_clause = [self._from_records_normalize_column(x) for x in group_by]
            group_clause = ', '.join(group_clause)

        column = self._from_records_normalize_column(column)
        select_clause = '{0}, SUM({1})'.format(group_clause, column)
        trailing_clause = 'GROUP BY ' + group_clause

        cursor = self._execute_query(self._table, select_clause, trailing_clause, **filter_by)

        if not isinstance(group_by, str):
            mktup = lambda row: (row[:len(group_by)], row[-1])
            cursor = (mktup(x) for x in cursor)

        return ResultMapping(cursor, group_by)

    def count(self, **filter_by):
        """Return count of rows."""
        cursor = self._execute_query(self._table, 'COUNT(*)', **filter_by)
        return cursor.fetchone()[0]

    def distinct(self, column, **filter_by):
        """Return iterable of tuples containing distinct *column* values."""
        all_cols = self.columns()
        if isinstance(column, str) or not isinstance(column, Iterable):
            not_found = [column] if column not in all_cols else []
        else:
            not_found = [x for x in column if x not in all_cols]
        if not_found:
            raise KeyError(not_found[0])

        if isinstance(column, str):
            select_clause = self._from_records_normalize_column(column)
        else:
            select_clause = [self._from_records_normalize_column(x) for x in column]
            select_clause = ', '.join(select_clause)
        select_clause = 'DISTINCT ' + select_clause

        cursor = self._execute_query(self._table, select_clause, **filter_by)

        if isinstance(column, str):
            cursor = (x[0] for x in cursor)

        return ResultSet(x for x in cursor)

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
        testing in some cases.

        Indexes should be added one-by-one to tune a test suite's
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
    def from_result(cls, result, columns, in_memory=False):
        """Alternate constructor to load an existing ResultSet or
        ResultMapping::

            original = CsvDataSource('mydata.csv')
            result = original.distinct(['state', 'county'])
            subjectData = CsvDataSource.from_result(result, ['state', 'county'])

        """
        if isinstance(columns, str):
            columns = [columns]
            values = [(x,) for x in result.values]
        else:
            values = result.values

        if isinstance(result, ResultSet):
            source =  cls.from_records(values, columns, in_memory)
        elif isinstance(result, ResultMapping):
            items = result.values.items()
            items = iter(items)
            first_item = next(items)  # Get first item.
            items = itertools.chain([first_item], items)  # Rebuild original.

            first_k, first_v = first_item
            if not isinstance(first_k, tuple):
                items = (((k,), v) for k, v in items)
            if not isinstance(first_v, tuple):
                items = ((k, (v,)) for k, v in items)
            items = (k + v for k, v in items)

            kcols = result.grouped_by
            if not isinstance(kcols, (tuple, list)):
                kcols = [kcols]
            combined = list(kcols) + list(columns)

            source =  cls.from_records(items, combined, in_memory)
        else:
            raise TypeError('requires ResultSet or ResultMapping')

        return source

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
            if isinstance(e, UnicodeDecodeError):
                e.reason += '\n{0}'.format(statement)
                raise e
            raise e.__class__('{0}\n{1}'.format(e, statement))

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

    def sum2(self, column, group_by=None, **filter_by):
        return self._source.sum2(column, group_by, **filter_by)

    def count(self, **filter_by):
        """Return count of rows."""
        return self._source.count(**filter_by)

    def distinct(self, column, **filter_by):
        return self._source.distinct(column, **filter_by)

    def unique(self, *column, **filter_by):
        """Return iterable of tuples of unique column values."""
        return self._source.unique(*column, **filter_by)

    def set(self, column, **filter_by):
        """Convenience function for unwrapping single column results
        from ``unique()`` and returning as a set."""
        return self._source.set(column, **filter_by)

    def create_index(self, *columns):
        """Creating an index for certain columns can speed up data
        testing in some cases.

        See :meth:`SqliteDataSource.create_index
        <datatest.SqliteDataSource.create_index>` for more details.

        """
        self._source.create_index(*columns)


class FilteredDataSource(BaseDataSource):
    """A wrapper class to filter for those records of *source* for which
    *function* returns true.  If *function* is ``None``, the identity
    function is assumed, that is, it filters for records of *source*
    which contain at least one value that evaluates as true.

    The following example filters the original data source to records
    for which the "foo" column contains positive numeric values::

        def is_positive(dict_row):
            val = dict_row['foo']
            return int(val) > 0

        orig_src = datatest.CsvDataSource('mydata.csv')
        subjectData = datatest.FilteredDataSource(orig_src, is_positive)

    The original source is stored in the ``__wrapped__`` attribute.

    """

    def __init__(self, source, function=None):
        """Initialize self."""
        msg = 'Sources must be derived from BaseDataSource'
        assert isinstance(source, BaseDataSource), msg

        if function is None:
            function = lambda row: any(row.values())  # Identity function.
            function.__name__ = '<identity function>'

        self._function = function
        self.__wrapped__ = source

    def __repr__(self):
        """Return a string representation of the data source."""
        cls_name = self.__class__.__name__
        src_name = repr(self.__wrapped__)
        fun_name = self._function.__name__
        return '{0}({1}, {2})'.format(cls_name, src_name, fun_name)

    def columns(self):
        """Return list of column names."""
        return self.__wrapped__.columns()

    def slow_iter(self):
        """Return iterable of dictionary rows (like csv.DictReader)."""
        return (x for x in self.__wrapped__.slow_iter() if self._function(x))


class MappedDataSource(BaseDataSource):
    """A wrapper to apply *function* to every row in *source* and
    return a new source using these results.  *function* must accept a
    single dict and return a dict.  This class can be used to remove
    columns, rename columns, and create new columns.

    The following example calculates the percentage of hispanic
    population and appends the result as a new column::

        def make_percent(row):
            hisp = float(row['hisp_population'])
            total = float(row['total_population'])
            row['hisp_percent'] = hisp / total
            return row

        orig_src = datatest.CsvDataSource('mydata.csv')
        subjectData = datatest.MappedDataSource(orig_src, make_percent)

    The original source is stored in the ``__wrapped__`` attribute.

    """

    def __init__(self, source, function):
        """Initialize self."""
        msg = 'Sources must be derived from BaseDataSource'
        assert isinstance(source, BaseDataSource), msg
        self._function = function
        self.__wrapped__ = source

    def __repr__(self):
        """Return a string representation of the data source."""
        cls_name = self.__class__.__name__
        fun_name = self._function.__name__
        src_name = self.__wrapped__
        return '{0}({1}, {2})'.format(cls_name, fun_name, src_name)

    def columns(self):
        """Return list of column names."""
        one_row = next(self.slow_iter())
        keys = list(one_row.keys())

        cols = []
        for col in self.__wrapped__.columns():
            if col in keys:
                cols.append(keys.pop(keys.index(col)))
        return cols + sorted(keys)

    def slow_iter(self):
        """Return iterable of dictionary rows (like csv.DictReader)."""
        for row in self.__wrapped__.slow_iter():
            yield self._function(row)


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
        """Return list of column names."""
        columns = []
        for source in self.__wrapped__:
            for col in source.columns():
                if col not in columns:
                    columns.append(col)  # TODO: Look at improving order!
        return columns

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
        """Return iterable of tuples containing distinct *column* values."""
        noncollection_column = isinstance(column, str)
        if noncollection_column:
            column = [column]

        self_columns = self.columns()
        for col in column:
            if col not in self_columns:  # Must be in at least one sub-source.
                raise KeyError(col)

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
                        if tst.values:
                            subres = ResultSet([tuple(['']) * len(column)])
                            results.append(subres)
                    else:
                        # If subsrc contains at least 1 item, then
                        # add an empty row to the result list.  If
                        # subsrc is completely empty, then don't add
                        # anything.
                        iterable = subsrc.slow_iter()
                        try:
                            next(iterable)
                            subres = ResultSet([tuple(['']) * len(column)])
                            results.append(subres)
                        except StopIteration:
                            pass

        results = (x.values for x in results)  # Unwrap values property.
        results = itertools.chain(*results)

        if noncollection_column:
            results = (x[0] for x in results)  # Unpack 1-tuple into string.
        return ResultSet(results)

    def sum2(self, column, group_by=None, **filter_by):
        """Return sum of values in *column* grouped by *group_by*."""
        if column not in self.columns():
            raise KeyError(column)

        if group_by is None:
            total = 0
            for subsrc in self.__wrapped__:
                subsrc_columns = subsrc.columns()
                if column in subsrc_columns:
                    subfltr = self._make_sub_filter(subsrc_columns, **filter_by)
                    if subfltr is not None:
                        total = total + subsrc.sum2(column, **subfltr)
            return total
        else:
            noncollection_group = isinstance(group_by, str)
            if noncollection_group:
                group_by = [group_by]

            counter = Counter()
            for subsrc in self.__wrapped__:
                subsrc_columns = subsrc.columns()
                if column in subsrc_columns:
                    subfltr = self._make_sub_filter(subsrc_columns, **filter_by)
                    if subfltr is not None:
                        subgrp = [x for x in group_by if x in subsrc_columns]
                        subres = subsrc.sum2(column, subgrp, **subfltr)
                        subres = self._normalize_result(subres, subgrp, group_by)
                        for k, v in subres.values.items():
                            counter[k] += v
            if noncollection_group:  # Unpack 1-tuple key into string.
                counter = dict((k[0], v) for k, v in counter.items())
            return ResultMapping(counter, group_by)

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

        if isinstance(orig_cols, str):
            orig_cols = [orig_cols]

        if not all(x in targ_cols for x in orig_cols):
            raise ValueError('Target columns must include all original columns.')

        def normalize(orig):
            orig_dict = dict(zip(orig_cols, orig))
            return tuple(orig_dict.get(col, '') for col in targ_cols)

        if isinstance(result_obj, ResultSet):
            normalized = ResultSet(normalize(v) for v in result_obj.values)
        elif isinstance(result_obj, ResultMapping):
            item_gen = ((normalize(k), v) for k, v in result_obj.values.items())
            normalized = ResultMapping(item_gen, grouped_by=targ_cols)
        else:
            raise ValueError('Result object must be ResultSet or ResultMapping.')

        return normalized

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


#DefaultDataSource = CsvDataSource
