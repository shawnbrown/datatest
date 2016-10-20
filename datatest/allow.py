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


class allow_iter2(object):
    def __init__(self, function):
        if not callable(function):
            raise TypeError("'function' must be a function or other callable")
        self.function = function

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is None:  # <- Values are None when no exeption was raised.
            # TODO!!!: Look at getting __doc__ in addition to name for msg.
            msg = getattr(self.function, '__name__', str(self.function))
            exc = AssertionError('No differences found: ' + str(msg))
            exc.__cause__ = None
            raise exc

        if not issubclass(exc_type, DataError):
            raise exc_value  # If not DataError, re-raise without changes.

        differences = self.function(exc_value.differences)  # <- Apply function!

        if isinstance(exc_value.differences, collections.Mapping):
            if not isinstance(differences, collections.Mapping):
                # Get first_item from iterable of differences.
                try:
                    differences = iter(differences)
                    first_item = next(differences)
                    differences = itertools.chain([first_item], differences)  # Rebuild original.
                except StopIteration:
                    first_item = tuple()  # Empty tuple.

                # Check that first_item is usable as a mapping constructor.
                if isinstance(first_item, str) or not isinstance(first_item, collections.Sequence):
                    type_name = type(first_item).__name__
                    msg = ("mapping update element must be non-string sequence; "
                           "found '{0}' instead")
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

                differences = dict(differences)
        else:
            if isinstance(differences, collections.Mapping):
                msg = "input was '{0}' but function returned a mapping"
                type_name = type(exc_value.differences).__name__
                raise TypeError(msg.format(type_name))

        if differences:
            msg = getattr(exc_value, 'msg')
            exc = DataError(msg, differences)
            exc.__cause__ = None  # <- Suppress context using verbose
            raise exc             # alternative to support older Python
                                  # versions--see PEP 415 (same as
                                  # effect as "raise ... from None").

        return True  # <- Suppress original exception.


