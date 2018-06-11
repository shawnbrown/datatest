# -*- coding: utf-8 -*-
from __future__ import absolute_import
import inspect
try:
    import sqlite3
except ImportError:
    sqlite3 = None  # Missing from Jython and Micropython.
import sys
from io import IOBase
from glob import glob
from numbers import Number

from .._compatibility.builtins import *
from .._compatibility import abc
from .._compatibility import collections
from .._compatibility import contextlib
from .._compatibility import functools
from .._compatibility import itertools
from .._utils import _expects_multiple_params
from .._utils import _flatten
from .._utils import iterpeek
from .._utils import nonstringiter
from .._utils import sortable
from .._utils import exhaustible
from .._utils import _make_token
from .._utils import _unique_everseen
from .._utils import file_types
from .._utils import string_types
from .._load.get_reader import get_reader
from .._load.load_csv import load_csv
from .._load.temptable import drop_table
from .._load.temptable import load_data
from .._load.temptable import new_table_name
from .._load.temptable import savepoint
from .._load.temptable import table_exists

try:
    FileNotFoundError  # New in Python 3.3.
except NameError:
    # If not available, use as an alias for OSError.
    FileNotFoundError = OSError

# For the following database connection, the synchronous flag is
# set to "OFF" for faster insertions and commits. Since the database
# is temporary, long-term integrity should not be a concern--in the
# unlikely event of data corruption, it should be entirely acceptable
# to simply rebuild the temporary tables.
DEFAULT_CONNECTION = sqlite3.connect('')  # <- Using '' makes a temp file.
DEFAULT_CONNECTION.execute('PRAGMA synchronous=OFF')
DEFAULT_CONNECTION.isolation_level = None  # <- Run in 'autocommit' mode.


_Mapping = collections.Mapping    # Get direct reference to eliminate
_Iterable = collections.Iterable  # dot-lookups (these are used a lot).

class BaseElement(abc.ABC):
    """An abstract base class used to determine if an object should
    be treated as a single data element or as a collection of multiple
    data elements.

    Objects that are considered individual data elements include:

    * non-iterable objects
    * strings
    * mappings
    """
    @abc.abstractmethod
    def __init__(self, *args, **kwds):
        pass

    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is BaseElement:
            if (issubclass(subclass, (string_types, _Mapping))
                    or not issubclass(subclass, _Iterable)):
                return True
        return NotImplemented


class DictItems(collections.Iterator):
    """A wrapper used to normalize and identify iterators that
    should return a 2-tuple of key-value pairs. The underlying
    iterable should not contain duplicate keys and they should be
    appropriate for constructing a dictionary or other mapping.
    """
    def __init__(self, iterable):
        if isinstance(iterable, collections.Mapping):
            iterable = getattr(iterable, 'iteritems', iterable.items)()
            iterable = iter(iterable)
        else:
            if isinstance(iterable, Query):
                iterable = iterable.execute()

            while hasattr(iterable, '__wrapped__'):
                iterable = iterable.__wrapped__

            first_item, iterable = iterpeek(iterable)

            # Assert that first item contains a suitable key-value pair.
            if first_item:
                if isinstance(first_item, BaseElement):
                    raise TypeError((
                        'dictionary update sequence items can not be '
                        'registered BaseElement types, got {0}: {1!r}'
                    ).format(first_item.__class__.__name__, first_item))
                try:
                    first_item = tuple(first_item)
                except TypeError:
                    raise TypeError('cannot convert dictionary update '
                                    'sequence element #0 to a sequence')
                if len(first_item) != 2:
                    ValueError(('dictionary update sequence element #0 has length '
                                '{0}; 2 is required').format(len(first_item)))
                first_key = first_item[0]
                if not isinstance(first_key, collections.Hashable):
                    raise ValueError((
                        'unhashable type {0}: {1!r}'
                    ).format(first_key.__class__.__name__, first_key))

        self.__wrapped__ = iter(iterable)

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.__wrapped__)

    def next(self):
        return next(self.__wrapped__)  # For Python 2 compatibility.


_iteritem_types = (
    collections.ItemsView,
    DictItems,
    type(getattr(dict(), 'iteritems', dict().items)()),  # For Python 2 compatibility.
)

def _is_collection_of_items(obj):
    while hasattr(obj, '__wrapped__'):
        if isinstance(obj, DictItems):
            return True
        obj = obj.__wrapped__
    return isinstance(obj, _iteritem_types)


