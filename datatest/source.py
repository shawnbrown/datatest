# -*- coding: utf-8 -*-
import inspect
import os
import sqlite3
import sys
import warnings

from .utils.builtins import *
from .utils import collections
from .utils import decimal
from .utils import functools
from .utils import itertools
from .utils import TemporarySqliteTable
from .utils import UnicodeCsvReader

from .compare import CompareDict
from .compare import CompareSet
from .compare import _is_nscontainer

#pattern = 'test*.py'
prefix = 'test_'

sqlite3.register_adapter(decimal.Decimal, str)


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
        """Return a string representation of the data source."""
        return NotImplemented

    def columns(self):
        """Return list of column names."""
        return NotImplemented

    def __iter__(self):
        """Return an iterable of dictionary rows (like
        ``csv.DictReader``).
        """
        return NotImplemented

    def filter_rows(self, **kwds):
        """Filter data by keywords, returns iterable of dict-rows (much
        like csv.DictReader() object).  E.g., where column1=value1,
        column2=value2, etc. (uses slow ``__iter__``).
        """
        if kwds:
            normalize = lambda v: (v,) if isinstance(v, str) else v
            kwds = dict((k, normalize(v)) for k, v in kwds.items())
            matches_kwds = lambda row: all(row[k] in v for k, v in kwds.items())
            return filter(matches_kwds, self.__iter__())
        return self.__iter__()

    def distinct(self, column, **kwds_filter):
        """Return iterable of tuples containing distinct *column*
        values (uses slow ``__iter__``).
        """
        if not _is_nscontainer(column):
            column = (column,)
        self._assert_columns_exist(column)
        iterable = self.filter_rows(**kwds_filter)  # Filtered rows only.
        iterable = (tuple(row[c] for c in column) for row in iterable)
        return CompareSet(iterable)

    def sum(self, columns, keys=None, **kwds_filter):
        """Returns sum of one or more *columns* grouped by *keys* as a
        CompareDict.
        """
        mapper = lambda x: decimal.Decimal(x) if x else decimal.Decimal(0)
        if not _is_nscontainer(columns):
            reducer = lambda x, y: x + y
        else:
            map_one = mapper
            mapper = lambda x: tuple(map_one(n) for n in x)
            reducer = lambda x, y: tuple(xi + yi for xi, yi in zip(x, y))
        return self.mapreduce(mapper, reducer, columns, keys, **kwds_filter)

    def count(self, column, keys=None, **kwds_filter):
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
            cursor = self._execute_query(self._table, '*', **kwds)  # <- applies filter
            column_names = self.columns()
            dict_row = lambda row: dict(zip(column_names, row))
            return (dict_row(row) for row in cursor)
        return self.__iter__()

    def distinct(self, column, **kwds_filter):
        """Return iterable of tuples containing distinct *column*
        values.
        """
        if not _is_nscontainer(column):
            column = (column,)
        self._assert_columns_exist(column)
        select_clause = [self._normalize_column(x) for x in column]
        select_clause = ', '.join(select_clause)
        select_clause = 'DISTINCT ' + select_clause

        cursor = self._execute_query(self._table, select_clause, **kwds_filter)
        return CompareSet(cursor)

    def sum(self, columns, keys=None, **kwds_filter):
        """Returns sum of *columns* grouped by *keys* as CompareDict."""
        if not _is_nscontainer(columns):
            columns = (columns,)
        self._assert_columns_exist(columns)
        columns = (self._normalize_column(x) for x in columns)
        sql_functions = tuple('SUM({0})'.format(x) for x in columns)
        return self._sql_aggregate(sql_functions, keys, **kwds_filter)

    def count(self, column, keys=None, **kwds_filter):
        """."""
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
        if not _is_nscontainer(sql_function):
            sql_function = (sql_function,)

        if keys == None:
            sql_function = ', '.join(sql_function)
            cursor = self._execute_query(self._table, sql_function, **kwds_filter)
            result = cursor.fetchone()
            if len(result) == 1:
                return result[0]
            return result  # <- EXIT!

        if not _is_nscontainer(keys):
            keys = (keys,)
        group_clause = [self._normalize_column(x) for x in keys]
        group_clause = ', '.join(group_clause)

        select_clause = '{0}, {1}'.format(group_clause, ', '.join(sql_function))
        trailing_clause = 'GROUP BY ' + group_clause

        cursor = self._execute_query(self._table, select_clause, trailing_clause, **kwds_filter)
        pos = len(sql_function)
        iterable = ((row[:-pos], getvals(row)) for row in cursor)
        if pos > 1:
            # Gets values by slicing (i.e., row[-pos:]).
            iterable = ((row[:-pos], row[-pos:]) for row in cursor)
        else:
            # Gets value by index (i.e., row[-pos]).
            iterable = ((row[:-pos], row[-pos]) for row in cursor)
        return CompareDict(iterable, keys)

    # Regarding SqliteBase.mapreduce():
    #
    # This subclass does not implement its own mapreduce() optimization
    # and it probably should not in the future.  However, this class
    # *does* implement a SQL-optimized filter_rows() method--which
    # mapreduce() uses internally.
    #
    # A generalized optimization of mapreduce() cannot be implemented
    # in basic SQL.  Although, it is technically possible to implement
    # several special cases and then fallback to the parent
    # implementation when a novel case is encountered.  The sum() and
    # count() methods are, themselves, special cases of mapreduce() and
    # this class does provide optimized versions of them.  But
    # attempting to optimize an open-ended number of special cases
    # would require a lot of speculation and hardly seems advisable at
    # this time.

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
        """Creating an index for certain columns can speed up data
        testing in some cases.

        See :meth:`SqliteSource.create_index
        <datatest.SqliteSource.create_index>` for more details.
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
    def _normalize_column(name):
        """Normalize value for use as SQLite column name."""
        name = name.strip()
        name = name.replace('"', '""')  # Escape quotes.
        if name == '':
            name = '_empty_'
        return '"' + name + '"'


class SqliteSource(SqliteBase):
    """Loads *table* data from given SQLite *connection*:
    ::

        conn = sqlite3.connect('mydatabase.sqlite3')
        subjectData = datatest.SqliteSource(conn, 'mytable')
    """
    @classmethod
    def from_records(cls, data, columns=None):
        """Alternate constructor to load an existing collection of
        records.  Loads *data* (an iterable of lists, tuples, or dicts)
        into a new SQLite database with the given *columns*::

            subjectData = datatest.SqliteSource.from_records(records, columns)

        The *columns* argument can be omitted if *data* contains
        ``dict`` or ``namedtuple`` records::

            dict_rows = [
                { ... },
                { ... },
            ]
            subjectData = datatest.SqliteSource.from_records(dict_rows)
        """
        temptable = TemporarySqliteTable(data, columns)
        return cls(temptable.connection, temptable.name)

    def create_index(self, *columns):
        """Creating an index for certain columns can speed up data
        testing in some cases.

        Indexes should be added one-by-one to tune a test suite's
        over-all performance.  Creating several indexes before testing
        even begins could lead to worse performance so use them with
        discretion.

        For example:  If you're using "town" to group aggregation
        tests (like ``self.assertDataSum('population', ['town'])``),
        then you might be able to improve performance by adding an
        index for the "town" column::

            subjectData.create_index('town')

        Using two or more columns creates a multi-column index::

            subjectData.create_index('town', 'zipcode')

        Calling the function multiple times will create multiple
        indexes::

            subjectData.create_index('town')
            subjectData.create_index('zipcode')
        """
        # Calling super() with older convention to support Python 2.7 & 2.6.
        super(SqliteSource, self).create_index(*columns)


class CsvSource(SqliteBase):
    """Loads CSV data from *file* (path or file-like object):
    ::

        subjectData = datatest.CsvSource('mydata.csv')
    """
    def __init__(self, file, encoding=None, in_memory=False):
        """Initialize self."""
        self._file_repr = repr(file)

        # If *file* is relative path, uses directory of calling file as base.
        if isinstance(file, str) and not os.path.isabs(file):
            calling_frame = sys._getframe(1)
            calling_file = inspect.getfile(calling_frame)
            base_path = os.path.dirname(calling_file)
            file = os.path.join(base_path, file)
            file = os.path.normpath(file)

        # Create temporary SQLite table object.
        if encoding:
            with UnicodeCsvReader(file, encoding=encoding) as reader:
                columns = next(reader)  # Header row.
                temptable = TemporarySqliteTable(reader, columns)
        else:
            try:
                with UnicodeCsvReader(file, encoding='utf-8') as reader:
                    columns = next(reader)  # Header row.
                    temptable = TemporarySqliteTable(reader, columns)

            except UnicodeDecodeError:
                with UnicodeCsvReader(file, encoding='iso8859-1') as reader:
                    columns = next(reader)  # Header row.
                    temptable = TemporarySqliteTable(reader, columns)

                # Prepare message and raise as warning.
                try:
                    filename = os.path.basename(file)
                except AttributeError:
                    filename = repr(file)
                msg = ('\nData in file {0!r} does not appear to be encoded '
                       'as UTF-8 (used ISO-8859-1 as fallback). To assure '
                       'correct operation, please specify a text encoding.')
                warnings.warn(msg.format(filename))

        # Calling super() with older convention to support Python 2.7 & 2.6.
        super(CsvSource, self).__init__(temptable.connection, temptable.name)

    def __repr__(self):
        """Return a string representation of the data source."""
        cls_name = self.__class__.__name__
        src_file = self._file_repr
        return '{0}({1})'.format(cls_name, src_file)


class _FilterValueError(ValueError):
    """Used by AdapterSource.  This error is raised when attempting to
    unwrap a filter that specifies an inappropriate (non-missing) value
    for a missing column."""
    pass


class AdapterSource(BaseSource):
    """A wrapper class that adapts a data *source* to an *interface* of
    column names. The *interface* should be a sequence of 2-tuples where
    the first item is the desired column name and the second item is
    the existing column name. If column order is not important, the
    *interface* can, alternatively, be a dict.

    For example, a CSV file that contains the columns 'old_1', 'old_2',
    and 'old_4' can be adapted to behave as if it has the columns
    'new_1', 'new_2', 'new_3' and 'new_4' with the following::

        source = CsvSource('mydata.csv')
        interface = [
            ('new_1', 'old_1'),
            ('new_2', 'old_2'),
            ('new_3', None),
            ('new_4', 'old_4'),
        ]
        subjectData = AdapterSource(source, interface)

    An AdapterSource can be thought of as a virtual source that renames,
    reorders, adds, or removes columns of the original *source*. To add
    a column that does not exist in original, use None in place of a
    column name (see 'new_3', above). Columns mapped to None will
    contain *missing* values (defaults to empty string).

    The original source can be accessed via the __wrapped__ property.
    """
    def __init__(self, source, interface, missing=''):
        if not isinstance(interface, collections.Sequence):
            if isinstance(interface, dict):
                interface = interface.items()
            interface = sorted(interface)

        source_columns = source.columns()
        interface_cols = [x[1] for x in interface]
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
        return [x[0] for x in self._interface]

    def __iter__(self):
        interface = self._interface
        missing = self._missing
        for row in self.__wrapped__.__iter__():
            yield dict((new, row.get(old, missing)) for new, old in interface)

    def filter_rows(self, **kwds):
        try:
            unwrap_kwds = self._unwrap_filter(kwds)
        except _FilterValueError:
            return  # <- EXIT! Raises StopIteration to signify empty generator.

        interface = self._interface
        missing = self._missing
        for row in self.__wrapped__.filter_rows(**unwrap_kwds):
            yield dict((new, row.get(old, missing)) for new, old in interface)

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

    def sum(self, columns, keys=None, **kwds_filter):
        """Returns sum of *columns* grouped by *keys* as CompareDict."""
        unwrap_src = self.__wrapped__
        unwrap_cols = self._unwrap_columns(columns)
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
        if not unwrap_cols:
            distinct = self.distinct(keys, **kwds_filter)
            if isinstance(columns, str):
                val = 0
            else:
                val = (0,) * len(columns)
            result = ((key, val) for key in distinct)
            return CompareDict(result, keys)  # <- EXIT!

        result = unwrap_src.sum(unwrap_cols, unwrap_keys, **unwrap_flt)

        rewrap_cols = self._rewrap_columns(unwrap_cols)
        rewrap_keys = self._rewrap_columns(unwrap_keys)
        return self._rebuild_comparedict(result, rewrap_cols, columns,
                                         rewrap_keys, keys, missing_col=0)

    #def count(self, column, keys=None, **kwds_filter):
    #    pass

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
            interface_dict = dict(self._interface)

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
            interface_dict = dict(self._interface)

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

    def _rewrap_columns(self, unwrapped_columns, interface_dict=None):
        """Take unwrapped adaptee column names and wrap them in adapter
        column names (specified by _interface).
        """
        if not unwrapped_columns:
            return None  # <- EXIT!

        if interface_dict:
            interface = interface_dict.items()
        else:
            interface = self._interface
        rev_interface = dict((v, k) for k, v in interface)

        if isinstance(unwrapped_columns, str):
            return rev_interface[unwrapped_columns]
        return tuple(rev_interface[k] for k in unwrapped_columns)

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
                if not _is_nscontainer(v):
                    v = (v,)
                value_dict = dict(zip(rewrapped_columns, v))
                return tuple(value_dict.get(v, missing) for v in columns)
            item_gen = ((k, rebuild_values(v, missing_col)) for k, v in item_gen)

        return CompareDict(item_gen, key_names=keys)


class MultiSource(BaseSource):
    """
    MultiSource(*sources, missing='')

    A wrapper class that allows multiple data sources to be treated
    as a single, composite data source::

        subjectData = datatest.MultiSource(
            datatest.CsvSource('file1.csv'),
            datatest.CsvSource('file2.csv'),
            datatest.CsvSource('file3.csv')
        )

    The original sources are stored in the ``__wrapped__`` attribute.
    """
    def __init__(self, *sources, **kwd):
        """
        __init__(self, *sources, missing='')

        Initialize self.
        """
        # Accept `missing` as a keyword-only argument.
        try:
            missing = kwd.pop('missing')
        except KeyError:
            missing = ''

        if kwd:                     # Enforce keyword-only argument
            key, _ = kwd.popitem()  # behavior that works in Python 2.x.
            msg = "__init__() got an unexpected keyword argument " + repr(key)
            raise TypeError(msg)

        msg = 'Sources must be derived from BaseSource'
        assert all(isinstance(s, BaseSource) for s in sources), msg

        all_columns = []
        for s in sources:
            for c in s.columns():
                if c not in all_columns:
                    all_columns.append(c)

        normalized_sources = []
        for s in sources:
            if set(s.columns()) < set(all_columns):
                columns = s.columns()
                fn = lambda x: x if x in columns else None
                old = [fn(x) for x in all_columns]
                interface = list(zip(all_columns, old))
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
        #columns = self.columns()
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

    def sum(self, columns, keys=None, **kwds_filter):
        """Return sum of values in *columns* grouped by *keys*."""
        fn = lambda source: source.sum(columns, keys, **kwds_filter)
        results = (fn(source) for source in self._sources)

        if not keys:
            if isinstance(columns, str):
                sum_total = sum(results)
            else:
                sum_total = (0,) * len(columns)
                for val in results:
                    sum_total = tuple(xi + yi for xi, yi in zip(sum_total, val))
            return sum_total  # <- EXIT!

        if isinstance(columns, str):
            sum_total = collections.defaultdict(lambda: 0)
            for result in results:
                for key, val in result.items():
                    sum_total[key] += val
        else:
            all_zeros = (0,) * len(columns)
            sum_total = collections.defaultdict(lambda: all_zeros)
            for result in results:
                for key, val in result.items():
                    existing = sum_total[key]
                    sum_total[key] = tuple(xi + yi for xi, yi in zip(existing, val))
        return CompareDict(sum_total, keys)

    #def count(self, column, keys=None, **kwds_filter):
    #    pass

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


#DefaultDataSource = CsvSource
