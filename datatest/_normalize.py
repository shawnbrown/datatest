"""Normalize objects for validation."""
import sys
from ._compatibility.collections.abc import Collection
from ._compatibility.collections.abc import Iterable
from ._compatibility.collections.abc import Iterator
from ._compatibility.collections.abc import Mapping
from ._utils import exhaustible
from ._utils import iterpeek
from ._utils import IterItems


class TypedIterator(Iterator):
    def __init__(self, iterable, evaltype):
        self._iterator = iter(iterable)
        self.evaltype = evaltype

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._iterator)

    def next(self):  # Python 2.x support.
        return self.__next__()

    def fetch(self):
        return self.evaltype(self._iterator)


NoneType = type(None)


def _normalize_lazy(obj):
    """Return an iterator for lazy evaluation."""
    if isinstance(obj, TypedIterator):
        if issubclass(obj.evaltype, Mapping):
            obj = IterItems(obj)
        return obj  # <- EXIT!

    # Separate Squint module.
    squint = sys.modules.get('squint', None)
    if squint:
        if isinstance(obj, squint.Query):
            obj = obj.execute()
            if issubclass(getattr(obj, 'evaltype', NoneType), Mapping):
                obj = IterItems(obj)
            return obj  # <- EXIT!

        if isinstance(obj, squint.Result):
            if issubclass(obj.evaltype, Mapping):
                obj = IterItems(obj)
            return obj  # <- EXIT!

        if isinstance(obj, squint.Select):
            try:
                return obj().execute()  # <- EXIT!
            except TypeError:  # Squint >= 0.1.0 raises an error.
                return obj(obj.fieldnames).execute()  # <- EXIT!

    pandas = sys.modules.get('pandas', None)
    if pandas:
        if isinstance(obj, pandas.DataFrame):
            if not obj.index.is_unique:
                msg = '{0} index contains duplicates, must be unique'
                raise ValueError(msg.format(obj.__class__.__name__))

            if isinstance(obj.index, pandas.RangeIndex):
                # DataFrame with RangeIndex is treated as an iterator.
                if len(obj.columns) == 1:
                    obj = (x[0] for x in obj.values)
                else:
                    obj = (tuple(x) for x in obj.values)
                return TypedIterator(obj, evaltype=list)  # <- EXIT!
            else:
                # DataFrame with another index type is treated as a mapping.
                if len(obj.columns) == 1:
                    gen = ((x[0], x[1]) for x in obj.itertuples())
                else:
                    gen = ((x[0], tuple(x[1:])) for x in obj.itertuples())
                return IterItems(gen)  # <- EXIT!
        elif isinstance(obj, pandas.Series):
            if not obj.index.is_unique:
                msg = '{0} index contains duplicates, must be unique'
                raise ValueError(msg.format(obj.__class__.__name__))

            if isinstance(obj.index, pandas.RangeIndex):
                # Series with RangeIndex is treated as an iterator.
                return TypedIterator(obj.values, evaltype=list)  # <- EXIT!
            else:
                # Series with another index type is treated as a mapping.
                return IterItems(obj.iteritems())  # <- EXIT!

    numpy = sys.modules.get('numpy', None)
    if numpy and isinstance(obj, numpy.ndarray):
        # Two-dimentional array, recarray, or structured array.
        if obj.ndim == 2 or (obj.ndim == 1 and len(obj.dtype) > 1):
            obj = (tuple(x) for x in obj)
            return TypedIterator(obj, evaltype=list)  # <- EXIT!

        # One-dimentional array, recarray, or structured array.
        if obj.ndim == 1:
            if len(obj.dtype) == 1:        # Unpack single-valued recarray
                obj = (x[0] for x in obj)  # or structured array.
            else:
                obj = iter(obj)
            return TypedIterator(obj, evaltype=list)  # <- EXIT!

    # Check for cursor-like object (if obj has DBAPI2 cursor attributes).
    if all(hasattr(obj, n) for n in ('fetchone', 'execute',
                                     'rowcount', 'description')):
        if not isinstance(obj, Iterable):
            def cursor_to_gen(cursor):       # While most cursor objects are
                while True:                  # iterable, it is not required
                    row = cursor.fetchone()  # by the DBAPI2 specification.
                    if row is None:
                        break
                    yield row
            obj = cursor_to_gen(obj)

        first, obj = iterpeek(obj)
        if first and len(first) == 1:
            obj = iter(x[0] for x in obj)  # Unwrap single-value records.
        return obj  # <- EXIT!

    return obj


def _normalize_eager(obj, default_type=None):
    """Eagerly evaluate *obj* when possible. When *obj* is exhaustible,
    a *default_type* must be specified. When provided, *default_type*
    must be a collection type (a sized iterable container).
    """
    if isinstance(obj, TypedIterator):
        return obj.fetch()

    # Separate Squint module.
    squint = sys.modules.get('squint', None)
    if squint and isinstance(obj, squint.Result):
        return obj.fetch()

    if isinstance(obj, IterItems):
        return dict(obj)

    if isinstance(obj, Iterable) and exhaustible(obj):
        if isinstance(default_type, type) and issubclass(default_type, Collection):
            return default_type(obj)
        else:
            cls_name = obj.__class__.__name__
            msg = ("exhaustible type '{0}' cannot be eagerly evaluated "
                   "without specifying a 'default_type' collection")
            raise TypeError(msg.format(cls_name))

    return obj


def normalize(obj, lazy_evaluation=False, default_type=None):
    obj = _normalize_lazy(obj)
    if lazy_evaluation:
        return obj
    return _normalize_eager(obj, default_type)
