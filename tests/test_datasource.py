# -*- coding: utf-8 -*-
from . import _unittest as unittest
from datatest.utils.collections import Iterable

from datatest.sources.datasource import DataSource
from datatest.sources.datasource import ResultSequence


class TestResultSequence(unittest.TestCase):
    def test_repr(self):
        sequence = ResultSequence([1, 2, 3, 4, 5])
        sequence_repr = repr(sequence)

        expected = 'ResultSequence([1, 2, 3, 4, 5])'
        self.assertEqual(sequence_repr, expected)

    def test_iter(self):
        sequence = ResultSequence([1, 2, 3, 4, 5])

        as_iter = iter(sequence)
        self.assertIsInstance(as_iter, Iterable)

        as_list = [x for x in sequence]
        self.assertEqual(as_list, [1, 2, 3, 4, 5])

    def test_map(self):
        sequence = ResultSequence([1, 2, 3, 4, 5])

        sequence = sequence.map(lambda x: x * 2)
        self.assertIsInstance(sequence, ResultSequence)

        as_list = list(sequence)
        self.assertEqual(as_list, [2, 4, 6, 8, 10])

    def test_map_multiple_args(self):
        sequence = ResultSequence([(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)])

        # Using a function of one argument.
        function = lambda x: '{0}-{1}'.format(x[0], x[1])
        as_list = list(sequence.map(function))
        self.assertEqual(as_list, ['1-1', '2-2', '3-3', '4-4', '5-5'])

        # Using a function of two arguments.
        function = lambda x, y: '{0}-{1}'.format(x, y)
        as_list = list(sequence.map(function))
        self.assertEqual(as_list, ['1-1', '2-2', '3-3', '4-4', '5-5'])

    def test_reduce(self):
        sequence = ResultSequence([2, 2, 2, 2, 2])
        multiply = lambda x, y: x * y
        result = sequence.reduce(multiply)
        self.assertEqual(result, 32)


class SqliteHelper(unittest.TestCase):
    """Helper class for testing DataSource parity with SQLite behavior."""
    @staticmethod
    def sqlite3_aggregate(function_name, values):
        """Test SQLite3 aggregation function on list of values."""
        assert function_name in ('AVG', 'COUNT', 'GROUP_CONCAT', 'MAX', 'MIN', 'SUM', 'TOTAL')
        values = [[x] for x in values]  # Wrap as single-column rows.
        temptable = TemporarySqliteTable(values, ['values'])

        cursor = temptable.connection.cursor()
        table = temptable.name
        query = 'SELECT {0}("values") FROM {1}'.format(function_name, table)
        cursor.execute(query)

        result = cursor.fetchall()[0][0]
        cursor.close()
        return result


class TestDataSourceBasics(unittest.TestCase):
    def setUp(self):
        columns = ['label1', 'label2', 'value']
        data = [['a', 'x', '17'],
                ['a', 'x', '13'],
                ['a', 'y', '20'],
                ['a', 'z', '15'],
                ['b', 'z', '5' ],
                ['b', 'y', '40'],
                ['b', 'x', '25']]
        self.source = DataSource(data, columns)

    def test_columns(self):
        expected = ['label1', 'label2', 'value']
        self.assertEqual(self.source.columns(), expected)

    def test_iter(self):
        """Test __iter__."""
        result = [row for row in self.source]
        expected = [
            {'label1': 'a', 'label2': 'x', 'value': '17'},
            {'label1': 'a', 'label2': 'x', 'value': '13'},
            {'label1': 'a', 'label2': 'y', 'value': '20'},
            {'label1': 'a', 'label2': 'z', 'value': '15'},
            {'label1': 'b', 'label2': 'z', 'value': '5' },
            {'label1': 'b', 'label2': 'y', 'value': '40'},
            {'label1': 'b', 'label2': 'x', 'value': '25'},
        ]
        self.assertEqual(expected, result)

    def test_select(self):
        result = self.source('label1')
        expected = [
            'a',
            'a',
            'a',
            'a',
            'b',
            'b',
            'b',
        ]
        self.assertEqual(list(result), expected)

        result = self.source('label1', 'label2')
        expected = [
            ('a', 'x'),
            ('a', 'x'),
            ('a', 'y'),
            ('a', 'z'),
            ('b', 'z'),
            ('b', 'y'),
            ('b', 'x'),
        ]
        self.assertEqual(list(result), expected)

        result = self.source(['label1'], 'value')
        expected = {
            'a': [
                '17',
                '13',
                '20',
                '15',
            ],
            'b': [
                '5',
                '40',
                '25',
            ],
        }
        self.assertEqual(result, expected)

        result = self.source(['label1'], 'label2', 'value')
        expected = {
            'a': [
                ('x', '17'),
                ('x', '13'),
                ('y', '20'),
                ('z', '15'),
            ],
            'b': [
                ('z', '5'),
                ('y', '40'),
                ('x', '25'),
            ],
        }
        self.assertEqual(result, expected)

        result = self.source(['label1', 'label2'], 'value')
        expected = {
            ('a', 'x'): ['17', '13'],
            ('a', 'y'): ['20'],
            ('a', 'z'): ['15'],
            ('b', 'z'): ['5'],
            ('b', 'y'): ['40'],
            ('b', 'x'): ['25'],
        }
        self.assertEqual(result, expected)

        result = self.source(['label1', 'label2'], 'label2', 'value')
        expected = {
            ('a', 'x'): [('x', '17'), ('x', '13')],
            ('a', 'y'): [('y', '20')],
            ('a', 'z'): [('z', '15')],
            ('b', 'z'): [('z', '5')],
            ('b', 'y'): [('y', '40')],
            ('b', 'x'): [('x', '25')],
        }
        self.assertEqual(result, expected)

        msg = 'Support for nested dictionaries removed (for now).'
        with self.assertRaises(Exception, msg=msg):
            self.source(['label1'], ['label2'], 'value')
