"""Tests for validation and comparison functions."""
import re
import textwrap
from . import _unittest as unittest
from datatest._utils import exhaustible

from datatest.difference import BaseDifference
from datatest.difference import Extra
from datatest.difference import Missing
from datatest.difference import Invalid
from datatest.difference import Deviation
from datatest.difference import NOTFOUND

from datatest._required import Required
from datatest._required import RequiredPredicate
from datatest._required import RequiredSequence
from datatest._required import RequiredSet
from datatest.validation import _get_group_requirement
from datatest.validation import _get_required
from datatest.validation import _apply_required_to_data
from datatest.validation import _apply_required_to_mapping
from datatest.validation import _apply_mapping_to_mapping
from datatest.validation import validate2
from datatest.validation import _require_sequence
from datatest.validation import _require_set
from datatest.validation import _require_predicate
from datatest.validation import _require_predicate_from_iterable
from datatest.validation import _get_msg_and_func
from datatest.validation import _apply_mapping_requirement
from datatest.validation import _normalize_data
from datatest.validation import _normalize_requirement
from datatest.validation import _get_invalid_info
from datatest.validation import ValidationError
from datatest.validation import valid
from datatest.validation import validate
from datatest.validation import _check_single_value

from datatest._query.query import DictItems
from datatest._query.query import Result

try:
    import pandas
except ImportError:
    pandas = None

try:
    import numpy
except ImportError:
    numpy = None


class TestRequireSequence(unittest.TestCase):
    def test_no_difference(self):
        first = ['aaa', 'bbb', 'ccc']
        second = ['aaa', 'bbb', 'ccc']
        error = _require_sequence(first, second)
        self.assertIsNone(error)  # No difference, returns None.

    def test_extra(self):
        data = ['aaa', 'bbb', 'ccc', 'ddd', 'eee', 'fff']
        requirement = ['aaa', 'ccc', 'fff']
        error = _require_sequence(data, requirement)
        self.assertEqual(error, {(1, 2): [Extra('bbb')], (3, 5): [Extra('ddd'), Extra('eee')]})

    def test_extra_with_empty_requirement(self):
        data = ['aaa', 'bbb']
        requirement = []
        error = _require_sequence(data, requirement)
        self.assertEqual(error, {(0, 2): [Extra('aaa'), Extra('bbb')]})

    def test_missing(self):
        data = ['bbb', 'eee']
        requirement = ['aaa', 'bbb', 'ccc', 'ddd', 'eee']
        error = _require_sequence(data, requirement)
        expected = {
            (0, 0): [Missing('aaa')],
            (1, 1): [Missing('ccc'), Missing('ddd')],
        }
        self.assertEqual(error, expected)

    def test_missing_with_empty_data(self):
        data = []
        requirement = ['aaa', 'bbb']
        error = _require_sequence(data, requirement)
        self.assertEqual(error, {(0, 0): [Missing('aaa'), Missing('bbb')]})

    def test_invalid(self):
        data = ['aaa', 'xxx', 'ccc']
        requirement = ['aaa', 'bbb', 'ccc']
        actual = _require_sequence(data, requirement)
        expected = {
            (1, 2): [Invalid('xxx', 'bbb')],
        }
        self.assertEqual(actual, expected)

    def test_invalid_different_lengths(self):
        data = ['aaa', 'xxx', 'ddd']
        requirement = ['aaa', 'bbb', 'ccc', 'ddd']
        actual = _require_sequence(data, requirement)
        expected = {
            (1, 2): [Invalid('xxx', 'bbb'), Missing('ccc')],
        }
        self.assertEqual(actual, expected)

        data = ['aaa', 'xxx', 'yyy', 'ccc']
        requirement = ['aaa', 'bbb', 'ccc']
        actual = _require_sequence(data, requirement)
        expected = {
            (1, 3): [Invalid('xxx', 'bbb'), Extra('yyy')],
        }
        self.assertEqual(actual, expected)

    def test_mixed_differences(self):
        data = ['aaa', 'xxx', 'ddd', 'eee', 'ggg']
        requirement = ['aaa', 'bbb', 'ccc', 'ddd', 'fff']
        actual = _require_sequence(data, requirement)
        expected = {
            (1, 2): [Invalid('xxx', expected='bbb'), Missing('ccc')],
            (3, 5): [Invalid('eee', expected='fff'), Extra('ggg')],
        }
        self.assertEqual(actual, expected)

    def test_numeric_matching(self):
        """When checking sequence order, numeric differences should not
        be converted into Deviation objects.
        """
        data = [1, 100, 4, 200, 300]
        requirement = [1, 2, 3, 4, 5]
        actual = _require_sequence(data, requirement)
        expected = {
            (1, 2): [Invalid(100, expected=2), Missing(3)],
            (3, 5): [Invalid(200, expected=5), Extra(300)],
        }
        self.assertEqual(actual, expected)

    def test_unhashable(self):
        """Uses "deep hashing" to attempt to sort unhashable types."""
        first = [{'a': 1}, {'b': 2}, {'c': 3}]
        second = [{'a': 1}, {'b': 2}, {'c': 3}]
        error = _require_sequence(first, second)
        self.assertIsNone(error)  # No difference, returns None.

        data = [{'a': 1}, {'x': 0}, {'d': 4}, {'y': 5}, {'g': 7}]
        requirement = [{'a': 1}, {'b': 2}, {'c': 3}, {'d': 4}, {'f': 6}]
        actual = _require_sequence(data, requirement)
        expected = {
            (1, 2): [Invalid({'x': 0}, expected={'b': 2}), Missing({'c': 3})],
            (3, 5): [Invalid({'y': 5}, expected={'f': 6}), Extra({'g': 7})],
        }
        self.assertEqual(actual, expected)


class TestRequireSet(unittest.TestCase):
    def setUp(self):
        self.requirement = set(['a', 'b', 'c'])

    def test_no_difference(self):
        data = iter(['a', 'b', 'c'])
        result = _require_set(data, self.requirement)
        self.assertIsNone(result)  # No difference, returns None.

    def test_missing(self):
        data = iter(['a', 'b'])
        result = _require_set(data, self.requirement)
        self.assertEqual(list(result), [Missing('c')])

    def test_extra(self):
        data = iter(['a', 'b', 'c', 'x'])
        result = _require_set(data, self.requirement)
        self.assertEqual(list(result), [Extra('x')])

    def test_duplicate_extras(self):
        """Should return only one error for each distinct extra value."""
        data = iter(['a', 'b', 'c', 'x', 'x', 'x'])  # <- Multiple x's.
        result = _require_set(data, self.requirement)
        self.assertEqual(list(result), [Extra('x')])

    def test_missing_and_extra(self):
        data = iter(['a', 'c', 'x'])
        result = _require_set(data, self.requirement)

        result = list(result)
        self.assertEqual(len(result), 2)
        self.assertIn(Missing('b'), result)
        self.assertIn(Extra('x'), result)

    def test_string_or_noniterable(self):
        data = 'a'
        result = _require_set(data, self.requirement)

        result = list(result)
        self.assertEqual(len(result), 2)
        self.assertIn(Missing('b'), result)
        self.assertIn(Missing('c'), result)

    def test_notfound(self):
        result = _require_set(NOTFOUND, set(['a']))
        self.assertEqual(list(result), [Missing('a')])

    def test_atomic_object_handling(self):
        # Non-containers are, of course, treated as atomic objects.
        requirement = set([777])
        self.assertIsNone(
            _require_set([777], requirement),
            msg='list containing one int',
        )
        self.assertIsNone(
            _require_set(777, requirement),
            msg='int, no container',
        )

        # Strings should treated as an atomic objects.
        requirement = set(['abc'])
        self.assertIsNone(
            _require_set(['abc'], requirement),
            msg='list containing one str',
        )
        self.assertIsNone(
            _require_set('abc', requirement),
            msg='single strings should be treated as atomic objects',
        )

        # Tuples should also be treated as an atomic objects.
        requirement = set([('a', 'b', 'c')])
        self.assertIsNone(
            _require_set([('a', 'b', 'c')], requirement),
            msg='list containing one tuple',
        )
        self.assertIsNone(
            _require_set(('a', 'b', 'c'), requirement),
            msg='single tuples should be treated as atomic objects',
        )


