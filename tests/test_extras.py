
from . import _unittest as unittest
from .test_source import TestBaseSource
from .test_source import MinimalSource

from datatest.extras import ExcelSource
from datatest.extras import PandasSource
from datatest.extras import _version_info

try:
    import xlrd
except ImportError:
    xlrd = None

try:
    import pandas
    assert (_version_info(pandas) >= (0, 13, 0)
                and _version_info(pandas.np) >= (1, 7, 1))
except (ImportError, AssertionError):
    pandas = None


#@unittest.skipIf(xlrd is None, 'xlrd not installed')
#class TestExcelSource(TestBaseSource):
#    def setUp(self):
#        path =
#        self.datasource = ExcelSource(path)


@unittest.skipIf(pandas is None, 'pandas not found')
class TestPandasSource(TestBaseSource):
    def setUp(self):
        df = pandas.DataFrame(self.testdata, columns=self.fieldnames)
        self.datasource = PandasSource(df)


@unittest.skipIf(pandas is None, 'pandas not found')
class TestPandasSourceWithIndex(TestBaseSource):
    def setUp(self):
        df = pandas.DataFrame(self.testdata, columns=self.fieldnames)
        df = df.set_index(['label1', 'label2'])
        #df = df.set_index(['label1'])
        self.datasource = PandasSource(df)
