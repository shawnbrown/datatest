# -*- coding: utf-8 -*-
import re
from . import _unittest as unittest

from datatest._predicate import _get_matcher
from datatest._predicate import get_predicate
from datatest._predicate import PredicateObject
from datatest._predicate import PredicateTuple
from datatest._predicate import PredicateMatcher

from datatest import Missing


class TestInheritance(unittest.TestCase):
    def test_inheritance(self):
        self.assertTrue(issubclass(PredicateTuple, PredicateObject))
        self.assertTrue(issubclass(PredicateMatcher, PredicateObject))


class TestTypeMatcher(unittest.TestCase):
    def test_isinstance(self):
        matcher = _get_matcher(int)

        self.assertTrue(matcher == 0)
        self.assertTrue(matcher == 1)
        self.assertFalse(matcher == 0.0)
        self.assertFalse(matcher == 1.0)


class TestCallableMatcher(unittest.TestCase):
    def test_equality(self):
        def divisible3or5(x):  # <- Helper function.
            return (x % 3 == 0) or (x % 5 == 0)
        matcher = _get_matcher(divisible3or5)

        self.assertFalse(matcher == 1)
        self.assertFalse(matcher == 2)
        self.assertTrue(matcher == 3)
        self.assertFalse(matcher == 4)
        self.assertTrue(matcher == 5)
        self.assertTrue(matcher == 6)

    def test_error(self):
        def fails_internally(x):  # <- Helper function.
            raise TypeError('raising an error')
        matcher = _get_matcher(fails_internally)

        with self.assertRaises(TypeError):
            self.assertFalse(matcher == 'abc')

    def test_identity(self):
        def always_false(x):
            return False
        matcher = _get_matcher(always_false)

        self.assertTrue(matcher == always_false)

    def test_identity_with_error(self):
        def fails_internally(x):  # <- Helper function.
            raise TypeError('raising an error')
        matcher = _get_matcher(fails_internally)

        self.assertTrue(matcher == fails_internally)

    def test_repr(self):
        def userfunc(x):
            return True
        matcher = _get_matcher(userfunc)
        self.assertEqual(repr(matcher), 'userfunc')

        userlambda = lambda x: True
        matcher = _get_matcher(userlambda)
        self.assertEqual(repr(matcher), '<lambda>')

    def test_returned_difference(self):
        """If predicate function returns a difference object, it
        should count as False.
        """
        def true_or_difference(x):
            return x == 'foo' or Missing(x)
        matcher = _get_matcher(true_or_difference)

        self.assertTrue(matcher == 'foo')
        self.assertFalse(matcher == 'bar')


class TestRegexMatcher(unittest.TestCase):
    def test_equality(self):
        matcher = _get_matcher(re.compile('(Ch|H)ann?ukk?ah?'))

        self.assertTrue(matcher == 'Happy Hanukkah')
        self.assertTrue(matcher == 'Happy Chanukah')
        self.assertFalse(matcher == 'Merry Christmas')

    def test_error(self):
        matcher = _get_matcher(re.compile('abc'))

        with self.assertRaisesRegex(TypeError, "got int: 123"):
            self.assertFalse(matcher == 123)  # Regex fails with TypeError.

        with self.assertRaisesRegex(TypeError, "got tuple: \('a', 'b'\)"):
            self.assertFalse(matcher == ('a', 'b'))

    def test_identity(self):
        regex = re.compile('abc')
        matcher = _get_matcher(regex)

        self.assertTrue(matcher == regex)

    def test_repr(self):
        matcher = _get_matcher(re.compile('abc'))

        self.assertEqual(repr(matcher), "re.compile('abc')")


class TestSetMatcher(unittest.TestCase):
    def test_equality(self):
        matcher = _get_matcher(set(['a', 'e', 'i', 'o', 'u']))

        self.assertTrue(matcher == 'a')
        self.assertFalse(matcher == 'x')

    def test_whole_set_equality(self):
        matcher = _get_matcher(set(['a', 'b', 'c']))

        self.assertTrue(matcher == set(['a', 'b', 'c']))

    def test_repr(self):
        matcher = _get_matcher(set(['a']))

        self.assertEqual(repr(matcher), repr(set(['a'])))


class TestEllipsisWildcardMatcher(unittest.TestCase):
    def test_equality(self):
        matcher = _get_matcher(Ellipsis)

        self.assertTrue(matcher == 1)
        self.assertTrue(matcher == object())
        self.assertTrue(matcher == None)

    def test_repr(self):
        matcher = _get_matcher(Ellipsis)

        self.assertEqual(repr(matcher), '...')


