# -*- coding: utf-8 -*-
from __future__ import division

import collections
import inspect
import re
from unittest import TestCase

from ._builtins import *
from . import _itertools as itertools

from .differences import _make_decimal
from .differences import DataAssertionError
from .differences import BaseDifference
from .differences import Missing
from .differences import Extra
from .differences import Invalid
from .differences import Deviation
from .source import BaseSource
from .sourceresult import CompareSet


__datatest = True  # Used to detect in-module stack frames (which are
                   # omitted from output).

_re_type = type(re.compile(''))


def _walk_diff(diff):
    """Iterate over difference or collection of differences."""
    if isinstance(diff, dict):
        diff = diff.values()
    elif isinstance(diff, BaseDifference):
        diff = (diff,)

    for item in diff:
        if isinstance(item, (dict, list, tuple)):
            for elt2 in _walk_diff(item):
                yield elt2
        else:
            if not isinstance(item, BaseDifference):
                raise TypeError('Object {0!r} is not derived from BaseDifference.'.format(item))
            yield item


class _BaseAllowance(object):
    """Base class for DataTestCase.allow...() context managers."""
    def __init__(self, test_case, msg=None):
        self.test_case = test_case
        self.obj_name = None
        self.msg = msg

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        raise NotImplementedError()

    def _raiseFailure(self, standardMsg, differences):
        msg = self.test_case._formatMessage(self.msg, standardMsg)
        subject = self.test_case.subjectData
        #required = getattr(self.test_case, 'referenceData', None)
        try:
            required = self.test_case.referenceData
        except NameError:
            required = None

        exc = DataAssertionError(msg, differences, subject, required)
        exc.__cause__ = None  # Suppress context (usu. "raise ... from None")
        raise exc             # using verbose alternative to support older
                              # Python versions--see PEP 415.


class _AllowOnly(_BaseAllowance):
    """Context manager for DataTestCase.allowOnly() method."""
    def __init__(self, differences, test_case, msg=None):
        self.differences = differences
        super(_AllowOnly, self).__init__(test_case, msg=None)

    def __exit__(self, exc_type, exc_value, tb):
        diff = getattr(exc_value, 'differences', [])
        message = getattr(exc_value, 'msg', 'No error raised')

        observed = list(_walk_diff(diff))
        allowed = list(_walk_diff(self.differences))
        not_allowed = [x for x in observed if x not in allowed]
        if not_allowed:
            self._raiseFailure(message, not_allowed)  # <- EXIT!

        not_found = [x for x in allowed if x not in observed]
        if not_found:
            message = 'Allowed difference not found'
            self._raiseFailure(message, not_found)  # <- EXIT!
        return True


# TODO: Fix and normalize *msg* handling for all allowance managers.
class _AllowAny(_BaseAllowance):
    """Context manager for DataTestCase.allowAny() method."""
    def __init__(self, test_case, number=None, msg=None, **filter_by):
        if number != None:
            assert number > 0, 'number must be positive'
        self.number = number
        #self.msg = msg
        self.filter_kwds = filter_by
        self.filter_class = BaseDifference
        super(_AllowAny, self).__init__(test_case, msg=None)

    def __exit__(self, exc_type, exc_value, tb):
        differences = getattr(exc_value, 'differences', [])

        filter_class = self.filter_class
        is_class = lambda x: isinstance(x, filter_class)
        rejected_class, matched_class = self._partition(is_class, differences)

        rejected_kwds, matched_kwds = self._partition_kwds(matched_class, **self.filter_kwds)
        not_allowed = itertools.chain(rejected_kwds, rejected_class)

        message = getattr(exc_value, 'msg', '')
        matched_kwds = list(matched_kwds)
        observed = len(matched_kwds)
        if self.number and observed > self.number:
            not_allowed = itertools.chain(matched_kwds, not_allowed)  # Matching diffs go first.
            prefix = 'expected at most {0} matching difference{1}, got {2}: '
            plural = 's' if self.number != 1 else ''
            prefix = prefix.format(self.number, plural, observed)
            message = prefix + message

        not_allowed = list(not_allowed)
        if not_allowed:
            #if self.msg:
            #    message = self.msg + ': ' + message
            self._raiseFailure(message, not_allowed)  # <- EXIT!

        return True

    @classmethod
    def _partition_kwds(cls, differences, **filter_by):
        """Takes an iterable of *differences* and keyword filters,
        returns a 2-tuple of lists containing *nonmatches* and
        *matches* differences.
        """
        if not filter_by:
            return ([], differences)  # <- EXIT!

        for k, v in filter_by.items():
            if isinstance(v, str):
                filter_by[k] = (v,)  # If string, wrap in 1-tuple.
        filter_items = tuple(filter_by.items())

        def matches_filter(obj):
            for k, v in filter_items:
                if (k not in obj.kwds) or (obj.kwds[k] not in v):
                    return False
            return True

        return cls._partition(matches_filter, differences)

    @staticmethod
    def _partition(pred, iterable):
        """Use a predicate to partition entries into false entries and
        true entries.
        """
        t1, t2 = itertools.tee(iterable)
        return itertools.filterfalse(pred, t1), filter(pred, t2)


