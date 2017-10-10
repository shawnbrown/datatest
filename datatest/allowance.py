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
from .dataaccess import _is_collection_of_items
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
    'BaseAllowance',
    'ElementAllowance',
    'allowed_missing',
    'allowed_extra',
    'allowed_invalid',
    'allowed_deviation',
    'allowed_percent_deviation',
    'allowed_specific',
    'allowed_key',
    'allowed_args',
    'allowed_limit',
]


def _is_mapping_type(obj):
    return isinstance(obj, collections.Mapping) or \
                _is_collection_of_items(obj)


class BaseAllowance(abc.ABC):
    """Context manager to allow certain differences without
    triggering a test failure. *filterfalse* should accept an
    iterable of difference and return an iterable of only
    those differences which are **not** allowed.
    """
    def __init__(self, msg=None):
        """Initialize object values."""
        self.msg = msg

    def __or__(self, other):
        return NotImplemented

    def __and__(self, other):
        return NotImplemented

    def __enter__(self):
        return self

    @abc.abstractmethod
    def filterfalse(self, iterable):
        """Filter iterable and yield elements that are not allowed."""

    def apply_filterfalse(self, iterable):
        if isinstance(iterable, collections.Mapping):
            iterable = getattr(iterable, 'iteritems', iterable.items)()

        if _is_collection_of_items(iterable):
            for key, diff in iterable:
                if isinstance(diff, (BaseElement, Exception)):
                    # Error is a single element.
                    filtered = self.filterfalse(iter([(key, diff)]))
                    if isinstance(filtered, collections.Mapping):
                        filtered = filtered.items()
                    filtered = list(filtered)
                    if filtered:
                        yield filtered[0]
                else:
                    # Error is a container of multiple elements.
                    diff = self.filterfalse((key, d) for d in diff)
                    diff = list(d for key, d in diff)
                    if diff:
                        yield key, diff
        else:
            filtered = self.filterfalse(iterable)
            if _is_mapping_type(filtered):
                raise TypeError('returned mapping output for non-mapping input')
            for diff in filtered:
                yield diff

    def __exit__(self, exc_type, exc_value, tb):
        # Setup traceback-hiding for pytest integration.
        __tracebackhide__ = lambda excinfo: excinfo.errisinstance(ValidationError)

        # Apply filterfalse or reraise non-validation error.
        if exc_type and not issubclass(exc_type, ValidationError):
            raise exc_value
        differences = getattr(exc_value, 'differences', [])
        differences = self.apply_filterfalse(differences)

        # Check container types.
        mappable_in = _is_mapping_type(getattr(exc_value, 'differences', None))
        mappable_out = _is_mapping_type(differences)

        # Check if any differences were returned.
        try:
            first_item = next(iter(differences))
            if _is_consumable(differences):  # Rebuild if consumable.
                differences = itertools.chain([first_item], differences)
        except StopIteration:
            return True  # <- EXIT!

        # Handle mapping input with iterable-of-items output.
        if (mappable_in and not mappable_out
                and isinstance(first_item, collections.Sized)
                and len(first_item) == 2):
            differences = DictItems(differences)
            mappable_out = True

        # Verify type compatibility.
        if mappable_in != mappable_out:
            message = ('{0} received {1!r} collection but '
                       'returned incompatible {2!r} collection')
            filter_name = getattr(self.filterfalse, '__name__',
                                  repr(self.filterfalse))
            output_cls = differences.__class__.__name__
            input_cls = exc_value.differences.__class__.__name__
            raise TypeError(message.format(filter_name, input_cls, output_cls))

        # Re-raise ValidationError() with remaining differences.
        message = getattr(exc_value, 'message', '')
        if self.msg:
            message = '{0}: {1}'.format(self.msg, message)
        exc = ValidationError(message, differences)
        exc.maxDiff = exc_value.maxDiff  # <- Re-raised error inherits the
                                         #    maxDiff of the original error.
        exc.__cause__ = None  # <- Suppress context using verbose
        raise exc             #    alternative to support older Python
                              #    versions--see PEP 415 (same as
                              #    effect as "raise ... from None").


