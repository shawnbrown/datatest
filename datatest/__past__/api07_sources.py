# -*- coding: utf-8 -*-
from __future__ import absolute_import
from .load_csv import load_csv
from .temptable import (
    load_data,
    new_table_name,
    savepoint,
)
from .squint.query import DEFAULT_CONNECTION


def _load_temp_sqlite_table(columns, records):
    global DEFAULT_CONNECTION
    cursor = DEFAULT_CONNECTION.cursor()
    with savepoint(cursor):
        table = new_table_name(cursor)
        load_data(cursor, table, columns, records)
    return DEFAULT_CONNECTION, table


########################################################################
# From sources/base.py
########################################################################
from .._compatibility.builtins import *
from .._compatibility.collections.abc import Sequence
from .._compatibility import decimal
from .._compatibility import functools
from .._utils import nonstringiter
from .api07_comp import CompareDict
from .api07_comp import CompareSet


class BaseSource(object):
    """Common base class for all data sources.  Custom sources can be
    created by subclassing BaseSource and implementing
    :meth:`__init__()`, :meth:`__repr__()`, :meth:`columns()` and
    :meth:`__iter__()`.

    All data sources implement a common set of methods.
    """
    def __new__(cls, *args, **kwds):
        if cls is BaseSource:
            msg = ('Cannot instantiate BaseSource directly.  Use a '
                   'data source of the appropriate type or make a '
                   'subclass.')
            raise NotImplementedError(msg)
        return super(BaseSource, cls).__new__(cls)

    def __init__(self):
        """Initialize self."""
        return NotImplemented

    def __repr__(self):
        """Returns string representation describing the data source."""
        return NotImplemented

    def columns(self):
        """Returns list of column names."""
        return NotImplemented

    def __iter__(self):
        """Returns iterable of dictionary rows (like
        :class:`csv.DictReader`)."""
        return NotImplemented

    def filter_rows(self, **kwds):
        """Returns iterable of dictionary rows (like
        :class:`csv.DictReader`) filtered by keywords.  E.g., where
        column1=value1, column2=value2, etc. (unoptimized, uses
        :meth:`__iter__`).
        """
        if kwds:
            normalize = lambda v: (v,) if isinstance(v, str) else v
            kwds = dict((k, normalize(v)) for k, v in kwds.items())
            matches_kwds = lambda row: all(row[k] in v for k, v in kwds.items())
            return filter(matches_kwds, self.__iter__())
        return self.__iter__()

    def distinct(self, columns, **kwds_filter):
        """Returns :class:`CompareSet` of distinct values or distinct
        tuples of values if given multiple *columns* (unoptimized, uses
        :meth:`__iter__`).
        """
        if not nonstringiter(columns):
            columns = (columns,)
        self._assert_columns_exist(columns)
        iterable = self.filter_rows(**kwds_filter)  # Filtered rows only.
        iterable = (tuple(row[c] for c in columns) for row in iterable)
        return CompareSet(iterable)

    def sum(self, column, keys=None, **kwds_filter):
        """Returns :class:`CompareDict` containing sums of *column*
        values grouped by *keys*.
        """
        mapper = lambda x: decimal.Decimal(x) if x else decimal.Decimal(0)
        reducer = lambda x, y: x + y
        return self.mapreduce(mapper, reducer, column, keys, **kwds_filter)

    def count(self, column, keys=None, **kwds_filter):
        """Returns :class:`CompareDict` containing count of non-empty
        *column* values grouped by *keys*.
        """
        mapper = lambda value: 1 if value else 0  # 1 for truthy, 0 for falsy
        reducer = lambda x, y: x + y
        return self.mapreduce(mapper, reducer, column, keys, **kwds_filter)

    def mapreduce(self, mapper, reducer, columns, keys=None, **kwds_filter):
        """Apply a *mapper* to specified *columns* (which are grouped by
        *keys* and filtered by keywords) then apply a *reducer* of two
        arguments cumulatively to the mapped values, from left to right,
        so as to reduce the values to a single result (per group of
        *keys*).  If *keys* is omitted, a single result is returned,
        otherwise returns a :class:`CompareDict` object.

        *mapper* (function or other callable):
            Should accept a column value and return a computed result.
            Mapper always receives a single argument---if *columns* is a
            sequence, *mapper* will receive a tuple of values from the
            specified columns.
        *reducer* (function or other callable):
            Should accept two arguments (values produced by *mapper*)
            and apply them, from left to right, to return a single
            result.
        *columns* (string or sequence):
            Name of column or columns whose values are passed to
            *mapper*.
        *keys* (None, string, or sequence):
            Name of key or keys used to group column values.
        *kwds_filter*:
            Keywords used to filter rows.
        """
        if isinstance(columns, str):
            get_value = lambda row: row[columns]
        elif isinstance(columns, Sequence):
            get_value = lambda row: tuple(row[column] for column in columns)
        else:
            raise TypeError('colums must be str or sequence')

        filtered_rows = self.filter_rows(**kwds_filter)

        if not keys:
            filtered_values = (get_value(row) for row in filtered_rows)
            mapped_values = (mapper(value) for value in filtered_values)
            return functools.reduce(reducer, mapped_values)  # <- EXIT!

        if not nonstringiter(keys):
            keys = (keys,)
        self._assert_columns_exist(keys)

        result = {}                            # Do not remove this
        for row in filtered_rows:              # accumulator and loop
            y = get_value(row)                 # without a good reason!
            y = mapper(y)                      # While a more functional
            key = tuple(row[k] for k in keys)  # style (using sorted,
            if key in result:                  # groupby, and reduce)
                x = result[key]                # is nicer to read, this
                result[key] = reducer(x, y)    # base class should
            else:                              # prioritize memory
                result[key] = y                # efficiency over other
        return CompareDict(result, keys)       # considerations.

    def _assert_columns_exist(self, columns):
        """Asserts that given columns are present in data source,
        raises LookupError if columns are missing.
        """
        if not nonstringiter(columns):
            columns = (columns,)
        self_cols = self.columns()
        is_missing = lambda col: col not in self_cols
        missing = [c for c in columns if is_missing(c)]
        if missing:
            missing = ', '.join(repr(x) for x in missing)
            msg = '{0} not in {1}'.format(missing, self.__repr__())
            raise LookupError(msg)


