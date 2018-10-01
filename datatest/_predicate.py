# -*- coding: utf-8 -*-
import re
from ._compatibility.builtins import *
from ._compatibility import abc
from ._utils import regex_types
from .difference import BaseDifference


class MatcherBase(abc.ABC):
    """Base class for objects that implement rich predicate matching."""
    @abc.abstractmethod
    def __repr__(self):
        return super(MatcherBase, self).__repr__()


class MatcherObject(MatcherBase):
    """Wrapper to call *function* when evaluating the '==' operator."""
    def __init__(self, function, repr_string):
        self._func = function
        self._repr = repr_string

    def __eq__(self, other):
        return self._func(other)

    def __ne__(self, other):  # <- For Python 2.x compatibility.
        return not self.__eq__(other)

    def __repr__(self):
        return self._repr


class MatcherTuple(MatcherBase, tuple):
    """Wrapper to mark tuples that contain one or more MatcherObject
    instances.
    """
    pass


def _check_type(type_, value):
    """Return true if *value* is an instance of the specified type
    or if *value* is the specified type.
    """
    return value is type_ or isinstance(value, type_)


def _check_callable(func, value):
    """Return true if func(value) returns is true or if *func* is
    *value*.
    """
    return value is func or func(value)


def _check_wildcard(value):
    """Always returns true."""
    return True


def _check_truthy(value):
    """Return true if *value* is truthy."""
    return bool(value)


def _check_falsy(value):
    """Return true if *value* is falsy."""
    return not bool(value)


def _check_regex(regex, value):
    """Return true if *value* matches regex."""
    try:
        return regex.search(value) is not None
    except TypeError:
        if value is regex:
            return True  # <- EXIT!

        value_repr = repr(value)
        if len(value_repr) > 45:
            value_repr = value_repr[:42] + '...'
        msg = 'expected string or bytes-like object, got {0}: {1}'
        exc = TypeError(msg.format(value.__class__.__name__, value_repr))
        exc.__cause__ = None
        raise exc


def _check_set(set_, value):
    """Return true if *value* is a member of the given set or if
    the *value* is equal to the given set."""
    return value in set_ or value == set_


def _get_matcher_parts(obj):
    """Return a 2-tuple containing a handler function (to check for
    matches) and a string (to use for displaying a user-readable
    value). Return None if *obj* can be matched with the "==" operator
    and requires no other special handling.
    """
    if isinstance(obj, type):
        pred_handler = lambda x: _check_type(obj, x)
        repr_string = getattr(obj, '__name__', repr(obj))
    elif callable(obj):
        pred_handler = lambda x: _check_callable(obj, x)
        repr_string = getattr(obj, '__name__', repr(obj))
    elif obj is Ellipsis:
        pred_handler = _check_wildcard  # <- Matches everything.
        repr_string = '...'
    elif obj is True:
        pred_handler = _check_truthy
        repr_string = 'True'
    elif obj is False:
        pred_handler = _check_falsy
        repr_string = 'False'
    elif isinstance(obj, regex_types):
        pred_handler = lambda x: _check_regex(obj, x)
        repr_string = 're.compile({0!r})'.format(obj.pattern)
    elif isinstance(obj, set):
        pred_handler = lambda x: _check_set(obj, x)
        repr_string = repr(obj)
    else:
        return None

    return pred_handler, repr_string


def _get_matcher_or_original(obj):
    parts = _get_matcher_parts(obj)
    if parts:
        return MatcherObject(*parts)
    return obj


def get_matcher(obj):
    """Return an object suitable for comparing against other objects
    using the "==" operator.

    If special comparison handling is implemented, a MatcherObject or
    MatcherTuple will be returned. If the object is already suitable
    for this purpose, the original object will be returned unchanged.
    """
    if isinstance(obj, tuple):
        matcher = tuple(_get_matcher_or_original(x) for x in obj)
        for x in matcher:
            if isinstance(x, MatcherBase):
                return MatcherTuple(matcher)  # <- Wrapper.
        return obj  # <- Orignal reference.

    return _get_matcher_or_original(obj)


class Predicate(object):
    """Returns a callable object that can be used as a functional
    predicate.
    """
    def __init__(self, obj):
        if isinstance(obj, Predicate):
            self._pred_handler = obj._pred_handler
            self._repr_string = obj._repr_string
            self._inverted = obj._inverted
        else:
            matcher = get_matcher(obj)
            self._pred_handler = matcher.__eq__
            self._repr_string = repr(matcher)
            self._inverted = False

    def __call__(self, other):
        result = self._pred_handler(other)
        if self._inverted:
            return not result
        return result

    def __invert__(self):
        new_pred = self.__class__(self)
        new_pred._inverted = not self._inverted
        return new_pred

    def __repr__(self):
        cls_name = self.__class__.__name__
        inverted = '~' if self._inverted else ''
        return '{0}{1}({2})'.format(inverted, cls_name, self._repr_string)
