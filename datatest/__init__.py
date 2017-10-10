# -*- coding: utf-8 -*-

# Datatest Core API (__all__ property defined in submodules)
from .validation import *  # Validation error and functions.
from .difference import *  # Difference classes.
from .allowance import *   # Allowance context mangers.

# Unittest-style API
from .case import DataTestCase
from .runner import mandatory
from .runner import skip
from .runner import skipIf
from .runner import skipUnless
from .runner import DataTestRunner
from .main import DataTestProgram
from .main import main

# Data Access API
from .dataaccess import DataSource
from .dataaccess import DataQuery
from .dataaccess import DataResult
from .dataaccess import working_directory


__version__ = '0.8.3.dev0'

required = mandatory  # Temporary alias for old "required" decorator.
