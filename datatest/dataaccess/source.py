# -*- coding: utf-8 -*-
from __future__ import absolute_import
import abc
import collections
import functools
import itertools
import os
from numbers import Number
from sqlite3 import Binary

from ..utils.builtins import *
from ..utils.misc import _is_nsiterable
from ..utils.misc import _get_calling_filename
from ..utils.misc import _is_sortable
from ..utils.misc import _unique_everseen
from .sqltemp import TemporarySqliteTable
from .sqltemp import _from_csv
from .result import DataResult
from .query import _DataQuery


class ItemsIter(collections.Iterator):
    """A simple wrapper used to identify iterators that should
    return a 2-tuple of key-value pairs. The underlying iterable
    should not contain duplicate keys and it should be appropriate
    for constructing a dictionary or other mapping.
    """
    def __init__(self, iterable):
        self._iterator = iter(iterable)  # <- Here, we use _iterator
                                         #    instead of __wrapped__
    def __iter__(self):                  #    because this iterable
        return self                      #    should not be
                                         #    automatically unwrapped.
    def __next__(self):
        return next(self._iterator)

    def next(self):
        return next(self._iterator)  # For Python 2 compatibility.


def _is_collection_of_items(obj):
    while hasattr(obj, '__wrapped__'):
        obj = obj.__wrapped__
    return isinstance(obj, (ItemsIter, collections.ItemsView))


class DataIterator(collections.Iterator):
    """A wrapper for results from DataQuery and DataSource method
    calls. The given *iterable* should contain data appropriate
    for constructing an object of the *intended_type*.

    The primary purpose of this wrapper is to facilitate the lazy
    evaluation of data objects (where possible) when asserting
    data validity.

    The underlying iterator is accessible through the __wrapped__
    attribute. This is useful when introspecting or rewrapping
    the iterator.
    """
    def __init__(self, iterable, intended_type):
        if not isinstance(intended_type, type):
            msg = 'intended_type must be a type, found instance of {0}'
            raise TypeError(msg.format(intended_type.__class__.__name__))

        while hasattr(iterable, '__wrapped__'):
            iterable = iterable.__wrapped__

        if isinstance(iterable, collections.Mapping):
            iterable = ItemsIter(iterable.items())

        if (issubclass(intended_type, collections.Mapping)
                and not _is_collection_of_items(iterable)):
            cls_name = iterable.__class__.__name__
            raise TypeError('when intended_type is a mapping, '
                            'iterator must be ItemsIter or ItemsView, '
                            'found {0} instead'.format(cls_name))

        self.__wrapped__ = iter(iterable)
        self.intended_type = intended_type

    def __iter__(self):
        return self

    def __repr__(self):
        cls_name = self.__class__.__name__
        rtn_name = self.intended_type.__name__
        hex_id = hex(id(self))
        template = '<{0} intended_type={1} at {2}>'
        return template.format(cls_name, rtn_name, hex_id)

    def __next__(self):
        return next(self.__wrapped__)

    def next(self):
        return next(self.__wrapped__)  # For Python 2 compatibility.

    def evaluate(self):
        intended_type = self.intended_type
        if issubclass(intended_type, collections.Mapping):
            def func(obj):
                if hasattr(obj, 'intended_type'):
                    return obj.intended_type(obj)
                return obj

            return intended_type((k, func(v)) for k, v in self)

        return intended_type(self)


def _get_intended_type(obj):
    """Return object's intended_type property. If the object does not
    have an intended_type property and is a mapping, sequence, or set,
    then return the type of the object itself. If the object is an
    iterable, return None. Raises a Type error for any other object.
    """
    if hasattr(obj, 'intended_type'):
        return obj.intended_type  # <- EXIT!

    #if _is_collection_of_items(obj):
    #    return dict

    if isinstance(obj, (collections.Mapping,
                        collections.Sequence,
                        collections.Set)):
        return type(obj)  # <- EXIT!

    if isinstance(obj, collections.Iterable):
        return None  # <- EXIT!

    cls_name = obj.__class__.__name__
    err_msg = 'unable to determine intended type for {0!r} instance'
    raise TypeError(err_msg.format(cls_name))