class TestRequireCallable(unittest.TestCase):
    def setUp(self):
        self.isdigit = lambda x: x.isdigit()

    def test_all_true(self):
        data = ['10', '20', '30']
        result = _require_predicate_from_iterable(data, self.isdigit)
        self.assertIsNone(result)

    def test_some_false(self):
        """Elements that evaluate to False are returned as Invalid() errors."""
        data = ['10', '20', 'XX']
        result = _require_predicate_from_iterable(data, self.isdigit)
        self.assertEqual(list(result), [Invalid('XX')])

    def test_duplicate_false(self):
        """Should return an error for every false result (incl. duplicates)."""
        data = ['10', '20', 'XX', 'XX', 'XX']  # <- Multiple XX's.
        result = _require_predicate_from_iterable(data, self.isdigit)
        self.assertEqual(list(result), [Invalid('XX'), Invalid('XX'), Invalid('XX')])

    def test_returned_error(self):
        """When a difference is returned, it is used in place of Invalid."""
        def func(x):
            if x == 'c':
                return Invalid("Letter 'c' is no good!")
            return True

        data = ['a', 'b', 'c']
        result = _require_predicate_from_iterable(data, func)
        self.assertEqual(list(result), [Invalid("Letter 'c' is no good!")])

    def test_notfound(self):
        def func(x):
            return False
        result = _require_predicate_from_iterable(NOTFOUND, func)
        self.assertEqual(result, Invalid(None))


class TestRequireRegex(unittest.TestCase):
    def setUp(self):
        self.regex = re.compile('[a-z][0-9]+')

    def test_all_true(self):
        data = iter(['a1', 'b2', 'c3'])
        result = _require_predicate_from_iterable(data, self.regex)
        self.assertIsNone(result)

    def test_some_false(self):
        data = iter(['a1', 'b2', 'XX'])
        result = _require_predicate_from_iterable(data, self.regex)
        self.assertEqual(list(result), [Invalid('XX')])

    def test_duplicate_false(self):
        """Should return an error for every non-match (incl. duplicates)."""
        data = iter(['a1', 'b2', 'XX', 'XX', 'XX'])  # <- Multiple XX's.
        result = _require_predicate_from_iterable(data, self.regex)
        self.assertEqual(list(result), [Invalid('XX'), Invalid('XX'), Invalid('XX')])

    def test_notfound(self):
        result = _require_predicate_from_iterable(NOTFOUND, self.regex)
        self.assertEqual(result, Invalid(None))


class TestRequirePredicate(unittest.TestCase):
    def test_eq(self):
        """Should use __eq__() comparison, not __ne__()."""

        class EqualsAll(object):
            def __init__(_self):
                _self.times_checked = 0

            def __eq__(_self, other):
                _self.times_checked += 1
                return True

            def __ne__(_self, other):
                return NotImplemented

        requirement = EqualsAll()
        result = _require_predicate('A', requirement)
        self.assertEqual(requirement.times_checked, 1)

    def test_all_true(self):
        result = _require_predicate('A', 'A', True)
        self.assertIsNone(result)

    def test_some_invalid(self):
        result = _require_predicate('XX', 'A', True)
        self.assertEqual(result, Invalid('XX', 'A'))

    def test_deviation(self):
        result = _require_predicate(11, 10, True)
        self.assertEqual(result, Deviation(+1, 10))

    def test_invalid(self):
        result = _require_predicate('XX', 10, True)
        self.assertEqual(result, Invalid('XX', 10))

    def test_dict_comparison(self):
        result = _require_predicate({'a': 1}, {'a': 2}, True)
        self.assertEqual(result, Invalid({'a': 1}, {'a': 2}))

    def test_custom_difference(self):
        """When a predicate function returns a difference object,
        it should be used in place of an auto-generated one.
        """
        pred = lambda x: Invalid('custom')
        result = _require_predicate('A', pred, False)
        self.assertEqual(result, Invalid('custom'))

    def test_broken_comparison(self):
        class BadClass(object):
            def __eq__(self, other):
                raise Exception('I have betrayed you!')

            def __hash__(self):
                return hash((self.__class__, 101))

        bad_instance = BadClass()
        msg = 'errors should bubble-up for debugging'
        with self.assertRaises(Exception, msg=msg):
            _require_predicate(bad_instance, 10)


class TestRequirePredicateFromIterable(unittest.TestCase):
    def test_all_true(self):
        data = ['x', 'x', 'x']
        result = _require_predicate_from_iterable(data, 'x')
        self.assertIsNone(result)

    def test_some_false(self):
        data = ['x', 'x', 'y']
        result = _require_predicate_from_iterable(data, 'x')
        self.assertEqual(list(result), [Invalid('y')])

        data = [2, 2, 7]
        result = _require_predicate_from_iterable(data, 2)
        self.assertEqual(list(result), [Deviation(+5, 2)])

    def test_duplicate_false(self):
        """Should return an error for every false result (incl. duplicates)."""
        data = ['x', 'x', 'y', 'y']  # <- Multiple invalid y's.
        result = _require_predicate_from_iterable(data, 'x')
        self.assertEqual(list(result), [Invalid('y'), Invalid('y')])

    def test_raised_error(self):
        """Exceptions should raise as normal (earlier implementation
        coerced errors to False).
        """
        capital_letters = lambda x: x.isupper()
        data = ['X', 'X', 10]  # <- Fails on 30 (int has no 'isupper' method).
        with self.assertRaises(AttributeError):
            result = _require_predicate_from_iterable(data, capital_letters)

    def test_returned_error(self):
        """When a difference is returned, it should be used in place of
        an auto-generated one.
        """
        def func(x):
            if x == 5:
                return Invalid("Five is right out!")
            return True

        data = [1, 2, 5]
        result = _require_predicate_from_iterable(data, func)
        self.assertEqual(list(result), [Invalid("Five is right out!")])

    def test_notfound(self):
        def func(x):
            return False
        result = _require_predicate_from_iterable(NOTFOUND, func)
        self.assertEqual(result, Invalid(None))