class Result(collections.Iterator):
    """A simple iterator that wraps the results of :class:`Query`
    execution. This iterator is used to facilitate the lazy evaluation
    of data objects (where possible) when asserting data validity.

    Although Result objects are usually constructed automatically,
    it's possible to create them directly::

        iterable = iter([...])
        result = Result(iterable, evaluation_type=list)

    .. warning::

        When iterated over, the *iterable* **must** yield only those
        values necessary for constructing an object of the given
        *evaluation_type* and no more. For example, when the
        *evaluation_type* is a set, the *iterable* must not contain
        duplicate or unhashable values. When the *evaluation_type*
        is a :py:class:`dict` or other mapping, the *iterable* must
        contain unique key-value pairs or a mapping.
    """
    def __init__(self, iterable, evaluation_type):
        if not isinstance(evaluation_type, type):
            msg = 'evaluation_type must be a type, found instance of {0}'
            raise TypeError(msg.format(evaluation_type.__class__.__name__))

        while (hasattr(iterable, '__wrapped__')
                   and not isinstance(iterable, DictItems)):
            iterable = iterable.__wrapped__

        if isinstance(iterable, collections.Mapping):
            iterable = DictItems(iterable.items())

        if (issubclass(evaluation_type, collections.Mapping)
                and not _is_collection_of_items(iterable)):
            cls_name = iterable.__class__.__name__
            raise TypeError('when evaluation_type is a mapping, '
                            'iterator must be DictItems or ItemsView, '
                            'found {0} instead'.format(cls_name))

        #: The underlying iterator---useful when introspecting
        #: or rewrapping.
        self.__wrapped__ = iter(iterable)

        #: The type of instance returned when data is evaluated
        #: with the :meth:`fetch <Result.fetch>` method.
        self.evaluation_type = evaluation_type

    def __iter__(self):
        return self

    def __repr__(self):
        cls_name = self.__class__.__name__
        eval_name = self.evaluation_type.__name__
        hex_id = hex(id(self))
        template = '<{0} object (evaluation_type={1}) at {2}>'
        return template.format(cls_name, eval_name, hex_id)

    def __next__(self):
        return next(self.__wrapped__)

    def next(self):
        return next(self.__wrapped__)  # For Python 2 compatibility.

    def fetch(self):
        """Evaluate the entire iterator and return its result::

            result = Result(iter([...]), evaluation_type=set)
            result_set = result.fetch()  # <- Returns a set of values.

        When evaluating a :py:class:`dict` or other mapping type, any
        values that are, themselves, :class:`Result` objects will
        also be evaluated.
        """
        evaluation_type = self.evaluation_type
        if issubclass(evaluation_type, collections.Mapping):
            def func(obj):
                if hasattr(obj, 'evaluation_type'):
                    return obj.evaluation_type(obj)
                return obj

            return evaluation_type((k, func(v)) for k, v in self)

        return evaluation_type(self)


def _get_evaluation_type(obj, default=None):
    """Return object's evaluation_type property. If the object does
    not have an evaluation_type property and is a mapping, sequence,
    or set, then return the type of the object itself. If the object
    is an iterable, return None. Raises a Type error for any other
    object.
    """
    if hasattr(obj, 'evaluation_type'):
        return obj.evaluation_type  # <- EXIT!

    obj_cls = obj.__class__  # Avoiding type() to support old-style
                             # classes in Python 2.7 and 2.6.

    #if isinstance(obj, DictItems):
    #    return dict  # <- EXIT!

    if issubclass(obj_cls, (collections.Mapping,
                            collections.Sequence,
                            collections.Set)):
        return obj_cls  # <- EXIT!

    if default and issubclass(obj_cls, collections.Iterable):
        return default  # <- EXIT!

    err_msg = 'unable to determine target type for {0!r} instance'
    raise TypeError(err_msg.format(obj_cls.__name__))


def _make_dataresult(iterable):
    eval_type = _get_evaluation_type(iterable)
    if issubclass(eval_type, collections.Mapping):
        iterable = getattr(iterable, 'iteritems', iterable.items)()
        iterable = DictItems(iterable)
    else:
        iterable = iter(iterable)
    return Result(iterable, eval_type)


def _apply_to_data(function, data_iterator):
    """Apply a *function* of one argument to the to the given
    iterator *data_iterator*.
    """
    if _is_collection_of_items(data_iterator):
        result = DictItems((k, function(v)) for k, v in data_iterator)
        return Result(result, _get_evaluation_type(data_iterator))
    return function(data_iterator)


def _map_data(function, iterable):
    def wrapper(iterable):
        if isinstance(iterable, BaseElement):
            return function(iterable)  # <- EXIT!

        evaluation_type = _get_evaluation_type(iterable)
        if issubclass(evaluation_type, collections.Set):
            evaluation_type = list

        def domap(func, itrbl):
            if _expects_multiple_params(func):
                for x in itrbl:
                    if isinstance(x, BaseElement):
                        yield func(x)
                    else:
                        yield func(*x)
            else:
                for x in itrbl:
                    yield func(x)
        return Result(domap(function, iterable), evaluation_type)

    return _apply_to_data(wrapper, iterable)


def _reduce_data(function, iterable):
    def wrapper(iterable):
        if isinstance(iterable, BaseElement):
            return iterable
        return functools.reduce(function, iterable)

    return _apply_to_data(wrapper, iterable)


def _filter_data(function, iterable):
    def wrapper(iterable):
        if isinstance(iterable, BaseElement):
            raise TypeError(('filter expects a collection of data elements, '
                             'got 1 data element: {0}').format(iterable))
        filtered_data = filter(function, iterable)
        return Result(filtered_data, _get_evaluation_type(iterable))

    return _apply_to_data(wrapper, iterable)


def _apply_data(function, data):
    """Group-wise function application."""
    return _apply_to_data(function, data)


def _sqlite_cast_as_real(value):
    """Convert value to REAL (float) or default to 0.0 to match SQLite
    behavior. See the "Conversion Processing" table in the "CAST
    expressions" section for details:

        https://www.sqlite.org/lang_expr.html#castexpr
    """
    # TODO: Implement behavioral parity with SQLite and add tests.
    try:
        return float(value)
    except ValueError:
        return 0.0


