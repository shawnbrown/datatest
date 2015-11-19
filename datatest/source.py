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
    ``sum()``, ``count()``, and ``aggregate()``.

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
        """Return iterable of tuples containing distinct *column* values
        (uses slow ``__iter__``).
        """
        iterable = self.__filter_by(**filter_by)  # Filtered rows only.
        if isinstance(column, str):
            column = [column]
        iterable = (tuple(row[c] for c in column) for row in iterable)
        return ResultSet(iterable)

    def sum(self, column, group_by=None, **filter_by):
        """Returns sum of *column* grouped by *group_by* as ResultMapping
        (uses ``aggregate`` method).
        """
        fn = lambda iterable: sum(Decimal(x) for x in iterable if x)
        return self.aggregate(fn, column, group_by, **filter_by)

    def count(self, group_by=None, **filter_by):
        """Returns count of *column* grouped by *group_by* as ResultMapping
        (uses ``aggregate`` method).
        """
        fn = lambda iterable: sum(1 for x in iterable)
        return self.aggregate(fn, column=None, group_by=group_by, **filter_by)

    def aggregate(self, function, column=None, group_by=None, **filter_by):
        """Aggregates values in the given *column* (uses slow ``__iter__``).
        If group_by is omitted, the result is returned as-is, otherwise
        returns a ResultMapping object.  The *function* should take an
        iterable and return a single summary value.

        """
        iterable = self.__filter_by(**filter_by)

        if column:
            fn = lambda grp: function(row[column] for row in grp)
        else:
            fn = lambda grp: function(None for row in grp)

        if group_by == None:
            return fn(iterable)  # <- EXIT!

        if isinstance(group_by, str):
            group_by = [group_by]

        keyfn = lambda row: tuple(row[x] for x in group_by)
        iterable = sorted(iterable, key=keyfn)
        iterable = itertools.groupby(iterable, keyfn)
        iterable = ((k, fn(g)) for k, g in iterable)
        return ResultMapping(iterable, group_by)

    def __filter_by(self, **filter_by):
        """Filter data by keywords, returns iterable.  E.g., where
        column1=value1, column2=value2, etc. (uses slow ``__iter__``).
        """
        mktup = lambda v: (v,) if not _is_nscontainer(v) else v
        filter_by = dict((k, mktup(v)) for k, v in filter_by.items())
        for row in self.__iter__():
            if all(row[k] in v for k, v in filter_by.items()):
                yield row


