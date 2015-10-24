# -*- coding: utf-8 -*-
from __future__ import division

import collections
import inspect
import pprint
import re
from unittest import TestCase

from .diff import _make_decimal
from .diff import ItemBase
from .diff import MissingItem
from .diff import ExtraItem
from .diff import InvalidItem
from .diff import InvalidNumber
from .queryresult import ResultSet
from .queryresult import ResultMapping


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
    elif isinstance(diff, ItemBase):
        diff = (diff,)

    for item in diff:
        if isinstance(item, (dict, list, tuple)):
            for elt2 in _walk_diff(item):
                yield elt2
        else:
            if not isinstance(item, ItemBase):
                raise TypeError('Object {0!r} is not derived from ItemBase.'.format(item))
            yield item


class _AcceptableBaseContext(object):
    """Base class for DataTestCase.acceptable...() context managers."""
    def __init__(self, accepted, test_case, msg=None):
        self.accepted = accepted
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


class _AcceptableDifference(_AcceptableBaseContext):
    """Context manager for DataTestCase.acceptableDifference() method."""
    def __exit__(self, exc_type, exc_value, tb):
        if exc_value:
            diff = exc_value.diff
            message = exc_value.msg
        else:
            diff = []
            message = 'No error raised'

        diff = list(_walk_diff(diff))
        accepted = list(_walk_diff(self.accepted))
        unaccepted = [x for x in diff if x not in accepted]
        if unaccepted:
            return self._raiseFailure(message, unaccepted)  # <- EXIT!

        accepted_not_found = [x for x in accepted if x not in diff]
        if accepted_not_found:
            message = message + ', accepted difference not found'
            return self._raiseFailure(message, accepted_not_found)  # <- EXIT!

        return True


class _AcceptableAbsoluteTolerance(_AcceptableBaseContext):
    """Context manager for DataTestCase.acceptableTolerance() method."""
    def __init__(self, accepted, test_case, msg, **filter_by):
        assert accepted >= 0, 'Tolerance cannot be defined with a negative number.'
        wrap = lambda v: [v] if isinstance(v, str) else v
        self._filter_by = dict((k, wrap(v)) for k, v in filter_by.items())

        _AcceptableBaseContext.__init__(self, accepted, test_case, msg)

    def __exit__(self, exc_type, exc_value, tb):
        if exc_value:
            difference = exc_value.diff
            message = exc_value.msg
        else:
            difference = []
            message = 'No error raised'

        diff_list = list(_walk_diff(difference))
        failed = [obj for obj in diff_list if not self._acceptable(obj)]

        if failed:
            return self._raiseFailure(message, failed)  # <- EXIT!

        return True

    def _acceptable(self, obj):
        for k, v in self._filter_by.items():
            if (k not in obj.kwds) or (obj.kwds[k] not in v):
                return False
        return abs(obj.diff) <= self.accepted


