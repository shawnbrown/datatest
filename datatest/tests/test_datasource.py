# -*- coding: utf-8 -*-
import csv
import sqlite3
import sys
import unittest

import datatest.tests._io as io
#import datatest.tests._unittest as unittest
import unittest

from datatest.datasource import BaseDataSource
from datatest.datasource import SqliteDataSource
from datatest.datasource import CsvDataSource


class TestBaseDataSource(unittest.TestCase):
    fieldnames = ['label1', 'label2', 'value']
    testdata = [['a', 'x', '17'],
                ['a', 'x', '13'],
                ['a', 'y', '20'],
                ['a', 'z', '15'],
                ['b', 'z', '5' ],
                ['b', 'y', '40'],
                ['b', 'x', '25']]

    def setUp(self):
        """Define and instantiate a minimal data source."""
        class MinimalDataSource(BaseDataSource):
            def __init__(self, data, fieldnames):
                self._data = data
                self._fieldnames = fieldnames

            def slow_iter(self):
                for row in self._data:
                    yield dict(zip(self._fieldnames, row))

            def columns(self):
                return self._fieldnames

        self.datasource = MinimalDataSource(self.testdata, self.fieldnames)

    def test_slow_iter(self):
        """Test slow iterator."""
        results = self.datasource.slow_iter()
        if results == NotImplemented:
            return  # <- EXIT!

        results = list(results)
        expected = [
            {'label1': 'a', 'label2': 'x', 'value': '17'},
            {'label1': 'a', 'label2': 'x', 'value': '13'},
            {'label1': 'a', 'label2': 'y', 'value': '20'},
            {'label1': 'a', 'label2': 'z', 'value': '15'},
            {'label1': 'b', 'label2': 'z', 'value': '5' },
            {'label1': 'b', 'label2': 'y', 'value': '40'},
            {'label1': 'b', 'label2': 'x', 'value': '25'},
        ]
        self.assertEqual(results, expected)

    def test_filter_iter(self):
        """Test filter iterator."""
        testdata = [dict(zip(self.fieldnames, x)) for x in self.testdata]

        # Filter by single value (where label1 is 'a').
        results = self.datasource._filtered(testdata, label1='a')
        results = list(results)
        expected = [
            {'label1': 'a', 'label2': 'x', 'value': '17'},
            {'label1': 'a', 'label2': 'x', 'value': '13'},
            {'label1': 'a', 'label2': 'y', 'value': '20'},
            {'label1': 'a', 'label2': 'z', 'value': '15'},
        ]
        self.assertEqual(results, expected)

        # Filter by multiple values (where label2 is 'x' OR 'y').
        results = self.datasource._filtered(testdata, label2=['x', 'y'])
        results = list(results)
        expected = [
            {'label1': 'a', 'label2': 'x', 'value': '17'},
            {'label1': 'a', 'label2': 'x', 'value': '13'},
            {'label1': 'a', 'label2': 'y', 'value': '20'},
            {'label1': 'b', 'label2': 'y', 'value': '40'},
            {'label1': 'b', 'label2': 'x', 'value': '25'},
        ]
        self.assertEqual(results, expected)

        # Filter by multiple columns (where label1 is 'a', label2 is 'x' OR 'y').
        results = self.datasource._filtered(testdata,
                                            label1='a', label2=['x', 'y'])
        results = list(results)
        expected = [
            {'label1': 'a', 'label2': 'x', 'value': '17'},
            {'label1': 'a', 'label2': 'x', 'value': '13'},
            {'label1': 'a', 'label2': 'y', 'value': '20'},
        ]
        self.assertEqual(results, expected)

    def test_columns(self):
        header = self.datasource.columns()
        self.assertEqual(header, ['label1', 'label2', 'value'])

    def test_set(self):
        result = self.datasource.set('label1')
        self.assertEqual(result, set(['a', 'b']))

        result = self.datasource.set('value', label2='x')
        self.assertEqual(result, set(['17', '13', '25']))

    def test_sum(self):
        result = self.datasource.sum('value')
        self.assertEqual(result, 135)

        result = self.datasource.sum('value', label1='a')
        self.assertEqual(result, 65)

    def test_count(self):
        result = self.datasource.count('value')
        self.assertEqual(result, 7)

        result = self.datasource.count('value', label2='x')
        self.assertEqual(result, 3)

    def test_groups(self):
        # Test single column.
        result = self.datasource.groups('label1')
        expected = [{'label1': 'a'}, {'label1': 'b'}]
        result_set = set(tuple(x.items()) for x in result)
        expected_set = set(tuple(x.items()) for x in expected)
        self.assertEqual(result_set, expected_set)

        # Test multiple columns.
        result = self.datasource.groups('label1', 'label2')
        expected = [{'label1': 'a', 'label2': 'x'},
                    {'label1': 'a', 'label2': 'y'},
                    {'label1': 'a', 'label2': 'z'},
                    {'label1': 'b', 'label2': 'x'},  # <- expect ordered.
                    {'label1': 'b', 'label2': 'y'},  # <- expect ordered.
                    {'label1': 'b', 'label2': 'z'},  # <- expect ordered.
                   ]
        result = [tuple(x.items()) for x in result]
        expected = [tuple(x.items()) for x in expected]
        self.assertEqual(result, expected)

        # Test multiple columns with filter.
        result = self.datasource.groups('label1', 'label2', label2=['x', 'y'])
        expected = [{'label1': 'a', 'label2': 'x'},
                    {'label1': 'a', 'label2': 'y'},
                    {'label1': 'b', 'label2': 'x'},
                    {'label1': 'b', 'label2': 'y'}]
        result_set = set(tuple(x.items()) for x in result)
        expected_set = set(tuple(x.items()) for x in expected)
        self.assertEqual(result_set, expected_set)


