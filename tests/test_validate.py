"""Tests for validation and comparison functions."""
import re
import textwrap
from . import _unittest as unittest
from datatest.utils.misc import _is_consumable

from datatest.errors import Extra
from datatest.errors import Missing
from datatest.errors import Invalid
from datatest.errors import Deviation
from datatest.errors import NOTFOUND

from datatest.validate import _compare_sequence
from datatest.validate import _compare_set
from datatest.validate import _compare_callable
from datatest.validate import _compare_regex
from datatest.validate import _compare_other
from datatest.validate import _do_comparison
from datatest.validate import _compare_mapping
from datatest.validate import _do_mapping_comparison


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

    def test_notfound(self):
        with self.assertRaises(ValueError):
            _compare_sequence(NOTFOUND, [1, 2, 3])


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

        result = list(result)
        self.assertEqual(len(result), 2)
        self.assertIn(Missing('b'), result)
        self.assertIn(Extra('x'), result)

    def test_string_or_noniterable(self):
        data = 'a'
        result = _compare_set(data, self.requirement)

        result = list(result)
        self.assertEqual(len(result), 2)
        self.assertIn(Missing('b'), result)
        self.assertIn(Missing('c'), result)

    def test_notfound(self):
        result = _compare_set(NOTFOUND, set(['a']))
        self.assertEqual(list(result), [Missing('a')])


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

    def test_notfound(self):
        def func(x):
            return False
        result = _compare_callable(NOTFOUND, func)
        self.assertEqual(list(result), [Invalid(None)])


class TestCompareRegex(unittest.TestCase):
    def setUp(self):
        self.regex = re.compile('[a-z][0-9]+')

    def test_all_true(self):
        data = iter(['a1', 'b2', 'c3'])
        result = _compare_regex(data, self.regex)
        self.assertEqual(list(result), [])

    def test_some_false(self):
        data = iter(['a1', 'b2', 'XX'])
        result = _compare_regex(data, self.regex)
        self.assertEqual(list(result), [Invalid('XX')])

    def test_duplicate_false(self):
        """Should return an error for every non-match (incl. duplicates)."""
        data = iter(['a1', 'b2', 'XX', 'XX', 'XX'])  # <- Multiple XX's.
        result = _compare_regex(data, self.regex)
        self.assertEqual(list(result), [Invalid('XX'), Invalid('XX'), Invalid('XX')])

    def test_raised_error(self):
        """When an Exception is raised, it counts as False."""
        data = ['a1', 'b2', 30]  # <- Fails on 30 (re.search() expects a string).
        result = _compare_regex(data, self.regex)
        self.assertEqual(list(result), [Invalid(30)])

    def test_notfound(self):
        result = _compare_regex(NOTFOUND, self.regex)
        self.assertEqual(list(result), [Invalid(None)])


class TestCompareOther(unittest.TestCase):
    def test_all_true(self):
        data = iter(['A', 'A', 'A'])
        result = _compare_other(data, 'A')
        self.assertEqual(list(result), [])

    def test_some_invalid(self):
        data = iter(['A', 'A', 'XX'])
        result = _compare_other(data, 'A')
        self.assertEqual(list(result), [Invalid('XX', expected='A')])

    def test_some_deviation(self):
        data = iter([10, 10, 11])
        result = _compare_other(data, 10)
        self.assertEqual(list(result), [Deviation(+1, 10)])

    def test_invalid_and_deviation(self):
        data = iter([10, 'XX', 11])
        result = _compare_other(data, 10)

        result = list(result)
        self.assertEqual(len(result), 2)
        self.assertIn(Invalid('XX', expected=10), result)
        self.assertIn(Deviation(+1, 10), result)

    def test_dict_comparison(self):
        data = iter([{'a': 1}, {'b': 2}])
        result = _compare_other(data, {'a': 1})
        self.assertEqual(list(result), [Invalid({'b': 2}, expected={'a': 1})])

    def test_broken_comparison(self):
        class BadClass(object):
            def __eq__(self, other):
                raise Exception("I have betrayed you!")

            def __hash__(self):
                return hash((self.__class__, 101))

        bad_instance = BadClass()

        data = iter([10, bad_instance, 10])
        result = _compare_other(data, 10)
        self.assertEqual(list(result), [Invalid(bad_instance, 10)])