########################################################################
# For Testing
########################################################################
class MinimalSource(BaseSource):
    """Minimal data source implementation for testing."""
    def __init__(self, data, fieldnames=None):
        if not fieldnames:
            data_iter = iter(data)
            fieldnames = next(data_iter)  # <- First row.
            data = list(data_iter)        # <- Remaining rows.
        self._data = data
        self._fieldnames = fieldnames

    def __repr__(self):
        return self.__class__.__name__ + '(<data>, <fieldnames>)'

    def columns(self):
        return self._fieldnames

    def __iter__(self):
        for row in self._data:
            yield dict(zip(self._fieldnames, row))


########################################################################
# From sources/adapter.py
########################################################################
from .._compatibility.builtins import *
from .._compatibility.collections.abc import Sequence
from .._utils import nonstringiter
from .api07_comp import CompareDict
from .api07_comp import CompareSet


class _FilterValueError(ValueError):
    """Used by AdapterSource.  This error is raised when attempting to
    unwrap a filter that specifies an inappropriate (non-missing) value
    for a missing column."""
    pass


class AdapterSource(BaseSource):
    """A wrapper class that adapts a data *source* to an *interface* of
    column names. The *interface* should be a sequence of 2-tuples where
    the first item is the existing column name and the second item is
    the desired column name. If column order is not important, the
    *interface* can, alternatively, be a dictionary.

    For example, a CSV file that contains the columns 'AAA', 'BBB',
    and 'DDD' can be adapted to behave as if it has the columns
    'AAA', 'BBB', 'CCC' and 'DDD' with the following::

        source = CsvSource('mydata.csv')
        interface = [
            ('AAA', 'AAA'),
            ('BBB', 'BBB'),
            (None,  'CCC'),
            ('DDD', 'DDD'),
        ]
        subject = AdapterSource(source, interface)

    An :class:`AdapterSource` can be thought of as a virtual source that
    renames, reorders, adds, or removes columns of the original
    *source*.

    To add a column that does not exist in original, use None in place
    of a column name (see column 'CCC', above). Columns mapped to None
    will contain *missing* values (defaults to empty string).  To remove
    a column, simply omit it from the interface.

    The original source can be accessed via the :attr:`__wrapped__`
    property.
    """
    def __init__(self, source, interface, missing=''):
        if not isinstance(interface, Sequence):
            if isinstance(interface, dict):
                interface = interface.items()
            interface = sorted(interface)

        source_columns = source.columns()
        interface_cols = [x[0] for x in interface]
        for c in interface_cols:
            if c != None and c not in source_columns:
                raise KeyError(c)

        self._interface = list(interface)
        self._missing = missing
        self.__wrapped__ = source

    def __repr__(self):
        self_class = self.__class__.__name__
        wrapped_repr = repr(self.__wrapped__)
        interface = self._interface
        missing = self._missing
        if missing != '':
            missing = ', missing=' + repr(missing)
        return '{0}({1}, {2}{3})'.format(self_class, wrapped_repr, interface, missing)

    def columns(self):
        return [new for (old, new) in self._interface if new != None]

    def __iter__(self):
        interface = self._interface
        missing = self._missing
        for row in self.__wrapped__.__iter__():
            yield dict((new, row.get(old, missing)) for old, new in interface)

    def filter_rows(self, **kwds):
        try:
            unwrap_kwds = self._unwrap_filter(kwds)
        except _FilterValueError:
            return  # <- EXIT! Raises StopIteration to signify empty generator.

        interface = self._interface
        missing = self._missing
        for row in self.__wrapped__.filter_rows(**unwrap_kwds):
            yield dict((new, row.get(old, missing)) for old, new in interface)

    def distinct(self, columns, **kwds_filter):
        unwrap_src = self.__wrapped__  # Unwrap data source.
        unwrap_cols = self._unwrap_columns(columns)
        try:
            unwrap_flt = self._unwrap_filter(kwds_filter)
        except _FilterValueError:
            return CompareSet([])  # <- EXIT!

        if not unwrap_cols:
            iterable = iter(unwrap_src)
            try:
                next(iterable)  # Check for any data at all.
                length = 1 if isinstance(columns, str) else len(columns)
                result = [tuple([self._missing]) * length]  # Make 1 row of *missing* vals.
            except StopIteration:
                result = []  # If no data, result is empty.
            return CompareSet(result)  # <- EXIT!

        results = unwrap_src.distinct(unwrap_cols, **unwrap_flt)
        rewrap_cols = self._rewrap_columns(unwrap_cols)
        return self._rebuild_compareset(results, rewrap_cols, columns)

    def sum(self, column, keys=None, **kwds_filter):
        return self._aggregate('sum', column, keys, **kwds_filter)

    def count(self, column, keys=None, **kwds_filter):
        return self._aggregate('count', column, keys, **kwds_filter)

    def _aggregate(self, method, column, keys=None, **kwds_filter):
        """Call aggregation method ('sum' or 'count'), return result."""
        unwrap_src = self.__wrapped__
        unwrap_col = self._unwrap_columns(column)
        unwrap_keys = self._unwrap_columns(keys)
        try:
            unwrap_flt = self._unwrap_filter(kwds_filter)
        except _FilterValueError:
            if keys:
                result = CompareDict({}, keys)
            else:
                result = 0
            return result  # <- EXIT!

        # If all *columns* are missing, build result of missing values.
        if not unwrap_col:
            distinct = self.distinct(keys, **kwds_filter)
            result = ((key, 0) for key in distinct)
            return CompareDict(result, keys)  # <- EXIT!

        # Get method ('sum' or 'count') and perform aggregation.
        aggregate = getattr(unwrap_src, method)
        result = aggregate(unwrap_col, unwrap_keys, **unwrap_flt)

        rewrap_col = self._rewrap_columns(unwrap_col)
        rewrap_keys = self._rewrap_columns(unwrap_keys)
        return self._rebuild_comparedict(result, rewrap_col, column,
                                         rewrap_keys, keys, missing_col=0)

    def mapreduce(self, mapper, reducer, columns, keys=None, **kwds_filter):
        unwrap_src = self.__wrapped__
        unwrap_cols = self._unwrap_columns(columns)
        unwrap_keys = self._unwrap_columns(keys)
        try:
            unwrap_flt = self._unwrap_filter(kwds_filter)
        except _FilterValueError:
            if keys:
                result = CompareDict({}, keys)
            else:
                result = self._missing
            return result  # <- EXIT!

        # If all *columns* are missing, build result of missing values.
        if not unwrap_cols:
            distinct = self.distinct(keys, **kwds_filter)
            if isinstance(columns, str):
                val = self._missing
            else:
                val = (self._missing,) * len(columns)
            result = ((key, val) for key in distinct)
            return CompareDict(result, keys)  # <- EXIT!

        result = unwrap_src.mapreduce(mapper, reducer,
                                      unwrap_cols, unwrap_keys, **unwrap_flt)

        rewrap_cols = self._rewrap_columns(unwrap_cols)
        rewrap_keys = self._rewrap_columns(unwrap_keys)
        return self._rebuild_comparedict(result, rewrap_cols, columns,
                                           rewrap_keys, keys,
                                           missing_col=self._missing)

    def _unwrap_columns(self, columns, interface_dict=None):
        """Unwrap adapter *columns* to reveal hidden adaptee columns."""
        if not columns:
            return None  # <- EXIT!

        if not interface_dict:
            interface_dict = dict((new, old) for old, new in self._interface)

        if isinstance(columns, str):
            return interface_dict[columns]  # <- EXIT!

        unwrapped = (interface_dict[k] for k in columns)
        return tuple(x for x in unwrapped if x != None)

    def _unwrap_filter(self, filter_dict, interface_dict=None):
        """Unwrap adapter *filter_dict* to reveal hidden adaptee column
        names.  An unwrapped filter cannot be created if the filter
        specifies that a missing column equals a non-missing value--if
        this condition occurs, a _FilterValueError is raised.
        """
        if not interface_dict:
            interface_dict = dict((new, old) for old, new in self._interface)

        translated = {}
        for k, v in filter_dict.items():
            tran_k = interface_dict[k]
            if tran_k != None:
                translated[tran_k] = v
            else:
                if v != self._missing:
                    raise _FilterValueError('Missing column can only be '
                                            'filtered to missing value.')
        return translated

    def _rewrap_columns(self, unwrapped_columns, rev_dict=None):
        """Take unwrapped adaptee column names and wrap them in adapter
        column names (specified by _interface).
        """
        if not unwrapped_columns:
            return None  # <- EXIT!

        if rev_dict:
            interface_dict = dict((old, new) for new, old in rev_dict.items())
        else:
            interface_dict = dict(self._interface)

        if isinstance(unwrapped_columns, str):
            return interface_dict[unwrapped_columns]
        return tuple(interface_dict[k] for k in unwrapped_columns)

    def _rebuild_compareset(self, result, rewrapped_columns, columns):
        """Take CompareSet from unwrapped source and rebuild it to match
        the CompareSet that would be expected from the wrapped source.
        """
        normalize = lambda x: x if (isinstance(x, str) or not x) else tuple(x)
        rewrapped_columns = normalize(rewrapped_columns)
        columns = normalize(columns)

        if rewrapped_columns == columns:
            return result  # <- EXIT!

        missing = self._missing
        def rebuild(x):
            lookup_dict = dict(zip(rewrapped_columns, x))
            return tuple(lookup_dict.get(c, missing) for c in columns)
        return CompareSet(rebuild(x) for x in result)

    def _rebuild_comparedict(self,
                             result,
                             rewrapped_columns,
                             columns,
                             rewrapped_keys,
                             keys,
                             missing_col):
        """Take CompareDict from unwrapped source and rebuild it to
        match the CompareDict that would be expected from the wrapped
        source.
        """
        normalize = lambda x: x if (isinstance(x, str) or not x) else tuple(x)
        rewrapped_columns = normalize(rewrapped_columns)
        rewrapped_keys = normalize(rewrapped_keys)
        columns = normalize(columns)
        keys = normalize(keys)

        if rewrapped_keys == keys and rewrapped_columns == columns:
            if isinstance(result, CompareDict):
                key_names = (keys,) if isinstance(keys, str) else keys
                result.key_names = key_names
            return result  # <- EXIT!

        try:
            item_gen = iter(result.items())
        except AttributeError:
            item_gen = [(self._missing, result)]

        if rewrapped_keys != keys:
            def rebuild_keys(k, missing):
                if isinstance(keys, str):
                    return k
                key_dict = dict(zip(rewrapped_keys, k))
                return tuple(key_dict.get(c, missing) for c in keys)
            missing_key = self._missing
            item_gen = ((rebuild_keys(k, missing_key), v) for k, v in item_gen)

        if rewrapped_columns != columns:
            def rebuild_values(v, missing):
                if isinstance(columns, str):
                    return v
                if not nonstringiter(v):
                    v = (v,)
                value_dict = dict(zip(rewrapped_columns, v))
                return tuple(value_dict.get(v, missing) for v in columns)
            item_gen = ((k, rebuild_values(v, missing_col)) for k, v in item_gen)

        return CompareDict(item_gen, key_names=keys)


