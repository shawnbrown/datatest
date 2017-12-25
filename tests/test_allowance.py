# -*- coding: utf-8 -*-
import inspect
import sys
from . import _unittest as unittest
from datatest.utils.builtins import *
from datatest.utils import collections
from datatest.utils import contextlib
from datatest.utils import itertools

from datatest.allowance import BaseAllowance2
from datatest.allowance import LogicalAndMixin
from datatest.allowance import LogicalOrMixin
from datatest.allowance import ElementAllowance2
from datatest.allowance import allowed_missing
from datatest.allowance import allowed_extra
from datatest.allowance import allowed_invalid
from datatest.allowance import allowed_key
from datatest.allowance import allowed_args
from datatest.allowance import allowed_deviation
from datatest.allowance import allowed_percent_deviation
from datatest.allowance import BaseAllowance
from datatest.allowance import ElementAllowance
from datatest.allowance import allowed_specific
from datatest.allowance import allowed_limit

from datatest.validation import ValidationError
from datatest.difference import Missing
from datatest.difference import Extra
from datatest.difference import Invalid
from datatest.difference import Deviation


class MinimalAllowance(BaseAllowance2):  # A minimal subclass for
    def call_predicate(self, item):      # testing--defines three
        return False                     # concrete stubs to satisfy
                                         # abstract method requirement
    def __and__(self, other):            # of the base class.
        return NotImplemented

    def __or__(self, other):
        return NotImplemented


class TestBaseAllowance2(unittest.TestCase):
    def test_serialized_items(self):
        item_list = [1, 2]
        actual = BaseAllowance2._serialized_items(item_list)
        expected = [(None, 1), (None, 2)]
        self.assertEqual(list(actual), expected, 'serialize list of elements')

        item_dict = {'A': 'x', 'B': 'y'}
        actual = BaseAllowance2._serialized_items(item_dict)
        expected = [('A', 'x'), ('B', 'y')]
        self.assertEqual(sorted(actual), expected, 'serialize mapping of elements')

        item_dict = {'A': ['x', 'y'], 'B': ['x', 'y']}
        actual = BaseAllowance2._serialized_items(item_dict)
        expected = [('A', 'x'), ('A', 'y'), ('B', 'x'), ('B', 'y')]
        self.assertEqual(sorted(actual), expected, 'serialize mapping of lists')

    def test_deserialized_items(self):
        stream = [(None, 1), (None, 2)]
        actual = BaseAllowance2._deserialized_items(stream)
        expected = {None: [1, 2]}
        self.assertEqual(actual, expected)

        stream = [('A', 'x'), ('B', 'y')]
        actual = BaseAllowance2._deserialized_items(stream)
        expected = {'A': 'x', 'B': 'y'}
        self.assertEqual(actual, expected)

        stream = [('A', 'x'), ('A', 'y'), ('B', 'x'), ('B', 'y')]
        actual = BaseAllowance2._deserialized_items(stream)
        expected = {'A': ['x', 'y'], 'B': ['x', 'y']}
        self.assertEqual(actual, expected)

    def test_filterfalse(self):
        class allowed_missing(MinimalAllowance):
            def call_predicate(_self, item):
                return isinstance(item[1], Missing)

        allowed = allowed_missing()
        result = allowed._filterfalse([
            (None, Missing('A')),
            (None, Extra('B')),
        ])
        self.assertEqual(list(result), [(None, Extra('B'))])

    def test_enter_context(self):
        """The __enter__() method should return the object itself
        (see PEP 343 for context manager protocol).
        """
        allowance = MinimalAllowance()
        result = allowance.__enter__()
        self.assertIs(result, allowance)

    def test_exit_context(self):
        """The __exit__() method should re-raise exceptions that are
        not allowed and it should return True when there are no errors
        or if all differences have been allowed (see PEP 343 for
        context manager protocol).
        """
        try:
            raise ValidationError('invalid data', [Missing('A'), Extra('B')])
        except ValidationError:
            type, value, traceback = sys.exc_info()  # Get exception info.

        with self.assertRaises(ValidationError):
            allowance = MinimalAllowance()
            allowance.__exit__(type, value, traceback)


class TestAllowanceProtocol(unittest.TestCase):
    def setUp(self):
        class LoggingAllowance(MinimalAllowance):
            def __init__(_self, msg=None):
                _self.log = []
                super(LoggingAllowance, _self).__init__(msg)

            def __getattribute__(_self, name):
                attr = object.__getattribute__(_self, name)
                if name in ('log', '_filterfalse'):
                    return attr  # <- EXIT!

                if callable(attr):
                    def wrapper(*args, **kwds):
                        args_repr = [repr(arg) for arg in args]
                        for key, value in kwds.items():
                            args_repr.append('{0}={1!r}'.format(key, value))
                        args_repr = ', '.join(args_repr)
                        _self.log.append('{0}({1})'.format(name, args_repr))
                        return attr(*args, **kwds)
                    return wrapper  # <- EXIT!
                _self.log.append(name)
                return attr

        self.LoggingAllowance = LoggingAllowance

    def test_allowance_protocol(self):
        allowed = self.LoggingAllowance()
        result = allowed._filterfalse([
            ('foo', Missing('A')),
            ('foo', Extra('B')),
            ('bar', Missing('C')),
        ])
        list(result)  # Evaluate entire iterator, discarding result.

        expected = [
            'start_collection()',
            "start_group('foo')",
            "call_predicate(('foo', Missing('A')))",
            "call_predicate(('foo', Extra('B')))",
            "end_group('foo')",
            "start_group('bar')",
            "call_predicate(('bar', Missing('C')))",
            "end_group('bar')",
            'end_collection()',
        ]
        self.assertEqual(allowed.log, expected)


