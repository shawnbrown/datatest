# -*- coding: utf-8 -*-
from __future__ import absolute_import
import platform
from . import _unittest as unittest

from datatest.utils import misc


_pypy2 = (platform.python_implementation() == 'PyPy'
          and platform.python_version_tuple()[0] == '2')


class TestGetArgLengths(unittest.TestCase):
    def test_positional(self):
        def userfunc(a, b, c):
            return True
        args, vararg = misc._get_arg_lengths(userfunc)
        self.assertEqual((args, vararg), (3, 0))

    def test_positional_and_keyword(self):
        def userfunc(a, b, c=True):
            return True
        args, vararg = misc._get_arg_lengths(userfunc)
        self.assertEqual((args, vararg), (3, 0))

    def test_varargs(self):
        def userfunc(*args):
            return True
        args, vararg = misc._get_arg_lengths(userfunc)
        self.assertEqual((args, vararg), (0, 1))

    def test_builtin_type(self):
        with self.assertRaises(ValueError):
            misc._get_arg_lengths(int)

    @unittest.skipIf(_pypy2, 'Built-in functions do work in PyPy 2.')
    def test_builtin_function(self):
        with self.assertRaises(ValueError):
            misc._get_arg_lengths(max)


class TestExpectsMultipleParams(unittest.TestCase):
    def test_one_positional(self):
        def userfunc(a):
            return True
        expects_multiple = misc._expects_multiple_params(userfunc)
        self.assertFalse(expects_multiple)

    def test_multiple_positional(self):
        def userfunc(a, b, c):
            return True
        expects_multiple = misc._expects_multiple_params(userfunc)
        self.assertTrue(expects_multiple)

    def test_varargs(self):
        def userfunc(*args):
            return True
        expects_multiple = misc._expects_multiple_params(userfunc)
        self.assertTrue(expects_multiple)

    def test_builtin_type(self):
        expects_multiple = misc._expects_multiple_params(int)
        self.assertIsNone(expects_multiple)

    @unittest.skipIf(_pypy2, 'Built-in functions do work in PyPy 2.')
    def test_builtin_function(self):
        expects_multiple = misc._expects_multiple_params(max)
        self.assertIsNone(expects_multiple)
