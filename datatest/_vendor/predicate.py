"""Predicate class and matcher functions."""

from __future__ import absolute_import
import re
import sys
from cmath import isnan
from .._compatibility.builtins import *
from .._compatibility import abc
from .._utils import regex_types
from .._utils import isidentifier


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


def _check_nan(value):
    """Return true if *value* is NaN (not a number)."""
    try:
        return isnan(value)
    except TypeError:
        return False


def _check_regex(regex, value):
    """Return true if *value* matches regex."""
    try:
        return regex.search(value) is not None
    except TypeError:
        return value is regex


def _check_set(set_, value):
    """Return true if *value* is a member of the given set or if
    the *value* is equal to the given set.
    """
    try:
        return value in set_ or value == set_
    except TypeError:
        return False


def _get_matcher_parts(obj):
    """Return a 2-tuple containing a handler function (to check for
    matches) and a string (to use for displaying a user-readable
    value). Return None if *obj* can be matched with the "==" operator
    and requires no other special handling.
    """
    if isinstance(obj, type):
        if 'numpy' in sys.modules:
            if obj is str:
                alt_obj = (str, sys.modules['numpy'].character)
            elif obj is int:
                alt_obj = (int, sys.modules['numpy'].integer)
            elif obj is float:
                alt_obj = (float, sys.modules['numpy'].floating)
            elif obj is complex:
                alt_obj = (complex, sys.modules['numpy'].complexfloating)
            else:
                alt_obj = obj
        else:
            alt_obj = obj
        pred_handler = lambda x: _check_type(alt_obj, x)
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
    elif _check_nan(obj):
        pred_handler = _check_nan
        repr_string = 'NaN'
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
    if isinstance(obj, MatcherBase):
        return obj  # <- EXIT!

    if isinstance(obj, Predicate):
        return obj.matcher  # <- EXIT!

    if isinstance(obj, tuple):
        matcher = tuple(_get_matcher_or_original(x) for x in obj)
        for x in matcher:
            if isinstance(x, MatcherBase):
                return MatcherTuple(matcher)  # <- Wrapper.
        return obj  # <- Orignal reference.

    return _get_matcher_or_original(obj)