class TestTruthyMatcher(unittest.TestCase):
    def test_equality(self):
        matcher = _get_matcher(True)

        self.assertTrue(matcher == 'x')
        self.assertTrue(matcher == 1.0)
        self.assertTrue(matcher == [1])
        self.assertTrue(matcher == range(1))

        self.assertFalse(matcher == '')
        self.assertFalse(matcher == 0.0)
        self.assertFalse(matcher == [])
        self.assertFalse(matcher == range(0))

    def test_number_one(self):
        matcher = _get_matcher(1)  # <- Should not match True

        self.assertTrue(matcher == 1.0)
        self.assertFalse(matcher == 'x')

    def test_repr(self):
        matcher = _get_matcher(True)

        self.assertEqual(repr(matcher), 'True')


class TestFalsyMatcher(unittest.TestCase):
    def test_equality(self):
        matcher = _get_matcher(False)

        self.assertFalse(matcher == 'x')
        self.assertFalse(matcher == 1.0)
        self.assertFalse(matcher == [1])
        self.assertFalse(matcher == range(1))

        self.assertTrue(matcher == '')
        self.assertTrue(matcher == 0.0)
        self.assertTrue(matcher == [])
        self.assertTrue(matcher == range(0))

    def test_number_zero(self):
        matcher = _get_matcher(0)  # <- Should not match False

        self.assertTrue(matcher == 0.0)
        self.assertFalse(matcher == '')

    def test_repr(self):
        matcher = _get_matcher(False)

        self.assertEqual(repr(matcher), 'False')


class TestGetPredicate(unittest.TestCase):
    def test_single_value(self):
        # Check for PredicateMatcher wrapping.
        def isodd(x):  # <- Helper function.
            return x % 2 == 1
        predicate = get_predicate(isodd)
        self.assertIsInstance(predicate, PredicateMatcher)

        predicate = get_predicate(Ellipsis)
        self.assertIsInstance(predicate, PredicateMatcher)

        predicate = get_predicate(re.compile('abc'))
        self.assertIsInstance(predicate, PredicateMatcher)

        predicate = get_predicate(set([1, 2, 3]))
        self.assertIsInstance(predicate, PredicateMatcher)

        # When original is adequate, it should be returned unchanged.
        original = 123
        predicate = get_predicate(original)
        self.assertIs(predicate, original)

        original = 'abc'
        predicate = get_predicate(original)
        self.assertIs(predicate, original)

        original = ['abc', 123]
        predicate = get_predicate(original)
        self.assertIs(predicate, original)

        original = object()
        predicate = get_predicate(original)
        self.assertIs(predicate, original)

    def test_tuple_of_values(self):
        # Check for PredicateTuple wrapping.
        def isodd(x):  # <- Helper function.
            return x % 2 == 1
        predicate = get_predicate((1, isodd))
        self.assertIsInstance(predicate, PredicateTuple)

        predicate = get_predicate((1, Ellipsis))
        self.assertIsInstance(predicate, PredicateTuple)

        predicate = get_predicate((1, re.compile('abc')))
        self.assertIsInstance(predicate, PredicateTuple)

        predicate = get_predicate((1, set([1, 2, 3])))
        self.assertIsInstance(predicate, PredicateTuple)

        # When tuple contains no PredicateMatcher objects,
        # the original should be returned unchanged.
        original = ('abc', 123)
        predicate = get_predicate(original)
        self.assertIs(predicate, original)

    def test_integration(self):
        def mycallable(x):  # <- Helper function.
            return x == '_'

        myregex = re.compile('_')

        myset = set(['_'])

        predicate = get_predicate(
            (mycallable,  myregex, myset, '_', Ellipsis)
        )

        self.assertTrue(predicate == ('_', '_', '_', '_', '_'))   # <- Passes all conditions.
        self.assertFalse(predicate == ('X', '_', '_', '_', '_'))  # <- Callable returns False.
        self.assertFalse(predicate == ('_', 'X', '_', '_', '_'))  # <- Regex has no match.
        self.assertFalse(predicate == ('_', '_', 'X', '_', '_'))  # <- Not in set.
        self.assertFalse(predicate == ('_', '_', '_', 'X', '_'))  # <- Does not equal string.
        self.assertTrue(predicate == ('_', '_', '_', '_', 'X'))   # <- Passes all conditions (wildcard).

        expected = "(mycallable, re.compile('_'), {0!r}, '_', ...)".format(myset)
        self.assertEqual(repr(predicate), expected)
