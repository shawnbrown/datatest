# -*- coding: utf-8 -*-
import datetime
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
    AcceptedKeys,
    AcceptedArgs,
    AcceptedTolerance,
    AcceptedPercent,
    AcceptedFuzzy,
    AcceptedCount,
)


class MinimalAcceptance(BaseAcceptance):  # A minimal subclass for
    def call_predicate(self, item):       # testing--defines three
        return False                      # concrete stubs to satisfy
                                          # abstract method requirement
    def scope(self):                      # of the base class.
        return set(['element'])

    def __repr__(self):
        return super(MinimalAcceptance, self).__repr__()


class TestBaseAcceptance(unittest.TestCase):
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
            @property
            def scope(self):
                return set(['element'])

            def call_predicate(_self, item):
                return isinstance(item[1], Missing)

        class accepted_letter_a(MinimalAcceptance):
            @property
            def scope(self):
                return set(['group'])

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

        acceptance = LogicalAnd(left=self.accepted_missing,
                                right=self.accepted_letter_a)
        self.assertEqual(acceptance.scope, set(['element', 'group']))

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
            'b': [Missing('X'), Missing('Y'), Missing('Y')],
        }

        # Defaults to element-wise scope.
        acceptance = AcceptedDifferences({'a': Missing('X'), 'b': Missing('Y')})
        expected = {'b': Missing('X')}
        self.assertAcceptance(differences, acceptance, expected)

        # Defaults to group-wise scope.
        acceptance = AcceptedDifferences({'a': [Missing('X')], 'b': [Missing('Y')]})
        expected = {'a': Missing('X'), 'b': [Missing('X'), Missing('Y')]}
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

    def test_nonremovable_containers(self):
        """Allowance containers with no remove() method should be
        converted to lists.
        """
        # Mapping vs iter.
        differences = {
            'a': iter([Missing('X'), Missing('X')]),
            'b': iter([Missing('Y'), Missing('X')]),
        }
        acceptance = AcceptedDifferences(iter([Missing('X'), Missing('Y')]))
        expected = {'a': Missing('X')}
        self.assertAcceptance(differences, acceptance, expected)

        # Defaults to element-wise scope.
        differences = {
            'a': iter([Missing('X'), Missing('X')]),
            'b': iter([Missing('Y'), Missing('X')]),
        }
        acceptance = AcceptedDifferences({'a': Missing('X'), 'b': Missing('Y')})
        expected = {'b': Missing('X')}
        self.assertAcceptance(differences, acceptance, expected)

        # Defaults to group-wise scope.
        differences = {
            'a': iter([Missing('X'), Missing('X')]),
            'b': iter([Missing('Y'), Missing('X')]),
        }
        acceptance = AcceptedDifferences({'a': iter([Missing('X')]), 'b': tuple([Missing('Y')])})
        expected = {'a': Missing('X'), 'b': Missing('X')}
        self.assertAcceptance(differences, acceptance, expected)

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
            with AcceptedDifferences(accepted):
                raise ValidationError(differences)

        actual = cm.exception.differences
        self.assertEqual(actual, {'baz': Extra('zzz')})

    def test_scope(self):
        acceptance = AcceptedDifferences(Extra)
        self.assertEqual(acceptance.scope, set(['element']))

        acceptance = AcceptedDifferences(Extra('foo'))
        self.assertEqual(acceptance.scope, set(['element']))

        acceptance = AcceptedDifferences([Extra('foo')], scope='element')
        self.assertEqual(acceptance.scope, set(['element']))

        acceptance = AcceptedDifferences([Extra('foo')])  # Defaults to 'group' scope.
        self.assertEqual(acceptance.scope, set(['group']))

        acceptance = AcceptedDifferences([Extra('foo')], scope='whole')
        self.assertEqual(acceptance.scope, set(['whole']))

        # Mapping of differences defaults to 'group' scope, too.
        acceptance = AcceptedDifferences({'a': Extra('foo')})
        self.assertEqual(acceptance.scope, set(['group']))

    def test_repr(self):
        acceptance = AcceptedDifferences(Extra)
        self.assertEqual(repr(acceptance), 'AcceptedDifferences(Extra)')

        acceptance = AcceptedDifferences(Extra('foo'))
        self.assertEqual(repr(acceptance), "AcceptedDifferences(Extra('foo'))")

        acceptance = AcceptedDifferences([Extra('foo')], scope='element')
        self.assertEqual(repr(acceptance), "AcceptedDifferences([Extra('foo')], scope='element')")

        acceptance = AcceptedDifferences([Extra('foo')])  # Defaults to 'group' scope.
        self.assertEqual(repr(acceptance), "AcceptedDifferences([Extra('foo')])")

        acceptance = AcceptedDifferences([Extra('foo')], scope='whole')
        self.assertEqual(repr(acceptance), "AcceptedDifferences([Extra('foo')], scope='whole')")

        acceptance = AcceptedDifferences({'a': Extra('foo')})
        self.assertEqual(repr(acceptance), "AcceptedDifferences({'a': Extra('foo')})")


