# -*- coding: utf-8 -*-
import re
from ._compatibility.builtins import *
from ._compatibility import abc
from ._utils import regex_types


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
    """Wrapper to call *func* when evaluating the '==' operator."""
    def __init__(self, func, repr_string):
        self._func = func
        self._repr = repr_string

    def __eq__(self, other):
        return self._func(other)

    def __repr__(self):
        return self._repr


def _get_matcher(value):
    """Return an object suitable for comparing to other values
    using the "==" operator.

    When special comparison handling is required, returns a
    PredicateMatcher instance. When no special comparison is
    needed, returns the original object unchanged.
    """
    if callable(value):
        func = lambda x: (x is value) or value(x)
        name = getattr(value, '__name__', repr(value))
    elif value is Ellipsis:
        func = lambda x: True  # <- Wildcard (matches everything).
        name = '...'
    elif isinstance(value, regex_types):
        func = lambda x: (x is value) or (value.search(x) is not None)
        name = 're.compile({0!r})'.format(value.pattern)
    elif isinstance(value, set):
        func = lambda x: (x in value) or (x == value)
        name = repr(value)
    else:
        return value  # <- EXIT!
    return PredicateMatcher(func, name)


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
