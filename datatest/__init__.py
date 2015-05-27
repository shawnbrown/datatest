#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datatest.case import DataTestCase
from datatest.case import DataAssertionError
from datatest.datasource import BaseDataSource
from datatest.datasource import SqliteDataSource
from datatest.datasource import CsvDataSource
from datatest.datasource import MultiDataSource
from datatest.diff import ExtraColumn
from datatest.diff import ExtraValue
from datatest.diff import ExtraSum
from datatest.diff import MissingColumn
from datatest.diff import MissingValue
from datatest.diff import MissingSum
from datatest.runner import DataTestRunner
from datatest.main import DataTestProgram
from datatest.main import main

__version__ = '0.0.1a'

__all__ = [
    # Test case.
    'DataTestCase',
    'DataAssertionError',

    # Data sources.
    'BaseDataSource',
    'SqliteDataSource',
    'CsvDataSource',
    'MultiDataSource',

    # Differences.
    'ExtraColumn',
    'ExtraValue',
    'ExtraSum',
    'MissingColumn',
    'MissingValue',
    'MissingSum',

    # Test runner and command-line program.
    'DataTestRunner',
    'DataTestProgram',
    'main',
]