class TestRequirePredicateTuple(unittest.TestCase):
    def test_all_true(self):
        data = [('x', 'y'), ('x', 'y')]
        result = _require_predicate_from_iterable(data, ('x', 'y'))
        self.assertIsNone(result)

    def test_some_false(self):
        data = [('x', 'y'), ('x', 'x')]
        result = _require_predicate_from_iterable(data, ('x', 'y'))
        self.assertEqual(list(result), [Invalid(('x', 'x'))])

    def test_wildcard(self):
        data = [('x', 'y'), ('x', 'x')]
        result = _require_predicate_from_iterable(data, (Ellipsis, 'y'))
        self.assertEqual(list(result), [Invalid(('x', 'x'))])


class TestGetMsgAndFunc(unittest.TestCase):
    def setUp(self):
        self.multiple = ['A', 'B', 'A']
        self.single = 'B'

    def test_sequence(self):
        default_msg, require_func = _get_msg_and_func(['A', 'B'], ['A', 'B'])
        self.assertIsInstance(default_msg, str)
        self.assertEqual(require_func, _require_sequence)

    def test_tuple(self):
        default_msg, require_func = _get_msg_and_func([('A', 'B')], ('A', 'B'))
        self.assertIsInstance(default_msg, str)
        self.assertEqual(require_func, _require_predicate_from_iterable)

    def test_set(self):
        default_msg, require_func = _get_msg_and_func(['A', 'B'], set(['A', 'B']))
        self.assertIsInstance(default_msg, str)
        self.assertEqual(require_func, _require_set)

    def test_callable(self):
        def mydocstr_func(x):
            """helper docstring"""
            return True
        default_msg, require_func = _get_msg_and_func(['A', 'B'], mydocstr_func)
        self.assertIn('helper docstring', default_msg, 'message should include docstring')
        self.assertEqual(require_func, _require_predicate_from_iterable)

        def myfunc(x):
            return True
        default_msg, require_func = _get_msg_and_func(['A', 'B'], myfunc)
        self.assertIn("does not satisfy 'myfunc'", default_msg, 'when no docstring, message should include name')
        self.assertEqual(require_func, _require_predicate_from_iterable)

        mylambda = lambda x: True
        default_msg, require_func = _get_msg_and_func(['A', 'B'], mylambda)
        self.assertIn('<lambda>', default_msg, 'message should include function name')
        self.assertEqual(require_func, _require_predicate_from_iterable)

        class MyClass(object):
            def __call__(_self, x):
                return True
        myinstance = MyClass()
        default_msg, require_func = _get_msg_and_func(['A', 'B'], myinstance)
        self.assertIn('MyClass', default_msg, 'message should include class name')
        self.assertEqual(require_func, _require_predicate_from_iterable)

    def test_regex(self):
        myregex = re.compile('[AB]')
        default_msg, require_func = _get_msg_and_func(['A', 'B'], myregex)
        self.assertIn(repr(myregex.pattern), default_msg, 'message should include pattern')
        self.assertEqual(require_func, _require_predicate_from_iterable)

    def test_require_predicate_from_iterable(self):
        default_msg, require_func = _get_msg_and_func(['A', 'B'], 'A')
        self.assertIsInstance(default_msg, str)
        self.assertEqual(require_func, _require_predicate_from_iterable)

        default_msg, require_func = _get_msg_and_func([{'a': 1}, {'a': 1}], {'a': 1})
        self.assertIsInstance(default_msg, str)
        self.assertEqual(require_func, _require_predicate_from_iterable)

    def test_predicate_single_value(self):
        default_msg, require_func = _get_msg_and_func('A', 'A')
        self.assertIsInstance(default_msg, str)
        self.assertEqual(require_func, _require_predicate)

        default_msg, require_func = _get_msg_and_func({'a': 1}, {'a': 1})
        self.assertIsInstance(default_msg, str)
        self.assertEqual(require_func, _require_predicate)


class TestApplyMappingRequirement(unittest.TestCase):
    """Calling _apply_mapping_requirement() should run the appropriate
    comparison function (internally) for each value-group and
    return the results as an iterable of key-value items.
    """
    def test_no_differences(self):
        # Sequence order.
        data = {'a': ['x', 'y']}
        result = _apply_mapping_requirement(data, {'a': ['x', 'y']})
        self.assertEqual(dict(result), {})

        # Set membership.
        data = {'a': ['x', 'y']}
        result = _apply_mapping_requirement(data, {'a': set(['x', 'y'])})
        self.assertEqual(dict(result), {})

        # Equality of single values.
        data = {'a': 'x', 'b': 'y'}
        result = _apply_mapping_requirement(data, {'a': 'x', 'b': 'y'})
        self.assertEqual(dict(result), {})

    def test_some_differences(self):
        # Sequence order.
        data = {'a': ['x', 'y']}
        result = _apply_mapping_requirement(data, {'a': ['x', 'z']})
        result = dict(result)
        self.assertTrue(len(result) == 1)
        self.assertEqual(result, {'a': {(1, 2): [Invalid('y', 'z')]}})

        # Set membership.
        data = {'a': ['x', 'x'], 'b': ['x', 'y', 'z']}
        result = _apply_mapping_requirement(data, {'a': set(['x', 'y']),
                                                   'b': set(['x', 'y'])})
        expected = {'a': [Missing('y')], 'b': [Extra('z')]}
        self.assertEqual(dict(result), expected)

        # Equality of single values.
        data = {'a': 'x', 'b': 10}
        result = _apply_mapping_requirement(data, {'a': 'j', 'b': 9})
        expected = {'a': Invalid('x', expected='j'), 'b': Deviation(+1, 9)}
        self.assertEqual(dict(result), expected)

        # Equality of multiple values.
        data = {'a': ['x', 'j'], 'b': [10, 9]}
        result = _apply_mapping_requirement(data, {'a': 'j', 'b': 9})
        expected = {'a': [Invalid('x')], 'b': [Deviation(+1, 9)]}
        self.assertEqual(dict(result), expected)

        # Equality of single tuples.
        data = {'a': (1, 'x'), 'b': (9, 10)}
        result = _apply_mapping_requirement(data, {'a': (1, 'j'), 'b': (9, 9)})
        expected = {'a': Invalid((1, 'x'), expected=(1, 'j')),
                    'b': Invalid((9, 10), expected=(9, 9))}
        self.assertEqual(dict(result), expected)

        # Equality of multiple tuples.
        data = {'a': [(1, 'j'), (1, 'x')], 'b': [(9, 9), (9, 10)]}
        result = _apply_mapping_requirement(data, {'a': (1, 'j'), 'b': (9, 9)})
        expected = {'a': [Invalid((1, 'x'))],
                    'b': [Invalid((9, 10))]}
        self.assertEqual(dict(result), expected)

        # Equality of multiple values, missing key with single item.
        data = {'a': ['x', 'j'], 'b': [10, 9]}
        result = _apply_mapping_requirement(data, {'a': 'j', 'b': 9, 'c': 'z'})
        expected = {'a': [Invalid('x')], 'b': [Deviation(+1, 9)], 'c': Missing('z')}
        self.assertEqual(dict(result), expected)

        # Missing key, set membership.
        data = {'a': 'x'}
        result = _apply_mapping_requirement(data, {'a': 'x', 'b': set(['z'])})
        expected = {'b': [Missing('z')]}
        self.assertEqual(dict(result), expected)

    def test_mismatched_types(self):
        nonsequence_type = {'a': 'x'}      # The value 'x' is not a sequence so
        sequence_type = {'a': ['x', 'y']}  # comparing it against the required
                                           # ['x', 'y'] should raise an error.
        with self.assertRaises(ValueError):
            result = _apply_mapping_requirement(nonsequence_type, sequence_type)
            dict(result)  # Evaluate iterator.

    def test_empty_vs_nonempty_values(self):
        empty = {}
        nonempty = {'a': set(['x'])}

        result = _apply_mapping_requirement(empty, empty)
        self.assertEqual(dict(result), {})

        result = _apply_mapping_requirement(nonempty, empty)
        self.assertEqual(dict(result), {'a': [Extra('x')]})

        result = _apply_mapping_requirement(empty, nonempty)
        self.assertEqual(dict(result), {'a': [Missing('x')]})


