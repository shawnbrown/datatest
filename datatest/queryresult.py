"""Scratchpad for DataSource query result objects."""
from collections import Mapping
from collections import Set
from functools import wraps

from .diff import MissingValue
from .diff import ExtraValue
from .diff import InvalidValue


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
        return self.values != other.values

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

    @_coerce_other
    def compare(self, other):
        """Build a list of differences between *self* and *other* sets."""
        extra = self.values - other.values
        extra = [ExtraValue(x) for x in extra]

        missing = other.values - self.values
        missing = [MissingValue(x) for x in missing]

        return extra + missing


class ResultMapping(object):
    """"""