class ElementAllowance(BaseAllowance):
    """Allow differences where *predicate* returns True. For each
    difference, *predicate* will receive two arguments---a **key**
    and **difference**---and should return True if the difference
    is allowed or False if it is not.
    """
    def __init__(self, predicate, msg=None):
        self.predicate = predicate
        super(ElementAllowance, self).__init__(msg)

    def filterfalse(self, iterable):
        predicate = self.predicate
        for key, difference in iterable:
            if not predicate(key, difference):
                yield key, difference

    def apply_filterfalse(self, iterable):
        if _is_mapping_type(iterable):
            return super(ElementAllowance, self).apply_filterfalse(iterable)  # <- EXIT!

        iterable = ((None, difference) for difference in iterable)
        filtered = super(ElementAllowance, self).apply_filterfalse(iterable)
        return (diff for key, diff in filtered)  # 'key' intentionally discarded

    def __or__(self, other):
        if not isinstance(other, ElementAllowance):
            return NotImplemented

        pred1 = self.predicate
        pred2 = other.predicate
        def predicate(*args, **kwds):
            return pred1(*args, **kwds) or pred2(*args, **kwds)
        return ElementAllowance(predicate)

    def __and__(self, other):
        if not isinstance(other, ElementAllowance):
            return NotImplemented

        pred1 = self.predicate
        pred2 = other.predicate
        def predicate(*args, **kwds):
            return pred1(*args, **kwds) and pred2(*args, **kwds)
        return ElementAllowance(predicate)


class allowed_missing(ElementAllowance):
    def __init__(self, msg=None):
        def is_missing(_, difference):  # Key argument "_" not used.
            return isinstance(difference, Missing)
        super(allowed_missing, self).__init__(is_missing, msg)


class allowed_extra(ElementAllowance):
    def __init__(self, msg=None):
        def is_extra(_, difference):  # Key argument "_" not used.
            return isinstance(difference, Extra)
        super(allowed_extra, self).__init__(is_extra, msg)


class allowed_invalid(ElementAllowance):
    def __init__(self, msg=None):
        def is_invalid(_, difference):  # Key argument "_" not used.
            return isinstance(difference, Invalid)
        super(allowed_invalid, self).__init__(is_invalid, msg)


def _normalize_devargs(lower, upper, msg):
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


class allowed_deviation(ElementAllowance):
    """allowed_deviation(tolerance, /, msg=None)
    allowed_deviation(lower, upper, msg=None)

    Context manager that allows Deviations within a given tolerance
    without triggering a test failure.

    See documentation for full details.
    """
    def __init__(self, lower, upper=None, msg=None):
        lower, upper, msg = _normalize_devargs(lower, upper, msg)
        def tolerance(_, diff):  # <- Closes over lower & upper.
            deviation = diff.deviation or 0.0
            if isnan(deviation) or isnan(diff.expected or 0.0):
                return False
            return lower <= deviation <= upper
        super(allowed_deviation, self).__init__(tolerance, msg)

