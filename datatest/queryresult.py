"""Scratchpad for DataSource query result objects."""
import itertools
from collections import Mapping
from collections import Set
from functools import wraps

from ._builtins import *

from .diff import ExtraItem
from .diff import MissingItem
from .diff import InvalidItem

ExtraValue = ExtraItem

def _coerce_other(f):
    """Decorator for comparison methods to convert 'other' argument into
    a ResultSet instance.

    """
    @wraps(f)
    def wrapped(self, other):
        if not isinstance(other, ResultSet):
            try:
                other = ResultSet(other)
            except TypeError:
                return NotImplemented
        return f(self, other)
    return wrapped


class ResultSet(object):
    """DataSource query result set."""
    def __init__(self, values):
        """Initialize object."""
        if not isinstance(values, Set):
            if isinstance(values, Mapping):
                raise TypeError('cannot be mapping')
            values = set(values)
        self.values = values

    @_coerce_other
    def __eq__(self, other):
        return self.values == other.values

    @_coerce_other
    def __ne__(self, other):
        return not self.__eq__(other)

    @_coerce_other
    def __lt__(self, other):
        return self.values < other.values

    @_coerce_other
    def __gt__(self, other):
        return self.values > other.values

    @_coerce_other
    def __le__(self, other):
        return self.values <= other.values

    @_coerce_other
    def __ge__(self, other):
        return self.values >= other.values

    def __contains__(self, item):
        return item in self.values

    def compare(self, other):
        """Compare *self* to *other* and return a list of difference objects.
        If *other* is callable, constructs a list of InvalidItem objects
        for values where *other* returns False.  If *other* is a ResultSet or
        other collection, differences are compiled as a list of ExtraItem and
        MissingItem objects.

        """
        if callable(other):
            differences = (InvalidItem(x) for x in self.values if not other(x))
        else:
            if not isinstance(other, ResultSet):
                other = ResultSet(other)
            extra = self.values.difference(other.values)
            extra = (ExtraItem(x) for x in extra)
            missing = other.values.difference(self.values)
            missing = (MissingItem(x) for x in missing)
            differences = itertools.chain(extra, missing)
        return list(differences)

    def all(self, func):
        """Return True if *func* evaluates to True for all items in set."""
        return all(func(x) for x in self.values)


class ResultMapping(object):
    """"""