class TestAcceptedDifferencesByType(unittest.TestCase):
    """These tests were taken from older AcceptedMissing,
    AcceptedExtra, and AcceptedInvalid acceptances.

    These checks may overlap ones in TestAcceptedDifferences.
    Once the new interface has proven to be an adequate replacement
    for the old interface, the duplicate checks can be removed
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


class TestAcceptedTolerance(unittest.TestCase):
    def setUp(self):
        self.differences = {
            'aaa': Deviation(-1, 16),  # -6.25%
            'bbb': Deviation(+4, 16),  # +25.0%
            'ccc': Deviation(+2, 16),  # +12.5%
        }

    def test_get_deviation_expected_blanks(self):
        func = AcceptedTolerance._get_deviation_expected
        self.assertEqual(func(Invalid('', 0)), (0, 0))
        self.assertEqual(func(Invalid(0, '')), (0, 0))

    def test_get_deviation_expected_missing(self):
        func = AcceptedTolerance._get_deviation_expected
        self.assertEqual(func(Missing(2)), (-2, 2))
        self.assertEqual(func(Missing(-2)), (2, -2))
        self.assertEqual(func(Missing(0)), (0, 0))

        with self.assertRaises(TypeError):
            func(Missing((1, 2)))

        with self.assertRaises(TypeError):
            func(Missing('abc'))

    def test_get_deviation_expected_extra_or_single_arg_invalid(self):
        """Extra and single-argument Invalid differences should be
        treated the same.
        """
        func = AcceptedTolerance._get_deviation_expected

        self.assertEqual(func(Extra(2)), (2, 0))
        self.assertEqual(func(Invalid(2)), (2, 0))

        self.assertEqual(func(Extra(-2)), (-2, 0))
        self.assertEqual(func(Invalid(-2)), (-2, 0))

        self.assertEqual(func(Extra(0)), (0, 0))
        self.assertEqual(func(Invalid(0)), (0, 0))

        with self.assertRaises(TypeError):
            func(Extra((1, 2)))

        with self.assertRaises(TypeError):
            func(Invalid((1, 2)))

        with self.assertRaises(TypeError):
            func(Extra('abc'))

        with self.assertRaises(TypeError):
            func(Invalid('abc'))

    def test_get_deviation_expected_invalid_two_args(self):
        """Two-argument Invalid differences are used to make a
        deviation value.
        """
        func = AcceptedTolerance._get_deviation_expected
        self.assertEqual(func(Invalid(5, 7)), (-2, 7))
        self.assertEqual(func(Invalid(7, 5)), (+2, 5))
        self.assertEqual(func(Invalid(0, '')), (0, 0))
        self.assertEqual(func(Invalid(None, 0)), (0, 0))
        self.assertEqual(func(Invalid(0, None)), (0, 0))

        with self.assertRaises(TypeError):
            func(Invalid((1,), (2,)))

        with self.assertRaises(TypeError):
            func(Invalid('abc', 'def'))

        # Test non-numeric but compatible.
        date = Invalid(datetime.datetime(1989, 2, 24, hour=10, minute=30),
                           datetime.datetime(1989, 2, 24, hour=11, minute=30))
        self.assertEqual(func(date), (datetime.timedelta(hours=-1), datetime.datetime(1989, 2, 24, hour=11, minute=30)))

    def test_get_deviation_expected_duck_typing(self):
        """If it looks like a Deviation, it should be treated like a
        Deviation.
        """
        func = AcceptedTolerance._get_deviation_expected

        # Define a non-deviation class that "looks" like a deviation.
        class DeviationLike(BaseDifference):
            def __init__(self, a, b):
                self.deviation = a
                self.expected = b

            @property
            def args(self):
                return (self.expected, self.deviation)

        self.assertEqual(func(DeviationLike(-3, 9)), (-3, 9))

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

    def test_malformed_arguments(self):
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
            raise ValidationError(Invalid('', 0))

        with AcceptedTolerance(0):  # <- Pass without failure.
            raise ValidationError(Invalid(0, ''))

    def test_NaN_values(self):
        with self.assertRaises(ValidationError):  # <- NaN values should not be caught!
            with AcceptedTolerance(0):
                raise ValidationError(Deviation(float('nan'), 0))

    def test_nonnumeric_but_compatible(self):
        with self.assertRaises(ValidationError) as cm:
            with AcceptedTolerance(datetime.timedelta(hours=2)):  # <- Accepts +/- 2 hours.
                raise ValidationError([
                    Invalid(datetime.datetime(1989, 2, 24, hour=10, minute=30),
                            datetime.datetime(1989, 2, 24, hour=11, minute=30)),
                    Invalid(datetime.datetime(1989, 2, 24, hour=15, minute=10),
                            datetime.datetime(1989, 2, 24, hour=11, minute=30))
                ])
        remaining = cm.exception.differences
        self.assertEqual(remaining, [Invalid(datetime.datetime(1989, 2, 24, 15, 10),
                                             expected=datetime.datetime(1989, 2, 24, 11, 30))])

    def test_repr(self):
        acceptance = AcceptedTolerance(0.5)
        self.assertEqual(repr(acceptance), 'AcceptedTolerance(0.5)')

        acceptance = AcceptedTolerance(0.5, msg='some message')
        self.assertEqual(repr(acceptance), "AcceptedTolerance(0.5, msg='some message')")

        acceptance = AcceptedTolerance(-0.25, 0.5)
        self.assertEqual(repr(acceptance), 'AcceptedTolerance(lower=-0.25, upper=0.5)')


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
                Invalid(None, 0),
                Invalid('', 0),
            ])

        # Test diffs that can not be accepted as percentages.
        with self.assertRaises(ValidationError) as cm:
            with AcceptedPercent(2.00):  # <- Accepts +/- 200%.
                raise ValidationError([
                    Invalid(None, 0),             # 0%
                    Invalid(0, None),             # 0%
                    Deviation(+2, 0),             # Can not be accepted by percent.
                    Invalid(+2, None),            # Can not be accepted by percent.
                    Deviation(float('nan'), 16),  # Not a number.
                ])
        actual = cm.exception.differences
        expected = [
            Deviation(+2, 0),             # Can not be accepted by percent.
            Invalid(+2, None),            # Can not be accepted by percent.
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

    def test_extra_deviation_percent(self):
        with self.assertRaises(ValidationError) as cm:
            with AcceptedPercent(2.0):  # <- Accepts +/- 200%.
                raise ValidationError([
                    Extra(-1),  # <- Rejected: Can not be accepted by percent.
                    Extra(0),   # <- ACCEPTED!
                    Extra(2),   # <- Rejected: Can not be accepted by percent.
                ])
        remaining = cm.exception.differences
        self.assertEqual(remaining, [Extra(-1), Extra(2)])

    def test_missing_deviation_percent(self):
        with self.assertRaises(ValidationError) as cm:
            with AcceptedPercent(1.0):  # <- Accepts +/- 100%.
                raise ValidationError([
                    Missing(-1),  # <- ACCEPTED!
                    Missing(0),   # <- ACCEPTED!
                    Missing(2),   # <- ACCEPTED!
                    Missing((1, 2)),  # <- Rejected: Wrong type.
                    Missing('abc'),   # <- Rejected: Wrong type.
                ])
        remaining = cm.exception.differences
        self.assertEqual(remaining, [Missing((1, 2)), Missing('abc')])

    def test_invalid_deviation_single_arg_percent(self):
        # Check error percent.
        with self.assertRaises(ValidationError) as cm:
            with AcceptedPercent(2.0):  # <- Accepts +/- 200%.
                raise ValidationError([
                    Invalid(-1),  # <- Rejected: Can not be accepted by percent.
                    Invalid(0),   # <- ACCEPTED!
                    Invalid(2),   # <- Rejected: Can not be accepted by percent.
                ])
        remaining = cm.exception.differences
        self.assertEqual(remaining, [Invalid(-1), Invalid(2)])

    def test_invalid_deviation_multiple_args_percent(self):
        with self.assertRaises(ValidationError) as cm:
            with AcceptedPercent(0.5):  # <- Accepts +/- 50%.
                raise ValidationError([
                    Invalid(50, 100),   # <- ACCEPTED: -50% deviation.
                    Invalid(150, 100),  # <- ACCEPTED: +50% deviation.
                    Invalid(0.5, 0),    # <- Rejected: Can not be accepted by percent.
                    Invalid(4, 2),      # <- Rejected: +100% is outside range.
                ])
        remaining = cm.exception.differences
        self.assertEqual(remaining, [Invalid(0.5, 0), Invalid(4, 2)])

    def test_percent_error(self):
        # Test "tolerance" syntax.
        with self.assertRaises(ValidationError) as cm:
            with AcceptedPercent(0.2):  # <- Accepts +/- 20%.
                raise ValidationError(self.differences)
        remaining = cm.exception.differences
        self.assertEqual(remaining, {'bbb': Deviation(+4, 16)})

        # Test "upper/lower" syntax.
        with self.assertRaises(ValidationError) as cm:
            with AcceptedPercent(0.0, 0.3):  # <- Accepts from 0 to 30%.
                raise ValidationError(self.differences)
        result_diffs = cm.exception.differences
        self.assertEqual({'aaa': Deviation(-1, 16)}, result_diffs)

    def test_percent_empty_value_handling(self):
        # Test empty deviation cases--should pass without error.
        with AcceptedPercent(0):  # <- Accepts empty deviations only.
            raise ValidationError([
                Invalid(None, 0),
                Invalid('', 0),
            ])

        # Test diffs that can not be accepted as percentages.
        with self.assertRaises(ValidationError) as cm:
            with AcceptedPercent(2.00):  # <- Accepts +/- 200%.
                raise ValidationError([
                    Invalid(None, 0),             # 0%
                    Invalid(0, None),             # 0%
                    Deviation(+2, 0),             # Can not be accepted by percent.
                    Invalid(+2, None),            # Can not be accepted by percent.
                    Deviation(float('nan'), 16),  # Not a number.
                ])
        actual = cm.exception.differences
        expected = [
            Deviation(+2, 0),             # Can not be accepted by percent.
            Invalid(2, None),             # Can not be accepted by percent.
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


class TestAcceptedCount(unittest.TestCase):
    def test_bad_arg(self):
        """An old version of AcceptedCount() used to support dict
        arguments but this behavior has been removed. It should now
        raise a TypeError.
        """
        with self.assertRaises(TypeError):
            AcceptedCount(dict())

    def test_under_limit(self):
        with AcceptedCount(3):  # <- Accepts 3 and there are only 2.
            raise ValidationError([Extra('xxx'), Missing('yyy')])

        with AcceptedCount(3):  # <- Accepts 3 and there are only 2.
            raise ValidationError({'foo': Extra('xxx'), 'bar': Missing('yyy')})

    def test_at_limit(self):
        with AcceptedCount(2):  # <- Accepts 2 and there are 2.
            raise ValidationError([Extra('xxx'), Missing('yyy')])

        with AcceptedCount(3):  # <- Accepts 2 and there are 2.
            raise ValidationError({'foo': Extra('xxx'), 'bar': Missing('yyy')})

    def test_over_limit(self):
        with self.assertRaises(ValidationError) as cm:
            with AcceptedCount(1):  # <- Accepts 1 but there are 2.
                raise ValidationError([Extra('xxx'), Missing('yyy')])

        remaining = list(cm.exception.differences)
        self.assertEqual(remaining, [Missing('yyy')])

        with self.assertRaises(ValidationError) as cm:
            with AcceptedCount(1):  # <- Accepts 1 and there are 2.
                raise ValidationError({'foo': Extra('xxx'), 'bar': Missing('yyy')})

        remaining = cm.exception.differences
        self.assertIsInstance(remaining, Mapping)
        self.assertEqual(len(remaining), 1)

    def test_scope(self):
        with self.assertRaises(ValidationError) as cm:
            with AcceptedCount(2, scope='group'):  # <- Accepts 2 per group.
                raise ValidationError({
                    'foo': [Extra('xxx'), Extra('yyy')],
                    'bar': [Missing('xxx'), Missing('yyy')],
                    'baz': [Invalid('xxx'), Invalid('yyy'), Invalid('zzz')],
                })

        remaining = cm.exception.differences
        self.assertEqual(remaining, {'baz': Invalid('zzz')})

    def test_repr(self):
        acceptance = AcceptedCount(2)
        self.assertEqual(repr(acceptance), "AcceptedCount(2)")

        acceptance = AcceptedCount(2, msg='Some message.')
        self.assertEqual(repr(acceptance), "AcceptedCount(2, msg='Some message.')")

        acceptance = AcceptedCount(2, scope='group')
        self.assertEqual(repr(acceptance), "AcceptedCount(2, scope='group')")


class TestUniversalComposability(unittest.TestCase):
    """Test that acceptances are composable with acceptances of the
    same type as well as all other acceptance types.
    """
    def setUp(self):
        ntup = namedtuple('ntup', ('cls', 'args', 'scope'))
        self.acceptances = [
            ntup(cls=AcceptedDifferences, args=(Invalid('A'),),        scope=set(['element'])),
            ntup(cls=AcceptedDifferences, args=([Invalid('A')],),      scope=set(['group'])),
            ntup(cls=AcceptedDifferences, args=({'X': [Invalid('A')]},), scope=set(['group'])),
            ntup(cls=AcceptedDifferences, args=([Invalid('A')], None, 'whole'), scope=set(['whole'])),
            ntup(cls=AcceptedKeys,      args=(lambda args: True,),     scope=set(['element'])),
            ntup(cls=AcceptedArgs,      args=(lambda *args: True,),    scope=set(['element'])),
            ntup(cls=AcceptedTolerance, args=(10,),                    scope=set(['element'])),
            ntup(cls=AcceptedPercent,   args=(0.05,),                  scope=set(['element'])),
            ntup(cls=AcceptedFuzzy,     args=tuple(),                  scope=set(['element'])),
            ntup(cls=AcceptedCount,     args=(4,),                     scope=set(['whole'])),
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

    def test_scope(self):
        for x in self.acceptances:
            instance = x.cls(*x.args)  # <- Initialize class instance.
            actual = instance.scope
            expected = x.scope
            self.assertIsInstance(actual, frozenset)
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
            self.assertIsInstance(composed.scope, frozenset)
            self.assertEqual(composed.scope, (a.scope | b.scope))

        for a, b in combinations:
            composed = a & b  # <- Intersection!
            self.assertIsInstance(composed, IntersectedAcceptance)
            self.assertIsInstance(composed.scope, frozenset)
            self.assertEqual(composed.scope, (a.scope | b.scope), 'UNION of component scopes')

        # The composed scope should always be the UNION of component
        # scopes (regardless of whether or not it was composed as a
        # UNION or an INTERSECTION).

    def test_integration_examples(self):
        # Test acceptance of +/- 2 OR +/- 6%.
        with self.assertRaises(ValidationError) as cm:
            differences = [
                Deviation(+2, 1),   # 200%
                Deviation(+4, 8),   #  50%
                Deviation(+8, 32),  #  25%
            ]
            with AcceptedTolerance(2) | AcceptedPercent(0.25):
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
            with AcceptedDifferences(Missing) & AcceptedArgs(lambda x: x == 'A'):
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
            with AcceptedCount(1) | AcceptedDifferences(Missing):
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
            with AcceptedCount(1) & AcceptedDifferences(Missing):  # Accepts only 1 missing.
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
            with AcceptedCount(1) | AcceptedDifferences(Extra('A')):
                raise ValidationError(differences)

        remaining = cm.exception.differences
        self.assertEqual(remaining, [Extra('C'), Missing('D')])

    def assertPrecedenceLess(self, a, b):
        if not BaseAcceptance._get_precedence(a) < BaseAcceptance._get_precedence(b):
            message = 'precedence of %r not less than %r' % (a.scope, b.scope)
            self.fail(message)

    def test_precedence_relations(self):
        """Should implement specified precedence order for element (e),
        group (g), and whole (w) scoped acceptances:

            e < ge < g < we < wge < wg < w
        """
        element = AcceptedDifferences([Missing(1)], scope='element')
        group = AcceptedDifferences([Missing(1)], scope='group')
        whole = AcceptedDifferences([Missing(1)], scope='whole')

        self.assertPrecedenceLess(
            element,
            (group | element),
        )
        self.assertPrecedenceLess(
            (group | element),
            group,
        )
        self.assertPrecedenceLess(
            group,
            (whole | element),
        )
        self.assertPrecedenceLess(
            (whole | element),
            (whole | group | element),
        )
        self.assertPrecedenceLess(
            (whole | group | element),
            (whole | group),
        )
        self.assertPrecedenceLess(
            (whole | group),
            whole,
        )
