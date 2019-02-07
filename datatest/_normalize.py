"""Normalize objects for validation."""
import sys
from ._compatibility.collections.abc import Collection
from ._compatibility.collections.abc import Iterable
from ._compatibility.collections.abc import Mapping
from ._query.query import BaseElement
from ._query.query import Query
from ._query.query import Result
from ._utils import exhaustible
from ._utils import IterItems


def _normalize_lazy(obj):
    """ Make Result for lazy evaluation."""
    if isinstance(obj, Query):
        obj = obj.execute()

    if isinstance(obj, Result):
        if issubclass(obj.evaluation_type, Mapping):
            obj = IterItems(obj)
        return obj  # <- EXIT!

    pandas = sys.modules.get('pandas', None)
    if pandas:
        is_series = isinstance(obj, pandas.Series)
        is_dataframe = isinstance(obj, pandas.DataFrame)

        if (is_series or is_dataframe) and not obj.index.is_unique:
            cls_name = obj.__class__.__name__
            raise ValueError(('{0} index contains duplicates, must '
                              'be unique').format(cls_name))

        if is_series:
            return IterItems(obj.iteritems())  # <- EXIT!

        if is_dataframe:
            gen = ((x[0], x[1:]) for x in obj.itertuples())
            if len(obj.columns) == 1:
                gen = ((k, v[0]) for k, v in gen)  # Unwrap if 1-tuple.
            return IterItems(gen)  # <- EXIT!

    numpy = sys.modules.get('numpy', None)
    if numpy and isinstance(obj, numpy.ndarray):
        # Two-dimentional array, recarray, or structured array.
        if obj.ndim == 2 or (obj.ndim == 1 and len(obj.dtype) > 1):
            obj = (tuple(x) for x in obj)
            return Result(obj, evaluation_type=list)  # <- EXIT!

        # One-dimentional array, recarray, or structured array.
        if obj.ndim == 1:
            if len(obj.dtype) == 1:        # Unpack single-valued recarray
                obj = (x[0] for x in obj)  # or structured array.
            else:
                obj = iter(obj)
            return Result(obj, evaluation_type=list)  # <- EXIT!

    return obj


def _normalize_eager(obj, default_type=None):
    """Eagerly evaluate *obj* when possible. When *obj* is exhaustible,
    a *default_type* must be specified. When provided, *default_type*
    must be a collection type (a sized iterable container).
    """
    if isinstance(obj, Result):
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
