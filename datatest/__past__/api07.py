# -*- coding: utf-8 -*-
"""Backward compatibility for version 0.7.0.dev2 API."""
from __future__ import absolute_import
import re
from math import isnan
from numbers import Number

import datatest
from datatest.__past__ import api08

from datatest.utils.builtins import *
from datatest.utils import collections
from datatest.utils import itertools
from datatest.utils import functools

from datatest.utils.misc import _make_decimal

from datatest import DataTestCase

# Put error and differences into main namespace.
from datatest.__past__.api07_error import DataError
from datatest.__past__.api07_diffs import xBaseDifference
from datatest.__past__.api07_diffs import xMissing
from datatest.__past__.api07_diffs import xExtra
from datatest.__past__.api07_diffs import xInvalid
from datatest.__past__.api07_diffs import xDeviation
datatest.DataError = DataError
datatest.BaseDifference = xBaseDifference
datatest.Missing = xMissing
datatest.Extra = xExtra
datatest.Invalid = xInvalid
datatest.Deviation = xDeviation

# Needed for assertEqual() wrapper.
from datatest.__past__.api07_comp import CompareSet
from datatest.__past__.api07_comp import CompareDict
from datatest.__past__.api07_comp import BaseCompare

# Put old data source classes into main namespace.
from datatest.sources.adapter import AdapterSource
from datatest.sources.base import BaseSource
from datatest.sources.csv import CsvSource
from datatest.sources.excel import ExcelSource
from datatest.sources.multi import MultiSource
from datatest.sources.pandas import PandasSource
from datatest.sources.sqlite import SqliteBase
from datatest.sources.sqlite import SqliteSource
datatest.AdapterSource = AdapterSource
datatest.BaseSource = BaseSource
datatest.CsvSource = CsvSource
datatest.ExcelSource = ExcelSource
datatest.MultiSource = MultiSource
datatest.PandasSource = PandasSource
datatest.SqliteBase = SqliteBase
datatest.SqliteSource = SqliteSource


_re_type = type(re.compile(''))


def _normalize_required(self, required, method, *args, **kwds):
    """If *required* is None, query data from reference; if it is
    another data source, query from this other source; else, return
    unchanged.
    """
    if required == None:
        required = self.reference

    if isinstance(required, datatest.BaseSource):
        fn = getattr(required, method)
        required = fn(*args, **kwds)

    return required
DataTestCase._normalize_required = _normalize_required


def assertEqual(self, first, second, msg=None):
    """Fail if *first* does not satisfy *second* as determined by
    appropriate validation comparison.

    If *first* and *second* are comparable, a failure will raise a
    DataError containing the differences between the two.

    If the *second* argument is a helper-function (or other
    callable), it is used as a key which must return True for
    acceptable values.
    """
    if not isinstance(first, BaseCompare):
        if isinstance(first, str) or not isinstance(first, collections.Container):
            first = CompareSet([first])
        elif isinstance(first, collections.Set):
            first = CompareSet(first)
        elif isinstance(first, collections.Mapping):
            first = CompareDict(first)

    if callable(second):
        equal = first.all(second)
        default_msg = 'first object contains invalid items'
    else:
        equal = first == second
        default_msg = 'first object does not match second object'

    if not equal:
        differences = first.compare(second)
        self.fail(msg or default_msg, differences)
DataTestCase.assertEqual = assertEqual


def assertSubjectColumns(self, required=None, msg=None):
    """Test that the column names of subject match the *required*
    values.  The *required* argument can be a collection, callable,
    data source, or None.

    If *required* is omitted, the column names from reference are used
    in its place.
    """
    subject_set = CompareSet(self.subject.columns())
    required = self._normalize_required(required, 'columns')
    msg = msg or 'different column names'
    self.assertEqual(subject_set, required, msg)
DataTestCase.assertSubjectColumns = assertSubjectColumns


def assertSubjectSet(self, columns, required=None, msg=None, **kwds_filter):
    """Test that the column or *columns* in subject contain the
    *required* values. If *columns* is a sequence of strings, we can
    check for distinct groups of values.

    If the *required* argument is a helper-function (or other callable),
    it is used as a key which must return True for acceptable values.

    If the *required* argument is omitted, then values from reference
    will be used in its place.
    """
    subject_set = self.subject.distinct(columns, **kwds_filter)
    required = self._normalize_required(required, 'distinct', columns, **kwds_filter)
    msg = msg or 'different {0!r} values'.format(columns)
    self.assertEqual(subject_set, required, msg)