########################################################################
# From sources/multi.py
########################################################################
from .._compatibility.builtins import *
from .._compatibility.collections import defaultdict
from .._compatibility import itertools
from .._compatibility import functools
from .api07_comp import CompareDict
from .api07_comp import CompareSet


class MultiSource(BaseSource):
    """
    MultiSource(*sources, missing='')

    A wrapper class that allows multiple data sources to be treated
    as a single, composite data source::

        subject = datatest.MultiSource(
            datatest.CsvSource('file1.csv'),
            datatest.CsvSource('file2.csv'),
            datatest.CsvSource('file3.csv')
        )

    The original sources are stored in the :attr:`__wrapped__`
    attribute.
    """
    def __init__(self, *sources, **kwd):
        """
        __init__(self, *sources, missing='')

        Initialize self.
        """
        if not sources:
            raise TypeError('expected 1 or more sources, got 0')

        missing = kwd.pop('missing', '')  # Accept as keyword-only argument.

        if kwd:                     # Enforce keyword-only argument
            key, _ = kwd.popitem()  # behavior that works in Python 2.x.
            msg = "__init__() got an unexpected keyword argument " + repr(key)
            raise TypeError(msg)

        if not all(isinstance(s, BaseSource) for s in sources):
            raise TypeError('sources must be derived from BaseSource')

        all_columns = []
        for s in sources:
            for c in s.columns():
                if c not in all_columns:
                    all_columns.append(c)

        normalized_sources = []
        for s in sources:
            if set(s.columns()) < set(all_columns):
                columns = s.columns()
                make_old = lambda x: x if x in columns else None
                interface = [(make_old(x), x) for x in all_columns]
                s = AdapterSource(s, interface, missing)
            normalized_sources.append(s)

        self._columns = all_columns
        self._sources = normalized_sources
        self.__wrapped__ = sources  # <- Original sources.

    def __repr__(self):
        """Return a string representation of the data source."""
        cls_name = self.__class__.__name__
        src_names = [repr(src) for src in self.__wrapped__]  # Get reprs.
        src_names = ['    ' + src for src in src_names]      # Prefix with 4 spaces.
        src_names = ',\n'.join(src_names)                    # Join w/ comma & new-line.
        return '{0}(\n{1}\n)'.format(cls_name, src_names)

    def columns(self):
        """Return list of column names."""
        return self._columns

    def __iter__(self):
        """Return iterable of dictionary rows (like csv.DictReader)."""
        for source in self._sources:
            for row in source.__iter__():
                yield row

    def filter_rows(self, **kwds):
        for source in self._sources:
            for row in source.filter_rows(**kwds):
                yield row

    def distinct(self, columns, **kwds_filter):
        """Return iterable of tuples containing distinct *column*
        values.
        """
        fn = lambda source: source.distinct(columns, **kwds_filter)
        results = (fn(source) for source in self._sources)
        results = itertools.chain(*results)
        return CompareSet(results)

    def sum(self, column, keys=None, **kwds_filter):
        """Return sum of values in *column* grouped by *keys*."""
        return self._aggregate('sum', column, keys, **kwds_filter)

    def count(self, column, keys=None, **kwds_filter):
        return self._aggregate('count', column, keys, **kwds_filter)

    def _aggregate(self, method, column, keys=None, **kwds_filter):
        """Call aggregation method ('sum' or 'count'), return result."""
        fn = lambda src: getattr(src, method)(column, keys, **kwds_filter)
        results = (fn(source) for source in self._sources)  # Perform aggregation.

        if not keys:
            return sum(results)  # <- EXIT!

        total = defaultdict(lambda: 0)
        for result in results:
            for key, val in result.items():
                total[key] += val
        return CompareDict(total, keys)

    def mapreduce(self, mapper, reducer, columns, keys=None, **kwds_filter):
        fn = lambda source: source.mapreduce(mapper, reducer, columns, keys, **kwds_filter)
        results = (fn(source) for source in self._sources)

        if not keys:
            return functools.reduce(reducer, results)  # <- EXIT!

        final_result = {}
        results = (result.items() for result in results)
        for key, y in itertools.chain(*results):
            if key in final_result:
                x = final_result[key]
                final_result[key] = reducer(x, y)
            else:
                final_result[key] = y
        return CompareDict(final_result, keys)


