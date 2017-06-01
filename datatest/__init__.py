# -*- coding: utf-8 -*-
from .case import DataTestCase

from .errors import ValidationError
from .errors import DataError
from .errors import Missing
from .errors import Extra
from .errors import Invalid
from .errors import Deviation

from datatest.allow import allowed_missing
from datatest.allow import allowed_extra
from datatest.allow import allowed_invalid
from datatest.allow import allowed_deviation
from datatest.allow import allowed_percent_deviation
from datatest.allow import allowed_specific
from datatest.allow import allowed_key
from datatest.allow import allowed_args
from datatest.allow import allowed_limit

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


__version__ = '0.8.2.dev0'

__all__ = [
    # Test case.
    'DataTestCase',

    # Error classes.
    'ValidationError',
    'DataError',
    'Missing',
    'Extra',
    'Invalid',
    'Deviation',

    # Allowance context mangers.
    'allowed_missing',
    'allowed_extra',
    'allowed_invalid',
    'allowed_deviation',
    'allowed_percent_deviation',
    'allowed_specific',
    'allowed_key',
    'allowed_args',
    'allowed_limit',

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
