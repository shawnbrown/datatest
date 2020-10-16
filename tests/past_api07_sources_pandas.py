# -*- coding: utf-8 -*-
from . import _unittest as unittest
from .mixins import CountTests
from .mixins import OtherTests

from datatest.__past__.api07_sources import PandasSource
from datatest.__past__.api07_sources import _version_info


########################################################################
# Test version parsing and import ``pandas`` if available.
########################################################################
class TestVersionInfo(unittest.TestCase):
    def test_public_version(self):
        public_version = '0.19.2'
        info_tuple = _version_info(public_version)
        self.assertEqual(info_tuple, (0, 19, 2))

    def test_local_version(self):
        """Version items after a "+" are considered "local" version
        identifiers (see PEP 440).
        """
        local_version = '0.19.2+0.g825876c.dirty'
        info_tuple = _version_info(local_version)
        self.assertEqual(info_tuple, (0, 19, 2, 0, 'g825876c', 'dirty'))


try:
    import pandas
    if (_version_info(pandas) < (0, 13, 0)
            or _version_info(pandas.np) < (1, 7, 1)):
        raise ImportError
except ImportError:
    pandas = None


########################################################################
# Test with DataFrame with no specified index (using default indexing).
########################################################################
@unittest.skipUnless(pandas, 'requires pandas 0.13 or newer')
class TestPandasSource(OtherTests, unittest.TestCase):
    def setUp(self):
        df = pandas.DataFrame(self.testdata, columns=self.fieldnames)
        self.datasource = PandasSource(df)


@unittest.skipUnless(pandas, 'requires pandas 0.13 or newer')
class TestPandasSourceCount(CountTests, unittest.TestCase):
    def setUp(self):
        df = pandas.DataFrame(self.testdata, columns=self.fieldnames)
        self.datasource = PandasSource(df)


########################################################################
# Test with DataFrame that has a specified index.
########################################################################
@unittest.skipUnless(pandas, 'requires pandas 0.13 or newer')
class TestPandasSourceWithIndex(OtherTests, unittest.TestCase):
    def setUp(self):
        df = pandas.DataFrame(self.testdata, columns=self.fieldnames)
        df = df.set_index(['label1', 'label2'])  # <- Specify index!
        self.datasource = PandasSource(df)


@unittest.skipUnless(pandas, 'requires pandas 0.13 or newer')
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
