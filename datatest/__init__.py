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

# Data Handling API
from ._load.get_reader import get_reader
from ._load.working_directory import working_directory
from ._query.query import Selector
from ._query.query import Query
from ._query.query import Result

# Set module explicitly to cleanup reprs and error reporting.
Selector.__module__ = 'datatest'
Query.__module__ = 'datatest'
Result.__module__ = 'datatest'

__version__ = '0.9.0'

required = mandatory  # Temporary alias for old "required" decorator.