def _sqlite_sum(iterable):
    """Sum the elements and return the total (should match SQLite
    behavior).
    """
    if isinstance(iterable, BaseElement):
        iterable = [iterable]
    iterable = (_sqlite_cast_as_real(x) for x in iterable if x != None)
    try:
        start_value = next(iterable)
    except StopIteration:  # From SQLite docs: "If there are no non-NULL
        return None        # input rows then sum() returns NULL..."
    return sum(iterable, start_value)


def _sqlite_count(iterable):
    """Return the number non-NULL (!= None) elements in iterable."""
    if isinstance(iterable, BaseElement):
        iterable = [iterable]
    return sum(1 for x in iterable if x != None)


# The SQLite BLOB/Binary type in sortable Python 2 but unsortable in Python 3.
Binary = sqlite3.Binary  # Pull into local namespace to eliminate dot-lookup.
_unsortable_blob_type = not sortable(Binary(b'0'))


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
    if value is None:                    # NULL (sort group 0)
        return (0, 0)
    if isinstance(value, Number):        # INTEGER and REAL (sort group 1)
        return (1, value)
    if isinstance(value, string_types):  # TEXT (sort group 2)
        return (2, value)
    if isinstance(value, Binary):        # BLOB (sort group 3)
        if _unsortable_blob_type:
            value = bytes(value)
        return (3, value)
    return (4, value)  # unsupported type (sort group 4)


def _sqlite_avg(iterable):
    """Return the average of elements in iterable. Returns None if all
    elements are None.
    """
    if isinstance(iterable, BaseElement):
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
    if isinstance(iterable, BaseElement):
        return iterable  # <- EXIT!
    iterable = (x for x in iterable if x != None)
    return min(iterable, default=None, key=_sqlite_sortkey)


def _sqlite_max(iterable):
    """Return the maximum value of all values. Returns None if all
    values are None.
    """
    if isinstance(iterable, BaseElement):
        return iterable  # <- EXIT!
    return max(iterable, default=None, key=_sqlite_sortkey)


def _sqlite_distinct(iterable):
    """Filter iterable to unique values, while maintaining
    evaluation_type.
    """
    def dodistinct(itr):
        if isinstance(itr, BaseElement):
            return itr
        return Result(_unique_everseen(itr), _get_evaluation_type(itr))

    if _is_collection_of_items(iterable):
        result = DictItems((k, dodistinct(v)) for k, v in iterable)
        return Result(result, _get_evaluation_type(iterable))
    return dodistinct(iterable)


########################################################
# Functions to validate and parse query 'select' syntax.
########################################################

def _validate_fields(fields):
    if isinstance(fields, string_types):
        return  # <- EXIT!

    for field in fields:
        if not isinstance(field, string_types):
            message = "expected 'str' elements, got {0!r}"
            raise ValueError(message.format(field))


def _normalize_columns(columns):
    """Returns normalized *columns* selection or raise error if
    unsupported.
    """
    if not isinstance(columns, collections.Sized):
        raise ValueError(('unsupported columns '
                          'format, got {0!r}').format(columns))

    if isinstance(columns, collections.Mapping):
        if len(columns) != 1:
            raise ValueError(('expected container of 1 item, got {0} '
                              'items: {1!r}').format(len(columns), columns))

        key, value = tuple(columns.items())[0]
        if isinstance(value, collections.Mapping):
            message = 'mappings can not be nested, got {0!r}'
            raise ValueError(message.format(columns))

        if isinstance(value, str) or len(value) > 1:
            columns = {key: [value]}  # Rebuild with default list container.

        _validate_fields(key)
        _validate_fields(tuple(value)[0])
        return columns  # <- EXIT!

    if isinstance(columns, str) or len(columns) > 1:
        columns = [columns]  # Wrap with default list container.

    _validate_fields(tuple(columns)[0])
    return columns


def _parse_columns(columns):
    """Expects a normalized *columns* selection and returns its
    *key* and *value* components as a tuple.
    """
    if isinstance(columns, collections.Mapping):
        key, value = tuple(columns.items())[0]
    else:
        key, value = tuple(), columns
    return key, value


##################
# Helper Functions
##################
def _make_args_repr(args):
    func = lambda x: getattr(x, '__name__', repr(x))
    return ', '.join(func(x) for x in args)

def _make_kwds_repr(kwds):
    func = lambda x: getattr(x, '__name__', repr(x))
    kwds_repr = [(k, func(v)) for k, v in kwds.items()]
    kwds_repr = ['{0}={1}'.format(k, v) for k, v in kwds_repr]
    return ', '.join(kwds_repr)


##########################################
# Functions for query and execution steps.
##########################################

def _get_step_repr(step):
    """Helper function to return repr for a single query step."""
    func, args, kwds = step
    func_repr = getattr(func, '__name__', repr(func))
    args_repr = _make_args_repr(args)
    kwds_repr = _make_kwds_repr(kwds)
    return '{0}, ({1}), {{{2}}}'.format(func_repr, args_repr, kwds_repr)


