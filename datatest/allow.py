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
    failure.  *function* should accept an iterable of differences and
    return an iterable of only those differences which are not allowed.

    .. note::
        :class:`allow_iter` is the base context manager on which all
        other allowences are implemented.
    """
    def __init__(self, function, msg=None, **kwds):
        assert callable(function), 'must be function or other callable'
        self.function = function
        self.msg = msg
        self.kwds = kwds

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is None:  # <- Values are None when no exeption was raised.
            if self.msg:
                msg = self.msg
            else:
                msg = getattr(self.function, '__name__', str(self.function))
            exc = AssertionError('No differences found: ' + str(msg))
            exc.__cause__ = None
            raise exc

        if not issubclass(exc_type, DataError):
            raise exc_value  # If not DataError, re-raise without changes.

        diffs = exc_value.differences
        rejected_kwds, accepted_kwds = self._partition_kwds(diffs, **self.kwds)
        rejected_func = self.function(accepted_kwds)  # <- Apply function!
        not_allowed = itertools.chain(rejected_kwds, rejected_func)

        not_allowed = list(not_allowed)
        if not_allowed:
            msg = [self.msg, getattr(exc_value, 'msg')]
            msg = ': '.join(x for x in msg if x)
            exc = DataError(msg, not_allowed)
            exc.__cause__ = None  # Suppress context using verbose
            raise exc             # alternative to support older Python
                                  # versions--see PEP 415 (same as
                                  # effect as "raise ... from None").

        return True  # <- Suppress original exception.

    @staticmethod
    def _partition_kwds(differences, **kwds):
        """Takes an iterable of *differences* and keyword filters,
        returns a 2-tuple of lists containing *nonmatches* and
        *matches* differences.
        """
        if not kwds:
            return ([], differences)  # <- EXIT!

        # Normalize values.
        for k, v in kwds.items():
            if isinstance(v, str):
                kwds[k] = (v,)
        filter_items = tuple(kwds.items())

        # Make predicate and partition into "rejected" and "accepted".
        def predicate(obj):
            for k, v in filter_items:  # Closes over filter_items.
                if (k not in obj.kwds) or (obj.kwds[k] not in v):
                    return False
            return True
        t1, t2 = itertools.tee(differences)
        return itertools.filterfalse(predicate, t1), filter(predicate, t2)


class allow_each(allow_iter):
    def __init__(self, function, msg=None, **kwds):
        @functools.wraps(function)
        def filterfalse(iterable):  # Returns elements where function evals to False.
            return (x for x in iterable if not function(x))
        super(allow_each, self).__init__(filterfalse, msg, **kwds)


class allow_any(allow_iter):
    def __init__(self, msg=None, **kwds):
        function = lambda iterable: iter([])
        function.__name__ = self.__class__.__name__
        super(allow_any, self).__init__(function, msg, **kwds)


class allow_extra(allow_each):
    def __init__(self, msg=None, **kwds):
        function = lambda diff: isinstance(diff, Extra)
        function.__name__ = self.__class__.__name__
        super(allow_extra, self).__init__(function, msg, **kwds)


class allow_missing(allow_each):
    def __init__(self, msg=None, **kwds):
        function = lambda diff: isinstance(diff, Missing)
        function.__name__ = self.__class__.__name__
        super(allow_missing, self).__init__(function, msg, **kwds)


class allow_only(allow_iter):
    def __init__(self, differences, msg=None):
        def function(iterable):
            allowed = self._walk_diff(differences)  # <- Closes over *differences*.
            allowed = collections.Counter(allowed)
            not_allowed = []
            for x in iterable:
                if allowed[x]:
                    allowed[x] -= 1
                else:
                    not_allowed.append(x)
            if not_allowed:
                return not_allowed  # <- EXIT!
            not_found = list(allowed.elements())
            if not_found:
                exc = DataError('Allowed difference not found', not_found)
                exc.__cause__ = None
                raise exc
            return iter([])
        function.__name__ = self.__class__.__name__
        super(allow_only, self).__init__(function, msg)

    @classmethod
    def _walk_diff(cls, diff):
        """Iterate over difference or collection of differences."""
        if isinstance(diff, dict):
            diff = diff.values()
        elif isinstance(diff, BaseDifference):
            diff = (diff,)

        for item in diff:
            if isinstance(item, (dict, list, tuple)):
                for elt2 in cls._walk_diff(item):
                    yield elt2
            else:
                if not isinstance(item, BaseDifference):
                    raise TypeError('Object {0!r} is not derived from BaseDifference.'.format(item))
                yield item


class allow_limit(allow_iter):
    def __init__(self, number, msg=None, **kwds):
        if not isinstance(number, Number):
            raise TypeError('number can not be type '+ number.__class__.__name__)

        def function(iterable):
            t1, t2 = itertools.tee(iterable)
            # Consume *number* of items (closes over *number*).
            next(itertools.islice(t1, number, number), None)
            try:
                next(t1)
                too_many = True
            except StopIteration:
                too_many = False
            return t2 if too_many else iter([])
        function.__name__ = self.__class__.__name__

        if not msg:
            msg = 'expected at most {0} matching difference{1}'
            msg = msg.format(number, ('' if number == 1 else 's'))
        super(allow_limit, self).__init__(function, msg, **kwds)


def _prettify_deviation_signature(method):
    """Helper function intended for internal use.  Prettify signature
    of deviation __init__ classes by patching its signature to make
    the "tolerance" syntax the default option when introspected (with
    an IDE, REPL, or other user interface).
    """
    try:
        signature = inspect.signature(method)
        parameters = list(signature.parameters.values())

        if parameters[0].name == 'self':
            _self = parameters.pop(0)
            _self = _self.replace(kind=inspect.Parameter.POSITIONAL_ONLY)
        else:
            _self = None
        _lower, _upper, _msg, _kwds = parameters  # Unpack remaining.

        _tolerance = inspect.Parameter('tolerance', inspect.Parameter.POSITIONAL_ONLY)
        if _self:
            parameters = [_self, _tolerance, _msg, _kwds]
        else:
            parameters = [_tolerance, _msg, _kwds]
        method.__signature__ = signature.replace(parameters=parameters)

    except AttributeError:
        pass  # In Python 3.2 and older, lower/upper syntax is the default.


def _normalize_deviation_args(lower, upper, msg):
    """Helper function intended for internal use.  Normalize __init__
    arguments for deviation classes to provide support for both
    "tolerance" and "lower/upper" signatures.
    """
    if msg == None and isinstance(upper, str):
        msg = upper   # Adjust positional 'msg' for "tolerance" syntax.
        upper = None

    if upper == None:
        tolerance = lower
        assert tolerance >= 0, ('tolerance should not be negative, '
                                'for full control of lower and upper '
                                'bounds, use "lower, upper" syntax')
        lower, upper = -tolerance, tolerance

    assert lower <= upper

    lower = _make_decimal(lower)
    upper = _make_decimal(upper)
    return (lower, upper, msg)


class allow_deviation(allow_each):
    def __init__(self, lower, upper=None, msg=None, **kwds):
        """
        allow_deviation(tolerance, /, msg=None, **kwds)
        allow_deviation(lower, upper, msg=None, **kwds)
        """
        lower, upper, msg = _normalize_deviation_args(lower, upper, msg)
        normalize_numbers = lambda x: x if x else 0
        def function(diff):
            if not isinstance(diff, Deviation):
                return False
            value = normalize_numbers(diff.value)  # Closes over normalize_numbers().
            required = normalize_numbers(diff.required)
            if isnan(value) or isnan(required):
                return False
            return lower <= value <= upper  # Closes over *lower* and *upper*.
        function.__name__ = self.__class__.__name__
        super(allow_deviation, self).__init__(function, msg, **kwds)
_prettify_deviation_signature(allow_deviation.__init__)


class allow_percent_deviation(allow_each):
    def __init__(self, lower, upper=None, msg=None, **kwds):
        """
        allow_percent_deviation(tolerance, /, msg=None, **kwds)
        allow_percent_deviation(lower, upper, msg=None, **kwds)
        """
        lower, upper, msg = _normalize_deviation_args(lower, upper, msg)
        normalize_numbers = lambda x: x if x else 0
        def function(diff):
            if not isinstance(diff, Deviation):
                return False
            value = normalize_numbers(diff.value)  # Closes over normalize_numbers().
            required = normalize_numbers(diff.required)
            if isnan(value) or isnan(required):
                return False
            if value != 0 and required == 0:
                return False
            percent = value / required if required else 0  # % error calc.
            return lower <= percent <= upper  # Closes over *lower* and *upper*.
        function.__name__ = self.__class__.__name__
        super(allow_percent_deviation, self).__init__(function, msg, **kwds)
_prettify_deviation_signature(allow_percent_deviation.__init__)
