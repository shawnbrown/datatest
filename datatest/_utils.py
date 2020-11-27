# -*- coding: utf-8 -*-
"""Utility helper functions."""
from __future__ import absolute_import
import re
from io import IOBase
from numbers import Number

from ._compatibility.abc import ABC
from ._compatibility.collections.abc import ItemsView
from ._compatibility.collections.abc import Iterable
from ._compatibility.collections.abc import Mapping
from ._compatibility.decimal import Decimal
from ._compatibility.itertools import chain
from ._compatibility.itertools import filterfalse


try:
    string_types = (basestring,)  # Removed in Python 3.0
except NameError:
    string_types = (str,)

try:
    from StringIO import StringIO
    file_types = (IOBase, file, StringIO)
    # Above: StringIO module and file object were removed
    # in Python 3. Also, the old StringIO is not a subclass
    # of io.IOBase.
except (ImportError, NameError):
    file_types = (IOBase,)

regex_types = type(re.compile(''))


def nonstringiter(obj):
    """Returns True if *obj* is a non-string iterable object."""
    return not isinstance(obj, string_types) and isinstance(obj, Iterable)


def seekable(buf):
    """Returns True if *buf* is a seekable file-like buffer."""
    try:
        return buf.seekable()
    except AttributeError:
        try:
            buf.seek(buf.tell())  # <- For StringIO in Python 2.
            return True
        except Exception:
            return False


def sortable(obj):
    """Returns True if *obj* is sortable else returns False."""
    try:
        sorted([obj, obj])
        return True
    except TypeError:
        return False


def exhaustible(iterable):
    """Returns True if *iterable* is an exhaustible iterator."""
    return iter(iterable) is iter(iterable)
    # Above: This works because exhaustible iterators return themselves
    # when passed to iter() but non-exhaustible iterables will return
    # newly created iterators.


def iterpeek(iterable, default=None):
    if exhaustible(iterable):
        try:
            first_item = next(iterable)  # <- Do not use default value here!
            iterable = chain([first_item], iterable)
        except StopIteration:
            first_item = default
    else:
        first_item = next(iter(iterable), default)
    return first_item, iterable


def _safesort_key(obj):
    """Return a key suitable for sorting objects of any type."""
    if obj is None:
        index = 0
    elif isinstance(obj, Number):
        index = 1
    elif isinstance(obj, str):
        index = 2
    elif isinstance(obj, Iterable):
        index = 3
        obj = tuple(_safesort_key(x) for x in obj)
    else:
        index = id(obj.__class__)
        obj = str(obj)
    return (index, obj)


def _flatten(iterable):
    """Flatten an iterable of elements."""
    for element in iterable:
        if nonstringiter(element):
            for sub_element in _flatten(element):
                yield sub_element
        else:
            yield element


def _unique_everseen(iterable):  # Adapted from itertools recipes.
    """Returns unique elements, preserving order."""
    seen = set()
    seen_add = seen.add
    iterable = filterfalse(seen.__contains__, iterable)
    for element in iterable:
        seen_add(element)
        yield element


def _make_decimal(d):
    """Converts number into normalized Decimal object."""
    if isinstance(d, float):
        d = str(d)
    d = Decimal(d)

    if d == d.to_integral():           # Remove_exponent (from official
        return d.quantize(Decimal(1))  # docs: 9.4.10. Decimal FAQ).
    return d.normalize()


def _make_sentinel(name, reprstring, docstring, truthy=True):
    """Return a new object instance to use as a sentinel to represent
    an entity that cannot be used directly because of some logical
    reason or implementation detail.

    * Query uses a sentinel for the result data when optimizing
      queries because the result does not exist until the query
      is actually executed.
    * _get_error() uses a sentinel to build an appropriate error
      when objects normally required for processing are not found.
    * DataError uses a sentinel to compare float('nan') objects
      because they are not considered to be equal when directly
      compared.
    """
    cls_dict = {
        '__repr__': lambda self: reprstring,
        '__doc__': docstring,
    }

    if not truthy:  # Make object falsy.
        cls_dict['__bool__'] = lambda self: False
        cls_dict['__nonzero__'] = lambda self: False

    return type(name, (object,), cls_dict)()


class IterItems(ABC):
    """An iterator that returns item-pairs appropriate for constructing
    a dictionary or other mapping. The given *items_or_mapping* should
    be an iterable of key/value pairs or a mapping.

    .. warning::

        :class:`IterItems` does no type checking or verification of
        the iterable's contents. When iterated over, it should yield
        only those values necessary for constructing a :py:class:`dict`
        or other mapping and no more---no duplicate or unhashable keys.
    """
    def __init__(self, items_or_mapping):
        """Initialize self."""
        if not isinstance(items_or_mapping, (Iterable, Mapping)):
            msg = 'expected iterable or mapping, got {0!r}'
            raise TypeError(msg.format(items_or_mapping.__class__.__name__))

        if isinstance(items_or_mapping, Mapping):
            if hasattr(items_or_mapping, 'iteritems'):
                items = items_or_mapping.iteritems()
            else:
                items = items_or_mapping.items()
        else:
            items = items_or_mapping
            while isinstance(items, IterItems) and hasattr(items, '__wrapped__'):
                items = items.__wrapped__

        self.__wrapped__ = iter(items)

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.__wrapped__)

    def next(self):
        return next(self.__wrapped__)

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{0}({1!r})'.format(cls_name, self.__wrapped__)

    # Set iteritems type as a class attribute.
    _iteritems_type = type(getattr(dict(), 'iteritems', dict().items)())

    @classmethod
    def __subclasshook__(cls, C):
        if cls is IterItems:
            if issubclass(C, (ItemsView, cls._iteritems_type, enumerate)):
                return True
        return NotImplemented


def pretty_timedelta_repr(delta):
    """Supports more human-readable reprs for negative value timedeltas.

    Negative values are presented naturally::

        >>> pretty_timedelta_repr(datetime.timedelta(microseconds=-1))
        'timedelta(microseconds=-1)'

    Compare this with timedelta's default repr::

        >>> repr(datetime.timedelta(microseconds=-1))
        'datetime.timedelta(days=-1, seconds=86399, microseconds=999999)'
    """
    # Note: timedeltas are normalized so that negative values
    # always have a negative 'days' attribute. For example:
    #
    #    >>> datetime.timedelta(microseconds=-1)
    #    datetime.timedelta(days=-1, seconds=86399, microseconds=999999)
    if delta.days < 0:
        isnegative = True
        delta = -delta  # Flip sign get rid of negative value normalization.
    else:
        isnegative = False

    days = delta.days
    seconds = delta.seconds
    microseconds = delta.microseconds

    if isnegative:
        days = -days
        seconds = -seconds
        microseconds = -microseconds

    args = []
    if days:
        args.append('days=%d' % days)
    if seconds:
        args.append('seconds=%d' % seconds)
    if microseconds:
        args.append('microseconds=%d' % microseconds)
    if not args:
        args.append('0')
    return '%s(%s)' % (delta.__class__.__name__, ', '.join(args))
