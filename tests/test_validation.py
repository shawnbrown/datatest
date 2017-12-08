"""Tests for validation and comparison functions."""
import re
import textwrap
from . import _unittest as unittest
from datatest.utils.misc import _is_consumable

from datatest.difference import BaseDifference
from datatest.difference import Extra
from datatest.difference import Missing
from datatest.difference import Invalid
from datatest.difference import Deviation
from datatest.difference import NOTFOUND

from datatest.validation import _require_sequence
from datatest.validation import _require_set
from datatest.validation import _require_callable
from datatest.validation import _require_regex
from datatest.validation import _require_equality
from datatest.validation import _require_single_equality
from datatest.validation import _get_msg_and_func
from datatest.validation import _apply_mapping_requirement
from datatest.validation import _get_invalid_info
from datatest.validation import ValidationError
from datatest.validation import is_valid
from datatest.validation import validate


class TestRequireSequence(unittest.TestCase):
    def test_no_difference(self):
        first = ['aaa', 'bbb', 'ccc']
        second = ['aaa', 'bbb', 'ccc']
        error = _require_sequence(first, second)
        self.assertIsNone(error)  # No difference, returns None.

    def test_extra(self):
        data = ['aaa', 'bbb', 'ccc', 'ddd', 'eee']
        requirement = ['aaa', 'ccc', 'eee']
        error = _require_sequence(data, requirement)
        self.assertEqual(error, {(1, 1): Extra('bbb'), (3, 2): Extra('ddd')})

    def test_extra_with_empty_requirement(self):
        data = ['aaa', 'bbb']
        requirement = []
        error = _require_sequence(data, requirement)
        self.assertEqual(error, {(0, 0): Extra('aaa'), (1, 0): Extra('bbb')})

    def test_missing(self):
        data = ['bbb', 'ddd']
        requirement = ['aaa', 'bbb', 'ccc', 'ddd', 'eee']
        error = _require_sequence(data, requirement)
        expected = {
            (0, 0): Missing('aaa'),
            (1, 2): Missing('ccc'),
            (2, 4): Missing('eee'),
        }
        self.assertEqual(error, expected)

    def test_missing_with_empty_data(self):
        data = []
        requirement = ['aaa', 'bbb']
        error = _require_sequence(data, requirement)
        self.assertEqual(error, {(0, 0): Missing('aaa'), (0, 1): Missing('bbb')})

    def test_invalid(self):
        data = ['aaa', 'bbb', '---', 'ddd', 'eee']
        requirement = ['aaa', 'bbb', 'ccc', 'ddd', 'eee']
        actual = _require_sequence(data, requirement)
        expected = {
            (2, 2): Invalid('---', 'ccc'),
        }
        self.assertEqual(actual, expected)

    def test_mixed_differences(self):
        data = ['aaa', '---', 'ddd', 'eee', 'ggg']
        requirement = ['aaa', 'bbb', 'ccc', 'ddd', 'fff']
        actual = _require_sequence(data, requirement)
        expected = {
            (1, 1): Invalid('---', 'bbb'),
            (2, 2): Missing('ccc'),
            (3, 4): Invalid('eee', 'fff'),
            (4, 5): Extra('ggg'),
        }
        self.assertEqual(actual, expected)

    def test_unhashable(self):
        """Uses "deep hashing" to attempt to sort unhashable types."""
        first = [{'a': 1}, {'b': 2}, {'c': 3}]
        second = [{'a': 1}, {'b': 2}, {'c': 3}]
        error = _require_sequence(first, second)
        self.assertIsNone(error)  # No difference, returns None.

        data = [{'a': 1}, {'-': 0}, {'d': 4}, {'e': 5}, {'g': 7}]
        requirement = [{'a': 1}, {'b': 2}, {'c': 3}, {'d': 4}, {'f': 6}]
        actual = _require_sequence(data, requirement)
        expected = {
            (1, 1): Invalid({'-': 0}, {'b': 2}),
            (2, 2): Missing({'c': 3}),
            (3, 4): Invalid({'e': 5}, {'f': 6}),
            (4, 5): Extra({'g': 7}),
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


class TestRequireCallable(unittest.TestCase):
    def setUp(self):
        self.isdigit = lambda x: x.isdigit()

    def test_all_true(self):
        data = ['10', '20', '30']
        result = _require_callable(data, self.isdigit)
        self.assertIsNone(result)

    def test_some_false(self):
        """Elements that evaluate to False are returned as Invalid() errors."""
        data = ['10', '20', 'XX']
        result = _require_callable(data, self.isdigit)
        self.assertEqual(list(result), [Invalid('XX')])

    def test_duplicate_false(self):
        """Should return an error for every false result (incl. duplicates)."""
        data = ['10', '20', 'XX', 'XX', 'XX']  # <- Multiple XX's.
        result = _require_callable(data, self.isdigit)
        self.assertEqual(list(result), [Invalid('XX'), Invalid('XX'), Invalid('XX')])

    def test_raised_error(self):
        """When an Exception is raised, it counts as False."""
        data = ['10', '20', 30]  # <- Fails on 30 (int has no 'isdigit' method).
        result = _require_callable(data, self.isdigit)
        self.assertEqual(list(result), [Invalid(30)])

    def test_returned_error(self):
        """When a difference is returned, it is used in place of Invalid."""
        def func(x):
            if x == 'c':
                return Invalid("Letter 'c' is no good!")
            return True

        data = ['a', 'b', 'c']
        result = _require_callable(data, func)
        self.assertEqual(list(result), [Invalid("Letter 'c' is no good!")])

    def test_bad_return_type(self):
        """If callable returns an unexpected type, raise a TypeError."""
        def func(x):
            return Exception('my error')  # <- Not True, False or difference!

        with self.assertRaises(TypeError):
            result = _require_callable(['a', 'b', 'c'], func)
            list(result)  # Evaluate generator.

    def test_notfound(self):
        def func(x):
            return False
        result = _require_callable(NOTFOUND, func)
        self.assertEqual(result, Invalid(None))


class TestRequireRegex(unittest.TestCase):
    def setUp(self):
        self.regex = re.compile('[a-z][0-9]+')

    def test_all_true(self):
        data = iter(['a1', 'b2', 'c3'])
        result = _require_regex(data, self.regex)
        self.assertIsNone(result)

    def test_some_false(self):
        data = iter(['a1', 'b2', 'XX'])
        result = _require_regex(data, self.regex)
        self.assertEqual(list(result), [Invalid('XX')])

    def test_duplicate_false(self):
        """Should return an error for every non-match (incl. duplicates)."""
        data = iter(['a1', 'b2', 'XX', 'XX', 'XX'])  # <- Multiple XX's.
        result = _require_regex(data, self.regex)
        self.assertEqual(list(result), [Invalid('XX'), Invalid('XX'), Invalid('XX')])

    def test_raised_error(self):
        """When an Exception is raised, it counts as False."""
        data = ['a1', 'b2', 30]  # <- Fails on 30 (re.search() expects a string).
        result = _require_regex(data, self.regex)
        self.assertEqual(list(result), [Invalid(30)])

    def test_notfound(self):
        result = _require_regex(NOTFOUND, self.regex)
        self.assertEqual(result, Invalid(None))


class TestRequireEquality(unittest.TestCase):
    def test_eq(self):
        """Should use __eq__() comparison, not __ne__()."""

        class EqualsAll(object):
            def __init__(_self):
                _self.times_called = 0

            def __eq__(_self, other):
                _self.times_called += 1
                return True

            def __ne__(_self, other):
                return NotImplemented

        data = ['A', 'A', 'A']
        requirement = EqualsAll()
        result = _require_equality(data, requirement)
        self.assertEqual(requirement.times_called, len(data))

    def test_all_true(self):
        result = _require_equality(iter(['A', 'A']), 'A')
        self.assertIsNone(result)

    def test_some_invalid(self):
        result = _require_equality(iter(['A', 'XX']), 'A')
        self.assertEqual(list(result), [Invalid('XX')])

    def test_some_deviation(self):
        result = _require_equality(iter([10, 11]), 10)
        self.assertEqual(list(result), [Deviation(+1, 10)])

    def test_invalid_and_deviation(self):
        result = _require_equality(iter([10, 'XX', 11]), 10)

        result = list(result)
        self.assertEqual(len(result), 2)
        self.assertIn(Invalid('XX'), result)
        self.assertIn(Deviation(+1, 10), result)

    def test_dict_comparison(self):
        data = iter([{'a': 1}, {'b': 2}])
        result = _require_equality(data, {'a': 1})
        self.assertEqual(list(result), [Invalid({'b': 2})])

    def test_broken_comparison(self):
        class BadClass(object):
            def __eq__(self, other):
                raise Exception("I have betrayed you!")

            def __hash__(self):
                return hash((self.__class__, 101))

        bad_instance = BadClass()

        data = iter([10, bad_instance, 10])
        result = _require_equality(data, 10)
        self.assertEqual(list(result), [Invalid(bad_instance)])


class TestRequireSingleEquality(unittest.TestCase):
    def test_eq(self):
        """Should use __eq__() comparison, not __ne__()."""

        class EqualsAll(object):
            def __init__(_self):
                _self.times_called = 0

            def __eq__(_self, other):
                _self.times_called += 1
                return True

            def __ne__(_self, other):
                return NotImplemented

        requirement = EqualsAll()
        result = _require_single_equality('A', requirement)
        self.assertEqual(requirement.times_called, 1)

    def test_all_true(self):
        result = _require_single_equality('A', 'A')
        self.assertIsNone(result)

    def test_some_invalid(self):
        result = _require_single_equality('XX', 'A')
        self.assertEqual(result, Invalid('XX', 'A'))

    def test_deviation(self):
        result = _require_single_equality(11, 10)
        self.assertEqual(result, Deviation(+1, 10))

    def test_invalid(self):
        result = _require_single_equality('XX', 10)
        self.assertEqual(result, Invalid('XX', 10))

    def test_dict_comparison(self):
        result = _require_single_equality({'a': 1}, {'a': 2})
        self.assertEqual(result, Invalid({'a': 1}, {'a': 2}))

    def test_broken_comparison(self):
        class BadClass(object):
            def __eq__(self, other):
                raise Exception("I have betrayed you!")

            def __hash__(self):
                return hash((self.__class__, 101))

        bad_instance = BadClass()
        result = _require_single_equality(bad_instance, 10)
        self.assertEqual(result, Invalid(bad_instance, 10))


class TestGetMsgAndFunc(unittest.TestCase):
    def setUp(self):
        self.multiple = ['A', 'B', 'A']
        self.single = 'B'

    def test_sequence(self):
        default_msg, require_func = _get_msg_and_func(['A', 'B'], ['A', 'B'])
        self.assertIsInstance(default_msg, str)
        self.assertEqual(require_func, _require_sequence)

    def test_set(self):
        default_msg, require_func = _get_msg_and_func(['A', 'B'], set(['A', 'B']))
        self.assertIsInstance(default_msg, str)
        self.assertEqual(require_func, _require_set)

    def test_callable(self):
        def myfunc(x):
            return True
        default_msg, require_func = _get_msg_and_func(['A', 'B'], myfunc)
        self.assertIn(myfunc.__name__, default_msg, 'message should include function name')
        self.assertEqual(require_func, _require_callable)

        mylambda = lambda x: True
        default_msg, require_func = _get_msg_and_func(['A', 'B'], mylambda)
        self.assertIn('<lambda>', default_msg, 'message should include function name')
        self.assertEqual(require_func, _require_callable)

        class MyClass(object):
            def __call__(_self, x):
                return True
        myinstance = MyClass()
        default_msg, require_func = _get_msg_and_func(['A', 'B'], myinstance)
        self.assertIn('MyClass', default_msg, 'message should include class name')
        self.assertEqual(require_func, _require_callable)

    def test_regex(self):
        myregex = re.compile('[AB]')
        default_msg, require_func = _get_msg_and_func(['A', 'B'], myregex)
        self.assertIn(repr(myregex.pattern), default_msg, 'message should include pattern')
        self.assertEqual(require_func, _require_regex)

    def test_equality(self):
        default_msg, require_func = _get_msg_and_func(['A', 'B'], 'A')
        self.assertIsInstance(default_msg, str)
        self.assertEqual(require_func, _require_equality)

        default_msg, require_func = _get_msg_and_func([{'a': 1}, {'a': 1}], {'a': 1})
        self.assertIsInstance(default_msg, str)
        self.assertEqual(require_func, _require_equality)

    def test_single_equality(self):
        default_msg, require_func = _get_msg_and_func('A', 'A')
        self.assertIsInstance(default_msg, str)
        self.assertEqual(require_func, _require_single_equality)

        default_msg, require_func = _get_msg_and_func({'a': 1}, {'a': 1})
        self.assertIsInstance(default_msg, str)
        self.assertEqual(require_func, _require_single_equality)


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
        self.assertEqual(result, {'a': {(1, 1): Invalid('y', 'z')}})

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

        msg, diffs = _get_invalid_info(mapping1, mapping2)
        self.assertTrue(_is_consumable(diffs))
        self.assertEqual(dict(diffs), {'b': Invalid('y', expected='z')})

        with self.assertRaises(TypeError):
            _get_invalid_info(set(['x', 'y']), mapping2)

    def test_mapping_data(self):
        """"When *data* is a mapping but *requirement* is a non-mapping."""
        mapping = {'a': 'x', 'b': 'y'}

        x_or_y = lambda value: value == 'x' or value == 'y'
        result = _get_invalid_info(mapping, x_or_y)
        self.assertIsNone(result)

        msg, diffs = _get_invalid_info(mapping, 'x')  # <- string
        self.assertTrue(_is_consumable(diffs))
        self.assertEqual(dict(diffs), {'b': Invalid('y', expected='x')})

        msg, diffs = _get_invalid_info(mapping, set('x'))  # <- set
        self.assertTrue(_is_consumable(diffs))
        self.assertEqual(dict(diffs), {'b': [Missing('x'), Extra('y')]})

    def test_nonmapping(self):
        """When neither *data* or *requirement* are mappings."""
        result = _get_invalid_info(set(['x', 'y']), set(['x', 'y']))
        self.assertIsNone(result)

        msg, diffs = _get_invalid_info(set(['x']), set(['x', 'y']))
        self.assertTrue(_is_consumable(diffs))
        self.assertEqual(list(diffs), [Missing('y')])


# FOR TESTING: A minimal subclass of BaseDifference.
# BaseDifference itself should not be instantiated
# directly.
class MinimalDifference(BaseDifference):
    pass


class TestValidationError(unittest.TestCase):
    def test_error_list(self):
        error_list = [MinimalDifference('A'), MinimalDifference('B')]

        err = ValidationError('invalid data', error_list)
        self.assertEqual(err.differences, error_list)

    def test_error_iter(self):
        error_list = [MinimalDifference('A'), MinimalDifference('B')]
        error_iter = iter(error_list)

        err = ValidationError('invalid data', error_iter)
        self.assertEqual(err.differences, error_list, 'iterable should be converted to list')

    def test_error_dict(self):
        error_dict = {'a': MinimalDifference('A'), 'b': MinimalDifference('B')}

        err = ValidationError('invalid data', error_dict)
        self.assertEqual(err.differences, error_dict)

    def test_error_iteritems(self):
        error_dict = {'a': MinimalDifference('A'), 'b': MinimalDifference('B')}
        error_iteritems = getattr(error_dict, 'iteritems', error_dict.items)()

        err = ValidationError('invalid data', error_iteritems)
        self.assertEqual(err.differences, error_dict)

    def test_bad_args(self):
        with self.assertRaises(TypeError, msg='must be iterable'):
            single_error = MinimalDifference('A')
            ValidationError('invalid data', single_error)

    def test_str(self):
        # Assert basic format and trailing comma.
        err = ValidationError('invalid data', [MinimalDifference('A')])
        expected = """
            invalid data (1 difference): [
                MinimalDifference('A'),
            ]
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(str(err), expected)

        # Assert "no cacheing"--objects that inhereit from some
        # Exceptions can cache their str--but ValidationError should
        # not do this.
        err.args = ('changed', [MinimalDifference('B')])  # <- Change existing error.
        updated = textwrap.dedent("""
            changed (1 difference): [
                MinimalDifference('B'),
            ]
        """).strip()
        self.assertEqual(str(err), updated)

        # Assert dict format and trailing comma.
        err = ValidationError('invalid data', {'x': MinimalDifference('A'),
                                               'y': MinimalDifference('B')})
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
        err = ValidationError('invalid data', [MinimalDifference('Z', 'Z'),
                                               MinimalDifference('Z'),
                                               MinimalDifference(1, 'C'),
                                               MinimalDifference('B', 'C'),
                                               MinimalDifference('A'),
                                               MinimalDifference(1.5),
                                               MinimalDifference(True),
                                               MinimalDifference(0),
                                               MinimalDifference(None)])
        expected = """
            invalid data (9 differences): [
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
            invalid data (9 differences): [
                MinimalDifference(None),
                MinimalDifference(0),
                MinimalDifference(True),
                MinimalDifference(1, 'C'),
                ...
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(str(err), expected)

        # Check sorting of non-mapping container.
        err = ValidationError('invalid data', {
            ('C', 3): [MinimalDifference('Z', 3), MinimalDifference(1, 2)],
            ('A', 'C'): MinimalDifference('A'),
            'A': [MinimalDifference('C'), MinimalDifference(1)],
            2: [MinimalDifference('B'), MinimalDifference('A')],
            1: MinimalDifference('A'),
            (None, 4): MinimalDifference('A'),
        })
        expected = """
            invalid data (6 differences): {
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
        err = ValidationError('invalid data', [MinimalDifference('A'),
                                               MinimalDifference('B'),
                                               MinimalDifference('C'),])
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
        err = ValidationError('invalid data', [MinimalDifference('A')])
        expected = "ValidationError('invalid data', [MinimalDifference('A')])"
        self.assertEqual(repr(err), expected)

        # Objects that inhereit from some Exceptions can cache their
        # repr--but ValidationError should not do this.
        err.args = ('changed', [MinimalDifference('B')])
        self.assertNotEqual(repr(err), expected, 'exception should not cache repr')

        updated = "ValidationError('changed', [MinimalDifference('B')])"
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
        err = ValidationError('invalid data', [MinimalDifference('A')])
        self.assertEqual(err.args, ('invalid data', [MinimalDifference('A')]))


class TestIsValidAndValidate(unittest.TestCase):
    def test_is_valid_and_validate(self):
        a = set([1, 2, 3])
        b = set([2, 3, 4])

        self.assertTrue(is_valid(a, a))
        self.assertFalse(is_valid(a, b))

        self.assertTrue(validate(a, a))
        with self.assertRaises(ValidationError):
            validate(a, b)
