# -*- coding: utf-8 -*-
import collections
import csv
import inspect
import io
import os
import sqlite3
import sys
import warnings
from decimal import Decimal

from datatest._builtins import *
import datatest._itertools as itertools

#pattern = 'test*.py'
prefix = 'test_'


class BaseDataSource(object):
    """Common base class for all data sources.  Custom sources can be
    created by subclassing BaseDataSource and implementing `__init__()`,
    `__str__()`, `slow_iter()`, and `columns()`.  Performance can be
    improved by implementing `set()`, `sum()`, `count()`, and `unique()`.
    """
    def __init__(self):
        """NotImplemented

        Initialize self.
        """
        return NotImplemented

    def __str__(self):
        """NotImplemented

        Should return a brief, one line, description of the data source.
        """
        return NotImplemented

    def slow_iter(self):
        """NotImplemented

        Should return an iterable of dictionary rows (like csv.DictReader).
        """
        return NotImplemented

    def columns(self):
        """NotImplemented

        Should return a sequence or collection of column names.
        """
        return NotImplemented

    def sum(self, column, **filter_by):
        """Return sum of values in `column` (uses slow_iter)."""
        iterable = self._base_filter_by(self.slow_iter(), **filter_by)
        iterable = (x for x in iterable if x)
        return sum(Decimal(x[column]) for x in iterable)

    def count(self, column, **filter_by):
        """Return count of non-empty values in `column` (uses slow_iter)."""
        iterable = self._base_filter_by(self.slow_iter(), **filter_by)
        return sum(bool(x[column]) for x in iterable)

    def unique(self, *column, **filter_by):
        """Return iterable of unique values in column (uses slow_iter)."""
        iterable = self._base_filter_by(self.slow_iter(), **filter_by)  # Filtered rows only.
        fn = lambda row: tuple(row.get(col, '') for col in column)  # Gets columns.
        iterable = (fn(x) for x in iterable)
        seen = set()  # Using "unique_everseen" recipe from itertools.
        seen_add = seen.add
        for element in itertools.filterfalse(seen.__contains__, iterable):
            seen_add(element)
            yield element

    def set(self, column, **filter_by):
        """Convenience function for unwrapping single column results."""
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
    """SQLite interface, requires SQLite database `connection` and name
    of database `table`::

        conn = sqlite3.connect('mydatabase.sqlite3')
        subjectData = datatest.SqliteDataSource(conn, 'mytable')
    """
    def __init__(self, connection, table):
        """Initialize self."""
        self.__name__ = 'SQLite Table {0!r}'.format(table)
        self._connection = connection
        self._table = table

    def __str__(self):
        return 'Table {0!r} in {1}'.format(self._table, self._connection)

    def slow_iter(self):
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

    def unique(self, *column, **filter_by):
        """Return iterable of unique values in column."""
        source_columns = self.columns()
        select_columns = [x for x in column if x in source_columns]
        if not select_columns:
            return [('',) * len(column)]  # <- EXIT!

        select_clause = ['"{0}"'.format(x) for x in select_columns]
        select_clause = ', '.join(select_clause)
        select_clause = 'DISTINCT {0}'.format(select_clause)
        cursor = self._execute_query(self._table, select_clause, **filter_by)

        def mkrow(row):
            def getval(col):
                if col in source_columns:
                    index = select_columns.index(col)
                    return row[index]
                else:
                    return ''
            return tuple(getval(col) for col in column)

        return (mkrow(x) for x in cursor)

    def sum(self, column, **filter_by):
        """Return sum of values in column."""
        select_clause = 'SUM("' + column + '")'
        cursor = self._execute_query(self._table, select_clause, **filter_by)
        return cursor.fetchone()[0]

    def count(self, column, **filter_by):
        """Return count of non-empty values in column."""
        select_clause = 'COUNT("' + column +  '")'
        cursor = self._execute_query(self._table, select_clause, **filter_by)
        return cursor.fetchone()[0]

    def _execute_query(self, table, select_clause, trailing_clause=None, **kwds):
        try:
            stmnt, params = self._build_query(self._table, select_clause, **kwds)
            if trailing_clause:
                stmnt += '\n' + trailing_clause
            cursor = self._connection.cursor()
            #print(stmnt, params)
            cursor.execute(stmnt, params)
        except Exception as e:
            exc_cls = e.__class__
            msg = '%s\n  query: %s\n  params: %r' % (e, stmnt, params)
            raise exc_cls(msg)
        return cursor

    @classmethod
    def _build_query(cls, table, select_clause, **kwds):
        query = 'SELECT ' + select_clause + ' FROM ' + table
        where_clause, params = cls._build_where_clause(**kwds)
        if where_clause:
            query = query + ' WHERE ' + where_clause
        return query, params

    @staticmethod
    def _build_where_clause(**kwds):
        clause = []
        params = []
        items = kwds.items()
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


