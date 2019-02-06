"""Normalize data for testing."""
import sys
from ._compatibility.collections.abc import Iterable
from ._compatibility.collections.abc import Mapping
from ._query.query import BaseElement
from ._query.query import Query
from ._query.query import Result
from ._utils import exhaustible
from ._utils import IterItems


def _normalize_lazy(data):
    if isinstance(data, Query):
        data = data.execute()  # Make Result for lazy evaluation.

    if isinstance(data, Result):
        if issubclass(data.evaluation_type, Mapping):
            data = IterItems(data)
        return data  # <- EXIT!

    pandas = sys.modules.get('pandas', None)
    if pandas:
        is_series = isinstance(data, pandas.Series)
        is_dataframe = isinstance(data, pandas.DataFrame)

        if (is_series or is_dataframe) and not data.index.is_unique:
            cls_name = data.__class__.__name__
            raise ValueError(('{0} index contains duplicates, must '
                              'be unique').format(cls_name))

        if is_series:
            return IterItems(data.iteritems())  # <- EXIT!

        if is_dataframe:
            gen = ((x[0], x[1:]) for x in data.itertuples())
            if len(data.columns) == 1:
                gen = ((k, v[0]) for k, v in gen)  # Unwrap if 1-tuple.
            return IterItems(gen)  # <- EXIT!

    numpy = sys.modules.get('numpy', None)
    if numpy and isinstance(data, numpy.ndarray):
        # Two-dimentional array, recarray, or structured array.
        if data.ndim == 2 or (data.ndim == 1 and len(data.dtype) > 1):
            data = (tuple(x) for x in data)
            return Result(data, evaluation_type=list)  # <- EXIT!

        # One-dimentional array, recarray, or structured array.
        if data.ndim == 1:
            if len(data.dtype) == 1:         # Unpack single-valued recarray
                data = (x[0] for x in data)  # or structured array.
            else:
                data = iter(data)
            return Result(data, evaluation_type=list)  # <- EXIT!

    return data


def _normalize_eager(requirement):
    if isinstance(requirement, Result):
        return requirement.fetch()  # <- Eagerly evaluate.

    if isinstance(requirement, IterItems):
        return dict(requirement)

    if isinstance(requirement, Iterable) and exhaustible(requirement):
        cls_name = requirement.__class__.__name__
        raise TypeError(("exhaustible type '{0}' cannot be used "
                         "as a requirement").format(cls_name))

    return requirement


def normalize(data, lazy_evaluation=False):
    data = _normalize_lazy(data)
    if lazy_evaluation:
        return data
    return _normalize_eager(data)