class TestLogicalMixins(unittest.TestCase):
    def setUp(self):
        class allowed_missing(MinimalAllowance):
            def call_predicate(_self, item):
                return isinstance(item[1], Missing)

        class allowed_value_A(MinimalAllowance):
            def call_predicate(_self, item):
                return item[1].args == ('A',)

        self.allowed_missing = allowed_missing()
        self.allowed_value_A = allowed_value_A()

    def test_LogicalAndMixin(self):
        class LeftAndRight(LogicalAndMixin, MinimalAllowance):
            pass

        with self.assertRaises(ValidationError) as cm:
            with LeftAndRight(left=self.allowed_missing,
                              right=self.allowed_value_A):
                raise ValidationError(
                    'example error',
                    [Missing('A'), Extra('A'), Missing('B'), Extra('B')],
                )
        differences = cm.exception.differences
        self.assertEqual(list(differences), [Extra('A'), Missing('B'), Extra('B')])

    def test_LogicalOrMixin(self):
        class LeftOrRight(LogicalOrMixin, MinimalAllowance):
            pass

        with self.assertRaises(ValidationError) as cm:
            with LeftOrRight(left=self.allowed_missing,
                             right=self.allowed_value_A):
                raise ValidationError(
                    'example error',
                    [Missing('A'), Extra('A'), Missing('B'), Extra('B')],
                )
        differences = cm.exception.differences
        self.assertEqual(list(differences), [Extra('B')])


class TestElementAllowance2(unittest.TestCase):
    def setUp(self):
        class allowed_nothing(ElementAllowance2):
            def call_predicate(_self, item):
                return False
        self.allowed_nothing = allowed_nothing

    def test_bitwise_and(self):
        left = self.allowed_nothing()
        right = self.allowed_nothing()
        composed = left & right  # <- Bitwise-and.

        self.assertIsInstance(composed, ElementAllowance2)
        self.assertIsInstance(composed, LogicalAndMixin)
        self.assertIs(composed.left, left)
        self.assertIs(composed.right, right)
        self.assertEqual(composed.msg, '(allowed_nothing <and> allowed_nothing)')
        self.assertEqual(composed.__class__.__name__, 'ComposedElementAllowance')

    def test_bitwise_or(self):
        left = self.allowed_nothing()
        right = self.allowed_nothing()
        composed = left | right  # <- Bitwise-or.

        self.assertIsInstance(composed, ElementAllowance2)
        self.assertIsInstance(composed, LogicalOrMixin)
        self.assertIs(composed.left, left)
        self.assertIs(composed.right, right)
        self.assertEqual(composed.msg, '(allowed_nothing <or> allowed_nothing)')
        self.assertEqual(composed.__class__.__name__, 'ComposedElementAllowance')


class TestAllowedMissing(unittest.TestCase):
    def test_allowed_missing(self):
        differences =  [Missing('X'), Missing('Y'), Extra('X')]

        with self.assertRaises(ValidationError) as cm:
            with allowed_missing():  # <- Apply allowance!
                raise ValidationError('some message', differences)
        remaining_diffs = cm.exception.differences
        self.assertEqual(list(remaining_diffs), [Extra('X')])


class TestAllowedExtra(unittest.TestCase):
    def test_allowed_extra(self):
        differences =  [Extra('X'), Extra('Y'), Missing('X')]

        with self.assertRaises(ValidationError) as cm:
            with allowed_extra():  # <- Apply allowance!
                raise ValidationError('some message', differences)
        remaining_diffs = cm.exception.differences
        self.assertEqual(list(remaining_diffs), [Missing('X')])


class TestAllowedInvalid(unittest.TestCase):
    def test_allowed_invalid(self):
        differences =  [Invalid('X'), Invalid('Y'), Extra('Z')]

        with self.assertRaises(ValidationError) as cm:
            with allowed_invalid():  # <- Apply allowance!
                raise ValidationError('some message', differences)
        remaining_diffs = cm.exception.differences
        self.assertEqual(list(remaining_diffs), [Extra('Z')])


class TestAllowedKey(unittest.TestCase):
    def test_allowed_key(self):
        # Test mapping of differences.
        differences = {'aaa': Missing(1), 'bbb': Missing(2)}
        def function(key):
            return key == 'aaa'

        with self.assertRaises(ValidationError) as cm:
            with allowed_key(function):  # <- Apply allowance!
                raise ValidationError('some message', differences)

        remaining_diffs = cm.exception.differences
        self.assertEqual(dict(remaining_diffs), {'bbb': Missing(2)})

        # Test mapping of differences with composite keys.
        differences = {('a', 7): Missing(1), ('b', 7): Missing(2)}
        def function(letter, number):
            return letter == 'a' and number == 7

        with self.assertRaises(ValidationError) as cm:
            with allowed_key(function):  # <- Apply allowance!
                raise ValidationError('some message', differences)

        remaining_diffs = cm.exception.differences
        self.assertEqual(dict(remaining_diffs), {('b', 7): Missing(2)})

        # Test non-mapping container of differences.
        differences = [Missing(1), Extra(2)]
        def function(key):
            assert key is None  # <- Always Non for non-mapping differences.
            return False  # < Don't match any differences.

        with self.assertRaises(ValidationError) as cm:
            with allowed_key(function):  # <- Apply allowance!
                raise ValidationError('some message', differences)

        remaining_diffs = cm.exception.differences
        self.assertEqual(list(remaining_diffs), [Missing(1), Extra(2)])


