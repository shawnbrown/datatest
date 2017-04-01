"""Tests for validation and comparison functions."""
import textwrap
from . import _unittest as unittest

from datatest.errors import Extra
from datatest.errors import Missing
from datatest.errors import Invalid
from datatest.errors import Deviation

from datatest.validate import _compare_sequence
from datatest.validate import _compare_set
from datatest.validate import _compare_callable


class TestCompareSequence(unittest.TestCase):
    def test_return_object(self):
        first = ['aaa', 'bbb', 'ccc']
        second = ['aaa', 'bbb', 'ccc']
        error = _compare_sequence(first, second)
        self.assertIsNone(error)  # No difference, returns None.

        first = ['aaa', 'XXX', 'ccc']
        second = ['aaa', 'bbb', 'ccc']
        error = _compare_sequence(first, second)
        self.assertIsInstance(error, AssertionError)

    def test_differs(self):
        first = ['aaa', 'XXX', 'ccc']
        second = ['aaa', 'bbb', 'ccc']
        error = _compare_sequence(first, second)

        message = """
            Data sequence differs starting at index 1:

              'aaa', 'XXX', 'ccc'
                     ^^^^^
            Found 'XXX', expected 'bbb'
        """
        message = textwrap.dedent(message).strip()
        self.assertEqual(str(error), message)

    def test_missing(self):
        first = ['aaa', 'bbb']
        second = ['aaa', 'bbb', 'ccc']
        error = _compare_sequence(first, second)

        message = """
            Data sequence is missing elements starting with index 2:

              ..., 'bbb', ?????
                          ^^^^^
            Expected 'ccc'
        """
        message = textwrap.dedent(message).strip()
        self.assertEqual(str(error), message)

    def test_extra(self):
        first = ['aaa', 'bbb', 'ccc', 'ddd']
        second = ['aaa', 'bbb', 'ccc']
        error = _compare_sequence(first, second)

        message = """
            Data sequence contains extra elements starting with index 3:

              ..., 'ccc', 'ddd'
                          ^^^^^
            Found 'ddd'
        """
        message = textwrap.dedent(message).strip()
        self.assertEqual(str(error), message)


class TestCompareSet(unittest.TestCase):
    def setUp(self):
        self.requirement = set(['a', 'b', 'c'])

    def test_no_difference(self):
        data = iter(['a', 'b', 'c'])
        result = _compare_set(data, self.requirement)
        self.assertEqual(list(result), [])

    def test_missing(self):
        data = iter(['a', 'b'])
        result = _compare_set(data, self.requirement)
        self.assertEqual(list(result), [Missing('c')])

    def test_extra(self):
        data = iter(['a', 'b', 'c', 'x'])
        result = _compare_set(data, self.requirement)
        self.assertEqual(list(result), [Extra('x')])

    def test_duplicate_extras(self):
        """Should return only one error for each distinct extra value."""
        data = iter(['a', 'b', 'c', 'x', 'x', 'x'])  # <- Multiple x's.
        result = _compare_set(data, self.requirement)
        self.assertEqual(list(result), [Extra('x')])

    def test_missing_and_extra(self):
        data = iter(['a', 'c', 'x'])
        result = _compare_set(data, self.requirement)
        self.assertEqual(set(result), set([Missing('b'), Extra('x')]))

    def test_string_or_noniterable(self):
        data = 'a'
        result = _compare_set(data, self.requirement)
        self.assertEqual(set(result), set([Missing('b'), Missing('c')]))


class TestCompareCallable(unittest.TestCase):
    def setUp(self):
        self.isdigit = lambda x: x.isdigit()

    def test_all_true(self):
        data = ['10', '20', '30']
        result = _compare_callable(data, self.isdigit)
        self.assertEqual(list(result), [])

    def test_some_false(self):
        """Elements that evaluate to False are returned as Invalid() errors."""
        data = ['10', '20', 'XX']
        result = _compare_callable(data, self.isdigit)
        self.assertEqual(list(result), [Invalid('XX')])

    def test_duplicate_false(self):
        """Should return an error for every false result (incl. duplicates)."""
        data = ['10', '20', 'XX', 'XX', 'XX']  # <- Multiple XX's.
        result = _compare_callable(data, self.isdigit)
        self.assertEqual(list(result), [Invalid('XX'), Invalid('XX'), Invalid('XX')])

    def test_raised_error(self):
        """When an Exception is raised, it counts as False."""
        data = ['10', '20', 30]  # <- Fails on 30 (int has no 'isdigit' method).
        result = _compare_callable(data, self.isdigit)
        self.assertEqual(list(result), [Invalid(30)])

    def test_returned_error(self):
        """When a DataError is returned, it is used in place of Invalid."""
        def func(x):
            if x == 'c':
                return Invalid("Letter 'c' is no good!")
            return True

        data = ['a', 'b', 'c']
        result = _compare_callable(data, func)
        self.assertEqual(list(result), [Invalid("Letter 'c' is no good!")])

    def test_bad_return_type(self):
        """If callable returns an unexpected type, raise a TypeError."""
        def func(x):
            return Exception('my error')  # <- Not True, False or DataError!

        with self.assertRaises(TypeError):
            result = _compare_callable(['a', 'b', 'c'], func)
            list(result)  # Evaluate generator.
