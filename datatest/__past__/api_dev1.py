# -*- coding: utf-8 -*-
"""Backwards compatibility for version 0.6.0.dev1 API."""
from __future__ import absolute_import
from datatest import DataTestCase

DataTestCase.subjectData = DataTestCase.subject
DataTestCase.referenceData = DataTestCase.reference

_wrapped_find_data_source = DataTestCase._find_data_source
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
DataTestCase._find_data_source = staticmethod(_find_data_source)