class TestAllowedArgs(unittest.TestCase):
    def test_allowed_args(self):
        # Single argument.
        differences =  [Missing('aaa'), Missing('bbb'), Extra('bbb')]
        def function(arg):
            return arg == 'bbb'

        with self.assertRaises(ValidationError) as cm:
            with allowed_args(function):  # <- Apply allowance!
                raise ValidationError('some message', differences)

        remaining_diffs = cm.exception.differences
        self.assertEqual(list(remaining_diffs), [Missing('aaa')])

        # Multiple arguments.
        differences =  [Deviation(+1, 5), Deviation(+2, 5)]
        def function(diff, expected):
            return diff < 2 and expected == 5

        with self.assertRaises(ValidationError) as cm:
            with allowed_args(function):  # <- Apply allowance!
                raise ValidationError('some message', differences)

        remaining_diffs = cm.exception.differences
        self.assertEqual(list(remaining_diffs), [Deviation(+2, 5)])


class TestAllowedDeviation(unittest.TestCase):
    def setUp(self):
        self.differences = {
            'aaa': Deviation(-1, 10),
            'bbb': Deviation(+3, 10),
            'ccc': Deviation(+2, 10),
        }

    def test_function_signature(self):
        with contextlib.suppress(AttributeError):       # Python 3.2 and older
            sig = inspect.signature(allowed_deviation)  # use ugly signatures.
            parameters = list(sig.parameters)
            self.assertEqual(parameters, ['tolerance', 'msg'])

    def test_tolerance_syntax(self):
        with self.assertRaises(ValidationError) as cm:
            with allowed_deviation(2):  # <- Allows +/- 2.
                raise ValidationError('example error', self.differences)
        remaining = cm.exception.differences
        self.assertEqual(remaining, {'bbb': Deviation(+3, 10)})

    def test_lower_upper_syntax(self):
        with self.assertRaises(ValidationError) as cm:
            with allowed_deviation(0, 3):  # <- Allows from 0 to 3.
                raise ValidationError('example error', self.differences)
        result_diffs = cm.exception.differences
        self.assertEqual({'aaa': Deviation(-1, 10)}, result_diffs)

    def test_same_value_case(self):
        with self.assertRaises(ValidationError) as cm:
            with allowed_deviation(3, 3):  # <- Allows off-by-3 only.
                raise ValidationError('example error', self.differences)
        result_diffs = cm.exception.differences
        self.assertEqual({'aaa': Deviation(-1, 10), 'ccc': Deviation(+2, 10)}, result_diffs)

    def test_invalid_tolerance(self):
        with self.assertRaises(AssertionError) as cm:
            with allowed_deviation(-5):  # <- invalid
                pass
        exc = str(cm.exception)
        self.assertTrue(exc.startswith('tolerance should not be negative'))

    def test_empty_string(self):
        with allowed_deviation(0):  # <- Pass without failure.
            raise ValidationError('example error', [Deviation('', 0)])

        with allowed_deviation(0):  # <- Pass without failure.
            raise ValidationError('example error', [Deviation(0, '')])

    def test_NaN_values(self):
        with self.assertRaises(ValidationError):  # <- NaN values should not be caught!
            with allowed_deviation(0):
                raise ValidationError('example error', [Deviation(float('nan'), 0)])

        with self.assertRaises(ValidationError):  # <- NaN values should not be caught!
            with allowed_deviation(0):
                raise ValidationError('example error', [Deviation(0, float('nan'))])


class TestAllowedPercentDeviation(unittest.TestCase):
    def setUp(self):
        self.differences = {
            'aaa': Deviation(-1, 10),
            'bbb': Deviation(+3, 10),
            'ccc': Deviation(+2, 10),
        }

    def test_function_signature(self):
        with contextlib.suppress(AttributeError):       # Python 3.2 and older
            sig = inspect.signature(allowed_percent_deviation)  # use ugly signatures.
            parameters = list(sig.parameters)
            self.assertEqual(parameters, ['tolerance', 'msg'])

    def test_tolerance_syntax(self):
        with self.assertRaises(ValidationError) as cm:
            with allowed_percent_deviation(0.2):  # <- Allows +/- 20%.
                raise ValidationError('example error', self.differences)
        remaining = cm.exception.differences
        self.assertEqual(remaining, {'bbb': Deviation(+3, 10)})

    def test_lower_upper_syntax(self):
        with self.assertRaises(ValidationError) as cm:
            with allowed_percent_deviation(0.0, 0.3):  # <- Allows from 0 to 30%.
                raise ValidationError('example error', self.differences)
        result_diffs = cm.exception.differences
        self.assertEqual({'aaa': Deviation(-1, 10)}, result_diffs)

    def test_same_value_case(self):
        with self.assertRaises(ValidationError) as cm:
            with allowed_percent_deviation(0.3, 0.3):  # <- Allows +30% only.
                raise ValidationError('example error', self.differences)
        result_diffs = cm.exception.differences
        self.assertEqual({'aaa': Deviation(-1, 10), 'ccc': Deviation(+2, 10)}, result_diffs)


