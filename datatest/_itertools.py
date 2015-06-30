"""itertools compatibility layer"""
from itertools import *

try:
    filterfalse  # New in Python 3.
except NameError:
    filterfalse = ifilterfalse
