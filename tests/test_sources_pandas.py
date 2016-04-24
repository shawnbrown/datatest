# -*- coding: utf-8 -*-
from . import _unittest as unittest
from .mixins import CountTests
from .mixins import OtherTests

from datatest import PandasSource
from datatest.sources.pandas import _version_info


try:
    import pandas
    assert (_version_info(pandas) >= (0, 13, 0)
                and _version_info(pandas.np) >= (1, 7, 1))
except (ImportError, AssertionError):
    pandas = None


@unittest.skipIf(pandas is None, 'pandas not found')
class TestPandasSource(OtherTests, unittest.TestCase):
    def setUp(self):
        df = pandas.DataFrame(self.testdata, columns=self.fieldnames)
        self.datasource = PandasSource(df)


@unittest.skipIf(pandas is None, 'pandas not found')
class TestPandasSourceWithIndex(OtherTests, unittest.TestCase):
    def setUp(self):
        df = pandas.DataFrame(self.testdata, columns=self.fieldnames)
        df = df.set_index(['label1', 'label2'])
        #df = df.set_index(['label1'])
        self.datasource = PandasSource(df)
