# -*- coding: utf-8 -*-
import inspect
from math import isnan
from numbers import Number
from .utils.builtins import *
from .utils import abc
from .utils import collections
from .utils import contextlib
from .utils import functools
from .utils import itertools

from .utils.misc import _is_consumable
from .utils.misc import _get_arg_lengths
from .utils.misc import _expects_multiple_params
from .utils.misc import _make_decimal
from .utils.misc import string_types
from .dataaccess import BaseElement
from .dataaccess import DictItems

from .validation import ValidationError
from .difference import BaseDifference
from .difference import Missing
from .difference import Extra
from .difference import Invalid
from .difference import Deviation


__datatest = True  # Used to detect in-module stack frames (which are
                   # omitted from output).


__all__ = [
    'allowed_missing',
    'allowed_extra',
    'allowed_invalid',
    'allowed_key',
    'allowed_args',
    'allowed_deviation',
    'allowed_percent_deviation',
    'allowed_specific',
    'allowed_limit',
]


class BaseAllowance(abc.ABC):
    """Context manager base class to allow certain differences without
    triggering a test failure.
    """
    def __init__(self, msg=None):
        """Initialize object values."""
        self.msg = msg
        self.priority = getattr(self, 'priority', 1)  # Use existing priority
                                                      # if already defined.
    @abc.abstractmethod
    def __repr__(self):
        cls_name = self.__class__.__name__
        msg_part = 'msg={0!r}'.format(self.msg) if self.msg else ''
        return '{0}({1})'.format(cls_name, msg_part)

    ######################################
    # Hook methods for allowance protocol.
    ######################################
    def start_collection(self):
        """Called first before any group or predicate checking."""

    def start_group(self, key):
        """Called before processing each group."""

    @abc.abstractmethod
    def call_predicate(self, item):
        """Call once for each item."""
        return False

    def end_group(self, key):
        """Called after processing each group."""

    def end_collection(self):
        """Called last after all items have been checked."""

    ####################################
    # Operators for boolean composition.
    ####################################
    def __and__(self, other):
        if not isinstance(other, BaseAllowance):
            return NotImplemented
        return LogicalAndAllowance(self, other)

    def __or__(self, other):
        if not isinstance(other, BaseAllowance):
            return NotImplemented
        return LogicalOrAllowance(self, other)

    ###############################################
    # Data handling methods for context management.
    ###############################################
    def _filterfalse(self, serialized):
        self.start_collection()

        def make_key(item):
            return item[0]
        grouped = itertools.groupby(serialized, key=make_key)

        for key, group in grouped:
            self.start_group(key)
            for item in group:
                if self.call_predicate(item):
                    continue
                yield item
            self.end_group(key)

        self.end_collection()

    @staticmethod
    def _serialized_items(iterable):
        if isinstance(iterable, collections.Mapping):
            for key in iterable:
                value = iterable[key]
                if isinstance(value, (BaseElement, Exception)):
                    yield (key, value)
                else:
                    for subvalue in value:
                        yield (key, subvalue)
        else:
            for value in iterable:
                yield (None, value)

    @staticmethod
    def _deserialized_items(iterable):
        def make_key(item):
            return item[0]

        grouped = itertools.groupby(iterable, key=make_key)

        def make_value(group):
            value = [item[1] for item in group]
            if len(value) == 1:
                return value.pop()
            return value

        return dict((key, make_value(group)) for key, group in grouped)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type and not issubclass(exc_type, ValidationError):
            raise exc_value

        differences = getattr(exc_value, 'differences', [])
        is_not_mapping = not isinstance(differences, collections.Mapping)

        stream = self._serialized_items(differences)
        stream = self._filterfalse(stream)
        differences = self._deserialized_items(stream)

        if not differences:
            return True  # <- EXIT!

        if is_not_mapping:
            assert len(differences) == 1
            differences = differences.popitem()[1]
            if isinstance(differences, BaseDifference):
                differences = [differences]

        # Extend message with allowance message.
        message = getattr(exc_value, 'message', '')
        if self.msg:
            message = '{0}: {1}'.format(self.msg, message)

        # Build new ValidationError with remaining differences.
        exc = ValidationError(message, differences)

        # Re-raised error inherits truncation behavior of original.
        exc._should_truncate = exc_value._should_truncate
        exc._truncation_notice = exc_value._truncation_notice

        exc.__cause__ = None  # <- Suppress context using verbose
        raise exc             #    alternative to support older Python
                              #    versions--see PEP 415 (same as
                              #    effect as "raise ... from None").


class CompositionAllowance(BaseAllowance):
    """Base class for combining allowances using Boolean composition."""
    def __init__(self, left, right, msg=None):
        if left.priority > right.priority:
            left, right = right, left
        self.left = left
        self.right = right
        self.msg = msg
        self.priority = max(left.priority, right.priority)

    def start_collection(self):
        self.left.start_collection()
        self.right.start_collection()

    def start_group(self, key):
        self.left.start_group(key)
        self.right.start_group(key)

    def end_group(self, key):
        self.left.end_group(key)
        self.right.end_group(key)

    def end_collection(self):
        self.left.end_collection()
        self.right.end_collection()


