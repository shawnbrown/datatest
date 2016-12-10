# -*- coding: utf-8 -*-
from . import _unittest as unittest
from datatest.sources.datasource import DataSource


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
        expected = ['a', 'a', 'a', 'a', 'b', 'b', 'b']
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

        expected = {
            'a': ['17', '13', '20', '15'],
            'b': ['5', '40', '25'],
        }
        result = self.source(['label1'], 'value')
        self.assertEqual(result, expected)