class _UnicodeCsvReader:
    """UnicodeCsvReader wraps the standard library's `csv.reader` object
    to support unicode CSV files in both Python 3 and Python 2.

    Example usage:

        with UnicodeCsvReader('myfile.csv', encoding='utf-8') as reader:
            for row in reader:
                process(row)

    The `csvfile` argument can be a file path (as in the example above)
    or a file-like object.  When passing file objects, Python 3 requires
    them to be opened in text-mode ('r') while Python 2 requires them to
    be opened in binary-mode ('rb').  UnicodeCsvReader manages these
    differences automatically when given a file path.

    """
    def __init__(self, csvfile, encoding='utf-8', dialect='excel', **fmtparams):
        self.encoding = encoding
        self.dialect = dialect
        self._csvfile = csvfile  # Can be path or file-like object.
        self._fileobj = self._get_file_object(csvfile, self.encoding)
        self._reader = csv.reader(self._fileobj, dialect=self.dialect, **fmtparams)

    @property
    def line_num(self):
        return self._reader.line_num

    def __del__(self):
        # Note: When  __init__ fails, _fileobj will not exist.
        if hasattr(self, '_fileobj') and self._fileobj != self._csvfile:
            self._fileobj.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.__del__()

    def __iter__(self):
        return self

    @staticmethod
    def _get_file_object(csvfile, encoding):
        if isinstance(csvfile, str):
            return open(csvfile, 'rt', encoding=encoding, newline='')  # <- EXIT!

        if hasattr(csvfile, 'mode'):
            assert 'b' not in csvfile.mode, "File must be open in text mode ('rt')."
        elif issubclass(csvfile.__class__, io.IOBase):
            assert issubclass(csvfile.__class__, io.TextIOBase), ("Stream object must inherit "
                                                                  "from io.TextIOBase.")
        return csvfile

    def __next__(self):
        return next(self._reader)


# Patch `_UnicodeCsvReader` if using Python 2.
if sys.version < '3':
    _py3_UnicodeCsvReader = _UnicodeCsvReader
    class _UnicodeCsvReader(_py3_UnicodeCsvReader):
        @staticmethod
        def _get_file_object(csvfile, encoding):
            if isinstance(csvfile, str):
                return open(csvfile, 'rb')  # <- EXIT!

            if hasattr(csvfile, 'mode'):
                assert 'b' in csvfile.mode, ("When using Python 2, file must "
                                             "be open in binary mode ('rb').")
            elif issubclass(csvfile.__class__, io.IOBase):
                assert not issubclass(csvfile.__class__, io.TextIOBase), ("When using Python 2, "
                                                                          "must use byte stream "
                                                                          "(not text stream).")
            return csvfile

        def __next__(self):
            row = next(self._reader)
            return [s.decode(self.encoding) for s in row]

        def next(self):
            return self.__next__()


