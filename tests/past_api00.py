# -*- coding: utf-8 -*-
"""Test backwards compatibility with pre-release API.

.. note:: Because this sub-module works by monkey-patching the global
          ``datatest`` package, these tests should be run in a separate
          process.
"""
from . import _unittest as unittest

import datatest
from datatest.__past__ import api00  # <- MONKEY PATCH!!!

from .common import MinimalSource
DataTestCase = datatest.DataTestCase
from datatest.__past__.api07_error import DataError


class TestAttributes(unittest.TestCase):
    def test_api_dev0(self):
        # Error class.
        self.assertTrue(hasattr(datatest, 'DataAssertionError'))

        # Data source properties.
        self.assertTrue(hasattr(datatest.DataTestCase, 'subjectData'))
        self.assertTrue(hasattr(datatest.DataTestCase, 'referenceData'))

        # Acceptance context managers.
        self.assertTrue(hasattr(datatest.DataTestCase, 'allowSpecified'))
        self.assertTrue(hasattr(datatest.DataTestCase, 'allowUnspecified'))
        self.assertTrue(hasattr(datatest.DataTestCase, 'allowDeviationPercent'))

        # Assert methods.
        self.assertTrue(hasattr(datatest.DataTestCase, 'assertColumnSet'))
        self.assertTrue(hasattr(datatest.DataTestCase, 'assertColumnSubset'))
        self.assertTrue(hasattr(datatest.DataTestCase, 'assertColumnSuperset'))
        self.assertTrue(hasattr(datatest.DataTestCase, 'assertValueSet'))
        self.assertTrue(hasattr(datatest.DataTestCase, 'assertValueSubset'))
        self.assertTrue(hasattr(datatest.DataTestCase, 'assertValueSuperset'))
        self.assertTrue(hasattr(datatest.DataTestCase, 'assertValueSum'))
        self.assertTrue(hasattr(datatest.DataTestCase, 'assertValueCount'))
        self.assertTrue(hasattr(datatest.DataTestCase, 'assertValueRegex'))
        self.assertTrue(hasattr(datatest.DataTestCase, 'assertValueNotRegex'))


class TestColumnSubset(datatest.DataTestCase):
    def setUp(self):
        self.subjectData = MinimalSource(data=[['a', '65'], ['b', '70']],
                                         fieldnames=['label1', 'value'])

    def test_is_same(self):
        self.assertColumnSubset(ref=['label1', 'value'])  # Should pass without error.

    def test_is_subset(self):
        self.assertColumnSubset(ref=['label1', 'label2', 'value'])  # Should pass without error.

    def test_is_superset(self):
        regex = "different column names:\n xExtra\(u?'value'\)"
        with self.assertRaisesRegex(DataError, regex):
            self.assertColumnSubset(ref=['label1'])


class TestColumnSuperset(datatest.DataTestCase):
    def setUp(self):
        self.subjectData = MinimalSource(data=[['a', '65'], ['b', '70']],
                                         fieldnames=['label1', 'value'])

    def test_is_same(self):
        self.assertColumnSuperset(ref=['label1', 'value'])  # Should pass without error.

    def test_is_superset(self):
        self.assertColumnSuperset(ref=['label1'])  # Should pass without error.

    def test_is_subset(self):
        regex = "different column names:\n xMissing\(u?'label2'\)"
        with self.assertRaisesRegex(DataError, regex):
            self.assertColumnSuperset(ref=['label1', 'label2', 'value'])


class TestValueSubset(DataTestCase):
    def setUp(self):
        self.subjectData = MinimalSource(data=[['a'], ['b'], ['c']],
                                         fieldnames=['label'])

    def test_is_same(self):
        self.assertValueSubset('label', ref=['a', 'b', 'c'])  # Should pass without error.

    def test_is_subset(self):
        self.assertValueSubset('label', ref=['a', 'b', 'c', 'd'])  # Should pass without error.

    def test_is_superset(self):
        regex = "different 'label' values:\n xExtra\(u?'c'\)"
        with self.assertRaisesRegex(DataError, regex):
            self.assertValueSubset('label', ref=['a', 'b'])


class TestValueSuperset(DataTestCase):
    def setUp(self):
        self.subjectData = MinimalSource(data=[['a'], ['b'], ['c']],
                                         fieldnames=['label'])

    def test_is_same(self):
        self.assertValueSuperset('label', ref=['a', 'b', 'c'])  # Should pass without error.

    def test_is_superset(self):
        self.assertValueSuperset('label', ref=['a', 'b'])  # Should pass without error.

    def test_is_subset(self):
        regex = "different 'label' values:\n xMissing\(u?'d'\)"
        with self.assertRaisesRegex(DataError, regex):
            self.assertValueSuperset('label', ref=['a', 'b', 'c', 'd'])


if __name__ == '__main__':
    unittest.main()
else:
    raise Exception('This test must be run directly or as a subprocess.')
