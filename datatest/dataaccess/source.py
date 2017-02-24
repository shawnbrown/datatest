# -*- coding: utf-8 -*-
from __future__ import absolute_import
import abc
import collections
import functools
import itertools
import os

from ..utils.misc import _is_nscontainer
from ..utils.misc import _get_calling_filename
from .sqltemp import TemporarySqliteTable
from .sqltemp import _from_csv
from .result import DataResult
from .query import _DataQuery


class _RESULT_TOKEN(object):
    def __repr__(self):
        return '<result>'
RESULT_TOKEN = _RESULT_TOKEN()
del _RESULT_TOKEN


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


def _get_intended_type(obj):
    """Return object's intended_type property. If the object does not
    have an intended_type property and is a mapping, sequence, or set,
    then return the type of the object itself. If the object is an
    iterable, return None. Raises a Type error for any other object.
    """
    if hasattr(obj, 'intended_type'):
        return obj.intended_type  # <- EXIT!

    if isinstance(obj, (collections.Mapping,
                        collections.Sequence,
                        collections.Set)):
        return type(obj)  # <- EXIT!

    if isinstance(obj, collections.Iterable):
        return None  # <- EXIT!

    cls_name = obj.__class__.__name__
    err_msg = 'unable to determine intended type for {0!r} instance'
    raise TypeError(err_msg.format(cls_name))


def _map_data(function, iterable):
    intended_type = _get_intended_type(iterable)
    if _is_collection_of_items(iterable):
        map_func = lambda v: DataIterator(map(function, v), list)
        result = ((k, map_func(v)) for k, v in iterable)
    else:
        result = map(function, iterable)
    return DataIterator(result, intended_type)


def _filter_data(function, iterable):
    intended_type = _get_intended_type(iterable)
    if _is_collection_of_items(iterable):
        filter_func = lambda v: DataIterator(filter(function, v), list)
        result = ((k, filter_func(v)) for k, v in iterable)
    else:
        result = filter(function, iterable)
    return DataIterator(result, intended_type)


def _reduce_data(function, iterable):
    intended_type = _get_intended_type(iterable)
    if _is_collection_of_items(iterable):
        reduce_func = lambda v: functools.reduce(function, v)
        result = ((k, reduce_func(v)) for k, v in iterable)
        return DataIterator(result, intended_type)  # <- EXIT!
    return functools.reduce(function, iterable)


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

    def execute(self, initializer=None, **kwds):
        """
        execute(initializer=None, *, lazy=False, optimize=True)

        Evaluate query and return its result.

        Use ``lazy=True`` to evaluate the query but leave the result
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

        replace_token = lambda x: result if x is RESULT_TOKEN else x
        for step in self._query_steps:
            function, args, keywords = step  # Unpack 3-tuple.
            function = replace_token(function)
            args = tuple(replace_token(x) for x in args)
            keywords = dict((k, replace_token(v)) for k, v in keywords.items())
            result = function(*args, **keywords)

        if isinstance(result, DataIterator) and not lazy:
            def evaluate(obj):
                if isinstance(obj, DataIterator):
                    return obj.intended_type(obj)
                return obj

            if issubclass(result.intended_type, collections.Mapping):
                result = dict((k, evaluate(v)) for k, v in result)
            else:
                result = evaluate(result)

        return result

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
        if not _is_nscontainer(file):
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
        if not _is_nscontainer(columns):
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
        if _is_nscontainer(columns[0]):
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
            result = (result_type(x) for x  in cursor)
            return DataIterator(result, intended_type=list) # <- EXIT!

        if isinstance(selection, collections.Set):
            result_type = type(selection)
            result = (result_type(x) for x  in cursor)
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
                    return list(row[-1] for row in group)
            else:
                def valuefunc(group):
                    group = (row[slice_index:] for row in group)
                    return list(value_type(row) for row in group)
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
        if isinstance(selection, str):
            normalized = self._normalize_column(selection)
            select = '{0}({1})'.format(sqlfunc, normalized)
            group_by = None
        elif isinstance(selection, (collections.Sequence, collections.Set)):
            normalized = [self._normalize_column(x) for x in selection]
            formatted = ['{0}({1})'.format(sqlfunc, x) for x in normalized]
            select = ', '.join(formatted)
            group_by = None
        elif isinstance(selection, collections.Mapping):
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

        cursor = self._execute_query(select, group_by, **where)
        results = self._format_results(selection, cursor)

        if not isinstance(selection, collections.Mapping):
            return next(results)  # <- EXIT!
        results = ((k, v[0]) for k, v in results)
        return results

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
            if _is_nscontainer(val):
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