def _apply_to_data(function, data_iterator):
    """Applies a *function* of one argument to the to the given
    DataIterator *data_iterator*.
    """
    if _is_collection_of_items(data_iterator):
        result = ItemsIter((k, function(v)) for k, v in data_iterator)
        return DataIterator(result, _get_intended_type(data_iterator))
    return function(data_iterator)


def _map_data(function, iterable):
    def wrapper(iterable):
        if _is_nsiterable(iterable):
            intended_type = _get_intended_type(iterable)
            return DataIterator(map(function, iterable), intended_type)
        return function(iterable)

    return _apply_to_data(wrapper, iterable)


def _reduce_data(function, iterable):
    def wrapper(iterable):
        if not _is_nsiterable(iterable):
            return iterable  # <- Not iterable, return object.
        return functools.reduce(function, iterable)

    return _apply_to_data(wrapper, iterable)


def _filter_data(function, iterable):
    def wrapper(iterable):
        if not _is_nsiterable(iterable):
            msg= 'filter expects a non-string iterable, found {0}'
            raise TypeError(msg.format(iterable.__class__.__name__))
        filtered_data = filter(function, iterable)
        return DataIterator(filtered_data, _get_intended_type(iterable))

    return _apply_to_data(wrapper, iterable)


def _sqlite_cast_as_real(value):
    """Convert value to REAL (float) or default to 0.0 to match SQLite
    behavior. See the "Conversion Processing" table in the "CAST
    expressions" section for details:

        https://www.sqlite.org/lang_expr.html#castexpr
    """
    try:
        return float(value)
    except ValueError:
        return 0.0


def _sqlite_sum(iterable):
    """Sum the elements and return the total (should match SQLite
    behavior).
    """
    if not _is_nsiterable(iterable):
        iterable = [iterable]
    iterable = (_sqlite_cast_as_real(x) for x in iterable if x != None)
    try:
        start_value = next(iterable)
    except StopIteration:  # From SQLite docs: "If there are no non-NULL
        return None        # input rows then sum() returns NULL..."
    return sum(iterable, start_value)


def _sqlite_count(iterable):
    """Returns the number non-NULL (!= None) elements in iterable."""
    if not _is_nsiterable(iterable):
        iterable = [iterable]
    return sum(1 for x in iterable if x != None)


# The SQLite BLOB/Binary type in sortable Python 2 but unsortable in Python 3.
_unsortable_blob_type = not _is_sortable(Binary(b'0'))


def _sqlite_sortkey(value):
    """Key function for use with sorted(), min(), max(), etc. that
    makes a best effort to match SQLite ORDER BY behavior for
    supported classes.

    From SQLite docs:

        "...values with storage class NULL come first, followed by
        INTEGER and REAL values interspersed in numeric order, followed
        by TEXT values in collating sequence order, and finally BLOB
        values in memcmp() order."

    For more details see "Datatypes In SQLite Version 3" section
    "4.1. Sort Order" <https://www.sqlite.org/datatype3.html>.
    """
    if value is None:              # NULL (sort group 0)
        return (0, 0)
    if isinstance(value, Number):  # INTEGER and REAL (sort group 1)
        return (1, value)
    if isinstance(value, str):     # TEXT (sort group 2)
        return (2, value)
    if isinstance(value, Binary):  # BLOB (sort group 3)
        if _unsortable_blob_type:
            value = bytes(value)
        return (3, value)
    return (4, value)  # unsupported type (sort group 4)


def _sqlite_avg(iterable):
    """Return the average of elements in iterable. Returns None if all
    elements are None.
    """
    if not _is_nsiterable(iterable):
        iterable = [iterable]
    iterable = (x for x in iterable if x != None)
    total = 0.0
    count = 0
    for x in iterable:
        total = total + _sqlite_cast_as_real(x)
        count += 1
    return total / count if count else None


def _sqlite_min(iterable):
    """Return the minimum non-None value of all values. Returns
    None only if all values are None.
    """
    if not _is_nsiterable(iterable):
        return iterable  # <- EXIT!
    iterable = (x for x in iterable if x != None)
    return min(iterable, default=None, key=_sqlite_sortkey)


def _sqlite_max(iterable):
    """Return the maximum value of all values. Returns None if all
    values are None.
    """
    if not _is_nsiterable(iterable):
        return iterable  # <- EXIT!
    return max(iterable, default=None, key=_sqlite_sortkey)


