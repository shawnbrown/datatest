# -*- coding: utf-8 -*-
import inspect
from functools import wraps
from math import isnan
from numbers import Number
from .utils.builtins import *
from .utils import collections
from .utils import functools
from .utils import itertools

from .dataaccess import _is_collection_of_items
from .dataaccess import DictItems
from .errors import ValidationError

from .utils.misc import _is_consumable
from .utils.misc import _is_nsiterable
from .utils.misc import _get_arg_lengths
from .utils.misc import _expects_multiple_params
from .utils.misc import _make_decimal
from .errors import Missing
from .errors import Extra
from .errors import Deviation


__datatest = True  # Used to detect in-module stack frames (which are
                   # omitted from output).


def _is_mapping_type(obj):
    return isinstance(obj, collections.Mapping) or \
                _is_collection_of_items(obj)


class BaseAllowance(object):
    """Context manager to allow certain data errors without
    triggering a test failure. *filterfalse* should accept an
    iterable of data errors and return an iterable of only
    those errors which are **not** allowed.
    """
    def __init__(self, filterfalse, msg=None):
        """Initialize object values."""
        assert callable(filterfalse)
        self.filterfalse = filterfalse
        self.msg = msg

    def __or__(self, other):
        return NotImplemented

    def __and__(self, other):
        return NotImplemented

    def __enter__(self):
        return self

    def apply_filterfalse(self, iterable):
        if isinstance(iterable, collections.Mapping):
            iterable = getattr(iterable, 'iteritems', iterable.items)()

        if _is_collection_of_items(iterable):
            for key, error in iterable:
                if (not _is_nsiterable(error)
                        or isinstance(error, Exception)
                        or isinstance(error, collections.Mapping)):
                    # Error is a single element.
                    filtered = self.filterfalse(iter([(key, error)]))
                    if isinstance(filtered, collections.Mapping):
                        filtered = filtered.items()
                    filtered = list(filtered)
                    if filtered:
                        yield filtered[0]
                else:
                    # Error is a container of multiple elements.
                    error = self.filterfalse((key, e) for e in error)
                    error = list(e for key, e in error)
                    if error:
                        yield key, error
        else:
            filtered = self.filterfalse(iterable)
            if _is_mapping_type(filtered):
                raise TypeError('returned mapping output for non-mapping input')
            for error in filtered:
                yield error

    def __exit__(self, exc_type, exc_value, tb):
        # Apply filterfalse or reraise non-validation error.
        if not exc_type:
            errors = self.apply_filterfalse([])
        elif issubclass(exc_type, ValidationError):
            errors = self.apply_filterfalse(exc_value.errors)
        else:
            raise exc_value

        # Check container types.
        mappable_in = _is_mapping_type(getattr(exc_value, 'errors', False))
        mappable_out = _is_mapping_type(errors)

        # Check if any errors were returned.
        try:
            first_item = next(iter(errors))
            if _is_consumable(errors):  # Rebuild if consumable.
                errors = itertools.chain([first_item], errors)
        except StopIteration:
            return True  # <- EXIT!

        # Handle mapping input with iterable-of-items output.
        if (mappable_in and not mappable_out
                and isinstance(first_item, collections.Sized)
                and len(first_item) == 2):
            errors = DictItems(errors)
            mappable_out = True

        # Verify type compatibility.
        if mappable_in != mappable_out:
            message = ('{0} received {1!r} collection but '
                       'returned incompatible {2!r} collection')
            filter_name = getattr(self.filterfalse, '__name__',
                                  repr(self.filterfalse))
            output_cls = errors.__class__.__name__
            input_cls = exc_value.errors.__class__.__name__
            raise TypeError(message.format(filter_name, input_cls, output_cls))

        # Re-raise ValidationError() with remaining errors.
        message = getattr(exc_value, 'message', '')
        if self.msg:
            message = '{0}: {1}'.format(self.msg, message)
        exc = ValidationError(message, errors)
        exc.__cause__ = None  # <- Suppress context using verbose
        raise exc             #    alternative to support older Python
                              #    versions--see PEP 415 (same as
                              #    effect as "raise ... from None").


