# -*- coding: utf-8 -*-
from numbers import Number
from sqlite3 import Binary

from ..utils.builtins import *
from ..utils import collections
from ..utils import functools
from ..utils.misc import _expects_multiple_params
from ..utils.misc import _is_sortable


# The SQLite BLOB/Binary type in sortable Python 2 but unsortable in Python 3.
_unsortable_blob_type = not _is_sortable(Binary(b'0'))


def _sqlite_sortkey(value):
    """Key function for use with sorted(), min(), max(), etc. that
    makes a best effort to match SQLite ORDER BY behavior for
    supported classes.

    From SQLite docs:

        "...values with storage class NULL come first, followed by
        INTEGER and REAL values interspersed in numeric order, followed
        by TEXT values in collating sequence order, and finally BLOB
        values in memcmp() order."

    For more details see "Datatypes In SQLite Version 3" section
    "4.1. Sort Order" <https://www.sqlite.org/datatype3.html>.
    """
    if value is None:              # NULL (sort group 0)
        return (0, 0)
    if isinstance(value, Number):  # INTEGER and REAL (sort group 1)
        return (1, value)
    if isinstance(value, str):     # TEXT (sort group 2)
        return (2, value)
    if isinstance(value, Binary):  # BLOB (sort group 3)
        if _unsortable_blob_type:
            value = bytes(value)
        return (3, value)
    return (4, value)  # unsupported type (sort group 4)


def _sqlite_cast_as_real(value):
    """Convert value to REAL (float) or default to 0.0 to match SQLite
    behavior. See the "Conversion Processing" table in the "CAST
    expressions" section for details:

        https://www.sqlite.org/lang_expr.html#castexpr
    """
    try:
        return float(value)
    except ValueError:
        return 0.0


def _sqlite_sum(iterable):
    """Sum the elements and return the total."""
    iterable = (_sqlite_cast_as_real(x) for x in iterable if x != None)
    try:
        start_value = next(iterable)
    except StopIteration:  # From SQLite docs: "If there are no non-NULL
        return None        # input rows then sum() returns NULL..."
    return sum(iterable, start_value)


def _sqlite_count(iterable):
    """Returns the number non-NULL (!= None) elements in iterable."""
    return sum(1 for x in iterable if x != None)


def _sqlite_avg(iterable):
    """Return the average of elements in iterable. Returns None if all
    elements are None.
    """
    iterable = (x for x in iterable if x != None)
    total = 0.0
    count = 0
    for x in iterable:
        total = total + _sqlite_cast_as_real(x)
        count += 1
    return total / count if count else None


def _sqlite_min(iterable):
    """Return the minimum non-None value of all values. Returns
    None only if all values are None.
    """
    iterable = (x for x in iterable if x != None)
    return min(iterable, default=None, key=_sqlite_sortkey)


def _sqlite_max(iterable):
    """Return the maximum value of all values. Returns None if all
    values are None.
    """
    return max(iterable, default=None, key=_sqlite_sortkey)


class DataResult(collections.Iterator):
    """A queryable iterator that can be evaluated to a given type."""
    def __init__(self, iterable, evaluates_to):
        self._iterator = iter(iterable)
        self._evaluates_to = evaluates_to
        self._exhausted_by = None

    def _exhaust_iterator(self, name, *args):
        args_repr = ', '.join(repr(x) for x in args)
        self._exhausted_by = '{0}({1})'.format(name, args_repr)
        self._iterator = iter([])  # Set empty iterator.

    def __iter__(self):
        """x.__iter__() <==> iter(x)"""
        return self

    def __next__(self):
        """x.__next__() <==> next(x)"""
        try:
            return next(self._iterator)
        except StopIteration:
            self._exhaust_iterator('__next__')
            raise

    def next(self):  # For Python 2.7 and earlier.
        return self.__next__()

    # Query methods.
    def map(self, function):
        """Return a new DataResult that applies *function* to the
        elements, yielding the results.
        """
        if _expects_multiple_params(function):
            function_orig = function
            function = lambda x: function_orig(*x)

        def apply(value):
            try:
                result = value.map(function)
            except AttributeError:
                result = function(value)
            return result

        if issubclass(self._evaluates_to, dict):
            iterator = ((k, apply(v)) for k, v in self._iterator)
        else:
            iterator = (apply(x) for x in self._iterator)

        self._exhaust_iterator('map')
        return self.__class__(iterator, self._evaluates_to)

    def reduce(self, function):
        """Apply a *function* of two arguments cumulatively to the
        elements, from left to right, so as to reduce the values to a
        single result.
        """
        def apply(value):
            try:
                result = value.reduce(function)
            except AttributeError:
                result = functools.reduce(function, value)
            return result

        if issubclass(self._evaluates_to, dict):
            result = ((k, apply(v)) for k, v in self._iterator)
            result = self.__class__(result, self._evaluates_to)
        else:
            result = apply(self._iterator)

        self._exhaust_iterator('reduce')
        return result

    def _sqlite_aggregate(self, method_name, alt_function):
        def apply(value):
            try:
                method = getattr(value, method_name)
                return method()
            except AttributeError:
                return alt_function(value)

        if issubclass(self._evaluates_to, dict):
            result = ((k, apply(v)) for k, v in self._iterator)
            result = self.__class__(result, self._evaluates_to)
        else:
            result = apply(self._iterator)

        self._exhaust_iterator(method_name)
        return result

    def sum(self):
        """Sum the elements and return the total."""
        return self._sqlite_aggregate('sum', _sqlite_sum)

    def count(self):
        return self._sqlite_aggregate('count', _sqlite_count)

    def avg(self):
        """Return the average of elements."""
        return self._sqlite_aggregate('avg', _sqlite_avg)

    def min(self):
        """Return the minimum non-None value of all values. Returns
        None only if all values are None.
        """
        return self._sqlite_aggregate('min', _sqlite_min)

    def max(self):
        """Return the maximum value of all values. Returns None if
        all values are None.
        """
        return self._sqlite_aggregate('max', _sqlite_max)

    def eval(self):
        eval_type = self._evaluates_to
        if issubclass(eval_type, dict):
            def apply(value):
                try:
                    return value.eval()
                except AttributeError:
                    return value
            result = eval_type((k, apply(v)) for k, v in self._iterator)
        elif eval_type:
            result = eval_type(self._iterator)
        else:
            result = self._iterator

        self._exhaust_iterator('eval')
        return result
