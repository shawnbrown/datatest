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
from datatest.allowance import GroupAllowance
from datatest.allowance import CollectionAllowance
from datatest.allowance import allowed_missing
from datatest.allowance import allowed_extra
from datatest.allowance import allowed_invalid
from datatest.allowance import allowed_key
from datatest.allowance import allowed_args
from datatest.allowance import allowed_deviation
from datatest.allowance import allowed_percent_deviation
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


class TestGroupAllowance(unittest.TestCase):
    def setUp(self):
        class group_allowance(GroupAllowance):
            def call_predicate(_self, item):
                return False
        self.group_allowance = group_allowance

        class element_allowance(ElementAllowance2):
            def call_predicate(_self, item):
                return False
        self.element_allowance = element_allowance

    def test_bitwise_and(self):
        group_allowance1 = self.group_allowance()
        group_allowance2 = self.group_allowance()
        element_allowance = self.element_allowance()

        composed = group_allowance1 & group_allowance2
        self.assertIsInstance(composed, GroupAllowance)
        self.assertIsInstance(composed, LogicalAndMixin)
        self.assertIs(composed.left, group_allowance1)
        self.assertIs(composed.right, group_allowance2)
        self.assertEqual(composed.__class__.__name__, 'ComposedGroupAllowance')

        # Check group-and-element composition.
        composed = group_allowance1 & element_allowance  # <- Group starts on left.
        self.assertIsInstance(composed, GroupAllowance)
        self.assertIs(composed.left, element_allowance)
        self.assertIs(composed.right, group_allowance1)  # <- Moves to right side.

        # Check __rand__() handling.
        composed = element_allowance & group_allowance1  # <- Group starts on right.
        self.assertIsInstance(composed, GroupAllowance)
        self.assertIs(composed.left, element_allowance)
        self.assertIs(composed.right, group_allowance1)  # <- Stays on right side.

    def test_bitwise_or(self):
        group_allowance1 = self.group_allowance()
        group_allowance2 = self.group_allowance()
        element_allowance = self.element_allowance()

        composed = group_allowance1 | group_allowance2
        self.assertIsInstance(composed, GroupAllowance)
        self.assertIsInstance(composed, LogicalOrMixin)
        self.assertIs(composed.left, group_allowance1)
        self.assertIs(composed.right, group_allowance2)
        self.assertEqual(composed.__class__.__name__, 'ComposedGroupAllowance')

        # Check group-or-element composition.
        composed = group_allowance1 | element_allowance  # <- Group starts on left.
        self.assertIsInstance(composed, GroupAllowance)
        self.assertIs(composed.left, element_allowance)
        self.assertIs(composed.right, group_allowance1)  # <- Moves to right side.

        # Check __ror__() handling.
        composed = element_allowance | group_allowance1  # <- Group starts on right.
        self.assertIsInstance(composed, GroupAllowance)
        self.assertIs(composed.left, element_allowance)
        self.assertIs(composed.right, group_allowance1)  # <- Stays on right side.


class TestCollectionAllowance(unittest.TestCase):
    def setUp(self):
        class collection_allowance(CollectionAllowance):
            def call_predicate(_self, item):
                return False
        self.collection_allowance = collection_allowance

        class group_allowance(GroupAllowance):
            def call_predicate(_self, item):
                return False
        self.group_allowance = group_allowance

        class element_allowance(ElementAllowance2):
            def call_predicate(_self, item):
                return False
        self.element_allowance = element_allowance

    def test_bitwise_and(self):
        collection_allowance1 = self.collection_allowance()
        collection_allowance2 = self.collection_allowance()
        group_allowance = self.group_allowance()
        element_allowance = self.element_allowance()

        composed = collection_allowance1 & collection_allowance2
        self.assertIsInstance(composed, CollectionAllowance)
        self.assertIsInstance(composed, LogicalAndMixin)
        self.assertIs(composed.left, collection_allowance1)
        self.assertIs(composed.right, collection_allowance2)
        self.assertEqual(composed.__class__.__name__, 'ComposedCollectionAllowance')

        # Check collection-and-group composition.
        composed = collection_allowance1 & group_allowance  # <- Collection starts on left.
        self.assertIsInstance(composed, CollectionAllowance)
        self.assertIs(composed.left, group_allowance)
        self.assertIs(composed.right, collection_allowance1)  # <- Moves to right side.

        # Check __rand__() handling (using collection-and-element).
        composed = element_allowance & collection_allowance1  # <- Collection starts on right.
        self.assertIsInstance(composed, CollectionAllowance)
        self.assertIs(composed.left, element_allowance)
        self.assertIs(composed.right, collection_allowance1)  # <- Stays on right side.

    def test_bitwise_or(self):
        collection_allowance1 = self.collection_allowance()
        collection_allowance2 = self.collection_allowance()
        group_allowance = self.group_allowance()
        element_allowance = self.element_allowance()

        composed = collection_allowance1 | collection_allowance2
        self.assertIsInstance(composed, CollectionAllowance)
        self.assertIsInstance(composed, LogicalOrMixin)
        self.assertIs(composed.left, collection_allowance1)
        self.assertIs(composed.right, collection_allowance2)
        self.assertEqual(composed.__class__.__name__, 'ComposedCollectionAllowance')

        # Check collection-or-group composition.
        composed = collection_allowance1 | group_allowance  # <- Collection starts on left.
        self.assertIsInstance(composed, CollectionAllowance)
        self.assertIs(composed.left, group_allowance)
        self.assertIs(composed.right, collection_allowance1)  # <- Moves to right side.

        # Check __rand__() handling (using collection-or-element).
        composed = element_allowance | collection_allowance1  # <- Collection starts on right.
        self.assertIsInstance(composed, CollectionAllowance)
        self.assertIs(composed.left, element_allowance)
        self.assertIs(composed.right, collection_allowance1)  # <- Stays on right side.


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


