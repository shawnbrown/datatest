# -*- coding: utf-8 -*-
import re
from ._compatibility.builtins import *
from ._compatibility import abc
from ._utils import regex_types
from .difference import BaseDifference


class PredicateObject(abc.ABC):
    """Base class for objects that implement rich predicate matching."""
    @abc.abstractmethod
    def __repr__(self):
        return super(PredicateObject, self).__repr__()


class PredicateTuple(PredicateObject, tuple):
    """Wrapper to mark tuples that contain one or more PredicateMatcher
    instances.
    """
    pass


class PredicateMatcher(PredicateObject):
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


def _get_matcher(value):
    """Return an object suitable for comparing to other values
    using the "==" operator.

    When special comparison handling is required, returns a
    PredicateMatcher instance. When no special comparison is
    needed, returns the original object unchanged.
    """
    if isinstance(value, type):
        function = lambda x: (x is value) or isinstance(x, value)
        repr_string = getattr(value, '__name__', repr(value))
    elif callable(value):
        def function(x):
            if x is value:
                return True
            result = value(x)
            if isinstance(result, BaseDifference):
                return False
            return result
        repr_string = getattr(value, '__name__', repr(value))
    elif value is Ellipsis:
        function = lambda x: True  # <- Wildcard (matches everything).
        repr_string = '...'
    elif isinstance(value, regex_types):
        def function(x):
            try:
                return x is value or value.search(x) is not None
            except TypeError:
                msg = 'expected string or bytes-like object, got {0}'
                exc = TypeError(msg.format(x.__class__.__name__))
                exc.__cause__ = None
                raise exc
        repr_string = 're.compile({0!r})'.format(value.pattern)
    elif isinstance(value, set):
        function = lambda x: (x in value) or (x == value)
        repr_string = repr(value)
    else:
        return value  # <- Original reference.
    return PredicateMatcher(function, repr_string)


def get_predicate(obj):
    """Return a predicate object suitable for comparing to other
    objects using the "==" operator.

    If the original object is already suitable for this purpose,
    it will be returned unchanged. If special comparison handling
    is implemented, a PredicateObject will be returned instead.
    """
    if isinstance(obj, tuple):
        predicate = tuple(_get_matcher(x) for x in obj)
        for x in predicate:
            if isinstance(x, PredicateObject):
                return PredicateTuple(predicate)  # <- Wrapper.
        return obj  # <- Orignal reference.

    return _get_matcher(obj)
