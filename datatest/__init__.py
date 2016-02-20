# -*- coding: utf-8 -*-
from .case import DataTestCase
from .case import DataAssertionError

from .source import BaseSource
from .source import SqliteSource
from .source import CsvSource
from .source import MultiSource

from .extras import ExcelSource
from .extras import PandasSource

from .diff import ExtraItem
from .diff import MissingItem
from .diff import InvalidItem
from .diff import InvalidNumber
from .diff import NotProperSubset
from .diff import NotProperSuperset

from .sourceresult import ResultSet
from .sourceresult import ResultMapping

from .runner import required
from .runner import DataTestRunner

from .main import DataTestProgram
from .main import main


__version__ = '0.0.1a'

__all__ = [
    # Test case.
    'DataTestCase',
    'DataAssertionError',

    # Data sources.
    'BaseSource',
    'SqliteSource',
    'CsvSource',
    'MultiSource',
    'ExcelSource',
    'PandasSource',

    # Query results.
    'ResultSet',
    'ResultMapping',

    # Differences.
    'ExtraItem',
    'MissingItem',
    'InvalidItem',
    'InvalidNumber',

    # Test runner and command-line program.
    'required',
    'DataTestRunner',
    'DataTestProgram',
    'main',
]

# Temporary aliases for deprecated names.
DataTestCase.allowDeviationPercent = DataTestCase.allowPercentDeviation

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