########################################################################
# From sources/sqlite.py
########################################################################
import sqlite3
from .._compatibility.builtins import *
from .._compatibility import decimal
from .._utils import nonstringiter
from .api07_comp import CompareDict
from .api07_comp import CompareSet


sqlite3.register_adapter(decimal.Decimal, float)

class SqliteBase(BaseSource):
    """Base class four SqliteSource and CsvSource (not intended to be
    instantiated directly).
    """
    def __new__(cls, *args, **kwds):
        if cls is SqliteBase:
            msg = 'cannot instantiate SqliteBase directly - make a subclass'
            raise NotImplementedError(msg)
        return super(SqliteBase, cls).__new__(cls)

    def __init__(self, connection, table):
        """Initialize self."""
        self._connection = connection
        self._table = table

    def __repr__(self):
        """Return a string representation of the data source."""
        cls_name = self.__class__.__name__
        conn_name = str(self._connection)
        tbl_name = self._table
        return '{0}({1}, table={2!r})'.format(cls_name, conn_name, tbl_name)

    def columns(self):
        """Return list of column names."""
        cursor = self._connection.cursor()
        cursor.execute('PRAGMA table_info(' + self._table + ')')
        return [x[1] for x in cursor.fetchall()]

    def __iter__(self):
        """Return iterable of dictionary rows (like csv.DictReader)."""
        cursor = self._connection.cursor()
        cursor.execute('SELECT * FROM ' + self._table)

        column_names = self.columns()
        dict_row = lambda x: dict(zip(column_names, x))
        return (dict_row(row) for row in cursor.fetchall())

    def filter_rows(self, **kwds):
        if kwds:
            cursor = self._connection.cursor()
            cursor = self._execute_query('*', **kwds)  # <- applies filter
            column_names = self.columns()
            dict_row = lambda row: dict(zip(column_names, row))
            return (dict_row(row) for row in cursor)
        return self.__iter__()

    def distinct(self, columns, **kwds_filter):
        """Return iterable of tuples containing distinct *columns*
        values.
        """
        if not nonstringiter(columns):
            columns = (columns,)
        self._assert_columns_exist(columns)
        select_clause = [self._normalize_column(x) for x in columns]
        select_clause = ', '.join(select_clause)
        select_clause = 'DISTINCT ' + select_clause

        cursor = self._execute_query(select_clause, **kwds_filter)
        return CompareSet(cursor)

    def sum(self, column, keys=None, **kwds_filter):
        """Returns :class:`CompareDict` containing sums of *column*
        values grouped by *keys*.
        """
        self._assert_columns_exist(column)
        column = self._normalize_column(column)
        sql_functions = 'SUM({0})'.format(column)
        return self._sql_aggregate(sql_functions, keys, **kwds_filter)

    def count(self, column, keys=None, **kwds_filter):
        """Returns :class:`CompareDict` containing count of non-empty
        *column* values grouped by *keys*.
        """
        self._assert_columns_exist(column)
        sql_function = "SUM(CASE COALESCE({0}, '') WHEN '' THEN 0 ELSE 1 END)"
        sql_function = sql_function.format(self._normalize_column(column))
        return self._sql_aggregate(sql_function, keys, **kwds_filter)

    def _sql_aggregate(self, sql_function, keys=None, **kwds_filter):
        """Aggregates values using SQL function select--e.g.,
        'COUNT(*)', 'SUM(col1)', etc.
        """
        # TODO: _sql_aggregate has grown messy after a handful of
        # iterations look to refactor it in the future to improve
        # maintainability.
        if not nonstringiter(sql_function):
            sql_function = (sql_function,)

        if keys == None:
            sql_function = ', '.join(sql_function)
            cursor = self._execute_query(sql_function, **kwds_filter)
            result = cursor.fetchone()
            if len(result) == 1:
                return result[0]
            return result  # <- EXIT!

        if not nonstringiter(keys):
            keys = (keys,)
        group_clause = [self._normalize_column(x) for x in keys]
        group_clause = ', '.join(group_clause)

        select_clause = '{0}, {1}'.format(group_clause, ', '.join(sql_function))
        trailing_clause = 'GROUP BY ' + group_clause

        cursor = self._execute_query(select_clause, trailing_clause, **kwds_filter)
        pos = len(sql_function)
        iterable = ((row[:-pos], getvals(row)) for row in cursor)
        if pos > 1:
            # Gets values by slicing (i.e., row[-pos:]).
            iterable = ((row[:-pos], row[-pos:]) for row in cursor)
        else:
            # Gets value by index (i.e., row[-pos]).
            iterable = ((row[:-pos], row[-pos]) for row in cursor)
        return CompareDict(iterable, keys)

    def mapreduce(self, mapper, reducer, columns, keys=None, **kwds_filter):
        obj = super(SqliteBase, self)  # 2.x compatible calling convention.
        return obj.mapreduce(mapper, reducer, columns, keys, **kwds_filter)
        # SqliteBase doesn't implement its own mapreduce() optimization.
        # A generalized, SQL optimization could do little more than the
        # already-optmized filter_rows() method.  Since the super-class'
        # mapreduce() already uses filter_rows() internally, a separate
        # optimization is unnecessary.

    def _execute_query(self, select_clause, trailing_clause=None, **kwds_filter):
        """Execute query and return cursor object."""
        try:
            stmnt, params = self._build_query(self._table, select_clause, **kwds_filter)
            if trailing_clause:
                stmnt += '\n' + trailing_clause
            cursor = self._connection.cursor()
            #print(stmnt, params)
            cursor.execute(stmnt, params)
        except Exception as e:
            exc_cls = e.__class__
            msg = '%s\n  query: %s\n  params: %r' % (e, stmnt, params)
            raise exc_cls(msg)
        return cursor

    @classmethod
    def _build_query(cls, table, select_clause, **kwds_filter):
        """Return 'SELECT' query."""
        query = 'SELECT ' + select_clause + ' FROM ' + table
        where_clause, params = cls._build_where_clause(**kwds_filter)
        if where_clause:
            query = query + ' WHERE ' + where_clause
        return query, params

    @staticmethod
    def _build_where_clause(**kwds_filter):
        """Return 'WHERE' clause that implements *kwds_filter*
        constraints.
        """
        clause = []
        params = []
        items = kwds_filter.items()
        items = sorted(items, key=lambda x: x[0])  # Ordered by key.
        for key, val in items:
            if nonstringiter(val):
                clause.append(key + ' IN (%s)' % (', '.join('?' * len(val))))
                for x in val:
                    params.append(x)
            else:
                clause.append(key + '=?')
                params.append(val)

        clause = ' AND '.join(clause) if clause else ''
        return clause, params

    def create_index(self, *columns):
        """Create an index for specified columns---can speed up testing
        in some cases.

        See :meth:`SqliteSource.create_index` for more details.
        """
        self._assert_columns_exist(columns)

        # Build index name.
        whitelist = lambda col: ''.join(x for x in col if x.isalnum())
        idx_name = '_'.join(whitelist(col) for col in columns)
        idx_name = 'idx_{0}_{1}'.format(self._table, idx_name)

        # Build column names.
        col_names = [self._normalize_column(x) for x in columns]
        col_names = ', '.join(col_names)

        # Prepare statement.
        statement = 'CREATE INDEX IF NOT EXISTS {0} ON {1} ({2})'
        statement = statement.format(idx_name, self._table, col_names)

        # Create index.
        cursor = self._connection.cursor()
        cursor.execute(statement)

    @staticmethod
    def _normalize_column(column):
        """Normalize value for use as SQLite column name."""
        if not isinstance(column, str):
            msg = "expected column of type 'str', got {0!r} instead"
            raise TypeError(msg.format(column.__class__.__name__))
        column = column.strip()
        column = column.replace('"', '""')  # Escape quotes.
        if column == '':
            column = '_empty_'
        return '"' + column + '"'


