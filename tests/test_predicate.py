#!/usr/bin/env python
# -*- coding: utf-8 -*-
from . import _unittest as unittest
import re

from datatest._predicate import (
    _check_type,
    _check_callable,
    _check_wildcard,
    _check_truthy,
    _check_falsy,
    _check_nan,
    _check_regex,
    _check_set,
    _get_matcher_parts,
    get_matcher,
    MatcherBase,
    MatcherObject,
    MatcherTuple,
    Predicate,
)


class TestCheckType(unittest.TestCase):
    def test_isinstance(self):
        function = lambda x: _check_type(int, x)
        self.assertTrue(function(0))
        self.assertTrue(function(1))
        self.assertFalse(function(0.0))
        self.assertFalse(function(1.0))

    def test_is_type(self):
        self.assertTrue(_check_type(int, int))


class TestCheckCallable(unittest.TestCase):
    def test_function(self):
        def divisible3or5(x):  # <- Helper function.
            return (x % 3 == 0) or (x % 5 == 0)

        function = lambda x: _check_callable(divisible3or5, x)
        self.assertFalse(function(1))
        self.assertFalse(function(2))
        self.assertTrue(function(3))
        self.assertFalse(function(4))
        self.assertTrue(function(5))
        self.assertTrue(function(6))

    def test_error(self):
        def fails_internally(x):  # <- Helper function.
            raise TypeError('raising an error')

        function = lambda x: _check_callable(fails_internally, x)
        with self.assertRaises(TypeError):
            self.assertFalse(function('abc'))

    def test_identity(self):
        def always_false(x):  # <- Helper function.
            return False

        function = lambda x: _check_callable(always_false, x)
        self.assertTrue(function(always_false))

    def test_identity_with_error(self):
        def fails_internally(x):  # <- Helper function.
            raise TypeError('raising an error')

        function = lambda x: _check_callable(fails_internally, x)
        self.assertTrue(function(fails_internally))


class TestCheckWildcard(unittest.TestCase):
    def test_always_true(self):
        self.assertTrue(_check_wildcard(1))
        self.assertTrue(_check_wildcard(object()))
        self.assertTrue(_check_wildcard(None))


class TestCheckTruthy(unittest.TestCase):
    def test_matches(self):
        self.assertTrue(_check_truthy('x'))
        self.assertTrue(_check_truthy(1.0))
        self.assertTrue(_check_truthy([1]))
        self.assertTrue(_check_truthy(range(1)))

    def test_nonmatches(self):
        self.assertFalse(_check_truthy(''))
        self.assertFalse(_check_truthy(0.0))
        self.assertFalse(_check_truthy([]))
        self.assertFalse(_check_truthy(range(0)))


class TestCheckFalsy(unittest.TestCase):
    def test_matches(self):
        self.assertTrue(_check_falsy(''))
        self.assertTrue(_check_falsy(0.0))
        self.assertTrue(_check_falsy([]))
        self.assertTrue(_check_falsy(range(0)))

    def test_nonmatches(self):
        self.assertFalse(_check_falsy('x'))
        self.assertFalse(_check_falsy(1.0))
        self.assertFalse(_check_falsy([1]))
        self.assertFalse(_check_falsy(range(1)))


class TestCheckRegex(unittest.TestCase):
    def test_function(self):
        regex = re.compile('(Ch|H)ann?ukk?ah?')
        function = lambda x: _check_regex(regex, x)

        self.assertTrue(function('Happy Hanukkah'))
        self.assertTrue(function('Happy Chanukah'))
        self.assertFalse(function('Merry Christmas'))

    def test_incompatible_types(self):
        regex = re.compile('abc')
        self.assertFalse(_check_regex(regex, 123))
        self.assertFalse(_check_regex(regex, ('a', 'b')))

    def test_identity(self):
        regex = re.compile('abc')
        self.assertTrue(_check_regex(regex, regex))


class TestCheckSet(unittest.TestCase):
    def test_function(self):
        function = lambda x: _check_set(set(['abc', 'def']), x)
        self.assertTrue(function('abc'))
        self.assertFalse(function('xyz'))

    def test_whole_set_equality(self):
        function = lambda x: _check_set(set(['abc', 'def']), x)
        self.assertTrue(function(set(['abc', 'def'])))

    def test_unhashable_check(self):
        function = lambda x: _check_set(set(['abc', 'def']), x)
        self.assertFalse(function(['abc']))
        self.assertFalse(function((1, ['xyz'])))


