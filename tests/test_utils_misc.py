# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
import platform
import re
from . import _unittest as unittest

from datatest import _utils
from datatest._utils import get_predicate


class TestAdaptedCallable(unittest.TestCase):
    def test_equality(self):
        def divisible3or5(x):  # <- Helper function.
            return (x % 3 == 0) or (x % 5 == 0)
        adapted = get_predicate._adapt(divisible3or5)

        self.assertFalse(adapted == 1)
        self.assertFalse(adapted == 2)
        self.assertTrue(adapted == 3)
        self.assertFalse(adapted == 4)
        self.assertTrue(adapted == 5)
        self.assertTrue(adapted == 6)

    def test_error(self):
        def fails_internally(x):  # <- Helper function.
            raise TypeError('raising an error')
        adapted = get_predicate._adapt(fails_internally)

        with self.assertRaises(TypeError):
            self.assertFalse(adapted == 'abc')

    def test_identity(self):
        def always_false(x):
            return False
        adapted = get_predicate._adapt(always_false)

        self.assertTrue(adapted ==always_false)

    def test_identity_with_error(self):
        def fails_internally(x):  # <- Helper function.
            raise TypeError('raising an error')
        adapted = get_predicate._adapt(fails_internally)

        self.assertTrue(adapted == fails_internally)

    def test_repr(self):
        def userfunc(x):
            return True
        adapted = get_predicate._adapt(userfunc)
        self.assertEqual(repr(adapted), 'userfunc')

        userlambda = lambda x: True
        adapted = get_predicate._adapt(userlambda)
        self.assertEqual(repr(adapted), '<lambda>')


class TestAdaptedRegex(unittest.TestCase):
    def test_equality(self):
        adapted = get_predicate._adapt(re.compile('(Ch|H)ann?ukk?ah?'))

        self.assertTrue(adapted == 'Happy Hanukkah')
        self.assertTrue(adapted == 'Happy Chanukah')
        self.assertFalse(adapted == 'Merry Christmas')

    def test_error(self):
        adapted = get_predicate._adapt(re.compile('abc'))

        with self.assertRaises(TypeError):
            self.assertFalse(adapted == 123)  # Regex fails with TypeError.

    def test_identity(self):
        regex = re.compile('abc')
        adapted = get_predicate._adapt(regex)

        self.assertTrue(adapted == regex)

    def test_repr(self):
        adapted = get_predicate._adapt(re.compile('abc'))

        self.assertEqual(repr(adapted), "re.compile('abc')")


class TestAdaptedSet(unittest.TestCase):
    def test_equality(self):
        adapted = get_predicate._adapt(set(['a', 'e', 'i', 'o', 'u']))
        self.assertTrue(adapted == 'a')
        self.assertFalse(adapted == 'x')

    def test_whole_set_equality(self):
        adapted = get_predicate._adapt(set(['a', 'b', 'c']))
        self.assertTrue(adapted == set(['a', 'b', 'c']))

    def test_repr(self):
        adapted = get_predicate._adapt(set(['a']))
        self.assertEqual(repr(adapted), repr(set(['a'])))


class TestAdaptedEllipsisWildcard(unittest.TestCase):
    def test_equality(self):
        adapted = get_predicate._adapt(Ellipsis)

        self.assertTrue(adapted == 1)
        self.assertTrue(adapted == object())
        self.assertTrue(adapted == None)

    def test_repr(self):
        adapted = get_predicate._adapt(Ellipsis)

        self.assertEqual(repr(adapted), '...')


class TestGetPredicate(unittest.TestCase):
    def test_single_object(self):
        predicate = get_predicate(1)

        self.assertTrue(predicate(1))
        self.assertFalse(predicate(2))
        self.assertEqual(predicate.__name__, '1')

    def test_tuple_of_objects(self):
        predicate = get_predicate(('A', 1))

        self.assertTrue(predicate(('A', 1)))
        self.assertFalse(predicate(('A', 2)))
        self.assertFalse(predicate(('B', 1)))
        self.assertEqual(predicate.__name__, "('A', 1)")

    def test_tuple_of_all_adapter_options(self):
        def mycallable(x):  # <- Helper function.
            return x == '_'

        myregex = re.compile('_')

        myset = set(['_'])

        predicate = get_predicate(
            (mycallable,  myregex, myset, '_', Ellipsis)
        )

        self.assertTrue(predicate(('_', '_', '_', '_', '_')))   # <- Passes all conditions.
        self.assertFalse(predicate(('X', '_', '_', '_', '_')))  # <- Callable returns False.
        self.assertFalse(predicate(('_', 'X', '_', '_', '_')))  # <- Regex has no match.
        self.assertFalse(predicate(('_', '_', 'X', '_', '_')))  # <- Not in set.
        self.assertFalse(predicate(('_', '_', '_', 'X', '_')))  # <- Does not equal string.
        self.assertTrue(predicate(('_', '_', '_', '_', 'X')))   # <- Passes all conditions (wildcard).

        expected = "(mycallable, re.compile('_'), {0!r}, '_', ...)".format(myset)
        self.assertEqual(predicate.__name__, expected)


_PYPY2 = (platform.python_implementation() == 'PyPy'
          and platform.python_version_tuple()[0] == '2')


class TestGetArgLengths(unittest.TestCase):
    def test_positional(self):
        def userfunc(a, b, c):
            return True
        args, vararg = _utils._get_arg_lengths(userfunc)
        self.assertEqual((args, vararg), (3, 0))

    def test_positional_and_keyword(self):
        def userfunc(a, b, c=True):
            return True
        args, vararg = _utils._get_arg_lengths(userfunc)
        self.assertEqual((args, vararg), (3, 0))

    def test_varargs(self):
        def userfunc(*args):
            return True
        args, vararg = _utils._get_arg_lengths(userfunc)
        self.assertEqual((args, vararg), (0, 1))

    def test_builtin_type(self):
        with self.assertRaises(ValueError):
            _utils._get_arg_lengths(int)

    def test_builtin_function(self):
        if _PYPY2:
            args, vararg = _utils._get_arg_lengths(max)  # Built-in functions
            self.assertEqual((args, vararg), (0, 1))   # only work in PyPy 2.
        else:
            with self.assertRaises(ValueError):
                _utils._get_arg_lengths(max)


class TestExpectsMultipleParams(unittest.TestCase):
    def test_zero(self):
        def userfunc():
            return True
        expects_multiple = _utils._expects_multiple_params(userfunc)
        self.assertIs(expects_multiple, False)

    def test_one_positional(self):
        def userfunc(a):
            return True
        expects_multiple = _utils._expects_multiple_params(userfunc)
        self.assertIs(expects_multiple, False)

    def test_multiple_positional(self):
        def userfunc(a, b, c):
            return True
        expects_multiple = _utils._expects_multiple_params(userfunc)
        self.assertIs(expects_multiple, True)

    def test_varargs(self):
        def userfunc(*args):
            return True
        expects_multiple = _utils._expects_multiple_params(userfunc)
        self.assertIs(expects_multiple, True)

    def test_builtin_type(self):
        expects_multiple = _utils._expects_multiple_params(int)
        self.assertIsNone(expects_multiple)

    def test_builtin_function(self):
        if _PYPY2:
            expects_multiple = _utils._expects_multiple_params(max)  # Built-in functions
            self.assertIs(expects_multiple, True)                  # only work in PyPy 2.
        else:
            expects_multiple = _utils._expects_multiple_params(max)
            self.assertIsNone(expects_multiple)
