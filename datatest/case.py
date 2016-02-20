# -*- coding: utf-8 -*-
from __future__ import division

import collections
import inspect
import pprint
import re
from unittest import TestCase

from .diff import _make_decimal
from .diff import BaseDifference
from .diff import MissingItem
from .diff import ExtraItem
from .diff import InvalidItem
from .diff import InvalidNumber
from .source import BaseSource
from .sourceresult import ResultSet
from .sourceresult import ResultMapping


__datatest = True  # Used to detect in-module stack frames (which are
                   # omitted from output).

_re_type = type(re.compile(''))


class DataAssertionError(AssertionError):
    """Data assertion failed."""
    def __init__(self, msg, diff, reference=None, subject=None):
        """Initialize self, store difference for later reference."""
        if not diff:
            raise ValueError('Missing difference.')
        self.diff = diff
        self.msg = msg
        self.reference = str(reference)  # Reference data source or object.
        self.subject = str(subject)  # Subject data source.
        self._verbose = False  # <- Set by DataTestResult if verbose.

        return AssertionError.__init__(self, msg)

    def __repr__(self):
        return self.__class__.__name__ + ': ' + self.__str__()

    def __str__(self):
        diff = pprint.pformat(self.diff, width=1)
        if any([diff.startswith('{') and diff.endswith('}'),
                diff.startswith('[') and diff.endswith(']'),
                diff.startswith('(') and diff.endswith(')')]):
            diff = diff[1:-1]

        if self._verbose:
            msg_extras = '\n\nREFERENCE DATA:\n{0}\nSUBJECT DATA:\n{1}'
            msg_extras = msg_extras.format(self.reference, self.subject)
        else:
            msg_extras = ''

        return '{0}:\n {1}{2}'.format(self.msg, diff, msg_extras)


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

    def _raiseFailure(self, standardMsg, difference):
        msg = self.test_case._formatMessage(self.msg, standardMsg)
        subj = self.test_case.subjectData
        trst = self.test_case.referenceData
        try:
            # For Python 3.x (some 3.2 builds will raise a TypeError
            # while 2.x will raise SyntaxError).
            expr = 'raise DataAssertionError(msg, {0}, subj, trst) from None'
            exec(expr.format(repr(difference)))
        except (SyntaxError, TypeError):
            raise DataAssertionError(msg, difference, subj, trst)  # For Python 2.x


class _AllowSpecified(_BaseAllowance):
    """Context manager for DataTestCase.allowSpecified() method."""
    def __init__(self, differences, test_case, msg=None):
        self.differences = differences
        super(self.__class__, self).__init__(test_case, msg=None)

    def __exit__(self, exc_type, exc_value, tb):
        diff = getattr(exc_value, 'diff', [])
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


class _AllowUnspecified(_BaseAllowance):
    """Context manager for DataTestCase.allowUnspecified() method."""
    def __init__(self, number, test_case, msg=None):
        assert number > 0, 'number must be positive'
        self.number = number
        super(self.__class__, self).__init__(test_case, msg=None)

    def __exit__(self, exc_type, exc_value, tb):
        differences = getattr(exc_value, 'diff', [])
        observed = len(differences)
        if observed > self.number:
            if self.number == 1:
                prefix = 'expected at most 1 difference, got {0}: '.format(observed)
            else:
                prefix = 'expected at most {0} differences, got {1}: '.format(self.number, observed)
            message = prefix + exc_value.msg
            self._raiseFailure(message, differences)  # <- EXIT!
        return True


class _AllowMissing(_BaseAllowance):
    """Context manager for DataTestCase.allowMissing() method."""
    def __exit__(self, exc_type, exc_value, tb):
        diff = getattr(exc_value, 'diff', [])
        message = getattr(exc_value, 'msg', 'No error raised')
        observed = list(diff)
        not_allowed = [x for x in observed if not isinstance(x, MissingItem)]
        if not_allowed:
            self._raiseFailure(message, not_allowed)  # <- EXIT!
        return True


class _AllowExtra(_BaseAllowance):
    """Context manager for DataTestCase.allowExtra() method."""
    def __exit__(self, exc_type, exc_value, tb):
        diff = getattr(exc_value, 'diff', [])
        message = getattr(exc_value, 'msg', 'No error raised')
        observed = list(diff)
        not_allowed = [x for x in observed if not isinstance(x, ExtraItem)]
        if not_allowed:
            self._raiseFailure(message, not_allowed)  # <- EXIT!
        return True


