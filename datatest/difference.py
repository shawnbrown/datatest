# -*- coding: utf-8 -*-
from math import isnan
from numbers import Number
from pprint import pformat

from .utils.builtins import *
from .utils import abc
from .utils import collections
from .utils import contextlib
from .utils.decimal import Decimal
from .utils.misc import _make_token


__all__ = [
    'BaseDifference',
    'Missing',
    'Extra',
    'Invalid',
    'Deviation',
]


NANTOKEN = _make_token(
    'NANTOKEN',
    'Token for comparing differences that contain not-a-number values.'
)

def _nan_to_token(x):
    with contextlib.suppress(TypeError):
        if isnan(x):
            return NANTOKEN
    return x


class BaseDifference(abc.ABC):
    """Base class for data differences."""
    def __init__(self, *args):
        if not args:
            msg = '{0} requires at least 1 argument, got 0'
            raise TypeError(msg.format(self.__class__.__name__))
        self._args = args

    @property
    @abc.abstractmethod
    def args(self):
        """The tuple of arguments given to the exception constructor."""
        return self._args

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False
            # POINT OF DISCUSSION: Should subclasses test equal
            # if args all match (like tuples and nameduples do)?
        self_args = [_nan_to_token(x) for x in self.args]
        other_args = [_nan_to_token(x) for x in other.args]
        return self_args == other_args

    def __repr__(self):
        cls_name = self.__class__.__name__
        args_repr = ', '.join(repr(arg) for arg in self.args)
        return '{0}({1})'.format(cls_name, args_repr)


class Missing(BaseDifference):
    """A value **not found in data** that is in *requirement*."""
    @property
    def args(self):
        return BaseDifference.args.fget(self)


class Extra(BaseDifference):
    """A value found in *data* but is **not in requirement**."""
    @property
    def args(self):
        return BaseDifference.args.fget(self)


class Invalid(BaseDifference):
    """A value in *data* that does not satisfy a function, equality,
    or regular expression *requirement*.
    """
    def __init__(self, invalid, expected=None):
        if expected is None:
            self._args = (invalid,)
        else:
            self._args = (invalid, expected)

    @property
    def args(self):
        return self._args


class Deviation(BaseDifference):
    """The difference between a numeric value in *data* and a matching
    numeric value in *requirement*.
    """
    def __init__(self, deviation, expected):
        isempty = lambda x: x is None or x == ''
        try:
            if expected == 0:
                assert deviation != 0
                assert isinstance(deviation, Number) or isempty(deviation)
            elif isempty(expected):
                assert isinstance(deviation, Number)
            elif isinstance(expected, Number):
                assert not isnan(expected)
                assert isinstance(deviation, Number) and deviation != 0
            else:
                raise AssertionError()
        except AssertionError:
            msg = ('invalid Deviation arguments, got deviation={0!r}, '
                   'expected={1!r}').format(deviation, expected)
            raise ValueError(msg)

        self.deviation = deviation
        self.expected = expected

    @property
    def args(self):
        return (self.deviation, self.expected)

    def __repr__(self):
        cls_name = self.__class__.__name__
        try:
            devi_repr = '{0:+}'.format(self.deviation)  # Apply +/- sign
        except (TypeError, ValueError):
            devi_repr = repr(self.deviation)
        return '{0}({1}, {2!r})'.format(cls_name, devi_repr, self.expected)


NOTFOUND = _make_token(
    'NOTFOUND',
    'Token for handling values that are not available for comparison.'
)


def _make_difference(actual, expected, show_expected=True):
    """Returns an appropriate difference for *actual* and *expected*
    values that are known to be unequal.

    Setting *show_expected* to False, signals that the *expected*
    argument should be omitted when creating an Invalid difference
    (this is useful for reducing duplication when validating data
    against a single function or object).
    """
    # Prepare for numeric comparisons.
    _isnum = lambda x: isinstance(x, Number) and not isnan(x)
    first_isnum = _isnum(actual)
    second_isnum = _isnum(expected)

    # Numeric vs numeric.
    if first_isnum and second_isnum:
        diff = actual - expected
        return Deviation(diff, expected)

    # Numeric vs empty (or not found).
    if first_isnum and (not expected or expected is NOTFOUND):
        if expected is NOTFOUND:
            expected = None

        diff = actual - 0
        return Deviation(diff, expected)

    # Empty (or not found) vs numeric.
    if (not actual or actual is NOTFOUND) and second_isnum:
        if actual is NOTFOUND:
            actual = None

        if expected == 0:
            diff = actual
        else:
            diff = 0 - expected
        return Deviation(diff, expected)

    # Object vs NOTFOUND.
    if expected is NOTFOUND:
        return Extra(actual)

    # NOTFOUND vs object.
    if actual is NOTFOUND:
        return Missing(expected)

    # All other pairs of objects.
    if show_expected:
        return Invalid(actual, expected)
    return Invalid(actual)
