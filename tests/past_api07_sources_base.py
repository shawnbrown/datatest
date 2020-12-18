# -*- coding: utf-8 -*-
from . import _unittest as unittest

from datatest.__past__.api07_sources import MinimalSource
from .mixins import OtherTests
from .mixins import CountTests


class TestBaseSource(OtherTests, unittest.TestCase):
    fieldnames = ['label1', 'label2', 'value']
    testdata = [['a', 'x', '17'],
                ['a', 'x', '13'],
                ['a', 'y', '20'],
                ['a', 'z', '15'],
                ['b', 'z', '5' ],
                ['b', 'y', '40'],
                ['b', 'x', '25']]

    def setUp(self):
        self.datasource = MinimalSource(self.testdata, self.fieldnames)


class TestDataSourceCount(CountTests, unittest.TestCase):
    def setUp(self):
        """Define self.datasource (base version uses MinimalSource)."""
        self.datasource = MinimalSource(self.testdata, self.fieldnames)
