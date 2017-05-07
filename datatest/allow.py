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


class allow_iter(object):
    """Context manager to allow differences without triggering a test
    failure. The *function* should accept an iterable or mapping of
    data errors and return an iterable or mapping of only those errors
    which are **not** allowed.

    .. admonition:: Fun Fact
        :class: note

        :class:`allow_iter` is the base context manager on which all
        other allowances are implemented.
    """
    def __init__(self, function):
        if not callable(function):
            raise TypeError("'function' must be a function or other callable")
        self.function = function

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        # Apply function or reraise non-validation error.
        if issubclass(exc_type, ValidationError):
            errors = self.function(exc_value.errors)
        elif exc_type is None:
            errors = self.function([])
        else:
            raise exc_value

        # Check container types.
        mappable_in = _is_mapping_type(exc_value.errors)
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
            message = ('function received {0!r} collection but '
                       'returned incompatible {1!r} collection')
            output_cls = errors.__class__.__name__
            input_cls = exc_value.errors.__class__.__name__
            raise TypeError(message.format(input_cls, output_cls))

        # Re-raise ValidationError() with remaining errors.
        message = getattr(exc_value, 'message')
        exc = ValidationError(message, errors)
        exc.__cause__ = None  # <- Suppress context using verbose
        raise exc             #    alternative to support older Python
                              #    versions--see PEP 415 (same as
                              #    effect as "raise ... from None").


def getvalue(function):
    def adapted(key, value):  # <- key not used.
        return function(value)
    adapted.__name__ = 'adapted_' + function.__name__
    adapted._decorator = getvalue
    return adapted


def getargs(function):
    def adapted(key, value):  # <- key not used.
        return function(*value.args)
    adapted.__name__ = 'adapted_' + function.__name__
    adapted._decorator = getargs
    return adapted


def getkey(function):
    def adapted(key, value):  # <- value not used.
        if _is_nsiterable(key):
            return function(*key)
        return function(key)
    adapted.__name__ = 'adapted_' + function.__name__
    adapted._decorator = getkey
    return adapted


def getpair(function):
    def adapted(key, value):
        return function(key, value)
    adapted.__name__ = 'adapted_' + function.__name__
    adapted._decorator = getpair
    return adapted


class _allow_element(allow_iter):
    def __init__(self, condition, functions, **kwds):
        msg = kwds.pop('msg', None)
        if kwds:                                  # Emulate keyword-only
            cls_name = self.__class__.__name__    # behavior for Python
            bad_arg =  next(iter(kwds.values()))  # versions 2.7 and 2.6.
            message = '{0}() got an unexpected keyword argument {1!r}'
            raise TypeError(message.format(cls_name, bad_arg))

        def filterfalse(iterable):
            if isinstance(iterable, collections.Mapping):
                iterable = getattr(iterable, 'iteritems', iterable.items)()

            if _is_collection_of_items(iterable):
                normalize = lambda f: f if hasattr(f, '_decorator') else getvalue(f)
                normfunc = tuple(normalize(f) for f in functions)
                wrapfunc = lambda k, v: condition(f(k, v) for f in normfunc)
                for key, value in iterable:
                    if (not _is_nsiterable(value)
                            or isinstance(value, Exception)
                            or isinstance(value, collections.Mapping)):
                        if not wrapfunc(key, value):
                            yield key, value
                    else:
                        values = list(v for v in value if not wrapfunc(key, v))
                        if values:
                            yield key, values
            else:
                for value in iterable:
                    if not condition(f(value) for f in functions):
                        yield value

        super(_allow_element, self).__init__(filterfalse)


class allow_specified(allow_iter):
    def __init__(self, errors, **kwds):
        msg = kwds.pop('msg', None)
        if kwds:                                  # Emulate keyword-only
            cls_name = self.__class__.__name__    # behavior for Python
            bad_arg =  next(iter(kwds.values()))  # versions 2.7 and 2.6.
            message = '{0}() got an unexpected keyword argument {1!r}'
            raise TypeError(message.format(cls_name, bad_arg))

        if _is_collection_of_items(errors):
            errors = dict(errors)
        elif isinstance(errors, Exception):
            errors = [errors]

        def grpfltrfalse(allowed, iterable):
            if isinstance(iterable, Exception):
                iterable = [iterable]

            if isinstance(allowed, Exception):
                allowed = [allowed]
            else:
                allowed = list(allowed)  # Make list or copy existing list.

            for x in iterable:
                try:
                    allowed.remove(x)
                except ValueError:
                    yield x

            if allowed:  # If there are left-over errors.
                message = 'allowed errors not found: {0!r}'
                exc = Exception(message.format(allowed))
                exc.__cause__ = None
                yield exc

        def filterfalse(iterable):
            if isinstance(iterable, collections.Mapping):
                iterable = getattr(iterable, 'iteritems', iterable.items)()

            if _is_collection_of_items(iterable):
                if isinstance(errors, collections.Mapping):
                    for key, group in iterable:
                        try:
                            errors_lst = errors[key]
                            result = list(grpfltrfalse(errors_lst, group))
                            if result:
                                yield key, result
                        except KeyError:
                            yield key, group
                else:
                    errors_lst = list(errors)  # Errors must not be consumable.
                    for key, group in iterable:
                        result = list(grpfltrfalse(errors_lst, group))
                        if result:
                            yield key, result
            else:
                if not _is_mapping_type(errors):
                    for x in grpfltrfalse(errors, iterable):
                        yield x
                else:
                    message = ('{0!r} of errors cannot be matched using {1!r} '
                               'of allowances, requires non-mapping type')
                    message = message.format(iterable.__class__.__name__,
                                             errors.__class__.__name__)
                    raise ValueError(message)

        super(allow_specified, self).__init__(filterfalse)


