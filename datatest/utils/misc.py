# -*- coding: utf-8 -*-
"""Miscellaneous helper functions."""
from __future__ import absolute_import
import inspect
import os
from sys import version_info as _version_info
from . import collections
from . import decimal
from .itertools import filterfalse


try:
    _basestring = basestring  # For _is_nsiterable(), below.
except NameError:
    _basestring = str

def _is_nsiterable(x):
    """Returns True if *x* is a non-string iterable object."""
    return not isinstance(x, _basestring) and isinstance(x, collections.Iterable)


def _is_sortable(obj):
    """Returns True if *obj* is sortable else returns False."""
    try:
        sorted([obj, obj])
        return True
    except TypeError:
        return False


def _is_consumable(obj):
    """Returns True of *obj* is a consumable iterator or generator."""
    return iter(obj) is iter(obj)


def _unique_everseen(iterable):  # Adapted from itertools recipes.
    """Returns unique elements, preserving order."""
    seen = set()
    seen_add = seen.add
    iterable = filterfalse(seen.__contains__, iterable)
    for element in iterable:
        seen_add(element)
        yield element


def _make_decimal(d):
    """Converts number into normalized decimal.Decimal object."""
    if isinstance(d, float):
        d = str(d)
    d = decimal.Decimal(d)

    if d == d.to_integral():                   # Remove_exponent (from official
        return d.quantize(decimal.Decimal(1))  # docs: 9.4.10. Decimal FAQ).
    return d.normalize()


def _make_token(name, description=None):
    """Return a new object instance to use as a symbol for representing
    an entity that cannot be used directly because of some logical
    reason or implementation detail.

    * DataQuery uses a token for the result data when optimizing
      queries because the result does not exist until the query is
      actually executed.
    * _get_error() uses a token to build an appropriate error when
      objects normally required for processing are not found.
    * DataError uses a token to compare float('nan') objects because
      they are not considered to be equal when directly compared.
    """
    class TOKEN(object):
        def __repr__(self):
            return '<{0}>'.format(name)
    TOKEN.description = description
    return TOKEN()


def _get_arg_lengths(func):
    """Returns a two-tuple containing the number of positional arguments
    as the first item and the number of variable positional arguments as
    the second item.
    """
    try:
        funcsig = inspect.signature(func)
        params_dict = funcsig.parameters
        parameters = params_dict.values()
        args_type = (inspect._POSITIONAL_OR_KEYWORD, inspect._POSITIONAL_ONLY)
        args = [x for x in parameters if x.kind in args_type]
        vararg = [x for x in parameters if x.kind == inspect._VAR_POSITIONAL]
        vararg = vararg.pop() if vararg else None
    except AttributeError:
        try:
            try:  # For Python 3.2 and earlier.
                args, vararg = inspect.getfullargspec(func)[:2]
            except AttributeError:  # For Python 2.7 and earlier.
                args, vararg = inspect.getargspec(func)[:2]
        except TypeError:     # In 3.2 and earlier, raises TypeError
            raise ValueError  # but 3.3 and later raise a ValueError.
    return (len(args), (1 if vararg else 0))


if _version_info[:2] == (3, 4):  # For version 3.4 only!
    _builtin_objects = set([
        abs, all, any, ascii, bin, bool, bytearray, bytes, callable, chr,
        classmethod, compile, complex, delattr, dict, dir, divmod, enumerate,
        eval, filter, float, format, frozenset, getattr, globals, hasattr,
        hash, help, hex, id, input, int, isinstance, issubclass, iter, len,
        list, locals, map, max, memoryview, min, next, object, oct, open, ord,
        pow, property, range, repr, reversed, round, set, setattr, slice,
        sorted, staticmethod, str, sum, super, tuple, type, vars, zip,
        __import__,
    ])
    try:
        eval('_builtin_objects.add(exec)')   # Using eval prevents SyntaxError
        eval('_builtin_objects.add(print)')  # when parsing in 2.7 and earlier.
    except SyntaxError:
        pass
    _get_arg_lengths_orig = _get_arg_lengths
    def _get_arg_lengths(func):
        # In Python 3.4, an empty signature is returned for built-in
        # functions and types--but this is wrong! If this happens,
        # an error should be raised.
        lengths = _get_arg_lengths_orig(func)
        if lengths == (0, 0) and func in _builtin_objects:
            raise ValueError('cannot get lengths of builtin callables')
        return lengths


def _expects_multiple_params(func):
    """Returns True if *func* accepts multiple positional arguments and
    returns False if it accepts one or zero arguments.

    Returns None if the number of arguments cannot be determined--this
    is usually the case for built-in functions and types.
    """
    try:
        arglen, vararglen = _get_arg_lengths(func)
    except ValueError:
        return None
    return (arglen > 1) or (vararglen > 0)
