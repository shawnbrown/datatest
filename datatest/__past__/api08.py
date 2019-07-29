"""Backward compatibility for version 0.8 API."""
from __future__ import absolute_import
import inspect

import datatest
from datatest._compatibility import itertools
from datatest._compatibility.collections.abc import Sequence
from datatest._vendor.get_reader import get_reader
from datatest._load.load_csv import load_csv
from datatest._vendor.temptable import (
    load_data,
    new_table_name,
    savepoint,
    table_exists,
)
from datatest._query.query import DEFAULT_CONNECTION
from datatest._query.query import BaseElement
from datatest._utils import file_types
from datatest._utils import string_types
from datatest._utils import iterpeek
from datatest.acceptances import BaseAcceptance
from datatest import Invalid
from datatest.differences import NOVALUE

datatest.DataResult = datatest.Result


class DataQuery(datatest.Query):
    def __call__(self, *args, **kwds):
        self.execute(*args, **kwds)
datatest.DataQuery = DataQuery


class DataSource(datatest.Select):
    def __init__(self, data, fieldnames=None):
        first_value, iterator = iterpeek(data)
        if isinstance(first_value, dict):
            if not fieldnames:
                fieldnames = list(first_value.keys())
            super(DataSource, self).__init__(iterator, fieldnames)
        else:
            if fieldnames:
                iterator = itertools.chain([fieldnames], iterator)
            super(DataSource, self).__init__(iterator)

    @classmethod
    def from_csv(cls, file, encoding=None, **fmtparams):
        if isinstance(file, string_types) or isinstance(file, file_types):
            data_list = [file]
        else:
            data_list = file

        new_cls = cls.__new__(cls)
        new_cls._connection = DEFAULT_CONNECTION
        cursor = new_cls._connection.cursor()
        with savepoint(cursor):
            table = new_table_name(cursor)
            for obj in data_list:
                load_csv(cursor, table, obj, encoding=encoding, **fmtparams)
        new_cls._table = table if table_exists(cursor, table) else None
        new_cls._data = file
        new_cls._args = (encoding,)
        new_cls._kwds = fmtparams
        new_cls._update_list = []
        return new_cls

    @classmethod
    def from_excel(cls, path, worksheet=0):
        new_cls = cls.__new__(cls)
        new_cls._connection = DEFAULT_CONNECTION
        cursor = new_cls._connection.cursor()
        with savepoint(cursor):
            table = new_table_name(cursor)
            reader = get_reader.from_excel(path, worksheet=0)
            load_data(cursor, table, reader)
        new_cls._table = table if table_exists(cursor, table) else None
        new_cls._data = path
        new_cls._args = tuple()
        new_cls._kwds = dict()
        if worksheet != 0:
            new_cls._kwds['worksheet'] = worksheet
        new_cls._update_list = []
        return new_cls

    def columns(self, type=list):  # Removed in datatest 0.8.2
        return type(self.fieldnames)

datatest.DataSource = DataSource


class allowed_key(BaseAcceptance):
    """The given *function* should accept a number of arguments
    equal the given key elements. If key is a single value (string
    or otherwise), *function* should accept one argument. If key
    is a three-tuple, *function* should accept three arguments.
    """
    def __init__(self, function, msg=None):
        super(allowed_key, self).__init__(msg)
        self.function = function

    @property
    def scope(self):
        return frozenset(['element'])

    def __repr__(self):
        cls_name = self.__class__.__name__
        msg_part = ', msg={0!r}'.format(self.msg) if self.msg else ''
        return '{0}({1!r}{2})'.format(cls_name, self.function, msg_part)

    def call_predicate(self, item):
        key = item[0]
        if not isinstance(key, tuple) and isinstance(key, BaseElement):
            return self.function(key)
        return self.function(*key)

datatest.allowed_key = allowed_key


class AcceptedArgs(BaseAcceptance):
    """The given *function* should accept a number of arguments equal
    the given elements in the 'args' attribute. If args is a single
    value (string or otherwise), *function* should accept one argument.
    If args is a three-tuple, *function* should accept three arguments.
    """
    def __init__(self, function, msg=None):
        super(AcceptedArgs, self).__init__(msg)
        self.function = function

    @property
    def scope(self):
        return frozenset(['element'])

    def __repr__(self):
        cls_name = self.__class__.__name__
        msg_part = ', msg={0!r}'.format(self.msg) if self.msg else ''
        return '{0}({1!r}{2})'.format(cls_name, self.function, msg_part)

    def call_predicate(self, item):
        args = item[1].args
        if not isinstance(args, tuple) and isinstance(args, BaseElement):
            return self.function(args)
        return self.function(*args)

datatest.AcceptedArgs = AcceptedArgs


def get_subject(self):
    if hasattr(self, '_subject_data'):
        return self._subject_data
    return self._find_data_source('subject')
def set_subject(self, value):
    self._subject_data = value
datatest.DataTestCase.subject = property(get_subject, set_subject)


