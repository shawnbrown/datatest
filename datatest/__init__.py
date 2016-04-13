# -*- coding: utf-8 -*-
from .case import DataTestCase

from .source import BaseSource
from .source import SqliteSource
from .source import CsvSource
from .source import MultiSource

from .extras import ExcelSource
from .extras import PandasSource

from .differences import DataAssertionError
from .differences import Extra
from .differences import Missing
from .differences import Invalid
from .differences import Deviation
from .differences import NotProperSubset
from .differences import NotProperSuperset

from .compare import CompareSet
from .compare import CompareDict

from .runner import required
from .runner import DataTestRunner

from .main import DataTestProgram
from .main import main


__version__ = '0.0.1a'

__all__ = [
    # Test case.
    'DataTestCase',

    # Data sources.
    'BaseSource',
    'SqliteSource',
    'CsvSource',
    'MultiSource',
    'ExcelSource',
    'PandasSource',

    # Query results.
    'CompareSet',
    'CompareDict',

    # Error and Differences.
    'DataAssertionError',
    'Extra',
    'Missing',
    'Invalid',
    'Deviation',

    # Test runner and command-line program.
    'required',
    'DataTestRunner',
    'DataTestProgram',
    'main',
]

# Temporary aliases for deprecated names.
DataTestCase.allowSpecified = DataTestCase.allowOnly
DataTestCase.allowUnspecified = DataTestCase.allowAny
DataTestCase.allowDeviationPercent = DataTestCase.allowPercentDeviation
DataTestCase.assertColumnSet = DataTestCase.assertDataColumns
DataTestCase.assertValueSet = DataTestCase.assertDataSet
DataTestCase.assertValueSum = DataTestCase.assertDataSum
DataTestCase.assertValueCount = DataTestCase.assertDataCount
DataTestCase.assertValueRegex = DataTestCase.assertDataRegex
DataTestCase.assertValueNotRegex = DataTestCase.assertDataNotRegex

def _assertColumnSubset(self, ref=None, msg=None):
    with self.allowMissing():
        self.assertColumnSet(ref, msg)
DataTestCase.assertColumnSubset = _assertColumnSubset

def _assertColumnSuperset(self, ref=None, msg=None):
    with self.allowExtra():
        self.assertColumnSet(ref, msg)
DataTestCase.assertColumnSuperset = _assertColumnSuperset

def _assertValueSubset(self, column, ref=None, msg=None, **filter_by):
    with self.allowMissing():
        self.assertValueSet(column, ref, msg, **filter_by)
DataTestCase.assertValueSubset = _assertValueSubset

def _assertValueSuperset(self, column, ref=None, msg=None, **filter_by):
    with self.allowExtra():
        self.assertValueSet(column, ref, msg, **filter_by)
DataTestCase.assertValueSuperset = _assertValueSuperset
