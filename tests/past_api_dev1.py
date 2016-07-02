# -*- coding: utf-8 -*-
"""Test __past__.api_dev1 to assure backwards compatibility with first
development-release API.

.. note:: Because this sub-module works by monkey-patching the global
          ``datatest`` package, these tests should be run in a separate
          process.
"""
import unittest


class TestApiDev1(unittest.TestCase):
    def test_api_dev1(self):
        import datatest
        from datatest.__past__ import api_dev1  # <- MONKEY PATCH!!!
        self.assertTrue(hasattr(datatest.DataTestCase, 'subjectData'))
        self.assertTrue(hasattr(datatest.DataTestCase, 'referenceData'))


if __name__ == '__main__':
    unittest.main()
else:
    raise Exception('This test must be run directly or as a subprocess.')