def _sqlite_distinct(iterable):
    """Filter iterable to unique values, while maintaining
    intended_type.
    """
    def dodistinct(itr):
        if not _is_nsiterable(itr):
            return itr
        return DataIterator(_unique_everseen(itr), _get_intended_type(itr))

    if _is_collection_of_items(iterable):
        result = ItemsIter((k, dodistinct(v)) for k, v in iterable)
        return DataIterator(result, _get_intended_type(iterable))
    return dodistinct(iterable)


def _cast_as_set(iterable):
    """Change intended_type to set."""
    def makeset(itr):
        if not _is_nsiterable(itr):
            itr = [itr]
        return DataIterator(itr, intended_type=set)

    if _is_collection_of_items(iterable):
        result = ItemsIter((k, makeset(v)) for k, v in iterable)
        return DataIterator(result, _get_intended_type(iterable))
    return makeset(iterable)


def _set_data(iterable):
    """Filter iterable to unique values and change intended_type to
    set.
    """
    return _cast_as_set(_sqlite_distinct(iterable))


def _get_step_repr(step):
    """Helper function returns repr for a single query step."""
    func, args, kwds = step

    def _callable_name_or_repr(x):  # <- Helper function for
        if callable(x):             #    the helper function!
            try:
                return x.__name__
            except NameError:
                pass
        return repr(x)

    func_repr = _callable_name_or_repr(func)

    args_repr = ', '.join(_callable_name_or_repr(x) for x in args)

    kwds_repr = kwds.items()
    kwds_repr = [(k, _callable_name_or_repr(v)) for k, v in kwds_repr]
    kwds_repr = ['{0}={1}'.format(k, v) for k, v in kwds_repr]
    kwds_repr = ', '.join(kwds_repr)
    return '{0}, ({1}), {{{2}}}'.format(func_repr, args_repr, kwds_repr)


class _RESULT_TOKEN(object):
    def __repr__(self):
        return '<result>'
RESULT_TOKEN = _RESULT_TOKEN()
del _RESULT_TOKEN


