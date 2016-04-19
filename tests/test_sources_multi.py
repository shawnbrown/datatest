# -*- coding: utf-8 -*-
from . import _io as io
from . import _unittest as unittest
from .test_sources_base import TestBaseSource
from .test_sources_base import MinimalSource
from .test_sources_csv import _make_csv_file

from datatest import CsvSource
from datatest import MultiSource


class TestMultiSource(TestBaseSource):
    def setUp(self):
        fieldnames1 = ['label1', 'label2', 'value']
        testdata1 = [['a', 'x', '17'],
                     ['a', 'x', '13'],
                     ['a', 'y', '20'],
                     ['a', 'z', '15']]

        fieldnames2 = ['label1', 'label2', 'value']
        testdata2 = [['b', 'z', '5' ],
                     ['b', 'y', '40'],
                     ['b', 'x', '25']]

        source1 = MinimalSource(testdata1, fieldnames1)
        source2 = MinimalSource(testdata2, fieldnames2)
        self.datasource = MultiSource(source1, source2)

    def test_sum_heterogeneous_columns(self):
        testdata1 = [['a', 'x', '1'],
                     ['a', 'y', '1']]
        src1 = MinimalSource(testdata1, ['label1', 'label2', 'value'])

        testdata2 = [['a', '5', '1'],
                     ['b', '5', '1'],
                     ['b', '5', '1']]
        src2 = MinimalSource(testdata2, ['label1', 'altval', 'value'])
        source = MultiSource(src1, src2)

        self.assertEqual(5, source.sum('value'))

        expected = {'a': 3, 'b': 2}
        self.assertEqual(expected, source.sum('value', 'label1'))

        expected = {'a': 5, 'b': 10}
        self.assertEqual(expected, source.sum('altval', 'label1'))

        expected = {'a': 1}
        self.assertEqual(expected, source.sum('value', 'label1', label2='x'))

    def test_count_heterogeneous_columns(self):
        testdata1 = [['a', 'x', '2'],
                     ['a', 'y', '2']]
        src1 = MinimalSource(testdata1, ['label1', 'label2', 'value'])

        testdata2 = [['a', '5', '2'],
                     ['b', '5', '2'],
                     ['b', '5', '2']]
        src2 = MinimalSource(testdata2, ['label1', 'altval', 'value'])
        source = MultiSource(src1, src2)

        expected = {'a': 3, 'b': 2}
        self.assertEqual(expected, source.count('label1', 'label1'))

        expected = {'a': 1}
        self.assertEqual(expected, source.count('label1', 'label1', label2='x'))


class TestMixedMultiSource(TestBaseSource):
    """Test MultiSource with sub-sources of different types."""
    def setUp(self):
        fieldnames1 = ['label1', 'label2', 'value']
        testdata1 = [['a', 'x', '17'],
                     ['a', 'x', '13'],
                     ['a', 'y', '20'],
                     ['a', 'z', '15']]
        minimal_source = MinimalSource(testdata1, fieldnames1)

        fieldnames2 = ['label1', 'label2', 'value']
        testdata2 = [['b', 'z', '5' ],
                     ['b', 'y', '40'],
                     ['b', 'x', '25']]
        fh = _make_csv_file(fieldnames2, testdata2)
        csv_source = CsvSource(fh)

        self.datasource = MultiSource(minimal_source, csv_source)


class TestMultiSourceDifferentColumns(unittest.TestCase):
    """Test MultiSource with sub-sources that use different columns."""
    def setUp(self):
        fieldnames1 = ['label1', 'label2', 'value']
        testdata1 = [['a',            'x',    '17'],
                     ['a',            'x',    '13'],
                     ['a',            'y',    '20'],
                     ['b',            'z',     '5']]

        fieldnames2 = ['label1', 'label3', 'value', 'other_value']
        testdata2 = [['a',          'zzz',    '15',           '3'],
                     ['b',          'yyy',     '4',            ''],
                     ['b',          'xxx',     '2',           '2']]

        subsrc1 = MinimalSource(testdata1, fieldnames1)
        subsrc2 = MinimalSource(testdata2, fieldnames2)
        self.datasource = MultiSource(subsrc1, subsrc2)

    def test_combined_columns(self):
        expected = ['label1', 'label2', 'value', 'label3', 'other_value']
        result = self.datasource.columns()
        self.assertSetEqual(set(expected), set(result))

    def test_kwds_filter(self):
        # Filtered value spans sub-sources.
        expected = ['17', '13', '20', '15']
        result = self.datasource.distinct('value', label1='a')
        self.assertEqual(expected, result)

        # Filter column exists in only one sub-source.
        expected = ['17', '13']
        result = self.datasource.distinct('value', label1='a', label2='x')
        self.assertEqual(expected, result)


class TestMultiSourceDifferentColumns2(unittest.TestCase):
    """Test MultiSource with sub-sources that use different columns."""
    def setUp(self):
        fieldnames1 = ['label1', 'label2', 'value']
        testdata1 = [['a',            'x',    '17'],
                     ['a',            'x',    '13'],
                     ['a',            'y',    '20'],
                     ['b',            'z',     '5']]

        fieldnames2 = ['label1', 'label3', 'value', 'other_value']
        testdata2 = [['a',          'zzz',    '15',           '3'],
                     ['b',          'yyy',     '4',           '0'],
                     ['b',          'xxx',     '2',           '2']]

        subsrc1 = MinimalSource(testdata1, fieldnames1)
        subsrc2 = MinimalSource(testdata2, fieldnames2)
        self.datasource = MultiSource(subsrc1, subsrc2)

    def test_distinct_missing_columns(self):
        distinct = self.datasource.distinct

        expected = ['', '3', '0', '2']
        self.assertEqual(expected, distinct('other_value'))
        self.assertEqual(expected, distinct(['other_value']))

        expected = [('',), ('3',), ('0',), ('2',)]
        self.assertEqual(expected, distinct('other_value'))
        self.assertEqual(expected, distinct(['other_value']))

        expected = ['3']
        self.assertEqual(expected, distinct('other_value', label3='zzz'))

        expected = ['']
        self.assertEqual(expected, distinct('other_value', label3=''))

        expected = ['']
        self.assertEqual(expected, distinct('other_value', label2='x'))

        expected = [('a', 'x'), ('a', 'y'), ('b', 'z'), ('a', ''), ('b', '')]
        self.assertEqual(expected, distinct(['label1', 'label2']))
