# -*- coding: utf-8 -*-
import inspect
from math import isnan
from numbers import Number
from .utils.builtins import *
from .utils import collections
from .utils import functools
from .utils import itertools

from .differences import _make_decimal
from .differences import BaseDifference
from .differences import Missing
from .differences import Extra
from .differences import Deviation

from .error import DataError

__datatest = True  # Used to detect in-module stack frames (which are
                   # omitted from output).


class allow_iter(object):
    """Context manager to allow differences without triggering a test
    failure.  The *function* should accept an iterable of differences
    and return an iterable of only those differences which are **not**
    allowed.

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
        if exc_type is None:  # Exception equired.
            msg = getattr(self.function, '__name__', str(self.function))
            exc = AssertionError('No differences found: ' + str(msg))
            exc.__cause__ = None
            raise exc
        elif not issubclass(exc_type, DataError):  # If not DataError, re-raise.
            raise exc_value

        differences = self.function(exc_value.differences)  # Apply function!

        try:  # Get 1st item and rebuild if differences are consumable.
            first_item = next(iter(differences))
            if differences is iter(differences):
                differences = itertools.chain([first_item], differences)
        except StopIteration:  # If no diffs, return True to suppress error.
            return True  # <- EXIT!

        if isinstance(exc_value.differences, collections.Mapping):
            if not isinstance(differences, collections.Mapping):
                is_bad_type = (isinstance(first_item, str) or not
                               isinstance(first_item, collections.Sequence))
                if is_bad_type:
                    type_name = type(first_item).__name__
                    msg = ("mapping update element must be non-string "
                           "sequence; found '{0}' instead")
                    raise TypeError(msg.format(type_name))
                else:
                    if len(first_item) == 2:
                        if not isinstance(first_item[1], BaseDifference):
                            msg = ("mapping update sequence elements should "
                                   "contain values which are subclasses of "
                                   "BaseDifference; found '{0}' instead")
                            type_name = type(first_item[1]).__name__
                            raise TypeError(msg.format(type_name))
                    else:
                        msg = 'mapping update sequence element has length {0}; 2 is required'
                        raise ValueError(msg.format(len(first_item)))

                differences = dict(differences)  # TODO: Explore idea
                                                 # of replacing dict
                                                 # with item-generator.
        else:
            if isinstance(differences, collections.Mapping):
                msg = "input was '{0}' but function returned a mapping"
                type_name = type(exc_value.differences).__name__
                raise TypeError(msg.format(type_name))

        msg = getattr(exc_value, 'msg')
        exc = DataError(msg, differences)
        exc.__cause__ = None  # <- Suppress context using verbose
        raise exc             # alternative to support older Python
                              # versions--see PEP 415 (same as
                              # effect as "raise ... from None").


def _get_arg_lengths(func):
    """Returns a two-tuple containing the number of positional arguments
    as the first item and the number of variable positional arguments as
    the second item.
    """
    try:
        funcsig = inspect.signature(func)
        params_dict = funcsig.parameters
        parameters = params_dict.values()
        args_type = (inspect._POSITIONAL_OR_KEYWORD, inspect._POSITIONAL_ONLY)
        args = [x for x in parameters if x.kind in args_type]
        vararg = [x for x in parameters if x.kind == inspect._VAR_POSITIONAL]
        vararg = vararg.pop() if vararg else None
    except AttributeError:
        try:  # For Python 3.2 and earlier.
            args, vararg = inspect.getfullargspec(func)[:2]
        except AttributeError:  # For Python 2.7 and earlier.
            args, vararg = inspect.getargspec(func)[:2]
    return (len(args), (1 if vararg else 0))


def _expects_multiple_params(func):
    """Returns True if *func* accepts 1 or more positional arguments."""
    arglen, vararglen = _get_arg_lengths(func)
    return (arglen > 1) or (vararglen > 0)


class allow_any(allow_iter):
    """Allows differences that match given keyword functions without
    triggering a teest failure::

        with datatest.allow_any(keys=capitalized):
            ...
    """
    def __init__(self, **kwds_func):
        self._validate_kwds_func(**kwds_func)

        def filterfalse(iterable):
            if isinstance(iterable, collections.Mapping):
                function = self._get_mapping_function(**kwds_func)
                iterable = iterable.items()  # Change to iterable of items.
            else:
                function = self._get_nonmapping_function(**kwds_func)
            return list(x for x in iterable if not function(x))
            # TODO: Explore idea of replacing above list with generator.

        names = (x.__name__ for x in kwds_func.values())
        filterfalse.__name__ = ' and '.join(x for x in names if x)

        super(allow_any, self).__init__(filterfalse)

    @staticmethod
    def _validate_kwds_func(**kwds_func):
        function_types = ('keys', 'diffs', 'items')

        if not kwds_func:
            msg = 'keyword argument required: must be one of {0}'
            msg = msg.format(', '.join(repr(x) for x in function_types))
            raise TypeError(msg)

        for key in kwds_func:
            if key not in function_types:
                msg = "'{0}' is an invalid keyword argument: must be one of {1}"
                types = ', '.join(repr(x) for x in function_types)
                raise TypeError(msg.format(key, types))

    @staticmethod
    def _get_mapping_function(**kwds_func):
        function_list = []

        # Get 'keys', 'diffs' and 'items' functions and adapt arguments
        # to accept dictionary item.
        if 'keys' in kwds_func:
            keys_fn = kwds_func['keys']
            if _expects_multiple_params(keys_fn):
                adapted_fn = lambda item: keys_fn(*item[0])
            else:
                adapted_fn = lambda item: keys_fn(item[0])
            function_list.append(adapted_fn)

        if 'diffs' in kwds_func:
            diffs_fn = kwds_func['diffs']
            adapted_fn = lambda item: diffs_fn(item[1])
            function_list.append(adapted_fn)

        # TODO: Consider implementing something like this...
        #if 'values' in kwds_func:
        #    values_fn = kwds_func['values']
        #    adapted_fn = lambda item: values_fn(item[1].value)
        #    function_list.append(adapted_fn)

        if 'items' in kwds_func:
            items_fn = kwds_func['items']
            args_len, vararg_len = _get_arg_lengths(items_fn)
            if args_len <= 2 and vararg_len == 0:
                if args_len == 2:
                    adapted_fn = lambda item: items_fn(*item)
                else:
                    adapted_fn = lambda item: items_fn(item)
            else:
                adapted_fn = lambda item: items_fn(*(item[0] + (item[1],)))
            function_list.append(adapted_fn)

        if len(function_list) == 1:
            return function_list.pop()
        return lambda x: all(fn(x) for fn in function_list)

    @staticmethod
    def _get_nonmapping_function(**kwds_func):
        if list(kwds_func.keys()) != ['diffs']:
            invalid = set(kwds_func.keys()) - set(['diffs'])
            invalid = ', '.join(repr(x) for x in invalid)
            msg = ("non-mapping iterable, accepts only 'diffs' "
                   "keyword, found {0}".format(invalid))
            exc = ValueError(msg)
            exc.__cause__ = None
            raise exc

        return kwds_func['diffs']


class allow_missing(allow_any):
    """Allows :class:`Missing` values without triggering a test
    failure::

        with datatest.allow_missing():
            ...
    """
    def __init__(self, **kwds_func):
        if 'diffs' in kwds_func:
            diffs_orig = kwds_func.pop('diffs')
            diffs_fn = lambda diff: diffs_orig(diff) and isinstance(diff, Missing)
            diffs_fn.__name__ = diffs_orig.__name__
        else:
            diffs_fn = lambda diff: isinstance(diff, Missing)
            diffs_fn.__name__ = self.__class__.__name__
        kwds_func['diffs'] = diffs_fn
        super(allow_missing, self).__init__(**kwds_func)


class allow_extra(allow_any):
    """Allows :class:`Extra` values without triggering a test
    failure::

        with datatest.allow_extra():
            ...
    """
    def __init__(self, **kwds_func):
        if 'diffs' in kwds_func:
            diffs_orig = kwds_func.pop('diffs')
            diffs_fn = lambda diff: diffs_orig(diff) and isinstance(diff, Extra)
            diffs_fn.__name__ = diffs_orig.__name__
        else:
            diffs_fn = lambda diff: isinstance(diff, Extra)
            diffs_fn.__name__ = self.__class__.__name__
        kwds_func['diffs'] = diffs_fn
        super(allow_extra, self).__init__(**kwds_func)


def _prettify_deviation_signature(method):
    """Helper function intended for internal use.  Prettify signature of
    deviation __init__ classes by patching its signature to make the
    "tolerance" syntax the default option when introspected (with an
    IDE, REPL, or other user interface).
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


