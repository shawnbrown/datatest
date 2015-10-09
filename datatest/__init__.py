# -*- coding: utf-8 -*-
from .case import DataTestCase
from .case import DataAssertionError

from .datasource import BaseDataSource
from .datasource import SqliteDataSource
from .datasource import CsvDataSource
from .datasource import FilteredDataSource
from .datasource import GroupedDataSource
from .datasource import MappedDataSource
from .datasource import MultiDataSource

from .datasource_extras import ExcelDataSource
from .datasource_extras import PandasDataSource

from .diff import ExtraColumn
from .diff import MissingColumn

from .diff import ExtraValue
from .diff import MissingValue
from .diff import InvalidNumber
from .diff import InvalidValue

from .queryresult import ResultSet
from .queryresult import ResultMapping

from .runner import DataTestRunner

from .main import DataTestProgram
from .main import main


__version__ = '0.0.1a'

__all__ = [
    # Test case.
    'DataTestCase',
    'DataAssertionError',

    # Data sources.
    'BaseDataSource',
    'SqliteDataSource',
    'CsvDataSource',
    'FilteredDataSource',
    'GroupedDataSource',
    'MappedDataSource',
    'MultiDataSource',
    'ExcelDataSource',
    'PandasDataSource',

    # Query results.
    'ResultSet',
    'ResultMapping',

    # Differences.
    'ExtraColumn',
    'ExtraValue',
    'MissingColumn',
    'MissingValue',
    'InvalidNumber',
    'InvalidValue',

    # Test runner and command-line program.
    'DataTestRunner',
    'DataTestProgram',
    'main',
]


# TODO: REMOVE BEFORE INITIAL RELEASE (DEPRECATED):
DataTestCase.acceptDifference = DataTestCase.acceptableDifference
DataTestCase.acceptTolerance = DataTestCase.acceptableTolerance
DataTestCase.acceptPercentTolerance = DataTestCase.acceptablePercentTolerance

#ExtraSum = InvalidNumber
#MissingSum = InvalidNumber
