"""compatibility layer for itertools (Python standard library)"""
from __future__ import absolute_import
from itertools import *

try:
    filterfalse  # New in Python 3.
except NameError:
    filterfalse = ifilterfalse
