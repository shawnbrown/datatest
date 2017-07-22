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


def _deephash(obj):
    """Return a "deep hash" value for the given object. If the
    object can not be deep-hashed, a TypeError is raised.
    """
    # Adapted from "deephash" Copyright 2017 Shawn Brown, Apache License 2.0.
    already_seen = {}

    def _hashable_proxy(obj):
        if isinstance(obj, collections.Hashable) and not isinstance(obj, tuple):
            return obj  # <- EXIT!

        # Guard against recursive references in compound objects.
        obj_id = id(obj)
        if obj_id in already_seen:
            return already_seen[obj_id]  # <- EXIT!
        else:
            already_seen[obj_id] = object()  # Token for duplicates.

        # Recurse into compound object to make hashable proxies.
        if isinstance(obj, collections.Sequence):
            proxy = tuple(_hashable_proxy(x) for x in obj)
        elif isinstance(obj, collections.Set):
            proxy = frozenset(_hashable_proxy(x) for x in obj)
        elif isinstance(obj, collections.Mapping):
            items = getattr(obj, 'iteritems', obj.items)()
            items = ((k, _hashable_proxy(v)) for k, v in items)
            proxy = frozenset(items)
        else:
            message = 'unhashable type: {0!r}'.format(obj.__class__.__name__)
            raise TypeError(message)
        return obj.__class__, proxy

    try:
        return hash(obj)
    except TypeError:
        return hash(_hashable_proxy(obj))


def _require_sequence(data, sequence):
    """Compare *data* against a *sequence* of values. If differences
    are found, a dictionary is returned with two-tuple keys that
    contain the index positions of the difference in both the *data*
    and *sequence* objects. If no differences are found, returns None.

    This function uses difflib.SequenceMatcher() which requires hashable
    values. This said, _require_sequence() will make a best effort
    attempt to build a "deep hash" to sort many types of unhashable
    objects.
    """
    data_type = getattr(data, 'evaluation_type', data.__class__)
    if issubclass(data_type, BaseElement) or \
            not issubclass(data_type, collections.Sequence):
        msg = 'data type {0!r} can not be checked for sequence order'
        raise ValueError(msg.format(data_type.__name__))

    if not isinstance(data, collections.Sequence):
        data = tuple(data)

    try:
        matcher = difflib.SequenceMatcher(a=data, b=sequence)
    except TypeError:  # Fall back to slower "deep hash" only if needed.
        data_proxy = tuple(_deephash(x) for x in data)
        sequence_proxy = tuple(_deephash(x) for x in sequence)
        matcher = difflib.SequenceMatcher(a=data_proxy, b=sequence_proxy)

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

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != 'equal':
            append_diff(i1, i2, j1, j2)

    return differences or None


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

    if extra_elements or missing_elements:
        missing = (Missing(x) for x in missing_elements)
        extra = (Extra(x) for x in extra_elements)
        return itertools.chain(missing, extra)
    return None


def _require_callable(data, function):
    if data is NOTFOUND:
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
    first_element = next(diffs, None)
    if first_element:
        return itertools.chain([first_element], diffs)  # <- EXIT!
    return None


def _require_regex(data, regex):
    search = regex.search  # Assign locally to minimize dot-lookups.
    func = lambda element: search(element) is not None
    return _require_callable(data, func)


def _require_other(data, other, show_expected=True):
    """Compare *data* against *other* object--one that does not match
    another supported comparison type.
    """
    def func(element):
        try:
            if not other == element:  # Uses "==" to trigger __eq__() call.
                return _make_difference(element, other, show_expected)
        except Exception:
            return _make_difference(element, other, show_expected)

    if isinstance(data, BaseElement):
        return func(data)  # <- EXIT!

    results = (func(elem) for elem in data)
    diffs = (diff for diff in results if diff)
    first_element = next(diffs, None)
    if first_element:
        return itertools.chain([first_element], diffs)  # <- EXIT!
    return None


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
        return _require_sequence(data, requirement)  # <- EXIT!

    if isinstance(requirement, collections.Set):
        return _require_set(data, requirement)  # <- EXIT!

    if callable(requirement):
        return _require_callable(data, requirement)  # <- EXIT!

    if isinstance(requirement, _regex_type):
        return _require_regex(data, requirement)  # <- EXIT!

    is_single_element = isinstance(data, BaseElement)
    return _require_other(data, requirement, show_expected=is_single_element)


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


#def _get_difference_info(data, requirement):
def _find_differences(data, requirement):
    """Return iterable of differences or None."""
    if isinstance(requirement, collections.Mapping):
        result = _apply_mapping_requirement(data, requirement)
        result = _normalize_mapping_result(result)
        default_msg = 'does not satisfy mapping requirement'
    elif isinstance(data, collections.Mapping):
        items = getattr(data, 'iteritems', data.items)()
        result = ((k, _apply_requirement(v, requirement)) for k, v in items)
        iter_to_list = lambda x: x if isinstance(x, BaseElement) else list(x)
        result = ((k, iter_to_list(v)) for k, v in result if v)
        result = _normalize_mapping_result(result)
        default_msg = None
    else:
        result = _apply_requirement(data, requirement)
        #default_msg, result = _apply_requirement(data, requirement)
        if isinstance(result, BaseDifference):
            result = [result]
        default_msg = None

    if not result:
        return None
    return (default_msg, result)
