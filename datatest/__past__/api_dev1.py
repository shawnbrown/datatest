# -*- coding: utf-8 -*-
"""Backwards compatibility for version 0.6.0.dev1 API."""
from __future__ import absolute_import
import datatest
from datatest import DataTestCase

DataTestCase.subjectData = DataTestCase.subject
DataTestCase.referenceData = DataTestCase.reference
DataTestCase.assertDataColumns = DataTestCase.assertSubjectColumns
DataTestCase.assertDataSet = DataTestCase.assertSubjectSet
DataTestCase.assertDataSum = DataTestCase.assertSubjectSum
DataTestCase.assertDataRegex = DataTestCase.assertSubjectRegex
DataTestCase.assertDataNotRegex = DataTestCase.assertSubjectNotRegex
#datatest.DataAssertionError = datatest.DataError


_wrapped_find_data_source = DataTestCase._find_data_source
@staticmethod
def _find_data_source(name):
    if name == 'subject':
        try:
            return _wrapped_find_data_source('subject')
        except NameError:
            return _wrapped_find_data_source('subjectData')
    elif name == 'reference':
        try:
            return _wrapped_find_data_source('reference')
        except NameError:
            return _wrapped_find_data_source('referenceData')
    return _wrapped_find_data_source(name)
DataTestCase._find_data_source = _find_data_source


def _assertDataCount(self, column, keys, required=None, msg=None, **kwds_filter):
    subject_dict = self.subject.count(column, keys, **kwds_filter)
    required = self._normalize_required(required, 'sum', column, keys, **kwds_filter)
    msg = msg or 'row counts different than {0!r} sums'.format(column)
    self.assertEqual(subject_dict, required, msg)
DataTestCase.assertDataCount = _assertDataCount
