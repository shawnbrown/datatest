# -*- coding: utf-8 -*-
from math import isnan
from numbers import Number
from pprint import pformat

from ._compatibility.builtins import *
from ._compatibility import abc
from ._compatibility import contextlib
from ._compatibility.decimal import Decimal
from ._utils import _make_token


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
    """The base class for "difference" objects---all other difference
    classes are derived from this base.
    """
    def __init__(self, *args):
        if not args:
            msg = '{0} requires at least 1 argument, got 0'
            raise TypeError(msg.format(self.__class__.__name__))
        self._args = args

    @property
    @abc.abstractmethod
    def args(self):
        """The tuple of arguments given to the difference constructor.
        Some difference (like :class:`Deviation`) expect a certain
        number of arguments and assign a special meaning to the
        elements of this tuple, while others are called with only
        a single value.
        """
        return self._args

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False
        self_args = tuple(_nan_to_token(x) for x in self.args)
        other_args = tuple(_nan_to_token(x) for x in other.args)
        return self_args == other_args

    def __ne__(self, other):           # <- For Python 2.x support. There is
        return not self.__eq__(other)  #    no implicit relationship between
                                       #    __eq__() and __ne__() in Python 2.

    def __repr__(self):
        cls_name = self.__class__.__name__
        args_repr = ', '.join(repr(arg) for arg in self.args)
        return '{0}({1})'.format(cls_name, args_repr)


class Missing(BaseDifference):
    """Created when *value* is missing from the data under test.

    In the following example, the required value ``'A'`` is missing
    from the data under test::

        data = ['B', 'C']

        requirement = {'A', 'B', 'C'}

        datatest.validate(data, requirement)

    Running this example raises the following error:

    .. code-block:: none
        :emphasize-lines: 2

        ValidationError: does not satisfy set membership (1 difference): [
            Missing('A'),
        ]
    """
    def __init__(self, value):
        self._args = (value,)

    @property
    def args(self):
        return self._args


class Extra(BaseDifference):
    """Created when *value* is unexpectedly found in the data under
    test.

    In the following example, the value ``'C'`` is found in the data
    under test but it's not part of the required values::


        data = ['A', 'B', 'C']

        requirement = {'A', 'B'}

        datatest.validate(data, requirement)

    Running this example raises the following error:

    .. code-block:: none
        :emphasize-lines: 2

        ValidationError: does not satisfy set membership (1 difference): [
            Extra('C'),
        ]
    """
    def __init__(self, value):
        self._args = (value,)

    @property
    def args(self):
        return self._args


class Invalid(BaseDifference):
    """Created when a value does not satisfy a function, equality, or
    regular expression requirement.

    In the following example, the value ``9`` does not satisfy the
    required function::

        data = [2, 4, 6, 9]

        def iseven(x):
            return x % 2 == 0

        datatest.validate(data, iseven)

    Running this example raises the following error:

    .. code-block:: none
        :emphasize-lines: 2

        ValidationError: does not satisfy iseven (1 difference): [
            Invalid(9),
        ]
    """
    def __init__(self, invalid, expected=None):
        self.invalid = invalid  #: The invalid value under test.
        self.expected = expected  #: The expected value.

    def __repr__(self):
        cls_name = self.__class__.__name__
        if self.expected is None:
            return '{0}({1!r})'.format(cls_name, self.invalid)
        return '{0}({1!r}, expected={2!r})'.format(cls_name,
                                                   self.invalid,
                                                   self.expected)

    @property
    def args(self):
        if self.expected is None:
            return (self.invalid,)
        return (self.invalid, self.expected)


class Deviation(BaseDifference):
    """Created when a numeric value deviates from its expected value.

    In the following example, the dictionary item ``'C': 33`` does
    not satisfy the required item ``'C': 30``::

        data = {'A': 10, 'B': 20, 'C': 33}

        requirement = {'A': 10, 'B': 20, 'C': 30}

        datatest.validate(data, requirement)

    Running this example raises the following error:

    .. code-block:: none
        :emphasize-lines: 2

        ValidationError: does not satisfy mapping requirement (1 difference): {
            'C': Deviation(+3, 30),
        }
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

        self.deviation = deviation  #: Numeric deviation from expected value.
        self.expected = expected  #: The expected value.

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