class _AllowMissing(_AllowAny):
    """Context manager for DataTestCase.allowMissing() method."""
    def __init__(self, test_case, number=None, msg=None, **filter_by):
        super(_AllowMissing, self).__init__(test_case, number, msg, **filter_by)
        self.filter_class = Missing  # <- Only Missing differences.


class _AllowExtra(_AllowAny):
    """Context manager for DataTestCase.allowExtra() method."""
    def __init__(self, test_case, number=None, msg=None, **filter_by):
        super(_AllowExtra, self).__init__(test_case, number, msg, **filter_by)
        self.filter_class = Extra  # <- Only Extra differences.


class _AllowDeviation(_BaseAllowance):
    """Context manager for DataTestCase.allowDeviation() method."""
    def __init__(self, lower, upper, test_case, msg, **filter_by):
        #assert deviation >= 0, 'Tolerance cannot be defined with a negative number.'

        lower = _make_decimal(lower)
        upper = _make_decimal(upper)

        wrap = lambda v: [v] if isinstance(v, str) else v
        self._filter_by = dict((k, wrap(v)) for k, v in filter_by.items())

        self.lower = lower
        self.upper = upper
        super(_AllowDeviation, self).__init__(test_case, msg=None)

    def __exit__(self, exc_type, exc_value, tb):
        differences = getattr(exc_value, 'differences', [])
        message = getattr(exc_value, 'msg', 'No error raised')

        def _not_allowed(obj):
            for k, v in self._filter_by.items():
                if (k not in obj.kwds) or (obj.kwds[k] not in v):
                    return True
            return (obj.value > self.upper) or (obj.value < self.lower)

        not_allowed = [x for x in differences if _not_allowed(x)]
        if not_allowed:
            self._raiseFailure(message, not_allowed)  # <- EXIT!
        return True


class _AllowPercentDeviation(_BaseAllowance):
    """Context manager for DataTestCase.allowPercentDeviation()
    method.
    """
    def __init__(self, deviation, test_case, msg, **filter_by):
        assert 1 >= deviation >= 0, 'Percent tolerance must be between 0 and 1.'
        wrap = lambda v: [v] if isinstance(v, str) else v
        self._filter_by = dict((k, wrap(v)) for k, v in filter_by.items())
        self.deviation = deviation
        super(_AllowPercentDeviation, self).__init__(test_case, msg=None)

    def __exit__(self, exc_type, exc_value, tb):
        differences = getattr(exc_value, 'differences', [])
        message = getattr(exc_value, 'msg', 'No error raised')

        def _not_allowed(obj):
            if not obj.required:
                return True  # <- EXIT!
            for k, v in self._filter_by.items():
                if (k not in obj.kwds) or (obj.kwds[k] not in v):
                    return True
            percent = obj.value / obj.required
            return abs(percent) > self.deviation

        failed = [x for x in differences if _not_allowed(x)]
        if failed:
            self._raiseFailure(message, failed)  # <- EXIT!
        return True