class TestDataRequirementNormalization(unittest.TestCase):
    def test_normalize_data(self):
        data = [1, 2, 3]
        self.assertIs(_normalize_data(data), data, 'should return original object')

        data = iter([1, 2, 3])
        self.assertIs(_normalize_data(data), data, 'should return original object')

    @unittest.skipIf(not pandas, 'pandas not found')
    def test_normalize_pandas_dataframe(self):
        df = pandas.DataFrame([(1, 'a'), (2, 'b'), (3, 'c')])
        result = _normalize_data(df)
        self.assertIsInstance(result, DictItems)
        expected = {0: (1, 'a'), 1: (2, 'b'), 2: (3, 'c')}
        self.assertEqual(dict(result), expected)

        # Single column.
        df = pandas.DataFrame([('x',), ('y',), ('z',)])
        result = _normalize_data(df)
        self.assertIsInstance(result, DictItems)
        expected = {0: 'x', 1: 'y', 2: 'z'}
        self.assertEqual(dict(result), expected, 'single column should be unwrapped')

        # Multi-index.
        df = pandas.DataFrame([('x',), ('y',), ('z',)])
        df.index = pandas.MultiIndex.from_tuples([(0, 0), (0, 1), (1, 0)])
        result = _normalize_data(df)
        self.assertIsInstance(result, DictItems)
        expected = {(0, 0): 'x', (0, 1): 'y', (1, 0): 'z'}
        self.assertEqual(dict(result), expected, 'multi-index should be tuples')

        # Indexes must contain unique values, no duplicates
        df = pandas.DataFrame([('x',), ('y',), ('z',)])
        df.index = pandas.Index([0, 0, 1])  # <- Duplicate values.
        with self.assertRaises(ValueError):
            _normalize_data(df)

    @unittest.skipIf(not pandas, 'pandas not found')
    def test_normalize_pandas_series(self):
        s = pandas.Series(['x', 'y', 'z'])
        result = _normalize_data(s)
        self.assertIsInstance(result, DictItems)
        expected = {0: 'x', 1: 'y', 2: 'z'}
        self.assertEqual(dict(result), expected)

        # Multi-index.
        s = pandas.Series(['x', 'y', 'z'])
        s.index = pandas.MultiIndex.from_tuples([(0, 0), (0, 1), (1, 0)])
        result = _normalize_data(s)
        self.assertIsInstance(result, DictItems)
        expected = {(0, 0): 'x', (0, 1): 'y', (1, 0): 'z'}
        self.assertEqual(dict(result), expected, 'multi-index should be tuples')

    @unittest.skipIf(not numpy, 'numpy not found')
    def test_normalize_numpy(self):
        # Two-dimentional array.
        arr = numpy.array([['a', 'x'], ['b', 'y']])
        lazy = _normalize_data(arr)
        self.assertIsInstance(lazy, Result)
        self.assertEqual(lazy.fetch(), [('a', 'x'), ('b', 'y')])

        # Two-valued structured array.
        arr = numpy.array([('a', 1), ('b', 2)],
                          dtype=[('one', 'U10'), ('two', 'i4')])
        lazy = _normalize_data(arr)
        self.assertIsInstance(lazy, Result)
        self.assertEqual(lazy.fetch(), [('a', 1), ('b', 2)])

        # Two-valued recarray (record array).
        arr = numpy.rec.array([('a', 1), ('b', 2)],
                              dtype=[('one', 'U10'), ('two', 'i4')])
        lazy = _normalize_data(arr)
        self.assertIsInstance(lazy, Result)
        self.assertEqual(lazy.fetch(), [('a', 1), ('b', 2)])

        # One-dimentional array.
        arr = numpy.array(['x', 'y', 'z'])
        lazy = _normalize_data(arr)
        self.assertIsInstance(lazy, Result)
        self.assertEqual(lazy.fetch(), ['x', 'y', 'z'])

        # Single-valued structured array.
        arr = numpy.array([('x',), ('y',), ('z',)],
                          dtype=[('one', 'U10')])
        lazy = _normalize_data(arr)
        self.assertIsInstance(lazy, Result)
        self.assertEqual(lazy.fetch(), ['x', 'y', 'z'])

        # Single-valued recarray (record array).
        arr = numpy.rec.array([('x',), ('y',), ('z',)],
                              dtype=[('one', 'U10')])
        lazy = _normalize_data(arr)
        self.assertIsInstance(lazy, Result)
        self.assertEqual(lazy.fetch(), ['x', 'y', 'z'])

        # Three-dimentional array--conversion is not supported.
        arr = numpy.array([[[1, 3], ['a', 'x']], [[2, 4], ['b', 'y']]])
        result = _normalize_data(arr)
        self.assertIs(result, arr, msg='unsupported, returns unchanged')

    def test_normalize_requirement(self):
        requirement = [1, 2, 3]
        self.assertIs(_normalize_requirement(requirement), requirement,
            msg='should return original object')

        with self.assertRaises(TypeError, msg='cannot use generic iter'):
            _normalize_requirement(iter([1, 2, 3]))

        result_obj = Result(iter([1, 2, 3]), evaluation_type=tuple)
        output = _normalize_requirement(result_obj)
        self.assertIsInstance(output, tuple)
        self.assertEqual(output, (1, 2, 3))

        items = DictItems(iter([(0, 'x'), (1, 'y'), (2, 'z')]))
        output = _normalize_requirement(items)
        self.assertIsInstance(output, dict)
        self.assertEqual(output, {0: 'x', 1: 'y', 2: 'z'})


