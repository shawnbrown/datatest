# -*- coding: utf-8 -*-
"""Temporary SQLite table loader and manager."""
from __future__ import absolute_import
import itertools
import sqlite3
from .csvreader import UnicodeCsvReader
from ..utils.misc import _is_nscontainer


# Default connection shared by TemporarySqliteTable instances.
_sqltemp_shared_connection = sqlite3.connect('')


def _get_columns_from_data(data):
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
    return columns, data


class _TransactionSyncOff(object):
    """Context manager to handle a single transaction that sets
    synchronous=OFF temporarily and restores it's original value on
    completion::

        with _TransactionSyncOff(connection) as cursor:
            ...

    .. note::

        This context manager is intended for use with temporary SQLite
        databases in a single execution thread (like the ones used
        internally by TemporarySqliteTable. Transactions are run with
        synchronous=OFF for speed and since the databases are temporary,
        long-term integrity is not a concern. In the unlikely event of
        data corruption, it is entirely acceptable to simply rebuild
        the temporary table.
    """
    def __init__(self, connection):
        self.connection = connection
        self._cursor = None
        self._isolation_level = None
        self._synchronous = None

    def __enter__(self):
        cursor = self.connection.cursor()
        self._cursor = cursor

        # Set isolation_level to None for explicit transaction control.
        self._isolation_level = self.connection.isolation_level
        self.connection.isolation_level = None

        # Set synchronous=OFF for faster loading.
        self._synchronous = cursor.execute("PRAGMA synchronous").fetchone()[0]
        cursor.execute('PRAGMA synchronous=OFF')

        cursor.execute('BEGIN TRANSACTION')
        return cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.connection.commit()  # <- COMMIT!
        else:
            self.connection.rollback()  # <- ROLLBACK!

        self._cursor.execute('PRAGMA synchronous={0}'.format(self._synchronous))
        self.connection.isolation_level = self._isolation_level


class TemporarySqliteTable(object):
    """Creates a temporary SQLite table and inserts given data."""
    def __init__(self, data, columns=None, connection=None):
        """Initialize self."""
        global _sqltemp_shared_connection
        if not connection:
            connection = _sqltemp_shared_connection

        if not columns:
            columns, data = _get_columns_from_data(data)

        with _TransactionSyncOff(connection) as cursor:
            table = self._get_new_table_name(cursor)
            self._create_table(cursor, table, columns)
            self._insert_data(cursor, table, columns, data)

        # Assign class properties.
        self._connection = connection
        self._name = table

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
        cursor = self._connection.cursor()
        cursor.execute('PRAGMA table_info(' + self._name + ')')
        return [x[1] for x in cursor.fetchall()]

    def drop(self):
        """Drops temporary table from database."""
        cursor = self.connection.cursor()
        cursor.execute('DROP TABLE IF EXISTS ' + self.name)

    @staticmethod
    def _get_existing_tables(cursor):
        """Takes sqlite3 *cursor*, returns existing temporary table
        names.
        """
        #cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        cursor.execute("SELECT name FROM sqlite_temp_master WHERE type='table'")
        return [x[0] for x in cursor]

    @staticmethod
    def _make_new_table(existing):
        """Takes a list of *existing* table names and returns a new,
        unique table name (tbl0, tbl1, tbl2, etc.).
        """
        prefix = 'tbl'
        numbers = [x[len(prefix):] for x in existing if x.startswith(prefix)]
        numbers = [int(x) for x in numbers if x.isdigit()]
        if numbers:
            table_num = max(numbers) + 1
        else:
            table_num = 0
        return prefix + str(table_num)

    @classmethod
    def _get_new_table_name(cls, cursor):
        existing_tables = cls._get_existing_tables(cursor)
        name = cls._make_new_table(existing_tables)
        return name

    @classmethod
    def _create_table_statement(cls, table, columns):
        """Return 'CREATE TEMPORARY TABLE' statement."""
        cls._assert_unique(columns)
        columns = [cls._normalize_column(x) for x in columns]
        #return 'CREATE TABLE %s (%s)' % (table, ', '.join(columns))
        return 'CREATE TEMPORARY TABLE %s (%s)' % (table, ', '.join(columns))

    @classmethod
    def _create_table(cls, cursor, table, columns):
        try:
            statement = cls._create_table_statement(table, columns)
            cursor.execute(statement)
        except Exception as e:
            if isinstance(e, UnicodeDecodeError):
                e.reason += '\n{0}'.format(statement)
                raise e
            raise e.__class__('{0}\n{1}'.format(e, statement))

    @classmethod
    def _insert_data(cls, cursor, table, columns, data):
        data_iter = iter(data)
        try:
            first_row = next(data_iter)
        except StopIteration:
            return  # <- EXIT! No data to insert.
        data_iter = itertools.chain([first_row], data_iter)

        if isinstance(first_row, dict):
            get_values = lambda row: tuple(row[col] for col in columns)
            data_iter = (get_values(row) for row in data_iter)

        statement = 'INSERT INTO {0} ({1}) VALUES ({2})'.format(
            table,
            ', '.join(cls._normalize_column(col) for col in columns),
            ', '.join(['?'] * len(columns)),
        )
        cursor.executemany(statement, data_iter)

        # TODO (2017-01-22): Remove the following section if the above
        # code proves stable for a few weeks on our in-house staging
        # server.
        #
        #for row in data:  # Insert all rows.
        #    if isinstance(row, dict):
        #        row = tuple(row[x] for x in columns)
        #    statement, params = cls._insert_into_statement(table, row)
        #    try:
        #        cursor.execute(statement, params)
        #    except Exception as e:
        #        exc_cls = e.__class__
        #        msg = ('\n'
        #               '    row -> %s\n'
        #               '    sql -> %s\n'
        #               ' params -> %s') % (row, statement, params)
        #        msg = str(e).strip() + msg
        #        raise exc_cls(msg)

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


class TemporarySqliteTableForCsv(TemporarySqliteTable):
    """."""
    @classmethod
    def _create_table_statement(cls, table, columns):
        """Includes added default-to-empty-string clause for columns."""
        cls._assert_unique(columns)
        columns = [cls._normalize_column(x) for x in columns]
        columns = ["{0} DEFAULT ''".format(col) for col in columns]
        return 'CREATE TEMPORARY TABLE %s (%s)' % (table, ', '.join(columns))

    def _concatenate_data(self, data, columns):
        if not columns:
            columns, data = _get_columns_from_data(data)

        with _TransactionSyncOff(self._connection) as cursor:
            existing_cols = self.columns
            missing_cols = [x for x in columns if x not in existing_cols]
            for column in missing_cols:
                statement = "ALTER TABLE {0} ADD COLUMN {1} DEFAULT ''"
                cursor.execute(statement.format(self._name, column))

            self._insert_data(cursor, self._name, columns, data)


def _from_csv(file, encoding=None, **fmtparams):
    """ """
    if not _is_nscontainer(file):
        file = [file]
    first_file = file[0]
    other_files = file[1:]

    with UnicodeCsvReader(first_file, encoding='utf-8', **fmtparams) as reader:
        columns = next(reader)  # Header row.
        temptable = TemporarySqliteTableForCsv(reader, columns)

    for f in other_files:
        with UnicodeCsvReader(f, encoding='utf-8', **fmtparams) as reader:
            columns = next(reader)  # Header row.
            temptable._concatenate_data(reader, columns)

    return temptable
