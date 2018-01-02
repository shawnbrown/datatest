# -*- coding: utf-8 -*-
import inspect
import sys
from . import _unittest as unittest
from datatest.utils.builtins import *
from datatest.utils import collections
from datatest.utils import contextlib
from datatest.utils import itertools

from datatest.allowance import BaseAllowance
from datatest.allowance import CombinedAllowance
from datatest.allowance import IntersectedAllowance
from datatest.allowance import UnionedAllowance
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


class MinimalAllowance(BaseAllowance):  # A minimal subclass for
    def call_predicate(self, item):     # testing--defines three
        return False                    # concrete stubs to satisfy
                                        # abstract method requirement
    def __repr__(self):                 # of the base class.
        return super(MinimalAllowance, self).__repr__()


class TestBaseAllowance(unittest.TestCase):
    def test_default_priority(self):
        class allowed_nothing(MinimalAllowance):
            def call_predicate(_self, item):
                return False

        allowance = allowed_nothing()
        self.assertEqual(allowance.priority, 1)

    def test_preserve_priority(self):
        # Calling the superclass' __init__() should not overwrite
        # the `priority` attribute if it has been previously set by
        # a subclass.
        class allowed_nothing(MinimalAllowance):
            def __init__(_self, msg=None):
                _self.priority = 2
                super(allowed_nothing, _self).__init__(msg)

            def call_predicate(_self, item):
                return False

        allowance = allowed_nothing()
        self.assertEqual(allowance.priority, 2, 'should not overwrite existing `priority`')

    def test_serialized_items(self):
        item_list = [1, 2]
        actual = BaseAllowance._serialized_items(item_list)
        expected = [(None, 1), (None, 2)]
        self.assertEqual(list(actual), expected, 'serialize list of elements')

        item_dict = {'A': 'x', 'B': 'y'}
        actual = BaseAllowance._serialized_items(item_dict)
        expected = [('A', 'x'), ('B', 'y')]
        self.assertEqual(sorted(actual), expected, 'serialize mapping of elements')

        item_dict = {'A': ['x', 'y'], 'B': ['x', 'y']}
        actual = BaseAllowance._serialized_items(item_dict)
        expected = [('A', 'x'), ('A', 'y'), ('B', 'x'), ('B', 'y')]
        self.assertEqual(sorted(actual), expected, 'serialize mapping of lists')

    def test_deserialized_items(self):
        stream = [(None, 1), (None, 2)]
        actual = BaseAllowance._deserialized_items(stream)
        expected = {None: [1, 2]}
        self.assertEqual(actual, expected)

        stream = [('A', 'x'), ('B', 'y')]
        actual = BaseAllowance._deserialized_items(stream)
        expected = {'A': 'x', 'B': 'y'}
        self.assertEqual(actual, expected)

        stream = [('A', 'x'), ('A', 'y'), ('B', 'x'), ('B', 'y')]
        actual = BaseAllowance._deserialized_items(stream)
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
            raise ValidationError('error message', [Missing('A'), Extra('B')])
        except ValidationError:
            type, value, traceback = sys.exc_info()  # Get exception info.

        with self.assertRaises(ValidationError) as cm:
            allowance = MinimalAllowance('allowance message')
            allowance.__exit__(type, value, traceback)

        message = cm.exception.message
        self.assertEqual(message, 'allowance message: error message')


class TestAllowanceProtocol(unittest.TestCase):
    def setUp(self):
        class LoggingAllowance(MinimalAllowance):
            def __init__(_self, msg=None):
                _self.log = []
                super(LoggingAllowance, _self).__init__(msg)

            def __repr__(self):
                return super(LoggingAllowance, _self).__repr__()

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


class TestLogicalComposition(unittest.TestCase):
    def setUp(self):
        class allowed_missing(MinimalAllowance):
            def call_predicate(_self, item):
                return isinstance(item[1], Missing)

        class allowed_letter_a(MinimalAllowance):
            def call_predicate(_self, item):
                return item[1].args[0] == 'a'

        self.allowed_missing = allowed_missing()
        self.allowed_letter_a = allowed_letter_a()

    def test_CombinedAllowance(self):
        class LogicalAnd(CombinedAllowance):
            def call_predicate(_self, item):
                return (_self.left.call_predicate(item)
                        and _self.right.call_predicate(item))

            def __repr__(_self):
                return super(LogicalAnd, _self).__repr__()

        allowance = LogicalAnd(left=self.allowed_missing,
                               right=self.allowed_letter_a)
        self.assertIs(allowance.left, self.allowed_missing)
        self.assertIs(allowance.right, self.allowed_letter_a)

        msg = 'Higher priority number should always move to the right-hand side.'
        self.allowed_missing.priority = 3   # <- Change priority.
        self.allowed_letter_a.priority = 2  # <- Change priority.
        allowance = LogicalAnd(left=self.allowed_missing,  # <- Given as `left`.
                               right=self.allowed_letter_a)
        self.assertIs(allowance.left, self.allowed_letter_a, msg=msg)
        self.assertIs(allowance.right, self.allowed_missing, msg=msg)  # <- Moved to `right`.

    def test_IntersectedAllowance(self):
        with self.assertRaises(ValidationError) as cm:
            with IntersectedAllowance(self.allowed_missing, self.allowed_letter_a):
                raise ValidationError(
                    'example error',
                    [Missing('a'), Extra('a'), Missing('b'), Extra('b')],
                )
        differences = cm.exception.differences
        self.assertEqual(list(differences), [Extra('a'), Missing('b'), Extra('b')])

    def test_UnionedAllowance(self):
        with self.assertRaises(ValidationError) as cm:
            with UnionedAllowance(self.allowed_missing, self.allowed_letter_a):
                raise ValidationError(
                    'example error',
                    [Missing('a'), Extra('a'), Missing('b'), Extra('b')],
                )
        differences = cm.exception.differences
        self.assertEqual(list(differences), [Extra('b')])


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


