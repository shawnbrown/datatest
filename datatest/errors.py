# -*- coding: utf-8 -*-
from math import isnan
from .utils.misc import _is_nsiterable


class ValidationErrors(AssertionError):
    """Iterable container of errors."""
    def __init__(self, message, errors):
        if not _is_nsiterable(errors):
            errors = [errors]
        super(ValidationErrors, self).__init__(message, errors)

    def __iter__(self):
        return iter(self.args[1])


class DataError(AssertionError):
    """
    DataError(arg[, arg [, ...]])

    Base class for data errors.
    """
    def __new__(cls, *args, **kwds):
        if cls is DataError:
            msg = "can't instantiate base class DataError - use a subclass"
            raise TypeError(msg)
        return super(DataError, cls).__new__(cls)

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
        return self.__class__ == other.__class__ and self.args == other.args

    def __repr__(self):
        cls_name = self.__class__.__name__
        args_repr = ', '.join(repr(arg) for arg in self.args)
        return '{0}({1})'.format(cls_name, args_repr)


class Missing(DataError):
    """A value **not found in data** that is in *requirement*."""
    pass


class Extra(DataError):
    """A value found in *data* that is **not in requirement**."""
    pass


class Invalid(DataError):
    """A value in *data* that does not satisfy a function or regular
    expression *requirement*.
    """
    def __init__(self, invalid, expected=None):
        if expected:
            super(Invalid, self).__init__(invalid, expected)
        else:
            super(Invalid, self).__init__(invalid)


class Deviation(DataError):
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
    def percent_deviation(self):
        deviation, expected = self.args[:2]
        return deviation / expected if expected else 0  # % error calc.

    def __repr__(self):
        cls_name = self.__class__.__name__
        try:
            diff_repr = '{0:+}'.format(self.args[0])  # Apply +/- sign
        except (TypeError, ValueError):
            diff_repr = repr(self.args[0])
        remaining_repr = ', '.join(repr(arg) for arg in self.args[1:])
        return '{0}({1}, {2})'.format(cls_name, diff_repr, remaining_repr)
