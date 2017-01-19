# -*- coding: utf-8 -*-
"""Temporary SQLite table loader and manager."""
from __future__ import absolute_import
import itertools
import sqlite3


class TemporarySqliteTable(object):
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
