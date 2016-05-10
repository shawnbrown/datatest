# -*- coding: utf-8 -*-
from . import _unittest as unittest
from datatest import DataTestCase

from datatest.runner import DataTestResult
from datatest.runner import skip
from datatest.runner import mandatory
from datatest.runner import _sort_key


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


class TestOrdering(unittest.TestCase):
    def test_sort_key(self):
        # Define and instantiate sample case.
        class SampleCase(unittest.TestCase):
            def test_reference(self):  # <- This line number used as reference.
                pass                         # +1
                                             # +2
            @skip('Testing skip behavior.')  # +3 (first check)
            def test_skipped(self):          # +4
                pass                         # +5
                                             # +6
            @mandatory                       # +7 (second check)
            def test_mandatory(self):        # +8
                pass                         # +9

        # Get line number of undecorated method--this is uses as a
        # reference point from which to determine the required line
        # numbers for the decorated methods.
        reference_case = SampleCase('test_reference')
        _, reference_line_no = _sort_key(reference_case)

        # Test line number of skipped method.
        skipped_case = SampleCase('test_skipped')
        skipped_line_no = reference_line_no + 3
        _, line_no = _sort_key(skipped_case)
        self.assertEqual(skipped_line_no, line_no)

        # Test line number of mandatory method.
        mandatory_case = SampleCase('test_mandatory')
        mandatory_line_no = reference_line_no + 7
        _, line_no = _sort_key(mandatory_case)
        self.assertEqual(mandatory_line_no, line_no)