_query_step = collections.namedtuple(
    typename='query_step',
    field_names=('name', 'args', 'kwds')
)

_execution_step = collections.namedtuple(
    typename='execution_step',
    field_names=('function', 'args', 'kwds')
)

RESULT_TOKEN = _make_token(
    'RESULT',
    'Token for representing a data result when optimizing execution plan.',
)


########################################################
# Main data handling classes (Query and Selector).
########################################################

class Query(object):
    """Query(columns, **where)
    Query(selector, columns, **where)

    A class to query data from a source object.

    See documentation for full details.
    """
    def __init__(self, *args, **where):
        """Initialize self.

        Query(columns, **where)
        Query(selector, columns, **where)
        """
        argcount = len(args)
        if argcount == 2:
            selector, columns = args
            if not isinstance(selector, Selector):
                msg = 'selector must be datatest.Selector object, got {0}'
                raise TypeError(msg.format(selector.__class__.__name__))
            flattened = _flatten([_parse_columns(columns), where.keys()])
            try:
                selector._assert_fields_exist(flattened)
            except LookupError:
                __tracebackhide__ = True
                raise
        elif argcount == 1:
            selector, columns = None, args[0]
        else:
            msg = 'expects 1 or 2 positional arguments but {0} were given'
            raise TypeError(msg.format(argcount))

        self.source = selector
        self.args = (_normalize_columns(columns),)
        self.kwds = where
        self._query_steps = []

    @classmethod
    def from_object(cls, obj):
        """Creates a query and associates it with the given object.

        .. code-block:: python

            mylist = [1, 2, 3, 4]
            query = Query.from_object(mylist)

        If *obj* is a Query itself, a copy of the original query
        is created.
        """
        if isinstance(obj, Query):
            return obj.__copy__()

        if not nonstringiter(obj):
            obj = [obj]

        new_query = cls.__new__(cls)
        new_query.source = obj
        new_query.args = ()
        new_query.kwds = {}
        new_query._query_steps = []
        return new_query

    @staticmethod
    def _validate_source(source):
        if not isinstance(source, Selector):
            raise TypeError('expected {0!r}, got {1!r}'.format(
                Selector.__name__,
                source.__class__.__name__,
            ))

    def __copy__(self):
        new_query = self.__class__.__new__(self.__class__)
        new_query.source = self.source
        new_query.args = self.args
        new_query.kwds = dict(self.kwds)                  # Makes copies of
        new_query._query_steps = list(self._query_steps)  # mutable types.
        return new_query

    def _add_step(self, name, *args, **kwds):
        step = _query_step(name, args, kwds)
        new_query = self.__copy__()
        new_query._query_steps.append(step)
        return new_query

    def map(self, function):
        """Apply *function* to each element, keeping the results.
        If the group of data is a set type, it will be converted
        to a list (as the results may not be distinct or hashable).
        """
        return self._add_step('map', function)

    def filter(self, function=None):
        """Filter elements, keeping only those values for which
        *function* returns True. If *function* is None, this method
        keeps all elements for which :py:class:`bool` returns True.
        """
        return self._add_step('filter', function)

    def reduce(self, function):
        """Reduce elements to a single value by applying a *function*
        of two arguments cumulatively to all elements from left to
        right.
        """
        return self._add_step('reduce', function)

    def apply(self, function):
        """Apply *function* to entire group keeping the resulting data.
        If element is not iterable, it will be wrapped as a single-item
        list.
        """
        return self._add_step('apply', function)

    def sum(self):
        """Get the sum of non-None elements."""
        return self._add_step('sum')

    def count(self):
        """Get the count of non-None elements."""
        return self._add_step('count')

    def avg(self):
        """Get the average of non-None elements. Strings and other
        objects that do not look like numbers are interpreted as 0.
        """
        return self._add_step('avg')

    def min(self):
        """Get the minimum value from elements."""
        return self._add_step('min')

    def max(self):
        """Get the maximum value from elements."""
        return self._add_step('max')

    def distinct(self):
        """Filter elements, removing duplicate values."""
        return self._add_step('distinct')

    @staticmethod
    def _translate_step(query_step):
        """Accept a query step and return a corresponding execution
        step.
        """
        name, query_args, query_kwds = query_step

        if name == 'map':
            function = _map_data
            args = (query_args[0], RESULT_TOKEN,)
        elif name == 'filter':
            function = _filter_data
            args = (query_args[0], RESULT_TOKEN,)
        elif name == 'reduce':
            function = _reduce_data
            args = (query_args[0], RESULT_TOKEN,)
        elif name == 'apply':
            function = _apply_data
            args = (query_args[0], RESULT_TOKEN,)
        elif name == 'sum':
            function = _apply_to_data
            args = (_sqlite_sum, RESULT_TOKEN)
        elif name == 'count':
            function = _apply_to_data
            args = (_sqlite_count, RESULT_TOKEN)
        elif name == 'avg':
            function = _apply_to_data
            args = (_sqlite_avg, RESULT_TOKEN)
        elif name == 'min':
            function = _apply_to_data
            args = (_sqlite_min, RESULT_TOKEN)
        elif name == 'max':
            function = _apply_to_data
            args = (_sqlite_max, RESULT_TOKEN)
        elif name == 'distinct':
            function = _sqlite_distinct
            args = (RESULT_TOKEN,)
        elif name == 'select':
            raise ValueError("this method does not handle 'select' step")
        else:
            raise ValueError('unrecognized query function {0!r}'.format(name))

        return _execution_step(function, args, {})

    def _get_execution_plan(self, source, query_steps):
        if isinstance(source, Selector):
            execution_plan = [
                _execution_step(getattr, (RESULT_TOKEN, '_select'), {}),
                _execution_step(RESULT_TOKEN, self.args, self.kwds),
            ]
        else:
            execution_plan = [
                _execution_step(_make_dataresult, (RESULT_TOKEN,), {}),
            ]
        for query_step in query_steps:
            execution_step = self._translate_step(query_step)
            execution_plan.append(execution_step)
        return tuple(execution_plan)

    @staticmethod
    def _optimize(execution_plan):
        try:
            step_0 = execution_plan[0]
            step_1 = execution_plan[1]
            step_2 = execution_plan[2]
            remaining_steps = execution_plan[3:]
        except IndexError:
            return None  # <- EXIT!

        if step_0 != (getattr, (RESULT_TOKEN, '_select'), {}):
            return None  # <- EXIT!

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
                    (getattr, (RESULT_TOKEN, '_select_aggregate'), {}),
                    (func_1, args_1, kwds_1),
                )
            else:
                optimized_steps = ()
        elif step_2 == (_sqlite_distinct, (RESULT_TOKEN,), {}):
            optimized_steps = (
                (getattr, (RESULT_TOKEN, '_select_distinct'), {}),
                step_1,
            )
        else:
            optimized_steps = ()

        if optimized_steps:
            return optimized_steps + remaining_steps
        return None

    def execute(self, source=None, optimize=True):
        """A Query can be executed to return a single value or an
        iterable :class:`Result` appropriate for lazy evaluation::

            query = source('A')
            result = query.execute()  # <- Returns Result (iterator)

        Setting *optimize* to False turns-off query optimization.
        """
        if source:
            if self.source:
                raise ValueError((
                    "cannot take 'source' argument, query is "
                    "already associated with a data source: {0!r}"
                ).format(self.source))
            self._validate_source(source)
            result = source
        else:
            if not self.source:
                raise ValueError("missing 'source' argument, none found")
            result = self.source

        execution_plan = self._get_execution_plan(result, self._query_steps)
        if optimize:
            execution_plan = self._optimize(execution_plan) or execution_plan

        replace_token = lambda x: result if x is RESULT_TOKEN else x
        for step in execution_plan:
            function, args, keywords = step  # Unpack 3-tuple.
            function = replace_token(function)
            args = tuple(replace_token(x) for x in args)
            keywords = dict((k, replace_token(v)) for k, v in keywords.items())
            result = function(*args, **keywords)

        return result

    def fetch(self):
        """Executes query and returns an eagerly evaluated result."""
        result = self.execute()
        if isinstance(result, Result):
            return result.fetch()
        return result

    def _explain(self, optimize=True, file=sys.stdout):
        """A convenience method primarily intended to help when
        debugging and developing execution plan optimizations.

        Prints execution plan to the text stream *file* (defaults
        to stdout). If *optimize* is True, an optimized plan will
        be printed if one can be constructed.

        If *file* is set to None, returns execution plan as a string.
        """
        source = self.source
        if source is not None:
            source_repr = repr(source)
            if len(source_repr) > 70:
                source_repr = source_repr[:67] + '...'
        else:
            source = Selector([], fieldnames=['dummy_source'])
            source_repr = '<none given> (assuming Selector object)'

        execution_plan = self._get_execution_plan(source, self._query_steps)

        optimized_text = ''
        if optimize:
            optimized_plan = self._optimize(execution_plan)
            if optimized_plan:
                execution_plan = optimized_plan
                optimized_text = ' (optimized)'

        steps = [_get_step_repr(step) for step in execution_plan]
        steps = '\n'.join('  {0}'.format(step) for step in steps)

        formatted = 'Data Source:\n  {0}\nExecution Plan{1}:\n{2}'
        formatted = formatted.format(source_repr, optimized_text, steps)

        if file:
            file.write(formatted)
            file.write('\n')
        else:
            return formatted

    def __repr__(self):
        class_repr = self.__class__.__name__

        if isinstance(self.source, Selector):
            source_repr = super(Selector, self.source).__repr__()
            is_from_object = False
        elif self.source:
            source_repr = repr(self.source)
            is_from_object = True
        else:
            source_repr = ''
            is_from_object = False

        args_repr = _make_args_repr(self.args)
        if source_repr and args_repr:
            args_repr = ', ' + args_repr

        kwds_repr = _make_kwds_repr(self.kwds)
        if kwds_repr:
            kwds_repr = ', ' + kwds_repr

        all_steps_repr = []
        for step_name, step_args, step_kwds in self._query_steps:
            if step_kwds:
                step_kwds_repr = ', ' + _make_kwds_repr(step_kwds)
            else:
                step_kwds_repr = ''
            step_args_repr = _make_args_repr(step_args)
            step_repr = '{0}({1}{2})'.format(step_name, step_args_repr, step_kwds_repr)
            all_steps_repr.append(step_repr)

        if all_steps_repr:
            query_steps_repr = '.' + ('.'.join(all_steps_repr))
        else:
            query_steps_repr = ''

        if is_from_object:
            return '{0}.from_object({1}){2}'.format(
                class_repr, source_repr, query_steps_repr)
        return '{0}({1}{2}{3}){4}'.format(
            class_repr, source_repr, args_repr, kwds_repr, query_steps_repr)


