# -*- coding: utf-8 -*-
from numbers import Number
from sqlite3 import Binary

from ..utils.builtins import *
from ..utils import collections
from ..utils import itertools
from ..utils import functools
from ..utils import TemporarySqliteTable
from ..utils import UnicodeCsvReader
from ..compare import _is_nscontainer
from ..allow import _expects_multiple_params


def _is_sortable(obj):
    """Returns True if *obj* is sortable else returns False."""
    try:
        sorted([obj, obj])
        return True
    except TypeError:
        return False


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
    """Sum the elements and return the total."""
    iterable = (_sqlite_cast_as_real(x) for x in iterable if x != None)
    try:
        start_value = next(iterable)
    except StopIteration:  # From SQLite docs: "If there are no non-NULL
        return None        # input rows then sum() returns NULL..."
    return sum(iterable, start_value)


class IterSequence(collections.Iterator):
    """A queryable iterator that supports most sequence methods.

    IterSequence supports map(), reduce(), etc. as well as all sequence
    behaviors except len() and reversed(). Since these methods will
    consume the iterator, only one call can be made per instance.
    """
    def __init__(self, iterable):
        self._iterator = iter(iterable)
        self._exhausted_by = None

    def _exhaust_iterator(self, name, *args):
        args_repr = ', '.join(repr(x) for x in args)
        self._exhausted_by = '{0}({1})'.format(name, args_repr)
        self._iterator = iter([])  # Set empty iterator.

    def __iter__(self):
        """x.__iter__() <==> iter(x)"""
        return self

    def __next__(self):
        """x.__next__() <==> next(x)"""
        try:
            return next(self._iterator)
        except StopIteration:
            self._exhaust_iterator('__next__')
            raise

    def next(self):  # For Python 2.7 and earlier.
        return self.__next__()

    def __getitem__(self, index):
        """x.__getitem__(index) <==> x[index]"""
        item = next(itertools.islice(self._iterator, index, None))
        self._exhaust_iterator('__getitem__({0})'.format(index))
        return item

    def index(self, value, start=0, stop=None):
        """Return zero-based index in the iterator of the first item
        that matches value. Raises a ValueError if there is no such
        item.
        """
        iterator = itertools.islice(self._iterator, start, stop)
        msg = 'index({0!r}, {1!r}, {2!r})'.format(value, start, stop)
        self._exhaust_iterator(msg)
        for i, x in enumerate(iterator, start):
            if x == value:
                return i
        raise ValueError('{0!r} is not in iterable'.format(value))

    def count(self, value):
        """Return the number of times value appears in the iterator."""
        result = sum(1 for x in self._iterator if x == value)
        self._exhaust_iterator('count', value)
        return result

    def __contains__(self, value):
        """x.__contains__(value) <==> value in x"""
        result = False
        for element in self._iterator:
            if element == value:
                result = True
                break
        self._exhaust_iterator('__contains__', value)
        return result

    def __repr__(self):
        """x.__repr__() <==> repr(x)"""
        class_name = self.__class__.__name__
        iterator_repr = repr(self._iterator)
        return '{0}({1})'.format(class_name, iterator_repr)

    def map(self, function):
        """Return a new IterSequence that applies *function* to the
        elements, yielding the results.
        """
        if _expects_multiple_params(function):
            result = IterSequence(function(*x) for x in self._iterator)
        else:
            result = IterSequence(function(x) for x in self._iterator)
        name = getattr(function, '__name__', repr(function))
        self._exhaust_iterator('map', name)
        return result

    def reduce(self, function):
        """Apply a *function* of two arguments cumulatively to the
        elements, from left to right, so as to reduce the values to a
        single result.
        """
        result = functools.reduce(function, self._iterator)
        name = getattr(function, '__name__', repr(function))
        self._exhaust_iterator('reduce', name)
        return result

    def sum(self):
        """Sum the elements and return the total."""
        result = _sqlite_sum(self._iterator)
        self._exhaust_iterator('sum')
        return result

    def avg(self):
        """Return the average of elements."""
        iterator = (x for x in self._iterator if x != None)
        self._exhaust_iterator('avg')
        total = 0.0
        count = 0
        for x in iterator:
            total = total + _sqlite_cast_as_real(x)
            count += 1
        return total / count if count else None

    def max(self):
        """Return the maximum value of all values. Returns None if
        all values are None.
        """
        result = max(self._iterator, default=None, key=_sqlite_sortkey)
        self._exhaust_iterator('max')
        return result

    def min(self):
        """Return the minimum non-None value of all values. Returns
        None only if all values are None.
        """
        iterator = (x for x in self._iterator if x != None)
        self._exhaust_iterator('min')
        return min(iterator, default=None, key=_sqlite_sortkey)


