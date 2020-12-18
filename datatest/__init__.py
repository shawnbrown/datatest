# -*- coding: utf-8 -*-
"""test driven data-wrangling and validation

PYTEST_DONT_REWRITE
"""
from __future__ import absolute_import

# Datatest Core API (__all__ property defined in submodules)
from .validation import *   # Validation error and functions.
from .differences import *  # Difference classes.
from .acceptances import accepted

from ._vendor.predicate import Predicate

# Pandas extensions.
from ._pandas_integration import register_accessors

# Unittest-style API
from .case import DataTestCase
from .runner import mandatory
from .runner import DataTestRunner
from .main import DataTestProgram
from .main import main

# Data Handling API
from ._working_directory import working_directory
from ._vendor.repeatingcontainer import RepeatingContainer


__version__ = '0.11.0.dev1'


#############################################
# Register traceback formatting handler.
#############################################
from . import _excepthook
import sys as _sys
_sys.excepthook = _excepthook.excepthook
