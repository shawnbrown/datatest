"""compatibility layer for collections.abc (Python standard library)"""
from __future__ import absolute_import
try:
    from collections.abc import *  # New in 3.3
except ImportError:
    # Previously, the collection ABCs were in the root namespace.
    from collections import (
        Container,
        Hashable,
        Iterable,
        Iterator,
        Sized,
        Callable,
        Sequence,
        MutableSequence,
        Set,
        MutableSet,
        Mapping,
        MutableMapping,
        MappingView,
        KeysView,
        ItemsView,
        ValuesView,
    )


try:
    Collection  # New in 3.6
except NameError:
    # Adapted from Python 3.6 standard library.
    def _check_methods(C, *methods):
        mro = C.__mro__
        for method in methods:
            for B in mro:
                if method in B.__dict__:
                    if B.__dict__[method] is None:
                        return NotImplemented
                    break
            else:
                return NotImplemented
        return True


    # Adapted from Python 3.6 standard library.
    class Collection(Sized, Iterable, Container):
        __slots__ = ()

        @classmethod
        def __subclasshook__(cls, C):
            if cls is Collection:
                return _check_methods(C, '__len__', '__iter__', '__contains__')