class TestBaseAllowance(unittest.TestCase):
    def test_all_filterfalse_good_list(self):
        class AllowEverything(BaseAllowance):
            def group_filterfalse(self, group):
                return []
        base = AllowEverything()
        allowed = base.all_filterfalse([Missing('x')])
        self.assertEqual(list(allowed), [])

        class AllowEverything(BaseAllowance):
            def group_filterfalse(self, group):
                return iter([])  # <- empty iterator
        base = AllowEverything()
        allowed = base.all_filterfalse([Missing('x')])
        self.assertEqual(list(allowed), [])

    def test_all_filterfalse_good_mapping(self):
        """If no errors are returned, the type doesn't matter."""
        in_diffs = {'a': Missing('x')}  # <- Input of mapping differences!

        class AllowEverything(BaseAllowance):
            def group_filterfalse(self, group):
                return dict()  # <- returns dict
        base = AllowEverything()
        allowed = base.all_filterfalse(in_diffs)
        self.assertEqual(list(allowed), [])

        class AllowEverything(BaseAllowance):
            def group_filterfalse(self, group):
                return iter([])  # <- empty iterator
        base = AllowEverything()
        allowed = base.all_filterfalse(in_diffs)
        self.assertEqual(list(allowed), [])

    def test_all_filterfalse_bad_list(self):
        in_diffs = [Missing('foo'), Extra('bar')]

        class ExampleAllowance(BaseAllowance):
            def group_filterfalse(self, group):
                return (x for x in group if not isinstance(x, Extra))

        with self.assertRaises(ValidationError) as cm:
            with ExampleAllowance():
                raise ValidationError('example error', in_diffs)

        differences = cm.exception.differences
        self.assertEqual(list(differences), [Missing('foo')])

    def test_all_filterfalse_bad_mapping(self):
        in_diffs = {'a': Extra('x'), 'b': Missing('y')}

        class ExampleAllowance(BaseAllowance):
            def group_filterfalse(self, group):
                differences = {}
                for key, diff in group:
                    if not isinstance(diff, Extra):
                        differences[key] = diff
                return differences

        with self.assertRaises(ValidationError) as cm:
            with ExampleAllowance():
                raise ValidationError('example error', in_diffs)

        differences = cm.exception.differences
        self.assertEqual(dict(differences), {'b': Missing('y')})

    def test_mismatched_types(self):
        """When given a non-mapping container, a non-mapping container
        should be returned for any remaining differences. Likewise, when
        given a mapping, a mapping should be returned for any remaining
        errors. If the intput and output types are mismatched, a
        TypeError should be raised.
        """
        # List input and dict output.
        list_input =  [Missing('foo'), Missing('bar')]
        class DictOutput(BaseAllowance):
            def group_filterfalse(self, group):
                return {'a': Missing('foo')}  # <- dict type

        with self.assertRaises(TypeError):
            with DictOutput():
                raise ValidationError('example error', list_input)

        # Dict input and list output.
        dict_input =  {'a': Missing('foo'), 'b': Missing('bar')}
        class ListOutput(BaseAllowance):
            def group_filterfalse(self, group):
                return [Missing('foo')]  # <- list type

        with self.assertRaises(TypeError):
            with ListOutput():
                raise ValidationError('example error', dict_input)

        # Dict input and list-item output.
        dict_input =  {'a': Missing('foo'), 'b': Missing('bar')}
        class ItemOutput(BaseAllowance):
            def group_filterfalse(self, group):
                return [('a', Missing('foo'))]  # <- list of items

        with self.assertRaises(ValidationError) as cm:
            with ItemOutput():
                raise ValidationError('example error', dict_input)

        differences = cm.exception.differences
        #self.assertIsInstance(differences, DictItems)
        self.assertEqual(dict(differences), {'a': Missing('foo')})

    def test_error_message(self):
        error = ValidationError('original message', [Missing('foo')])

        class AllowedNothing(BaseAllowance):
            def group_filterfalse(self, group):
                return group

        # No message.
        with self.assertRaises(ValidationError) as cm:
            with AllowedNothing():  # <- No 'msg' keyword!
                raise error
        message = cm.exception.message
        self.assertEqual(message, 'original message')

        # Test allowance message.
        with self.assertRaises(ValidationError) as cm:
            with AllowedNothing('allowance message'):  # <- Provides 'msg'.
                raise error
        message = cm.exception.message
        self.assertEqual(message, 'allowance message: original message')

        # Test allowance message.
        with self.assertRaises(ValidationError) as cm:
            with AllowedNothing(msg='allowance message'):  # <- Uses keyword.
                raise error
        message = cm.exception.message
        self.assertEqual(message, 'allowance message: original message')

    def test_propagation_of_maxdiff(self):
        """Check that re-raised errors inherit the original error's maxDiff."""
        parent = ValidationError('original message', [Missing('foo')])
        parent._should_truncate = lambda line_count, char_count: char_count > 35
        parent._truncation_notice = 'Message truncated.'

        class AllowedNothing(BaseAllowance):
            def group_filterfalse(self, group):
                return group

        with self.assertRaises(ValidationError) as cm:
            with AllowedNothing(msg='allowance message'):  # <- Uses keyword.
                raise parent
        child = cm.exception
        self.assertEqual(child._should_truncate, parent._should_truncate)
        self.assertEqual(child._truncation_notice, parent._truncation_notice)


