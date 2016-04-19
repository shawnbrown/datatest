# -*- coding: utf-8 -*-
from __future__ import absolute_import
from datatest import DataTestCase


DataTestCase.assertColumnSet = DataTestCase.assertDataColumns
DataTestCase.assertValueSet = DataTestCase.assertDataSet
DataTestCase.assertValueSum = DataTestCase.assertDataSum
DataTestCase.assertValueCount = DataTestCase.assertDataCount
DataTestCase.assertValueRegex = DataTestCase.assertDataRegex
DataTestCase.assertValueNotRegex = DataTestCase.assertDataNotRegex

def _assertColumnSubset(self, ref=None, msg=None):
    with self.allowMissing():
        self.assertColumnSet(ref, msg)
DataTestCase.assertColumnSubset = _assertColumnSubset

def _assertColumnSuperset(self, ref=None, msg=None):
    with self.allowExtra():
        self.assertColumnSet(ref, msg)
DataTestCase.assertColumnSuperset = _assertColumnSuperset

def _assertValueSubset(self, column, ref=None, msg=None, **filter_by):
    with self.allowMissing():
        self.assertValueSet(column, ref, msg, **filter_by)
DataTestCase.assertValueSubset = _assertValueSubset

def _assertValueSuperset(self, column, ref=None, msg=None, **filter_by):
    with self.allowExtra():
        self.assertValueSet(column, ref, msg, **filter_by)
DataTestCase.assertValueSuperset = _assertValueSuperset