class allow_any(_allow_element):
    """
    allow_any(function, *[, msg])
    allow_any(func1, func2[, ...][, msg])
    """
    def __init__(self, function, *funcs, **kwds):
        functions = (function,) + funcs
        super(allow_any, self).__init__(any, functions, **kwds)


class allow_all(_allow_element):
    def __init__(self, function, *funcs, **kwds):
        functions = (function,) + funcs
        super(allow_all, self).__init__(all, functions, **kwds)


class allow_missing(allow_all):
    def __init__(self, *funcs, **kwds):
        def is_missing(x):
            return isinstance(x, Missing)
        super(allow_missing, self).__init__(is_missing, *funcs, **kwds)


class allow_extra(allow_all):
    def __init__(self, *funcs, **kwds):
        def is_extra(x):
            return isinstance(x, Extra)
        super(allow_extra, self).__init__(is_extra, *funcs, **kwds)


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
        inspect.Parameter('kwds_func', inspect.Parameter.VAR_KEYWORD),
    ]
    method.__signature__ = signature.replace(parameters=parameters)


def _normalize_devargs(lower, upper, funcs):
    """Normalize deviation allowance arguments to support both
    "tolerance" and "lower, upper" signatures. This helper function
    is intended for internal use.
    """
    if callable(upper):
        funcs = (upper,) + funcs
        upper = None

    if upper == None:
        tolerance = lower
        assert tolerance >= 0, ('tolerance should not be negative, '
                                'for full control of lower and upper '
                                'bounds, use "lower, upper" syntax')
        lower, upper = -tolerance, tolerance
    lower = _make_decimal(lower)
    upper = _make_decimal(upper)
    assert lower <= upper
    return (lower, upper, funcs)


class allow_deviation(allow_all):
    """
    allow_deviation(tolerance, /, *funcs, msg=None)
    allow_deviation(lower, upper, *funcs, msg=None)

    Context manager that allows Deviations within a given tolerance
    without triggering a test failure.

    See documentation for full details.
    """
    def __init__(self, lower, upper=None, *funcs, **kwds):
        lower, upper, funcs = _normalize_devargs(lower, upper, funcs)
        def tolerance(error):  # <- Closes over lower & upper.
            deviation = error.deviation or 0.0
            if isnan(deviation) or isnan(error.expected or 0.0):
                return False
            return lower <= deviation <= upper
        super(allow_deviation, self).__init__(tolerance, *funcs, **kwds)
_prettify_devsig(allow_deviation.__init__)


class allow_percent_deviation(allow_all):
    def __init__(self, lower, upper=None, *funcs, **kwds):
        lower, upper, funcs = _normalize_devargs(lower, upper, funcs)
        def percent_tolerance(error):  # <- Closes over lower & upper.
            percent_deviation = error.percent_deviation
            if isnan(percent_deviation) or isnan(error.expected or 0):
                return False
            return lower <= percent_deviation <= upper
        super(allow_percent_deviation, self).__init__(percent_tolerance, *funcs, **kwds)
_prettify_devsig(allow_percent_deviation.__init__)


class allow_limit(allow_iter):
    def __init__(self, number, *funcs, **kwds):
        msg = kwds.pop('msg', None)
        if kwds:                                  # Emulate keyword-only
            cls_name = self.__class__.__name__    # behavior for Python
            bad_arg =  next(iter(kwds.values()))  # versions 2.7 and 2.6.
            message = '{0}() got an unexpected keyword argument {1!r}'
            raise TypeError(message.format(cls_name, bad_arg))

        normalize = lambda f: f if hasattr(f, '_decorator') else getvalue(f)
        funcs = tuple(normalize(f) for f in funcs)

        def grpfltrfalse(key, group):
            group = iter(group)  # Must be consumable.
            matching = []
            for value in group:
                if all(f(key, value) for f in funcs):  # Closes over 'funcs'.
                    matching.append(value)
                    if len(matching) > number:  # Closes over 'number'.
                        break
                else:
                    yield value
            # If number is exceeded, return all errors.
            if len(matching) > number:
                for value in itertools.chain(matching, group):
                    yield value

        def filterfalse(iterable):
            if isinstance(iterable, collections.Mapping):
                iterable = getattr(iterable, 'iteritems', iterable.items)()

            if _is_collection_of_items(iterable):
                for key, group in iterable:
                    if (not _is_nsiterable(group)
                            or isinstance(group, Exception)
                            or isinstance(group, collections.Mapping)):
                        group = [group]
                    value = list(grpfltrfalse(key, group))
                    if value:
                        yield key, value
            else:
                for f in funcs:  # Closes over 'funcs'.
                    if f._decorator != getvalue:
                        message = 'cannot use {0!r} decorator with {1!r} of errors'
                        dec_name = f._decorator.__name__
                        itr_type = iterable.__class__.__name__
                        raise ValueError(message.format(dec_name, itr_type))

                for value in grpfltrfalse(None, iterable):
                    yield value

        super(allow_limit, self).__init__(filterfalse)