class ElementAllowance(BaseAllowance):
    """Allow errors where *predicate* returns True. For each
    error, *predicate* will receive two arguments---a **key**
    and **error**---and should return True if the error is
    allowed or False if it is not.
    """
    def __init__(self, predicate, msg=None):
        self.predicate = predicate
        super(ElementAllowance, self).__init__(self.filterfalse, msg)

    def filterfalse(self, iterable):
        predicate = self.predicate
        for key, error in iterable:
            if not predicate(key, error):
                yield key, error

    def apply_filterfalse(self, iterable):
        if isinstance(iterable, collections.Mapping):
            iterable = getattr(iterable, 'iteritems', iterable.items)()

        if _is_collection_of_items(iterable):
            return super(ElementAllowance, self).apply_filterfalse(iterable)

        iterable = ((None, error) for error in iterable)
        filtered = super(ElementAllowance, self).apply_filterfalse(iterable)
        return (error for key, error in filtered)  # 'key' intentionally discarded

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


class allow_missing(ElementAllowance):
    def __init__(self, msg=None):
        def is_missing(_, error):
            return isinstance(error, Missing)
        super(allow_missing, self).__init__(is_missing, msg)


class allow_extra(ElementAllowance):
    def __init__(self, msg=None):
        def is_extra(_, error):
            return isinstance(error, Extra)
        super(allow_extra, self).__init__(is_extra, msg)