def _normalize_lower_upper(lower, upper):
    """Helper function intended for internal use.  Normalize __init__
    arguments for deviation classes to provide support for both
    "tolerance" and "lower, upper" signatures.
    """
    if upper == None:
        tolerance = lower
        assert tolerance >= 0, ('tolerance should not be negative, '
                                'for full control of lower and upper '
                                'bounds, use "lower, upper" syntax')
        lower, upper = -tolerance, tolerance
    lower = _make_decimal(lower)
    upper = _make_decimal(upper)
    assert lower <= upper
    return (lower, upper)


class allow_deviation(allow_any):
    """
    allow_deviation(tolerance, /, msg=None, **kwds_func)
    allow_deviation(lower, upper, msg=None, **kwds_func)

    Context manager that allows Deviations within a given tolerance
    without triggering a test failure.

    See documentation for full details.
    """
    def __init__(self, lower, upper=None, **kwds_func):
        lower, upper = _normalize_lower_upper(lower, upper)
        normalize_numbers = lambda x: x if x else 0
        def function(diff):                      # Function closes over
            if not isinstance(diff, Deviation):  # lower, upper, and
                return False                     # normalize_numbers().
            value = normalize_numbers(diff.value)
            required = normalize_numbers(diff.required)
            if isnan(value) or isnan(required):
                return False
            return lower <= value <= upper
        function.__name__ = self.__class__.__name__

        if 'diffs' in kwds_func:
            diffs_orig = kwds_func.pop('diffs')
            diffs_fn = lambda diff: diffs_orig(diff) and function(diff)
            diffs_fn.__name__ = diffs_orig.__name__
        else:
            diffs_fn = function
            diffs_fn.__name__ = self.__class__.__name__
        kwds_func['diffs'] = diffs_fn
        super(allow_deviation, self).__init__(**kwds_func)
