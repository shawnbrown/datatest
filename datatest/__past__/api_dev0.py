# -*- coding: utf-8 -*-
"""Backwards compatibility for version 0.6.0.dev0 API."""
from __future__ import absolute_import
import datatest
from datatest.__past__ import api_dev1
from datatest import DataTestCase

datatest.DataAssertionError = datatest.DataError


# Allowances.
DataTestCase.allowSpecified = DataTestCase.allowOnly
DataTestCase.allowUnspecified = DataTestCase.allowAny
DataTestCase.allowDeviationPercent = DataTestCase.allowPercentDeviation


# Assertions.
from .api_dev1 import _assertDataCount
DataTestCase.assertValueCount = _assertDataCount

DataTestCase.assertColumnSet = DataTestCase.assertSubjectColumns
DataTestCase.assertValueSet = DataTestCase.assertSubjectSet
DataTestCase.assertValueSum = DataTestCase.assertSubjectSum
DataTestCase.assertValueRegex = DataTestCase.assertSubjectRegex
DataTestCase.assertValueNotRegex = DataTestCase.assertSubjectNotRegex


def _assertColumnSubset(self, ref=None, msg=None):
    """Test that the set of subject columns is a subset of reference
    columns.  If *ref* is provided, it is used in-place of the set
    from ``referenceData``.
    """
    with self.allowMissing():
        self.assertColumnSet(ref, msg)
DataTestCase.assertColumnSubset = _assertColumnSubset


def _assertColumnSuperset(self, ref=None, msg=None):
    """Test that the set of subject columns is a superset of reference
    columns.  If *ref* is provided, it is used in-place of the set
    from ``referenceData``.
    """
    with self.allowExtra():
        self.assertColumnSet(ref, msg)
DataTestCase.assertColumnSuperset = _assertColumnSuperset


def _assertValueSubset(self, column, ref=None, msg=None, **filter_by):
    """Test that the set of subject values is a subset of reference
    values for the given *column*.  If *ref* is provided, it is used
    in place of the set from ``referenceData``.
    """
    with self.allowMissing():
        self.assertValueSet(column, ref, msg, **filter_by)
DataTestCase.assertValueSubset = _assertValueSubset


def _assertValueSuperset(self, column, ref=None, msg=None, **filter_by):
    """Test that the set of subject values is a superset of reference
    values for the given *column*.  If *ref* is provided, it is used
    in place of the set from ``referenceData``.
    """
    with self.allowExtra():
        self.assertValueSet(column, ref, msg, **filter_by)
DataTestCase.assertValueSuperset = _assertValueSuperset
