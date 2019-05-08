# -*- coding: utf-8 -*-
import inspect
import sys
from . import _unittest as unittest
from datatest._compatibility.builtins import *
from datatest._compatibility.collections import namedtuple
from datatest._compatibility.collections.abc import Mapping
from datatest._compatibility import contextlib
from datatest._compatibility import itertools
from datatest._utils import nonstringiter
from datatest.validation import ValidationError
from datatest.difference import BaseDifference
from datatest.difference import Missing
from datatest.difference import Extra
from datatest.difference import Invalid
from datatest.difference import Deviation
from datatest.acceptances import (
    BaseAcceptance,
    CombinedAcceptance,
    IntersectedAcceptance,
    UnionedAcceptance,
    AcceptedDifferences,
    AcceptedMissing,
    AcceptedExtra,
    AcceptedInvalid,
    AcceptedKeys,
    AcceptedArgs,
    AcceptedDeviation,
    AcceptedPercent,
    AcceptedTolerance,
    AcceptedFuzzy,
    AcceptedSpecific,
    AcceptedLimit,
)


class MinimalAcceptance(BaseAcceptance):  # A minimal subclass for
    def call_predicate(self, item):       # testing--defines three
        return False                      # concrete stubs to satisfy
                                          # abstract method requirement
    def __repr__(self):                   # of the base class.
        return super(MinimalAcceptance, self).__repr__()


class TestBaseAcceptance(unittest.TestCase):
    def test_default_priority(self):
        class accepts_nothing(MinimalAcceptance):
            def call_predicate(_self, item):
                return False

        acceptance = accepts_nothing()
        self.assertEqual(acceptance.priority, 100)

    def test_preserve_priority(self):
        # Calling the superclass' __init__() should not overwrite
        # the `priority` attribute if it has been previously set by
        # a subclass.
        class accepts_nothing(MinimalAcceptance):
            def __init__(_self, msg=None):
                _self.priority = 200
                super(accepts_nothing, _self).__init__(msg)

            def call_predicate(_self, item):
                return False

        acceptance = accepts_nothing()
        self.assertEqual(acceptance.priority, 200, 'should not overwrite existing `priority`')

    def test_serialized_items(self):
        item_list = [1, 2]
        actual = BaseAcceptance._serialized_items(item_list)
        expected = [(None, 1), (None, 2)]
        self.assertEqual(list(actual), expected, 'serialize list of elements')

        item_dict = {'A': 'x', 'B': 'y'}
        actual = BaseAcceptance._serialized_items(item_dict)
        expected = [('A', 'x'), ('B', 'y')]
        self.assertEqual(sorted(actual), expected, 'serialize mapping of elements')

        item_dict = {'A': ['x', 'y'], 'B': ['x', 'y']}
        actual = BaseAcceptance._serialized_items(item_dict)
        expected = [('A', 'x'), ('A', 'y'), ('B', 'x'), ('B', 'y')]
        self.assertEqual(sorted(actual), expected, 'serialize mapping of lists')

    def test_deserialized_items(self):
        stream = [(None, 1), (None, 2)]
        actual = BaseAcceptance._deserialized_items(stream)
        expected = {None: [1, 2]}
        self.assertEqual(actual, expected)

        stream = [('A', 'x'), ('B', 'y')]
        actual = BaseAcceptance._deserialized_items(stream)
        expected = {'A': 'x', 'B': 'y'}
        self.assertEqual(actual, expected)

        stream = [('A', 'x'), ('A', 'y'), ('B', 'x'), ('B', 'y')]
        actual = BaseAcceptance._deserialized_items(stream)
        expected = {'A': ['x', 'y'], 'B': ['x', 'y']}
        self.assertEqual(actual, expected)

    def test_filterfalse(self):
        class accepted_missing(MinimalAcceptance):
            def call_predicate(_self, item):
                return isinstance(item[1], Missing)

        acceptance = accepted_missing()
        result = acceptance._filterfalse([
            (None, Missing('A')),
            (None, Extra('B')),
        ])
        self.assertEqual(list(result), [(None, Extra('B'))])

    def test_enter_context(self):
        """The __enter__() method should return the object itself
        (see PEP 343 for context manager protocol).
        """
        acceptance = MinimalAcceptance()
        self.assertIs(acceptance, acceptance.__enter__())

    def test_exit_context(self):
        """The __exit__() method should re-raise exceptions that are
        not accepted and it should return True when there are no errors
        or if all differences have been accepted (see PEP 343 for
        context manager protocol).
        """
        try:
            raise ValidationError([Missing('A'), Extra('B')], 'error description')
        except ValidationError:
            type, value, traceback = sys.exc_info()  # Get exception info.

        with self.assertRaises(ValidationError) as cm:
            acceptance = MinimalAcceptance('acceptance message')
            acceptance.__exit__(type, value, traceback)

        description = cm.exception.description
        self.assertEqual(description, 'acceptance message: error description')

        # Test with no error description.
        try:
            raise ValidationError([Missing('A'), Extra('B')])  # <- No description.
        except ValidationError:
            type, value, traceback = sys.exc_info()  # Get exception info.

        with self.assertRaises(ValidationError) as cm:
            acceptance = MinimalAcceptance('acceptance message')
            acceptance.__exit__(type, value, traceback)

        description = cm.exception.description
        self.assertEqual(description, 'acceptance message')


