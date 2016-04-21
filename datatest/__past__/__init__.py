# -*- coding: utf-8 -*-
"""Backwards compatibility for phased-out features and behaviors.

To use a feature that is no longer supported in the current version of
datatest, use the following:

    from datatest.__past__ import <feature-name>_<major-version>

For example, importing 'assertions_alpha' would provide backwards
compatibility for the assertion methods that were implemented in the
alpha/pre-release version of datatest.

"""
