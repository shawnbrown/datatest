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

from datatest._query.query import Select
from datatest._query.query import Query
from datatest._query.query import Result

from datatest.validation import validate
from datatest.validation import ValidationError
from datatest.difference import Extra
from datatest.difference import Missing
from datatest.difference import Invalid
from datatest.difference import Deviation
from datatest.acceptances import (
    AcceptedMissing,
    AcceptedExtra,
    AcceptedInvalid,
    AcceptedFuzzy,
    AcceptedDeviation,
    AcceptedPercent,
    AcceptedLimit,
    AcceptedSpecific,
)


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
        """When *required* is a sequence, should compare predicates by
        position.
        """
        with self.assertRaises(ValidationError) as cm:
            data = ['a', 2, 'x', 3]
            required = ['a', 2, 'c', 4]
            self.assertValid(data, required)

        error = cm.exception
        expected = [
            Invalid('x', expected='c'),
            Deviation(-1, 4),
        ]
        self.assertEqual(error.differences, expected)
        self.assertEqual(error.args[1], 'does not match required sequence')

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
        source = Select([('A', 'B'), ('1', '2'), ('1', '2')])
        query_obj1 = source(['B'])
        query_obj2 = source(['B'])
        self.assertValid(query_obj1, query_obj2)

    def test_result_objects(self):
        result_obj1 = Result(['2', '2'], evaluation_type=list)
        result_obj2 = Result(['2', '2'], evaluation_type=list)
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


class TestValidationWrappers(unittest.TestCase):
    def setUp(self):
        class DummyCase(DataTestCase):
            def runTest(self_):
                pass

            def _apply_validation(self_, function, *args, **kwds):
                """Knocks-out existing method to log applied function."""
                self_._applied_function = function

        self.case = DummyCase()

    def test_methods_names(self):
        """For each validate() method, DataTestCase should have a
        matching unittest-style method.

        ==========  ===================
        validate()  DataTestCase
        ==========  ===================
        approx()    assertValidApprox()
        subset()    assertValidSubset()
        ...         ...
        ==========  ===================
        """
        methods = [x for x in dir(validate) if not x.startswith('_')]

        missing_methods = []
        for method in methods:
            name = 'assertValid{0}'.format(method.title())
            msg = 'DataTestCase does not have method named {0!r}'.format(name)
            if not hasattr(self.case, name):
                foo = '  {0}() -> {1}()'.format(method, name)
                missing_methods.append(foo)

        msg = ('validate() and DataTestCase should have matching '
               'validation methods:\n{0}').format('\n'.join(missing_methods))
        self.assertTrue(len(missing_methods) == 0, msg=msg)

    def test_methods_wrappers(self):
        """DataTestCase method wrappers should call appropriate
        validate methods.
        """
        method_calls = [
            ('predicate', ('aaa', 'aaa'), {}),
            ('approx', ([1.5, 1.5], 1.5), {}),
            ('fuzzy', ('aaa', 'aaa'), {}),
            ('interval', ([1, 2, 3], 1, 3), {}),
            ('set', ([1, 1, 2, 2], set([1, 2])), {}),
            ('subset', ([1, 2, 3], set([1, 2])), {}),
            ('superset', ([1, 2], set([1, 2, 3])), {}),
            ('unique', ([1, 2, 3],), {}),
            ('order', (['x', 'y'], ['x', 'y']), {}),
        ]
        method_names = set(x[0] for x in method_calls)
        all_names = set(x for x in dir(validate) if not x.startswith('_'))
        self.assertSetEqual(method_names, all_names)

        for orig_name, args, kwds in method_calls:
            case_name = 'assertValid{0}'.format(orig_name.title())
            case_method = getattr(self.case, case_name)
            case_method(*args, **kwds)
            orig_method = getattr(validate, orig_name)

            applied_name = self.case._applied_function.__name__
            msg = (
                '\n\n  '
                'DataTestCase.{0}() should map to validate.{1}() '
                'but instead maps to validate.{2}()'
            ).format(case_name, orig_name, applied_name)
            self.assertEqual(self.case._applied_function, orig_method, msg=msg)


class TestAcceptanceWrappers(unittest.TestCase):
    """Test method wrappers for acceptance context managers."""
    def setUp(self):
        class DummyCase(DataTestCase):
            def runTest(self):
                pass
        self.case = DummyCase()

    def test_acceptedSpecific(self):
        cm = self.case.acceptedSpecific([Missing('foo')])
        self.assertTrue(isinstance(cm, AcceptedSpecific))

    def test_acceptedMissing(self):
        cm = self.case.acceptedMissing()
        self.assertTrue(isinstance(cm, AcceptedMissing))

    def test_acceptedExtra(self):
        cm = self.case.acceptedExtra()
        self.assertTrue(isinstance(cm, AcceptedExtra))

    def test_acceptedInvalid(self):
        cm = self.case.acceptedInvalid()
        self.assertTrue(isinstance(cm, AcceptedInvalid))

    def test_acceptedFuzzy(self):
        cm = self.case.acceptedFuzzy()
        self.assertTrue(isinstance(cm, AcceptedFuzzy))

    def test_acceptedDeviation(self):
        cm = self.case.acceptedDeviation(5)
        self.assertTrue(isinstance(cm, AcceptedDeviation))

    def test_acceptedPercent(self):
        result = self.case.acceptedPercent(5)
        self.assertTrue(isinstance(result, AcceptedPercent))

    def test_acceptedLimit(self):
        cm = self.case.acceptedLimit(10)
        self.assertTrue(isinstance(cm, AcceptedLimit))