class TestElementAllowanceFilterFalse(unittest.TestCase):
    def test_mapping_of_nongroups(self):
        iterable = {
            'a': Missing(1),
            'b': Extra(2),
            'c': Invalid(3),
        }
        def predicate(key, value):
            return (key == 'b') or isinstance(value, Invalid)

        elementwise = ElementAllowance(predicate)
        result = elementwise.all_filterfalse(iterable)
        self.assertEqual(dict(result), {'a':  Missing(1)})

    def test_mapping_of_groups(self):
        """Key/value pairs should be passed to predicate for
        every element of an iterable group.
        """
        iterable = {
            'x': [
                Missing(1),
                Invalid(2),  # <- Matches predicate.
                Missing(3),
                Extra(4),    # <- Matches predicate.
            ],
            'y': [
                Missing(5),
                Extra(6),    # <- Matches predicate.
                Invalid(7),
            ],
            'z': [
                Extra(8),    # <- Matches predicate.
            ],
        }

        def predicate(key, value):
            if key == 'x' and isinstance(value, Invalid):
                return True
            if isinstance(value, Extra):
                return True
            return False

        elementwise = ElementAllowance(predicate)
        result = elementwise.all_filterfalse(iterable)
        expected = {'x': [Missing(1), Missing(3)],
                    'y': [Missing(5), Invalid(7)]}
        self.assertEqual(dict(result), expected)

    def test_nonmapping(self):
        iterable = [Extra(1), Missing(2), Invalid(3)]

        def predicate(key, value):
            assert key is None  # <- For non-mapping, key is always None.
            return isinstance(value, Missing)

        elementwise = ElementAllowance(predicate)
        result = elementwise.all_filterfalse(iterable)
        self.assertEqual(list(result), [Extra(1), Invalid(3)])


class TestElementAllowanceAndSubclasses(unittest.TestCase):
    def test_ElementAllowance(self):
        # Test mapping of differences.
        differences = {'a': Missing(1), 'b': Missing(2)}
        def function(key, error):
            return key == 'b' and isinstance(error, Missing)

        with self.assertRaises(ValidationError) as cm:
            with ElementAllowance(function):  # <- Apply allowance!
                raise ValidationError('some message', differences)

        remaining_diffs = cm.exception.differences
        self.assertEqual(dict(remaining_diffs), {'a': Missing(1)})

        # Test non-mapping container of differences.
        differences = [Missing(1), Extra(2)]
        def function(key, error):
            assert key is None  # None when differences are non-mapping.
            return isinstance(error, Missing)

        with self.assertRaises(ValidationError) as cm:
            with ElementAllowance(function):  # <- Apply allowance!
                raise ValidationError('some message', differences)

        remaining_diffs = cm.exception.differences
        self.assertEqual(list(remaining_diffs), [Extra(2)])


class TestComposability(unittest.TestCase):
    """Most allowances should support being combined using the
    "&" and "|" (bitwise-and and bitwise-or operators).
    """
    @unittest.skip('refactoring')
    def test_or_operator(self):
        differences =  [Extra('X'), Missing('Y'), Invalid('Z')]
        with self.assertRaises(ValidationError) as cm:
            with allowed_extra() | allowed_missing():  # <- Compose with "|"!
                raise ValidationError('some message', differences)
        remaining_diffs = cm.exception.differences
        self.assertEqual(list(remaining_diffs), [Invalid('Z')])

    @unittest.skip('refactoring')
    def test_and_operator(self):
        differences =  [Missing('X'), Extra('Y'), Missing('Z')]
        with self.assertRaises(ValidationError) as cm:
            is_x = lambda arg: arg == 'X'
            with allowed_missing() & allowed_args(is_x):  # <- Compose with "&"!
                raise ValidationError('some message', differences)
        remaining_diffs = cm.exception.differences
        self.assertEqual(list(remaining_diffs), [Extra('Y'), Missing('Z')])


