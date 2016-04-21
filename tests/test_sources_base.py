# -*- coding: utf-8 -*-
from . import _io as io
from . import _unittest as unittest

from .mixins import OtherTests
from .mixins import CountTests

from datatest import BaseSource


class MinimalSource(BaseSource):
    """Minimal data source implementation for testing."""
    def __init__(self, data, fieldnames):
        self._data = data
        self._fieldnames = fieldnames

    def __repr__(self):
        return self.__class__.__name__ + '(<data>, <fieldnames>)'

    def __iter__(self):
        for row in self._data:
            yield dict(zip(self._fieldnames, row))

    def columns(self):
        return self._fieldnames


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
