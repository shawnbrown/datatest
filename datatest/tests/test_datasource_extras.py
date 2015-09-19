
from . import _unittest as unittest
from .test_datasource import TestBaseDataSource
from .test_datasource import MinimalDataSource

from datatest.datasource_extras import xlrd
from datatest.datasource_extras import pandas

from datatest.datasource_extras import ExcelDataSource
from datatest.datasource_extras import PandasDataSource


#@unittest.skipIf(xlrd is None, 'xlrd not installed')
#class TestExcelDataSource(TestBaseDataSource):
#    def setUp(self):
#        path =
#        self.datasource = ExcelDataSource(path)


@unittest.skipIf(pandas is None, 'pandas not installed')
class TestPandasDataSource(TestBaseDataSource):
    def setUp(self):
        df = pandas.DataFrame(self.testdata, columns=self.fieldnames)
        self.datasource = PandasDataSource(df)

    def test_from_records_and_source(self):
        expected = [
            {'label1': 'a', 'label2': 'x', 'value': '17'},
            {'label1': 'a', 'label2': 'x', 'value': '13'},
            {'label1': 'a', 'label2': 'y', 'value': '20'},
            {'label1': 'a', 'label2': 'z', 'value': '15'},
            {'label1': 'b', 'label2': 'z', 'value': '5' },
            {'label1': 'b', 'label2': 'y', 'value': '40'},
            {'label1': 'b', 'label2': 'x', 'value': '25'},
        ]

        # Test from_records():
        source = PandasDataSource.from_records(self.testdata, self.fieldnames)
        results = source.slow_iter()
        self.assertEqual(expected, list(results))

        # Test from_source():
        source = MinimalDataSource(self.testdata, self.fieldnames)
        source = PandasDataSource.from_source(source)
        results = source.slow_iter()
        self.assertEqual(expected, list(results))


@unittest.skipIf(pandas is None, 'pandas not installed')
class TestPandasDataSourceWithIndex(TestBaseDataSource):
    def setUp(self):
        df = pandas.DataFrame(self.testdata, columns=self.fieldnames)
        df = df.set_index(['label1', 'label2'])
        #df = df.set_index(['label1'])
        self.datasource = PandasDataSource(df)

    def test_from_records_and_source(self):
        expected = [
            {'label1': 'a', 'label2': 'x', 'value': '17'},
            {'label1': 'a', 'label2': 'x', 'value': '13'},
            {'label1': 'a', 'label2': 'y', 'value': '20'},
            {'label1': 'a', 'label2': 'z', 'value': '15'},
            {'label1': 'b', 'label2': 'z', 'value': '5' },
            {'label1': 'b', 'label2': 'y', 'value': '40'},
            {'label1': 'b', 'label2': 'x', 'value': '25'},
        ]

        # Test from_records():
        source = PandasDataSource.from_records(self.testdata, self.fieldnames)
        results = source.slow_iter()
        self.assertEqual(expected, list(results))

        # Test from_source():
        source = MinimalDataSource(self.testdata, self.fieldnames)
        source = PandasDataSource.from_source(source)
        results = source.slow_iter()
        self.assertEqual(expected, list(results))

