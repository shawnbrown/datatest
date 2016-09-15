# -*- coding: utf-8 -*-
"""Test __past__.api_dev2 to assure backwards compatibility with first
development-release API.

.. note:: Because this sub-module works by monkey-patching the global
          ``datatest`` package, these tests should be run in a separate
          process.
"""
from . import _unittest as unittest
import datatest
from datatest.__past__ import api_dev2  # <- MONKEY PATCH!!!


class TestApiDev2(unittest.TestCase):
    def test_assertEqual_wrapper(self):
        """In the 0.7.0 API, the assertEqual() method should be wrapped
        in a datatest.DataTestCase method of the same name.
        """
        datatest_eq = datatest.DataTestCase.assertEqual
        unittest_eq = unittest.TestCase.assertEqual
        self.assertIsNot(datatest_eq, unittest_eq)


if __name__ == '__main__':
    unittest.main()
else:
    raise Exception('This test must be run directly or as a subprocess.')
