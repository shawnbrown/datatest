# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
import platform
import re
from . import _unittest as unittest
from datatest import _utils


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
