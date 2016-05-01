# -*- coding: utf-8 -*-
from .case import DataTestCase

from .sources.base import BaseSource
from .sources.adapter import AdapterSource
from .sources.multi import MultiSource
from .sources.sqlite import SqliteBase
from .sources.sqlite import SqliteSource
from .sources.csv import CsvSource
from .sources.excel import ExcelSource
from .sources.pandas import PandasSource

from .error import DataAssertionError

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
    'SqliteBase',

    # Query results.
    'CompareSet',
    'CompareDict',

    # Error.
    'DataAssertionError',

    # Differences.
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
