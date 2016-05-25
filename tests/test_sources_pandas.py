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
    missing_pandas = False
except (ImportError, AssertionError):
    missing_pandas = True


########################################################################
# Test with DataFrame with no specified index (using default indexing).
########################################################################
@unittest.skipIf(missing_pandas, 'pandas not found')
class TestPandasSource(OtherTests, unittest.TestCase):
    def setUp(self):
        df = pandas.DataFrame(self.testdata, columns=self.fieldnames)
        self.datasource = PandasSource(df)


@unittest.skipIf(missing_pandas, 'pandas not found')
class TestPandasSourceCount(CountTests, unittest.TestCase):
    def setUp(self):
        df = pandas.DataFrame(self.testdata, columns=self.fieldnames)
        self.datasource = PandasSource(df)


########################################################################
# Test with DataFrame that has a specified index.
########################################################################
@unittest.skipIf(missing_pandas, 'pandas not found')
class TestPandasSourceWithIndex(OtherTests, unittest.TestCase):
    def setUp(self):
        df = pandas.DataFrame(self.testdata, columns=self.fieldnames)
        df = df.set_index(['label1', 'label2'])  # <- Specify index!
        self.datasource = PandasSource(df)


@unittest.skipIf(missing_pandas, 'pandas not found')
class TestPandasSourceWithIndexCount(CountTests, unittest.TestCase):
    def setUp(self):
        df = pandas.DataFrame(self.testdata, columns=self.fieldnames)
        df = df.set_index(['label1', 'label2'])  # <- Specify index!
        self.datasource = PandasSource(df)

    def test_compound_keys(self):
        expected = {
            ('a', 'x'): 2,
            ('a', 'y'): 1,
            ('a', ''): 1,
            ('b', 'z'): 1,
            ('b', 'y'): 1,
            ('b', 'x'): 1,
            #('b', None): 1,
            ('b', pandas.np.nan): 1,  # <- Returns nan instead of None (and that's OK!).
            ('b', ''): 1,
        }
        result = self.datasource.count('label1', ['label1', 'label2'])
        self.assertEqual(expected, result)