DataTestCase.assertSubjectSet = assertSubjectSet


def assertSubjectSum(self, column, keys, required=None, msg=None, **kwds_filter):
    """Test that the sum of *column* in subject, when grouped by
    *keys*, matches a dict of *required* values.

    If *required* argument is omitted, then values from reference
    are used in its place.
    """
    subject_dict = self.subject.sum(column, keys, **kwds_filter)
    required = self._normalize_required(required, 'sum', column, keys, **kwds_filter)
    msg = msg or 'different {0!r} sums'.format(column)
    self.assertEqual(subject_dict, required, msg)
DataTestCase.assertSubjectSum = assertSubjectSum


def assertSubjectRegex(self, column, required, msg=None, **kwds_filter):
    """Test that *column* in subject contains values that match a
    *required* regular expression.

    The *required* argument must be a string or a compiled regular
    expression object (it can not be omitted).
    """
    subject_result = self.subject.distinct(column, **kwds_filter)
    if not isinstance(required, _re_type):
        required = re.compile(required)
    func = lambda x: required.search(x) is not None
    msg = msg or 'non-matching {0!r} values'.format(column)
    self.assertEqual(subject_result, func, msg)
DataTestCase.assertSubjectRegex = assertSubjectRegex


def assertSubjectNotRegex(self, column, required, msg=None, **kwds_filter):
    """Test that *column* in subject contains values that do **not**
    match a *required* regular expression.

    The *required* argument must be a string or a compiled regular
    expression object (it can not be omitted).
    """
    subject_result = self.subject.distinct(column, **kwds_filter)
    if not isinstance(required, _re_type):
        required = re.compile(required)
    func = lambda x: required.search(x) is None
    msg = msg or 'matching {0!r} values'.format(column)
    self.assertEqual(subject_result, func, msg)
DataTestCase.assertSubjectNotRegex = assertSubjectNotRegex


def assertSubjectUnique(self, columns, msg=None, **kwds_filter):
    """Test that values in column or *columns* of subject are unique.
    Any duplicate values are raised as Extra differences.

    .. warning::

        This method is unoptimized---it performs all operations
        in-memory. Avoid using this method on data sets that exceed
        available memory.

    .. todo::

        Optimize for memory usage (see issue #9 in development
        repository). Move functionality into compare.py when
        preparing for better py.test integration.
    """
    if isinstance(columns, str):
        get_value = lambda row: row[columns]
    elif isinstance(columns, collections.Sequence):
        get_value = lambda row: tuple(row[column] for column in columns)
    else:
        raise TypeError('colums must be str or sequence')

    seen_before = set()
    extras = set()
    for row in self.subject.filter_rows(**kwds_filter):
        values =get_value(row)
        if values in seen_before:
            extras.add(values)
        else:
            seen_before.add(values)

    if extras:
        differences = sorted([xExtra(x) for x in extras])
        default_msg = 'values in {0!r} are not unique'.format(columns)
        self.fail(msg or default_msg, differences)
DataTestCase.assertSubjectUnique = assertSubjectUnique


def fail(self, msg, differences=None):
    if differences:
        try:
            subject = self.subject
        except NameError:
            subject = None
        try:
            required = self.reference
        except NameError:
            required = None
        raise DataError(msg, differences, subject, required)
    else:
        raise self.failureException(msg)
DataTestCase.fail = fail


class allow_iter(object):
    """Context manager to allow differences without triggering a test
    failure.  The *function* should accept an iterable of differences
    and return an iterable of only those differences which are **not**
    allowed.
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
datatest.allow_iter = allow_iter


class allow_only(allow_iter):
    """Context manager to allow specified *differences* without
    triggering a test failure.  If a test fails with some differences
    that have not been allowed, the DataError is re-raised with the
    remaining differences.

    Using a dictionary---keys are strings that provide context (for
    future reference and derived reports) and values are the individual
    differences themselves.
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
        elif isinstance(diff, xBaseDifference):
            diff = (diff,)

        for item in diff:
            if isinstance(item, (dict, list, tuple)):
                for elt2 in cls._walk_diff(item):
                    yield elt2
            else:
                if not isinstance(item, xBaseDifference):
                    raise TypeError('Object {0!r} is not derived from xBaseDifference.'.format(item))
                yield item
