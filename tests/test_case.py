# -*- coding: utf-8 -*-
import inspect
import re
import textwrap
from sys import version_info as _version_info
from unittest import TestCase as _TestCase  # Originial TestCase, not
                                            # compatibility layer.

# Import compatiblity layers.
from . import _io as io
from . import _unittest as unittest

# Import code to test.
from datatest.case import DataTestCase

from datatest._load.dataaccess import DataSource
from datatest._load.dataaccess import DataQuery
from datatest._load.dataaccess import DataResult

from datatest.validation import ValidationError
from datatest.difference import Extra
from datatest.difference import Missing
from datatest.difference import Invalid
from datatest.difference import Deviation

from datatest.allowance import allowed_missing
from datatest.allowance import allowed_extra
from datatest.allowance import allowed_invalid
from datatest.allowance import allowed_deviation
from datatest.allowance import allowed_percent_deviation
from datatest.allowance import allowed_limit
from datatest.allowance import allowed_specific


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
    """
    +-------------------------------------------------------------+
    |   Object Comparisons and Returned *differences* Container   |
    +--------------+----------------------------------------------+
    |              |             *requirement* type               |
    | *data* type  +-------+---------+--------------+-------------+
    |              | set   | mapping | sequence     | other       |
    +==============+=======+=========+==============+=============+
    | **set**      | list  |         |              | list        |
    +--------------+-------+---------+--------------+-------------+
    | **mapping**  | dict  | dict    | dict         | dict        |
    +--------------+-------+---------+--------------+-------------+
    | **sequence** | list  |         | assert error | list        |
    +--------------+-------+---------+--------------+-------------+
    | **iterable** | list  |         |              | list        |
    +--------------+-------+---------+--------------+-------------+
    | **other**    | list  |         |              | diff object |
    +--------------+-------+---------+--------------+-------------+
    """
    def test_nonmapping(self):
        with self.assertRaises(ValidationError) as cm:
            data = set([1, 2, 3])
            required = set([1, 2, 4])
            self.assertValid(data, required)

        differences = cm.exception.differences
        self.assertEqual(differences, [Missing(4), Extra(3)])

    def test_data_mapping(self):
        with self.assertRaises(ValidationError) as cm:
            data = {'a': set([1, 2]), 'b': set([1]), 'c': set([1, 2, 3])}
            required = set([1, 2])
            self.assertValid(data, required)

        differences = cm.exception.differences
        self.assertEqual(differences, {'b': [Missing(2)], 'c': [Extra(3)]})

    def test_required_mapping(self):
        with self.assertRaises(ValidationError) as cm:
            data = {'AAA': 'a', 'BBB': 'x'}
            required = {'AAA': 'a', 'BBB': 'b', 'CCC': 'c'}
            self.assertValid(data, required)

        differences = cm.exception.differences
        self.assertEqual(differences, {'BBB': Invalid('x', 'b'), 'CCC': Missing('c')})

    def test_required_sequence(self):
        """When *required* is a sequence, _compare_sequence() should be
        called.
        """
        with self.assertRaises(ValidationError) as cm:
            data = ['a', 2, 'x', 3]
            required = ['a', 2, 'c', 4]
            self.assertValid(data, required)

        error = cm.exception
        expected = {
            (2, 2): Invalid('x', 'c'),
            (3, 3): Invalid(3, 4),
        }
        self.assertEqual(error.differences, expected)
        self.assertEqual(error.args[0], 'does not match sequence order')

    def test_required_other(self):
        """When *required* is a string or other object, _compare_other()
        should be called.
        """
        with self.assertRaises(ValidationError) as cm:
            required = lambda x: x.isupper()
            data = ['AAA', 'BBB', 'ccc', 'DDD']
            self.assertValid(data, required)

        differences = cm.exception.differences
        self.assertEqual(differences, [Invalid('ccc')])

    def test_maxdiff_propagation(self):
        self.maxDiff = 35  # <- Set custom maxDiff (as number of characters)!
        with self.assertRaises(ValidationError) as cm:
            self.assertValid(set([1, 2, 3, 4, 5, 6]), set([1, 2]))

        expected = """
            does not satisfy set membership (4 differences): [
                Extra(3),
                Extra(4),
                ...

            Diff is too long. Set self.maxDiff to None to see it.
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(str(cm.exception), expected)

    def test_maxdiff_none(self):
        self.maxDiff = None
        with self.assertRaises(ValidationError) as cm:
            self.assertValid(set([1, 2, 3, 4, 5, 6]), set([1, 2]))

        message = str(cm.exception)
        self.assertTrue(message.endswith(']'), 'should show full diff when None')

    def test_query_objects(self):
        source = DataSource([('A', 'B'), ('1', '2'), ('1', '2')])
        query_obj1 = source(['B'])
        query_obj2 = source(['B'])
        self.assertValid(query_obj1, query_obj2)

    def test_result_objects(self):
        result_obj1 = DataResult(['2', '2'], evaluation_type=list)
        result_obj2 = DataResult(['2', '2'], evaluation_type=list)
        self.assertValid(result_obj1, result_obj2)


class TestAssertEqual(unittest.TestCase):
    def test_for_unwrapped_behavior(self):
        """The datatest.DataTestCase class should NOT wrap the
        assertEqual() method of its superclass. In version 0.7.0,
        datatest DID wrap this method--this test should remain part
        of the suite to prevent regression.
        """
        if _version_info >= (3, 1):
            self.assertIs(DataTestCase.assertEqual, unittest.TestCase.assertEqual)
        else:
            with self.assertRaises(Exception) as cm:
                first  = set([1,2,3,4,5,6,7])
                second = set([1,2,3,4,5,6])
                self.assertEqual(first, second)

            self.assertIs(type(cm.exception), AssertionError)


class TestAllowanceWrappers(unittest.TestCase):
    """Test method wrappers for allowance context managers."""
    def setUp(self):
        class DummyCase(DataTestCase):
            def runTest(self):
                pass
        self.case = DummyCase()

    def test_allowedSpecific(self):
        cm = self.case.allowedSpecific([Missing('foo')])
        self.assertTrue(isinstance(cm, allowed_specific))

    def test_allowedMissing(self):
        cm = self.case.allowedMissing()
        self.assertTrue(isinstance(cm, allowed_missing))

    def test_allowedExtra(self):
        cm = self.case.allowedExtra()
        self.assertTrue(isinstance(cm, allowed_extra))

    def test_allowedInvalid(self):
        cm = self.case.allowedInvalid()
        self.assertTrue(isinstance(cm, allowed_invalid))

    def test_allowedDeviation(self):
        cm = self.case.allowedDeviation(5)
        self.assertTrue(isinstance(cm, allowed_deviation))

    def test_allowedPercentDeviation(self):
        result = self.case.allowedPercentDeviation(5)
        self.assertTrue(isinstance(result, allowed_percent_deviation))

    def test_allowedLimit(self):
        cm = self.case.allowedLimit(10)
        self.assertTrue(isinstance(cm, allowed_limit))
