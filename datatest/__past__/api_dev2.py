# -*- coding: utf-8 -*-
"""Backward compatibility for version 0.7.0.dev2 API."""
from __future__ import absolute_import
import collections
import re

from datatest.utils.builtins import *

from datatest import DataTestCase
from datatest import CompareSet
from datatest import Extra
from datatest import BaseSource

# Needed for assertEqual() wrapper.
from datatest.compare import CompareSet
from datatest.compare import CompareDict
from datatest.compare import BaseCompare

_re_type = type(re.compile(''))


def _normalize_required(self, required, method, *args, **kwds):
    """If *required* is None, query data from reference; if it is
    another data source, query from this other source; else, return
    unchanged.
    """
    if required == None:
        required = self.reference

    if isinstance(required, BaseSource):
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
        differences = sorted([Extra(x) for x in extras])
        default_msg = 'values in {0!r} are not unique'.format(columns)
        self.fail(msg or default_msg, differences)
DataTestCase.assertSubjectUnique = assertSubjectUnique