_prettify_deviation_signature(allow_deviation.__init__)


class allow_percent_deviation(allow_any):
    """
    allow_percent_deviation(tolerance, /, msg=None, **kwds_func)
    allow_percent_deviation(lower, upper, msg=None, **kwds_func)

    Context manager that allows Deviations within a given percentage
    of error without triggering a test failure.

    See documentation for full details.
    """
    def __init__(self, lower, upper=None, **kwds_func):
        lower, upper = _normalize_lower_upper(lower, upper)
        normalize_numbers = lambda x: x if x else 0
        def function(diff):                      # Function closes over
            if not isinstance(diff, Deviation):  # lower, upper, and
                return False                     # normalize_numbers().
            value = normalize_numbers(diff.value)
            required = normalize_numbers(diff.required)
            if isnan(value) or isnan(required):
                return False
            if value != 0 and required == 0:
                return False
            percent = value / required if required else 0  # % error calc.
            return lower <= percent <= upper
        function.__name__ = self.__class__.__name__

        if 'diffs' in kwds_func:
            diffs_orig = kwds_func.pop('diffs')
            diffs_fn = lambda diff: diffs_orig(diff) and function(diff)
            diffs_fn.__name__ = diffs_orig.__name__
        else:
            diffs_fn = function
            diffs_fn.__name__ = self.__class__.__name__
        kwds_func['diffs'] = diffs_fn

        super(allow_percent_deviation, self).__init__(**kwds_func)

