# -*- coding: utf-8 -*-
from . import _unittest as unittest
from datatest import DataTestCase

from datatest.runner import DataTestResult


class TestDataTestResult(unittest.TestCase):
    def test_is_mandatory(self):
        testresult = DataTestResult()

        class _TestClass(DataTestCase):  # Dummy class.
            def test_method(_self):
                pass

            def runTest(_self):
                pass

        # Not mandatory.
        testcase = _TestClass()
        self.assertFalse(testresult._is_mandatory(testcase))

        # Mandatory class.
        testcase = _TestClass()
        testcase.__datatest_mandatory__ = True
        self.assertTrue(testresult._is_mandatory(testcase))

        # Mandatory method.
        #TODO!!!: Need to make this test.

        # Check non-test-case behavior.
        not_a_testcase = object()
        self.assertFalse(testresult._is_mandatory(not_a_testcase))
