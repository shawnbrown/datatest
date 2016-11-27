# -*- coding: utf-8 -*-
"""Backward compatibility for version 0.7.0.dev2 API."""
from __future__ import absolute_import
from datatest import DataTestCase

from datatest import CompareSet


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