class DataResult(collections.Iterator):
    """A queryable iterator that can be evaluated to a given type."""
    def __init__(self, iterable, evaluates_to):
        self._iterator = iter(iterable)
        self._evaluates_to = evaluates_to
        self._exhausted_by = None

    def _exhaust_iterator(self, name, *args):
        args_repr = ', '.join(repr(x) for x in args)
        self._exhausted_by = '{0}({1})'.format(name, args_repr)
        self._iterator = iter([])  # Set empty iterator.

    def __iter__(self):
        """x.__iter__() <==> iter(x)"""
        return self

    def __next__(self):
        """x.__next__() <==> next(x)"""
        try:
            return next(self._iterator)
        except StopIteration:
            self._exhaust_iterator('__next__')
            raise

    def next(self):  # For Python 2.7 and earlier.
        return self.__next__()

    # Query methods.
    def map(self, function):
        if _expects_multiple_params(function):
            function_orig = function
            function = lambda x: function_orig(*x)

        def apply(value):
            try:
                result = value.map(function)
            except AttributeError:
                result = function(value)
            return result

        if issubclass(self._evaluates_to, dict):
            iterator = ((k, apply(v)) for k, v in self._iterator)
        else:
            iterator = (apply(x) for x in self._iterator)

        self._exhaust_iterator('map')
        return self.__class__(iterator, self._evaluates_to)

    def reduce(self, function):
        def apply(value):
            try:
                result = value.reduce(function)
            except AttributeError:
                result = functools.reduce(function, value)
            return result

        if issubclass(self._evaluates_to, dict):
            result = ((k, apply(v)) for k, v in self._iterator)
            result = self.__class__(result, self._evaluates_to)
        else:
            result = apply(self._iterator)

        self._exhaust_iterator('reduce')
        return result

    def sum(self):
        def apply(value):
            try:
                return value.sum()
            except AttributeError:
                return _sqlite_sum(value)

        if issubclass(self._evaluates_to, dict):
            result = ((k, apply(v)) for k, v in self._iterator)
            result = self.__class__(result, self._evaluates_to)
        else:
            result = apply(self._iterator)

        self._exhaust_iterator('sum')
        return result

    def eval(self):
        eval_type = self._evaluates_to
        if issubclass(eval_type, dict):
            def apply(value):
                try:
                    return value.eval()
                except AttributeError:
                    return value
            result = eval_type((k, apply(v)) for k, v in self._iterator)
        elif eval_type:
            result = eval_type(self._iterator)
        else:
            result = self._iterator

        self._exhaust_iterator('eval')
        return result


class ResultMapping(collections.Mapping):
    def __init__(self, iterable):
        self._iterable = iterable

    def __repr__(self):
        class_name = self.__class__.__name__
        iterable_repr = repr(self._iterable)
        return '{0}({1})'.format(class_name, iterable_repr)

    def __getitem__(self, key):
        return self._iterable.__getitem__(key)

    def __iter__(self):
        return iter(self._iterable)

    def __len__(self):
        return len(self._iterable)

    def map(self, function):
        if _expects_multiple_params(function):
            function_orig = function
            function = lambda x: function_orig(*x)

        result = {}
        for key, value in self._iterable.items():
            if isinstance(value, IterSequence):
                value = value.map(function)
            else:
                value = map(function, value)
            result[key] = value
        return ResultMapping(result)

    def reduce(self, function):
        result = {}
        for key, value in self._iterable.items():
            if isinstance(value, IterSequence):
                value = value.reduce(function)
            else:
                value = functools.reduce(function, value)
            result[key] = value
        return ResultMapping(result)

    def sum(self):
        result = {}
        for key, iterable in self._iterable.items():
            result[key] = _sqlite_sum(iterable)
        return ResultMapping(result)


def _validate_call_chain(call_chain):
    """Validate call chain--if invalid, raises TypeError else returns
    None. Call chain should be an iterable containing strings and
    2-tuples. In the case of 2-tuples, the first item must be an *args
    'tuple' and the second item must be a **kwds dict.
    """
    if isinstance(call_chain, str):
        raise TypeError("cannot be 'str'")

    try:
        iterable = iter(call_chain)
    except TypeError:
        raise TypeError('call_chain must be iterable')

    for item in iterable:
        if isinstance(item, str):
            continue  # Skip to next item.

        if not isinstance(item, tuple):
            err_msg = 'item must be string or 2-tuple, found {0}'
            err_obj = type(item).__name__
        elif len(item) != 2:
            err_msg = 'expected string or 2-tuple, found {0}-tuple'
            err_obj = len(item)
        elif not isinstance(item[0], tuple):
            err_msg = "first item must be *args 'tuple', found {0}"
            err_obj = type(item[0]).__name__
        elif not isinstance(item[1], dict):
            err_msg = "second item must be **kwds 'dict', found {0}"
            err_obj = type(item[1]).__name__
        else:
            err_msg = None
            err_obj = None

        if err_msg:
            raise TypeError(err_msg.format(repr(err_obj)))


def _get_call_repr(call):
    """Helper function returns repr for a single call chain item."""
    if isinstance(call, str):
        return repr(call)  # <- EXIT!

    args, kwds = call

    def _callable_name_or_repr(x):  # <- Helper function for
        if callable(x):             #    the helper function!
            try:
                return x.__name__
            except NameError:
                pass
        return repr(x)

    args_repr = [_callable_name_or_repr(x) + ',' for x in args]
    args_repr = ' '.join(args_repr)
    args_repr = '(' + args_repr + ')'

    kwds_repr = kwds.items()
    kwds_repr = [(repr(k), _callable_name_or_repr(v)) for k, v in kwds_repr]
    kwds_repr = ['{0}: {1}'.format(k, v) for k, v in kwds_repr]
    kwds_repr = ', '.join(kwds_repr)
    kwds_repr = '{' + kwds_repr + '}'

    return '({0}, {1})'.format(args_repr, kwds_repr)