class TestAcceptanceProtocol(unittest.TestCase):
    def setUp(self):
        class LoggingAcceptance(MinimalAcceptance):
            def __init__(_self, msg=None):
                _self.log = []
                super(LoggingAcceptance, _self).__init__(msg)

            def __repr__(self):
                return super(LoggingAcceptance, _self).__repr__()

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

        self.LoggingAcceptance = LoggingAcceptance

    def test_acceptance_protocol(self):
        accepted = self.LoggingAcceptance()
        result = accepted._filterfalse([
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
        self.assertEqual(accepted.log, expected)


class TestLogicalComposition(unittest.TestCase):
    def setUp(self):
        class accepted_missing(MinimalAcceptance):
            def call_predicate(_self, item):
                return isinstance(item[1], Missing)

        class accepted_letter_a(MinimalAcceptance):
            def __init__(_self):
                _self.priority = 150

            def start_collection(_self):
                _self._not_used = True

            def call_predicate(_self, item):
                if item[1].args[0] == 'a' and _self._not_used:
                    _self._not_used = False
                    return True
                return False

        self.accepted_missing = accepted_missing()
        self.accepted_letter_a = accepted_letter_a()

    def test_CombinedAcceptance(self):
        class LogicalAnd(CombinedAcceptance):
            def call_predicate(_self, item):
                return (_self.left.call_predicate(item)
                        and _self.right.call_predicate(item))

            def __repr__(_self):
                return super(LogicalAnd, _self).__repr__()

        self.accepted_missing.priority = 222
        self.accepted_letter_a.priority = 333

        acceptance = LogicalAnd(left=self.accepted_missing,
                                right=self.accepted_letter_a)
        self.assertEqual(acceptance.priority, 333)

    def test_IntersectedAcceptance(self):
        original_diffs = [Extra('a'), Missing('a'), Missing('b'), Extra('b')]

        with self.assertRaises(ValidationError) as cm:
            with IntersectedAcceptance(self.accepted_missing, self.accepted_letter_a):
                raise ValidationError(original_diffs)
        differences = cm.exception.differences
        self.assertEqual(list(differences), [Extra('a'), Missing('b'), Extra('b')])

        # Test with acceptances in reverse-order (should give same result).
        with self.assertRaises(ValidationError) as cm:
            with IntersectedAcceptance(self.accepted_letter_a, self.accepted_missing):
                raise ValidationError(original_diffs)
        differences = cm.exception.differences
        self.assertEqual(list(differences), [Extra('a'), Missing('b'), Extra('b')])

    def test_UnionedAcceptance(self):
        original_diffs = [Missing('a'), Extra('a'), Missing('b'), Extra('b')]

        with self.assertRaises(ValidationError) as cm:
            with UnionedAcceptance(self.accepted_missing, self.accepted_letter_a):
                raise ValidationError(original_diffs)
        differences = cm.exception.differences
        self.assertEqual(list(differences), [Extra('b')])

        # Test with acceptances in reverse-order (should give same result).
        with self.assertRaises(ValidationError) as cm:
            with UnionedAcceptance(self.accepted_letter_a, self.accepted_missing):
                raise ValidationError(original_diffs)
        differences = cm.exception.differences
        self.assertEqual(list(differences), [Extra('b')])


class TestAcceptedDifferences(unittest.TestCase):
    def assertAcceptance(self, differences, acceptance, expected):
        """Helper method to test acceptances."""
        with self.assertRaises(ValidationError) as cm:
            with acceptance:  # <- Apply acceptance!
                raise ValidationError(differences)
        remaining_diffs = cm.exception.differences

        if isinstance(differences, Mapping):
            remaining_diffs = dict(remaining_diffs)
        elif nonstringiter(remaining_diffs):
            remaining_diffs = list(remaining_diffs)
        self.assertEqual(remaining_diffs, expected)

    def test_mapping_vs_mapping(self):
        differences = {
            'a': [Missing('X'), Missing('X')],
            'b': [Missing('Y'), Missing('X')],
        }

        # Defaults to element-wise scope.
        acceptance = AcceptedDifferences({'a': Missing('X'), 'b': Missing('Y')})
        expected = {'b': Missing('X')}
        self.assertAcceptance(differences, acceptance, expected)

        # Defaults to group-wise scope.
        acceptance = AcceptedDifferences({'a': [Missing('X')], 'b': [Missing('Y')]})
        expected = {'a': Missing('X'), 'b': Missing('X')}
        self.assertAcceptance(differences, acceptance, expected)

    def test_mapping_vs_list(self):
        differences = {
            'a': [Missing('X')],
            'b': [Missing('Y'), Missing('X')],
            'c': [Missing('Y'), Missing('X'), Missing('X')],
        }

        acceptance = AcceptedDifferences([Missing('X')])
        expected = {'b': Missing('Y'), 'c': [Missing('Y'), Missing('X')]}
        self.assertAcceptance(differences, acceptance, expected)

        acceptance = AcceptedDifferences([Missing('X')], scope='element')
        expected = {'b': Missing('Y'), 'c': Missing('Y')}
        self.assertAcceptance(differences, acceptance, expected)

    def test_mapping_vs_difference(self):
        differences = {
            'a': [Missing('X')],
            'b': [Missing('Y'), Missing('X')],
        }
        acceptance = AcceptedDifferences(Missing('X'))
        expected = {'b': Missing('Y')}
        self.assertAcceptance(differences, acceptance, expected)

    def test_mapping_vs_type(self):
        differences = {
            'a': [Missing('X')],
            'b': [Missing('Y'), Extra('X')],
            'c': Missing('X'),
        }
        acceptance = AcceptedDifferences(Missing)
        expected = {'b': Extra('X')}
        self.assertAcceptance(differences, acceptance, expected)

    def test_nonmapping_vs_mapping(self):
        """A mapping accpetance will not accept any non-mapping differences."""

        differences = [Missing('Y'), Extra('X')]
        acceptance = AcceptedDifferences({'a': Extra('X')})
        self.assertAcceptance(differences, acceptance, differences)

        differences = Extra('X')
        acceptance = AcceptedDifferences({'a': Extra('X')})
        self.assertAcceptance(differences, acceptance, [differences])

    def test_list_vs_list(self):
        differences =  [Missing('X'), Missing('Y'), Missing('X')]
        acceptance = AcceptedDifferences([Missing('Y'), Missing('X')])  # <- Accept list of differences.
        expected = [Missing('X')]
        self.assertAcceptance(differences, acceptance, expected)

    def test_list_vs_difference(self):
        differences =  [Missing('X'), Missing('Y'), Missing('X')]
        acceptance = AcceptedDifferences(Missing('X'))
        expected = [Missing('Y')]
        self.assertAcceptance(differences, acceptance, expected)

    def test_list_vs_type(self):
        differences =  [Missing('X'), Missing('Y'), Extra('X')]
        acceptance = AcceptedDifferences(Missing)
        expected = [Extra('X')]
        self.assertAcceptance(differences, acceptance, expected)

    def test_difference_vs_list(self):
        differences =  Missing('X')
        acceptance = AcceptedDifferences([Missing('Y'), Missing('Z')])
        expected = [Missing('X')]
        self.assertAcceptance(differences, acceptance, expected)

        differences =  Missing('X')
        acceptance = AcceptedDifferences([Missing('X'), Missing('Y')])
        with acceptance:  # <- No error, all diffs accepted
            raise ValidationError(differences)

    def test_difference_vs_difference(self):
        differences =  Missing('X')
        acceptance = AcceptedDifferences(Missing('Y'))
        expected = [Missing('X')]
        self.assertAcceptance(differences, acceptance, expected)

        differences =  Missing('X')
        acceptance = AcceptedDifferences(Missing('X'))
        with acceptance:  # <- No error, all diffs accepted
            raise ValidationError(differences)

    def test_difference_vs_type(self):
        differences =  Missing('X')
        acceptance = AcceptedDifferences(Extra)
        expected = [Missing('X')]
        self.assertAcceptance(differences, acceptance, expected)

        differences =  Missing('X')
        acceptance = AcceptedDifferences(Missing)
        with acceptance:  # <- No error, all diffs accepted
            raise ValidationError(differences)

    def test_specified_scopes(self):
        # list vs difference, scope
        differences = {
            'a': [Missing('X'), Missing('X')],
            'b': [Missing('Y'), Missing('X')],
        }

        acceptance = AcceptedDifferences(
            {'a': [Missing('X')], 'b': [Missing('Y')]},
            scope='element',  # <- Element-wise scope.
        )
        expected = {'b': Missing('X')}
        self.assertAcceptance(differences, acceptance, expected)

        acceptance = AcceptedDifferences(
            {'a': Missing('X'), 'b': Missing('Y')},
            scope='group',  # <- Group-wise scope.
        )
        expected = {'a': Missing('X'), 'b': Missing('X')}
        self.assertAcceptance(differences, acceptance, expected)


class TestAcceptedDifferencesByType(unittest.TestCase):
    """These tests were taken from older AcceptedMissing,
    AcceptedExtra, and AcceptedInvalid acceptances.

    These checks may overlap ones in TestAcceptedDifferences.
    Once the new interface has proven to be an adequate replacement
    for the old interface, the duplicate checks should be removed
    and the unique ones should be moved to an appropriate location.
    """
    def test_accepted_missing(self):
        differences =  [Missing('X'), Missing('Y'), Extra('X')]

        with self.assertRaises(ValidationError) as cm:
            with AcceptedDifferences(Missing):  # <- Apply acceptance!
                raise ValidationError(differences)
        remaining_diffs = cm.exception.differences
        self.assertEqual(list(remaining_diffs), [Extra('X')])

    def test_accepted_extra(self):
        differences =  [Extra('X'), Extra('Y'), Missing('X')]

        with self.assertRaises(ValidationError) as cm:
            with AcceptedDifferences(Extra):  # <- Apply acceptance!
                raise ValidationError(differences)
        remaining_diffs = cm.exception.differences
        self.assertEqual(list(remaining_diffs), [Missing('X')])

    def test_accepted_invalid(self):
        differences =  [Invalid('X'), Invalid('Y'), Extra('Z')]

        with self.assertRaises(ValidationError) as cm:
            with AcceptedDifferences(Invalid):  # <- Apply acceptance!
                raise ValidationError(differences)
        remaining_diffs = cm.exception.differences
        self.assertEqual(list(remaining_diffs), [Extra('Z')])


class TestAcceptedMissing(unittest.TestCase):
    def test_accepted_missing(self):
        differences =  [Missing('X'), Missing('Y'), Extra('X')]

        with self.assertRaises(ValidationError) as cm:
            with AcceptedMissing():  # <- Apply acceptance!
                raise ValidationError(differences)
        remaining_diffs = cm.exception.differences
        self.assertEqual(list(remaining_diffs), [Extra('X')])


class TestAcceptedExtra(unittest.TestCase):
    def test_accepted_extra(self):
        differences =  [Extra('X'), Extra('Y'), Missing('X')]

        with self.assertRaises(ValidationError) as cm:
            with AcceptedExtra():  # <- Apply acceptance!
                raise ValidationError(differences)
        remaining_diffs = cm.exception.differences
        self.assertEqual(list(remaining_diffs), [Missing('X')])


class TestAcceptedInvalid(unittest.TestCase):
    def test_accepted_invalid(self):
        differences =  [Invalid('X'), Invalid('Y'), Extra('Z')]

        with self.assertRaises(ValidationError) as cm:
            with AcceptedInvalid():  # <- Apply acceptance!
                raise ValidationError(differences)
        remaining_diffs = cm.exception.differences
        self.assertEqual(list(remaining_diffs), [Extra('Z')])


class TestAcceptedKeys(unittest.TestCase):
    def test_internal_function(self):
        """The internal function object should be a predicate created
        by get_predicate().
        """
        acceptance = AcceptedKeys('aaa')
        self.assertEqual(acceptance.function.__name__, "'aaa'",
                         msg='predicate set to repr of string')

    def test_accept_string(self):
        with self.assertRaises(ValidationError) as cm:

            with AcceptedKeys('aaa'):  # <- Accept by string!
                raise ValidationError({
                    'aaa': Missing(1),
                    'bbb': Missing(2),
                })

        remaining_diffs = cm.exception.differences
        self.assertEqual(dict(remaining_diffs), {'bbb': Missing(2)})

    def test_accept_function(self):
        with self.assertRaises(ValidationError) as cm:

            def function(key):
                return key == 'aaa'

            with AcceptedKeys(function):  # <- Accept by function!
                raise ValidationError({
                    'aaa': Missing(1),
                    'bbb': Missing(2),
                })

        remaining_diffs = cm.exception.differences
        self.assertEqual(dict(remaining_diffs), {'bbb': Missing(2)})

    def test_composite_key(self):
        with self.assertRaises(ValidationError) as cm:

            with AcceptedKeys(('a', 7)):  # <- Accept using tuple!
                raise ValidationError({
                    ('a', 7): Missing(1),
                    ('b', 7): Missing(2)
                })

        remaining_diffs = cm.exception.differences
        self.assertEqual(dict(remaining_diffs), {('b', 7): Missing(2)})

    def test_nonmapping_container(self):
        """When differences container is not a mapping, the keys that
        AcceptedKeys() sees are all None.
        """
        with self.assertRaises(ValidationError) as cm:

            with AcceptedKeys('foo'):  # <- Accept keys that equal 'foo'.
                differences = [Missing(1), Extra(2)]  # <- List has no keys!
                raise ValidationError(differences)

        remaining_diffs = cm.exception.differences
        self.assertEqual(list(remaining_diffs), [Missing(1), Extra(2)])

    def test_repr(self):
        acceptance = AcceptedKeys('aaa')
        self.assertEqual(repr(acceptance), "AcceptedKeys('aaa')")

        acceptance = AcceptedKeys(('aaa', 1))
        self.assertEqual(repr(acceptance), "AcceptedKeys(('aaa', 1))")

        def helper(x):
            return True
        acceptance = AcceptedKeys(helper)
        self.assertEqual(repr(acceptance), "AcceptedKeys(helper)")


class TestAcceptedArgs(unittest.TestCase):
    def test_string_predicate(self):
        with self.assertRaises(ValidationError) as cm:

            with AcceptedArgs('bbb'):  # <- Acceptance!
                raise ValidationError([
                    Missing('aaa'),
                    Missing('bbb'),
                    Extra('bbb'),
                ])

        remaining_diffs = cm.exception.differences
        self.assertEqual(list(remaining_diffs), [Missing('aaa')])

    def test_function_predicate(self):
        with self.assertRaises(ValidationError) as cm:

            def function(args):
                diff, expected = args
                return diff < 2 and expected == 5

            with AcceptedArgs(function):  # <- Acceptance!
                raise ValidationError([
                    Deviation(+1, 5),
                    Deviation(+2, 5),
                ])

        remaining_diffs = cm.exception.differences
        self.assertEqual(list(remaining_diffs), [Deviation(+2, 5)])

    def test_multiarg_predicate(self):
        with self.assertRaises(ValidationError) as cm:

            def func(diff):
                return diff < 2

            with AcceptedArgs((func, 5)):
                raise ValidationError([
                    Deviation(+1, 5),
                    Deviation(+2, 5),
                ])

        remaining_diffs = cm.exception.differences
        self.assertEqual(list(remaining_diffs), [Deviation(+2, 5)])


class TestAcceptedDeviation(unittest.TestCase):
    def setUp(self):
        self.differences = {
            'aaa': Deviation(-1, 10),
            'bbb': Deviation(+3, 10),
            'ccc': Deviation(+2, 10),
        }

    def test_function_signature(self):
        with contextlib.suppress(AttributeError):       # Python 3.2 and older
            sig = inspect.signature(AcceptedDeviation)  # use ugly signatures.
            parameters = list(sig.parameters)
            self.assertEqual(parameters, ['tolerance', 'msg'])

    def test_tolerance_syntax(self):
        with self.assertRaises(ValidationError) as cm:
            with AcceptedDeviation(2):  # <- Accepts +/- 2.
                raise ValidationError(self.differences)
        remaining = cm.exception.differences
        self.assertEqual(remaining, {'bbb': Deviation(+3, 10)})

    def test_lower_upper_syntax(self):
        with self.assertRaises(ValidationError) as cm:
            with AcceptedDeviation(0, 3):  # <- Accepts from 0 to 3.
                raise ValidationError(self.differences)
        result_diffs = cm.exception.differences
        self.assertEqual({'aaa': Deviation(-1, 10)}, result_diffs)

    def test_same_value_case(self):
        with self.assertRaises(ValidationError) as cm:
            with AcceptedDeviation(3, 3):  # <- Accepts off-by-3 only.
                raise ValidationError(self.differences)
        result_diffs = cm.exception.differences
        self.assertEqual({'aaa': Deviation(-1, 10), 'ccc': Deviation(+2, 10)}, result_diffs)

    def test_invalid_arguments(self):
        with self.assertRaises(ValueError) as cm:
            with AcceptedDeviation(-5):  # <- invalid
                pass
        exc = str(cm.exception)
        self.assertTrue(exc.startswith('tolerance should not be negative'))

        with self.assertRaises(ValueError) as cm:
            with AcceptedDeviation(3, 2):  # <- invalid
                pass
        exc = str(cm.exception)
        expected = 'lower must not be greater than upper, got 3 (lower) and 2 (upper)'
        self.assertEqual(exc, expected)

    def test_empty_string(self):
        with AcceptedDeviation(0):  # <- Pass without failure.
            raise ValidationError(Deviation('', 0))

        with AcceptedDeviation(0):  # <- Pass without failure.
            raise ValidationError(Deviation(0, ''))

    def test_NaN_values(self):
        with self.assertRaises(ValidationError):  # <- NaN values should not be caught!
            with AcceptedDeviation(0):
                raise ValidationError(Deviation(float('nan'), 0))

    def test_non_deviation_diffs(self):
        diffs = [Missing('foo'), Extra('bar'), Invalid('baz')]
        with self.assertRaises(ValidationError) as cm:
            with AcceptedDeviation(5):
                raise ValidationError(diffs)

        uncaught_diffs = cm.exception.differences
        self.assertEqual(diffs, uncaught_diffs)


class TestAcceptedPercent(unittest.TestCase):
    def setUp(self):
        self.differences = {
            'aaa': Deviation(-1, 16),  # -6.25%
            'bbb': Deviation(+4, 16),  # 25.0%
            'ccc': Deviation(+2, 16),  # 12.5%
        }

    def test_function_signature(self):
        with contextlib.suppress(AttributeError):     # Python 3.2 and older
            sig = inspect.signature(AcceptedPercent)  # use ugly signatures.
            parameters = list(sig.parameters)
            self.assertEqual(parameters, ['tolerance', 'msg'])

    def test_tolerance_syntax(self):
        with self.assertRaises(ValidationError) as cm:
            with AcceptedPercent(0.2):  # <- Accepts +/- 20%.
                raise ValidationError(self.differences)
        remaining = cm.exception.differences
        self.assertEqual(remaining, {'bbb': Deviation(+4, 16)})

    def test_lower_upper_syntax(self):
        with self.assertRaises(ValidationError) as cm:
            with AcceptedPercent(0.0, 0.3):  # <- Accepts from 0 to 30%.
                raise ValidationError(self.differences)
        result_diffs = cm.exception.differences
        self.assertEqual({'aaa': Deviation(-1, 16)}, result_diffs)

    def test_same_value_case(self):
        with self.assertRaises(ValidationError) as cm:
            with AcceptedPercent(0.25, 0.25):  # <- Accepts +25% only.
                raise ValidationError(self.differences)
        result_diffs = cm.exception.differences
        self.assertEqual({'aaa': Deviation(-1, 16), 'ccc': Deviation(+2, 16)}, result_diffs)

    def test_special_values(self):
        # Test empty deviation cases--should pass without error.
        with AcceptedPercent(0):  # <- Accepts empty deviations only.
            raise ValidationError([
                Deviation(None, 0),
                Deviation('', 0),
            ])

        # Test diffs that can not be accepted as percentages.
        with self.assertRaises(ValidationError) as cm:
            with AcceptedPercent(2.00):  # <- Accepts +/- 200%.
                raise ValidationError([
                    Deviation(None, 0),           # 0%
                    Deviation(0, None),           # 0%
                    Deviation(+2, 0),             # Can not be accepted by percent.
                    Deviation(+2, None),          # Can not be accepted by percent.
                    Deviation(float('nan'), 16),  # Not a number.
                ])
        actual = cm.exception.differences
        expected = [
            Deviation(+2, 0),             # Can not be accepted by percent.
            Deviation(+2, None),          # Can not be accepted by percent.
            Deviation(float('nan'), 16),  # Not a number.
        ]
        self.assertEqual(actual, expected)

    def test_non_deviation_diffs(self):
        diffs = [Missing('foo'), Extra('bar'), Invalid('baz')]
        with self.assertRaises(ValidationError) as cm:
            with AcceptedPercent(0.05):
                raise ValidationError(diffs)

        uncaught_diffs = cm.exception.differences
        self.assertEqual(diffs, uncaught_diffs)


class TestAcceptedTolerance(unittest.TestCase):
    def setUp(self):
        self.differences = {
            'aaa': Deviation(-1, 16),  # -6.25%
            'bbb': Deviation(+4, 16),  # +25.0%
            'ccc': Deviation(+2, 16),  # +12.5%
        }

    @unittest.skip('Not implemented.')
    def test_function_signature(self):
        with contextlib.suppress(AttributeError):       # Python 3.2 and older
            sig = inspect.signature(AcceptedTolerance)  # use ugly signatures.
            parameters = list(sig.parameters)
            self.assertEqual(parameters, ['tolerance', 'msg'])

    def test_tolerance_syntax(self):
        with self.assertRaises(ValidationError) as cm:
            with AcceptedTolerance(2):  # <- Accepts +/- 2.
                raise ValidationError(self.differences)
        remaining = cm.exception.differences
        self.assertEqual(remaining, {'bbb': Deviation(+4, 16)})

    def test_lower_upper_syntax(self):
        with self.assertRaises(ValidationError) as cm:
            with AcceptedTolerance(0, 4):  # <- Accepts from 0 to 4.
                raise ValidationError(self.differences)
        result_diffs = cm.exception.differences
        self.assertEqual({'aaa': Deviation(-1, 16)}, result_diffs)

    def test_same_value_case(self):
        with self.assertRaises(ValidationError) as cm:
            with AcceptedTolerance(4, 4):  # <- Accepts off-by-4 only.
                raise ValidationError(self.differences)
        result_diffs = cm.exception.differences
        self.assertEqual({'aaa': Deviation(-1, 16), 'ccc': Deviation(+2, 16)}, result_diffs)

    def test_invalid_arguments(self):
        with self.assertRaises(ValueError) as cm:
            with AcceptedTolerance(-5):  # <- invalid
                pass
        exc = str(cm.exception)
        self.assertTrue(exc.startswith('tolerance should not be negative'))

        with self.assertRaises(ValueError) as cm:
            with AcceptedTolerance(4, 2):  # <- invalid
                pass
        exc = str(cm.exception)
        expected = 'lower must not be greater than upper, got 4 (lower) and 2 (upper)'
        self.assertEqual(exc, expected)

    def test_empty_string(self):
        with AcceptedTolerance(0):  # <- Pass without failure.
            raise ValidationError(Deviation('', 0))

        with AcceptedTolerance(0):  # <- Pass without failure.
            raise ValidationError(Deviation(0, ''))

    def test_NaN_values(self):
        with self.assertRaises(ValidationError):  # <- NaN values should not be caught!
            with AcceptedTolerance(0):
                raise ValidationError(Deviation(float('nan'), 0))

    def test_duck_typing(self):
        """If it looks like a Deviation, it should be treated like a
        Deviation.
        """
        # Define a non-deviation class that "looks" like a deviation.
        class DeviationLike(BaseDifference):
            def __init__(self, a, b):
                self.deviation = a
                self.expected = b

            @property
            def args(self):
                return (self.expected, self.deviation)

        # Check that Deviation-like differences are treated as Deviations.
        with self.assertRaises(ValidationError) as cm:
            with AcceptedTolerance(2):  # <- Accepts +/- 2.
                raise ValidationError([
                    DeviationLike(-1, 16),
                    DeviationLike(+4, 16),
                    DeviationLike(+2, 16),
                ])
        remaining = cm.exception.differences
        self.assertEqual(remaining, [DeviationLike(+4, 16)])

    def test_extra_deviation(self):
        with self.assertRaises(ValidationError) as cm:
            with AcceptedTolerance(-2, 1):  # <- Accepts from -2 to +1.
                raise ValidationError([
                    Extra(-3),      # <- Rejected: Outside accepted range.
                    Extra(-2),      # <- ACCEPTED!
                    Extra(0),       # <- ACCEPTED!
                    Extra(1),       # <- ACCEPTED!
                    Extra(2),       # <- Rejected: Outside accepted range.
                    Extra((1, 2)),  # <- Rejected: Too many args.
                    Extra('abc'),   # <- Rejected: Wrong type.
                ])
        remaining = cm.exception.differences
        self.assertEqual(remaining, [Extra(-3), Extra(2), Extra((1, 2)), Extra('abc')])

        # Check error percent.
        with self.assertRaises(ValidationError) as cm:
            with AcceptedTolerance(2.0, percent=True):  # <- Accepts +/- 200%.
                raise ValidationError([
                    Extra(-1),  # <- Rejected: Can not be accepted by percent.
                    Extra(0),   # <- ACCEPTED!
                    Extra(2),   # <- Rejected: Can not be accepted by percent.
                ])
        remaining = cm.exception.differences
        self.assertEqual(remaining, [Extra(-1), Extra(2)])

    def test_missing_deviation(self):
        with self.assertRaises(ValidationError) as cm:
            with AcceptedTolerance(-2, 1):  # <- Accepts from -2 to +1.
                raise ValidationError([
                    Missing(-3),      # <- Rejected: Outside accepted range.
                    Missing(-2),      # <- Rejected: Outside accepted range.
                    Missing(0),       # <- ACCEPTED!
                    Missing(1),       # <- ACCEPTED!
                    Missing(2),       # <- ACCEPTED!
                    Missing((1, 2)),  # <- Rejected: Wrong type.
                    Missing('abc'),   # <- Rejected: Wrong type.
                ])
        remaining = cm.exception.differences
        self.assertEqual(remaining, [Missing(-3), Missing(-2), Missing((1, 2)), Missing('abc')])

        # Check error percent.
        with self.assertRaises(ValidationError) as cm:
            with AcceptedTolerance(1.0, percent=True):  # <- Accepts +/- 100%.
                raise ValidationError([
                    Missing(-1),  # <- ACCEPTED!
                    Missing(0),   # <- ACCEPTED!
                    Missing(2),   # <- ACCEPTED!
                    Missing((1, 2)),  # <- Rejected: Wrong type.
                    Missing('abc'),   # <- Rejected: Wrong type.
                ])
        remaining = cm.exception.differences
        self.assertEqual(remaining, [Missing((1, 2)), Missing('abc')])

    def test_invalid_deviation_single_arg(self):
        """Single argument Invalid differences treated the same as
        Extra differences.
        """
        with self.assertRaises(ValidationError) as cm:
            with AcceptedTolerance(-2, 1):  # <- Accepts from -2 to +1.
                raise ValidationError([
                    Invalid(-3),      # <- Rejected: Outside accepted range.
                    Invalid(-2),      # <- ACCEPTED!
                    Invalid(0),       # <- ACCEPTED!
                    Invalid(1),       # <- ACCEPTED!
                    Invalid(2),       # <- Rejected: Outside accepted range.
                    Invalid((1, 2)),  # <- Rejected: Wrong type.
                    Invalid('abc'),   # <- Rejected: Wrong type.
                ])
        remaining = cm.exception.differences
        self.assertEqual(remaining, [Invalid(-3), Invalid(2), Invalid((1, 2)), Invalid('abc')])

        # Check error percent.
        with self.assertRaises(ValidationError) as cm:
            with AcceptedTolerance(2.0, percent=True):  # <- Accepts +/- 200%.
                raise ValidationError([
                    Invalid(-1),  # <- Rejected: Can not be accepted by percent.
                    Invalid(0),   # <- ACCEPTED!
                    Invalid(2),   # <- Rejected: Can not be accepted by percent.
                ])
        remaining = cm.exception.differences
        self.assertEqual(remaining, [Invalid(-1), Invalid(2)])

    def test_invalid_deviation_multiple_args(self):
        """Two-element Invalid differences are normalized and treated
        like Deviation differences.
        """
        with self.assertRaises(ValidationError) as cm:
            with AcceptedTolerance(-2, 1):  # <- Accepts from -2 to +1.
                raise ValidationError([
                    Invalid(-3, 0),         # <- Rejected: -3 is outside accepted range.
                    Invalid(5, 7),          # <- ACCEPTED: -2 deviation.
                    Invalid(0, ''),         # <- ACCEPTED.
                    Invalid(11, 10),        # <- ACCEPTED: +1 deviation.
                    Invalid(12, 10),        # <- Rejected: +2 is outside accepted range.
                    Invalid((1,), (3,)),    # <- Rejected: Wrong type.
                    Invalid('abc', 'def'),  # <- Rejected: Wrong type.
                ])
        remaining = cm.exception.differences
        self.assertEqual(remaining, [Invalid(-3, 0), Invalid(12, 10), Invalid((1,), (3,)), Invalid('abc', 'def')])

        # Check error percent.
        with self.assertRaises(ValidationError) as cm:
            with AcceptedTolerance(0.5, percent=True):  # <- Accepts +/- 50%.
                raise ValidationError([
                    Invalid(50, 100),   # <- ACCEPTED: -50% deviation.
                    Invalid(150, 100),  # <- ACCEPTED: +50% deviation.
                    Invalid(0, 0),      # <- ACCEPTED!
                    Invalid(0.5, 0),    # <- Rejected: Can not be accepted by percent.
                    Invalid(4, 2),      # <- Rejected: +100% is outside range.
                ])
        remaining = cm.exception.differences
        self.assertEqual(remaining, [Invalid(0.5, 0), Invalid(4, 2)])

    @unittest.skip('TODO: Finish this test.')
    def test_nonnumeric_but_compatible(self):
        pass

    @unittest.skip('TODO: Finish this test.')
    def test_incompatible_diffs(self):
        pass

    def test_percent_error(self):
        # Test "tolerance" syntax.
        with self.assertRaises(ValidationError) as cm:
            with AcceptedTolerance(0.2, percent=True):  # <- Accepts +/- 20%.
                raise ValidationError(self.differences)
        remaining = cm.exception.differences
        self.assertEqual(remaining, {'bbb': Deviation(+4, 16)})

        # Test "upper/lower" syntax.
        with self.assertRaises(ValidationError) as cm:
            with AcceptedTolerance(0.0, 0.3, percent=True):  # <- Accepts from 0 to 30%.
                raise ValidationError(self.differences)
        result_diffs = cm.exception.differences
        self.assertEqual({'aaa': Deviation(-1, 16)}, result_diffs)

    def test_percent_empty_value_handling(self):
        # Test empty deviation cases--should pass without error.
        with AcceptedTolerance(0, percent=True):  # <- Accepts empty deviations only.
            raise ValidationError([
                Deviation(None, 0),
                Deviation('', 0),
            ])

        # Test diffs that can not be accepted as percentages.
        with self.assertRaises(ValidationError) as cm:
            with AcceptedTolerance(2.00, percent=True):  # <- Accepts +/- 200%.
                raise ValidationError([
                    Deviation(None, 0),           # 0%
                    Deviation(0, None),           # 0%
                    Deviation(+2, 0),             # Can not be accepted by percent.
                    Deviation(+2, None),          # Can not be accepted by percent.
                    Deviation(float('nan'), 16),  # Not a number.
                ])
        actual = cm.exception.differences
        expected = [
            Deviation(+2, 0),             # Can not be accepted by percent.
            Deviation(+2, None),          # Can not be accepted by percent.
            Deviation(float('nan'), 16),  # Not a number.
        ]
        self.assertEqual(actual, expected)


class TestAcceptedFuzzy(unittest.TestCase):
    def setUp(self):
        self.differences = [
            Invalid('aaax', 'aaaa'),
            Invalid('bbyy', 'bbbb'),
        ]

    def test_passing(self):
        with AcceptedFuzzy():  # <- default cutoff=0.6
            raise ValidationError([Invalid('aaax', 'aaaa')])

        with AcceptedFuzzy(cutoff=0.5):  # <- Lower cutoff accepts more.
            raise ValidationError(self.differences)

    def test_failing(self):
        with self.assertRaises(ValidationError) as cm:
            with AcceptedFuzzy(cutoff=0.7):
                raise ValidationError(self.differences)
        remaining = cm.exception.differences
        self.assertEqual(remaining, [Invalid('bbyy', 'bbbb')])

        with self.assertRaises(ValidationError) as cm:
            with AcceptedFuzzy(cutoff=0.8):
                raise ValidationError(self.differences)
        remaining = cm.exception.differences
        self.assertEqual(remaining, self.differences, msg='none accepted')

    def test_incompatible_diffs(self):
        """Test differences that cannot be fuzzy matched."""
        incompatible_diffs = [
            Missing('foo'),
            Extra('bar'),
            Invalid('baz'),  # <- Cannot accept if there's no expected value.
            Deviation(1, 10),
        ]
        differences = incompatible_diffs + self.differences

        with self.assertRaises(ValidationError) as cm:
            with AcceptedFuzzy(cutoff=0.5):
                raise ValidationError(differences)

        remaining = cm.exception.differences
        self.assertEqual(remaining, incompatible_diffs)


class TestAcceptedSpecific(unittest.TestCase):
    def test_list_and_list(self):
        differences = [Extra('xxx'), Missing('yyy')]
        accepted = [Extra('xxx')]
        expected = [Missing('yyy')]

        with self.assertRaises(ValidationError) as cm:
            with AcceptedSpecific(accepted):
                raise ValidationError(differences)

        actual = list(cm.exception.differences)
        self.assertEqual(actual, expected)

    def test_list_and_diff(self):
        differences = [Extra('xxx'), Missing('yyy')]
        accepted = Extra('xxx')  # <- Single diff, not in a container.

        with self.assertRaises(ValidationError) as cm:
            with AcceptedSpecific(accepted):
                raise ValidationError(differences)

        actual = list(cm.exception.differences)
        expected = [Missing('yyy')]
        self.assertEqual(actual, expected)

    def test_excess_accepted(self):
        diffs = [Extra('xxx')]
        accepted = [Extra('xxx'), Missing('yyy')]  # <- More accepted than
        with AcceptedSpecific(accepted):           #    are actually found.
            raise ValidationError(diffs)

    def test_duplicates(self):
        # Three of the exact-same differences.
        differences = [Extra('xxx'), Extra('xxx'), Extra('xxx')]

        # Only accept one of them.
        with self.assertRaises(ValidationError) as cm:
            accepted = [Extra('xxx')]
            with AcceptedSpecific(accepted):
                raise ValidationError(differences)

        actual = list(cm.exception.differences)
        expected = [Extra('xxx'), Extra('xxx')]  # Expect two remaining.
        self.assertEqual(actual, expected)

        # Only accept two of them.
        with self.assertRaises(ValidationError) as cm:
            accepted = [Extra('xxx'), Extra('xxx')]
            with AcceptedSpecific(accepted):
                raise ValidationError(differences)

        actual = list(cm.exception.differences)
        expected = [Extra('xxx')]  # Expect one remaining.
        self.assertEqual(actual, expected)

        # Accept all three.
        accepted = [Extra('xxx'), Extra('xxx'), Extra('xxx')]
        with AcceptedSpecific(accepted):
            raise ValidationError(differences)

    def test_dict_and_list(self):
        """List of accepted differences applied to each group separately."""
        differences = {'foo': Extra('xxx'), 'bar': [Extra('xxx'), Missing('yyy')]}
        accepted = [Extra('xxx')]

        with self.assertRaises(ValidationError) as cm:
            with AcceptedSpecific(accepted):
                raise ValidationError(differences)

        actual = cm.exception.differences
        expected = {'bar': Missing('yyy')}
        self.assertEqual(actual, expected)

    def test_dict_and_dict(self):
        differences = {'foo': Extra('xxx'), 'bar': [Extra('xxx'), Missing('yyy')]}
        accepted = {'bar': Extra('xxx')}

        with self.assertRaises(ValidationError) as cm:
            with AcceptedSpecific(accepted):
                raise ValidationError(differences)

        actual = cm.exception.differences
        expected = {'foo': Extra('xxx'), 'bar': Missing('yyy')}
        self.assertEqual(actual, expected)

    def test_dict_with_predicates(self):
        """Ellipsis wildcard key matches all, treats as a single group."""
        differences = {
            'foo': Extra('xxx'),
            'bar': [Extra('yyy'), Missing('yyy')],
            'baz': [Extra('zzz'), Missing('zzz')],
        }

        accepted = {
            lambda x: x.startswith('ba'): [
                Extra('yyy'),
                Extra('zzz'),
            ],
        }

        with self.assertRaises(ValidationError) as cm:
            with AcceptedSpecific(accepted):
                raise ValidationError(differences)

        actual = cm.exception.differences
        expected = {
            'foo': Extra('xxx'),
            'bar': Missing('yyy'),
            'baz': Missing('zzz'),
        }
        self.assertEqual(actual, expected)

    def test_predicate_collision(self):
        """Ellipsis wildcard key matches all, treats as a single group."""
        differences = {
            'foo': Extra('xxx'),
            'bar': [Extra('yyy'), Missing('yyy')],
        }

        def accepted1(x):
            return x.startswith('ba')

        def accepted2(x):
            return x == 'bar'

        accepted = {
            accepted1: Extra('yyy'),
            accepted2: Missing('yyy'),
        }

        regex = ("the key 'bar' matches multiple predicates: "
                 "accepted[12], accepted[12]")
        with self.assertRaisesRegex(KeyError, regex):
            with AcceptedSpecific(accepted):
                raise ValidationError(differences)

    def test_dict_global_wildcard_predicate(self):
        """Ellipsis wildcard key matches all, treats as a single group."""
        differences = {'foo': Extra('xxx'), 'bar': [Extra('xxx'), Missing('yyy')]}
        accepted = {Ellipsis: Extra('xxx')}

        with self.assertRaises(ValidationError) as cm:
            with AcceptedSpecific(accepted):
                raise ValidationError(differences)

        actual = cm.exception.differences
        # Actual result can vary with unordered dictionaries.
        if len(actual) == 1:
            expected = {'bar': [Extra('xxx'), Missing('yyy')]}
        else:
            expected = {'foo': Extra('xxx'), 'bar': Missing('yyy')}
        self.assertEqual(actual, expected)

    def test_all_accepted(self):
        differences = {'foo': Extra('xxx'), 'bar': Missing('yyy')}
        accepted = {'foo': Extra('xxx'), 'bar': Missing('yyy')}

        with AcceptedSpecific(accepted):  # <- Accepts all differences, no error!
            raise ValidationError(differences)

    def test_combination_of_cases(self):
        """This is a bit of an integration test."""
        differences = {
            'foo': [Extra('xxx'), Missing('yyy')],
            'bar': [Extra('xxx')],
            'baz': [Extra('xxx'), Missing('yyy'), Extra('zzz')],
        }
        #accepted = {Ellipsis: [Extra('xxx'), Missing('yyy')]}
        accepted = [Extra('xxx'), Missing('yyy')]
        with self.assertRaises(ValidationError) as cm:
            with AcceptedSpecific(accepted):
                raise ValidationError(differences)

        actual = cm.exception.differences
        self.assertEqual(actual, {'baz': Extra('zzz')})


class TestAcceptedLimit(unittest.TestCase):
    def test_bad_arg(self):
        """An old version of AcceptedLimit() used to support dict
        arguments but this behavior has been removed. It should now
        raise a TypeError.
        """
        with self.assertRaises(TypeError):
            AcceptedLimit(dict())

    def test_under_limit(self):
        with AcceptedLimit(3):  # <- Accepts 3 and there are only 2.
            raise ValidationError([Extra('xxx'), Missing('yyy')])

        with AcceptedLimit(3):  # <- Accepts 3 and there are only 2.
            raise ValidationError({'foo': Extra('xxx'), 'bar': Missing('yyy')})

    def test_at_limit(self):
        with AcceptedLimit(2):  # <- Accepts 2 and there are 2.
            raise ValidationError([Extra('xxx'), Missing('yyy')])

        with AcceptedLimit(3):  # <- Accepts 2 and there are 2.
            raise ValidationError({'foo': Extra('xxx'), 'bar': Missing('yyy')})

    def test_over_limit(self):
        with self.assertRaises(ValidationError) as cm:
            with AcceptedLimit(1):  # <- Accepts 1 but there are 2.
                raise ValidationError([Extra('xxx'), Missing('yyy')])

        remaining = list(cm.exception.differences)
        self.assertEqual(remaining, [Missing('yyy')])

        with self.assertRaises(ValidationError) as cm:
            with AcceptedLimit(1):  # <- Accepts 1 and there are 2.
                raise ValidationError({'foo': Extra('xxx'), 'bar': Missing('yyy')})

        remaining = cm.exception.differences
        self.assertIsInstance(remaining, Mapping)
        self.assertEqual(len(remaining), 1)


class TestUniversalComposability(unittest.TestCase):
    """Test that acceptances are composable with acceptances of the
    same type as well as all other acceptance types.
    """
    def setUp(self):
        ntup = namedtuple('ntup', ('cls', 'args', 'priority'))
        self.acceptances = [
            ntup(cls=AcceptedMissing,   args=tuple(),                  priority=100),
            ntup(cls=AcceptedExtra,     args=tuple(),                  priority=100),
            ntup(cls=AcceptedInvalid,   args=tuple(),                  priority=100),
            ntup(cls=AcceptedDeviation, args=(5,),                     priority=100),
            ntup(cls=AcceptedFuzzy,     args=tuple(),                  priority=100),
            ntup(cls=AcceptedPercent,   args=(0.05,),                  priority=100),
            ntup(cls=AcceptedKeys,      args=(lambda args: True,),     priority=100),
            ntup(cls=AcceptedArgs,      args=(lambda *args: True,),    priority=100),
            ntup(cls=AcceptedSpecific,  args=({'X': [Invalid('A')]},), priority=200),
            ntup(cls=AcceptedLimit,     args=(4,),                     priority=300),
        ]

    def test_completeness(self):
        """Check that self.acceptances contains all of the acceptances
        defined in datatest.
        """
        import datatest
        actual = list(datatest.acceptances.__all__)  # Get copy of list.
        actual = [name for name in actual if name.startswith('Accepted')]
        expected = (x.cls.__name__ for x in self.acceptances)
        self.assertEqual(set(actual), set(expected))

    def test_priority_values(self):
        for x in self.acceptances:
            instance = x.cls(*x.args)  # <- Initialize class instance.
            actual = instance.priority
            expected = x.priority
            self.assertEqual(actual, expected, x.cls.__name__)

    def test_union_and_intersection(self):
        """Check that all acceptance types can be composed with each
        other without exception.
        """
        # Create two lists of identical acceptances. Even though
        # the lists are the same, they should contain separate
        # instances--not simply pointers to the same instances.
        accepted1 = list(x.cls(*x.args) for x in self.acceptances)
        accepted2 = list(x.cls(*x.args) for x in self.acceptances)
        combinations = list(itertools.product(accepted1, accepted2))

        for a, b in combinations:
            composed = a | b  # <- Union!
            self.assertIsInstance(composed, UnionedAcceptance)
            self.assertEqual(composed.priority, max(a.priority, b.priority))

        for a, b in combinations:
            composed = a & b  # <- Intersection!
            self.assertIsInstance(composed, IntersectedAcceptance)
            self.assertEqual(composed.priority, max(a.priority, b.priority))

    def test_integration_examples(self):
        # Test acceptance of +/- 2 OR +/- 6%.
        with self.assertRaises(ValidationError) as cm:
            differences = [
                Deviation(+2, 1),   # 200%
                Deviation(+4, 8),   #  50%
                Deviation(+8, 32),  #  25%
            ]
            with AcceptedDeviation(2) | AcceptedPercent(0.25):
                raise ValidationError(differences)

        remaining = cm.exception.differences
        self.assertEqual(remaining, [Deviation(+4, 8)])

        # Test missing-type AND matching-value.
        with self.assertRaises(ValidationError) as cm:
            differences = [
                Missing('A'),
                Missing('B'),
                Extra('C'),
            ]
            with AcceptedMissing() & AcceptedArgs(lambda x: x == 'A'):
                raise ValidationError(differences)

        remaining = cm.exception.differences
        self.assertEqual(remaining, [Missing('B'), Extra('C')])

        # Test missing-type OR accepted-limit.
        with self.assertRaises(ValidationError) as cm:
            differences = [
                Extra('A'),
                Missing('B'),
                Extra('C'),
                Missing('D'),
            ]
            with AcceptedLimit(1) | AcceptedMissing():
                raise ValidationError(differences)

        remaining = cm.exception.differences
        self.assertEqual(remaining, [Extra('C')])

        # Test missing-type AND accepted-limit.
        with self.assertRaises(ValidationError) as cm:
            differences = [
                Extra('A'),
                Missing('B'),
                Missing('C'),
            ]
            with AcceptedLimit(1) & AcceptedMissing():  # Accepts only 1 missing.
                raise ValidationError(differences)

        remaining = cm.exception.differences
        self.assertEqual(remaining, [Extra('A'), Missing('C')])

        # Test missing-type OR accepted-limit.
        with self.assertRaises(ValidationError) as cm:
            differences = [
                Extra('A'),
                Missing('B'),
                Extra('C'),
                Missing('D'),
            ]
            with AcceptedLimit(1) | AcceptedSpecific(Extra('A')):
                raise ValidationError(differences)

        remaining = cm.exception.differences
        self.assertEqual(remaining, [Extra('C'), Missing('D')])