with contextlib.suppress(AttributeError):  # inspect.Signature() is new in 3.3
    Query.__init__.__signature__ = inspect.Signature([
        inspect.Parameter('self', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('columns', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('where', inspect.Parameter.VAR_KEYWORD),
    ])


_registered_function_ids = collections.defaultdict(set)
def _register_function(connection, func_list):
    """Register user-defined functions with SQLite connection.

    This uses a global defaultdict to prevent from registering
    the same function multiple times with the same connection.
    """
    connection_id = id(connection)
    for func in func_list:
        func_id = id(func)
        if func_id in _registered_function_ids[connection_id]:
            return  # <- EXIT! (if already registered)

        _registered_function_ids[connection_id].add(func_id)

        name = 'FUNC{0}'.format(func_id)
        if isinstance(func, collections.Hashable):
            connection.create_function(name, 1, func)  # <- Register!
        else:
            @functools.wraps(func)
            def wrapper(x):
                return func(x)
            connection.create_function(name, 1, wrapper)  # <- Register!


class Selector(object):
    """A class to quickly load and select tabular data. The given
    *objs*, *\*args*, and *\*\*kwds*, can be any values supported
    by :class:`load_data()`::

        select = datatest.Selector('myfile.csv')

    Create an empty Selector that can be populated later::

        select = datatest.Selector()
    """
    def __init__(self, objs=None, *args, **kwds):
        """Initialize self."""
        self._connection = DEFAULT_CONNECTION
        self._table = None
        self._obj_strings = []
        if objs:
            try:
                self.load_data(objs, *args, **kwds)
            except FileNotFoundError:
                __tracebackhide__ = True
                raise

    def load_data(self, objs, *args, **kwds):
        """Load data from one or more objects. The given *objs*,
        *\*args*, and *\*\*kwds*, can be any values supported by
        :class:`get_reader()`. Additionally, *objs* can be a list
        of supported objects or a string with shell-style wildcards.

        Load data from single objects of various kinds::

            # CSV file.
            select = datatest.Selector()
            select.load_data('myfile.csv')

            # Excel file.
            select = datatest.Selector()
            select.load_data('myfile.xlsx', worksheet='Sheet2')

            # Pandas DataFrame.
            df = pandas.DataFrame([...])
            select = datatest.Selector()
            select.load_data(df)

        Load data from multiple sources using a list of objects::

            select = datatest.Selector()
            select.load_data(['myfile1.csv', 'myfile2.csv'])

        Load data from multple sources using a string with shell-style
        wildcards::

            select = datatest.Selector()
            select.load_data('*.csv')
        """
        if isinstance(objs, string_types):
            obj_list = glob(objs)  # Get shell-style wildcard matches.
            if not obj_list:
                __tracebackhide__ = True
                raise FileNotFoundError('no files matching {0!r}'.format(objs))
        elif not isinstance(objs, list) \
                or isinstance(objs[0], (list, tuple, dict)):  # Not a list or is a
            obj_list = [objs]                                 # reader-like list.
        else:
            obj_list = objs

        cursor = self._connection.cursor()
        with savepoint(cursor):
            table = self._table or new_table_name(cursor)
            for obj in obj_list:
                if ((
                        isinstance(obj, string_types)
                        and obj.lower().endswith('.csv')
                    ) or (
                        isinstance(obj, file_types)
                        and getattr(obj, 'name', '').lower().endswith('.csv')
                    )
                ):
                    load_csv(cursor, table, obj, *args, **kwds)
                else:
                    reader = get_reader(obj, *args, **kwds)
                    load_data(cursor, table, reader)

                self._append_obj_string(obj)

        if not self._table and table_exists(cursor, table):
            self._table = table

    def _append_obj_string(self, obj):
        """Get string for *obj*, limit to one line, and append to list."""
        obj_str = repr(obj)

        obj_str = obj_str.strip().replace('\r\n', ' ').replace('\n', ' ')
        if len(obj_str) > 72:
            obj_str = '{0}...{1}'.format(obj_str[:64], obj_str[-5:])
        self._obj_strings.append(obj_str)

    def __repr__(self):
        """Return a string representation of the data source."""
        if not self._obj_strings:
            return '<Selector (no data loaded)>'

        if len(self._obj_strings) == 1:
            return '<Selector {0}>'.format(self._obj_strings[0])

        return '<Selector ({0} sources):\n    {1}>'.format(
            len(self._obj_strings),
            '\n    '.join(sorted(self._obj_strings)),
        )

    @property
    def fieldnames(self):
        """A list of field names used by the data source."""
        cursor = self._connection.cursor()
        cursor.execute('PRAGMA table_info({0})'.format(self._table))
        return [x[1] for x in cursor]

    def __iter__(self):
        """Return iterable of dictionary rows (like csv.DictReader)."""
        cursor = self._connection.cursor()
        cursor.execute('SELECT * FROM ' + self._table)

        fieldnames = self.fieldnames
        dict_row = lambda x: dict(zip(fieldnames, x))
        return (dict_row(row) for row in cursor.fetchall())

    def __call__(self, columns, **where):
        """After a Selector has been created, it can be called like a
        function to select fields and return an associated :class:`Query`
        object.

        The *columns* argument serves as a template to define the values
        and data types selected. All *columns* selections will be wrapped
        in an outer container. When a container is unspecified, a
        :py:class:`list` is used as the default::

            select = datatest.Selector('example.csv')
            query = select('A')  # <- selects a list of values from 'A'

        When *columns* specifies an outer container, it must hold only
        one field---if a given container holds multiple fields, it is
        assumed to be an inner container (which gets wrapped in the
        default outer container)::

            query = select(('A', 'B'))  # <- selects a list of tuple
                                        #    values from 'A' and 'B'

        When *columns* is a :py:class:`dict`, values are grouped by
        key::

            query = select({'A': 'B'})  # <- selects a dict with
                                        #    keys from 'A' and
                                        #    values from 'B'

        Optional *where* keywords can narrow the selected data to
        matching rows. A key must specify the field to check and a
        value must be a predicate object (see :ref:`predicate-docs`
        for details). Rows where the predicate is a match are
        selected and rows where it doesn't match are excluded::

            select = datatest.Selector('example.csv')
            query = select({'A'}, B='foo')  # <- selects only the rows
                                            #    where 'B' equals 'foo'

        See the :ref:`querying-data` tutorial for step-by-step
        examples.
        """
        try:
            return Query(self, columns, **where)
        except LookupError:
            __tracebackhide__ = True
            raise

    def _execute_query(self, select_clause, trailing_clause=None, **kwds_filter):
        """Execute query and return cursor object."""
        try:
            # Register where-clause functions with SQLite connection.
            func_list = [x for x in kwds_filter.values() if callable(x)]
            _register_function(self._connection, func_list)

            # Build select-query.
            stmnt = 'SELECT {0} FROM {1}'.format(select_clause, self._table)
            where_clause, params = self._build_where_clause(kwds_filter)
            if where_clause:
                stmnt = '{0} WHERE {1}'.format(stmnt, where_clause)
            if trailing_clause:
                stmnt = '{0}\n{1}'.format(stmnt, trailing_clause)

            # Execute query.
            cursor = self._connection.cursor()
            cursor.execute(stmnt, params)

        except Exception as e:
            exc_cls = e.__class__
            msg = '{0}\n  query: {1}\n  params: {2}'.format(e, stmnt, params)
            raise exc_cls(msg)

        return cursor

    @staticmethod
    def _build_where_clause(where_dict):
        """Return 'WHERE' clause that implements *where* keyword
        constraints.
        """
        clause = []
        params = []
        items = where_dict.items()
        items = sorted(items, key=lambda x: x[0])  # Ordered by key.
        for key, val in items:
            # If value is a function.
            if callable(val):
                func_name = 'FUNC{0}'.format(id(val))
                clause.append('{0}({1})'.format(func_name, key))
            # If value is a collection of strings.
            elif nonstringiter(val):
                clause.append('{key} IN ({qmarks})'.format(
                    key=key,
                    qmarks=', '.join('?' * len(val))
                ))
                for x in val:
                    params.append(x)
            # Else, treat as a single value.
            else:
                clause.append(key + '=?')
                params.append(val)

        clause = ' AND '.join(clause) if clause else ''
        return clause, params

    def _format_result_group(self, columns, cursor):
        outer_type = type(columns)
        inner_type = type(next(iter(columns)))
        if issubclass(inner_type, str):
            result = (row[0] for row in cursor)
        elif issubclass(inner_type, tuple) and hasattr(inner_type, '_fields'):
            result = (inner_type(*x) for x in cursor)  # If namedtuple.
        else:
            result = (inner_type(x) for x in cursor)
        return Result(result, evaluation_type=outer_type) # <- EXIT!

    def _format_results(self, columns, cursor):
        """Return an iterator of results formatted by *columns*
        types from DBAPI2-compliant *cursor*.

        The *columns* can be a string, sequence, set or mapping--see
        the _select() method for details.
        """
        if isinstance(columns, (collections.Sequence, collections.Set)):
            return self._format_result_group(columns, cursor)

        if isinstance(columns, collections.Mapping):
            result_type = type(columns)
            key, value = tuple(columns.items())[0]
            key_type = type(key)
            slice_index = 1 if issubclass(key_type, str) else len(key)

            if issubclass(key_type, str):
                keyfunc = lambda row: row[0]
            elif issubclass(key_type, tuple) and hasattr(key_type, '_fields'):
                keyfunc = lambda row: key_type(*row[:slice_index])  # If namedtuple.
            else:
                keyfunc = lambda row: key_type(row[:slice_index])
            grouped = itertools.groupby(cursor, keyfunc)

            inner = next(iter(value))
            index = 1 if isinstance(inner, str) else len(inner)
            sliced = ((k, (x[-index:] for x in g)) for k, g in grouped)
            formatted = ((k, self._format_result_group(value, g)) for k, g in sliced)
            dictitems =  DictItems(formatted)
            return Result(dictitems, evaluation_type=result_type) # <- EXIT!

        raise TypeError('type {0!r} not supported'.format(type(columns)))

    def _assert_fields_exist(self, fieldnames):
        """Assert that given fieldnames are present in data source,
        raises LookupError if fields are missing.
        """
        #assert not isinstance(fieldnames, BaseElement)
        available = self.fieldnames
        for name in fieldnames:
            if name not in available:
                msg = '{0!r} not in {1!r}'.format(name, self)
                __tracebackhide__ = True
                raise LookupError(msg)

    def _escape_field_name(self, name):
        """Escape field names for SQLite."""
        name = name.replace('"', '""')
        return '"{0}"'.format(name)

    def _parse_key_value(self, key, value):
        key_columns = (key,) if isinstance(key, str) else tuple(key)
        value = tuple(value)[0]
        value_columns = (value,) if isinstance(value, str) else  tuple(value)
        self._assert_fields_exist(key_columns)
        self._assert_fields_exist(value_columns)
        key_columns = tuple(self._escape_field_name(x) for x in key_columns)
        value_columns = tuple(self._escape_field_name(x) for x in value_columns)

        return key_columns, value_columns

    def _select(self, columns, **where):
        key, value = _parse_columns(columns)
        key_columns, value_columns = self._parse_key_value(key, value)

        select_clause = ', '.join(key_columns + value_columns)
        if isinstance(value, collections.Set):
            select_clause = 'DISTINCT ' + select_clause

        if key:
            order_by = 'ORDER BY {0}'.format(', '.join(key_columns))
        else:
            order_by = None
        cursor = self._execute_query(select_clause, order_by, **where)
        return self._format_results(columns, cursor)

    def _select_distinct(self, columns, **where):
        key, value = _parse_columns(columns)
        key_columns, value_columns = self._parse_key_value(key, value)

        all_columns = ', '.join(key_columns + value_columns)
        select_clause = 'DISTINCT {0}'.format(all_columns)
        if key:
            order_by = 'ORDER BY {0}'.format(', '.join(key_columns))
        else:
            order_by = None
        cursor = self._execute_query(select_clause, order_by, **where)
        return self._format_results(columns, cursor)

    def _select_aggregate(self, sqlfunc, columns, **where):
        key, value = _parse_columns(columns)
        key_columns, value_columns = self._parse_key_value(key, value)

        if isinstance(value, collections.Set):
            func = lambda col: 'DISTINCT {0}'.format(col)
            value_columns = tuple(func(col) for col in value_columns)

        sqlfunc = sqlfunc.upper()
        value_columns = tuple('{0}({1})'.format(sqlfunc, x) for x in value_columns)
        select_clause = ', '.join(key_columns + value_columns)
        if key:
            group_by = 'GROUP BY {0}'.format(', '.join(key_columns))
        else:
            group_by = None
        cursor = self._execute_query(select_clause, group_by, **where)
        results =  self._format_results(columns, cursor)

        if isinstance(columns, collections.Mapping):
            results = DictItems((k, next(v)) for k, v in results)
            return Result(results, evaluation_type=dict)
        return next(results)

    def create_index(self, *columns):
        """Create an index for specified columns---can speed up
        testing in many cases.

        If you repeatedly use the same few columns to group or
        filter results, then you can often improve performance by
        adding an index for these columns::

            select.create_index('town')

        Using two or more columns creates a multi-column index::

            select.create_index('town', 'postal_code')

        Calling the function multiple times will create multiple
        indexes::

            select.create_index('town')
            select.create_index('postal_code')

        .. note:: Indexes should be added with discretion to tune
                  a test suite's over-all performance.  Creating
                  several indexes before testing even begins could
                  lead to longer run times so use indexes with care.
        """
        self._assert_fields_exist(columns)

        # Build index name.
        whitelist = lambda col: ''.join(x for x in col if x.isalnum())
        idx_name = '_'.join(whitelist(col) for col in columns)
        idx_name = 'idx_{0}_{1}'.format(self._table, idx_name)

        # Build column names.
        columns = tuple(self._escape_field_name(x) for x in columns)

        # Prepare statement.
        statement = 'CREATE INDEX IF NOT EXISTS {0} ON {1} ({2})'
        statement = statement.format(idx_name, self._table, ', '.join(columns))

        # Create index.
        cursor = self._connection.cursor()
        cursor.execute(statement)


# Prepare error message for old or non-standard builds of Python
# that don't have adequate "sqlite3" support (Jython 2.7, Jython
# 2.5, Python 3.1.4, and Python 2.6.6).
if not sqlite3:
    class Selector(object):
        def __init__(self, *args, **kwds):
            msg = (
                'The Selector class requires SQLite but the standard '
                'library "sqlite3" package is missing from the current '
                'Python installation:\n\nPython {0}'
            ).format(sys.version)
            raise Exception(msg)

elif sqlite3.sqlite_version_info < (3, 6, 8):
    class Selector(object):
        def __init__(self, *args, **kwds):
            msg = (
                'The Selector class requires SQLite 3.6.8 or newer but '
                'the current Python installation was built with an old '
                'version:\n\nPython {0}\nBuilt with SQLite {1}'
            ).format(sys.version, sqlite3.sqlite_version)
            raise Exception(msg)
