# -*- coding: utf-8 -*-
from ..utils.builtins import *
from ..utils import collections
from ..utils import decimal
from ..utils import functools

from ..compare import CompareDict
from ..compare import CompareSet
from ..compare import _is_nscontainer


class BaseSource(object):
    """Common base class for all data sources.  Custom sources can be
    created by subclassing BaseSource and implementing ``__init__()``,
    ``__repr__()``, ``columns()`` and ``__iter__()``.  Optionally,
    performance can be improved by implementing ``filter_rows()``,
    ``distinct()``, ``sum()``, ``count()``, and ``mapreduce()``.
    """
    def __new__(cls, *args, **kwds):
        if cls is BaseSource:
            msg = 'cannot instantiate BaseSource directly - make a subclass'
            raise NotImplementedError(msg)
        return super(BaseSource, cls).__new__(cls)

    def __init__(self):
        """Initialize self."""
        return NotImplemented

    def __repr__(self):
        """Returns string representation of the data source."""
        return NotImplemented

    def columns(self):
        """Returns list of column names."""
        return NotImplemented

    def __iter__(self):
        """Returns iterable of dictionary rows (like ``csv.DictReader``)."""
        return NotImplemented

    def filter_rows(self, **kwds):
        """Returns iterable of dictionary rows (like ``csv.DictReader``)
        filtered by keywords.  E.g., where column1=value1,
        column2=value2, etc. (uses slow ``__iter__``).
        """
        if kwds:
            normalize = lambda v: (v,) if isinstance(v, str) else v
            kwds = dict((k, normalize(v)) for k, v in kwds.items())
            matches_kwds = lambda row: all(row[k] in v for k, v in kwds.items())
            return filter(matches_kwds, self.__iter__())
        return self.__iter__()

    def distinct(self, columns, **kwds_filter):
        """Returns CompareSet of distinct values or distinct tuples of
        values if given multiple *columns* (uses slow ``__iter__``).
        """
        if not _is_nscontainer(columns):
            columns = (columns,)
        self._assert_columns_exist(columns)
        iterable = self.filter_rows(**kwds_filter)  # Filtered rows only.
        iterable = (tuple(row[c] for c in columns) for row in iterable)
        return CompareSet(iterable)

    def sum(self, column, keys=None, **kwds_filter):
        """Returns CompareDict containing sums of *column* values
        grouped by *keys*.
        """
        mapper = lambda x: decimal.Decimal(x) if x else decimal.Decimal(0)
        reducer = lambda x, y: x + y
        return self.mapreduce(mapper, reducer, column, keys, **kwds_filter)

    def count(self, column, keys=None, **kwds_filter):
        """Returns CompareDict containing count of non-empty *column*
        values grouped by *keys*.
        """
        mapper = lambda value: 1 if value else 0  # 1 for truthy, 0 for falsy
        reducer = lambda x, y: x + y
        return self.mapreduce(mapper, reducer, column, keys, **kwds_filter)

    def mapreduce(self, mapper, reducer, columns, keys=None, **kwds_filter):
        """Apply *mapper* to the values in *columns* (which are grouped
        by *keys* and filtered by *filter*) then apply *reducer* of two
        arguments cumulatively to the mapped values, from left to right,
        so as to reduce the values to a single result per group of
        *keys*.  If *keys* is omitted, a single result is returned,
        otherwise returns a CompareDict object.

        *mapper* (function or other callable):
            Should accept column values from a single row and return a
            single computed result.  Mapper always receives a single
            argument--if *columns* is a sequence, *mapper* will receive
            a tuple of values containing in the specified columns.
        *reducer* (function or other callable):
            Should accept two arguments that are applied cumulatively to
            the intermediate mapped results (produced by *mapper*), from
            left to right, so as to reduce them to a single value for
            each group of *keys*.
        *columns* (string or sequence):
            Name of column or columns that are passed into *mapper*.
        *keys* (None, string, or sequence):
            Name of key or keys used to group column values.
        *kwds_filter*:
            Keywords used to filter rows.
        """
        if isinstance(columns, str):
            get_value = lambda row: row[columns]
        elif isinstance(columns, collections.Sequence):
            get_value = lambda row: tuple(row[column] for column in columns)
        else:
            raise TypeError('colums must be str or sequence')

        filtered_rows = self.filter_rows(**kwds_filter)

        if not keys:
            filtered_values = (get_value(row) for row in filtered_rows)
            mapped_values = (mapper(value) for value in filtered_values)
            return functools.reduce(reducer, mapped_values)  # <- EXIT!

        if not _is_nscontainer(keys):
            keys = (keys,)
        self._assert_columns_exist(keys)

        result = {}
        for row in filtered_rows:              # Do not remove this loop
            y = get_value(row)                 # without a good reason!
            y = mapper(y)                      # While a more functional
            key = tuple(row[k] for k in keys)  # style (using sorted,
            if key in result:                  # groupby, and reduce) is
                x = result[key]                # nicer to read, this base
                result[key] = reducer(x, y)    # class should prioritize
            else:                              # memory efficiency over
                result[key] = y                # speed.
        return CompareDict(result, keys)

    def _assert_columns_exist(self, columns):
        """Asserts that given columns are present in data source,
        raises LookupError if columns are missing.
        """
        if not _is_nscontainer(columns):
            columns = (columns,)
        self_cols = self.columns()
        is_missing = lambda col: col not in self_cols
        missing = [c for c in columns if is_missing(c)]
        if missing:
            missing = ', '.join(repr(x) for x in missing)
            msg = '{0} not in {1}'.format(missing, self.__repr__())
            raise LookupError(msg)


#DefaultDataSource = CsvSource
