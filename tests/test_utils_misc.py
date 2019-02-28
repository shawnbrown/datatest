# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
import platform
import re
from . import _unittest as unittest
from datatest import _utils
from datatest._utils import IterItems

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


class TestIterItems(unittest.TestCase):
    def test_type_error(self):
        regex = "expected iterable or mapping, got 'int'"
        with self.assertRaisesRegex(TypeError, regex):
            IterItems(123)

    def test_non_exhaustible(self):
        items_list = [('a', 1), ('b', 2)]  # <- Non-exhaustible input.

        items = IterItems(items_list)
        self.assertIs(iter(items), iter(items), msg='exhaustible output')
        self.assertEqual(list(items), items_list)
        self.assertEqual(list(items), [], msg='already exhausted')

    def test_exhaustible(self):
        items_iter = iter([('a', 1), ('b', 2)])  # <- Exhaustible iterator.

        items = IterItems(items_iter)
        self.assertIs(iter(items), iter(items))
        self.assertEqual(list(items), [('a', 1), ('b', 2)])
        self.assertEqual(list(items), [], msg='already exhausted')

    def test_dict(self):
        mapping = {'a': 1, 'b': 2}

        items = IterItems(mapping)
        self.assertEqual(set(items), set([('a', 1), ('b', 2)]))
        self.assertEqual(set(items), set(), msg='already exhausted')

    def test_dictitems(self):
        dic = {'a': 1}

        if hasattr(dic, 'iteritems'):  # <- Python 2
            dic_items = dic.iteritems()

            items = IterItems(dic_items)
            self.assertEqual(list(items), [('a', 1)])
            self.assertEqual(list(items), [], msg='already exhausted')

        dic_items = dic.items()

        items = IterItems(dic_items)
        self.assertEqual(list(items), [('a', 1)])
        self.assertEqual(list(items), [], msg='already exhausted')

    def test_empty_iterable(self):
        empty = iter([])

        items = IterItems(empty)
        self.assertEqual(list(items), [])

    def test_repr(self):
        items = IterItems([1, 2])

        repr_part = repr(iter([])).partition(' ')[0]
        repr_start = 'IterItems({0}'.format(repr_part)
        self.assertTrue(repr(items).startswith(repr_start))

        generator = (x for x in [1, 2])
        items = IterItems(generator)
        self.assertEqual(repr(items), 'IterItems({0!r})'.format(generator))

    def test_subclasshook(self):
        items = IterItems(iter([]))
        self.assertIsInstance(items, IterItems)

        try:
            items = dict([]).iteritems()  # <- For Python 2
        except AttributeError:
            items = dict([]).items()  # <- For Python 3
        self.assertIsInstance(items, IterItems)

        items = enumerate([])
        self.assertIsInstance(items, IterItems)

    def test_virtual_subclass(self):
        class OtherClass(object):
            pass

        oth_cls = OtherClass()

        IterItems.register(OtherClass)  # <- Register virtual subclass.
        self.assertIsInstance(oth_cls, IterItems)
