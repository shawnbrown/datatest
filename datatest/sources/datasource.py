# -*- coding: utf-8 -*-
from numbers import Number
from sqlite3 import Binary

from ..utils.builtins import *
from ..utils import collections
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


class ResultSequence(object):
    """."""
    def __init__(self, iterable):
        self._iterable = iterable

    def __repr__(self):
        class_name = self.__class__.__name__
        iterable_repr = repr(self._iterable)
        return '{0}({1})'.format(class_name, iterable_repr)

    def __iter__(self):
        return iter(self._iterable)

    def map(self, function):
        """Return a ResultSequence iterator that applies *function* to
        the elements, yielding the results.
        """
        if _expects_multiple_params(function):
            return ResultSequence(function(*x) for x in self)
        return ResultSequence(function(x) for x in self)

    def reduce(self, function):
        """Apply a *function* of two arguments cumulatively to the
        elements, from left to right, so as to reduce the values to a
        single result.
        """
        return functools.reduce(function, self)

    def sum(self):
        """Sum the elements and return the total."""
        return _sqlite_sum(self)

    def avg(self):
        """Return the average of elements."""
        iterable = (_sqlite_cast_as_real(x) for x in self if x != None)
        total = 0.0
        count = 0
        for x in iterable:
            total = total + x
            count += 1
        return total / count if count else None

    def max(self):
        """Return the maximum value of all values.  Returns None if
        all values are None.
        """
        return max(self, default=None, key=_sqlite_sortkey)

    def min(self):
        """Return the minimum non-None value of all values.
        Returns None only if all values are None.
        """
        iterable = (x for x in self if x != None)
        return min(iterable, default=None, key=_sqlite_sortkey)


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
            if isinstance(value, ResultSequence):
                value = value.map(function)
            else:
                value = map(function, value)
            result[key] = value
        return ResultMapping(result)

    def reduce(self, function):
        result = {}
        for key, value in self._iterable.items():
            if isinstance(value, ResultSequence):
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
    None. Call chain should be an iterable of 3-tuples where each item
    contains a name 'str', an *args 'tuple', and a **kwds 'dict'.
    """
    if isinstance(call_chain, str):
        raise TypeError("cannot be 'str'")

    for item in call_chain:
        if not isinstance(item, tuple):
            err_msg = 'item must be 3-tuple, found {0}'
            err_obj = type(item).__name__
        elif len(item) != 3:
            err_msg = 'expected 3-tuple, found {0}-tuple'
            err_obj = len(item)
        elif not isinstance(item[0], str):
            err_msg = "first item must be method name 'str', found {0}"
            err_obj = type(item[0]).__name__
        elif not isinstance(item[1], tuple):
            err_msg = "second item must be *args 'tuple', found {0}"
            err_obj = type(item[1]).__name__
        elif not isinstance(item[2], dict):
            err_msg = "third item must be **kwds 'dict', found {0}"
            err_obj = type(item[2]).__name__
        else:
            err_msg = None
            err_obj = None

        if err_msg:
            raise TypeError(err_msg.format(repr(err_obj)))


def _get_call_repr(call):
    """Helper function returns repr for a single call chain item."""
    name, args, kwds = call

    name_repr = repr(name)

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

    return '({0}, {1}, {2})'.format(name_repr, args_repr, kwds_repr)


def _rindex(sequence, x, default=None):
    """Helper function returns index of last item whose value is x."""
    length = len(sequence)
    for rindex, value in enumerate(reversed(sequence), start=1):
        if value == x:
            return length - rindex
    if default == None:
        raise ValueError(repr(x) + ' is not in sequence')
    return default


class DataQuery(object):
    def __init__(self, data_source, call_chain=None, optimizer=None):
        assert optimizer == None or callable(optimizer)
        self._optimizer = optimizer

        if call_chain:
            _validate_call_chain(call_chain)
            call_chain = tuple(call_chain)
        else:
            call_chain = tuple()

        self._call_chain = call_chain
        self._data_source = data_source

    def _new_call(self, method, *args, **kwds):
        call_chain = self._call_chain + ((method, args, kwds),)
        return self.__class__(self._data_source, call_chain)

    def map(self, function):
        return self._new_call('map', function)

    def reduce(self, function):
        return self._new_call('reduce', function)

    def sum(self):
        return self._new_call('sum')

    def avg(self):
        return self._new_call('avg')

    def count(self):
        return self._new_call('count')

    def min(self):
        return self._new_call('min')

    def max(self):
        return self._new_call('max')

    def __repr__(self):
        class_name = self.__class__.__name__
        source_repr = repr(self._data_source)
        chain_repr = [_get_call_repr(call) for call in self._call_chain]
        chain_repr = ',\n        '.join(chain_repr)
        if chain_repr:
            chain_repr = '\n        ' + chain_repr + '\n    '
        optimizer_repr = repr(self._optimizer)
        return ('{0}(\n'
                '    data_source={1},\n'
                '    call_chain=[{2}],\n'
                '    optimizer={3}\n'
                ')').format(class_name, source_repr, chain_repr, optimizer_repr)


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
        if len(columns) == 1 and isinstance(columns[0], collections.Mapping):
            return self.select(*columns, **kwds_filter)
        return DataQuery(self, [('select', columns, kwds_filter)])

    def select(self, *columns, **kwds_filter):
        if len(columns) == 1 and isinstance(columns[0], collections.Mapping):
            columns_dict = columns[0]
            groupby, columns = tuple(columns_dict.items())[0]
            if isinstance(groupby, str):
                groupby = tuple([groupby])
            if isinstance(columns, (str, collections.Mapping)):
                columns = tuple([columns])
        else:
            groupby = tuple()

        all_columns = groupby + columns
        self._assert_columns_exist(all_columns)
        all_columns = [self._normalize_column(x) for x in all_columns]

        select_clause = ', '.join(all_columns)
        cursor = self._execute_query(self._table, select_clause, **kwds_filter)

        if not groupby:
            if len(columns) == 1:
                result = (row[0] for row in cursor)
            else:
                result = cursor
            return ResultSequence(result)  # <- EXIT!

        # Prepare key and value functions.
        slice_index = len(groupby)
        if slice_index == 1:
            get_key = lambda row: row[0]
        else:
            get_key = lambda row: row[:slice_index]

        if len(all_columns) - slice_index == 1:
            get_value = lambda row: row[-1]
        else:
            get_value = lambda row: row[slice_index:]

        # Parse rows.
        result = {}
        for row in cursor:
            key = get_key(row)
            value = get_value(row)
            try:
                result[key].append(value)
            except KeyError:
                result[key] = [value]

        return result
        #return ResultMapping(result)

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
