"""compatibility layer for abc (Python standard library)"""
from __future__ import absolute_import
from abc import *


try:
    ABC  # New in version 3.4.
    ABC.__slots__  # New in version 3.7
except (NameError, AttributeError):
    # Using Python 2 and 3 compatible syntax.
    ABC = ABCMeta('ABC', (object,), {'__slots__': ()})