class TestDoComparison(unittest.TestCase):
    """Calling _do_comparison() should run the appropriate comparison
    function (internally) and return the result.
    """
    def setUp(self):
        self.multiple = ['A', 'B', 'A']
        self.single = 'B'

    def test_sequence(self):
        result = _do_comparison(self.multiple, ['A', 'B', 'A'])
        self.assertIsNone(result)

        result = _do_comparison(self.multiple, ['A', 'A', 'B'])
        self.assertIsInstance(result, AssertionError)

        with self.assertRaises(ValueError):
            _do_comparison(self.single, ['A', 'A', 'B'])

    def test_set(self):
        result = _do_comparison(self.multiple, set(['A', 'B']))
        self.assertIsNone(result)

        result = _do_comparison(self.multiple, set(['A', 'B', 'C']))
        self.assertTrue(_is_consumable(result))
        self.assertEqual(list(result), [Missing('C')])

        result = _do_comparison(self.single, set(['A', 'B']))
        self.assertEqual(list(result), [Missing('A')])  # <- Iterable of errors.

    def test_callable(self):
        result = _do_comparison(self.multiple, lambda x: x in ('A', 'B'))
        self.assertIsNone(result)

        result = _do_comparison(self.multiple, lambda x: x == 'A')
        self.assertTrue(_is_consumable(result))
        self.assertEqual(list(result), [Invalid('B')])

        #func = lambda x: x == 'A'
        result = _do_comparison(self.single, lambda x: x == 'A')
        self.assertEqual(result, Invalid('B'))  # <- Error.
        #self.assertEqual(result, Invalid('B', expected=func)  # <- Error.

    def test_regex(self):
        result = _do_comparison(self.multiple, re.compile('[AB]'))
        self.assertIsNone(result)

        result = _do_comparison(self.multiple, re.compile('[A]'))
        self.assertTrue(_is_consumable(result))
        self.assertEqual(list(result), [Invalid('B')])

        result = _do_comparison(self.single, re.compile('[A]'))
        self.assertEqual(result, Invalid('B'))  # <- Error.
        #self.assertEqual(result, Invalid('B', expected=re.compile('[A]')))  # <- Error.

    def test_other_string(self):
        data = ['A', 'A', 'A']
        result = _do_comparison(data, 'A')
        self.assertIsNone(result)

        result = _do_comparison(self.multiple, 'A')
        self.assertTrue(_is_consumable(result))
        self.assertEqual(list(result), [Invalid('B')])

        result = _do_comparison(self.single, 'A')
        self.assertEqual(result, Invalid('B', expected='A'))  # <- Error.

    def test_other_mapping(self):
        data = [{'a': 1}, {'b': 2}]
        result = _do_comparison(data, [{'a': 1}, {'b': 2}])
        self.assertIsNone(result)

        data = [{'b': 2}]
        result = _do_comparison(data, {'a': 1})
        self.assertTrue(_is_consumable(result))
        self.assertEqual(list(result), [Invalid({'b': 2})])

        data = {'b': 2}
        result = _do_comparison(data, {'a': 1})
        self.assertEqual(result, Invalid({'b': 2}, expected={'a': 1}))  # <- Error.


class TestCompareMapping(unittest.TestCase):
    """Calling _compare_mapping() should run the appropriate
    comparison function (internally) for each value-group and
    return the results as an iterable of key-value items.
    """
    def test_no_differences(self):
        # Sequence order.
        data = {'a': ['x', 'y']}
        result = _compare_mapping(data, {'a': ['x', 'y']})
        self.assertEqual(dict(result), {})

        # Set membership.
        data = {'a': ['x', 'y']}
        result = _compare_mapping(data, {'a': set(['x', 'y'])})
        self.assertEqual(dict(result), {})

        # Equality of single values.
        data = {'a': 'x', 'b': 'y'}
        result = _compare_mapping(data, {'a': 'x', 'b': 'y'})
        self.assertEqual(dict(result), {})

    def test_some_differences(self):
        # Sequence order.
        data = {'a': ['x', 'y']}
        result = _compare_mapping(data, {'a': ['x', 'z']})
        result = dict(result)
        self.assertTrue(len(result) == 1)
        self.assertIsInstance(result['a'], AssertionError)

        # Set membership.
        data = {'a': ['x', 'x'], 'b': ['x', 'y', 'z']}
        result = _compare_mapping(data, {'a': set(['x', 'y']),
                                         'b': set(['x', 'y'])})
        expected = {'a': [Missing('y')], 'b': [Extra('z')]}
        self.assertEqual(dict(result), expected)

        # Equality of single values.
        data = {'a': 'x', 'b': 10}
        result = _compare_mapping(data, {'a': 'j', 'b': 9})
        expected = {'a': Invalid('x', expected='j'), 'b': Deviation(+1, 9)}
        self.assertEqual(dict(result), expected)

        # Equality of multiple values.
        data = {'a': ['x', 'j'], 'b': [10, 9]}
        result = _compare_mapping(data, {'a': 'j', 'b': 9})
        expected = {'a': [Invalid('x')], 'b': [Deviation(+1, 9)]}
        self.assertEqual(dict(result), expected)

        # Equality of multiple values, missing key with single item.
        data = {'a': ['x', 'j'], 'b': [10, 9]}
        result = _compare_mapping(data, {'a': 'j', 'b': 9, 'c': 'z'})
        expected = {'a': [Invalid('x')], 'b': [Deviation(+1, 9)], 'c': Missing('z')}
        self.assertEqual(dict(result), expected)

        # Missing key, set membership.
        data = {'a': 'x'}
        result = _compare_mapping(data, {'a': 'x', 'b': set(['z'])})
        expected = {'b': [Missing('z')]}
        self.assertEqual(dict(result), expected)

    def test_comparison_error(self):
        # Sequence failure.
        nonsequence = {'a': 'x'}  # The value "x" is not a sequence
                                  # so comparing  it against the list
                                  # ['x', 'y'] should raise an error.
        with self.assertRaises(ValueError):
            result = _compare_mapping(nonsequence, {'a': ['x', 'y']})
            dict(result)  # Evaluate iterator.


class TestDoMappingComparison(unittest.TestCase):
    def test_no_differences(self):
        data = {'a': 'x', 'b': 'y'}
        result = _do_mapping_comparison(data, {'a': 'x', 'b': 'y'})
        self.assertIsNone(result)

    def test_some_differences(self):
        data = {'a': 'x', 'b': 'y'}
        result = _do_mapping_comparison(data, {'a': 'x', 'b': 'z'})
        self.assertTrue(_is_consumable(result))
        self.assertEqual(dict(result), {'b': Invalid('y', expected='z')})
