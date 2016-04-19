# -*- coding: utf-8 -*-
import sqlite3

from .test_sources_base import TestBaseSource
from .test_sources_base import TestDataSourceCount

from datatest import SqliteSource


class TestSqliteSourceCount(TestDataSourceCount):
    def setUp(self):
        tablename = 'testtable'
        connection = sqlite3.connect(':memory:')
        cursor = connection.cursor()
        cursor.execute("CREATE TABLE testtable (label1, label2, value)")
        for values in self.testdata:
            cursor.execute("INSERT INTO testtable VALUES (?, ?, ?)", values)
        connection.commit()

        self.datasource = SqliteSource(connection, tablename)


class TestSqliteSource(TestBaseSource):
    def setUp(self):
        tablename = 'testtable'
        connection = sqlite3.connect(':memory:')
        cursor = connection.cursor()
        cursor.execute("CREATE TABLE testtable (label1, label2, value)")
        for values in self.testdata:
            cursor.execute("INSERT INTO testtable VALUES (?, ?, ?)", values)
        connection.commit()

        self.datasource = SqliteSource(connection, tablename)

    def test_where_clause(self):
        # No key-word args.
        clause, params = SqliteSource._build_where_clause()
        self.assertEqual(clause, '')
        self.assertEqual(params, [])

        # Single condition (where label1 equals 'a').
        clause, params = SqliteSource._build_where_clause(label1='a')
        self.assertEqual(clause, 'label1=?')
        self.assertEqual(params, ['a'])

        # Multiple conditions (where label1 equals 'a' AND label2 equals 'x').
        clause, params = SqliteSource._build_where_clause(label1='a', label2='x')
        self.assertEqual(clause, 'label1=? AND label2=?')
        self.assertEqual(params, ['a', 'x'])

        # Compound condition (where label1 equals 'a' OR 'b').
        clause, params = SqliteSource._build_where_clause(label1=('a', 'b'))
        self.assertEqual(clause, 'label1 IN (?, ?)')
        self.assertEqual(params, ['a', 'b'])

        # Mixed conditions (where label1 equals 'a' OR 'b' AND label2 equals 'x').
        clause, params = SqliteSource._build_where_clause(label1=('a', 'b'), label2='x')
        self.assertEqual(clause, 'label1 IN (?, ?) AND label2=?')
        self.assertEqual(params, ['a', 'b', 'x'])

    def test_normalize_column(self):
        result = SqliteSource._normalize_column('foo')
        self.assertEqual('"foo"', result)

        result = SqliteSource._normalize_column('foo bar')
        self.assertEqual('"foo bar"', result)

        result = SqliteSource._normalize_column('foo "bar" baz')
        self.assertEqual('"foo ""bar"" baz"', result)

    def test_from_records(self):
        """Test from_records method (wrapper for TemporarySqliteTable class)."""
        # Test tuples.
        columns = ['foo', 'bar', 'baz']
        data = [
            ('a', 'x', '1'),
            ('b', 'y', '2'),
            ('c', 'z', '3'),
        ]
        source = SqliteSource.from_records(data, columns)

        expected = [
            {'foo': 'a', 'bar': 'x', 'baz': '1'},
            {'foo': 'b', 'bar': 'y', 'baz': '2'},
            {'foo': 'c', 'bar': 'z', 'baz': '3'},
        ]
        self.assertEqual(expected, list(source))

        # Test dict.
        columns = ['foo', 'bar', 'baz']
        data = [
            {'foo': 'a', 'bar': 'x', 'baz': '1'},
            {'foo': 'b', 'bar': 'y', 'baz': '2'},
            {'foo': 'c', 'bar': 'z', 'baz': '3'},
        ]
        source = SqliteSource.from_records(data, columns)
        self.assertEqual(data, list(source))

        # Test omitted *columns* argument.
        data_dict = [
            {'foo': 'a', 'bar': 'x', 'baz': '1'},
            {'foo': 'b', 'bar': 'y', 'baz': '2'},
            {'foo': 'c', 'bar': 'z', 'baz': '3'},
        ]
        source = SqliteSource.from_records(data_dict)
        self.assertEqual(data_dict, list(source))

    def test_create_index(self):
        cursor = self.datasource._connection.cursor()

        # There should be no indexes initially.
        cursor.execute("PRAGMA INDEX_LIST('testtable')")
        self.assertEqual(cursor.fetchall(), [])

        # Add single-column index.
        self.datasource.create_index('label1')  # <- CREATE INDEX!
        cursor.execute("PRAGMA INDEX_LIST('testtable')")
        results = [tup[1] for tup in cursor.fetchall()]
        self.assertEqual(results, ['idx_testtable_label1'])

        # Add multi-column index.
        self.datasource.create_index('label2', 'value')  # <- CREATE INDEX!
        cursor.execute("PRAGMA INDEX_LIST('testtable')")
        results = sorted(tup[1] for tup in cursor.fetchall())
        self.assertEqual(results, ['idx_testtable_label1', 'idx_testtable_label2_value'])

        # Duplicate of first, single-column index should have no effect.
        self.datasource.create_index('label1')  # <- CREATE INDEX!
        cursor.execute("PRAGMA INDEX_LIST('testtable')")
        results = sorted(tup[1] for tup in cursor.fetchall())
        self.assertEqual(results, ['idx_testtable_label1', 'idx_testtable_label2_value'])