with contextlib.suppress(AttributeError):  # inspect.Signature() is new in 3.3
    allowed_deviation.__init__.__signature__ = inspect.Signature([
        inspect.Parameter('self', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('tolerance', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('msg', inspect.Parameter.POSITIONAL_OR_KEYWORD),
    ])


class allowed_percent_deviation(ElementAllowance):
    def __init__(self, lower, upper=None, msg=None):
        lower, upper, msg = _normalize_devargs(lower, upper, msg)
        def percent_tolerance(_, diff):  # <- Closes over lower & upper.
            percent_deviation = diff.percent_deviation
            if isnan(percent_deviation) or isnan(diff.expected or 0):
                return False
            return lower <= percent_deviation <= upper
        super(allowed_percent_deviation, self).__init__(percent_tolerance, msg)

with contextlib.suppress(AttributeError):  # inspect.Signature() is new in 3.3
    allowed_percent_deviation.__init__.__signature__ = inspect.Signature([
        inspect.Parameter('self', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('tolerance', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('msg', inspect.Parameter.POSITIONAL_OR_KEYWORD),
    ])


class allowed_specific(BaseAllowance):
    def __init__(self, differences, msg=None):
        if _is_collection_of_items(differences):
            differences = dict(differences)
        self.differences = differences
        super(allowed_specific, self).__init__(msg)

    def filterfalse(self, iterable):
        """If the data being tested is a mapping, this is called for
        every group (grouped by key). If the data is a non-mapping,
        this is called only one time for the entire iterable.
        """
        if isinstance(self.differences, collections.Mapping):
            iterable = iter(iterable)
            first_key, first_diff = next(iterable)
            iterable = itertools.chain([(first_key, first_diff)], iterable)
            allowed = self.differences.get(first_key, [])
        else:
            allowed = self.differences

        if isinstance(allowed, BaseDifference):
            allowed = [allowed]
        else:
            allowed = list(allowed)  # Make list or copy existing list.

        for key, difference in iterable:
            try:
                allowed.remove(difference)
            except ValueError:
                yield key, difference

    def apply_filterfalse(self, iterable):
        if _is_mapping_type(iterable):
            return super(allowed_specific, self).apply_filterfalse(iterable)  # <- EXIT!

        if _is_mapping_type(self.differences):
            message = ('{0!r} of differences cannot be matched using a '
                       'specified {1!r}, requires non-mapping container')
            message = message.format(iterable.__class__.__name__,
                                     self.differences.__class__.__name__)
            raise ValueError(message)

        iterable = ((None, diff) for diff in iterable)
        filtered = super(allowed_specific, self).apply_filterfalse(iterable)
        return (diff for key, diff in filtered)  # 'key' intentionally discarded

    def _or_combine_diffs(self, self_diffs, other_diffs):
        if isinstance(self_diffs, BaseDifference):
            self_diffs = [self_diffs]
        if isinstance(other_diffs, BaseDifference):
            other_diffs = [other_diffs]

        differences = []
        for diff in self_diffs:
            if self_diffs.count(diff) >= other_diffs.count(diff):
                differences.append(diff)

        for diff in other_diffs:
            if other_diffs.count(diff) > self_diffs.count(diff):
                differences.append(diff)
        return differences

    def __or__(self, other):
        if not isinstance(other, allowed_specific):
            return NotImplemented

        self_diffs = self.differences
        other_diffs = other.differences

        if isinstance(self_diffs, collections.Mapping) != \
                isinstance(other_diffs, collections.Mapping):
            self_type = self_diffs.__class__.__name__
            other_type = other_diffs.__class__.__name__
            msg = ('cannot combine mapping with non-mapping differences: '
                   '{0!r} and {1!r}').format(self_type, other_type)
            raise ValueError(msg)

        if not isinstance(self_diffs, collections.Mapping):
            differences = self._or_combine_diffs(self_diffs, other_diffs)
            return allowed_specific(differences)  # <- EXIT!

        all_keys = set(self_diffs.keys()) | set(other_diffs.keys())
        differences = {}
        for key in all_keys:
            diff1 = self_diffs.get(key, [])
            diff2 = other_diffs.get(key, [])
            differences[key] = self._or_combine_diffs(diff1, diff2)
        return allowed_specific(differences)

    def _and_combine_diffs(self, self_diffs, other_diffs):
        if isinstance(self_diffs, BaseDifference):
            self_diffs = [self_diffs]
        if isinstance(other_diffs, BaseDifference):
            other_diffs = [other_diffs]

        differences = []
        for diff in self_diffs:
            if self_diffs.count(diff) <= other_diffs.count(diff):
                differences.append(diff)

        for diff in other_diffs:
            if other_diffs.count(diff) < self_diffs.count(diff):
                differences.append(diff)
        return differences

    def __and__(self, other):
        if not isinstance(other, allowed_specific):
            return NotImplemented

        self_diffs = self.differences
        other_diffs = other.differences

        if isinstance(self_diffs, collections.Mapping) != \
                isinstance(other_diffs, collections.Mapping):
            self_type = self_diffs.__class__.__name__
            other_type = other_diffs.__class__.__name__
            msg = ('cannot combine mapping with non-mapping differences: '
                   '{0!r} and {1!r}').format(self_type, other_type)
            raise ValueError(msg)

        if not isinstance(self_diffs, collections.Mapping):
            differences = self._and_combine_diffs(self_diffs, other_diffs)
            return allowed_specific(differences)  # <- EXIT!

        all_keys = set(self_diffs.keys()) & set(other_diffs.keys())
        differences = {}
        for key in all_keys:
            diff1 = self_diffs[key]
            diff2 = other_diffs[key]
            combined = self._and_combine_diffs(diff1, diff2)
            if combined:
                differences[key] = combined
        return allowed_specific(differences)


class allowed_key(ElementAllowance):
    """The given *function* should accept a number of arguments
    equal the given key elements. If key is a single value (string
    or otherwise), *function* should accept one argument. If key
    is a three-tuple, *function* should accept three arguments.
    """
    def __init__(self, function, msg=None):
        @functools.wraps(function)
        def wrapped(key, _):
            if isinstance(key, BaseElement):
                return function(key)
            return function(*key)
        super(allowed_key, self).__init__(wrapped, msg)


class allowed_args(ElementAllowance):
    """The given *function* should accept a number of arguments equal
    the given elements in the 'args' attribute. If args is a single
    value (string or otherwise), *function* should accept one argument.
    If args is a three-tuple, *function* should accept three arguments.
    """
    def __init__(self, function, msg=None):
        @functools.wraps(function)
        def wrapped(_, difference):
            args = difference.args
            if isinstance(args, BaseElement):
                return function(args)
            return function(*args)
        super(allowed_args, self).__init__(wrapped, msg)


class allowed_limit(BaseAllowance):
    def __init__(self, number, msg=None):
        self.number = number
        self.or_predicate = None
        self.and_predicate = None
        super(allowed_limit, self).__init__(msg)

    def filterfalse(self, iterable):
        number = self.number                # Reduce the number of
        or_predicate = self.or_predicate    # dot-lookups--these are
        and_predicate = self.and_predicate  # referenced many times.

        iterable = iter(iterable)  # Must be consumable.
        matching = []
        for key, diff in iterable:
            if or_predicate and or_predicate(key, diff):
                continue
            if and_predicate and not and_predicate(key, diff):
                yield key, diff
                continue
            matching.append((key, diff))
            if len(matching) > number:
                break

        if len(matching) > number:
            for key, diff in itertools.chain(matching, iterable):
                yield key, diff

    def apply_filterfalse(self, iterable):
        if _is_mapping_type(iterable):
            return super(allowed_limit, self).apply_filterfalse(iterable)  # <- EXIT!

        iterable = ((None, diff) for diff in iterable)
        filtered = super(allowed_limit, self).apply_filterfalse(iterable)
        return (diff for key, diff in filtered)  # 'key' intentionally discarded

    def __or__(self, other):
        if not isinstance(other, ElementAllowance):
            return NotImplemented

        allowance = allowed_limit(self.number, self.msg)
        allowance.and_predicate = self.and_predicate  # Copy 'and' as-is.
        if not self.or_predicate:
            allowance.or_predicate = other.predicate
        else:
            pred1 = self.or_predicate
            pred2 = other.predicate
            def predicate(*args, **kwds):
                return pred1(*args, **kwds) or pred2(*args, **kwds)
            allowance.or_predicate = predicate
        return allowance

    def __ror__(self, other):
        return self.__or__(other)

    def __and__(self, other):
        if not isinstance(other, ElementAllowance):
            return NotImplemented

        allowance = allowed_limit(self.number, self.msg)
        allowance.or_predicate = self.or_predicate  # Copy 'or' as-is.
        if not self.and_predicate:
            allowance.and_predicate = other.predicate
        else:
            pred1 = self.and_predicate
            pred2 = other.predicate
            def predicate(*args, **kwds):
                return pred1(*args, **kwds) and pred2(*args, **kwds)
            allowance.and_predicate = predicate
        return allowance

    def __rand__(self, other):
        return self.__and__(other)
