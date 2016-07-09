# -*- coding: utf-8 -*-
"""Backwards compatibility for version 0.6.0.dev1 API."""
from __future__ import absolute_import
import inspect
import datatest
from datatest import DataTestCase


DataTestCase.subjectData = property(fget=DataTestCase.subject.fget,
                                    fset=DataTestCase.subject.fset)
DataTestCase.referenceData = property(fget=DataTestCase.reference.fget,
                                      fset=DataTestCase.reference.fset)
DataTestCase.assertDataColumns = DataTestCase.assertSubjectColumns
DataTestCase.assertDataSet = DataTestCase.assertSubjectSet
DataTestCase.assertDataSum = DataTestCase.assertSubjectSum
DataTestCase.assertDataRegex = DataTestCase.assertSubjectRegex
DataTestCase.assertDataNotRegex = DataTestCase.assertSubjectNotRegex
datatest.DataAssertionError = datatest.DataError


_wrapped_find_data_source = DataTestCase._find_data_source
@staticmethod
def _find_data_source(name):
    if name in ('subject', 'subjectData'):
        stack = inspect.stack()
        stack.pop()  # Skip record of current frame.
        for record in stack:
            frame = record[0]
            if 'subject' in frame.f_globals:
                return frame.f_globals['subject']  # <- EXIT!
            if 'subjectData' in frame.f_globals:
                return frame.f_globals['subjectData']  # <- EXIT!
        raise NameError('cannot find {0!r}'.format(name))
    elif name in ('reference', 'referenceData'):
        stack = inspect.stack()
        stack.pop()  # Skip record of current frame.
        for record in stack:
            frame = record[0]
            if 'reference' in frame.f_globals:
                return frame.f_globals['reference']  # <- EXIT!
            if 'referenceData' in frame.f_globals:
                return frame.f_globals['referenceData']  # <- EXIT!
        raise NameError('cannot find {0!r}'.format(name))
    return _wrapped_find_data_source(name)
DataTestCase._find_data_source = _find_data_source


def _normalize_required(self, required, method, *args, **kwds):
    if required == None:
        required = self.referenceData  # <- OLD NAME!
    if isinstance(required, datatest.BaseSource):
        fn = getattr(required, method)
        required = fn(*args, **kwds)
    return required
DataTestCase._normalize_required = _normalize_required


def _assertDataCount(self, column, keys, required=None, msg=None, **kwds_filter):
    subject_dict = self.subject.count(column, keys, **kwds_filter)
    required = self._normalize_required(required, 'sum', column, keys, **kwds_filter)
    msg = msg or 'row counts different than {0!r} sums'.format(column)
    self.assertEqual(subject_dict, required, msg)
DataTestCase.assertDataCount = _assertDataCount