class SqliteSource(SqliteBase):
    """Loads *table* data from given SQLite *connection*:
    ::

        conn = sqlite3.connect('mydatabase.sqlite3')
        subject = datatest.SqliteSource(conn, 'mytable')
    """
    @classmethod
    def from_records(cls, data, columns=None):
        """Alternate constructor to load an existing collection of
        records into a tempoarary SQLite database.  Loads *data* (an
        iterable of lists, tuples, or dicts) into a temporary table
        using the named *columns*::

            records = [
                ('a', 'x'),
                ('b', 'y'),
                ('c', 'z'),
                ...
            ]
            subject = datatest.SqliteSource.from_records(records, ['col1', 'col2'])

        The *columns* argument can be omitted if *data* is a collection
        of dictionary or namedtuple records::

            dict_rows = [
                {'col1': 'a', 'col2': 'x'},
                {'col1': 'b', 'col2': 'y'},
                {'col1': 'c', 'col2': 'z'},
                ...
            ]
            subject = datatest.SqliteSource.from_records(dict_rows)
        """
        connection, table = _load_temp_sqlite_table(columns, data)
        return cls(connection, table)

    def create_index(self, *columns):
        """Create an index for specified columns---can speed up testing
        in some cases.

        Indexes should be added one-by-one to tune a test suite's
        over-all performance.  Creating several indexes before testing
        even begins could lead to worse performance so use them with
        discretion.

        An example:  If you're using "town" to group aggregation tests
        (like ``self.assertSubjectSum('population', ['town'])``), then
        you might be able to improve performance by adding an index for
        the "town" column::

            subject.create_index('town')

        Using two or more columns creates a multi-column index::

            subject.create_index('town', 'zipcode')

        Calling the function multiple times will create multiple
        indexes::

            subject.create_index('town')
            subject.create_index('zipcode')
        """
        # Calling super() with older convention to support Python 2.7 & 2.6.
        super(SqliteSource, self).create_index(*columns)


