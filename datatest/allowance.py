# -*- coding: utf-8 -*-
from __future__ import division
import inspect
from math import isnan
from numbers import Number
from ._compatibility.builtins import *
from ._compatibility import abc
from ._compatibility import collections
from ._compatibility import contextlib
from ._compatibility import functools
from ._compatibility import itertools

from ._utils import exhaustible
from ._predicate import PredicateObject
from ._predicate import get_predicate
from ._utils import _get_arg_lengths
from ._utils import _expects_multiple_params
from ._utils import _make_decimal
from ._utils import string_types
from ._query.query import BaseElement
from ._query.query import DictItems

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
    'allowed_keys',
    'allowed_args',
    'allowed_deviation',
    'allowed_percent',
    'allowed_percent_deviation',  # alias of allowed_percent
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
        self.priority = getattr(self, 'priority', 100)  # Use existing priority
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

    ##################################################
    # Methods and operators for union and intersection
    ##################################################
    def intersection(self, other):
        """Return a new allowance that accepts only those differences
        allowed by both the current allowance and the given *other*
        allowance.
        """
        return self.__and__(other)

    def __and__(self, other):
        if not isinstance(other, BaseAllowance):
            return NotImplemented
        return IntersectedAllowance(self, other)

    def union(self, other):
        """Return a new allowance that accepts any difference allowed
        by either the current allowance or the given *other* allowance.
        """
        return self.__or__(other)

    def __or__(self, other):
        if not isinstance(other, BaseAllowance):
            return NotImplemented
        return UnionedAllowance(self, other)

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

        __tracebackhide__ = True  # Set pytest flag to hide traceback.

        if is_not_mapping:
            assert len(differences) == 1
            differences = differences.popitem()[1]
            if isinstance(differences, BaseDifference):
                differences = [differences]

        # Extend description with allowance message.
        if self.msg:
            if exc_value.description:
                message = '{0}: {1}'.format(self.msg, exc_value.description)
            else:
                message = self.msg
        else:
            message = exc_value.description

        # Build new ValidationError with remaining differences.
        exc = ValidationError(differences, message)

        # Re-raised error inherits truncation behavior of original.
        exc._should_truncate = exc_value._should_truncate
        exc._truncation_notice = exc_value._truncation_notice

        exc.__cause__ = None  # <- Suppress context using verbose
        raise exc             #    alternative to support older Python
                              #    versions--see PEP 415 (same as
                              #    effect as "raise ... from None").


class CombinedAllowance(BaseAllowance):
    """Base class for combining allowances using Boolean composition."""
    def __init__(self, left, right, msg=None):
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


class IntersectedAllowance(CombinedAllowance):
    """Base class to allow only those differences allowed by both
    given allowances.
    """
    def __repr__(self):
        return '({0!r} & {1!r})'.format(self.left, self.right)

    def call_predicate(self, item):
        first, second = self.left, self.right
        if first.priority > second.priority:
            first, second = second, first

        # The allowance protocol is stateful so it's important to use
        # short-circuit evaluation to avoid calling the second allowance
        # unnecessarily. If `first` returns False, then `second` should
        # not be called.
        return first.call_predicate(item) and second.call_predicate(item)


class UnionedAllowance(CombinedAllowance):
    """Base class to allow differences allowed by either given
    allowance.
    """
    def __repr__(self):
        return '({0!r} | {1!r})'.format(self.left, self.right)

    def call_predicate(self, item):
        first, second = self.left, self.right
        if first.priority > second.priority:
            first, second = second, first

        # The allowance protocol is stateful so it's important to use
        # short-circuit evaluation to avoid calling the second allowance
        # unnecessarily. If `first` returns True, then `second` should
        # not be called.
        return first.call_predicate(item) or second.call_predicate(item)


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


class allowed_keys(BaseAllowance):
    """Allows differences whose associated keys satisfy the given
    *predicate* (see :ref:`predicate-docs` for details).
    """
    def __init__(self, predicate, msg=None):
        super(allowed_keys, self).__init__(msg)

        predicate = get_predicate(predicate)
        def function(x):
            return predicate == x
        function.__name__ = repr(predicate)

        self.function = function

    def __repr__(self):
        cls_name = self.__class__.__name__
        msg_part = ', msg={0!r}'.format(self.msg) if self.msg else ''
        obj_name = getattr(self.function, '__name__', repr(self.function))
        return '{0}({1}{2})'.format(cls_name, obj_name, msg_part)

    def call_predicate(self, item):
        key = item[0]
        return self.function(key)


class allowed_args(BaseAllowance):
    """Allows differences whose 'args' satisfy the given *predicate*
    (see :ref:`predicate-docs` for details).
    """
    def __init__(self, predicate, msg=None):
        super(allowed_args, self).__init__(msg)

        predicate = get_predicate(predicate)
        def function(x):
            return predicate == x
        function.__name__ = repr(predicate)

        self.function = function

    def __repr__(self):
        cls_name = self.__class__.__name__
        msg_part = ', msg={0!r}'.format(self.msg) if self.msg else ''
        obj_name = getattr(self.function, '__name__', repr(self.function))
        return '{0}({1}{2})'.format(cls_name, obj_name, msg_part)

    def call_predicate(self, item):
        args = item[1].args
        if len(args) == 1:
            args = args[0]  # Unwrap single-item tuple.
        return self.function(args)


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


