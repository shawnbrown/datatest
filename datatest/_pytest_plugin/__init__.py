# -*- coding: utf-8 -*-
from __future__ import absolute_import

try:
    # Check if the external development version is installed.
    import pytest_datatest as _
    from ._pytest_datatest import version
    from ._pytest_datatest import version_info
except ImportError:
    try:
        # If there's no external plugin, load the bundled version.
        from ._pytest_datatest import pytest_runtest_makereport
        from ._pytest_datatest import version
        from ._pytest_datatest import version_info
    except ImportError:
        # If there's no Pytest support at all, set dummy version numbers.
        version = '0.0.0'
        version_info = (0, 0, 0)