datatest.allow_only = allow_only


def allowOnly(self, differences, msg=None):
    return allow_only(differences, msg)
DataTestCase.allowOnly = allowOnly


class allow_limit(allow_iter):
    """Allows a limited *number* of differences (of any type) without
    triggering a test failure.

    If the count of differences exceeds the given *number*, the test
    case will fail with a DataError containing all observed differences.
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
datatest.allow_limit = allow_limit


def allowLimit(self, number, msg=None, **kwds):
    return allow_limit(number, msg, **kwds)
DataTestCase.allowLimit = allowLimit


class allow_any(allow_iter):
    """Allows differences of any type that match the given
    keywords.
    """
    def __init__(self, msg=None, **kwds):
        """Initialize self."""
        if not kwds:
            raise TypeError('requires 1 or more keyword arguments (0 given)')
        function = lambda iterable: iter([])
        function.__name__ = self.__class__.__name__
        super(allow_any, self).__init__(function, msg, **kwds)
datatest.allow_any = allow_any


def allowAny(self, msg=None, **kwds):
    return allow_any(msg, **kwds)
DataTestCase.allowAny = allowAny


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
        def group_filterfalse(group):  # Returns elements where function evals to False.
            return (x for x in group if not function(x))
        super(allow_each, self).__init__(group_filterfalse, msg, **kwds)
datatest.allow_each = allow_each


class allow_missing(allow_each):
    """Allows :class:`Missing` values without triggering a test
    failure::

        with datatest.allow_missing():
            ...
    """
    def __init__(self, msg=None, **kwds):
        function = lambda diff: isinstance(diff, xMissing)
        function.__name__ = self.__class__.__name__
        super(allow_missing, self).__init__(function, msg, **kwds)
datatest.allow_missing = allow_missing


def allowMissing(self, msg=None, **kwds):
    return allow_missing(msg, **kwds)
DataTestCase.allowMissing = allowMissing


class allow_extra(allow_each):
    """Allows :class:`Extra` values without triggering a test
    failure::

        with datatest.allow_extra():
            ...
    """
    def __init__(self, msg=None, **kwds):
        function = lambda diff: isinstance(diff, xExtra)
        function.__name__ = self.__class__.__name__
        super(allow_extra, self).__init__(function, msg, **kwds)
datatest.allow_extra = allow_extra


def allowExtra(self, msg=None, **kwds):
    return allow_extra(msg, **kwds)
DataTestCase.allowExtra = allowExtra


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
    def __init__(self, lower, upper=None, msg=None, **kwds):
        lower, upper, msg = _normalize_deviation_args(lower, upper, msg)
        normalize_numbers = lambda x: x if x else 0
        def function(diff):
            if not isinstance(diff, xDeviation):
                return False
            value = normalize_numbers(diff.value)  # Closes over normalize_numbers().
            required = normalize_numbers(diff.required)
            if isnan(value) or isnan(required):
                return False
            return lower <= value <= upper  # Closes over *lower* and *upper*.
        function.__name__ = self.__class__.__name__
        super(allow_deviation, self).__init__(function, msg, **kwds)
#_prettify_deviation_signature(allow_deviation.__init__)
datatest.allow_deviation = allow_deviation


def allowDeviation(self, lower, upper=None, msg=None, **kwds):
    return allow_deviation(lower, upper, msg, **kwds)
DataTestCase.allowDeviation = allowDeviation


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
    def __init__(self, lower, upper=None, msg=None, **kwds):
        lower, upper, msg = _normalize_deviation_args(lower, upper, msg)
        normalize_numbers = lambda x: x if x else 0
        def function(diff):
            if not isinstance(diff, xDeviation):
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
#_prettify_deviation_signature(allow_percent_deviation.__init__)
datatest.allow_percent_deviation = allow_percent_deviation


def allowPercentDeviation(self, lower, upper=None, msg=None, **kwds):
    return allow_percent_deviation(lower, upper, msg, **kwds)
DataTestCase.allowPercentDeviation = allowPercentDeviation
