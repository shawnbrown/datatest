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