def _prettify_devsig(method):
    """Prettify signature of deviation __init__ classes by patching
    its signature to make the "tolerance" syntax the default option
    when introspected (with an IDE, REPL, or other user interface).
    This helper function is intended for internal use.
    """
    assert method.__name__ == '__init__'
    try:
        signature = inspect.signature(method)
    except AttributeError:  # Not supported in Python 3.2 or older.
        return  # <- EXIT!

    parameters = [
        inspect.Parameter('self', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('tolerance', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('msg', inspect.Parameter.POSITIONAL_OR_KEYWORD),
    ]
    method.__signature__ = signature.replace(parameters=parameters)


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


class allow_deviation(ElementAllowance):
    """allow_deviation(tolerance, /, msg=None)
    allow_deviation(lower, upper, msg=None)

    Context manager that allows Deviations within a given tolerance
    without triggering a test failure.

    See documentation for full details.
    """
    def __init__(self, lower, upper=None, msg=None):
        lower, upper, msg = _normalize_devargs(lower, upper, msg)
        def tolerance(_, error):  # <- Closes over lower & upper.
            deviation = error.deviation or 0.0
            if isnan(deviation) or isnan(error.expected or 0.0):
                return False
            return lower <= deviation <= upper
        super(allow_deviation, self).__init__(tolerance, msg)
_prettify_devsig(allow_deviation.__init__)


class allow_percent_deviation(ElementAllowance):
    def __init__(self, lower, upper=None, msg=None):
        lower, upper, msg = _normalize_devargs(lower, upper, msg)
        def percent_tolerance(_, error):  # <- Closes over lower & upper.
            percent_deviation = error.percent_deviation
            if isnan(percent_deviation) or isnan(error.expected or 0):
                return False
            return lower <= percent_deviation <= upper
        super(allow_percent_deviation, self).__init__(percent_tolerance, msg)
_prettify_devsig(allow_percent_deviation.__init__)


class allow_specified(BaseAllowance):
    def __init__(self, errors, msg=None):
        if _is_collection_of_items(errors):
            errors = dict(errors)
        self.errors = errors
        super(allow_specified, self).__init__(self.grpfltrfalse, msg)

    def grpfltrfalse(self, iterable):
        if isinstance(self.errors, collections.Mapping):
            iterable = iter(iterable)
            first_key, first_error = next(iterable)
            iterable = itertools.chain([(first_key, first_error)], iterable)
            allowed = self.errors.get(first_key, [])
        else:
            allowed = self.errors

        if isinstance(allowed, Exception):
            allowed = [allowed]
        else:
            allowed = list(allowed)  # Make list or copy existing list.

        for key, error in iterable:
            try:
                allowed.remove(error)
            except ValueError:
                yield key, error

        if allowed:  # If there are left-over errors.
            key_repr = '{0!r}: '.format(key) if key else ''
            message = 'allowed errors not found: {0}{1!r}'
            exc = ValueError(message.format(key_repr, allowed))
            exc.__cause__ = None
            raise exc

    def apply_filterfalse(self, iterable):
        if isinstance(iterable, collections.Mapping):
            iterable = getattr(iterable, 'iteritems', iterable.items)()

        if _is_collection_of_items(iterable):
            return super(allow_specified, self).apply_filterfalse(iterable)  # <- EXIT!

        if _is_mapping_type(self.errors):
            message = ('{0!r} of errors cannot be matched using {1!r} '
                       'of allowances, requires non-mapping type')
            message = message.format(iterable.__class__.__name__,
                                     self.errors.__class__.__name__)
            raise ValueError(message)

        iterable = ((None, error) for error in iterable)
        filtered = super(allow_specified, self).apply_filterfalse(iterable)
        return (error for key, error in filtered)  # 'key' intentionally discarded


class allow_key(ElementAllowance):
    """The given *function* should accept a number of arguments
    equal the given key elements. If key is a single value (string
    or otherwise), *function* should accept one argument. If key
    is a three-tuple, *function* should accept three arguments.
    """
    def __init__(self, function, msg=None):
        @wraps(function)
        def wrapped(key, _):
            if _is_nsiterable(key):
                return function(*key)
            return function(key)
        super(allow_key, self).__init__(wrapped, msg)


class allow_args(ElementAllowance):
    """The given *function* should accept a number of arguments equal
    the given elements in the 'args' attribute. If args is a single
    value (string or otherwise), *function* should accept one argument.
    If args is a three-tuple, *function* should accept three arguments.
    """
    def __init__(self, function, msg=None):
        @wraps(function)
        def wrapped(_, error):
            args = error.args
            if _is_nsiterable(args):
                return function(*args)
            return function(args)
        super(allow_args, self).__init__(wrapped, msg)


class allow_limit(BaseAllowance):
    def __init__(self, number, msg=None):
        self.number = number
        self.or_predicate = None
        self.and_predicate = None
        super(allow_limit, self).__init__(self.limit_filterfalse, msg)

    def limit_filterfalse(self, iterable):
        number = self.number                # Reduce the number of
        or_predicate = self.or_predicate    # dot-lookups--these are
        and_predicate = self.and_predicate  # referenced many times.

        iterable = iter(iterable)  # Must be consumable.
        matching = []
        for key, value in iterable:
            if or_predicate and or_predicate(key, value):
                continue
            if and_predicate and not and_predicate(key, value):
                yield key, value
                continue
            matching.append((key, value))
            if len(matching) > number:
                break

        if len(matching) > number:
            for key, value in itertools.chain(matching, iterable):
                yield key, value

    def apply_filterfalse(self, iterable):
        if isinstance(iterable, collections.Mapping):
            iterable = getattr(iterable, 'iteritems', iterable.items)()

        if _is_collection_of_items(iterable):
            return super(allow_limit, self).apply_filterfalse(iterable)

        iterable = ((None, error) for error in iterable)
        filtered = super(allow_limit, self).apply_filterfalse(iterable)
        return (error for key, error in filtered)  # 'key' intentionally discarded

    def __or__(self, other):
        if not isinstance(other, ElementAllowance):
            return NotImplemented

        allowance = allow_limit(self.number, self.msg)
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

        allowance = allow_limit(self.number, self.msg)
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