########################################################################
# From sources/csv.py
########################################################################
import inspect
import os
import sys
import warnings
from .._compatibility.builtins import *


class CsvSource(SqliteBase):
    """Loads CSV data from *file* (path or file-like object):
    ::

        subject = datatest.CsvSource('mydata.csv')
    """
    def __init__(self, file, encoding=None, in_memory=False, **fmtparams):
        """Initialize self."""
        # The arg *in_memory* is now unused but should be kept in signature
        # so that old code doesn't error-out.

        global DEFAULT_CONNECTION

        self._file_repr = repr(file)

        # If *file* is relative path, uses directory of calling file as base.
        if isinstance(file, str) and not os.path.isabs(file):
            calling_frame = sys._getframe(1)
            calling_file = inspect.getfile(calling_frame)
            base_path = os.path.dirname(calling_file)
            file = os.path.join(base_path, file)
            file = os.path.normpath(file)

        # Create temporary SQLite table object.
        connection = DEFAULT_CONNECTION
        cursor = connection.cursor()
        with savepoint(cursor):
            table = new_table_name(cursor)
            load_csv(cursor, table, file, encoding=encoding, **fmtparams)

        # Calling super() with older convention to support Python 2.7 & 2.6.
        super(CsvSource, self).__init__(connection, table)

    def __repr__(self):
        """Return a string representation of the data source."""
        cls_name = self.__class__.__name__
        src_file = self._file_repr
        return '{0}({1})'.format(cls_name, src_file)


