"""compatibility layer for abc (Python standard library)"""
from __future__ import absolute_import
from abc import *


try:
    ABC  # New in version 3.4.
except NameError:
    ABC = ABCMeta('ABC', (object,), {})  # <- Using Python 2 and 3
                                         #    compatible syntax.