class DataTestCase(TestCase):
    """This class wraps ``unittest.TestCase`` and implements additional
    properties and methods for testing data quality.  When a data
    assertion method fails, it raises a ``DataAssertionError``
    containing the detected flaws.  When a non-data failure occurs,
    these methods raise a standard ``AssertionError``.
    """
    @property
    def subjectData(self):
        """Property to access the data being tested---the subject of
        the tests. Typically, ``subjectData`` should be assigned in
        ``setUpModule()`` or ``setUpClass()``.
        """
        if hasattr(self, '_subjectData'):
            return self._subjectData
        return self._find_data_source('subjectData')

    @subjectData.setter
    def subjectData(self, value):
        self._subjectData = value

    @property
    def referenceData(self):
        """Property to access reference data that is trusted to be
        correct. Typically, ``referenceData`` should be assigned in
        ``setUpModule()`` or ``setUpClass()``.
        """
        if hasattr(self, '_referenceData'):
            return self._referenceData
        return self._find_data_source('referenceData')

    @referenceData.setter
    def referenceData(self, value):
        self._referenceData = value

    @staticmethod
    def _find_data_source(name):
        # TODO: Make this method play nice with getattr() when
        # attribute is missing.
        stack = inspect.stack()
        stack.pop()  # Skip record of current frame.
        for record in stack:   # Bubble-up stack looking for name.
            frame = record[0]
            if name in frame.f_globals:
                return frame.f_globals[name]  # <- EXIT!
        raise NameError('cannot find {0!r}'.format(name))

    def _normalize_required(self, required, method, *args, **kwds):
        """If *required* is None, query data from ``referenceData``; if
        it is another data source, query from this other source; else,
        return unchanged.
        """
        if required == None:
            required = self.referenceData

        if isinstance(required, BaseSource):
            fn = getattr(required, method)
            required = fn(*args, **kwds)

        return required

    def assertDataColumns(self, required=None, msg=None):
        """Test that the column names in ``subjectData`` match the
        *required* values.  If *required* is omitted, the column names
        from the ``referenceData`` are used in its place.

        The *required* argument can be a collection, callable, data
        source, or None.
        See :meth:`assertDataSet <datatest.DataTestCase.assertDataSet>`
        for more details.
        """
        subject_set = CompareSet(self.subjectData.columns())
        required_list = self._normalize_required(required, 'columns')
        if subject_set != required_list:
            if msg is None:
                msg = 'different column names'
            self.fail(msg, subject_set.compare(required_list))
        # TODO: Implement callable *required* argument.
        # TODO: Explore the idea of implementing DataList to assert column order.

    def assertDataSet(self, column, required=None, msg=None, **filter_by):
        """Test that the *column* or columns in ``subjectData``
        contains the *required* values. If *required* is omitted,
        values from ``referenceData`` are used in its place.

        *column* (string or sequence of strings):
            Name of the ``subjectData`` column or columns to check.  If
            *column* contains multiple names, the tests will check
            tuples of values.
        *required* (collection, callable, data source, or None):
            If *required* is a set (or other collection), the set of
            *column* values must match the items in this collection.
            If *required* is a function (or other callable), it is used
            as a key which must return True for acceptable values. If
            *required* is a data source, it is used as reference data.
            If *required* is omitted, then ``referenceData`` will be
            used in its place.
        """
        subject_set = self.subjectData.distinct(column, **filter_by)

        if callable(required):
            differences = subject_set.compare(required)
        else:
            required_set = self._normalize_required(required, 'distinct', column, **filter_by)
            if subject_set != required_set:
                differences = subject_set.compare(required_set)
            else:
                differences = None

        if differences:
            if msg is None:
                msg = 'different {0!r} values'.format(column)
            self.fail(msg, differences)

    def assertDataSum(self, column, keys, required=None, msg=None, **filter_by):
        """Test that the sum of *column* in ``subjectData`` when
        grouped by *keys* matches *required* values dict.  If
        *required* is omitted, ``referenceData`` is used in its place.

        The *required* argument can be a dict, callable, data source,
        or None.  See :meth:`assertDataSet
        <datatest.DataTestCase.assertDataSet>` for more details::

            required = {2015: 146564,
                        2016: 152530,
                        2017: 158397}
            self.assertDataSum('income', 'year', required)

        By omitting the *required* argument, the following asserts that
        the sum of "income" in ``subjectData`` matches the sum of
        "income" in ``referenceData`` (for each group of "department"
        and "year" values)::

            self.assertDataSum('income', ['department', 'year'])
        """
        subject_dict = self.subjectData.sum(column, keys, **filter_by)

        if callable(required):
            differences = subject_dict.compare(required)
        else:
            required_dict = self._normalize_required(required, 'sum', column, keys, **filter_by)
            differences = subject_dict.compare(required_dict)

        if differences:
            if not msg:
                msg = 'different {0!r} sums'.format(column)
            self.fail(msg, differences)

    def assertDataCount(self, column, keys, msg=None, **filter_by):
        """Test that the count of subject rows matches the sum of
        reference *column* for each group in *keys*.

        The following asserts that the count of the subject's rows
        matches the sum of the reference's ``employees`` column for
        each group of ``department`` and ``project`` values::

            self.assertDataCount('employees', ['department', 'project'])
        """
        if column not in self.referenceData.columns():
            msg = 'no column named {0!r} in referenceData'.format(column)
            raise AssertionError(msg)

        subject_result = self.subjectData.count(keys, **filter_by)
        reference_result = self.referenceData.sum(column, keys, **filter_by)

        differences = subject_result.compare(reference_result)
        if differences:
            if not msg:
                msg = 'row counts different than {0!r} sums'.format(column)
            self.fail(msg=msg, differences=differences)

    def assertDataRegex(self, column, required, msg=None, **filter_by):
        """Test that *column* in ``subjectData`` contains values that
        match the *required* regular expression.

        The *required* argument must be a string or a compiled regular
        expression object (it can not be omitted).
        """
        subject_result = self.subjectData.distinct(column, **filter_by)
        if not isinstance(required, _re_type):
            required = re.compile(required)
        func = lambda x: required.search(x) is not None

        invalid = subject_result.compare(func)
        if invalid:
            if not msg:
                msg = 'non-matching {0!r} values'.format(column)
            self.fail(msg=msg, differences=invalid)

    def assertDataNotRegex(self, column, required, msg=None, **filter_by):
        """Test that *column* in ``subjectData`` contains values that
        do not match the *required* regular expression.

        The *required* argument must be a string or a compiled regular
        expression object (it can not be omitted).
        """
        subject_result = self.subjectData.distinct(column, **filter_by)
        if not isinstance(required, _re_type):
            required = re.compile(required)
        func = lambda x: required.search(x) is None

        invalid = subject_result.compare(func)
        if invalid:
            if not msg:
                msg = 'matching {0!r} values'.format(column)
            self.fail(msg=msg, differences=invalid)

    def allowOnly(self, differences, msg=None):
        """Context manager to allow specific *differences* without
        triggering a test failure::

            differences = [
                Extra('foo'),
                Missing('bar'),
            ]
            with self.allowOnly(differences):
                self.assertDataSet('column1')

        If the raised differences do not match *differences*, the test
        will fail with a DataAssertionError of the remaining
        differences.

        In the above example, *differences* is a list but it is also
        possible to pass a single difference or a dictionary.

        Using a single difference::

            with self.allowOnly(Extra('foo')):
                self.assertDataSet('column2')

        When using a dictionary, the keys are strings that provide
        context (for future reference and derived reports) and the
        values are the individual difference objects themselves::

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
            with self.allowOnly(differences):
                self.assertDataSum('population', ['town'])
        """
        return _AllowOnly(differences, self, msg)

    def allowAny(self, number=None, msg=None, **filter_by):
        """Allows a given *number* of differences (of any kind) without
        triggering a test failure::

            with self.allowAny(10):  # Allows up to ten differences.
                self.assertDataSet('city_name')

        If *number* is omitted, allows an unlimited number of
        differences as long as they match a given keyword filter::

            with self.allowAny(city_name='not a city'):
                self.assertDataSum('population', ['city_name'])

        If the count of differences exceeds the given *number*, the
        test case will fail with a DataAssertionError containing all
        observed differences.
        """
        return _AllowAny(self, number, msg, **filter_by)

    def allowMissing(self, number=None, msg=None):
        """Context manager to allow for missing values without
        triggering a test failure::

            with self.allowMissing():  # Allows Missing differences.
                self.assertDataSet('column1')
        """
        return _AllowMissing(self, number, msg)

    def allowExtra(self, number=None, msg=None):
        """Context manager to allow for extra values without triggering
        a test failure::

            with self.allowExtra():  # Allows Extra differences.
                self.assertDataSet('column1')
        """
        return _AllowExtra(self, number, msg)

    def allowDeviation(self, lower, upper=None, msg=None, **filter_by):
        """
        allowDeviation(tolerance, /, msg=None, **filter_by)
        allowDeviation(lower, upper, msg=None, **filter_by)

        Context manager to allow for deviations from required
        numeric values without triggering a test failure.

        Allowing deviations of plus-or-minus a given *tolerance*::

            with self.allowDeviation(5):  # tolerance of +/- 5
                self.assertDataSum('column2', keys=['column1'])

        Specifying different *lower* and *upper* bounds::

            with self.allowDeviation(-2, 3):  # tolerance from -2 to +3
                self.assertDataSum('column2', keys=['column1'])

        All deviations within the accepted tolerance range are
        suppressed but those that exceed the range will trigger
        a test failure.
        """
        if msg == None and isinstance(upper, str):  # Adjust positional 'msg'
            upper, msg = None, upper                # for "tolerance" syntax.

        if upper == None:
            tolerance = lower
            assert tolerance >= 0, ('tolerance should not be negative, '
                                    'for full control of lower and upper '
                                    'bounds, use "lower, upper" syntax.')
            lower, upper = -tolerance, tolerance

        assert lower <= 0 <= upper
        return _AllowDeviation(lower, upper, self, msg, **filter_by)

    def allowPercentDeviation(self, deviation, msg=None, **filter_by):
        """Context manager to allow positive or negative numeric
        differences of less than or equal to the given *deviation* as a
        percentage of the matching reference value::

            with self.allowPercentDeviation(0.02):  # Allows +/- 2%
                self.assertDataSum('column2', keys=['column1'])

        If differences exceed *deviation*, the test case will fail with
        a DataAssertionError containing the excessive differences.
        """
        tolerance = _make_decimal(deviation)
        return _AllowPercentDeviation(deviation, self, msg, **filter_by)

    def fail(self, msg, differences=None):
        """Signals a test failure unconditionally, with *msg* for the
        error message.  If *differences* is provided, a
        DataAssertionError is raised instead of an AssertionError.
        """
        if differences:
            try:
                required = self.referenceData
            except NameError:
                required = None
            raise DataAssertionError(msg, differences, self.subjectData, required)
        else:
            raise self.failureException(msg)


# Prettify signature of DataTestCase.allowDeviation() by making "tolerance"
# syntax the default option when introspected.
try:
    _sig = inspect.signature(DataTestCase.allowDeviation)
    _self, _lower, _upper, _msg, _filter_by = _sig.parameters.values()
    _self = _self.replace(kind=inspect.Parameter.POSITIONAL_ONLY)
    _tolerance = inspect.Parameter('tolerance', inspect.Parameter.POSITIONAL_ONLY)
    _sig = _sig.replace(parameters=[_self, _tolerance, _msg, _filter_by])
    DataTestCase.allowDeviation.__signature__ = _sig
except AttributeError:  # Fails for Python 3.2 and earlier.
    pass