class CsvDataSource(SqliteDataSource):
    """CSV file data source
    ::
        subjectData = datatest.CsvDataSource('mydata.csv')
    """

    def __init__(self, file, encoding=None, in_memory=False):
        """Initialize self."""
        # If `file` is relative path, uses directory of calling file as base.
        if isinstance(file, str) and not os.path.isabs(file):
            calling_frame = sys._getframe(1)
            calling_file = inspect.getfile(calling_frame)
            base_path = os.path.dirname(calling_file)
            file = os.path.join(base_path, file)
            file = os.path.normpath(file)

        # Create database (an empty string denotes use of a temp file).
        sqlite_path = ':memory:' if in_memory else ''
        connection = sqlite3.connect(sqlite_path)

        # Populate database.
        if encoding:
            with _UnicodeCsvReader(file, encoding=encoding) as reader:
                self._populate_database(connection, reader)
        else:
            try:
                with _UnicodeCsvReader(file, encoding='utf-8') as reader:
                    self._populate_database(connection, reader)

            except UnicodeDecodeError:
                with _UnicodeCsvReader(file, encoding='iso8859-1') as reader:
                    self._populate_database(connection, reader)

                try:
                    filename = os.path.basename(file)
                except AttributeError:
                    filename = repr(file)
                msg = ('\nData in file {0!r} does not appear to be encoded '
                       'as UTF-8 (used ISO-8859-1 as fallback). To assure '
                       'correct operation, please specify a text encoding.')
                warnings.warn(msg.format(filename))

        self._file = file
        SqliteDataSource.__init__(self, connection, 'main')

    def __str__(self):
        return str(self._file)

    @classmethod
    def _populate_database(cls, connection, reader, table='main'):
        _isolation_level = connection.isolation_level
        connection.isolation_level = None
        cursor = connection.cursor()
        cursor.execute('BEGIN TRANSACTION')
        try:
            csv_header = next(reader)
            statement = cls._build_create_statement(table, csv_header)
            cursor.execute(statement)

            for row in reader:  # Insert all rows.
                if not row:
                    continue  # Skip if row is empty.
                statement, params = cls._build_insert_statement(table, row)
                try:
                    cursor.execute(statement, params)
                except Exception as e:
                    exc_cls = e.__class__
                    msg = ('\n'
                           '    row -> %s\n'
                           '    sql -> %s\n'
                           ' params -> %s' % (row, statement, params))
                    msg = str(e).strip() + msg
                    raise exc_cls(msg)
            connection.commit()

        except Exception as e:
            connection.rollback()
            raise e

        finally:
            connection.isolation_level = _isolation_level  # Restore original.

    @classmethod
    def _build_create_statement(cls, table, columns):
        """Return 'CREATE TABLE' statement."""
        cls._assert_unique(columns)
        columns = [cls._normalize_column(x) for x in columns]
        return 'CREATE TABLE %s (%s)' % (table, ', '.join(columns))

    @staticmethod
    def _build_insert_statement(table, row):
        """Return 'INSERT INTO' statement."""
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


class MultiDataSource(BaseDataSource):
    """Composite of multiple data source objects.  All `sources` must be
    derived from BaseDataSource::

        subjectData = datatest.MultiDataSource(
            datatest.CsvDataSource('file1.csv'),
            datatest.CsvDataSource('file2.csv'),
            datatest.CsvDataSource('file3.csv')
        )

    """

    def __init__(self, *sources):
        """Initialize self."""
        for source in sources:
            msg = 'Sources must be derived from BaseDataSource'
            assert isinstance(source, BaseDataSource), msg
        self.sources = sources

    def __str__(self):
        all_sources = [str(src) for src in self.sources]
        return '\n'.join(str(src) for src in self.sources)

    def slow_iter(self):
        """Return iterable of dictionary rows (like csv.DictReader)."""
        columns = self.columns()
        for source in self.sources:
            for row in source.slow_iter():
                for col in columns:
                    if col not in row:
                        row[col] = ''
                yield row

    def columns(self):
        """Return sequence or collection of column names."""
        columns = []
        for source in self.sources:
            for col in source.columns():
                if col not in columns:
                    columns.append(col)  # TODO: Look at improving order!
        return columns

    def unique(self, *column, **filter_by):
        """Return iterable of unique values in column."""
        sub_results = []
        for source in self.sources:
            sub_cols = source.columns()
            if any(v != '' for k, v in filter_by.items() if k not in sub_cols):
                continue
            sub_filter = dict((k, v) for k, v in filter_by.items() if k in sub_cols)
            sub_results.append(source.unique(*column, **sub_filter))

        iterable = itertools.chain(*sub_results)
        seen = set()  # Using "unique_everseen" recipe from itertools.
        seen_add = seen.add
        for element in itertools.filterfalse(seen.__contains__, iterable):
            seen_add(element)
            yield element

    def sum(self, column, **filter_by):
        """Return sum of values in column."""
        if column not in self.columns():
            msg = 'No sub-sources not contain {0!r} column.'.format(column)
            raise Exception(msg)

        total_result = 0
        for source in self.sources:
            subcols = source.columns()
            if column in subcols:
                if any(v != '' for k, v in filter_by.items() if k not in subcols):
                    continue
                subkwds = dict((k, v) for k, v in filter_by.items() if k in subcols)
                result = source.sum(column, **subkwds)
                if result:
                    total_result += result

        return total_result

    def count(self, column, **filter_by):
        """Return count of non-empty values in column."""
        if column not in self.columns():
            msg = 'No sub-sources not contain {0!r} column.'.format(column)
            raise Exception(msg)

        total_result = 0
        for source in self.sources:
            subcols = source.columns()
            if column in subcols:
                if any(v != '' for k, v in filter_by.items() if k not in subcols):
                    continue
                subkwds = dict((k, v) for k, v in filter_by.items() if k in subcols)
                total_result += source.count(column, **subkwds)

        return total_result


#DefaultDataSource = CsvDataSource
