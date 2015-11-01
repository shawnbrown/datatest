# -*- coding: utf-8 -*-
from .case import DataTestCase
from .case import DataAssertionError

from .datasource import BaseDataSource
from .datasource import SqliteDataSource
from .datasource import CsvDataSource
from .datasource import MultiDataSource

from .datasource_extras import ExcelDataSource
from .datasource_extras import PandasDataSource

from .diff import ExtraItem
from .diff import MissingItem
from .diff import InvalidItem
from .diff import InvalidNumber
from .diff import NotProperSubset
from .diff import NotProperSuperset

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
    'ExtraItem',
    'MissingItem',
    'InvalidItem',
    'InvalidNumber',

    # Test runner and command-line program.
    'DataTestRunner',
    'DataTestProgram',
    'main',
]
