"""Validation and comparison handling."""
import difflib
import re
from .utils import itertools
from .utils import collections
from .utils.builtins import callable
from .dataaccess import BaseElement
from .dataaccess import DictItems
from .dataaccess import _is_collection_of_items
from .errors import BaseDifference
from .errors import Extra
from .errors import Missing
from .errors import Invalid
from .errors import Deviation
from .errors import _make_difference
from .errors import NOTFOUND

_regex_type = type(re.compile(''))


def _require_sequence(data, sequence):
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


def _require_sequence2(data, sequence):
    """Compare *data* against a *sequence* of values. If differences
    are found, a dictionary is returned with two-tuple keys that
    contain the index positions of the difference in both the *data*
    and *sequence* objects. If no differences are found, returns None.
    """
    if not isinstance(data, collections.Sequence):
        data = tuple(data)

    differences = {}
    def append_diff(i1, i2, j1, j2):
        if j1 == j2:
            for i in range(i1, i2):
                differences[(i, j1)] = Extra(data[i])
        elif i1 == i2:
            for j in range(j1, j2):
                differences[(i1, j)] = Missing(sequence[j])
        else:
            shortest = min(i2 - i1, j2 - j1)
            for i, j in zip(range(i1, i1+shortest), range(j1, j1+shortest)):
                differences[(i, j)] = Invalid(data[i], sequence[j])

            if (i1 + shortest != i2) or (j1 + shortest != j2):
                append_diff(i1+shortest, i2, j1+shortest, j2)

    matcher = difflib.SequenceMatcher(a=data, b=sequence)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != 'equal':
            append_diff(i1, i2, j1, j2)

    return differences


def _require_set(data, requirement_set):
    """Compare *data* against a *requirement_set* of values."""
    if data is NOTFOUND:
        data = []
    elif isinstance(data, BaseElement):
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


def _require_callable(data, function):
    if data is NOTFOUND:
        data = [None]
    elif isinstance(data, BaseElement):
        data = [data]

    for element in data:
        try:
            if isinstance(element, BaseElement):
                returned_value = function(element)
            else:
                returned_value = function(*element)
        except Exception:
            returned_value = False  # Raised errors count as False.

        if returned_value is True:
            continue

        if returned_value is False:
            yield Invalid(element)
            continue

        if isinstance(returned_value, BaseDifference):
            yield returned_value  # Returned difference is used as-is.
            continue

        callable_name = function.__name__
        message = \
            '{0!r} returned {1!r}, should return True, False or a difference instance'
        raise TypeError(message.format(callable_name, returned_value))


def _require_regex(data, regex):
    if data is NOTFOUND:
        data = [None]
    elif isinstance(data, BaseElement):
        data = [data]

    search = regex.search
    for element in data:
        try:
            if search(element) is None:
                yield Invalid(element)
        except TypeError:
            yield Invalid(element)


def _require_other(data, other, show_expected=True):
    """Compare *data* against *other* object--one that does not match
    another supported comparison type.
    """
    for element in data:
        try:
            if not other == element:  # Uses "==" to trigger __eq__() call.
                yield _make_difference(element, other, show_expected)
        except Exception:
            yield _make_difference(element, other, show_expected)


def _apply_requirement(data, requirement):
    """Compare *data* against *requirement* using appropriate
    comparison function (as determined by *requirement* type).

    Returns one of three types:
     * an iterable of errors,
     * a single error,
     * or None.
    """
    if not isinstance(requirement, str) and \
               isinstance(requirement, collections.Sequence):
        result = _require_sequence(data, requirement)
        return result  # <- EXIT!

    if isinstance(requirement, collections.Set):
        result =  _require_set(data, requirement)
        first_element = next(result, None)
        if first_element:
            return itertools.chain([first_element], result)  # <- EXIT!
        return None  # <- EXIT!

    is_single_element = isinstance(data, BaseElement)
    if is_single_element:
        data = [data]

    if callable(requirement):
        result = _require_callable(data, requirement)
    elif isinstance(requirement, _regex_type):
        result = _require_regex(data, requirement)
    else:
        result = _require_other(data, requirement,
                                show_expected=is_single_element)

    first_element = next(result, None)
    if first_element:
        if is_single_element:
            return first_element  # <- EXIT!
        return itertools.chain([first_element], result)  # <- EXIT!
    return None


def _apply_mapping_requirement(data, mapping):
    if isinstance(data, collections.Mapping):
        data_items = getattr(data, 'iteritems', data.items)()
    elif _is_collection_of_items(data):
        data_items = data
    else:
        raise TypeError('data must be mapping or iterable of key-value items')

    data_keys = set()
    for key, actual in data_items:
        data_keys.add(key)
        expected = mapping.get(key, NOTFOUND)
        result = _apply_requirement(actual, expected)
        if result:
            if not isinstance(result, BaseElement):
                result = list(result)
            yield key, result

    mapping_items = getattr(mapping, 'iteritems', mapping.items)()
    for key, expected in mapping_items:
        if key not in data_keys:
            result = _apply_requirement(NOTFOUND, expected)
            if not isinstance(result, BaseElement):
                result = list(result)
            yield key, result


def _normalize_mapping_result(result):
    """Accepts an iterator of dictionary items and returns a DictItems
    object or None.
    """
    first_element = next(result, None)
    if first_element:
        assert len(first_element) == 2, 'expects tuples of key-value pairs'
        return DictItems(itertools.chain([first_element], result))  # <- EXIT!
    return None


def _find_differences(data, requirement):
    """Return iterable of differences or None."""
    if isinstance(requirement, collections.Mapping):
        result = _apply_mapping_requirement(data, requirement)
        result = _normalize_mapping_result(result)
    elif isinstance(data, collections.Mapping):
        items = getattr(data, 'iteritems', data.items)()
        result = ((k, _apply_requirement(v, requirement)) for k, v in items)
        iter_to_list = lambda x: x if isinstance(x, BaseElement) else list(x)
        result = ((k, iter_to_list(v)) for k, v in result if v)
        result = _normalize_mapping_result(result)
    else:
        result = _apply_requirement(data, requirement)
        if isinstance(result, BaseDifference):
            result = [result]
    return result