class TestGetMatcherParts(unittest.TestCase):
    def test_type(self):
        pred_handler, repr_string = _get_matcher_parts(int)
        self.assertTrue(pred_handler(1))
        self.assertFalse(pred_handler(1.0))
        self.assertEqual(repr_string, 'int')

    def test_callable(self):
        def userfunc(x):
            return x == 1
        pred_handler, repr_string = _get_matcher_parts(userfunc)
        self.assertTrue(pred_handler(1))
        self.assertFalse(pred_handler(2))
        self.assertEqual(repr_string, 'userfunc')

        userlambda = lambda x: x == 1
        pred_handler, repr_string = _get_matcher_parts(userlambda)
        self.assertTrue(pred_handler(1))
        self.assertFalse(pred_handler(2))
        self.assertEqual(repr_string, '<lambda>')

    def test_ellipsis_wildcard(self):
        pred_handler, repr_string = _get_matcher_parts(Ellipsis)
        self.assertIs(pred_handler, _check_wildcard)
        self.assertEqual(repr_string, '...')

    def test_truthy(self):
        pred_handler, repr_string = _get_matcher_parts(True)
        self.assertIs(pred_handler, _check_truthy)
        self.assertEqual(repr_string, 'True')

    def test_falsy(self):
        pred_handler, repr_string = _get_matcher_parts(False)
        self.assertIs(pred_handler, _check_falsy)
        self.assertEqual(repr_string, 'False')

    def test_nan(self):
        pred_handler, repr_string = _get_matcher_parts(float('nan'))
        self.assertIs(pred_handler, _check_nan)
        self.assertEqual(repr_string, "float('nan')")

    def test_regex(self):
        regex = re.compile('ab[cd]')

        pred_handler, repr_string = _get_matcher_parts(regex)
        self.assertTrue(pred_handler('abc'))
        self.assertFalse(pred_handler('abe'))
        self.assertEqual(repr_string, "re.compile('ab[cd]')")

    def test_set(self):
        myset = set(['a'])
        pred_handler, repr_string = _get_matcher_parts(myset)
        self.assertTrue(pred_handler('a'))
        self.assertFalse(pred_handler('b'))
        self.assertEqual(repr_string, repr(myset))

    def test_no_special_handling(self):
        self.assertIsNone(_get_matcher_parts(1))
        self.assertIsNone(_get_matcher_parts(0))


class TestMatcherInheritance(unittest.TestCase):
    def test_inheritance(self):
        self.assertTrue(issubclass(MatcherTuple, MatcherBase))
        self.assertTrue(issubclass(MatcherObject, MatcherBase))


class TestGetMatcher(unittest.TestCase):
    def assertIsInstance(self, obj, cls, msg=None):  # New in Python 3.2.
        if not isinstance(obj, cls):
            standardMsg = '%s is not an instance of %r' % (safe_repr(obj), cls)
            self.fail(self._formatMessage(msg, standardMsg))

    def test_single_value(self):
        # Check for MatcherObject wrapping.
        def isodd(x):  # <- Helper function.
            return x % 2 == 1
        matcher = get_matcher(isodd)
        self.assertIsInstance(matcher, MatcherObject)

        # When original is adequate, it should be returned unchanged.
        original = object()
        matcher = get_matcher(original)
        self.assertIs(matcher, original)

    def test_tuple_of_values(self):
        # Check for MatcherTuple wrapping.
        def isodd(x):  # <- Helper function.
            return x % 2 == 1
        matcher = get_matcher((1, isodd))
        self.assertIsInstance(matcher, MatcherTuple)

        # When tuple contains no MatcherObject objects,
        # the original should be returned unchanged.
        original = ('abc', 123)
        matcher = get_matcher(original)
        self.assertIs(matcher, original)

    def test_get_matcher_from_matcher(self):
        original = get_matcher((1, 'abc'))
        matcher = get_matcher(original)
        self.assertIs(matcher, original)

    def test_get_matcher_from_predicate(self):
        predicate = Predicate('abc')
        matcher = get_matcher(predicate)
        self.assertIs(matcher, predicate.matcher)

    def test_integration(self):
        """A small integration test that checks a tuple containing all
        of the different special handling cases.
        """
        def mycallable(x):  # <- Helper function.
            return x == '_'

        myregex = re.compile('_')

        myset = set(['_'])

        matcher = get_matcher(
            (mycallable,  myregex, myset, '_', Ellipsis)
        )

        self.assertTrue(matcher == ('_', '_', '_', '_', '_'))   # <- Passes all conditions.
        self.assertFalse(matcher == ('X', '_', '_', '_', '_'))  # <- Callable returns False.
        self.assertFalse(matcher == ('_', 'X', '_', '_', '_'))  # <- Regex has no match.
        self.assertFalse(matcher == ('_', '_', 'X', '_', '_'))  # <- Not in set.
        self.assertFalse(matcher == ('_', '_', '_', 'X', '_'))  # <- Does not equal string.
        self.assertTrue(matcher == ('_', '_', '_', '_', 'X'))   # <- Passes all conditions (wildcard).

        expected = "(mycallable, re.compile('_'), {0!r}, '_', ...)".format(myset)
        self.assertEqual(repr(matcher), expected)


