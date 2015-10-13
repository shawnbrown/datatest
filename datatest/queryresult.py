"""Scratchpad for DataSource query result objects."""
import itertools
from collections import Mapping
from collections import Set
from functools import wraps

from ._builtins import *

from .diff import ExtraItem
from .diff import MissingItem
from .diff import InvalidItem


def _coerce_other(target_type):
    """Callable decorator for comparison methods to convert *other* argument
    into given *target_type* instance.

    """
    def callable(f):
        @wraps(f)
        def wrapped(self, other):
            if not isinstance(other, target_type):
                try:
                    other = target_type(other)
                except TypeError:
                    return NotImplemented
            return f(self, other)
        return wrapped

    return callable

class ResultSet(object):
    """DataSource query result set."""
    def __init__(self, values):
        """Initialize object."""
        if not isinstance(values, Set):
            if isinstance(values, Mapping):
                raise TypeError('cannot be mapping')
            values = set(values)
        self.values = values

    def __eq__(self, other):
        return self.values == other.values

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        return self.values < other.values

    def __gt__(self, other):
        return self.values > other.values

    def __le__(self, other):
        return self.values <= other.values

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
            differences = [InvalidItem(x) for x in self.values if not other(x)]
        else:
            if not isinstance(other, ResultSet):
                other = ResultSet(other)
            extra = self.values.difference(other.values)
            extra = (ExtraItem(x) for x in extra)
            missing = other.values.difference(self.values)
            missing = (MissingItem(x) for x in missing)
            differences = list(itertools.chain(extra, missing))
        return differences

    def all(self, func):
        """Return True if *func* evaluates to True for all items in set."""
        return all(func(x) for x in self.values)


# Decorate ResultSet comparison magic methods (cannot be decorated in-line as
# class must first be defined).
_other_to_resultset = _coerce_other(ResultSet)
ResultSet.__eq__ = _other_to_resultset(ResultSet.__eq__)
ResultSet.__ne__ = _other_to_resultset(ResultSet.__ne__)
ResultSet.__lt__ = _other_to_resultset(ResultSet.__lt__)
ResultSet.__gt__ = _other_to_resultset(ResultSet.__gt__)
ResultSet.__le__ = _other_to_resultset(ResultSet.__le__)
ResultSet.__ge__ = _other_to_resultset(ResultSet.__ge__)


class ResultMapping(object):
    """"""
