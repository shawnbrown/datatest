# -*- coding: utf-8 -*-
from . import _unittest as unittest
from datatest import DataTestCase

from datatest.runner import DataTestResult


class TestDataTestResult(unittest.TestCase):
    def test_is_required(self):
        testresult = DataTestResult()

        class _TestClass(DataTestCase):  # Dummy class.
            def test_method(_self):
                pass

            def runTest(_self):
                pass

        # Not required.
        testcase = _TestClass()
        self.assertFalse(testresult._is_required(testcase))

        # Required class.
        testcase = _TestClass()
        testcase.__datatest_required__ = True
        self.assertTrue(testresult._is_required(testcase))

        # Required method.
        #TODO!!!: Need to make this test.

        # Check non-test-case behavior.
        not_a_testcase = object()
        self.assertFalse(testresult._is_required(not_a_testcase))
