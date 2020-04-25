# -*- coding: utf-8 -*-
from math import isnan
from numbers import Number
from .._utils import _make_decimal

import datatest
from datatest.differences import (
    NANTOKEN,
    _nan_to_token,
)


class xBaseDifference(object):
    """The base class from which all differences must inherit."""
    def __new__(cls, *args, **kwds):
        if cls is xBaseDifference:
            msg = 'cannot instantiate xBaseDifference directly - make a subclass'
            raise NotImplementedError(msg)
        return super(xBaseDifference, cls).__new__(cls)

    def __init__(self, value, required=None, **kwds):
        self._value = value
        self._required = required
        self._kwds = kwds

    @property
    def value(self):
        """The subject *value* that differs from the required value."""
        return self._value

    @property
    def required(self):
        """The *required* value that was expected by the test (not all
        differences will use this property)."""
        return self._required

    @property
    def kwds(self):
        """A dictionary of the keyword arguments to help indicate where
        the difference was detected in the subject data.
        """
        return self._kwds

    def __repr__(self):
        clsname = self.__class__.__name__
        kwds = self._format_kwds(self.kwds)
        return '{0}({1!r}{2})'.format(clsname, self.value, kwds)

    def __hash__(self):
        return hash((self.__class__, self.__repr__()))

    def __eq__(self, other):
        diff_lookup = {
            xMissing: datatest.differences.Missing,
            xExtra: datatest.differences.Extra,
            xDeviation: datatest.differences.Deviation,
            xInvalid: datatest.differences.Invalid,
        }
        self_class = self.__class__
        self_class = diff_lookup.get(self_class, self_class)

        other_class = other.__class__
        other_class = diff_lookup.get(other_class, other_class)

        if self_class != other_class:
            return False

        try:
            self_args = tuple(_nan_to_token(x) for x in self.args)
        except AttributeError:
            self_args = (_nan_to_token(self._value),)
            if self._required:
                self_args += (_nan_to_token(self._required),)

        try:
            other_args = tuple(_nan_to_token(x) for x in other.args)
        except AttributeError:
            other_args = (_nan_to_token(other._value),)
            if other._required:
                other_args += (_nan_to_token(other._required),)

        return self_args == other_args

    @staticmethod
    def _format_kwds(kwds):
        if not kwds:
            return ''  # <- EXIT!
        kwds = sorted(kwds.items())
        try:
            kwds = [(k, unicode(v)) for k, v in kwds]  # Only if `unicode` is defined.
        except NameError:
            pass
        kwds = ['{0}={1!r}'.format(k, v) for k, v in kwds]
        kwds = ', '.join(kwds)
        return ', ' + kwds


class xMissing(xBaseDifference):
    """A value **not found in data** that is in *requirement*."""
    def __init__(self, value, **kwds):
        super(xMissing, self).__init__(value, **kwds)


class xExtra(xBaseDifference):
    """A value found in *data* that is **not in requirement**."""
    def __init__(self, value, **kwds):
        super(xExtra, self).__init__(value, **kwds)


class xInvalid(xBaseDifference):
    """A value in *data* that does not satisfy a function or regular
    expression *requirement*.
    """
    def __repr__(self):
        clsname = self.__class__.__name__
        kwds = self._format_kwds(self.kwds)
        if self.required == None:
            required = ''
        else:
            required = ', ' + repr(self.required)
        return '{0}({1!r}{2}{3})'.format(clsname, self.value, required, kwds)


class xDeviation(xBaseDifference):
    """The difference between a numeric value in *data* and a matching
    numeric value in *requirement*.
    """
    def __init__(self, value, required, **kwds):
        empty = lambda x: not x or isnan(x)
        if (not empty(required) and empty(value)) or (required == 0 and value == 0):
            raise ValueError('numeric deviation must be positive or negative')

        if value or value == 0:
            value = _make_decimal(value)

        if required or required == 0:
            required = _make_decimal(required)

        super(xDeviation, self).__init__(value, required, **kwds)

    def __repr__(self):
        clsname = self.__class__.__name__
        kwds = self._format_kwds(self.kwds)
        value = self.value
        if value:
            try:
                value = '{0:+}'.format(value)  # Apply +/- sign.
            except (TypeError, ValueError):
                pass
        return '{0}({1}, {2}{3})'.format(clsname, value, self.required, kwds)


class xNonStrictRelation(xBaseDifference):
    """Base class for non-strict subset or superset relationships."""
    def __new__(cls, *args, **kwds):
        if cls is xNonStrictRelation:
            msg = 'cannot instantiate xNonStrictRelation directly - make a subclass'
            raise NotImplementedError(msg)
        return super(xNonStrictRelation, cls).__new__(cls)

    def __init__(self, **kwds):
        super(xNonStrictRelation, self).__init__(None, None, **kwds)

    def __repr__(self):
        clsname = self.__class__.__name__
        kwds = self._format_kwds(self.kwds)
        return '{0}({1})'.format(clsname, kwds)


class xNotProperSubset(xNonStrictRelation):
    """Not a proper subset of a required set."""
    pass


class xNotProperSuperset(xNonStrictRelation):
    """Not a proper superset of a required set."""
    pass


class _NotFoundSentinel(object):
    """Sentinel for handling membership in collections."""
    def __repr__(self):
        return '<not found>'
_xNOTFOUND = _NotFoundSentinel()
del _NotFoundSentinel


# TODO: Investigate possibility of removing **kwds from _xgetdiff().
def _xgetdiff(first, second, is_common=False, **kwds):
    """Returns difference object for two objects known to be unequal.
    The *is_common* flag, when True, signals that the *second* argument
    should be omitted when creating an "xInvalid" difference.
    """
    # Prepare for numeric comparisons.
    _isnum = lambda x: isinstance(x, Number) and not isnan(x)
    first_isnum = _isnum(first)
    second_isnum = _isnum(second)

    # Numeric vs numeric.
    if first_isnum and second_isnum:
        difference = first - second
        return xDeviation(difference, second, **kwds)

    # Numeric vs empty (or not found).
    if first_isnum and (not second or second is _xNOTFOUND):
        if second is _xNOTFOUND:
            second = None

        difference = first - 0
        return xDeviation(difference, second, **kwds)

    # Empty (or not found) vs numeric.
    if (not first or first is _xNOTFOUND) and second_isnum:
        if first is _xNOTFOUND:
            first = None

        if second == 0:
            difference = first
        else:
            difference = 0 - second
        return xDeviation(difference, second, **kwds)

    # Object vs _xNOTFOUND.
    if second is _xNOTFOUND:
        return xExtra(first, **kwds)

    # _xNOTFOUND vs object.
    if first is _xNOTFOUND:
        return xMissing(second, **kwds)

    # All other pairs of objects.
    if is_common:
        return xInvalid(first, **kwds)
    return xInvalid(first, second, **kwds)