class TestPredicate(unittest.TestCase):
    def test_predicate_function(self):
        pred = Predicate('abc')
        self.assertTrue(pred('abc'))
        self.assertFalse(pred('def'))
        self.assertFalse(pred(123))

        pred = Predicate(re.compile('^abc$'))
        self.assertTrue(pred('abc'))
        self.assertFalse(pred('def'))
        self.assertFalse(pred(123))

        pred = Predicate(1)
        self.assertTrue(pred(1))
        self.assertFalse(pred(2))
        self.assertFalse(pred('abc'))

        pred = Predicate(('abc', int))
        self.assertTrue(pred(('abc', 1)))
        self.assertFalse(pred(('abc', 1.0)))

        pred = Predicate((str, float('nan')))
        self.assertTrue(pred(('abc', float('nan'))))
        self.assertFalse(pred(('abc', 1.0)))
        self.assertFalse(pred(('abc', 'xyz')))

    def test_inverted_logic(self):
        pred = ~Predicate('abc')
        self.assertFalse(pred('abc'))
        self.assertTrue(pred('def'))

    def test_repr(self):
        pred = Predicate('abc')
        self.assertEqual(repr(pred), "Predicate('abc')")

        pred = ~Predicate('abc')
        self.assertEqual(repr(pred), "~Predicate('abc')")

        pred = Predicate('abc', name='custom_name')
        self.assertEqual(repr(pred), "Predicate('abc', name='custom_name')")

    def test_optional_name(self):
        pred1 = Predicate('abc')  # <- No name arg provided.
        self.assertFalse(hasattr(pred1, '__name__'))

        pred2 = Predicate(pred1)  # <- No name arg inherited from pred1.
        self.assertFalse(hasattr(pred1, '__name__'))

        pred3 = Predicate('abc', name='pred3_name')  # <- Provides name.
        self.assertEqual(pred3.__name__, 'pred3_name')

        pred4 = Predicate(pred3)  # <- Inherits name from pred3.
        self.assertEqual(pred4.__name__, 'pred3_name')

        pred5 = Predicate(pred3, name='pred5_name')  # <- Overrides pred3 name.
        self.assertEqual(pred5.__name__, 'pred5_name')

    def test_str(self):
        pred = Predicate('abc')
        self.assertEqual(str(pred), "'abc'")

        inverted = ~Predicate('abc')
        self.assertEqual(str(inverted), "not 'abc'")

    def test_predicate_from_predicate(self):
        pred1 = Predicate('abc')
        pred2 = Predicate(pred1)
        self.assertIsNot(pred1, pred2, msg='should be different object')
        self.assertIs(pred1.obj, pred2.obj, msg='should keep original reference')
        self.assertEqual(pred1.matcher, pred2.matcher)
        self.assertEqual(pred1._inverted, pred2._inverted)

        from_inverted = Predicate(~Predicate('abc'))
        self.assertTrue(from_inverted._inverted)

    def test_passthrough(self):
        """Callable predicates should return the values provided by
        the given function as-is--the values should not be converted
        to True or False.
        """
        TOKEN = object()

        def divisible_or_token(x):  # <- Helper function.
            if x % 3 == 0:
                return True
            if x % 5 == 0:
                return TOKEN
            return False

        predicate = Predicate(divisible_or_token)
        self.assertEqual(predicate(1), False)
        self.assertEqual(predicate(3), True)
        self.assertIs(predicate(5), TOKEN, msg='TOKEN should be returned, not True.')


if __name__ == '__main__':
    unittest.main()
