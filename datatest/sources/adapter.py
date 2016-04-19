# -*- coding: utf-8 -*-
from ..utils.builtins import *
from ..utils import collections

from ..compare import CompareDict
from ..compare import CompareSet
from ..compare import _is_nscontainer

from .base import BaseSource


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

    def sum(self, column, keys=None, **kwds_filter):
        """Returns sum of *column* grouped by *keys* as CompareDict."""
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

        result = unwrap_src.sum(unwrap_col, unwrap_keys, **unwrap_flt)

        rewrap_col = self._rewrap_columns(unwrap_col)
        rewrap_keys = self._rewrap_columns(unwrap_keys)
        return self._rebuild_comparedict(result, rewrap_col, column,
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
