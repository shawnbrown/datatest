# -*- coding: utf-8 -*-
from .validation import ValidationError
from .validation import is_valid
from .validation import validate

from .difference import Missing
from .difference import Extra
from .difference import Invalid
from .difference import Deviation

from .allowance import allowed_missing
from .allowance import allowed_extra
from .allowance import allowed_invalid
from .allowance import allowed_deviation
from .allowance import allowed_percent_deviation
from .allowance import allowed_specific
from .allowance import allowed_key
from .allowance import allowed_args
from .allowance import allowed_limit

from .case import DataTestCase
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


__version__ = '0.8.3.dev0'

__all__ = [
    # Validation error and functions.
    'ValidationError',
    'is_valid',
    'validate',

    # Difference classes.
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

    # Unittest-style classes, decorators, and functions.
    'DataTestCase',
    'mandatory',
    'skip',
    'skipIf',
    'skipUnless',
    'DataTestRunner',
    'DataTestProgram',
    'main',

    # Data Access sub-package.
    'DataSource',
    'DataQuery',
    'DataResult',
    'working_directory',
]

# Temporary alias for old "required" decorator.
required = mandatory
