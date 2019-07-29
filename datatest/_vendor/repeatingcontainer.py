#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import operator
from .._compatibility.collections.abc import Iterable
from .._compatibility.collections.abc import Mapping
from .._compatibility.functools import partial
from .._compatibility.functools import partialmethod
from .._compatibility.itertools import chain
from .._utils import IterItems


class RepeatingContainerBase(Iterable):
    """A base class to provide magic methods that operate directly on
    the RepeatingContainer itself---rather than on the objects it
    contains.

    These methods must be accessed using super()::

        >>> repeating1 = RepeatingContainer(['foo', 'bar'])
        >>> repeating2 = RepeatingContainer(['foo', 'bar'])
        >>> super(RepeatingContainer, repeating1).__eq__(repeating2)
        True
    """
    def __eq__(self, other):
        return (isinstance(other, RepeatingContainer)
                and self._objs == other._objs
                and self._keys == other._keys)

    def __ne__(self, other):
        return not super(RepeatingContainer, self).__eq__(other)


class RepeatingContainer(RepeatingContainerBase):
    """A container that repeats attribute lookups, method calls,
    operations, and expressions on the objects it contains. When
    an action is performed, it is forwarded to each object in the
    container and a new RepeatingContainer is returned with the
    resulting values.

    In the following example, a RepeatingContainer with two strings
    is created. A method call to ``upper()`` is forwarded to the
    individual strings and a new RepeatingContainer is returned that
    contains the uppercase values::

        >>> repeating = RepeatingContainer(['foo', 'bar'])
        >>> repeating.upper()
        RepeatingContainer(['FOO', 'BAR'])

    A RepeatingContainer is an iterable and its individual items can
    be accessed through sequence unpacking or iteration. Below, the
    individual objects are unpacked into the variables ``x`` and
    ``y``::

        >>> repeating = RepeatingContainer(['foo', 'bar'])
        >>> repeating = repeating.upper()
        >>> x, y = repeating  # <- Unpack values.
        >>> x
        'FOO'
        >>> y
        'BAR'

    If the RepeatingContainer was created with a dict (or other
    mapping), then iterating over it will return a sequence of
    ``(key, value)`` tuples. This sequence can be used as-is or
    used to create another dict::

        >>> repeating = RepeatingContainer({'a': 'foo', 'b': 'bar'})
        >>> repeating = repeating.upper()
        >>> list(repeating)
        [('a', 'FOO'), ('b', 'BAR')]
        >>> dict(repeating)
        {'a': 'FOO', 'b': 'BAR'}
    """
    def __init__(self, iterable):
        if not isinstance(iterable, Iterable):
            msg = '{0!r} object is not iterable'
            raise TypeError(msg.format(iterable.__class__.__name__))

        if isinstance(iterable, str):
            msg = "expected non-string iterable, got 'str'"
            raise ValueError(msg)

        if isinstance(iterable, Mapping):
            self._keys = tuple(iterable.keys())
            self._objs = tuple(iterable.values())
        elif isinstance(iterable, IterItems):
            self._keys, self._objs = zip(*iterable)
        else:
            self._keys = tuple()
            self._objs = tuple(iterable)

    def __iter__(self):
        if self._keys:
            return IterItems(zip(self._keys, self._objs))
        return iter(self._objs)

    def __repr__(self):
        cls_name = self.__class__.__name__

        if self._keys:
            zipped = zip(self._keys, self._objs)
            obj_reprs = ['{0!r}: {1!r}'.format(k, v) for k, v in zipped]
            indent_str = '    '
            begin, end = '{', '}'
        else:
            obj_reprs = [repr(x) for x in self._objs]
            indent_str = '  '
            begin, end = '[', ']'

        # Get length of _objs reprs and separator characters.
        separator_len = (len(obj_reprs) - 1) * len(', ')
        internal_repr_len = sum(len(x) for x in obj_reprs) + separator_len

        # Determine internal repr limit for single-line reprs.
        outer_repr_length = len(cls_name) + len('([])')
        max_repr_width = 79
        internal_repr_limit = max_repr_width - outer_repr_length

        # Build internal repr string.
        if internal_repr_len > internal_repr_limit:
            indent = '\n' + indent_str
            indented_objs = [indent.join(x.splitlines()) for x in obj_reprs]
            internal_repr = '\n  {0}\n'.format(',\n  '.join(indented_objs))
        else:
            internal_repr = ', '.join(obj_reprs)

        return '{0}({1}{2}{3})'.format(cls_name, begin, internal_repr, end)

    def __getattr__(self, name):
        repeating = self.__class__(getattr(obj, name) for obj in self._objs)
        repeating._keys = self._keys
        return repeating

    def _compatible_container(self, value):
        """Returns True if *value* is a RepeatingContainer with
        compatible contents.
        """
        if not isinstance(value, RepeatingContainer):
            return False
        if len(value._objs) != len(self._objs):
            return False
        if set(value._keys) != set(self._keys):
            return False
        return True

    def _normalize_value(self, value):
        """Return a tuple of objects equal the number of objects
        contained in the RepeatingContainer.

        If *value* itself is a compatible RepeatingContainer, its
        contents will be returned::

            >>> repeating = RepeatingContainer([2, 4])
            >>> repeating._normalize_value(RepeatingContainer([5, 6]))
            (5, 6)

        If *value* is not a compatible RepeatingContainer, the iterable
        will contain multiple copies of the same *value*::

            >>> repeating = RepeatingContainer([2, 4])
            >>> repeating._normalize_value(9)
            (9, 9)
        """
        if self._compatible_container(value):
            if value._keys:
                key_order = (self._keys.index(x) for x in value._keys)
                _, objs = zip(*sorted(zip(key_order, value._objs)))
                return objs
            return value._objs
        return (value,) * len(self._objs)  # <- Expand single value.

    def _expand_args_kwds(self, *args, **kwds):
        """Return an expanded list of *args* and *kwds* to use when
        calling objects contained in the RepeatingContainer.

        When a compatible RepeatingContainer is passed as an argument,
        its contents are unwrapped and paired with each record. When a
        non-compatible value is passed as an argument, it is duplicated
        for each record::

            >>> repeating = RepeatingContainer([2, 4])
            >>> repeating._expand_args_kwds(RepeatingContainer([5, 6]), 9, a=12)
            [((5, 9), {'a': 12}),
             ((6, 9), {'a': 12})]
        """
        objs_len = len(self._objs)

        normalized_args = (self._normalize_value(arg) for arg in args)
        zipped_args = tuple(zip(*normalized_args))
        if not zipped_args:
            zipped_args = ((),) * objs_len

        normalized_values = (self._normalize_value(v) for v in kwds.values())
        zipped_values = zip(*normalized_values)
        zipped_kwds = tuple(dict(zip(kwds.keys(), x)) for x in zipped_values)
        if not zipped_kwds:
            zipped_kwds = ({},) * objs_len

        return list(zip(zipped_args, zipped_kwds))

    def __call__(self, *args, **kwds):
        if any(self._compatible_container(x) for x in chain(args, kwds.values())):
            # Call each object using args and kwds from the expanded list.
            expanded_list = self._expand_args_kwds(*args, **kwds)
            zipped = zip(self._objs, expanded_list)
            iterable = (obj(*a, **k) for (obj, (a, k)) in zipped)
        else:
            # Call each object with the same args and kwds.
            iterable = (obj(*args, **kwds) for obj in self._objs)

        repeating = self.__class__(iterable)
        repeating._keys = self._keys
        return repeating