_prettify_deviation_signature(allow_percent_deviation.__init__)


class allow_limit(allow_any):
    """Context manager to allow a limited *number* of differences (of
    any type) without triggering a test failure::

        with datatest.allow_limit(10):  # Allows up to ten differences.
            ...

    If the count of differences exceeds the given *number*, the test
    will fail with a :class:`DataError` containing all observed
    differences.
    """
    def __init__(self, number, **kwds_func):
        if not kwds_func:
            kwds_func['diffs'] = lambda x: True
        self._validate_kwds_func(**kwds_func)

        def filterfalse(iterable):
            if isinstance(iterable, collections.Mapping):
                function = self._get_mapping_function(**kwds_func)
                iterable = iterable.items()  # Change to iterable of items.
            else:
                function = self._get_nonmapping_function(**kwds_func)

            t1, t2 = itertools.tee(iterable)
            count = 0
            item = next(t1, None)
            while item and count <= number:
                if function(item):
                    count += 1
                item = next(t1, None)

            if count > number:   # If count exceeds number, return all
                return list(t2)  # diffs, else return non-matching only.
            return list(itertools.filterfalse(function, t2))
            # TODO: Explore idea of replacing above list with generator.

        names = (x.__name__ for x in kwds_func.values())
        filterfalse.__name__ = ' and '.join(x for x in names if x)
        super(allow_any, self).__init__(filterfalse)  # <- Calls ancestor method
                                                      #    (not parent method)!


class allow_only(allow_iter):
    """Context manager to allow specified *differences* without
    triggering a test failure::

        differences = [
            Extra('X'),
            Missing('Y')
        ]
        with datatest.allow_only(differences):
            ...

    The *differences* argument can be a :py:obj:`list` or
    :py:obj:`dict` of differences or a single difference.
    """
    def __init__(self, differences):
        def filterfalse(differences, iterable):         # filterfalse() is,
            allowed = collections.Counter(differences)  # later, wrapped to
            not_allowed = []                            # handle either mapping
            for x in iterable:                          # or non-mapping
                if allowed[x]:                          # differences.
                    allowed[x] -= 1
                else:
                    not_allowed.append(x)

            if not_allowed:
                return not_allowed  # <- EXIT!

            not_found = list(allowed.elements())
            if not_found:
                exc = DataError('allowed difference not found', not_found)
                exc.__cause__ = None
                raise exc
            return iter([])

        if not isinstance(differences, collections.Iterable):
            differences = [differences]  # Wrap single-difference as list.

        if isinstance(differences, collections.Mapping):
            @functools.wraps(filterfalse)
            def function(differences, iterable):
                differences = differences.items()
                if isinstance(iterable, collections.Mapping):  # *iterable* must be
                    iterable = iterable.items()                # mapping-compatible
                elif not isinstance(iterable, collections.ItemsView):
                    msg = ('{class_name} expects mapping of differences but '
                           'found {unexpected_type!r} of differences')
                    msg = msg.format(
                        class_name=self.__class__.__name__,
                        unexpected_type=type(iterable).__name__,
                    )
                    raise ValueError(msg)  # *iterable* must be mapping-compatible.
                return filterfalse(differences, iterable)
        else:
            @functools.wraps(filterfalse)
            def function(differences, iterable):
                if isinstance(iterable, collections.Mapping):
                    msg = ('{class_name} expects non-mapping differences but '
                           'found {unexpected_type!r} of differences')
                    msg = msg.format(
                        class_name=self.__class__.__name__,
                        unexpected_type=type(iterable).__name__,
                    )
                    raise ValueError(msg)  # *iterable* must not be mapping.
                return filterfalse(differences, iterable)

        # Change to a function of one argument, with partial(), and pass to
        # parent's __init__().
        function = functools.partial(function, differences)
        super(allow_only, self).__init__(function)
