# -*- coding: utf-8 -*-
from math import isnan
from numbers import Number
from pprint import pformat

from ._compatibility.builtins import *
from ._compatibility import abc
from ._compatibility import contextlib
from ._compatibility.decimal import Decimal
from ._utils import _make_sentinel


__all__ = [
    'BaseDifference',
    'Missing',
    'Extra',
    'Invalid',
    'Deviation',
]


NOVALUE = _make_sentinel(
    'NoValueType',
    '<no value>',
    'Sentinel to mark when a value does not exist.',
    truthy=False,
)


NANTOKEN = _make_sentinel(
    'NanSentinelType',
    '<nan sentinel>',
    'Token for comparing differences that contain not-a-number values.',
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
    __slots__ = ()

    @property
    @abc.abstractmethod
    def args(self):
        """The tuple of arguments given to the difference constructor.
        Some difference (like :class:`Deviation`) expect a certain
        number of arguments and assign a special meaning to the
        elements of this tuple, while others are called with only
        a single value.
        """
        # Concrete method should return tuple of args used in __init__().
        raise NotImplementedError

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False
        self_args = tuple(_nan_to_token(x) for x in self.args)
        other_args = tuple(_nan_to_token(x) for x in other.args)
        return self_args == other_args

    def __ne__(self, other):           # <- For Python 2.x support. There is
        return not self.__eq__(other)  #    no implicit relationship between
                                       #    __eq__() and __ne__() in Python 2.
    def __hash__(self):
        try:
            return hash((self.__class__, self.args))
        except TypeError as err:
            msg = '{0} in args tuple {1!r}'.format(str(err), self.args)
            hashfail = TypeError(msg)
            hashfail.__cause__ = getattr(err, '__cause__', None)  # getattr for 2.x support
            raise hashfail

    def __repr__(self):
        cls_name = self.__class__.__name__
        args_repr = ', '.join(
            getattr(x, '__name__', repr(x)) for x in self.args)
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
    __slots__ = ('_args',)

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
    __slots__ = ('_args',)

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
    __slots__ = ('_invalid', '_expected')

    def __init__(self, invalid, expected=NOVALUE):
        if invalid == expected:
            msg = 'expects unequal values, got {0!r} and {1!r}'
            raise ValueError(msg.format(invalid, expected))
        self._invalid = invalid
        self._expected = expected

    @property
    def args(self):
        if self._expected is NOVALUE:
            return (self._invalid,)
        return (self._invalid, self._expected)

    @property
    def invalid(self):
        """The invalid value under test."""
        return self._invalid

    @property
    def expected(self):
        """The expected value."""
        return self._expected

    def __repr__(self):
        cls_name = self.__class__.__name__
        invalid_repr = getattr(self._invalid, '__name__', repr(self._invalid))
        if self._expected is not NOVALUE:
            expected_repr = ', expected={0}'.format(
                getattr(self._expected, '__name__', repr(self._expected)))
        else:
            expected_repr = ''
        return '{0}({1}{2})'.format(cls_name, invalid_repr, expected_repr)


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
    __slots__ = ('_deviation', '_expected')

    def __init__(self, deviation, expected):
        isempty = lambda x: x is None or x == ''

        if expected == 0:
            args_ok = (
                deviation != 0
                and (isinstance(deviation, Number) or isempty(deviation))
            )
        elif isempty(expected):
            args_ok = isinstance(deviation, Number)
        elif isinstance(expected, Number):
            args_ok = (
                (not isnan(expected))
                and isinstance(deviation, Number)
                and deviation != 0
            )
        else:
            args_ok = False

        if not args_ok:
            msg = ('invalid Deviation arguments, got deviation={0!r}, '
                   'expected={1!r}').format(deviation, expected)
            raise ValueError(msg)

        self._deviation = deviation
        self._expected = expected

    @property
    def args(self):
        return (self._deviation, self._expected)

    @property
    def deviation(self):
        """Numeric deviation from expected value."""
        return self._deviation

    @property
    def expected(self):
        """The expected value."""
        return self._expected

    def __repr__(self):
        cls_name = self.__class__.__name__
        try:
            devi_repr = '{0:+}'.format(self._deviation)  # Apply +/- sign
        except (TypeError, ValueError):
            devi_repr = repr(self._deviation)
        return '{0}({1}, {2!r})'.format(cls_name, devi_repr, self._expected)


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

    # Object vs NOVALUE.
    if expected is NOVALUE:
        return Extra(actual)

    # NOVALUE vs object.
    if actual is NOVALUE:
        return Missing(expected)

    # All other pairs of objects.
    if show_expected:
        return Invalid(actual, expected)
    return Invalid(actual)