class allow_iter(object):
    """Context manager to allow differences without triggering a test
    failure.  The *function* should accept an iterable of differences
    and return an iterable of only those differences which are **not**
    allowed::

        def function(iterable):
            for diff in iterable:
                value = str(diff.value)
                is_note = value.startswith('NOTE: ')
                if not is_note:  # Return differences when values
                    yield diff   # DON'T start with "NOTE: ".

        with datatest.allow_iter(function):  # Allows differences that
            ...                              # start with "NOTE: ".

    .. admonition:: Fun Fact
        :class: note

        :class:`allow_iter` is the base context manager on which all
        other allowances are implemented.
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
            exc.__cause__ = None  # <- Suppress context using verbose
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
    """Allows differences for which *function* returns True.  The
    *function* should accept a single difference and return True if the
    difference should be allowed or False if it should not::

        def function(diff):
            value = str(diff.value)            # Returns True if value
            return value.startswith('NOTE: ')  # starts with "NOTE: ".

        with datatest.allow_each(function):    # Allows differences that
            ...                                # start with "NOTE: ".
    """
    def __init__(self, function, msg=None, **kwds):
        @functools.wraps(function)
        def filterfalse(iterable):  # Returns elements where function evals to False.
            return (x for x in iterable if not function(x))
        super(allow_each, self).__init__(filterfalse, msg, **kwds)


class allow_any(allow_iter):
    """Allows differences of any type that match the given
    keywords::

        with datatest.allow_any(town='UNLISTED'):
            ...
    """
    def __init__(self, msg=None, **kwds):
        """Initialize self."""
        if not kwds:
            raise TypeError('requires 1 or more keyword arguments (0 given)')
        function = lambda iterable: iter([])
        function.__name__ = self.__class__.__name__
        super(allow_any, self).__init__(function, msg, **kwds)

class allow_missing(allow_each):
    """Allows :class:`Missing` values without triggering a test
    failure::

        with datatest.allow_missing():
            ...
    """
    def __init__(self, msg=None, **kwds):
        function = lambda diff: isinstance(diff, Missing)
        function.__name__ = self.__class__.__name__
        super(allow_missing, self).__init__(function, msg, **kwds)


class allow_extra(allow_each):
    """Allows :class:`Extra` values without triggering a test
    failure::

        with datatest.allow_extra():
            ...
    """
    def __init__(self, msg=None, **kwds):
        function = lambda diff: isinstance(diff, Extra)
        function.__name__ = self.__class__.__name__
        super(allow_extra, self).__init__(function, msg, **kwds)


class allow_only(allow_iter):
    """Context manager to allow specified *differences* without
    triggering a test failure.  If a test fails with some differences
    that have not been allowed, the :class:`DataError` is re-raised with
    the remaining differences.

    Using a list::

        differences = [
            Extra('foo'),
            Missing('bar'),
        ]
        with datatest.allow_only(differences):
            ...

    Using a single difference::

        with datatest.allow_only(Extra('foo')):
            ...

    Using a dictionary---keys are strings that provide context (for
    future reference and derived reports) and values are the individual
    differences themselves::

        differences = {
            'Totals from state do not match totals from county.': [
                Deviation(+436, 38032, town='Springfield'),
                Deviation(-83, 8631, town='Union')
            ],
            'Some small towns were omitted from county report.': [
                Deviation(-102, 102, town='Anderson'),
                Deviation(-177, 177, town='Westfield')
            ]
        }
        with datatest.allow_only(differences):
            ...
    """
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
    """Allows a limited *number* of differences (of any type) without
    triggering a test failure::

        with datatest.allow_limit(10):  # Allow up to ten differences.
            ...

    If the count of differences exceeds the given *number*, the test
    case will fail with a :class:`DataError` containing all observed
    differences.
    """
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
    """Helper function intended for internal use.  Prettify signature of
    deviation __init__ classes by patching its signature to make the
    "tolerance" syntax the default option when introspected (with an
    IDE, REPL, or other user interface).
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
    """
    allow_deviation(tolerance, /, msg=None, **kwds)
    allow_deviation(lower, upper, msg=None, **kwds)

    Context manager to allow for deviations from required numeric values
    without triggering a test failure.

    Allowing deviations of plus-or-minus a given *tolerance*::

        with datatest.allow_deviation(5):  # tolerance of +/- 5
            ...

    Specifying different *lower* and *upper* bounds::

        with datatest.allow_deviation(-2, 3):  # tolerance from -2 to +3
            ...

    All deviations within the accepted tolerance range are suppressed
    but those outside the range will trigger a test failure.

    When allowing deviations, empty values (like None or empty string)
    are treated as zeros.
    """
    # NOTE: CHANGES TO THE ABOVE DOCSTRING SHOULD BE REPLICATED IN THE
    # DOCUMENTATION (.RST FILE)!  This docstring is not included using
    # the Sphinx "autoclass" directive because there is no way to
    # automatically handle multiple file signatures for Python.
    def __init__(self, lower, upper=None, msg=None, **kwds):
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
    """
    allow_percent_deviation(tolerance, /, msg=None, **kwds)
    allow_percent_deviation(lower, upper, msg=None, **kwds)

    Context manager to allow for deviations from required numeric values
    within a given error percentage without triggering a test failure.

    Allowing deviations of plus-or-minus a given *tolerance*::

        with datatest.allow_percent_deviation(0.02):  # tolerance of +/- 2%
            ...

    Specifying different *lower* and *upper* bounds::

        with datatest.allow_percent_deviation(-0.02, 0.03):  # tolerance from -2% to +3%
            ...

    All deviations within the accepted tolerance range are suppressed
    but those that exceed the range will trigger a test failure.

    When allowing deviations, empty values (like None or empty string)
    are treated as zeros.
    """
    # NOTE: CHANGES TO THE ABOVE DOCSTRING SHOULD BE REPLICATED IN THE
    # DOCUMENTATION (.RST FILE)!  This docstring is not included using
    # the Sphinx "autoclass" directive because there is no way to
    # automatically handle multiple file signatures for Python.
    def __init__(self, lower, upper=None, msg=None, **kwds):
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
