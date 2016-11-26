# -*- coding: utf-8 -*-
"""Backward compatibility for version 0.7.0.dev2 API."""
from __future__ import absolute_import
from datatest import DataTestCase

from datatest import CompareSet


def assertSubjectColumns(self, required=None, msg=None):
    """Test that the column names of subject match the *required*
    values.  The *required* argument can be a collection, callable,
    data source, or None:

        def test_columns(self):
            required_names = {'col1', 'col2'}
            self.assertSubjectColumns(required_names)

    If *required* is omitted, the column names from reference are used
    in its place:

        def test_columns(self):
            self.assertSubjectColumns()
    """
    subject_set = CompareSet(self.subject.columns())
    required = self._normalize_required(required, 'columns')
    msg = msg or 'different column names'
    self.assertEqual(subject_set, required, msg)
DataTestCase.assertSubjectColumns = assertSubjectColumns