class TestGetDifferenceInfo(unittest.TestCase):
    def test_mapping_requirement(self):
        """When *requirement* is a mapping, then *data* should also
        be a mapping. If *data* is not a mapping, an error should be
        raised.
        """
        mapping1 = {'a': 'x', 'b': 'y'}
        mapping2 = {'a': 'x', 'b': 'z'}

        info = _get_invalid_info(mapping1, mapping1)
        self.assertIsNone(info)

        # This next test uses _require_predicate() internally.
        msg, diffs = _get_invalid_info(mapping1, mapping2)
        self.assertTrue(exhaustible(diffs))
        self.assertEqual(dict(diffs), {'b': Invalid('y', expected='z')})  # <- SHOWS EXPECTED!

        with self.assertRaises(TypeError):
            _get_invalid_info(set(['x', 'y']), mapping2)

    def test_dictitems_data(self):
        """"When *data* is an exhaustible iterator of dict-items and
        *requirement* is a non-mapping.
        """
        items = DictItems(iter([('a', 'x'), ('b', 'y')]))
        x_or_y = lambda value: value == 'x' or value == 'y'
        result = _get_invalid_info(items, x_or_y)
        self.assertIsNone(result)

        items = DictItems(iter([('a', 'x'), ('b', 'y')]))
        msg, diffs = _get_invalid_info(items, 'x')  # <- string
        self.assertTrue(exhaustible(diffs))
        self.assertEqual(dict(diffs), {'b': Invalid('y')})

        items = DictItems(iter([('a', 'x'), ('b', 'y')]))
        msg, diffs = _get_invalid_info(items, set('x'))  # <- set
        self.assertTrue(exhaustible(diffs))
        self.assertEqual(dict(diffs), {'b': [Missing('x'), Extra('y')]})

    def test_mapping_data(self):
        """"When *data* is a mapping, it should get converted into an
        exhaustible iterator of dict-items.
        """
        mapping = {'a': 'x', 'b': 'y'}

        x_or_y = lambda value: value == 'x' or value == 'y'
        result = _get_invalid_info(mapping, x_or_y)
        self.assertIsNone(result)

        msg, diffs = _get_invalid_info(mapping, 'x')  # <- string
        self.assertTrue(exhaustible(diffs))
        self.assertEqual(dict(diffs), {'b': Invalid('y')})

        msg, diffs = _get_invalid_info(mapping, set('x'))  # <- set
        self.assertTrue(exhaustible(diffs))
        self.assertEqual(dict(diffs), {'b': [Missing('x'), Extra('y')]})

    def test_nonmapping(self):
        """When neither *data* or *requirement* are mappings."""
        result = _get_invalid_info(set(['x', 'y']), set(['x', 'y']))
        self.assertIsNone(result)

        msg, diffs = _get_invalid_info(set(['x']), set(['x', 'y']))
        self.assertTrue(exhaustible(diffs))
        self.assertEqual(list(diffs), [Missing('y')])


# FOR TESTING: A minimal subclass of BaseDifference.
# BaseDifference itself should not be instantiated
# directly.
class MinimalDifference(BaseDifference):
    @property
    def args(self):
        return BaseDifference.args.fget(self)