class Predicate(object):
    """A Predicate is used like a function of one argument that
    returns ``True`` when applied to a matching value and ``False``
    when applied to a non-matching value. The criteria for matching
    is determined by the *obj* type used to define the predicate:

    +-------------------------+-----------------------------------+
    | *obj* type              | matches when                      |
    +=========================+===================================+
    | function                | the result of ``function(value)`` |
    |                         | tests as True                     |
    +-------------------------+-----------------------------------+
    | type                    | value is an instance of the type  |
    +-------------------------+-----------------------------------+
    | ``re.compile(pattern)`` | value matches the regular         |
    |                         | expression pattern                |
    +-------------------------+-----------------------------------+
    | ``True``                | value is truthy (``bool(value)``  |
    |                         | returns True)                     |
    +-------------------------+-----------------------------------+
    | ``False``               | value is falsy (``bool(value)``   |
    |                         | returns False)                    |
    +-------------------------+-----------------------------------+
    | str or non-container    | value is equal to the object      |
    +-------------------------+-----------------------------------+
    | set                     | value is a member of the set      |
    +-------------------------+-----------------------------------+
    | tuple of predicates     | tuple of values satisfies         |
    |                         | corresponding tuple of            |
    |                         | predicates---each according       |
    |                         | to their type                     |
    +-------------------------+-----------------------------------+
    | ``...`` (Ellipsis       | (used as a wildcard, matches      |
    | literal)                | any value)                        |
    +-------------------------+-----------------------------------+

    Example matches:

    +---------------------------+----------------+---------+
    | *obj* example             | value          | matches |
    +===========================+================+=========+
    | .. code-block:: python    | ``4``          | Yes     |
    |                           +----------------+---------+
    |     def is_even(x):       | ``9``          | No      |
    |         return x % 2 == 0 |                |         |
    +---------------------------+----------------+---------+
    | .. code-block:: python    | ``1.0``        | Yes     |
    |                           +----------------+---------+
    |     float                 | ``1``          | No      |
    +---------------------------+----------------+---------+
    | .. code-block:: python    | ``'bake'``     | Yes     |
    |                           +----------------+---------+
    |     re.compile('[bc]ake') | ``'cake'``     | Yes     |
    |                           +----------------+---------+
    |                           | ``'fake'``     | No      |
    +---------------------------+----------------+---------+
    | .. code-block:: python    | ``'x'``        | Yes     |
    |                           +----------------+---------+
    |     True                  | ``''``         | No      |
    +---------------------------+----------------+---------+
    | .. code-block:: python    | ``''``         | Yes     |
    |                           +----------------+---------+
    |     False                 | ``'x'``        | No      |
    +---------------------------+----------------+---------+
    | .. code-block:: python    | ``'foo'``      | Yes     |
    |                           +----------------+---------+
    |     'foo'                 | ``'bar'``      | No      |
    +---------------------------+----------------+---------+
    | .. code-block:: python    | ``'A'``        | Yes     |
    |                           +----------------+---------+
    |     {'A', 'B'}            | ``'C'``        | No      |
    +---------------------------+----------------+---------+
    | .. code-block:: python    | ``('A', 1.0)`` | Yes     |
    |                           +----------------+---------+
    |     ('A', float)          | ``('A', 2)``   | No      |
    +---------------------------+----------------+---------+
    | .. code-block:: python    | ``('A', 'X')`` | Yes     |
    |                           +----------------+---------+
    |     ('A', ...)            | ``('A', 'Y')`` | Yes     |
    |                           +----------------+---------+
    | Uses ellipsis wildcard.   | ``('B', 'X')`` | No      |
    +---------------------------+----------------+---------+

    Example code::

        >>> pred = Predicate({'A', 'B'})
        >>> pred('A')
        True
        >>> pred('C')
        False

    Predicate matching behavior can also be inverted with the inversion
    operator (``~``). Inverted Predicates return ``False`` when applied
    to a matching value and ``True`` when applied to a non-matching
    value::

        >>> pred = ~Predicate({'A', 'B'})
        >>> pred('A')
        False
        >>> pred('C')
        True

    If the *name* argument is given, a ``__name__`` attribute is
    defined using the given value::

        >>> pred = Predicate({'A', 'B'}, name='a_or_b')
        >>> pred.__name__
        'a_or_b'

    If the *name* argument is omitted, the object will not have a
    ``__name__`` attribute::

        >>> pred = Predicate({'A', 'B'})
        >>> pred.__name__
        Traceback (most recent call last):
          File "<input>", line 1, in <module>
            pred.__name__
        AttributeError: 'Predicate' object has no attribute '__name__'
    """
    def __init__(self, obj, name=None):
        if isinstance(obj, Predicate):
            self.obj = obj.obj
            self.matcher = obj.matcher
            self._inverted = obj._inverted
            if hasattr(obj, '__name__'):
                self.__name__ = obj.__name__
        else:
            self.obj = obj
            self.matcher = get_matcher(obj)
            self._inverted = False

        if name is not None:
            if not isidentifier(name):
                message = "name must be valid Python identifier, got {0!r}"
                raise ValueError(message.format(name))
            self.__name__ = name

    def __call__(self, other):
        try:
            is_match = self.matcher == other
        except TypeError:
            is_match = False

        if self._inverted:
            return not is_match
        return is_match

    def __copy__(self):
        new_pred = self.__class__.__new__(self.__class__)
        new_pred.obj = self.obj
        new_pred.matcher = self.matcher
        new_pred._inverted = self._inverted
        if hasattr(self, '__name__'):
            new_pred.__name__ = self.__name__
        return new_pred

    def __invert__(self):
        new_pred = self.__copy__()
        new_pred._inverted = not self._inverted
        return new_pred

    def intersection(self, other):
        """Return a new predicate that matches only those values
        that match both the current predicate and the given *other*
        predicate.
        """
        return self.__and__(other)

    def __and__(self, other):
        if not isinstance(other, Predicate):
            return NotImplemented
        return PredicateIntersectionType(self, other)

    def __repr__(self):
        inverted = '~' if self._inverted else ''
        class_name = self.__class__.__name__
        instance_name = getattr(self, '__name__', None)
        if instance_name is not None:
            name_arg = ', name={0!r}'.format(instance_name)
        else:
            name_arg = ''

        return '{0}{1}({2!r}{3})'.format(
            inverted, class_name, self.matcher, name_arg)

    def __str__(self):
        inverted = 'not ' if self._inverted else ''
        return '{0}{1}'.format(inverted, repr(self.matcher))


class PredicateIntersectionType(Predicate):
    def __init__(self, left, right):
        self.left = left
        self.right = right
        self._inverted = False

    def __copy__(self):
        new_pred = self.__class__.__new__(self.__class__)
        new_pred.left = self.left
        new_pred.right = self.right
        new_pred._inverted = self._inverted
        return new_pred

    def __repr__(self):
        inverted = '~' if self._inverted else ''
        return '{0}({1!r} & {2!r})'.format(inverted, self.left, self.right)

    def __call__(self, other):
        is_match = self.left(other) and self.right(other)
        if self._inverted:
            return not is_match
        return is_match