class TestAllowedPercentDeviation(unittest.TestCase):
    def setUp(self):
        self.differences = {
            'aaa': Deviation(-1, 16),  # -6.25%
            'bbb': Deviation(+4, 16),  # 25.0%
            'ccc': Deviation(+2, 16),  # 12.5%
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
        self.assertEqual(remaining, {'bbb': Deviation(+4, 16)})

    def test_lower_upper_syntax(self):
        with self.assertRaises(ValidationError) as cm:
            with allowed_percent_deviation(0.0, 0.3):  # <- Allows from 0 to 30%.
                raise ValidationError('example error', self.differences)
        result_diffs = cm.exception.differences
        self.assertEqual({'aaa': Deviation(-1, 16)}, result_diffs)

    def test_same_value_case(self):
        with self.assertRaises(ValidationError) as cm:
            with allowed_percent_deviation(0.25, 0.25):  # <- Allows +25% only.
                raise ValidationError('example error', self.differences)
        result_diffs = cm.exception.differences
        self.assertEqual({'aaa': Deviation(-1, 16), 'ccc': Deviation(+2, 16)}, result_diffs)

    def test_special_values(self):
        # Test empty deviation cases--should pass without error.
        with allowed_percent_deviation(0):  # <- Allows empty deviations only.
            raise ValidationError('example error',
                                  [Deviation(None, 0), Deviation('', 0)])

        # Test diffs that can not be allowed as percentages.
        differences = [
            Deviation(None, 0),           # 0%
            Deviation(0, None),           # 0%
            Deviation(+2, 0),             # Can not be allowed by percent.
            Deviation(+2, None),          # Can not be allowed by percent.
            Deviation(float('nan'), 16),  # Not a number.
        ]
        with self.assertRaises(ValidationError) as cm:
            with allowed_percent_deviation(2.00):  # <- Allows +/- 200%.
                raise ValidationError('example error', differences)
        actual = cm.exception.differences
        expected = [
            Deviation(+2, 0),
            Deviation(+2, None),
            Deviation(float('nan'), 16),
        ]
        self.assertEqual(actual, expected)


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
        # Actual result can vary with unordered dictionaries.
        if len(actual) == 1:
            expected = {'bar': [Extra('xxx'), Missing('yyy')]}
        else:
            expected = {'foo': Extra('xxx'), 'bar': Missing('yyy')}
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

    def test_mapping_of_differences_and_wildcard_allowances(self):
        differences = {'foo': Extra('xxx'), 'bar': [Extra('xxx'), Missing('yyy')]}
        allowed = {Ellipsis: Extra('xxx')}

        with self.assertRaises(ValidationError) as cm:
            with allowed_specific(allowed):
                raise ValidationError('example error', differences)

        actual = cm.exception.differences
        expected = {'bar': Missing('yyy')}
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
        allowed = {Ellipsis: [Extra('xxx'), Missing('yyy')]}
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

    def test_dict_of_limits(self):
        with self.assertRaises(ValidationError) as cm:
            with allowed_limit({'A': 1, 'B': 2, 'C': 2}):
                raise ValidationError('example error',
                                      {'A': Extra('xxx'),
                                       'B': [Missing('yyy'), Missing('zzz')],
                                       'C': Extra('xxx'),
                                       'D': Extra('xxx')})

        remaining = cm.exception.differences
        self.assertIsInstance(remaining, collections.Mapping)
        self.assertEqual(remaining, {'D': Extra('xxx')})

    def test_ellipsis_wildcard_matching(self):
        # Using an ellipsis will match any key. So you can use
        # {...: 1} to allow 1 difference for every group.
        with self.assertRaises(ValidationError) as cm:
            with allowed_limit({Ellipsis: 1}):  # <- Allows 1 per group.
                raise ValidationError('example error',
                                      {'foo': Extra('xxx'), 'bar': [Missing('yyy'), Missing('zzz')]})

        remaining = cm.exception.differences
        self.assertIsInstance(remaining, collections.Mapping)
        self.assertEqual(remaining, {'bar': Missing('zzz')})


class TestUniversalComposability(unittest.TestCase):
    """Test that allowances are composable with allowances of the
    same type as well as all other allowance types.
    """
    def setUp(self):
        ntup = collections.namedtuple('ntup', ('cls', 'args', 'priority'))
        self.allowances = [
            ntup(cls=allowed_missing,           args=tuple(),                  priority=1),
            ntup(cls=allowed_extra,             args=tuple(),                  priority=1),
            ntup(cls=allowed_invalid,           args=tuple(),                  priority=1),
            ntup(cls=allowed_deviation,         args=(5,),                     priority=1),
            ntup(cls=allowed_percent_deviation, args=(0.05,),                  priority=1),
            ntup(cls=allowed_key,               args=(lambda *args: True,),    priority=1),
            ntup(cls=allowed_args,              args=(lambda *args: True,),    priority=1),
            ntup(cls=allowed_specific,          args=({'X': [Invalid('A')]},), priority=2),
            ntup(cls=allowed_limit,             args=({Ellipsis: 4},),         priority=3),
            ntup(cls=allowed_specific,          args=([Invalid('A')],),        priority=4),
            ntup(cls=allowed_limit,             args=(4,),                     priority=5),
        ]

    def test_completeness(self):
        """Check that self.allowances contains all of the allowances
        defined in datatest.
        """
        import datatest
        actual = datatest.allowance.__all__
        expected = (x.cls.__name__ for x in self.allowances)
        self.assertEqual(set(actual), set(expected))

    def test_priority_values(self):
        for x in self.allowances:
            instance = x.cls(*x.args)  # <- Initialize class instance.
            actual = instance.priority
            expected = x.priority
            self.assertEqual(actual, expected, x.cls.__name__)

    def test_bitwise_composition(self):
        """Check that all allowance types can be composed with each
        other without exception.
        """
        # Create two lists of identical allowances. Even though
        # the lists are the same, they should contain separate
        # instances--not simply pointers to the same instances.
        allow1 = list(x.cls(*x.args) for x in self.allowances)
        allow2 = list(x.cls(*x.args) for x in self.allowances)
        combinations = list(itertools.product(allow1, allow2))

        for a, b in combinations:
            composed = a | b
            self.assertIsInstance(composed, UnionedAllowance)
            self.assertEqual(composed.priority, max(a.priority, b.priority))

        for a, b in combinations:
            composed = a & b
            self.assertIsInstance(composed, IntersectedAllowance)
            self.assertEqual(composed.priority, max(a.priority, b.priority))

    def test_integration_examples(self):
        # Test allowance of +/- 2 OR +/- 6%.
        with self.assertRaises(ValidationError) as cm:
            differences = [
                Deviation(+2, 1),   # 200%
                Deviation(+4, 8),   #  50%
                Deviation(+8, 32),  #  25%
            ]
            with allowed_deviation(2) | allowed_percent_deviation(0.25):
                raise ValidationError('example error', differences)

        remaining = cm.exception.differences
        self.assertEqual(remaining, [Deviation(+4, 8)])

        # Test missing-type AND matching-value.
        with self.assertRaises(ValidationError) as cm:
            differences = [
                Missing('A'),
                Missing('B'),
                Extra('C'),
            ]
            with allowed_missing() & allowed_args(lambda x: x == 'A'):
                raise ValidationError('example error', differences)

        remaining = cm.exception.differences
        self.assertEqual(remaining, [Missing('B'), Extra('C')])

        # Test missing-type OR allowed-limit.
        with self.assertRaises(ValidationError) as cm:
            differences = [
                Extra('A'),
                Missing('B'),
                Extra('C'),
                Missing('D'),
            ]
            with allowed_limit(1) | allowed_missing():
                raise ValidationError('example error', differences)

        remaining = cm.exception.differences
        self.assertEqual(remaining, [Extra('C')])

        # Test missing-type AND allowed-limit.
        with self.assertRaises(ValidationError) as cm:
            differences = [
                Extra('A'),
                Missing('B'),
                Missing('C'),
            ]
            with allowed_limit(1) & allowed_missing():  # Allows only 1 missing.
                raise ValidationError('example error', differences)

        remaining = cm.exception.differences
        self.assertEqual(remaining, [Extra('A'), Missing('C')])

        # Test missing-type OR allowed-limit.
        with self.assertRaises(ValidationError) as cm:
            differences = [
                Extra('A'),
                Missing('B'),
                Extra('C'),
                Missing('D'),
            ]
            with allowed_limit(1) | allowed_specific(Extra('A')):
                raise ValidationError('example error', differences)

        remaining = cm.exception.differences
        self.assertEqual(remaining, [Extra('C'), Missing('D')])
