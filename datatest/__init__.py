# -*- coding: utf-8 -*-
from .case import DataTestCase

from .error import DataError

from .differences import BaseDifference
from .differences import Extra
from .differences import Missing
from .differences import Invalid
from .differences import Deviation
from .differences import NotProperSubset
from .differences import NotProperSuperset

from .allow import allow_iter
from .allow import allow_any
from .allow import allow_missing
from .allow import allow_extra
from .allow import allow_deviation
from .allow import allow_percent_deviation
from .allow import allow_limit
from .allow import allow_only

from .runner import mandatory
from .runner import skip
from .runner import skipIf
from .runner import skipUnless
from .runner import DataTestRunner

from .main import DataTestProgram
from .main import main

from .dataaccess import DataSource
from .dataaccess import DataQuery
from .dataaccess import DataResult
from .dataaccess import working_directory


__version__ = '0.8.0.dev3'

__all__ = [
    # Test case.
    'DataTestCase',

    # Data sources (TODO: remove once "data access" is complete).
    'BaseSource',
    'SqliteSource',
    'CsvSource',
    'AdapterSource',
    'MultiSource',
    'ExcelSource',
    'PandasSource',
    'SqliteBase',

    # Error.
    'DataError',

    # Differences.
    'BaseDifference',
    'Extra',
    'Missing',
    'Invalid',
    'Deviation',

    # Allowance context mangers.
    'allow_iter',
    'allow_any',
    'allow_missing',
    'allow_extra',
    'allow_deviation',
    'allow_percent_deviation',
    'allow_limit',
    'allow_only',

    # Test runner and command-line program.
    'mandatory',
    'skip',
    'skipIf',
    'skipUnless',
    'DataTestRunner',
    'DataTestProgram',
    'main',

    # From Data Access sub-package.
    'DataSource',
    'DataQuery',
    'DataResult',
    'working_directory',
]

# Temporary alias for old "required" decorator.
required = mandatory