class TestAllowedSpecific(unittest.TestCase):
    def test_some_allowed(self):
        differences = [Extra('xxx'), Missing('yyy')]
        allowed = [Extra('xxx')]

        with self.assertRaises(ValidationError) as cm:
            with allowed_specific(allowed):
                raise ValidationError('example error', differences)

        expected = [Missing('yyy')]
        actual = list(cm.exception.differences)
        self.assertEqual(expected, actual)

    def test_single_diff_without_container(self):
        differences = [Extra('xxx'), Missing('yyy')]
        allowed = Extra('xxx')  # <- Single diff, not in list.

        with self.assertRaises(ValidationError) as cm:
            with allowed_specific(allowed):
                raise ValidationError('example error', differences)

        expected = [Missing('yyy')]
        actual = list(cm.exception.differences)
        self.assertEqual(expected, actual)

    def test_all_allowed(self):
        diffs = [Extra('xxx'), Missing('yyy')]
        allowed = [Extra('xxx'), Missing('yyy')]
        with allowed_specific(allowed):
            raise ValidationError('example error', diffs)

    def test_excess_allowed(self):
        diffs = [Extra('xxx')]
        allowed = [Extra('xxx'), Missing('yyy'), Invalid('zzz', 'ZZZ')]
        with allowed_specific(allowed):
            raise ValidationError('example error', diffs)

    def test_duplicates(self):
        # Three of the exact-same differences.
        differences = [Extra('xxx'), Extra('xxx'), Extra('xxx')]

        # Only allow one of them.
        with self.assertRaises(ValidationError) as cm:
            allowed = [Extra('xxx')]
            with allowed_specific(allowed):
                raise ValidationError('example error', differences)

        expected = [Extra('xxx'), Extra('xxx')]  # Expect two remaining.
        actual = list(cm.exception.differences)
        self.assertEqual(expected, actual)

        # Only allow two of them.
        with self.assertRaises(ValidationError) as cm:
            allowed = [Extra('xxx'), Extra('xxx')]
            with allowed_specific(allowed):
                raise ValidationError('example error', differences)

        expected = [Extra('xxx')]  # Expect one remaining.
        actual = list(cm.exception.differences)
        self.assertEqual(expected, actual)

        # Allow all three.
        allowed = [Extra('xxx'), Extra('xxx'), Extra('xxx')]
        with allowed_specific(allowed):
            raise ValidationError('example error', differences)

    def test_error_mapping_allowance_list(self):
        differences = {'foo': [Extra('xxx')], 'bar': [Extra('xxx'), Missing('yyy')]}
        allowed = [Extra('xxx')]

        with self.assertRaises(ValidationError) as cm:
            with allowed_specific(allowed):
                raise ValidationError('example error', differences)

        expected = {'bar': [Missing('yyy')]}
        actual = cm.exception.differences
        self.assertEqual(expected, actual)

    def test_mapping_some_allowed(self):
        differences = {'foo': Extra('xxx'), 'bar': Missing('yyy')}
        allowed = {'foo': Extra('xxx')}

        with self.assertRaises(ValidationError) as cm:
            with allowed_specific(allowed):
                raise ValidationError('example error', differences)

        expected = {'bar': Missing('yyy')}
        actual = cm.exception.differences
        self.assertEqual(expected, actual)

    def test_mapping_none_allowed(self):
        differences = {'foo': Extra('xxx'), 'bar': Missing('yyy')}
        allowed = {}

        with self.assertRaises(ValidationError) as cm:
            with allowed_specific(allowed):
                raise ValidationError('example error', differences)

        actual = cm.exception.differences
        self.assertEqual(differences, actual)

    def test_mapping_all_allowed(self):
        differences = {'foo': Extra('xxx'), 'bar': Missing('yyy')}
        allowed = differences

        with allowed_specific(allowed):  # <- Catches all differences, no error!
            raise ValidationError('example error', differences)

    def test_mapping_mismatched_types(self):
        diff_list = [Extra('xxx'), Missing('yyy')]
        allowed_dict = {'foo': Extra('xxx'), 'bar': Missing('yyy')}

        regex = "'list' of differences cannot be matched.*requires non-mapping container"

        with self.assertRaisesRegex(ValueError, regex):
            with allowed_specific(allowed_dict):
                raise ValidationError('example error', diff_list)

    def test_integration(self):
        """This is a bit of an integration test."""
        differences = {
            'foo': [Extra('xxx'), Missing('yyy')],
            'bar': [Extra('xxx')],
            'baz': [Extra('xxx'), Missing('yyy'), Extra('zzz')],
        }
        allowed = [Extra('xxx'), Missing('yyy')]
        with self.assertRaises(ValidationError) as cm:
            with allowed_specific(allowed):
                raise ValidationError('example error', differences)

        actual = cm.exception.differences
        self.assertEqual(actual, {'baz': [Extra('zzz')]})

    def test_composition_bitwise_or(self):
        # One shared element.
        allowed1 = [Extra('xxx'), Missing('yyy')]
        allowed2 = [Missing('yyy'), Invalid('zzz')]
        specific = allowed_specific(allowed1) | allowed_specific(allowed2)
        self.assertEqual(specific.differences, [Extra('xxx'), Missing('yyy'), Invalid('zzz')])

        # Duplicate shared element.
        allowed1 = [Extra('xxx'), Extra('xxx')]
        allowed2 = [Missing('yyy'), Extra('xxx')]
        specific = allowed_specific(allowed1) | allowed_specific(allowed2)
        self.assertEqual(specific.differences, [Extra('xxx'), Extra('xxx'), Missing('yyy')])

        # Mismatched types (list and dict)
        allowed1 = [Extra('xxx'), Missing('yyy')]
        allowed2 = {'a': Missing('yyy'), 'b': Extra('zzz')}
        regex = r"cannot combine .* 'list' and 'dict'"
        with self.assertRaisesRegex(ValueError, regex):
            allowed_specific(allowed1) | allowed_specific(allowed2)

        # Mapping with one shared element.
        allowed1 = {'a': [Extra('xxx'), Missing('yyy')]}
        allowed2 = {'a': [Missing('yyy'), Invalid('zzz')]}
        specific = allowed_specific(allowed1) | allowed_specific(allowed2)
        self.assertEqual(
            specific.differences,
            {'a': [Extra('xxx'), Missing('yyy'), Invalid('zzz')]},
        )

        # Mapping mismatched keys.
        allowed1 = {'a': [Extra('xxx'), Missing('yyy')]}
        allowed2 = {'b': [Missing('yyy'), Invalid('zzz')]}
        specific = allowed_specific(allowed1) | allowed_specific(allowed2)
        self.assertEqual(
            specific.differences,
            {'a': [Extra('xxx'), Missing('yyy')],
             'b': [Missing('yyy'), Invalid('zzz')]}
        )

        # Mapping with unwrapped differences.
        allowed1 = {'a': Extra('xxx'),    # <- Not wrapped in container.
                    'b': Missing('yyy')}  # <- Not wrapped in container.
        allowed2 = {'a': Extra('xxx'),    # <- Not wrapped in container.
                    'b': [Missing('yyy'), Invalid('zzz')]}
        specific = allowed_specific(allowed1) | allowed_specific(allowed2)
        self.assertEqual(
            specific.differences,
            {'a': [Extra('xxx')],  # <- Output is wrapped in list.
             'b': [Missing('yyy'), Invalid('zzz')]}
        )

    def test_composition_bitwise_and(self):
        allowed1 = [Extra('xxx'), Missing('yyy')]
        allowed2 = [Missing('yyy'), Invalid('zzz')]
        specific = allowed_specific(allowed1) & allowed_specific(allowed2)
        self.assertEqual(specific.differences, [Missing('yyy')])

        allowed1 = [Extra('xxx'), Extra('xxx'), Missing('yyy')]
        allowed2 = [Missing('yyy'), Extra('xxx'), Invalid('zzz'), Extra('xxx')]
        specific = allowed_specific(allowed1) & allowed_specific(allowed2)
        self.assertEqual(specific.differences, [Extra('xxx'), Extra('xxx'), Missing('yyy')])

        # Mismatched types (list and dict)
        allowed1 = [Extra('xxx'), Missing('yyy')]
        allowed2 = {'a': Missing('yyy'), 'b': Extra('zzz')}
        regex = r"cannot combine .* 'list' and 'dict'"
        with self.assertRaisesRegex(ValueError, regex):
            allowed_specific(allowed1) & allowed_specific(allowed2)

        # Mapping with one shared element.
        allowed1 = {'a': [Extra('xxx'), Missing('yyy')]}
        allowed2 = {'a': [Missing('yyy'), Invalid('zzz')]}
        specific = allowed_specific(allowed1) & allowed_specific(allowed2)
        self.assertEqual(specific.differences, {'a': [Missing('yyy')]})

        # Mapping mismatched keys.
        allowed1 = {'a': [Extra('xxx')]}
        allowed2 = {'b': [Extra('xxx')]}
        specific = allowed_specific(allowed1) & allowed_specific(allowed2)
        self.assertEqual(specific.differences, {})

        # Mapping mismatched values.
        allowed1 = {'a': [Extra('xxx')]}
        allowed2 = {'a': [Missing('yyy')]}
        specific = allowed_specific(allowed1) & allowed_specific(allowed2)
        self.assertEqual(specific.differences, {})

        # Mapping with unwrapped differences.
        allowed1 = {'a': Extra('xxx'),    # <- Not in container.
                    'b': Missing('yyy')}  # <- Not in container.
        allowed2 = {'a': Extra('xxx'),    # <- Not in container.
                    'b': [Missing('yyy'), Invalid('zzz')]}
        specific = allowed_specific(allowed1) & allowed_specific(allowed2)
        self.assertEqual(specific.differences,
                         {'a': [Extra('xxx')], 'b': [Missing('yyy')]})


