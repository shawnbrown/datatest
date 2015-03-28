# -*- coding: utf-8 -*-
import collections
import csv
import inspect
import itertools
import os
import sqlite3
import sys
from decimal import Decimal

#pattern = 'test*.py'
prefix = 'test_'


class BaseDataSource(object):
    """Common base class for all data sources."""

    def __init__(self):
        """Initialize self."""
        return NotImplemented

    def slow_iter(self):
        """Return iterable of dictionary rows (like csv.DictReader)."""
        return NotImplemented

    def columns(self):
        """Return sequence or collection of column names."""
        return NotImplemented

    def set(self, column, **kwds):
        """Return set of values in column."""
        iterable = self._filtered(self.slow_iter(), **kwds)
        return set(x[column] for x in iterable)

    def sum(self, column, **kwds):
        """Return sum of values in column."""
        iterable = self._filtered(self.slow_iter(), **kwds)
        iterable = (x for x in iterable if x)
        return sum(Decimal(x[column]) for x in iterable)

    def count(self, column, **kwds):
        """Return count of non-empty values in column."""
        iterable = self._filtered(self.slow_iter(), **kwds)
        return sum(bool(x[column]) for x in iterable)

    def groups(self, *columns, **kwds):
        """Return iterable of unique dictionaries grouped by given columns."""
        iterable = self._filtered(self.slow_iter(), **kwds)   # Filtered rows only.
        fn = lambda dic: tuple((k, dic[k]) for k in columns)  # Subset as item-tuples.

        iterable = set(fn(x) for x in iterable)               # Unique.
        iterable = sorted(iterable)                           # Ordered.
        # Explore possible TODOs:
        # replace unique with `unique_everseen` https://docs.python.org/3.4/library/itertools.html
        # remove sorted() call and make sorting optional
        return (dict(item) for item in iterable)              # Make dicts.

    @staticmethod
    def _filtered(iterable, **kwds):
        """Filter iterable by keywords (column=value, etc.)."""
        mktup = lambda v: (v,) if not isinstance(v, (list, tuple)) else v
        kwds = dict((k, mktup(v)) for k, v in kwds.items())
        for row in iterable:
            if all(row[k] in v for k, v in kwds.items()):
                yield row


class SqliteDataSource(BaseDataSource):
    """SQLite data source."""

    def __init__(self, connection, table):
        """Initialize self."""
        self.__name__ = 'SQLite Table {0!r}'.format(table)
        self._connection = connection
        self._table = table

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

    def set(self, column, **kwds):
        """Return set of values in column."""
        assert column in self.columns(), 'No column %r' % column
        select_clause = 'DISTINCT "' + column + '"'
        cursor = self._execute_query(self._table, select_clause, **kwds)
        return set(x[0] for x in cursor)

    def sum(self, column, **kwds):
        """Return sum of values in column."""
        select_clause = 'SUM("' + column + '")'
        cursor = self._execute_query(self._table, select_clause, **kwds)
        return cursor.fetchone()[0]

    def count(self, column, **kwds):
        """Return count of non-empty values in column."""
        select_clause = 'COUNT("' + column +  '")'
        cursor = self._execute_query(self._table, select_clause, **kwds)
        return cursor.fetchone()[0]

    def groups(self, *columns, **kwds):
        """Return sorted iterable of unique dictionaries grouped by given columns."""
        column_names = ['"{0}"'.format(x) for x in columns]
        select_clause = 'DISTINCT ' + ', '.join(column_names)
        trailing_clause = 'ORDER BY ' + ', '.join(column_names)
        cursor = self._execute_query(self._table, select_clause,
                                     trailing_clause, **kwds)
        return (dict(zip(columns, x)) for x in cursor)

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


class CsvDataSource(SqliteDataSource):
    """CSV file data source."""

    def __init__(self, file):
        """Initialize self."""
        if isinstance(file, str):
            # Assume file path.
            if not os.path.isabs(file):
                calling_frame = sys._getframe(1)
                calling_file = inspect.getfile(calling_frame)
                calling_path = os.path.dirname(calling_file)
                file = os.path.join(calling_path, file)

            with open(file) as fh:
                connection = self._setup_database(fh)
        else:
            # Assume file-like object.
            connection = self._setup_database(file)

        SqliteDataSource.__init__(self, connection, 'main')

    @classmethod
    def _setup_database(cls, fh, table='main', in_memory=False):
        path = '' if not in_memory else ':memory:'  # Empty str for temp file.
        connection = sqlite3.connect(path)

        cls._load_csv_file(connection, table, fh)
        return connection

    @classmethod
    def _load_csv_file(cls, connection, table, fh):
        """Load CSV file into default database of given connection."""
        reader = csv.reader(fh)
        csv_header = next(reader)

        cursor = connection.cursor()
        try:
            # Create table.
            statement = cls._build_create_statement(table, csv_header)
            cursor.execute(statement)

            # Insert rows.
            try:
                for row in reader:
                    if not row:
                        continue  # Skip empty rows.
                    statement, params = cls._build_insert_statement(table, row)
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
    """Composite of multiple data source objects."""

    def __init__(self, *sources):
        """Initialize self."""
        for source in sources:
            msg = 'Sources must be derived from BaseDataSource'
            assert isinstance(source, BaseDataSource), msg
        self.sources = sources

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

    def set(self, column, **kwds):
        """Return set of values in column."""
        if column not in self.columns():
            msg = 'No sub-sources not contain {0!r} column.'.format(column)
            raise Exception(msg)

        result_sets = []
        for source in self.sources:
            subcols = source.columns()
            if column in subcols:
                if any(v != '' for k, v in kwds.items() if k not in subcols):
                    continue
                subkwds = dict((k, v) for k, v in kwds.items() if k in subcols)
                result_sets.append(source.set(column, **subkwds))
            else:
                result_sets.append(set(['']))

        return set(itertools.chain(*result_sets))

    def sum(self, column, **kwds):
        """Return sum of values in column."""
        if column not in self.columns():
            msg = 'No sub-sources not contain {0!r} column.'.format(column)
            raise Exception(msg)

        total_result = 0
        for source in self.sources:
            subcols = source.columns()
            if column in subcols:
                if any(v != '' for k, v in kwds.items() if k not in subcols):
                    continue
                subkwds = dict((k, v) for k, v in kwds.items() if k in subcols)
                result = source.sum(column, **subkwds)
                if result:
                    total_result += result

        return total_result

    def count(self, column, **kwds):
        """Return count of non-empty values in column."""
        if column not in self.columns():
            msg = 'No sub-sources not contain {0!r} column.'.format(column)
            raise Exception(msg)

        total_result = 0
        for source in self.sources:
            subcols = source.columns()
            if column in subcols:
                if any(v != '' for k, v in kwds.items() if k not in subcols):
                    continue
                subkwds = dict((k, v) for k, v in kwds.items() if k in subcols)
                total_result += source.count(column, **subkwds)

        return total_result

    #def groups(self, *columns, **kwds):
    #    """Return unsorted iterable of unique dictionaries grouped by given columns."""


#DefaultDataSource = CsvDataSource