class LogicalAndAllowance(CompositionAllowance):
    """Base class to combine allowances using logical AND condition."""
    def __repr__(self):
        return '({0!r} & {1!r})'.format(self.left, self.right)

    def call_predicate(self, item):
        return (self.left.call_predicate(item)
                and self.right.call_predicate(item))


class LogicalOrAllowance(CompositionAllowance):
    """Base class to combine allowances using logical OR condition."""
    def __repr__(self):
        return '({0!r} | {1!r})'.format(self.left, self.right)

    def call_predicate(self, item):
        return (self.left.call_predicate(item)
                or self.right.call_predicate(item))


class allowed_missing(BaseAllowance):
    """Allows :class:`Missing` values without triggering a test
    failure::

        with datatest.allowed_missing():
            datatest.validate(..., ...)
    """
    def __repr__(self):
        return super(allowed_missing, self).__repr__()

    def call_predicate(self, item):
        return isinstance(item[1], Missing)


class allowed_extra(BaseAllowance):
    """Allows :class:`Extra` values without triggering a test
    failure::

        with datatest.allowed_extra():
            datatest.validate(..., ...)
    """
    def __repr__(self):
        return super(allowed_extra, self).__repr__()

    def call_predicate(self, item):
        return isinstance(item[1], Extra)


class allowed_invalid(BaseAllowance):
    """Allows :class:`Invalid` values without triggering a test
    failure::

        with datatest.allowed_invalid():
            datatest.validate(..., ...)
    """
    def __repr__(self):
        return super(allowed_invalid, self).__repr__()

    def call_predicate(self, item):
        return isinstance(item[1], Invalid)


class allowed_key(BaseAllowance):
    """The given *function* should accept a number of arguments
    equal the given key elements. If key is a single value (string
    or otherwise), *function* should accept one argument. If key
    is a three-tuple, *function* should accept three arguments.
    """
    def __init__(self, function, msg=None):
        super(allowed_key, self).__init__(msg)
        self.function = function

    def __repr__(self):
        cls_name = self.__class__.__name__
        msg_part = ', msg={0!r}'.format(self.msg) if self.msg else ''
        return '{0}({1!r}{2})'.format(cls_name, self.function, msg_part)

    def call_predicate(self, item):
        key = item[0]
        if isinstance(key, BaseElement):
            return self.function(key)
        return self.function(*key)


class allowed_args(BaseAllowance):
    """The given *function* should accept a number of arguments equal
    the given elements in the 'args' attribute. If args is a single
    value (string or otherwise), *function* should accept one argument.
    If args is a three-tuple, *function* should accept three arguments.
    """
    def __init__(self, function, msg=None):
        super(allowed_args, self).__init__(msg)
        self.function = function

    def __repr__(self):
        cls_name = self.__class__.__name__
        msg_part = ', msg={0!r}'.format(self.msg) if self.msg else ''
        return '{0}({1!r}{2})'.format(cls_name, self.function, msg_part)

    def call_predicate(self, item):
        args = item[1].args
        if isinstance(args, BaseElement):
            return self.function(args)
        return self.function(*args)


def _normalize_deviation_args(lower, upper, msg):
    """Normalize deviation allowance arguments to support both
    "tolerance" and "lower, upper" signatures. This helper function
    is intended for internal use.
    """
    if isinstance(upper, str) and msg is None:
        upper, msg = None, msg  # Shift values if using "tolerance" syntax.

    if upper == None:
        tolerance = lower
        assert tolerance >= 0, ('tolerance should not be negative, '
                                'for full control of lower and upper '
                                'bounds, use "lower, upper" syntax')
        lower, upper = -tolerance, tolerance
    lower = _make_decimal(lower)
    upper = _make_decimal(upper)
    assert lower <= upper
    return (lower, upper, msg)


class allowed_deviation(BaseAllowance):
    """allowed_deviation(tolerance, /, msg=None)
    allowed_deviation(lower, upper, msg=None)

    Context manager that allows Deviations within a given tolerance
    without triggering a test failure.

    See documentation for full details.
    """
    def __init__(self, lower, upper=None, msg=None):
        lower, upper, msg = _normalize_deviation_args(lower, upper, msg)
        self.lower = lower
        self.upper = upper
        super(allowed_deviation, self).__init__(msg)

    def __repr__(self):
        cls_name = self.__class__.__name__
        msg_part = ', msg={0!r}'.format(self.msg) if self.msg else ''
        if -self.lower ==  self.upper:
            return '{0}({1!r}{2})'.format(cls_name, self.upper, msg_part)
        return '{0}(lower={1!r}, upper={2!r}{3})'.format(cls_name,
                                                         self.lower,
                                                         self.upper,
                                                         msg_part)

    def call_predicate(self, item):
        diff = item[1]
        deviation = diff.deviation or 0
        if isnan(deviation) or isnan(diff.expected or 0):
            return False
        return self.lower <= deviation <= self.upper