def get_reference(self):
    if hasattr(self, '_reference_data'):
        return self._reference_data
    return self._find_data_source('reference')
def set_reference(self, value):
    self._reference_data = value
datatest.DataTestCase.reference = property(get_reference, set_reference)


def _find_data_source(name):
    stack = inspect.stack()
    stack.pop()  # Skip record of current frame.
    for record in stack:   # Bubble-up stack looking for name.
        frame = record[0]
        if name in frame.f_globals:
            return frame.f_globals[name]  # <- EXIT!
    raise NameError('cannot find {0!r}'.format(name))
datatest.DataTestCase._find_data_source = staticmethod(_find_data_source)


def allowedKey(self, function, msg=None):
    """Allows differences in a mapping where *function* returns True.
    For each difference, function will receive the associated mapping
    **key** unpacked into one or more arguments.
    """
    return allowed_key(function, msg)
datatest.DataTestCase.allowedKey = allowedKey


def allowedArgs(self, function, msg=None):
    """Accepts differences where *function* returns True. For the
    'args' attribute of each difference (a tuple), *function* must
    accept the number of arguments unpacked from 'args'.
    """
    return AcceptedArgs(function, msg)
datatest.DataTestCase.allowedArgs = allowedArgs


def _require_sequence(data, sequence):  # New behavior in datatest 0.8.3
    """Compare *data* against a *sequence* of values. Stops at the
    first difference found and returns an AssertionError. If no
    differences are found, returns None.
    """
    if isinstance(data, str):
        raise ValueError("uncomparable types: 'str' and sequence type")

    data_type = getattr(data, 'evaluation_type', data.__class__)
    if not issubclass(data_type, Sequence):
        type_name = data_type.__name__
        msg = "expected sequence type, but got " + repr(type_name)
        raise ValueError(msg)

    message_prefix = None
    previous_element = NOVALUE
    zipped = itertools.zip_longest(data, sequence, fillvalue=NOVALUE)
    for index, (actual, expected) in enumerate(zipped):
        if actual == expected:
            previous_element = actual
            continue

        if actual == NOVALUE:
            message_prefix = ('Data sequence is missing '
                             'elements starting with index {0}').format(index)
            message_suffix = 'Expected {0!r}'.format(expected)
        elif expected == NOVALUE:
            message_prefix = ('Data sequence contains extra '
                             'elements starting with index {0}').format(index)
            message_suffix = 'Found {0!r}'.format(actual)
        else:
            message_prefix = \
                'Data sequence differs starting at index {0}'.format(index)
            message_suffix = \
                'Found {0!r}, expected {1!r}'.format(actual, expected)
        break
    else:  # <- NOBREAK!
        return None  # <- EXIT!

    leading_elements = []
    if index > 1:
        leading_elements.append('...')
    if previous_element != NOVALUE:
        leading_elements.append(repr(previous_element))

    actual_repr = repr(actual) if actual != NOVALUE else '?????'
    caret_underline = '^' * len(actual_repr)

    trailing_elements = []
    next_tuple = next(zipped, NOVALUE)
    if next_tuple != NOVALUE:
        trailing_elements.append(repr(next_tuple[0]))
        if next(zipped, NOVALUE) != NOVALUE:
            trailing_elements.append('...')

    if leading_elements:
        leading_string = ', '.join(leading_elements) + ', '
    else:
        leading_string = ''
    leading_whitespace = ' ' * len(leading_string)

    if trailing_elements:
        trailing_string = ', ' + ', '.join(trailing_elements)
    else:
        trailing_string = ''

    sequence_string = leading_string + actual_repr + trailing_string

    message = '{0}:\n\n  {1}\n  {2}{3}\n{4}'.format(message_prefix,
                                                    sequence_string,
                                                    leading_whitespace,
                                                    caret_underline,
                                                    message_suffix)
    return AssertionError(message)
datatest.validation._require_sequence = _require_sequence


def _require_callable(data, function):
    if data is NOVALUE:
        return Invalid(None)  # <- EXIT!

    def wrapped(element):
        try:
            if isinstance(element, BaseElement):
                returned_value = function(element)
            else:
                returned_value = function(*element)
        except Exception:
            returned_value = False  # Raised errors count as False.

        if returned_value == True:
            return None  # <- EXIT!

        if returned_value == False:
            return Invalid(element)  # <- EXIT!

        if isinstance(returned_value, BaseDifference):
            return returned_value  # <- EXIT!

        callable_name = function.__name__
        message = \
            '{0!r} returned {1!r}, should return True, False or a difference instance'
        raise TypeError(message.format(callable_name, returned_value))

    if isinstance(data, BaseElement):
        return wrapped(data)  # <- EXIT!

    results = (wrapped(elem) for elem in data)
    diffs = (diff for diff in results if diff)
    first_element, diffs = iterpeek(diffs)
    if first_element:  # If not empty, return diffs.
        return diffs
    return None