class TestSqliteDataSource(TestBaseDataSource):
    def setUp(self):
        tablename = 'testtable'
        connection = sqlite3.connect(':memory:')
        cursor = connection.cursor()
        cursor.execute("CREATE TABLE testtable (label1, label2, value)")
        for values in self.testdata:
            cursor.execute("INSERT INTO testtable VALUES (?, ?, ?)", values)
        connection.commit()

        self.datasource = SqliteDataSource(connection, tablename)

    def test_where_clause(self):
        # No key-word args.
        clause, params = SqliteDataSource._build_where_clause()
        self.assertEqual(clause, '')
        self.assertEqual(params, [])

        # Single condition (where label1 equals 'a').
        clause, params = SqliteDataSource._build_where_clause(label1='a')
        self.assertEqual(clause, 'label1=?')
        self.assertEqual(params, ['a'])

        # Multiple conditions (where label1 equals 'a' AND label2 equals 'x').
        clause, params = SqliteDataSource._build_where_clause(label1='a', label2='x')
        self.assertEqual(clause, 'label1=? AND label2=?')
        self.assertEqual(params, ['a', 'x'])

        # Compound condition (where label1 equals 'a' OR 'b').
        clause, params = SqliteDataSource._build_where_clause(label1=('a', 'b'))
        self.assertEqual(clause, 'label1 IN (?, ?)')
        self.assertEqual(params, ['a', 'b'])

        # Mixed conditions (where label1 equals 'a' OR 'b' AND label2 equals 'x').
        clause, params = SqliteDataSource._build_where_clause(label1=('a', 'b'), label2='x')
        self.assertEqual(clause, 'label1 IN (?, ?) AND label2=?')
        self.assertEqual(params, ['a', 'b', 'x'])


class TestCsvDataSource(TestBaseDataSource):
    def setUp(self):
        fh = self._make_csv_file()
        self.datasource = CsvDataSource(fh)

    def _make_csv_file(self):
        """Build CSV file from source data (self.testdata)."""
        init_string = []
        init_string.append(','.join(self.fieldnames)) # Concat cells into row.
        for row in self.testdata:
            init_string.append(','.join(row)) # Concat cells into row.
        init_string = '\n'.join(init_string)  # Concat rows into final string.
        return io.StringIO(init_string)

    def test_empty_file(self):
        pass
        #file exists but is empty should fail, too!


#src = CsvDataSource(file=self._source_data)
#self.assertEqual(src._file, self._source_data)

# Test filename.
#trustedsource
#datasource
#trusted_datasource
#suspect_datasource
#suspect_datasource

#src = CsvDataSource(file='somefile.csv')
#trusted
#suspect
#self.assertEqual(src._file, self._source_data)

#self.assertSums(suspectsource, trustedsource, quantity='votes', groupby=['county', 'party'], office='pres')

#self.assertDataSum('votes', ['county', 'party'], office='pres')
#self.assertDataSum('votes', ['county', 'party'], office='ussen')
#self.assertDataSum('votes', ['county', 'party', 'cd'], office='ushse')
#self.assertDataSum('votes', ['county', 'party', 'stsen'], office='stsen')
#self.assertDataSum('votes', ['county', 'party', 'sthse'], office='sthse')

