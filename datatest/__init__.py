# -*- coding: utf-8 -*-
"""test driven data-wrangling and validation

PYTEST_DONT_REWRITE
"""

# Datatest Core API (__all__ property defined in submodules)
from .validation import *  # Validation error and functions.
from .difference import *  # Difference classes.
from .allowance import *   # Allowance context mangers.
from ._required import group_requirement
from ._predicate import Predicate

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
from ._proxygroup import ProxyGroup

# Set module explicitly to cleanup reprs and error reporting.
Selector.__module__ = 'datatest'
Query.__module__ = 'datatest'
Result.__module__ = 'datatest'

__version__ = '0.9.3.dev0'

required = mandatory  # Temporary alias for old "required" decorator.