class _AllowDeviation(_BaseAllowance):
    """Context manager for DataTestCase.allowDeviation() method."""
    def __init__(self, deviation, test_case, msg, **filter_by):
        assert deviation >= 0, 'Tolerance cannot be defined with a negative number.'
        wrap = lambda v: [v] if isinstance(v, str) else v
        self._filter_by = dict((k, wrap(v)) for k, v in filter_by.items())

        self.deviation = deviation
        super(self.__class__, self).__init__(test_case, msg=None)

    def __exit__(self, exc_type, exc_value, tb):
        differences = getattr(exc_value, 'diff', [])
        message = getattr(exc_value, 'msg', 'No error raised')

        def _not_allowed(obj):
            for k, v in self._filter_by.items():
                if (k not in obj.kwds) or (obj.kwds[k] not in v):
                    return True
            return abs(obj.diff) > self.deviation  # <- Using abs(...)!

        not_allowed = [x for x in differences if _not_allowed(x)]
        if not_allowed:
            self._raiseFailure(message, not_allowed)  # <- EXIT!
        return True


class _AllowDeviationUpper(_BaseAllowance):
    """Context manager for DataTestCase.allowDeviation() method."""
    def __init__(self, deviation, test_case, msg, **filter_by):
        assert deviation >= 0, 'Tolerance cannot be defined with a negative number.'
        wrap = lambda v: [v] if isinstance(v, str) else v
        self._filter_by = dict((k, wrap(v)) for k, v in filter_by.items())

        self.deviation = deviation
        super(self.__class__, self).__init__(test_case, msg=None)

    def __exit__(self, exc_type, exc_value, tb):
        differences = getattr(exc_value, 'diff', [])
        message = getattr(exc_value, 'msg', 'No error raised')

        def _not_allowed(obj):
            for k, v in self._filter_by.items():
                if (k not in obj.kwds) or (obj.kwds[k] not in v):
                    return True
            return (obj.diff > self.deviation) or (obj.diff < 0)

        not_allowed = [x for x in differences if _not_allowed(x)]
        if not_allowed:
            self._raiseFailure(message, not_allowed)  # <- EXIT!
        return True


class _AllowDeviationLower(_BaseAllowance):
    """Context manager for DataTestCase.allowDeviation() method."""
    def __init__(self, deviation, test_case, msg, **filter_by):
        assert deviation < 0, 'Lower deviation should not be defined with a positive number.'
        wrap = lambda v: [v] if isinstance(v, str) else v
        self._filter_by = dict((k, wrap(v)) for k, v in filter_by.items())

        self.deviation = deviation
        super(self.__class__, self).__init__(test_case, msg=None)

    def __exit__(self, exc_type, exc_value, tb):
        differences = getattr(exc_value, 'diff', [])
        message = getattr(exc_value, 'msg', 'No error raised')

        def _not_allowed(obj):
            for k, v in self._filter_by.items():
                if (k not in obj.kwds) or (obj.kwds[k] not in v):
                    return True
            return (obj.diff < self.deviation) or (obj.diff > 0)

        not_allowed = [x for x in differences if _not_allowed(x)]
        if not_allowed:
            self._raiseFailure(message, not_allowed)  # <- EXIT!
        return True


class _AllowPercentDeviation(_BaseAllowance):
    """Context manager for DataTestCase.allowPercentDeviation() method."""
    def __init__(self, deviation, test_case, msg, **filter_by):
        assert 1 >= deviation >= 0, 'Percent tolerance must be between 0 and 1.'
        wrap = lambda v: [v] if isinstance(v, str) else v
        self._filter_by = dict((k, wrap(v)) for k, v in filter_by.items())
        self.deviation = deviation
        super(self.__class__, self).__init__(test_case, msg=None)

    def __exit__(self, exc_type, exc_value, tb):
        differences = getattr(exc_value, 'diff', [])
        message = getattr(exc_value, 'msg', 'No error raised')

        def _not_allowed(obj):
            if not obj.expected:
                return True  # <- EXIT!
            for k, v in self._filter_by.items():
                if (k not in obj.kwds) or (obj.kwds[k] not in v):
                    return True
            percent = obj.diff / obj.expected
            return abs(percent) > self.deviation

        failed = [x for x in differences if _not_allowed(x)]
        if failed:
            self._raiseFailure(message, failed)  # <- EXIT!
        return True


