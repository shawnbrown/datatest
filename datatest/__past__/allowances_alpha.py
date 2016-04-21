# -*- coding: utf-8 -*-
"""Backwards compatibility for allowance methods from alpha version."""
from __future__ import absolute_import
from datatest import DataTestCase


DataTestCase.allowSpecified = DataTestCase.allowOnly
DataTestCase.allowUnspecified = DataTestCase.allowAny
DataTestCase.allowDeviationPercent = DataTestCase.allowPercentDeviation