class TestAllowedLimit(unittest.TestCase):
    """Test allowed_limit() behavior."""
    def test_exceeds_limit(self):
        differences = [Extra('xxx'), Missing('yyy')]
        with self.assertRaises(ValidationError) as cm:
            with allowed_limit(1):  # <- Allows only 1 but there are 2!
                raise ValidationError('example error', differences)

        remaining = list(cm.exception.differences)
        self.assertEqual(remaining, differences)

    def test_matches_limit(self):
        differences = [Extra('xxx'), Missing('yyy')]
        with allowed_limit(2):  # <- Allows 2 and there are only 2.
            raise ValidationError('example error', differences)

    def test_under_limit(self):
        differences = [Extra('xxx'), Missing('yyy')]
        with allowed_limit(3):  # <- Allows 3 and there are only 2.
            raise ValidationError('example error', differences)

    def test_dict_of_diffs_exceeds_and_match(self):
        differences = {
            'foo': [Extra('xxx'), Missing('yyy')],
            'bar': [Extra('zzz')],
        }
        with self.assertRaises(ValidationError) as cm:
            with allowed_limit(1):  # <- Allows only 1 but there are 2!
                raise ValidationError('example error', differences)

        actual = cm.exception.differences
        expected = {'foo': [Extra('xxx'), Missing('yyy')]}
        self.assertEqual(dict(actual), expected)

    @unittest.skip('refactoring')
    def test_bitwise_or_composition_under_limit(self):
        differences = [
            Extra('aaa'),
            Extra('bbb'),
            Missing('ccc'),
            Missing('ddd'),
            Missing('eee'),
        ]
        with allowed_limit(2) | allowed_missing():  # <- Limit of 2 or Missing.
            raise ValidationError('example error', differences)

    @unittest.skip('refactoring')
    def test_bitwise_ror(self):
        """The right-side-or/__ror__ should be wired up to __or__."""
        differences = [
            Extra('aaa'),
            Extra('bbb'),
            Missing('ccc'),
            Missing('ddd'),
            Missing('eee'),
        ]
        with allowed_missing() | allowed_limit(2):  # <- On right-hand side!
            raise ValidationError('example error', differences)

    @unittest.skip('refactoring')
    def test_bitwise_or_composition_over_limit(self):
        differences = [
            Extra('aaa'),
            Extra('bbb'),
            Extra('ccc'),
            Missing('ddd'),
            Missing('eee'),
        ]
        with self.assertRaises(ValidationError) as cm:
            with allowed_limit(2) | allowed_missing():
                raise ValidationError('example error', differences)

        # Returned differences *may* not be in the same order.
        actual = list(cm.exception.differences)
        self.assertEqual(actual, differences)

        # Test __ror__().
        with self.assertRaises(ValidationError) as cm:
            with allowed_missing() | allowed_limit(2):  # <- On right-hand side!
                raise ValidationError('example error', differences)

        # Returned differences *may* not be in the same order.
        actual = list(cm.exception.differences)
        self.assertEqual(actual, differences)

    @unittest.skip('refactoring')
    def test_bitwise_and_composition_under_limit(self):
        differences = [Extra('xxx'), Missing('yyy'), Extra('zzz')]

        with self.assertRaises(ValidationError) as cm:
            is_extra = lambda x: isinstance(x, Extra)
            with allowed_limit(4) & allowed_extra():
                raise ValidationError('example error', differences)

        actual = list(cm.exception.differences)
        self.assertEqual(actual, [Missing('yyy')])

    @unittest.skip('refactoring')
    def test_bitwise_rand(self):
        """The right-side-and/__rand__ should be wired up to __and__."""
        differences = [Extra('xxx'), Missing('yyy'), Extra('zzz')]

        # Make sure __rand__ (right-and) is wired-up to __and__.
        with self.assertRaises(ValidationError) as cm:
            is_extra = lambda x: isinstance(x, Extra)
            with allowed_extra() & allowed_limit(4):  # <- On right-hand side!
                raise ValidationError('example error', differences)

        actual = list(cm.exception.differences)
        self.assertEqual(actual, [Missing('yyy')])

    @unittest.skip('refactoring')
    def test_bitwise_and_composition_over_limit(self):
        differences = [Extra('xxx'), Missing('yyy'), Extra('zzz')]
        with self.assertRaises(ValidationError) as cm:
            is_extra = lambda x: isinstance(x, Extra)
            with allowed_limit(1) & allowed_extra():  # <- Limit of 1 and is_extra().
                raise ValidationError('example error', differences)

        # Returned errors can be in different order.
        actual = list(cm.exception.differences)
        expected = [Missing('yyy'), Extra('xxx'), Extra('zzz')]
        self.assertEqual(actual, expected)

    @unittest.skip('refactoring')
    def test_bitwise_and_composition_with_dict(self):
        differences = {
            'foo': [Extra('aaa'), Missing('bbb')],
            'bar': [Extra('ccc')],
            'baz': [Extra('ddd'), Extra('eee')],
        }
        with self.assertRaises(ValidationError) as cm:
            is_extra = lambda x: isinstance(x, Extra)
            with allowed_limit(1) & allowed_extra():
                raise ValidationError('example error', differences)

        actual = cm.exception.differences
        expected = {
            'foo': [Missing('bbb')],              # <- Missing not allowed at all.
            'baz': [Extra('ddd'), Extra('eee')],  # <- Returns everything when over limit.
        }
        self.assertEqual(dict(actual), expected)