########################################################################
# From sources/excel.py
########################################################################

class ExcelSource(SqliteBase):
    """Loads first worksheet from XLSX or XLS file *path*::

        subject = datatest.ExcelSource('mydata.xlsx')

    Specific worksheets can be accessed by name::

        subject = datatest.ExcelSource('mydata.xlsx', 'Sheet 2')

    .. note::
        This data source is optional---it requires the third-party
        library `xlrd <https://pypi.org/project/xlrd/>`_.
    """
    def __init__(self, path, worksheet=None, in_memory=False):
        """Initialize self."""
        try:
            import xlrd
        except ImportError:
            raise ImportError(
                "No module named 'xlrd'\n"
                "\n"
                "This is an optional data source that requires the "
                "third-party library 'xlrd'."
            )

        self._file_repr = repr(path)

        # Open Excel file and get worksheet.
        book = xlrd.open_workbook(path, on_demand=True)
        if worksheet:
            sheet = book.sheet_by_name(worksheet)
        else:
            sheet = book.sheet_by_index(0)

        # Build SQLite table from records, release resources.
        iterrows = (sheet.row(i) for i in range(sheet.nrows))
        iterrows = ([x.value for x in row] for row in iterrows)
        columns = next(iterrows)  # <- Get header row.
        connection, table = _load_temp_sqlite_table(columns, iterrows)
        book.release_resources()

        # Calling super() with older convention to support Python 2.7 & 2.6.
        super(ExcelSource, self).__init__(connection, table)


