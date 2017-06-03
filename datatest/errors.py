# -*- coding: utf-8 -*-
from math import isnan
from numbers import Number
from pprint import pformat

from .utils import collections
from .utils import contextlib
from .utils.decimal import Decimal
from .utils.misc import _is_nsiterable
from .utils.misc import _is_consumable
from .utils.misc import _make_token
from .dataaccess import _is_collection_of_items


class ValidationError(AssertionError):
    """Raised when a data validation fails."""
    def __init__(self, message, differences):
        self.args = message, differences

    @property
    def args(self):
        """The tuple of arguments given to the exception constructor."""
        return (self._message, self._errors)

    @args.setter
    def args(self, value):
        if not isinstance(value, tuple):
            value_type = value.__class__.__name__
            raise ValueError('expected tuple, got {0!r}'.format(value_type))

        if not len(value) == 2:
            raise ValueError('expected tuple of 2 items, got {0}'.format(len(value)))

        message, differences = value
        if not _is_nsiterable(differences) or isinstance(differences, Exception):
            # Above condition checks for Exception because
            # exceptions are iterable in Python 2.7 and 2.6.
            msg = 'expected iterable of differences, got {0!r}'
            raise TypeError(msg.format(differences.__class__.__name__))

        if _is_collection_of_items(differences):
            differences = dict(differences)
        elif _is_consumable(differences):
            differences = list(differences)

        if not differences:
            raise ValueError('differences must not be empty')

        self._message = message
        self._differences = differences

    @property
    def message(self):
        """The message given to the exception constructor."""
        return self._message

    @property
    def differences(self):
        """The differences given to the exception constructor."""
        return self._differences

    def __str__(self):
        differences = pformat(self._differences, width=1)
        if any([differences.startswith('[') and differences.endswith(']'),
                differences.startswith('{') and differences.endswith('}'),
                differences.startswith('(') and differences.endswith(')')]):
            differences = differences[1:-1]

        output = '{0} ({1} differences):\n {2}'
        return output.format(self._message, len(self._differences), differences)

    def __repr__(self):
        class_name = self.__class__.__name__
        return '{0}({1!r}, {2!r})'.format(class_name, self.message, self.differences)


NANTOKEN = _make_token(
    'NANTOKEN',
    'Token for comparing differences that contain not-a-number values.'
)

def _nan_to_token(x):
    with contextlib.suppress(TypeError):
        if isnan(x):
            return NANTOKEN
    return x


class BaseDifference(object):
    """Base class for data differences."""
    def __new__(cls, *args, **kwds):
        if cls is BaseDifference:
            msg = "can't instantiate BaseDifference directly - use a subclass"
            raise TypeError(msg)
        return super(BaseDifference, cls).__new__(cls)

    def __init__(self, *args):
        if not args:
            msg = '{0} requires at least 1 argument, got 0'
            raise TypeError(msg.format(self.__class__.__name__))
        self._args = args

    @property
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
    pass


class Extra(BaseDifference):
    """A value found in *data* that is **not in requirement**."""
    pass


class Invalid(BaseDifference):
    """A value in *data* that does not satisfy a function or regular
    expression *requirement*.
    """
    def __init__(self, invalid, expected=None):
        if expected:
            super(Invalid, self).__init__(invalid, expected)
        else:
            super(Invalid, self).__init__(invalid)


class Deviation(BaseDifference):
    """The difference between a numeric value in *data* and a matching
    numeric value in *requirement*.
    """
    def __init__(self, deviation, expected):
        empty = lambda x: not x or isnan(x)
        if ((not empty(expected) and empty(deviation)) or
                (expected == 0 and deviation == 0)):
            raise ValueError('numeric deviation must '
                             'be positive or negative')
        super(Deviation, self).__init__(deviation, expected)  # Set *_args*.

    @property
    def deviation(self):
        return self.args[0]

    @property
    def expected(self):
        return self.args[1]

    @property
    def percent_deviation(self):
        expected = self.expected
        if isinstance(expected, float):
            expected = Decimal.from_float(expected)
        else:
            expected = Decimal(expected if expected else 0)

        deviation = self.deviation
        if isinstance(deviation, float):
            deviation = Decimal.from_float(deviation)
        else:
            deviation = Decimal(deviation if deviation else 0)

        if isnan(expected) or isnan(deviation):
            return Decimal('NaN')
        return deviation / expected if expected else Decimal(0)  # % error calc.

    def __repr__(self):
        cls_name = self.__class__.__name__
        try:
            diff_repr = '{0:+}'.format(self.args[0])  # Apply +/- sign
        except (TypeError, ValueError):
            diff_repr = repr(self.args[0])
        remaining_repr = ', '.join(repr(arg) for arg in self.args[1:])
        return '{0}({1}, {2})'.format(cls_name, diff_repr, remaining_repr)


NOTFOUND = _make_token(
    'NOTFOUND',
    'Token for handling values that are not available for comparison.'
)


def _get_difference(actual, expected, show_expected=True):
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
