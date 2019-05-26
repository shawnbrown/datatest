# -*- coding: utf-8 -*-
"""test driven data-wrangling and validation

PYTEST_DONT_REWRITE
"""

# Datatest Core API (__all__ property defined in submodules)
from .validation import *   # Validation error and functions.
from .differences import *  # Difference classes.
from .acceptances import (  # Acceptance context manger API.
    accepted,
    allowed,  # <- Deprecated since 0.9.5
)

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
from ._query.query import Select
from ._query.query import Query
from ._query.query import Result
from ._repeatingcontainer import RepeatingContainer

# Set module explicitly to cleanup reprs and error reporting.
Select.__module__ = 'datatest'
Query.__module__ = 'datatest'
Result.__module__ = 'datatest'

__version__ = '0.9.6.dev0'


#############################################
# Temporary aliases and deprecation warnings.
#############################################
import warnings as _warnings


class Selector(Select):
    def __init__(self, *args, **kwds):
        _warnings.warn(
            'Selector has been renamed, use Select instead',
            category=DeprecationWarning,
            stacklevel=2,
        )
        return super(Selector, self).__init__(*args, **kwds)


class ProxyGroup(RepeatingContainer):
    def __init__(self, *args, **kwds):
        _warnings.warn(
            'ProxyGroup has been renamed, use RepeatingContainer instead',
            category=DeprecationWarning,
            stacklevel=2,
        )
        return super(ProxyGroup, self).__init__(*args, **kwds)