########################################################################
# From sources/pandas.py
########################################################################
import re


def _version_info(module):
    """Helper function returns a tuple containing the version number
    components for a given module.
    """
    try:
        version = module.__version__
    except AttributeError:
        version = str(module)

    def cast_as_int(value):
        try:
            return int(value)
        except ValueError:
            return value

    return tuple(cast_as_int(x) for x in re.split('[.+]', version))


class PandasSource(BaseSource):
    """Loads pandas DataFrame as a data source:

    .. code-block:: python

        subject = datatest.PandasSource(df)

    .. note::
        This data source is optional---it requires the third-party
        library `pandas <https://pypi.org/project/pandas/>`_.
    """
    def __init__(self, df):
        """Initialize self."""
        self._df = df
        self._default_index = (df.index.names == [None])
        self._pandas = __import__('pandas')

    def __repr__(self):
        """Return a string representation of the data source."""
        cls_name = self.__class__.__name__
        hex_id = hex(id(self._df))
        return "{0}(<pandas.DataFrame object at {1}>)".format(cls_name, hex_id)

    def __iter__(self):
        """Return iterable of dictionary rows (like csv.DictReader)."""
        columns = self.columns()
        if self._default_index:
            for row in self._df.itertuples(index=False):
                yield dict(zip(columns, row))
        else:
            mktup = lambda x: x if isinstance(x, tuple) else tuple([x])
            flatten = lambda x: mktup(x[0]) + mktup(x[1:])
            for row in self._df.itertuples(index=True):
                yield dict(zip(columns, flatten(row)))

    def columns(self):
        """Return list of column names."""
        if self._default_index:
            return list(self._df.columns)
        return list(self._df.index.names) + list(self._df.columns)

    def count(self, column, keys=None, **kwds_filter):
        """Returns CompareDict containing count of non-empty *column*
        values grouped by *keys*.
        """
        isnull = self._pandas.isnull
        mapper = lambda value: 1 if (value and not isnull(value)) else 0
        reducer = lambda x, y: x + y
        return self.mapreduce(mapper, reducer, column, keys, **kwds_filter)