class TestValidationError(unittest.TestCase):
    def test_error_list(self):
        error_list = [MinimalDifference('A'), MinimalDifference('B')]

        err = ValidationError(error_list)
        self.assertEqual(err.differences, error_list)

    def test_error_iter(self):
        error_list = [MinimalDifference('A'), MinimalDifference('B')]
        error_iter = iter(error_list)

        err = ValidationError(error_iter)
        self.assertEqual(err.differences, error_list, 'iterable should be converted to list')

    def test_error_dict(self):
        error_dict = {'a': MinimalDifference('A'), 'b': MinimalDifference('B')}

        err = ValidationError(error_dict)
        self.assertEqual(err.differences, error_dict)

    def test_error_iteritems(self):
        error_dict = {'a': MinimalDifference('A'), 'b': MinimalDifference('B')}
        error_iteritems = getattr(error_dict, 'iteritems', error_dict.items)()

        err = ValidationError(error_iteritems)
        self.assertEqual(err.differences, error_dict)

    def test_single_diff(self):
        single_diff = MinimalDifference('A')
        err = ValidationError(single_diff)
        self.assertEqual(err.differences, [single_diff])

    def test_bad_args(self):
        with self.assertRaises(TypeError, msg='must be iterable'):
            bad_arg = object()
            ValidationError(bad_arg, 'invalid data')

    def test_str_method(self):
        # Assert basic format and trailing comma.
        err = ValidationError([MinimalDifference('A')], 'invalid data')
        expected = """
            invalid data (1 difference): [
                MinimalDifference('A'),
            ]
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(str(err), expected)

        # Assert without description.
        err = ValidationError([MinimalDifference('A')])  # <- No description!
        expected = """
            1 difference: [
                MinimalDifference('A'),
            ]
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(str(err), expected)

        # Assert "no cacheing"--objects that inhereit from some
        # Exceptions can cache their str--but ValidationError should
        # not do this.
        err._differences = [MinimalDifference('B')]
        err._description = 'changed'
        updated = textwrap.dedent("""
            changed (1 difference): [
                MinimalDifference('B'),
            ]
        """).strip()
        self.assertEqual(str(err), updated)

        # Assert dict format and trailing comma.
        err = ValidationError({'x': MinimalDifference('A'),
                               'y': MinimalDifference('B')},
                              'invalid data')
        regex = textwrap.dedent(r"""
            invalid data \(2 differences\): \{
                '[xy]': MinimalDifference\('[AB]'\),
                '[xy]': MinimalDifference\('[AB]'\),
            \}
        """).strip()
        self.assertRegex(str(err), regex)  # <- Using regex because dict order
                                           #    can not be assumed for Python
                                           #    versions 3.5 and earlier.

    def test_str_sorting(self):
        """Check that string shows differences sorted by arguments."""
        self.maxDiff = None

        # Check sorting of non-mapping container.
        err = ValidationError([MinimalDifference('Z', 'Z'),
                               MinimalDifference('Z'),
                               MinimalDifference(1, 'C'),
                               MinimalDifference('B', 'C'),
                               MinimalDifference('A'),
                               MinimalDifference(1.5),
                               MinimalDifference(True),
                               MinimalDifference(0),
                               MinimalDifference(None)])
        expected = """
            9 differences: [
                MinimalDifference(None),
                MinimalDifference(0),
                MinimalDifference(True),
                MinimalDifference(1, 'C'),
                MinimalDifference(1.5),
                MinimalDifference('A'),
                MinimalDifference('B', 'C'),
                MinimalDifference('Z'),
                MinimalDifference('Z', 'Z'),
            ]
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(str(err), expected)

        # Make sure that all differences are being sorted (not just
        # those being displayed).
        err._should_truncate = lambda lines, chars: lines > 4
        expected = """
            9 differences: [
                MinimalDifference(None),
                MinimalDifference(0),
                MinimalDifference(True),
                MinimalDifference(1, 'C'),
                ...
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(str(err), expected)

        # Check sorting of non-mapping container.
        err = ValidationError(
            {
                ('C', 3): [MinimalDifference('Z', 3), MinimalDifference(1, 2)],
                ('A', 'C'): MinimalDifference('A'),
                'A': [MinimalDifference('C'), MinimalDifference(1)],
                2: [MinimalDifference('B'), MinimalDifference('A')],
                1: MinimalDifference('A'),
                (None, 4): MinimalDifference('A'),
            },
            'description string'
        )
        expected = """
            description string (6 differences): {
                1: MinimalDifference('A'),
                2: [MinimalDifference('A'), MinimalDifference('B')],
                'A': [MinimalDifference(1), MinimalDifference('C')],
                (None, 4): MinimalDifference('A'),
                ('A', 'C'): MinimalDifference('A'),
                ('C', 3): [MinimalDifference(1, 2), MinimalDifference('Z', 3)],
            }
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(str(err), expected)

    def test_str_truncation(self):
        # Assert optional truncation behavior.
        err = ValidationError([MinimalDifference('A'),
                               MinimalDifference('B'),
                               MinimalDifference('C'),],
                              'invalid data')
        self.assertIsNone(err._should_truncate)
        self.assertIsNone(err._truncation_notice)
        no_truncation = """
            invalid data (3 differences): [
                MinimalDifference('A'),
                MinimalDifference('B'),
                MinimalDifference('C'),
            ]
        """
        no_truncation = textwrap.dedent(no_truncation).strip()
        self.assertEqual(str(err), no_truncation)

        # Truncate without notice.
        err._should_truncate = lambda line_count, char_count: char_count > 35
        err._truncation_notice = None
        truncation_witout_notice = """
            invalid data (3 differences): [
                MinimalDifference('A'),
                ...
        """
        truncation_witout_notice = textwrap.dedent(truncation_witout_notice).strip()
        self.assertEqual(str(err), truncation_witout_notice)

        # Truncate and use truncation notice.
        err._should_truncate = lambda line_count, char_count: char_count > 35
        err._truncation_notice = 'Message truncated.'
        truncation_plus_notice = """
            invalid data (3 differences): [
                MinimalDifference('A'),
                ...

            Message truncated.
        """
        truncation_plus_notice = textwrap.dedent(truncation_plus_notice).strip()
        self.assertEqual(str(err), truncation_plus_notice)

    def test_repr(self):
        err = ValidationError([MinimalDifference('A')])  # <- No description.
        expected = "ValidationError([MinimalDifference('A')])"
        self.assertEqual(repr(err), expected)

        err = ValidationError([MinimalDifference('A')], 'description string')
        expected = "ValidationError([MinimalDifference('A')], 'description string')"
        self.assertEqual(repr(err), expected)

        # Objects that inhereit from some Exceptions can cache their
        # repr--but ValidationError should not do this.
        err._differences = [MinimalDifference('B')]
        err._description = 'changed'
        self.assertNotEqual(repr(err), expected, 'exception should not cache repr')

        updated = "ValidationError([MinimalDifference('B')], 'changed')"
        self.assertEqual(repr(err), updated)

    def test_module_property(self):
        """Module property should be 'datatest' so that testing
        frameworks display the error as 'datatest.ValidationError'.

        By default, instances would be displayed as
        'datatest.validation.ValidationError' but this awkwardly
        long and the submodule name--'validation'--is not needed
        because the class is imported into datatest's root namespace.
        """
        import datatest
        msg = "should be in datatest's root namespace"
        self.assertIs(ValidationError, datatest.ValidationError)

        msg = "should be set to 'datatest' to shorten display name"
        self.assertEqual('datatest', ValidationError.__module__)

    def test_args(self):
        err = ValidationError([MinimalDifference('A')], 'invalid data')
        self.assertEqual(err.args, ([MinimalDifference('A')], 'invalid data'))

        err = ValidationError([MinimalDifference('A')])
        self.assertEqual(err.args, ([MinimalDifference('A')], None))


class TestValidationIntegration(unittest.TestCase):
    def test_valid(self):
        a = set([1, 2, 3])
        b = set([2, 3, 4])

        self.assertTrue(valid(a, a))

        self.assertFalse(valid(a, b))

    def test_validate(self):
        a = set([1, 2, 3])
        b = set([2, 3, 4])

        self.assertIsNone(validate(a, a))

        with self.assertRaises(ValidationError):
            validate(a, b)


class TestCheckSingleValue(unittest.TestCase):
    def test_simple_equality(self):
        """Should return None or single difference."""
        self.assertIsNone(_check_single_value('a', 'a'))
        self.assertEqual(
            _check_single_value('a', 'b'),
            Invalid('a', 'b'),
        )

        self.assertIsNone(_check_single_value(1, 1))
        self.assertEqual(
            _check_single_value(1, 5),
            Deviation(-4, 5),
        )

    def test_predicate_matcher(self):
        """Should return None or single difference."""
        self.assertIsNone(_check_single_value('a', True))
        self.assertEqual(
            _check_single_value('a', False),
            Invalid('a', False),
        )

    def test_set_of_values(self):
        """Should return None or list of differences."""
        self.assertIsNone(_check_single_value('abc', set(['abc'])))
        self.assertEqual(
            _check_single_value('abc', set(['abc', 'def'])),
            [Missing('def')],
        )

    def test_required_subclass(self):
        class RequiredFoo(Required):
            @property
            def msg(self):
                return "equals 'foo'"

            def filterfalse(self, iterable):
                for x in iterable:
                    if x != 'foo':
                        yield Invalid('Value is not foo!')

        required_foo = RequiredFoo()
        self.assertIsNone(_check_single_value('foo', required_foo))
        self.assertEqual(
            _check_single_value('a', required_foo),
            [Invalid('Value is not foo!')],
        )


class TestGetRequired(unittest.TestCase):
    def test_set(self):
        required = _get_required(set(['foo']))
        self.assertIsInstance(required, RequiredSet)

    def test_predicate(self):
        required = _get_required('foo')
        self.assertIsInstance(required, RequiredPredicate)

    def test_sequence(self):  # For base-item sequences.
        required = _get_required(['foo'])
        self.assertIsInstance(required, RequiredSequence)

    def test_required(self):
        original = RequiredPredicate('foo')
        required = _get_required(original)
        self.assertIs(required, original)


class TestGetGroupRequirement(unittest.TestCase):
    def test_set(self):
        requirement = _get_group_requirement(set(['foo']))
        self.assertTrue(requirement._group_requirement)

    def test_predicate(self):
        requirement = _get_group_requirement('foo')
        self.assertTrue(requirement._group_requirement)

        requirement = _get_group_requirement('bar', show_expected=True)
        self.assertTrue(requirement._group_requirement)

    @unittest.skip('TODO: Implement using new @group_requirement decorator.')
    def test_sequence(self):  # For base-item sequences.
        requirement = _get_group_requirement(['foo'])
        self.assertTrue(requirement._group_requirement)

    def test_already_requirement(self):
        """If the requirement is already a group requirement, then the
        original object should be returned.
        """
        requirement1 = _get_group_requirement('foo')
        requirement2 = _get_group_requirement(requirement1)
        self.assertIs(requirement1, requirement2)


class TestApplyRequiredToData(unittest.TestCase):
    def test_set_against_container(self):
        required = RequiredSet(set(['foo']))

        result = _apply_required_to_data(['foo', 'foo'], required)
        self.assertIsNone(result)

        result = _apply_required_to_data(['foo', 'bar'], required)
        self.assertEqual(list(result), [Extra('bar')])

    def test_set_against_single_item(self):
        required = RequiredSet(set(['foo']))
        result = _apply_required_to_data('foo', required)
        self.assertIsNone(result)

        required = RequiredSet(set(['foo', 'bar']))
        result = _apply_required_to_data('bar', required)
        self.assertEqual(result, Missing('foo'), msg='no container')

        required = RequiredSet(set(['foo']))
        result = _apply_required_to_data('bar', required)
        result = list(result)
        self.assertEqual(len(result), 2, msg='expects container if multiple diffs')
        self.assertIn(Missing('foo'), result)
        self.assertIn(Extra('bar'), result)

    def test_predicate_against_container(self):
        required = RequiredPredicate('foo')
        result = _apply_required_to_data(['foo', 'foo'], required)
        self.assertIsNone(result)

        required = RequiredPredicate('foo')
        result = _apply_required_to_data(['foo', 'bar'], required)
        self.assertEqual(list(result), [Invalid('bar')], msg='should be iterable of diffs')

        required = RequiredPredicate(10)
        result = _apply_required_to_data([10, 12], required)
        self.assertEqual(list(result), [Deviation(+2, 10)], msg='should be iterable of diffs')

    def test_predicate_against_single_item(self):
        required = RequiredPredicate('foo')
        result = _apply_required_to_data('foo', required)
        self.assertIsNone(result)

        required = RequiredPredicate('foo')
        result = _apply_required_to_data('bar', required)
        self.assertEqual(result, Invalid('bar', expected='foo'), msg='should have no container and include "expected"')

        required = RequiredPredicate(10)
        result = _apply_required_to_data(12, required)
        self.assertEqual(result, Deviation(+2, 10), msg='should have no container')

        required = RequiredPredicate((1, 'j'))
        result = _apply_required_to_data((1, 'x'), required)
        self.assertEqual(result, Invalid((1, 'x'), (1, 'j')))


class TestApplyRequiredToMapping(unittest.TestCase):
    def test_no_differences(self):
        # Set membership.
        data = {'a': ['x', 'y'], 'b': ['x', 'y'],}
        required = RequiredSet(set(['x', 'y']))
        result = _apply_required_to_mapping(data, required)
        self.assertEqual(dict(result), {})

        # Equality of single value.
        data = {'a': 'x', 'b': 'x'}
        required = RequiredPredicate('x')
        result = _apply_required_to_mapping(data, required)
        self.assertEqual(dict(result), {})

    def test_some_differences(self):
        # Set membership.
        data = {'a': ['x', 'x'], 'b': ['x', 'y', 'z']}
        required = RequiredSet(set(['x', 'y']))
        result = _apply_required_to_mapping(data, required)
        expected = {'a': [Missing('y')], 'b': [Extra('z')]}
        self.assertEqual(dict(result), expected)

        # Equality of single values.
        data = {'a': 'x', 'b': 10, 'c': 9}
        required = RequiredPredicate(9)
        result = _apply_required_to_mapping(data, required)
        expected = {'a': Invalid('x'), 'b': Deviation(+1, 9)}
        self.assertEqual(dict(result), expected)

        # Equality of multiple values.
        data = {'a': ['x', 'j'], 'b': [10, 9], 'c': [9, 9]}
        required = RequiredPredicate(9)
        result = _apply_required_to_mapping(data, required)
        expected = {'a': [Invalid('x'), Invalid('j')], 'b': [Deviation(+1, 9)]}
        self.assertEqual(dict(result), expected)

        # Equality of single tuples.
        data = {'a': ('x', 1.0), 'b': ('y', 2), 'c': ('x', 3)}
        required = RequiredPredicate(('x', int))
        result = _apply_required_to_mapping(data, required)
        expected = {'a': Invalid(('x', 1.0)), 'b': Invalid(('y', 2))}
        self.assertEqual(dict(result), expected)

        # Equality of multiple tuples.
        data = {'a': [('x', 1.0), ('x', 1)], 'b': [('y', 2), ('x', 3)]}
        required = RequiredPredicate(('x', int))
        result = _apply_required_to_mapping(data, required)
        expected = {'a': [Invalid(('x', 1.0))], 'b': [Invalid(('y', 2))]}
        self.assertEqual(dict(result), expected)


class TestApplyMappingToMapping(unittest.TestCase):
    """Calling _apply_mapping_to_mapping() should run the appropriate
    comparison function (internally) for each value-group and
    return the results as an iterable of key-value items.
    """
    def test_no_differences(self):
        # Set membership.
        data = {'a': ['x', 'y']}
        result = _apply_mapping_to_mapping(data, {'a': set(['x', 'y'])})
        self.assertEqual(dict(result), {})

        # Equality of single values.
        data = {'a': 'x', 'b': 'y'}
        result = _apply_mapping_to_mapping(data, {'a': 'x', 'b': 'y'})
        self.assertEqual(dict(result), {})

    def test_bad_data_type(self):
        not_a_mapping = 'abc'
        a_mapping = {'a': 'abc'}

        with self.assertRaises(TypeError):
            result = _apply_mapping_to_mapping(not_a_mapping, a_mapping)
            dict(result)  # <- Evaluate generator.

    def test_some_differences(self):
        # Set membership.
        data = {'a': ['x', 'x'], 'b': ['x', 'y', 'z']}
        result = _apply_mapping_to_mapping(data, {'a': set(['x', 'y']),
                                                  'b': set(['x', 'y'])})
        expected = {'a': [Missing('y')], 'b': [Extra('z')]}
        self.assertEqual(dict(result), expected)

        # Equality of single values.
        data = {'a': 'x', 'b': 10}
        result = _apply_mapping_to_mapping(data, {'a': 'j', 'b': 9})
        expected = {'a': Invalid('x', expected='j'), 'b': Deviation(+1, 9)}
        self.assertEqual(dict(result), expected)

        data = {'a': 'x', 'b': 10, 'c': 10}
        result = _apply_mapping_to_mapping(data, {'a': 'j', 'b': 'k', 'c': 9})
        expected = {'a': Invalid('x', 'j'), 'b': Invalid(10, 'k'), 'c': Deviation(+1, 9)}
        self.assertEqual(dict(result), expected)

        # Equality of multiple values.
        data = {'a': ['x', 'j'], 'b': [10, 9]}
        result = _apply_mapping_to_mapping(data, {'a': 'j', 'b': 9})
        expected = {'a': [Invalid('x')], 'b': [Deviation(+1, 9)]}
        self.assertEqual(dict(result), expected)

        # Equality of single tuples.
        data = {'a': (1, 'x'), 'b': (9, 10)}
        result = _apply_mapping_to_mapping(data, {'a': (1, 'j'), 'b': (9, 9)})
        expected = {'a': Invalid((1, 'x'), expected=(1, 'j')),
                    'b': Invalid((9, 10), expected=(9, 9))}
        self.assertEqual(dict(result), expected)

        # Equality of multiple tuples.
        data = {'a': [(1, 'j'), (1, 'x')], 'b': [(9, 9), (9, 10)]}
        result = _apply_mapping_to_mapping(data, {'a': (1, 'j'), 'b': (9, 9)})
        expected = {'a': [Invalid((1, 'x'))],
                    'b': [Invalid((9, 10))]}
        self.assertEqual(dict(result), expected)

    def test_missing_keys(self):
        # Equality of multiple values, missing key with single item.
        data = {'a': ['x', 'j'], 'b': [10, 9]}
        result = _apply_mapping_to_mapping(data, {'a': 'j', 'b': 9, 'c': 'z'})
        expected = {'a': [Invalid('x')], 'b': [Deviation(+1, 9)], 'c': Missing('z')}
        self.assertEqual(dict(result), expected)

        # Equality of multiple values, missing key with single item.
        data = {'a': ['x', 'j'], 'b': [10, 9], 'c': 'z'}
        result = _apply_mapping_to_mapping(data, {'a': 'j', 'b': 9})
        expected = {'a': [Invalid('x')], 'b': [Deviation(+1, 9)], 'c': Extra('z')}
        self.assertEqual(dict(result), expected)

        # Missing key, set membership.
        data = {'a': 'x'}
        result = _apply_mapping_to_mapping(data, {'a': 'x', 'b': set(['z'])})
        expected = {'b': [Missing('z')]}
        self.assertEqual(dict(result), expected)

    def test_empty_vs_nonempty_values(self):
        empty = {}
        nonempty = {'a': set(['x'])}

        result = _apply_mapping_to_mapping(empty, empty)
        self.assertEqual(dict(result), {})

        result = _apply_mapping_to_mapping(nonempty, empty)
        self.assertEqual(dict(result), {'a': Extra(set(['x']))})

        result = _apply_mapping_to_mapping(empty, nonempty)
        self.assertEqual(dict(result), {'a': [Missing('x')]})


class TestValidate2(unittest.TestCase):
    """An integration test to check behavior of validate() function."""
    def test_required_vs_data_passing(self):
        """Single requirement to BaseElement or non-mapping
        container of data.
        """
        data = ('abc', 1)  # A single base element.
        requirement = ('abc', int)
        self.assertIsNone(validate2(data, requirement))

        data = [('abc', 1), ('abc', 2)]  # Non-mapping container of base elements.
        requirement = ('abc', int)
        self.assertIsNone(validate2(data, requirement))

    def test_required_vs_data_failing(self):
        """Apply single requirement to BaseElement or non-mapping
        container of data.
        """
        with self.assertRaises(ValidationError) as cm:
            data = ('abc', 1.0)  # A single base element.
            requirement = ('abc', int)
            validate2(data, requirement)
        differences = cm.exception.differences
        self.assertEqual(differences, [Invalid(('abc', 1.0), ('abc', int))])

        with self.assertRaises(ValidationError) as cm:
            data = [('abc', 1.0), ('xyz', 2)]  # Non-mapping container of base elements.
            requirement = ('abc', int)
            validate2(data, requirement)
        differences = cm.exception.differences
        self.assertEqual(differences, [Invalid(('abc', 1.0)), Invalid(('xyz', 2))])

    def test_required_vs_mapping_passing(self):
        data = {'a': ('abc', 1), 'b': ('abc', 2)}  # Mapping of base-elements.
        requirement = ('abc', int)
        self.assertIsNone(validate2(data, requirement))

        data = {'a': [1, 2], 'b': [3, 4]}  # Mapping of containers.
        requirement = int
        self.assertIsNone(validate2(data, requirement))

    def test_required_vs_mapping_failing(self):
        with self.assertRaises(ValidationError) as cm:
            data = {'a': ('abc', 1.0), 'b': ('xyz', 2)}  # Mapping of base-elements.
            requirement = ('abc', int)
            validate2(data, requirement)
        differences = cm.exception.differences
        self.assertEqual(differences, {'a': Invalid(('abc', 1.0)), 'b': Invalid(('xyz', 2))})

        with self.assertRaises(ValidationError) as cm:
            data = {'a': [1, 2.0], 'b': [3.0, 4]}  # Mapping of containers.
            validate2(data, int)
        differences = cm.exception.differences
        self.assertEqual(differences, {'a': [Invalid(2.0)], 'b': [Invalid(3.0)]})

    def test_mapping_vs_mapping_passing(self):
        data = {'a': ('abc', 1), 'b': ('abc', 2.0)}  # Mapping of base-elements.
        requirement = {'a': ('abc', int), 'b': ('abc', float)}  # Mapping of requirements.
        self.assertIsNone(validate2(data, requirement))

        data = {'a': [('abc', 1), ('abc', 2)],
                'b': [('abc', 1.0), ('abc', 2.0)]}  # Mapping of containers.
        requirement = {'a': ('abc', int), 'b': ('abc', float)}  # Mapping of requirements.
        self.assertIsNone(validate2(data, requirement))

    def test_mapping_vs_mapping_failing(self):
        with self.assertRaises(ValidationError) as cm:
            data = {'a': ('abc', 1.0), 'b': ('xyz', 2.0)}  # Mapping of base-elements.
            requirement = {'a': ('abc', int), 'b': ('abc', float)}  # Mapping of requirements.
            validate2(data, requirement)
        actual = cm.exception.differences
        expected = {
            'a': Invalid(('abc', 1.0), ('abc', int)),
            'b': Invalid(('xyz', 2.0), ('abc', float)),
        }
        self.assertEqual(actual, expected)

        with self.assertRaises(ValidationError) as cm:
            data = {'a': [('abc', 1.0), ('abc', 2)],
                    'b': [('abc', 1.0), ('xyz', 2.0)]}  # Mapping of containers.
            requirement = {'a': ('abc', int), 'b': ('abc', float)}  # Mapping of requirements.
            validate2(data, requirement)
        actual = cm.exception.differences
        expected = {
            'a': [Invalid(('abc', 1.0))],
            'b': [Invalid(('xyz', 2.0))],
        }
        self.assertEqual(actual, expected)

    @unittest.skip('TODO: Implement mismatched key handling for validate2().')
    def test_mapping_vs_mapping_mismatched_keys(self):
        # Mapping of base-elements.
        data = {'a': ('abc', 1), 'c': ('abc', 2.0)}
        requirement = {'a': ('abc', int), 'b': ('abc', float)}
        with self.assertRaises(ValidationError) as cm:
            validate2(data, requirement)
        actual = cm.exception.differences
        expected = {
            'b': Missing(('abc', float)),
            'c': Extra(('abc', 2.0)),
        }
        self.assertEqual(actual, expected)

        # Mapping of containers (lists of base-elements).
        data = {
            'a': [('abc', 1), ('abc', 2)],
            'c': [('abc', 1.0), ('abc', 2.0)],
        }
        requirement = {'a': ('abc', int), 'b': ('abc', float)}
        with self.assertRaises(ValidationError) as cm:
            validate2(data, requirement)
        actual = cm.exception.differences
        expected = {
            'c': [Extra(('abc', 1.0)), Extra(('abc', 2.0))],
            'b': Missing(('abc', float)),
        }
        self.assertEqual(actual, expected)