def _setup_RepeatingContainer_special_names(repeating_class):
    """This function is run when the module is imported--users should
    not call this function directly. It assigns magic methods and
    special attribute names to the RepeatingContainer class.

    This behavior is wrapped in a function to help keep the
    module-level namespace clean.
    """
    special_names = """
        getitem missing setitem delitem
        lt le eq ne gt ge
        add sub mul matmul truediv floordiv mod pow
        lshift rshift and xor or div
    """.split()

    def repeating_getattr(self, name):
        repeating = self.__class__(getattr(obj, name) for obj in self._objs)
        repeating._keys = self._keys
        return repeating

    for name in special_names:
        dunder = '__{0}__'.format(name)
        method = partial(repeating_getattr, name=dunder)
        setattr(repeating_class, dunder, property(method))

    # When a reflected method is called on a RepeatingContainer itself, the
    # original (unreflected) operation is re-applied to the individual objects
    # contained in the container. If these new calls are also reflected, they
    # will act on the individual objects--rather than on the container as a
    # whole.
    reflected_special_names = """
        radd rsub rmul rmatmul rtruediv rfloordiv rmod rpow
        rlshift rrshift rand rxor ror rdiv
    """.split()

    def repeating_reflected_method(self, other, name):
        unreflected_op = name[1:]  # Slice-off 'r' prefix.
        operation = getattr(operator, unreflected_op)
        repeating = self.__class__(operation(other, obj) for obj in self._objs)
        repeating._keys = self._keys
        return repeating

    for name in reflected_special_names:
        dunder = '__{0}__'.format(name)
        method = partialmethod(repeating_reflected_method, name=name)
        setattr(repeating_class, dunder, method)

_setup_RepeatingContainer_special_names(RepeatingContainer)