@unittest.skip('Prerequisite refactoring still in progress.')
class TestUniversalComposability(unittest.TestCase):
    """Test that allowances are composable with allowances of the
    same type as well as all other allowance types.
    """
    def setUp(self):
        """Build pairs representing all possible combinations of
        allowance types.
        """
        allow1 = [
            allowed_missing(),
            allowed_extra(),
            allowed_invalid(),
            allowed_deviation(5),
            allowed_percent_deviation(0.05),
            allowed_specific([Invalid('A')]),
            allowed_key(lambda *args: True),
            allowed_args(lambda *args: True),
            allowed_limit(3),
        ]
        allow2 = [                             # Define a second list
            allowed_missing(),                 # of allowances so we
            allowed_extra(),                   # have two lists with
            allowed_invalid(),                 # unique instances (not
            allowed_deviation(5),              # just two lists of
            allowed_percent_deviation(0.05),   # pointers to the same
            allowed_specific([Invalid('A')]),  # set of objects).
            allowed_key(lambda *args: True),
            allowed_args(lambda *args: True),
            allowed_limit(3),
        ]
        # Make sure all of the allowances are unique instances.
        for a, b in zip(allow1, allow2):
            assert a is not b, 'must be different instances'

        combinations = itertools.product(allow1, allow2)
        self.combinations = list(combinations)

    def test_bitwise_or(self):
        for a, b in self.combinations:
            combined = a | b  # Compose using "bitwise or".
            self.assertIsInstance(combined, BaseAllowance)

    def test_bitwise_and(self):
        for a, b in self.combinations:
            combined = a & b  # Compose using "bitwise and".
            self.assertIsInstance(combined, BaseAllowance)


class TestMsgIntegration(unittest.TestCase):
    """The 'msg' keyword is passed to to each parent class and
    eventually handled in the allow_iter base class. These tests
    do some sanity checking to make sure that 'msg' values are
    passed through the inheritance chain.
    """
    def test_allowed_missing(self):
        # Check for modified message.
        with self.assertRaises(ValidationError) as cm:
            with allowed_missing(msg='modified'):  # <- No msg!
                raise ValidationError('original', [Extra('X')])
        message = cm.exception.message
        self.assertEqual(message, 'modified: original')
