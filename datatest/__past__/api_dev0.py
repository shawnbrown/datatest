# -*- coding: utf-8 -*-
"""Backwards compatibility for version 0.6.0.dev0 API."""
from __future__ import absolute_import
import datatest
from datatest.__past__ import api_dev1

datatest.DataAssertionError = datatest.DataError
