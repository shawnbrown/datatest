# -*- coding: utf-8 -*-
import inspect
import re
from sys import version_info as _version_info
from unittest import TestCase as _TestCase  # Originial TestCase, not
                                            # compatibility layer.

# Import compatiblity layers.
from . import _io as io
from . import _unittest as unittest
from .common import MinimalSource

# Import code to test.
from datatest.case import DataTestCase
from datatest import DataError
from datatest import Extra
from datatest import Missing
from datatest import Invalid
from datatest import Deviation
from datatest import CsvSource

from datatest import allow_any
from datatest import allow_missing
from datatest import allow_extra
from datatest import allow_deviation
from datatest import allow_percent_deviation
from datatest import allow_limit
from datatest import allow_only


class TestHelperCase(unittest.TestCase):
    """Helper class for subsequent cases."""
    def _run_one_test(self, case, method):
        suite = unittest.TestSuite()
        audit_case = case(method)
        runner = unittest.TextTestRunner(stream=io.StringIO())
        test_result = runner.run(audit_case)
        self.assertEqual(test_result.testsRun, 1, 'Should one run test.')
        if test_result.errors:
            return test_result.errors[0][1]
        if test_result.failures:
            return test_result.failures[0][1]
        return None


class TestSubclass(TestHelperCase):
    def test_subclass(self):
        """DataTestCase should be a subclass of unittest.TestCase."""
        self.assertTrue(issubclass(DataTestCase, _TestCase))


class TestAssertValid(DataTestCase):
    """The assertValid() method should handle all supported validation
    comparisons.  These comparisons are implemented using four separate
    functions (one for each supported *required* type):

    +--------------------------------------------------------------+
    |       Object Comparisons and Returned Difference Type        |
    +-------------------+------------------------------------------+
    |                   |           *required* condition           |
    | *data* under test +------+---------+----------+--------------+
    |                   | set  | mapping | sequence | str or other |
    +===================+======+=========+==========+==============+
    | **set**           | list |         |          | list         |
    +-------------------+------+---------+----------+--------------+
    | **mapping**       | list | dict    |          | dict         |
    +-------------------+------+---------+----------+--------------+
    | **sequence**      | list |         | dict     | dict         |
    +-------------------+------+---------+----------+--------------+
    | **iterable**      | list |         |          | list         |
    +-------------------+------+---------+----------+--------------+
    | **str or other**  |      |         |          | list         |
    +-------------------+------+---------+----------+--------------+

    Currently, this test checks that the appropriate underlying function
    is called given the type of the *required* argument.  For a
    comprehensive test of all underlying functions, see the
    test_compare.py file.
    """
    def test_required_set(self):
        """When *required* is a set, _compare_set() should be called."""
        with self.assertRaises(DataError) as cm:
            required = set([1, 2, 4])
            data = set([1, 2, 3])
            self.assertValid(data, required)

        differences = cm.exception.differences
        self.assertEqual(set(differences), set([Extra(3), Missing(4)]))

        with self.assertRaises(DataError) as cm:
            required = set([1, 2])
            data = {'a': set([1, 2]), 'b': set([1]), 'c': set([1, 2, 3])}
            self.assertValid(data, required)

        differences = cm.exception.differences
        self.assertEqual(differences, {'b': [Missing(2)], 'c': [Extra(3)]})

    def test_required_mapping(self):
        """When *required* is a mapping, _compare_mapping() should be
        called."""
        with self.assertRaises(DataError) as cm:
            required = {'AAA': 'a', 'BBB': 'b', 'CCC': 'c'}
            data = {'AAA': 'a', 'BBB': 'b', 'DDD': 'd'}
            self.assertValid(data, required)

        differences = cm.exception.differences
        self.assertEqual(differences, {'CCC': Missing('c'), 'DDD': Extra('d')})

    def test_required_sequence(self):
        """When *required* is a sequence, _compare_sequence() should be
        called."""
        with self.assertRaises(DataError) as cm:
            required = ['a', 2, 'c', 4]
            data = ['a', 2, 'x', 3]
            self.assertValid(data, required)

        differences = cm.exception.differences
        self.assertEqual = super(DataTestCase, self).assertEqual
        self.assertEqual(differences, {2: Invalid('x', 'c'), 3: Deviation(-1, 4)})

    def test_required_other(self):
        """When *required* is a string or other object, _compare_other()
        should be called."""
        with self.assertRaises(DataError) as cm:
            required = lambda x: x.isupper()
            data = ['AAA', 'BBB', 'ccc', 'DDD']
            self.assertValid(data, required)

        differences = cm.exception.differences
        self.assertEqual = super(DataTestCase, self).assertEqual
        self.assertEqual(differences, {2: Invalid('ccc')})


class TestAssertEqual(unittest.TestCase):
    def test_for_unwrapped_behavior(self):
        """The datatest.DataTestCase class should NOT wrap the
        assertEqual() method of its superclass. In version 0.7.0,
        datatest DID wrap this method--this test should remain part
        of the suite to prevent regression.
        """
        with self.assertRaises(Exception) as cm:
            first  = set([1,2,3,4,5,6,7])
            second = set([1,2,3,4,5,6])
            self.assertEqual(first, second)

        self.assertIsNot(type(cm.exception), DataError)


class TestAllowanceWrappers(unittest.TestCase):
    """Test method wrappers for allowance context managers."""
    def setUp(self):
        class DummyCase(DataTestCase):
            def runTest(self):
                pass
        self.case = DummyCase()

    def test_allowOnly(self):
        cm = self.case.allowOnly([Missing('foo')])
        self.assertTrue(isinstance(cm, allow_only))

    def test_allowAny(self):
        cm = self.case.allowAny(diffs=lambda x: x == 'aaa')
        self.assertTrue(isinstance(cm, allow_any))

    def test_allowMissing(self):
        cm = self.case.allowMissing()
        self.assertTrue(isinstance(cm, allow_missing))

    def test_allowExtra(self):
        cm = self.case.allowExtra()
        self.assertTrue(isinstance(cm, allow_extra))

    def test_allowDeviation(self):
        cm = self.case.allowDeviation(5)
        self.assertTrue(isinstance(cm, allow_deviation))

    def test_allowPercentDeviation(self):
        result = self.case.allowPercentDeviation(5)
        self.assertTrue(isinstance(result, allow_percent_deviation))

    def test_allowLimit(self):
        cm = self.case.allowLimit(10)
        self.assertTrue(isinstance(cm, allow_limit))