class DataQuery2(object):
    def __init__(self, selection, **where):
        self._query_steps = tuple([
            (getattr, (RESULT_TOKEN, '_select2'), {}),
            (RESULT_TOKEN, (selection,), where),
        ])
        self._initializer = None

    @staticmethod
    def _validate_initializer(initializer):
        if not isinstance(initializer, DataSource):
            raise TypeError('expected {0!r}, got {1!r}'.format(
                DataSource.__name__,
                initializer.__class__.__name__,
            ))

    #@staticmethod
    #def _validate_steps(steps):
    #    pass

    @classmethod
    def _from_parts(cls, query_steps=None, initializer=None):
        if initializer:
            cls._validate_initializer(initializer)

        if query_steps:
            query_steps = tuple(query_steps)
        else:
            query_steps = tuple()

        new_cls = cls.__new__(cls)
        new_cls._query_steps = query_steps
        new_cls._initializer = initializer
        return new_cls

    def _append_new(self, step):
        steps = self._query_steps + (step,)
        new_query = self.__class__._from_parts(steps, self._initializer)
        return new_query

    def map(self, function):
        step = (_map_data, (function, RESULT_TOKEN), {})
        return self._append_new(step)

    def filter(self, function):
        step = (_filter_data, (function, RESULT_TOKEN), {})
        return self._append_new(step)

    def reduce(self, function):
        step = (_reduce_data, (function, RESULT_TOKEN), {})
        return self._append_new(step)

    def sum(self):
        step = (_apply_to_data, (_sqlite_sum, RESULT_TOKEN,), {})
        return self._append_new(step)

    def count(self):
        step = (_apply_to_data, (_sqlite_count, RESULT_TOKEN,), {})
        return self._append_new(step)

    def avg(self):
        step = (_apply_to_data, (_sqlite_avg, RESULT_TOKEN,), {})
        return self._append_new(step)

    def min(self):
        step = (_apply_to_data, (_sqlite_min, RESULT_TOKEN,), {})
        return self._append_new(step)

    def max(self):
        step = (_apply_to_data, (_sqlite_max, RESULT_TOKEN,), {})
        return self._append_new(step)

    def distinct(self):
        step = (_sqlite_distinct, (RESULT_TOKEN,), {})
        return self._append_new(step)

    def set(self):
        step = (_set_data, (RESULT_TOKEN,), {})
        return self._append_new(step)

    @staticmethod
    def _optimize(query_steps):
        try:
            step_0 = query_steps[0]
            step_1 = query_steps[1]
            step_2 = query_steps[2]
            remaining_steps = query_steps[3:]
        except IndexError:
            return query_steps  # <- EXIT!

        if step_0 != (getattr, (RESULT_TOKEN, '_select2'), {}):
            return query_steps  # <- EXIT!

        if step_2[0] == _apply_to_data:
            func_dict = {
                _sqlite_sum: 'SUM',
                _sqlite_count: 'COUNT',
                _sqlite_avg: 'AVG',
                _sqlite_min: 'MIN',
                _sqlite_max: 'MAX',
            }
            py_function = step_2[1][0]
            sqlite_function = func_dict.get(py_function, None)
            if sqlite_function:
                func_1, args_1, kwds_1 = step_1
                args_1 = (sqlite_function,) + args_1  # <- Add SQL function
                optimized_steps = (                   #    as 1st arg.
                    (getattr, (RESULT_TOKEN, '_select2_aggregate'), {}),
                    (func_1, args_1, kwds_1),
                )
            else:
                optimized_steps = ()
        elif step_2 == (_sqlite_distinct, (RESULT_TOKEN,), {}):
            optimized_steps = (
                (getattr, (RESULT_TOKEN, '_select2_distinct'), {}),
                step_1,
            )
        elif step_2 == (_set_data, (RESULT_TOKEN,), {}):
            optimized_steps = (
                (getattr, (RESULT_TOKEN, '_select2_distinct'), {}),
                step_1,
                (_cast_as_set, (RESULT_TOKEN,), {}),
            )
        else:
            optimized_steps = ()

        if optimized_steps:
            return optimized_steps + remaining_steps
        return query_steps

    def execute(self, initializer=None, **kwds):
        """
        execute(initializer=None, *, lazy=False, optimize=True)

        Execute query and return its result.

        Use ``lazy=True`` to execute the query but leave the result
        in its raw, iterator form. By default, results are eagerly
        evaluated and loaded into memory.

        Use ``optimize=False`` to turn-off query optimization.
        """
        result = initializer or self._initializer
        if result is None:
            raise ValueError('must provide initializer, None found')
        self._validate_initializer(result)

        lazy = kwds.pop('lazy', False)         # Emulate keyword-only
        optimize = kwds.pop('optimize', True)  # behavior for 2.7 and
        if kwds:                               # 2.6 compatibility.
            key, _ = kwds.popitem()
            raise TypeError('got an unexpected keyword '
                            'argument {0!r}'.format(key))

        query_steps = self._query_steps
        if optimize:
            query_steps = self._optimize(query_steps)

        replace_token = lambda x: result if x is RESULT_TOKEN else x
        for step in query_steps:
            function, args, keywords = step  # Unpack 3-tuple.
            function = replace_token(function)
            args = tuple(replace_token(x) for x in args)
            keywords = dict((k, replace_token(v)) for k, v in keywords.items())
            result = function(*args, **keywords)

        if isinstance(result, DataIterator) and not lazy:
            result = result.evaluate()

        return result

    def explain(self):
        """Return string of current query steps."""
        unoptimized_steps = self._query_steps
        steps = [_get_step_repr(step) for step in unoptimized_steps]
        steps = '\n'.join('  {0}'.format(step) for step in steps)
        output = 'Steps:\n{0}'.format(steps)

        optimized_steps = self._optimize(unoptimized_steps)
        if optimized_steps != unoptimized_steps:
            steps = [_get_step_repr(step) for step in optimized_steps]
            steps = '\n'.join('  {0}'.format(step) for step in steps)
            output += '\n\nOptimized steps:\n{0}'.format(steps)

        return output


