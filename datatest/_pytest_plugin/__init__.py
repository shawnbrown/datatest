# -*- coding: utf-8 -*-
from __future__ import absolute_import
from .pytest_datatest import version
from .pytest_datatest import version_info

try:
    import pytest_datatest as _  # Check if development version is installed.
except ImportError:
    # In there's no external plugin, load the bundled version.
    from .pytest_datatest import pytest_runtest_makereport