class SqliteSource(BaseSource):
    """Loads *table* data from given SQLite *connection*:
    ::

        conn = sqlite3.connect('mydatabase.sqlite3')
        subjectData = datatest.SqliteSource(conn, 'mytable')

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
        cursor.execute('PRAGMA synchronous=OFF')
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
        """Return iterable of tuples containing distinct *column* values."""
        if isinstance(column, str):
            column = [column]

        all_cols = self.columns()
        not_found = [x for x in column if x not in all_cols]
        if not_found:
            raise KeyError(not_found[0])

        select_clause = [self._normalize_column(x) for x in column]
        select_clause = ', '.join(select_clause)
        select_clause = 'DISTINCT ' + select_clause

        cursor = self._execute_query(self._table, select_clause, **filter_by)
        return ResultSet(cursor)

    def sum(self, column, group_by=None, **filter_by):
        """Returns sum of *column* grouped by *group_by* as ResultMapping."""
        column = self._normalize_column(column)
        sql_function = 'SUM({0})'.format(column)
        return self._sql_aggregate(sql_function, group_by, **filter_by)

    def count(self, group_by=None, **filter_by):
        """Returns count of *column* grouped by *group_by* as ResultMapping."""
        return self._sql_aggregate('COUNT(*)', group_by, **filter_by)

    def _sql_aggregate(self, sql_function, group_by=None, **filter_by):
        """Aggregates values using SQL function select--e.g., 'COUNT(*)',
        'SUM(col1)', etc.

        """
        if group_by == None:
            cursor = self._execute_query(self._table, sql_function, **filter_by)
            return cursor.fetchone()[0]  # <- EXIT!

        if isinstance(group_by, str):
            group_by = [group_by]
        group_clause = [self._normalize_column(x) for x in group_by]
        group_clause = ', '.join(group_clause)

        select_clause = '{0}, {1}'.format(group_clause, sql_function)
        trailing_clause = 'GROUP BY ' + group_clause

        cursor = self._execute_query(self._table, select_clause, trailing_clause, **filter_by)
        iterable = ((row[:-1], row[-1]) for row in cursor)
        return ResultMapping(iterable, group_by)

    def aggregate(self, function, column=None, group_by=None, **filter_by):
        """Aggregates values in the given *column*.  If group_by is omitted,
        the result is returned as-is, otherwise returns a ResultMapping
        object.  The *function* should take an iterable and return a single
        summary value.

        """
        normalize = self._normalize_column

        if column:
            if column not in self.columns():
                raise KeyError(column)
            select_clause = normalize(column)
            fn = lambda grp: function(row[0] for row in grp)
        else:
            select_clause = 'NULL'
            fn = lambda grp: function(None for row in grp)

        if group_by == None:
            cursor = self._execute_query(self._table, select_clause, **filter_by)
            return fn(cursor)  # <- EXIT!

        if isinstance(group_by, str):
            group_by = [group_by]

        result = {}
        groups = self.distinct(group_by, **filter_by)
        for group in groups:
            subfilter_by = dict(zip(group_by, group))
            subfilter_by.update(filter_by)
            cursor = self._execute_query(self._table, select_clause, **subfilter_by)
            result[group] = fn(cursor)
        return ResultMapping(result, group_by)

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
        col_names = [self._normalize_column(x) for x in columns]
        col_names = ', '.join(col_names)

        # Prepare statement.
        statement = 'CREATE INDEX IF NOT EXISTS {0} ON {1} ({2})'
        statement = statement.format(idx_name, self._table, col_names)

        # Create index.
        cursor = self._connection.cursor()
        cursor.execute('PRAGMA synchronous=OFF')
        cursor.execute(statement)

    @classmethod
    def from_result(cls, result, columns, in_memory=False):
        """Alternate constructor to load an existing ResultSet or
        ResultMapping::

            original = CsvSource('mydata.csv')
            result = original.distinct(['state', 'county'])
            subjectData = CsvSource.from_result(result, ['state', 'county'])

        """
        if isinstance(columns, str):
            columns = [columns]
            values = ((x,) for x in result)
        else:
            values = result

        if isinstance(result, ResultSet):
            source =  cls.from_records(values, columns, in_memory)
        elif isinstance(result, ResultMapping):
            items = iter(result.items())
            first_item = next(items)  # Get first item.
            items = itertools.chain([first_item], items)  # Rebuild original.

            first_k, first_v = first_item
            if not _is_nscontainer(first_k):
                items = (((k,), v) for k, v in items)
            if not _is_nscontainer(first_v):
                items = ((k, (v,)) for k, v in items)
            items = (k + v for k, v in items)

            kcols = result.key_names
            if not _is_nscontainer(kcols):
                kcols = [kcols]
            combined = list(kcols) + list(columns)

            source =  cls.from_records(items, combined, in_memory)
        else:
            raise TypeError('requires ResultSet or ResultMapping')

        return source

    @classmethod
    def from_records(cls, data, columns=None, in_memory=False):
        """Alternate constructor to load an existing collection of
        records.  Loads *data* (an iterable of lists, tuples, or dicts)
        into a new SQLite database with the given *columns*::

            subjectData = datatest.SqliteSource.from_records(records, columns)

        """
        if not columns:
            data = iter(data)
            first_row = next(data)
            if hasattr(first_row, 'keys'):  # Dict-like rows.
                columns = tuple(first_row.keys())
            elif hasattr(first_row, '_fields'):  # Namedtuple-like rows.
                columns = first_row._fields
            else:
                msg = ('columns argument can only be omitted if data '
                       'contains dict-rows or namedtuple-rows')
                raise TypeError(msg)
            data = itertools.chain([first_row], data)  # Rebuild original.

        # Create database (an empty string denotes use of a temp file).
        sqlite_path = ':memory:' if in_memory else ''
        connection = sqlite3.connect(sqlite_path)

        # Load data into table and return new instance.
        table = 'main'
        cls._load_table(connection, table, columns, data)
        return cls(connection, table)

    @classmethod
    def _load_table(cls, connection, table, columns, data):
        # Set isolation_level to None for proper transaction handling.
        _isolation_level = connection.isolation_level
        connection.isolation_level = None

        cursor = connection.cursor()
        cursor.execute('PRAGMA synchronous=OFF')  # For faster loading.
        cursor.execute('BEGIN TRANSACTION')
        try:
            statement = cls._create_table_statement(table, columns)
            cursor.execute(statement)

            for row in data:  # Insert all rows.
                if isinstance(row, dict):
                    row = tuple(row[x] for x in columns)
                statement, params = cls._insert_into_statement(table, row)
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

    @classmethod
    def _create_table_statement(cls, table, columns):
        """Return 'CREATE TABLE' statement."""
        cls._assert_unique(columns)
        columns = [cls._normalize_column(x) for x in columns]
        return 'CREATE TABLE %s (%s)' % (table, ', '.join(columns))

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


class CsvSource(BaseSource):
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

        # Populate database.
        if encoding:
            with _UnicodeCsvReader(file, encoding=encoding) as reader:
                columns = next(reader)  # Header row.
                self._source = SqliteSource.from_records(reader, columns)

        else:
            try:
                with _UnicodeCsvReader(file, encoding='utf-8') as reader:
                    columns = next(reader)  # Header row.
                    self._source = SqliteSource.from_records(reader, columns)

            except UnicodeDecodeError:
                with _UnicodeCsvReader(file, encoding='iso8859-1') as reader:
                    columns = next(reader)  # Header row.
                    self._source = SqliteSource.from_records(reader, columns)

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

    def __iter__(self):
        """Return iterable of dictionary rows (like csv.DictReader)."""
        return self._source.__iter__()

    def sum(self, column, group_by=None, **filter_by):
        return self._source.sum(column, group_by, **filter_by)

    def count(self, group_by=None, **filter_by):
        return self._source.count(group_by, **filter_by)

    def distinct(self, column, **filter_by):
        return self._source.distinct(column, **filter_by)

    def create_index(self, *columns):
        """Creating an index for certain columns can speed up data
        testing in some cases.

        See :meth:`SqliteSource.create_index
        <datatest.SqliteSource.create_index>` for more details.

        """
        self._source.create_index(*columns)


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
        if isinstance(column, str):
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

    def sum(self, column, group_by=None, **filter_by):
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
                        total = total + subsrc.sum(column, **subfltr)
            return total
        else:
            if isinstance(group_by, str):
                group_by = [group_by]

            counter = Counter()
            for subsrc in self.__wrapped__:
                subsrc_columns = subsrc.columns()
                if column in subsrc_columns:
                    subfltr = self._make_sub_filter(subsrc_columns, **filter_by)
                    if subfltr is not None:
                        subgrp = [x for x in group_by if x in subsrc_columns]
                        subres = subsrc.sum(column, subgrp, **subfltr)
                        subres = self._normalize_result(subres, subgrp, group_by)
                        for k, v in subres.items():
                            counter[k] += v
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
            normalized = ResultSet(normalize(v) for v in result_obj)
        elif isinstance(result_obj, ResultMapping):
            item_gen = ((normalize(k), v) for k, v in result_obj.items())
            normalized = ResultMapping(item_gen, key_names=targ_cols)
        else:
            raise ValueError('Result object must be ResultSet or ResultMapping.')

        return normalized


#DefaultDataSource = CsvSource