class DataQuery(_DataQuery):
    @staticmethod
    def _validate_initializer(initializer):
        if not isinstance(initializer, DataSource):
            raise TypeError('expected {0!r}, got {1!r}'.format(
                DataSource.__name__,
                initializer.__class__.__name__,
            ))

    @classmethod
    def _from_parts(cls, query_steps=None, initializer=None):
        if initializer:
            cls._validate_initializer(initializer)
        return super(DataQuery, cls)._from_parts(query_steps, initializer)

    def eval(self, initializer=None, **kwds):
        initializer = initializer or self._initializer
        self._validate_initializer(initializer)
        return super(DataQuery, self).eval(initializer, **kwds)


class DataSource(object):
    """A basic data source to quickly load and query data::

        data = [
            ['a', 'x', 100],
            ['b', 'y', 100],
            ['c', 'x', 100],
            ['d', 'x', 100],
            ['e', 'y', 100],
        ]
        columns = ['col1', 'col2', 'col3']
        source = datatest.DataSource(data, columns)

    If *data* is an iterable of :py:class:`dict` or
    :py:func:`namedtuple <collections.namedtuple>` rows,
    then *columns* can be omitted::

        data = [
            {'col1': 'a', 'col2': 'x', 'col3': 100},
            {'col1': 'b', 'col2': 'y', 'col3': 100},
            {'col1': 'c', 'col2': 'x', 'col3': 100},
            {'col1': 'd', 'col2': 'x', 'col3': 100},
            {'col1': 'e', 'col2': 'y', 'col3': 100},
        ]
        source = datatest.DataSource(data)
    """
    def __init__(self, data, columns=None):
        """Initialize self."""
        temptable = TemporarySqliteTable(data, columns)
        self._connection = temptable.connection
        self._table = temptable.name

    @classmethod
    def from_csv(cls, file, encoding=None, relative_to=None, **fmtparams):
        """Initialize :class:`DataSource` using CSV data from *file*
        (a path or file-like object)::

            source = datatest.DataSource.from_csv('mydata.csv')
        """
        if not _is_nsiterable(file):
            file = [file]

        if relative_to is None:
            relative_to = _get_calling_filename(frame_index=2)
        dirname = os.path.dirname(relative_to)

        def get_path(f):
            if isinstance(f, str) and not os.path.isabs(f):
                f = os.path.join(dirname, f)
            return os.path.normpath(f)
        file = [get_path(f) for f in file]

        new_cls = cls.__new__(cls)
        temptable = _from_csv(file, encoding, **fmtparams)
        new_cls._connection = temptable.connection
        new_cls._table = temptable.name
        return new_cls

    @classmethod
    def from_excel(cls, path, worksheet=0):
        """Initialize :class:`DataSource` using worksheet data from
        an XLSX or XLS file *path*.

        Load first worksheet::

            source = datatest.DataSource.from_excel('mydata.xlsx')

        Specific worksheets can be loaded by name or index::

            source = datatest.DataSource.from_excel('mydata.xlsx', 'Sheet 2')

        .. note::
            This constructor requires the optional, third-party
            library `xlrd <https://pypi.python.org/pypi/xlrd>`_.
        """
        try:
            import xlrd
        except ImportError:
            raise ImportError(
                "No module named 'xlrd'\n"
                "\n"
                "This is an optional data source that requires the "
                "third-party library 'xlrd'."
            )

        book = xlrd.open_workbook(path, on_demand=True)
        try:
            if isinstance(worksheet, int):
                sheet = book.sheet_by_index(worksheet)
            else:
                sheet = book.sheet_by_name(worksheet)
            data = (sheet.row(i) for i in range(sheet.nrows))  # Build *data*
            data = ([x.value for x in row] for row in data)    # and *columns*
            columns = next(data)                               # from rows.
            new_instance = cls(data, columns)  # <- Create instance.
        finally:
            book.release_resources()

        return new_instance

    def columns(self):
        """Return list of column names.

        .. code-block:: python

            source = datatest.DataSource(...)
            columns = source.columns()
        """
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

    def _assert_columns_exist(self, columns):
        """Asserts that given columns are present in data source,
        raises LookupError if columns are missing.
        """
        if not _is_nsiterable(columns):
            columns = (columns,)
        self_cols = self.columns()
        is_missing = lambda col: col not in self_cols
        missing = [c for c in columns if is_missing(c)]
        if missing:
            missing = ', '.join(repr(x) for x in missing)
            msg = '{0} not in {1}'.format(missing, self.__repr__())
            raise LookupError(msg)

    def __call__(self, *columns, **kwds_filter):
        return DataQuery._from_parts(['_select', (columns, kwds_filter)], self)
        #steps = [
        #    (getattr, (RESULT_TOKEN, '_select2',), {}),
        #    (RESULT_TOKEN, columns, kwds_filter),
        #]
        #return DataQuery2._from_parts(steps, initializer=self)

    def _prepare_column_groups(self, *columns):
        """Returns tuple of columns split into key and value groups."""
        if _is_nsiterable(columns[0]):
            if len(columns) != 1:
                raise ValueError('cannot mix container and variable args')
            if isinstance(columns[0], dict):
                key_columns, value_columns = tuple(columns[0].items())[0]
                if isinstance(key_columns, str):
                    key_columns = tuple([key_columns])
                if isinstance(value_columns, (str, collections.Mapping)):
                    value_columns = tuple([value_columns])
            else:
                key_columns = tuple()
                value_columns = tuple(columns[0])
        else:
            key_columns = tuple()
            value_columns = columns
        self._assert_columns_exist(key_columns + value_columns)
        key_columns = tuple(self._normalize_column(x) for x in key_columns)
        value_columns = tuple(self._normalize_column(x) for x in value_columns)
        return key_columns, value_columns

    def _sql_select_cols(self, selection):
        """Returns a string of normalized columns to use with a
        SELECT clause.
        """
        if isinstance(selection, str):
            return self._normalize_column(selection)  # <- EXIT!

        if isinstance(selection, (collections.Sequence, collections.Set)):
            row_type = type(selection)
            select_clause = (self._normalize_column(x) for x in selection)
            return ', '.join(select_clause)  # <- EXIT!

        if isinstance(selection, collections.Mapping):
            assert len(selection) == 1
            key, value = tuple(selection.items())[0]
            if isinstance(key, str):
                key = (key,)
            if isinstance(value, str):
                value = (value,)
            key_tuple = tuple(self._normalize_column(x) for x in key)
            value_tuple = tuple(self._normalize_column(x) for x in value)
            return ', '.join(key_tuple + value_tuple)  # <- EXIT!

        raise TypeError('type {0!r} not supported'.format(type(selection)))

    def _sql_group_order_cols(self, selection):
        """Returns a string of normalized column names appropriate
        for use with a GROUP BY or ORDER BY clause.

        The *selection* can be a string, sequence, set or mapping--see
        the _select2() method for details.
        """
        if isinstance(selection, str):
            return self._normalize_column(selection)  # <- EXIT!

        if isinstance(selection, (collections.Sequence, collections.Set)):
            columns = tuple(self._normalize_column(x) for x in selection)
            return ', '.join(columns)  # <- EXIT!

        if isinstance(selection, collections.Mapping):
            key = tuple(selection.keys())[0]
            if isinstance(key, str):
                return self._normalize_column(key)  # <- EXIT
            key_tuple = tuple(self._normalize_column(x) for x in key)
            return ', '.join(key_tuple)  # <- EXIT!

        raise TypeError('type {0!r} not supported'.format(type(selection)))

    def _format_results(self, selection, cursor):
        """Returns iterator of results formatted by *selection* types
        from DBAPI2-compliant *cursor*.

        The *selection* can be a string, sequence, set or mapping--see
        the _select2() method for details.
        """
        if isinstance(selection, str):
            result = (row[0] for row in cursor)
            return DataIterator(result, intended_type=list) # <- EXIT!

        if isinstance(selection, collections.Sequence):
            result_type = type(selection)
            result = (result_type(x) for x in cursor)
            return DataIterator(result, intended_type=list) # <- EXIT!

        if isinstance(selection, collections.Set):
            result_type = type(selection)
            result = (result_type(x) for x in cursor)
            return DataIterator(result, intended_type=set) # <- EXIT!

        if isinstance(selection, collections.Mapping):
            result_type = type(selection)
            key, value = tuple(selection.items())[0]
            key_type = type(key)
            value_type = type(value)
            slice_index = 1 if issubclass(key_type, str) else len(key)

            if issubclass(key_type, str):
                keyfunc = lambda row: row[0]
            else:
                keyfunc = lambda row: key_type(row[:slice_index])
            grouped = itertools.groupby(cursor, keyfunc)

            if issubclass(value_type, str):
                def valuefunc(group):
                    result = (row[-1] for row in group)
                    return DataIterator(result, intended_type=list)
            else:
                def valuefunc(group):
                    group = (row[slice_index:] for row in group)
                    result = (value_type(row) for row in group)
                    return DataIterator(result, intended_type=list)

            result =  ItemsIter((k, valuefunc(g)) for k, g in grouped)
            return DataIterator(result, intended_type=result_type) # <- EXIT!

        raise TypeError('type {0!r} not supported'.format(type(selection)))

    def _select2(self, selection, **where):
        select = self._sql_select_cols(selection)
        if isinstance(selection, collections.Mapping):
            order_cols = self._sql_group_order_cols(selection)
            order_by = 'ORDER BY {0}'.format(order_cols)
        else:
            order_by = None
        cursor = self._execute_query(select, order_by, **where)
        return self._format_results(selection, cursor)

    def _select2_distinct(self, selection, **where):
        select_cols = self._sql_select_cols(selection)
        select = 'DISTINCT {0}'.format(select_cols)
        if isinstance(selection, collections.Mapping):
            order_cols = self._sql_group_order_cols(selection)
            order_by = 'ORDER BY {0}'.format(order_cols)
        else:
            order_by = None
        cursor = self._execute_query(select, order_by, **where)
        return self._format_results(selection, cursor)

    def _select2_aggregate(self, sqlfunc, selection, **where):
        """."""
        sqlfunc = sqlfunc.upper()

        if isinstance(selection, collections.Mapping):
            value_cols = tuple(selection.values())[0]
            if isinstance(value_cols, str):
                normalized = self._normalize_column(value_cols)
                formatted = '{0}({1})'.format(sqlfunc, normalized)
            else:
                normalized = [self._normalize_column(x) for x in value_cols]
                formatted = ['{0}({1})'.format(sqlfunc, x) for x in normalized]
                formatted = ', '.join(formatted)
            key_cols = self._sql_group_order_cols(selection)
            select = '{0}, {1}'.format(key_cols, formatted)
            group_by = 'GROUP BY {0}'.format(key_cols)
        else:
            if isinstance(selection, str):
                normalized = self._normalize_column(selection)
                select = '{0}({1})'.format(sqlfunc, normalized)
                group_by = None
            elif isinstance(selection, (collections.Sequence, collections.Set)):
                normalized = [self._normalize_column(x) for x in selection]
                formatted = ['{0}({1})'.format(sqlfunc, x) for x in normalized]
                select = ', '.join(formatted)
                group_by = None
            else:
                raise TypeError('type {0!r} not supported'.format(type(selection)))

        cursor = self._execute_query(select, group_by, **where)
        results = self._format_results(selection, cursor)

        if isinstance(selection, collections.Mapping):
            results = ItemsIter((k, next(v)) for k, v in results)
            return DataIterator(results, intended_type=dict)
        return next(results)


    def _select(self, *columns, **kwds_filter):
        key_columns, value_columns = self._prepare_column_groups(*columns)
        select_clause = ', '.join(key_columns + value_columns)

        if not key_columns:
            cursor = self._execute_query(
                select_clause,
                **kwds_filter
            )
            if len(value_columns) == 1:
                return DataResult((row[0] for row in cursor), list)  # <- EXIT!
            return DataResult(cursor, list)  # <- EXIT!

        trailing_clause = 'ORDER BY {0}'.format(', '.join(key_columns))
        cursor = self._execute_query(
            select_clause,
            trailing_clause,
            **kwds_filter
        )
        # If one key column, get single key value, else get key tuples.
        slice_index = len(key_columns)
        if slice_index == 1:
            keyfunc = lambda row: row[0]
        else:
            keyfunc = lambda row: row[:slice_index]

        # If one value column, get iterable of single values, else get
        # an iterable of row tuples.
        if len(value_columns) == 1:
            valuefunc = lambda group: (row[-1] for row in group)
        else:
            valuefunc = lambda group: (row[slice_index:] for row in group)

        # Parse rows.
        grouped = itertools.groupby(cursor, keyfunc)
        grouped = ((k, valuefunc(g)) for k, g in grouped)
        grouped = ((k, DataResult(g, evaluates_to=list)) for k, g in grouped)
        return DataResult(grouped, evaluates_to=dict)

    def _select_distinct(self, *columns, **kwds_filter):
        key_columns, value_columns = self._prepare_column_groups(*columns)
        select_clause = ', '.join(key_columns + value_columns)
        select_clause = 'DISTINCT ' + select_clause

        if not key_columns:
            cursor = self._execute_query(
                select_clause,
                **kwds_filter
            )
            if len(value_columns) == 1:
                return DataResult((row[0] for row in cursor), list)  # <- EXIT!
            return DataResult(cursor, list)  # <- EXIT!

        trailing_clause = 'ORDER BY {0}'.format(', '.join(key_columns))
        cursor = self._execute_query(
            select_clause,
            trailing_clause,
            **kwds_filter
        )
        # If one key column, get single key value, else get key tuples.
        slice_index = len(key_columns)
        if slice_index == 1:
            keyfunc = lambda row: row[0]
        else:
            keyfunc = lambda row: row[:slice_index]

        # If one value column, get iterable of single values, else get
        # an iterable of row tuples.
        if len(value_columns) == 1:
            valuefunc = lambda group: (row[-1] for row in group)
        else:
            valuefunc = lambda group: (row[slice_index:] for row in group)

        # Parse rows.
        grouped = itertools.groupby(cursor, keyfunc)
        grouped = ((k, valuefunc(g)) for k, g in grouped)
        grouped = ((k, DataResult(g, evaluates_to=list)) for k, g in grouped)
        return DataResult(grouped, evaluates_to=dict)

    def _select_aggregate(self, sqlfunc, *columns, **kwds_filter):
        key_columns, value_columns = self._prepare_column_groups(*columns)
        if len(value_columns) != 1:
            raise ValueError('expects single value column')
        sql_function = '{0}({1})'.format(sqlfunc, value_columns[0])

        if not key_columns:
            cursor = self._execute_query(sql_function, **kwds_filter)
            result = cursor.fetchone()
            return result[0]  # <- EXIT!

        group_by = ', '.join(key_columns)
        select_clause = '{0}, {1}'.format(group_by, sql_function)
        trailing_clause = 'GROUP BY ' + group_by

        cursor = self._execute_query(
            select_clause,
            trailing_clause,
            **kwds_filter
        )
        # If one key column, get single key value, else get key tuples.
        slice_index = len(key_columns)
        if slice_index == 1:
            keyfunc = lambda row: row[0]
        else:
            keyfunc = lambda row: row[:slice_index]

        # Parse rows.
        iterable = ((keyfunc(x), x[-1]) for x in cursor)
        return DataResult(iterable, evaluates_to=dict)

    def __repr__(self):
        """Return a string representation of the data source."""
        cls_name = self.__class__.__name__
        conn_name = str(self._connection)
        tbl_name = self._table
        return '{0}({1}, table={2!r})'.format(cls_name, conn_name, tbl_name)

    def _execute_query(self, select_clause, trailing_clause=None, **kwds_filter):
        """Execute query and return cursor object."""
        try:
            stmnt, params = self._build_query(self._table, select_clause, **kwds_filter)
            if trailing_clause:
                stmnt += '\n' + trailing_clause
            cursor = self._connection.cursor()
            cursor.execute('PRAGMA synchronous=OFF')
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
            if _is_nsiterable(val):
                clause.append(key + ' IN (%s)' % (', '.join('?' * len(val))))
                for x in val:
                    params.append(x)
            else:
                clause.append(key + '=?')
                params.append(val)

        clause = ' AND '.join(clause) if clause else ''
        return clause, params

    def create_index(self, *columns):
        """Create an index for specified columns---can speed up
        testing in many cases.

        If you repeatedly use the same few columns to group or
        filter results, then you can often improve performance by
        adding an index for these columns::

            source.create_index('town')

        Using two or more columns creates a multi-column index::

            source.create_index('town', 'postal_code')

        Calling the function multiple times will create multiple
        indexes::

            source.create_index('town')
            source.create_index('postal_code')

        .. note:: Indexes should be added with discretion to tune
                  a test suite's over-all performance.  Creating
                  several indexes before testing even begins could
                  lead to longer run times so use indexes with care.
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
        cursor.execute('PRAGMA synchronous=OFF')
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
