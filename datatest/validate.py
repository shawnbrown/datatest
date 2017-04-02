"""Validation and comparison handling."""
from .utils import itertools
from .utils import collections
from .utils.misc import _is_nsiterable
from .errors import DataError
from .errors import Extra
from .errors import Missing
from .errors import Invalid
from .errors import Deviation
from .errors import _get_error
from .errors import NOTFOUND


def _compare_sequence(data, sequence):
    """Compare *data* against a *sequence* values. Stops at the
    first difference found and returns an AssertionError. If no
    differences are found, returns None.
    """
    if isinstance(data, str):
        raise ValueError("uncomparable types: 'str' and sequence type")

    if not isinstance(data, collections.Sequence):
        type_name = type(data).__name__
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


def _compare_set(data, requirement_set):
    """Compare *data* against a *requirement_set* of values."""
    if not _is_nsiterable(data):
        data = [data]

    matching_elements = set()
    extra_elements = set()
    for element in data:
        if element in requirement_set:
            matching_elements.add(element)
        else:
            extra_elements.add(element)

    missing_elements = requirement_set.difference(matching_elements)

    missing = (Missing(x) for x in missing_elements)
    extra = (Extra(x) for x in extra_elements)
    return itertools.chain(missing, extra)


def _compare_callable(data, function):
    for element in data:
        try:
            if _is_nsiterable(element):
                returned_value = function(*element)
            else:
                returned_value = function(element)
        except Exception:
            returned_value = False  # Raised errors count as False.

        if returned_value is True:
            continue
        if returned_value is False:
            yield Invalid(element)
            continue
        if isinstance(returned_value, DataError):
            yield returned_value  # Returned data errors are used as-is.
            continue

        callable_name = function.__name__
        message = \
            '{0!r} returned {1!r}, should return True, False or DataError'
        raise TypeError(message.format(callable_name, returned_value))


def _compare_regex(data, regex):
    search = regex.search
    for element in data:
        try:
            if search(element) is None:
                yield Invalid(element)
        except TypeError:
            yield Invalid(element)


def _compare_other(data, other):
    """Compare *data* against *other* object--one that does not match
    another supported comparison type.
    """
    for element in data:
        try:
            if element != other:
                yield _get_error(element, other, omit_expected=True)
        except Exception:
            yield _get_error(element, other, omit_expected=True)