with contextlib.suppress(AttributeError):  # inspect.Signature() is new in 3.3
    allowed_deviation.__init__.__signature__ = inspect.Signature([
        inspect.Parameter('self', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('tolerance', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('msg', inspect.Parameter.POSITIONAL_OR_KEYWORD),
    ])


class allowed_percent_deviation(BaseAllowance):
    """allowed_percent_deviation(tolerance, /, msg=None)
    allowed_percent_deviation(lower, upper, msg=None)

    Context manager that allows Deviations within a given percent
    tolerance without triggering a test failure.

    See documentation for full details.
    """
    def __init__(self, lower, upper=None, msg=None):
        lower, upper, msg = _normalize_deviation_args(lower, upper, msg)
        self.lower = lower
        self.upper = upper
        super(allowed_percent_deviation, self).__init__(msg)

    def __repr__(self):
        cls_name = self.__class__.__name__
        msg_part = ', msg={0!r}'.format(self.msg) if self.msg else ''
        if -self.lower ==  self.upper:
            return '{0}({1!r}{2})'.format(cls_name, self.upper, msg_part)
        return '{0}(lower={1!r}, upper={2!r}{3})'.format(cls_name,
                                                         self.lower,
                                                         self.upper,
                                                         msg_part)

    def call_predicate(self, item):
        diff = item[1]
        percent_deviation = diff.percent_deviation or 0
        if isnan(percent_deviation) or isnan(diff.expected or 0):
            return False
        return self.lower <= percent_deviation <= self.upper

with contextlib.suppress(AttributeError):  # inspect.Signature() is new in 3.3
    allowed_percent_deviation.__init__.__signature__ = inspect.Signature([
        inspect.Parameter('self', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('tolerance', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('msg', inspect.Parameter.POSITIONAL_OR_KEYWORD),
    ])


class allowed_specific(BaseAllowance):
    """Allows specific *differences* without triggering a test failure.
    If there are differences that have not been specified, a
    :class:`ValidationError` is raised with the remaining differences::

        known_issues = datatest.allowed_specific([
            Extra('foo'),
            Missing('bar'),
        ])
        with known_issues:
            datatest.validate(..., ...)
    """
    def __init__(self, differences, msg=None):
        if isinstance(differences, BaseDifference):
            self.differences = [differences]
        elif not _is_consumable(differences):
            self.differences = differences
        else:
            raise TypeError(
                'expected a single difference or non-exhaustable collection, '
                'got {0} type instead'.format(differences.__class__.__name__)
            )
        self.msg = msg
        self.priority = 2
        self._allowed = None  # Property to hold diffs during processing.

    def __repr__(self):
        cls_name = self.__class__.__name__
        msg_part = ', msg={0!r}'.format(self.msg) if self.msg else ''
        return '{0}({1!r}{2})'.format(cls_name, self.differences, msg_part)

    def start_group(self, key):
        try:
            allowed = self.differences.get(key, [])
            if isinstance(allowed, BaseDifference):
                self._allowed = [allowed]
            else:
                self._allowed = list(allowed)
        except AttributeError:
            self._allowed = list(self.differences)

    def call_predicate(self, item):
        diff = item[1]
        if diff in self._allowed:
            self._allowed.remove(diff)
            return True
        return False


class allowed_limit(BaseAllowance):
    """Allows a limited *number* of differences without triggering a
    test failure::

        with datatest.allowed_limit(5):  # Allow up to 5 differences.
            datatest.validate(..., ...)

    If the count of differences exceeds the given *number*, the test
    case will fail with a :class:`ValidationError` containing the
    remaining differences.

    A dictionary can be used to define individual limits per group::

        with datatest.allowed_limit({'A': 3, 'B': 2}):  # Allow up to 3 diffs
            datatest.validate(..., ...)                 # in group "A" and 2
                                                        # diffs in group "B".

    Using an ellipsis (``...``) will match any key---allowing a limited
    number of differences for every group::

        with datatest.allowed_limit({...: 5}):  # Allow up to 5 diffs
            datatest.validate(..., ...)         # for every group.
    """
    def __init__(self, number, msg=None):
        self.number = number
        self.msg = msg
        self._count = None        # Properties to hold
        self._limit = None        # working values during
        self._number_dict = None  # allowance checking.

    def __repr__(self):
        cls_name = self.__class__.__name__
        msg_part = ', msg={0!r}'.format(self.msg) if self.msg else ''
        return '{0}({1!r}{2})'.format(cls_name, self.number, msg_part)

    @property
    def priority(self):
        if isinstance(self.number, collections.Mapping):
            return 3
        return 5

    def _reset_count_and_limit(self, key):
        self._limit = self._number_dict[key]
        self._count = 0

    def start_collection(self):
        if isinstance(self.number, collections.Mapping):
            number_dict = dict(self.number)  # Make a copy.
            default_value = number_dict.pop(Ellipsis, 0)
            default_factory = lambda: default_value
            self._number_dict = collections.defaultdict(default_factory,
                                                        number_dict)
            self.start_group = self._reset_count_and_limit
        else:
            self.start_group = super(allowed_limit, self).start_group
            self._limit = self.number
            self._count = 0

    def call_predicate(self, item):
        self._count += 1
        return self._count <= self._limit
