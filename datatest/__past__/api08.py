"""Backward compatibility for version 0.8 API."""
from __future__ import absolute_import
import inspect

import datatest
from datatest.utils import collections
from datatest.utils import itertools
from datatest.difference import NOTFOUND


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


def _columns(self, type=list):  # Removed in datatest 0.8.2
    return type(self.fieldnames)
datatest.DataSource.columns = _columns


def _require_sequence(data, sequence):  # New behavior in datatest 0.8.3
    """Compare *data* against a *sequence* of values. Stops at the
    first difference found and returns an AssertionError. If no
    differences are found, returns None.
    """
    if isinstance(data, str):
        raise ValueError("uncomparable types: 'str' and sequence type")

    data_type = getattr(data, 'evaluation_type', data.__class__)
    if not issubclass(data_type, collections.Sequence):
        type_name = data_type.__name__
        msg = "expected sequence type, but got " + repr(type_name)
        raise ValueError(msg)

    message_prefix = None
    previous_element = NOTFOUND
    zipped = itertools.zip_longest(data, sequence, fillvalue=NOTFOUND)
    for index, (actual, expected) in enumerate(zipped):
        if actual == expected:
            previous_element = actual
            continue

        if actual == NOTFOUND:
            message_prefix = ('Data sequence is missing '
                             'elements starting with index {0}').format(index)
            message_suffix = 'Expected {0!r}'.format(expected)
        elif expected == NOTFOUND:
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
    if previous_element != NOTFOUND:
        leading_elements.append(repr(previous_element))

    actual_repr = repr(actual) if actual != NOTFOUND else '?????'
    caret_underline = '^' * len(actual_repr)

    trailing_elements = []
    next_tuple = next(zipped, NOTFOUND)
    if next_tuple != NOTFOUND:
        trailing_elements.append(repr(next_tuple[0]))
        if next(zipped, NOTFOUND) != NOTFOUND:
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