class allowed_percent(BaseAllowance):
    """allowed_percent(tolerance, /, msg=None)
    allowed_percent(lower, upper, msg=None)

    Context manager that allows Deviations within a given percent
    tolerance without triggering a test failure.

    See documentation for full details.
    """
    def __init__(self, lower, upper=None, msg=None):
        lower, upper, msg = _normalize_deviation_args(lower, upper, msg)
        self.lower = lower
        self.upper = upper
        super(allowed_percent, self).__init__(msg)

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
        deviation = diff.deviation
        expected = diff.expected

        if expected:
            percent_error = (deviation or 0) / expected
        elif not deviation:
            percent_error = 0
        else:
            return False  # <- EXIT!

        if isnan(percent_error):
            return False
        return self.lower <= percent_error <= self.upper

with contextlib.suppress(AttributeError):  # inspect.Signature() is new in 3.3
    allowed_percent.__init__.__signature__ = inspect.Signature([
        inspect.Parameter('self', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('tolerance', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('msg', inspect.Parameter.POSITIONAL_OR_KEYWORD),
    ])

allowed_percent_deviation = allowed_percent  # Set alias for full name.


class allowed_specific(BaseAllowance):
    """Allows specific *differences* without triggering a
    test failure::

        known_issues = datatest.allowed_specific([
            Missing('foo'),
            Extra('bar'),
        ])

        with known_issues:
            datatest.validate(..., ...)

    A dictionary can be used to specify differences per group::

        known_issues = datatest.allowed_specific({
            'AAA': Missing('foo'),
            'BBB': [Extra('bar'), Missing('baz')],
        })

        with known_issues:
            datatest.validate(..., ...)

    To treat multiple dictionary groups as a single group, use a
    single-item dictionary with an ellipsis (``...``) for the key::

        known_issues = datatest.allowed_specific({
            ...: [Missing('foo'), Extra('bar')],
        })

        with known_issues:
            datatest.validate(..., ...)
    """
    def __init__(self, differences, msg=None):
        if not isinstance(differences, (BaseDifference, list, set, dict)):
            raise TypeError(
                'differences must be a list, dict, or a single difference, '
                'got {0} type instead'.format(differences.__class__.__name__)
            )
        self.differences = differences
        self.msg = msg
        self._allowed = dict()         # Properties to hold working values
        self._predicate_keys = dict()  # during allowance checking.

    @property
    def priority(self):
        return 200

    def __repr__(self):
        cls_name = self.__class__.__name__
        msg_part = ', msg={0!r}'.format(self.msg) if self.msg else ''
        return '{0}({1!r}{2})'.format(cls_name, self.differences, msg_part)

    def start_collection(self):
        self._predicate_keys = dict()  # Clear _predicate_keys

        # Normalize and copy mutable containers, assign to "_allowed".
        diffs = self.differences
        if isinstance(diffs, BaseDifference):
            allowed = collections.defaultdict(lambda: [diffs])
        elif isinstance(diffs, (list, set)):
            allowed = collections.defaultdict(lambda: list(diffs))
        elif isinstance(diffs, dict):
            allowed = dict()
            for key, value in diffs.items():
                predicate = get_predicate(key)
                if isinstance(predicate, PredicateObject):
                    self._predicate_keys[key]= predicate

                if isinstance(value, (list, set)):
                    allowed[key] = list(value)  # Make a copy.
                else:
                    allowed[key] = [value]
        else:
            raise TypeError(
                'differences must be a list, dict, or a single difference, '
                'got {0} type instead'.format(allowed.__class__.__name__)
            )
        self._allowed = allowed

    def call_predicate(self, item):
        key, diff = item
        try:
            self._allowed[key].remove(diff)
            return True
        except KeyError:
            matches = dict()

            # See if key compares as equal to any predicate-keys.
            for match_key, match_pred in self._predicate_keys.items():
                if match_pred == key:
                    matches[match_key] = match_pred

            if not matches:
                return False
            elif len(matches) == 1:
                try:
                    match_key = next(iter(matches.keys()))
                    self._allowed[match_key].remove(diff)
                    return True
                except ValueError:
                    return False
            else:
                msg = (
                    'the key {0!r} matches multiple predicates: {1}'
                ).format(key, ', '.join(repr(x) for x in matches.values()))
                exc = KeyError(msg)
                exc.__cause__ = None
                raise exc

        except ValueError:
            return False


class allowed_limit(BaseAllowance):
    """Allows a limited *number* of differences without triggering a
    test failure::

        with datatest.allowed_limit(5):  # Allow up to 5 differences.
            datatest.validate(..., ...)

    If the count of differences exceeds the given *number*, the test
    case will fail with a :class:`ValidationError` containing the
    remaining differences.
    """
    def __init__(self, number, msg=None):
        if not isinstance(number, Number):
            err_msg = 'number must be a numeric type, got {0}'
            raise TypeError(err_msg.format(number.__class__.__name__))

        self.number = number
        self.msg = msg
        self._count = None  # Properties to hold working values
        self._limit = None  # during allowance checking.

    def __repr__(self):
        cls_name = self.__class__.__name__
        msg_part = ', msg={0!r}'.format(self.msg) if self.msg else ''
        return '{0}({1!r}{2})'.format(cls_name, self.number, msg_part)

    @property
    def priority(self):
        return 300

    def start_collection(self):
        self._limit = self.number
        self._count = 0

    def call_predicate(self, item):
        self._count += 1
        return self._count <= self._limit
