# -*- coding: utf-8 -*-
"""Miscellaneous helper functions."""
import inspect
from . import collections
from . import decimal


def _is_nscontainer(x):
    """Returns True if *x* is a non-string container object."""
    return not isinstance(x, str) and isinstance(x, collections.Container)


def _is_sortable(obj):
    """Returns True if *obj* is sortable else returns False."""
    try:
        sorted([obj, obj])
        return True
    except TypeError:
        return False


def _make_decimal(d):
    """Converts number into normalized decimal.Decimal object."""
    if isinstance(d, float):
        d = str(d)
    d = decimal.Decimal(d)

    if d == d.to_integral():                   # Remove_exponent (from official
        return d.quantize(decimal.Decimal(1))  # docs: 9.4.10. Decimal FAQ).
    return d.normalize()


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
        try:  # For Python 3.2 and earlier.
            args, vararg = inspect.getfullargspec(func)[:2]
        except AttributeError:  # For Python 2.7 and earlier.
            args, vararg = inspect.getargspec(func)[:2]
    return (len(args), (1 if vararg else 0))


def _expects_multiple_params(func):
    """Returns True if *func* accepts 1 or more positional arguments."""
    arglen, vararglen = _get_arg_lengths(func)
    return (arglen > 1) or (vararglen > 0)