class DataTestCase(TestCase):
    """This class wraps ``unittest.TestCase`` and implements additional
    properties and methods for testing data quality.  When a data
    assertion fails, this class raises a ``DataAssertionError``
    containing the detected flaws.  When a non-data failure occurs, this
    class raises a standard ``AssertionError``.
    """
    @property
    def subjectData(self):
        """Property to access the data being tested---the subject of the
        tests.  Typically, ``subjectData`` should be assigned in
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
        correct.  Typically, ``referenceData`` should be assigned in
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
        stack = inspect.stack()
        stack.pop()  # Skip record of current frame.
        for record in stack:   # Bubble-up stack looking for name.
            frame = record[0]
            if name in frame.f_globals:
                return frame.f_globals[name]  # <- EXIT!
        raise NameError('cannot find {0!r}'.format(name))

    def _normalize_reference(self, ref, method, *args, **kwds):
        """If *ref* is None, get query result from referenceData; if *ref*
        is a data source, get query result from ref; else, return *ref*
        without changes."""
        if ref == None:
            fn = getattr(self.referenceData, method)
            return fn(*args, **kwds)

        if isinstance(ref, BaseSource):
            fn = getattr(ref, method)
            return fn(*args, **kwds)

        return ref

    def assertDataColumns(self, ref=None, msg=None):
        """Test that the set of subject columns matches set of reference
        columns.  If *ref* is provided, it is used in-place of the set
        from ``referenceData``.
        """
        subject_columns = self.subjectData.columns()
        subject_result = ResultSet(subject_columns)

        reference_columns = self._normalize_reference(ref, 'columns')
        reference_result = ResultSet(reference_columns)

        if subject_result != reference_result:
            if msg is None:
                msg = 'different column names'
            self.fail(msg, subject_result.compare(reference_result))

    def assertDataSet(self, column, ref=None, msg=None, **filter_by):
        """Test that the set of subject values matches the set of
        reference values for the given *column*.  If *ref* is provided,
        it is used in place of the set from ``referenceData``.
        """
        subject_result = self.subjectData.distinct(column, **filter_by)
        reference_result = self._normalize_reference(ref, 'distinct', column, **filter_by)

        if subject_result != reference_result:
            if msg is None:
                msg = 'different {0!r} values'.format(column)
            self.fail(msg, subject_result.compare(reference_result))

    def assertDataSum(self, column, group_by, msg=None, **filter_by):
        """Test that the sum of subject values matches the sum of
        reference values for the given *column* for each group in
        *group_by*.

        The following asserts that the sum of the subject's ``income``
        matches the sum of the reference's ``income`` for each group of
        ``department`` and ``year`` values::

            self.assertDataSum('income', ['department', 'year'])

        """
        subject_result = self.subjectData.sum(column, group_by, **filter_by)
        reference_result = self.referenceData.sum(column, group_by, **filter_by)

        differences = subject_result.compare(reference_result)
        if differences:
            if not msg:
                msg = 'different {0!r} sums'.format(column)
            self.fail(msg=msg, diff=differences)

    def assertDataCount(self, column, group_by, msg=None, **filter_by):
        """Test that the count of subject rows matches the sum of
        reference *column* for each group in *group_by*.

        The following asserts that the count of the subject's rows
        matches the sum of the reference's ``employees`` column for
        each group of ``department`` and ``project`` values::

            self.assertDataCount('employees', ['department', 'project'])

        """
        if column not in self.referenceData.columns():
            msg = 'no column named {0!r} in referenceData'.format(column)
            raise AssertionError(msg)

        subject_result = self.subjectData.count(group_by, **filter_by)
        reference_result = self.referenceData.sum(column, group_by, **filter_by)

        differences = subject_result.compare(reference_result)
        if differences:
            if not msg:
                msg = 'row counts different than {0!r} sums'.format(column)
            self.fail(msg=msg, diff=differences)

    def assertDataRegex(self, column, regex, msg=None, **filter_by):
        """Test that all subject values in *column* match the *regex*
        pattern search.
        """
        subject_result = self.subjectData.distinct(column, **filter_by)
        if not isinstance(regex, _re_type):
            regex = re.compile(regex)
        func = lambda x: regex.search(x) is not None

        invalid = subject_result.compare(func)
        if invalid:
            if not msg:
                msg = 'non-matching {0!r} values'.format(column)
            self.fail(msg=msg, diff=invalid)

    def assertDataNotRegex(self, column, regex, msg=None, **filter_by):
        """Test that all subject values in *column* do not match the
        *regex* pattern search.
        """
        subject_result = self.subjectData.distinct(column, **filter_by)
        if not isinstance(regex, _re_type):
            regex = re.compile(regex)
        func = lambda x: regex.search(x) is None

        invalid = subject_result.compare(func)
        if invalid:
            if not msg:
                msg = 'matching {0!r} values'.format(column)
            self.fail(msg=msg, diff=invalid)

    def allowSpecified(self, diff, msg=None):
        """Context manager to allow specific differences *diff* without
        triggering a test failure::

            diff = [
                ExtraItem('foo'),
                MissingItem('bar'),
            ]
            with self.allowSpecified(diff):
                self.assertDataSet('column1')

        If the raised differences do not match *diff*, the test will
        fail with a DataAssertionError of the remaining differences.

        In the above example, *diff* is a list of differences but it is also
        possible to pass a single difference or a dictionary of differences.

        Using a single difference::

            with self.allowSpecified(ExtraItem('foo')):
                self.assertDataSet('column2')

        When using a dictionary of differences, the keys are strings that
        provide context (for future reference and derived reports) and the
        values are the differences themselves::

            diff = {
                'Totals from state do not match totals from county.': [
                    InvalidNumber(+436, 38032, town='Springfield'),
                    InvalidNumber(-83, 8631, town='Union')
                ],
                'Some small towns were omitted from county report.': [
                    InvalidNumber(-102, 102, town='Anderson'),
                    InvalidNumber(-177, 177, town='Westfield')
                ]
            }
            with self.allowSpecified(diff):
                self.assertDataSum('population', ['town'])

        """
        return _AllowSpecified(diff, self, msg)

    def allowUnspecified(self, number, msg=None):
        """Context manager to allow a given *number* of unspecified
        differences without triggering a test failure::

            with self.allowUnspecified(10):  # Allows up to ten differences.
                self.assertDataSet('column1')

        If the count of differences exceeds the given *number*, the test case
        will fail with a DataAssertionError containing all observed
        differences.
        """
        return _AllowUnspecified(number, self, msg)

    def allowMissing(self, msg=None):
        """Context manager to allow for missing values without triggering a
        test failure::

            with self.allowMissing():  # Allows MissingItem differences.
                self.assertDataSet('column1')

        """
        return _AllowMissing(self, msg)

    def allowExtra(self, msg=None):
        """Context manager to allow for extra values without triggering a
        test failure.

            with self.allowExtra():  # Allows ExtraItem differences.
                self.assertDataSet('column1')

        """
        return _AllowExtra(self, msg)

    def allowDeviation(self, deviation, msg=None, **filter_by):
        """Context manager to allow positive or negative numeric differences
        of less than or equal to the given *deviation*::

            with self.allowDeviation(5):  # Allows +/- 5
                self.assertDataSum('column2', group_by=['column1'])

        If differences exceed *deviation*, the test case will fail with
        a DataAssertionError containing the excessive differences.
        """
        deviation = _make_decimal(deviation)
        return _AllowDeviation(deviation, self, msg, **filter_by)

    def allowDeviationUpper(self, deviation, msg=None, **filter_by):
        """Context manager to allow positive numeric differences of less than
        or equal to the given *deviation*::

            with self.allowDeviationUpper(5):  # Allows from 0 to +5
                self.assertDataSum('column2', group_by=['column1'])

        If differences exceed *deviation*, the test case will fail with
        a DataAssertionError containing the excessive differences.
        """
        deviation = _make_decimal(deviation)
        return _AllowDeviationUpper(deviation, self, msg, **filter_by)

    def allowDeviationLower(self, deviation, msg=None, **filter_by):
        """Context manager to allow negative numeric differences of greater than
        or equal to the given *deviation*::

            with self.allowDeviationLower(-5):  # Allows from -5 to 0
                self.assertDataSum('column2', group_by=['column1'])

        If differences exceed *deviation*, the test case will fail with
        a DataAssertionError containing the excessive differences.
        """
        deviation = _make_decimal(deviation)
        return _AllowDeviationLower(deviation, self, msg, **filter_by)

    def allowPercentDeviation(self, deviation, msg=None, **filter_by):
        """Context manager to allow positive or negative numeric differences
        of less than or equal to the given *deviation* as a percentage of the
        matching reference value::

            with self.allowPercentDeviation(0.02):  # Allows +/- 2%
                self.assertDataSum('column2', group_by=['column1'])

        If differences exceed *deviation*, the test case will fail with
        a DataAssertionError containing the excessive differences.
        """
        tolerance = _make_decimal(deviation)
        return _AllowPercentDeviation(deviation, self, msg, **filter_by)

    def fail(self, msg, diff=None):
        """Signals a test failure unconditionally, with *msg* for the
        error message.  If *diff* is provided, a DataAssertionError is
        raised instead of an AssertionError.
        """
        if diff:
            try:
                reference = self.referenceData
            except NameError:
                reference = None
            raise DataAssertionError(msg, diff, reference, self.subjectData)
        else:
            raise self.failureException(msg)
