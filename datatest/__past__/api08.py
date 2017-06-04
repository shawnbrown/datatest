"""Backward compatibility for version 0.8 API."""
from __future__ import absolute_import
import datatest


def _columns(self, type=list):  # Removed in datatest 0.8.2
    if type != list:
        return type(self.fieldnames)
    return self.fieldnames
datatest.DataSource.columns = _columns
