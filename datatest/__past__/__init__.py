# -*- coding: utf-8 -*-
"""Backwards compatibility for phased-out features and behaviors.

To use a feature that is no longer supported in the current version of
datatest, use the following:

    from datatest.__past__ import api<version-number>

For example, importing 'api07' would provide backwards compatibility
for the API as implemented in the 0.7 version of datatest.
"""