class BaseQuery(object):
    def __init__(self, data_source, call_chain=None):
        if call_chain:
            _validate_call_chain(call_chain)
            call_chain = tuple(call_chain)
        else:
            call_chain = tuple()
        self._call_chain = call_chain
        self._data_source = data_source

    def __getattr__(self, name):
        call_chain = self._call_chain + (name,)
        return self.__class__(self._data_source, call_chain)

    def __call__(self, *args, **kwds):
        call_chain = self._call_chain + ((args, kwds),)
        return self.__class__(self._data_source, call_chain)

    def __repr__(self):
        class_name = self.__class__.__name__
        source_repr = repr(self._data_source)
        chain_repr = [_get_call_repr(call) for call in self._call_chain]
        chain_repr = ['        ' + x for x in chain_repr]  # Indent items.
        chain_repr = ',\n'.join(chain_repr)
        if chain_repr:
            chain_repr = '\n{0}\n    '.format(chain_repr)
        return ('{0}(\n'
                '    data_source={1},\n'
                '    call_chain=[{2}]\n'
                ')').format(class_name, source_repr, chain_repr)

    def _eval(self, call_chain=False):
        """Evaluate query and return its result."""
        if not call_chain:
            call_chain = self._call_chain

        def function(obj, val):
            if isinstance(val, str):
                return getattr(obj, val)
            args, kwds = val  # Unpack tuple.
            return obj(*args, **kwds)

        return functools.reduce(function, call_chain, self._data_source)


class DataQuery(BaseQuery):
    def __init__(self, data_source, call_chain=None):
        if not isinstance(data_source, DataSource):
            class_name = data_source.__class__.__name__
            msg = ("expected 'DataSource', got {1!r} (use BaseQuery "
                   "for other data_source types)")
            raise TypeError(msg.format(class_name))

        super(DataQuery, self).__init__(data_source, call_chain)

    def _optimize(self, call_chain):
        """Return optimized call_chain for faster performance with
        DataSource object.
        """
        return call_chain

    def eval(self, lazy=False, optimize=True):
        """Evaluate query and return its result.

        Use ``lazy=True`` to evaluate the query but leave the result
        in its raw, iterator form. By default, results are eagerly
        evaluated and loaded into memory.

        Use ``optimize=False`` to turn-off query optimization.
        """
        call_chain = self._call_chain
        if optimize:
            call_chain = self._optimize(call_chain)

        result = self._eval(call_chain)

        if lazy:
            return result  # <- EXIT!

        if isinstance(result, DataResult):
            result = result.eval()
        elif isinstance(result, IterSequence):
            result = list(result)
        return result


class DataSource(object):
    """
    .. warning:: This class is a work in progress.  Eventually this
                 class will replace the current CsvSource(),
                 ExcelSource(), etc. objects.
    """
    def __init__(self, data, columns=None):
        """Initialize self."""
        temptable = TemporarySqliteTable(data, columns)
        self._connection = temptable.connection
        self._table = temptable.name

    @classmethod
    def from_csv(cls, file, encoding=None, **fmtparams):
        with UnicodeCsvReader(file, encoding='utf-8', **fmtparams) as reader:
            columns = next(reader)  # Header row.
            return cls(reader, columns)

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
        return DataQuery(self, ['_select', (columns, kwds_filter)])

    def _select(self, *columns, **kwds_filter):
        if len(columns) == 1 and isinstance(columns[0], dict):
            key_columns, value_columns = tuple(columns[0].items())[0]
            if isinstance(key_columns, str):
                key_columns = tuple([key_columns])
            if isinstance(value_columns, (str, collections.Mapping)):
                value_columns = tuple([value_columns])
        else:
            key_columns = tuple()
            value_columns = columns

        self._assert_columns_exist(key_columns + value_columns)
        key_columns = tuple(self._normalize_column(x) for x in key_columns)
        value_columns = tuple(self._normalize_column(x) for x in value_columns)

        select_clause = ', '.join(key_columns + value_columns)

        if not key_columns:
            cursor = self._execute_query(
                self._table,
                select_clause,
                **kwds_filter
            )
            if len(value_columns) == 1:
                return IterSequence(row[0] for row in cursor)  # <- EXIT!
            return IterSequence(cursor)  # <- EXIT!

        trailing_clause = 'ORDER BY {0}'.format(', '.join(key_columns))
        cursor = self._execute_query(
            self._table,
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

    def __repr__(self):
        """Return a string representation of the data source."""
        cls_name = self.__class__.__name__
        conn_name = str(self._connection)
        tbl_name = self._table
        return '{0}({1}, table={2!r})'.format(cls_name, conn_name, tbl_name)

    def _execute_query(self, table, select_clause, trailing_clause=None, **kwds_filter):
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
