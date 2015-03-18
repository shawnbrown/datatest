# -*- coding: utf-8 -*-
import collections
import csv
import sqlite3
from decimal import Decimal


#pattern = 'test*.py'
prefix = 'test_'


class BaseDataSource(object):
    """ """
    def __init__(self):
        """."""
        return NotImplemented

    def slow_iter(self):
        """Return iterator that yields dictionary rows."""
        return NotImplemented

    def columns(self):
        """Return list of column names."""
        return NotImplemented

    def set(self, column, **kwds):
        """Return set of column values."""
        iterable = self._filtered(self.slow_iter(), **kwds)
        return set(x[column] for x in iterable)

    def sum(self, column, **kwds):
        """Return sum of column values."""
        iterable = self._filtered(self.slow_iter(), **kwds)
        iterable = (x for x in iterable if x)
        return sum(Decimal(x[column]) for x in iterable)

    def count(self, column, **kwds):
        """Return count of non-empty column values."""
        iterable = self._filtered(self.slow_iter(), **kwds)
        return sum(bool(x[column]) for x in iterable)

    def groups(self, *columns, **kwds):
        """Return unique collection of dicts containing column/value pairs."""
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
        """Filter iterable by keywords (col_name=col_value, etc.)."""
        mktup = lambda v: (v,) if not isinstance(v, (list, tuple)) else v
        #kwds = {k: mktup(v) for k, v in kwds.items()}
        kwds = dict((k, mktup(v)) for k, v in kwds.items())
        for row in iterable:
            if all(row[k] in v for k, v in kwds.items()):
                yield row


class SqliteDataSource(BaseDataSource):
    def __init__(self, connection, table):
        self.__name__ = 'SQLite Table {0!r}'.format(table)
        self._connection = connection
        self._table = table

    #def slow_iter(self):
    #    """Return iterator that yields dictionary values."""
    #    cursor = self._connection.cursor()
    #    cursor.execute('SELECT * FROM ' + self._table)
    #    column_names = self.columns()
    #    mkdict = lambda x: dict(zip(column_names, x))
    #    return (mkdict(row) for row in cursor.fetchall())

    def columns(self):
        """Return list of column names."""
        cursor = self._connection.cursor()
        cursor.execute('PRAGMA table_info(' + self._table + ')')
        return [x[1] for x in cursor.fetchall()]

    def set(self, column, **kwds):
        """Return set of column values."""
        assert column in self.columns(), 'No column %r' % column
        select_clause = 'DISTINCT "' + column + '"'
        cursor = self._execute_query(self._table, select_clause, **kwds)
        return set(x[0] for x in cursor)

    def sum(self, column, **kwds):
        """Return sum of column values."""
        select_clause = 'SUM("' + column + '")'
        cursor = self._execute_query(self._table, select_clause, **kwds)
        return cursor.fetchone()[0]

    def count(self, column, **kwds):
        """Return count of non-empty column values."""
        select_clause = 'COUNT("' + column +  '")'
        cursor = self._execute_query(self._table, select_clause, **kwds)
        return cursor.fetchone()[0]

    def groups(self, *columns, **kwds):
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
    def __init__(self, file):
        if isinstance(file, str):
            # Use string as file path.
            # TODO: Make sure relative path is relative to calling module.
            with open(file) as fh:
                connection = self._setup_database(fh)
        else:
            # Assume file-like object.
            connection = self._setup_database(file)

        #super().__init__(connection, 'main')
        SqliteDataSource.__init__(self, connection, 'main')

        """
        def setUpModule():
            global subjectData, trustedData
            subjectData = CsvDataSource('ny12precinct-votes.csv')
            trustedData = CsvDataSource('ny12county-votes.csv')

        class TestCountyTotals(DataTestCase):
            pass

        class TestFile(DataTestCase):
            @classmethod
            self setUpClass(cls):
                cls.subjectData = CsvDataSource('ny12precinct-votes.csv')
                cls.trustedData = CsvDataSource('ny12county-votes.csv')

            def test_counties(self):
                #trusted = self.trustedData.columns()
                #subject = self.subjectData.columns()
                #self.assertEqual(trusted, subject)
                self.assertDataColumns('county')

            def test_offices(self):
                self.assertDataSet('office')

                #self.assertDataSubset('office')
                #self.assertDataSuperset('office')

            def test_pres(self):
                self.assertDataSums('votes', ['county', 'party'], office='pres')

            def test_ushse(self):
                global subjectData, trustedData
                self.assertEqual(subjectData.sum('votes', office='pres'), 17342)

                self.assertDataSums('votes',
                                    groupby=['county', 'cd', 'party'],
                                    office='ushse')

        """


    #def __del__(self):
    #    # If file was opened by init, then close it on del.
    #    if self._internal_fh:
    #        self._internal_fh.close()

    #def slow_iter(self):
    #    """Return iterator that yields dictionary values."""
    #    self._file.seek(0)
    #    return csv.DictReader(self._file)

    #def columns(self):
    #    """Return list of column names."""
    #    return self.slow_iter().fieldnames

    @classmethod
    def _setup_database(cls, fh, table='main', in_memory=False):
        path = '' if not in_memory else ':memory:'  # Empty str for temp file.
        connection = sqlite3.connect(path)

        cls._load_csv_file(connection, table, fh)
        return connection

    @classmethod
    def _load_csv_file(cls, connection, table, fh):
        """Loads CSV file into default database of given connection."""
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
        """Returns a CREATE TABLE statement."""
        cls._assert_unique(columns)
        columns = [cls._normalize_column(x) for x in columns]
        return 'CREATE TABLE %s (%s)' % (table, ', '.join(columns))

    @staticmethod
    def _build_insert_statement(table, row):
        """Returns an INSERT INTO statement."""
        statement = 'INSERT INTO ' + table + ' VALUES (' + ', '.join(['?'] * len(row)) + ')'
        parameters = row
        return statement, parameters

    @staticmethod
    def _normalize_column(name):
        """Normalize value for use as a SQLite column name."""
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


#DefaultDataSource = CsvDataSource
