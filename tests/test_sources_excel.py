# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
from . import _unittest as unittest
from .mixins import OtherTests
from .mixins import CountTests

try:
    import xlrd
except ImportError:
    xlrd = None

from datatest.sources.excel import ExcelSource

workbook_path = os.path.join(os.path.dirname(__file__), 'test_sources_excel.xlsx')


@unittest.skipIf(xlrd is None, 'xlrd not found')
class TestExcelSource(OtherTests, unittest.TestCase):
    def setUp(self):
        global workbook_path
        self.datasource = ExcelSource(workbook_path)  # <- Defaults to "Sheet 1"


@unittest.skipIf(xlrd is None, 'xlrd not found')
class TestExcelSourceCount(unittest.TestCase):
#class TestExcelSourceCount(CountTests, unittest.TestCase):
    def setUp(self):
        global workbook_path
        self.datasource = ExcelSource(workbook_path, 'count_data')

    def test_count(self):
        count = self.datasource.count

        self.assertEqual(9, count('label1'))

        expected = {'a': 4, 'b': 5}
        result = count('label1', ['label1'])
        self.assertEqual(expected, result)

        expected = {'a': 3, 'b': 3}  # Counts only truthy values (not '' or None).
        result = count('label2', ['label1'])
        self.assertEqual(expected, result)

        expected = {
            ('a', 'x'): 2,
            ('a', 'y'): 1,
            ('a', ''): 1,
            ('b', 'z'): 1,
            ('b', 'y'): 1,
            ('b', 'x'): 1,
            #('b', None): 1,  # <- None value has no equivalent in XLSX file.
            #('b', ''): 1,
            ('b', ''): 2,
        }
        result = count('label1', ['label1', 'label2'])
        self.assertEqual(expected, result)

        expected = {'x': 2, 'y': 1, '': 1}
        result = count('label1', 'label2', label1='a')
        self.assertEqual(expected, result)