class TestAllowedSpecific(unittest.TestCase):
    def test_list_containers(self):
        allowed = [Extra('xxx')]

        with self.assertRaises(ValidationError) as cm:
            with allowed_specific(allowed):
                raise ValidationError('example error',
                                      [Extra('xxx'), Missing('yyy')])

        actual = list(cm.exception.differences)
        expected = [Missing('yyy')]
        self.assertEqual(actual, expected)

    def test_diff_without_container(self):
        differences = [Extra('xxx'), Missing('yyy')]
        allowed = Extra('xxx')  # <- Single diff, not in a container.

        with self.assertRaises(ValidationError) as cm:
            with allowed_specific(allowed):
                raise ValidationError('example error', differences)

        actual = list(cm.exception.differences)
        expected = [Missing('yyy')]
        self.assertEqual(actual, expected)

    def test_excess_allowed(self):
        diffs = [Extra('xxx')]
        allowed = [Extra('xxx'), Missing('yyy')]  # <- More allowed than
        with allowed_specific(allowed):           #    are actually found.
            raise ValidationError('example error', diffs)

    def test_duplicates(self):
        # Three of the exact-same differences.
        differences = [Extra('xxx'), Extra('xxx'), Extra('xxx')]

        # Only allow one of them.
        with self.assertRaises(ValidationError) as cm:
            allowed = [Extra('xxx')]
            with allowed_specific(allowed):
                raise ValidationError('example error', differences)

        actual = list(cm.exception.differences)
        expected = [Extra('xxx'), Extra('xxx')]  # Expect two remaining.
        self.assertEqual(actual, expected)

        # Only allow two of them.
        with self.assertRaises(ValidationError) as cm:
            allowed = [Extra('xxx'), Extra('xxx')]
            with allowed_specific(allowed):
                raise ValidationError('example error', differences)

        actual = list(cm.exception.differences)
        expected = [Extra('xxx')]  # Expect one remaining.
        self.assertEqual(actual, expected)

        # Allow all three.
        allowed = [Extra('xxx'), Extra('xxx'), Extra('xxx')]
        with allowed_specific(allowed):
            raise ValidationError('example error', differences)

    def test_mapping_of_differences(self):
        differences = {'foo': Extra('xxx'), 'bar': [Extra('xxx'), Missing('yyy')]}
        allowed = [Extra('xxx')]

        with self.assertRaises(ValidationError) as cm:
            with allowed_specific(allowed):
                raise ValidationError('example error', differences)

        actual = cm.exception.differences
        expected = {'bar': Missing('yyy')}
        self.assertEqual(actual, expected)

    def test_mapping_of_differences_and_allowances(self):
        differences = {'foo': Extra('xxx'), 'bar': [Extra('xxx'), Missing('yyy')]}
        allowed = {'bar': Extra('xxx')}

        with self.assertRaises(ValidationError) as cm:
            with allowed_specific(allowed):
                raise ValidationError('example error', differences)

        actual = cm.exception.differences
        expected = {'foo': Extra('xxx'), 'bar': Missing('yyy')}
        self.assertEqual(actual, expected)

    def test_all_allowed(self):
        differences = {'foo': Extra('xxx'), 'bar': Missing('yyy')}
        allowed = {'foo': Extra('xxx'), 'bar': Missing('yyy')}

        with allowed_specific(allowed):  # <- Allows all differences, no error!
            raise ValidationError('example error', differences)

    def test_combination_of_cases(self):
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
        self.assertEqual(actual, {'baz': Extra('zzz')})


class TestAllowedLimit(unittest.TestCase):
    def test_under_limit(self):
        with allowed_limit(3):  # <- Allows 3 and there are only 2.
            raise ValidationError('example error',
                                  [Extra('xxx'), Missing('yyy')])

        with allowed_limit(3):  # <- Allows 3 and there are only 2.
            raise ValidationError('example error',
                                  {'foo': Extra('xxx'), 'bar': Missing('yyy')})

    def test_at_limit(self):
        with allowed_limit(2):  # <- Allows 2 and there are 2.
            raise ValidationError('example error',
                                  [Extra('xxx'), Missing('yyy')])

        with allowed_limit(3):  # <- Allows 2 and there are 2.
            raise ValidationError('example error',
                                  {'foo': Extra('xxx'), 'bar': Missing('yyy')})

    def test_over_limit(self):
        with self.assertRaises(ValidationError) as cm:
            with allowed_limit(1):  # <- Allows 1 but there are 2.
                raise ValidationError('example error',
                                      [Extra('xxx'), Missing('yyy')])

        remaining = list(cm.exception.differences)
        self.assertEqual(remaining, [Missing('yyy')])

        with self.assertRaises(ValidationError) as cm:
            with allowed_limit(1):  # <- Allows 1 and there are 2.
                raise ValidationError('example error',
                                      {'foo': Extra('xxx'), 'bar': Missing('yyy')})

        remaining = cm.exception.differences
        self.assertIsInstance(remaining, collections.Mapping)
        self.assertEqual(len(remaining), 1)


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
            self.assertIsInstance(combined, BaseAllowance2)

    def test_bitwise_and(self):
        for a, b in self.combinations:
            combined = a & b  # Compose using "bitwise and".
            self.assertIsInstance(combined, BaseAllowance2)


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