class _AcceptablePercentTolerance(_AcceptableBaseContext):
    """Context manager for DataTestCase.acceptablePercentTolerance() method."""
    def __init__(self, accepted, test_case, msg, **filter_by):
        assert 1 >= accepted >= 0, 'Percent tolerance must be between 0 and 1.'
        wrap = lambda v: [v] if isinstance(v, str) else v
        self._filter_by = dict((k, wrap(v)) for k, v in filter_by.items())
        _AcceptableBaseContext.__init__(self, accepted, test_case, msg)

    def __exit__(self, exc_type, exc_value, tb):
        if exc_value:
            difference = exc_value.diff
            message = exc_value.msg
        else:
            difference = []
            message = 'No error raised'

        diff_list = list(_walk_diff(difference))
        failed = [obj for obj in diff_list if not self._acceptable(obj)]

        if failed:
            return self._raiseFailure(exc_value.msg, failed)  # <- EXIT!

        return True

    def _acceptable(self, obj):
        if not obj.expected:
            return False  # <- EXIT!
        for k, v in self._filter_by.items():
            if (k not in obj.kwds) or (obj.kwds[k] not in v):
                return False
        percent = obj.diff / obj.expected
        return abs(percent) <= self.accepted


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

    def assertColumnSet(self, ref=None, msg=None):
        """Test that the set of subject columns matches set of reference
        columns.  If *ref* is provided, it is used in-place of the set
        from ``referenceData``.
        """
        subj = self.subjectData.columns()
        if ref == None:
            ref = self.referenceData.columns()

        subj = ResultSet(subj)
        ref = ResultSet(ref)
        if subj != ref:
            if msg is None:
                msg = 'different column names'
            self.fail(msg, subj.compare(ref))

    def assertColumnSubset(self, ref=None, msg=None):
        """Test that the set of subject columns is a subset of reference
        columns.  If *ref* is provided, it is used in-place of the set
        from ``referenceData``.
        """
        subj = self.subjectData.columns()
        if ref == None:
            ref = self.referenceData.columns()

        subj = ResultSet(subj)
        ref = ResultSet(ref)
        if not subj <= ref:
            if msg is None:
                msg = 'different column names'  # found extra columns
            self.fail(msg, subj.compare(ref, op='<='))

    def assertColumnSuperset(self, ref=None, msg=None):
        """Test that the set of subject columns is a superset of reference
        columns.  If *ref* is provided, it is used in-place of the set
        from ``referenceData``.
        """
        subj = self.subjectData.columns()
        if ref == None:
            ref = self.referenceData.columns()

        subj = ResultSet(subj)
        ref = ResultSet(ref)
        if not subj >= ref:
            if msg is None:
                msg = 'different column names'  # missing expected columns
            self.fail(msg, subj.compare(ref, op='>='))

    def assertValueSet(self, column, ref=None, msg=None, **filter_by):
        """Test that the set of subject values matches the set of
        reference values for the given *column*.  If *ref* is provided,
        it is used in place of the set from ``referenceData``.
        """
        subj = self.subjectData.distinct(column, **filter_by)
        if ref == None:
            ref = self.referenceData.distinct(column, **filter_by)

        if subj != ref:
            if msg is None:
                msg = 'different {0!r} values'.format(column)
            self.fail(msg, subj.compare(ref))

    def assertValueSubset(self, column, ref=None, msg=None, **filter_by):
        """Test that the set of subject values is a subset of reference
        values for the given *column*.  If *ref* is provided, it is used
        in-place of the set from ``referenceData``.
        """
        subj = self.subjectData.distinct(column, **filter_by)
        if ref == None:
            ref = self.referenceData.distinct(column, **filter_by)

        if not subj <= ref:
            if msg is None:
                msg = 'different {0!r} values'.format(column)
            self.fail(msg, subj.compare(ref, '<='))

    def assertValueSuperset(self, column, ref=None, msg=None, **filter_by):
        """Test that the set of subject values is a superset of reference
        values for the given *column*.  If *ref* is provided, it is used
        in-place of the set from ``referenceData``.
        """
        subj = self.subjectData.distinct(column, **filter_by)
        if ref == None:
            ref = self.referenceData.distinct(column, **filter_by)

        if not subj >= ref:
            if msg is None:
                msg = 'different {0!r} values'.format(column)
            self.fail(msg, subj.compare(ref, '>='))

    def assertValueSum(self, column, group_by, msg=None, **filter_by):
        """Test that the sum of subject values matches the sum of
        reference values for the given *column* for each group in
        *group_by*.

        The following asserts that the sum of the subject's ``income``
        matches the sum of the reference's ``income`` for each group of
        ``department`` and ``year`` values::

            self.assertValueSum('income', ['department', 'year'])

        """
        subj_vals = self.subjectData.sum2(column, group_by, **filter_by)
        ref_vals = self.referenceData.sum2(column, group_by, **filter_by)

        differences = subj_vals.compare(ref_vals)
        if differences:
            if not msg:
                msg = 'different {0!r} sums'.format(column)
            self.fail(msg=msg, diff=differences)

    def assertValueCount(self, column, group_by, msg=None, **filter_by):
        """Test that the count of subject rows matches the sum of
        reference *column* for each group in *group_by*.

        The following asserts that the count of the subject's rows
        matches the sum of the reference's ``employees`` column for
        each group of ``department`` and ``project`` values::

            self.assertValueCount('employees', ['department', 'project'])

        """
        if column not in self.referenceData.columns():
            msg = 'no column named {0!r} in referenceData'.format(column)
            raise AssertionError(msg)

        subj_vals = self.subjectData.count2(group_by, **filter_by)
        ref_vals = self.referenceData.sum2(column, group_by, **filter_by)

        differences = subj_vals.compare(ref_vals)
        if differences:
            if not msg:
                msg = 'row counts different than {0!r} sums'.format(column)
            self.fail(msg=msg, diff=differences)

    def assertValueRegex(self, column, regex, msg=None, **filter_by):
        """Test that all subject values in *column* match the *regex*
        pattern search.
        """
        subj = self.subjectData.distinct(column, **filter_by)
        if not isinstance(regex, _re_type):
            regex = re.compile(regex)
        func = lambda x: regex.search(x) is not None

        invalid = subj.compare(func)
        if invalid:
            if not msg:
                msg = 'non-matching {0!r} values'.format(column)
            self.fail(msg=msg, diff=invalid)

    def assertValueNotRegex(self, column, regex, msg=None, **filter_by):
        """Test that all subject values in *column* do not match the
        *regex* pattern search.
        """
        subj = self.subjectData.distinct(column, **filter_by)
        if not isinstance(regex, _re_type):
            regex = re.compile(regex)
        func = lambda x: regex.search(x) is None

        invalid = subj.compare(func)
        if invalid:
            if not msg:
                msg = 'matching {0!r} values'.format(column)
            self.fail(msg=msg, diff=invalid)

    def acceptableDifference(self, diff, msg=None):
        """Context manager to accept a given list of differences
        without triggering a test failure::

            diff = [
                ExtraItem('foo'),
                MissingItem('bar'),
            ]
            with self.acceptableDifference(diff):
                self.assertValueSet('column1')

        If the raised differences do not match *diff*, the test will
        fail with a DataAssertionError of the remaining differences.
        """
        return _AcceptableDifference(diff, self, msg)

    def acceptableTolerance(self, tolerance, msg=None, **filter_by):
        """Context manager to accept numeric differences less than or
        equal to the given *tolerance*::

            with self.acceptableTolerance(5):  # Accepts +/- 5
                self.assertValueSum('column2', group_by=['column1'])

        If differences exceed *tolerance*, the test case will fail with
        a DataAssertionError containing the excessive differences.
        """
        tolerance = _make_decimal(tolerance)
        return _AcceptableAbsoluteTolerance(tolerance, self, msg, **filter_by)

    def acceptablePercentTolerance(self, tolerance, msg=None, **filter_by):
        """Context manager to accept numeric difference percentages less
        than or equal to the given *tolerance*::

            with self.acceptablePercentTolerance(0.02):  # Accepts +/- 2%
                self.assertValueSum('column2', group_by=['column1'])

        If differences exceed *tolerance*, the test case will fail with
        a DataAssertionError containing the excessive differences.
        """
        tolerance = _make_decimal(tolerance)
        return _AcceptablePercentTolerance(tolerance, self, msg, **filter_by)

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
