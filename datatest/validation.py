"""Validation and comparison handling."""
import difflib
import re
import sys
from ._compatibility import itertools
from ._compatibility import collections
from ._compatibility.builtins import callable
from ._predicate import PredicateObject
from ._predicate import get_predicate
from ._utils import nonstringiter
from ._utils import exhaustible
from ._utils import iterpeek
from ._utils import _safesort_key
from ._query.query import (
    BaseElement,
    DictItems,
    _is_collection_of_items,
    Query,
    Result,
)
from .difference import (
    BaseDifference,
    Extra,
    Missing,
    Invalid,
    Deviation,
    _make_difference,
    NOTFOUND,
)


__all__ = [
    'validate',
    'valid',
    'ValidationError',
]


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


def _require_predicate(value, other, show_expected=False):
    # Predicate comparisons use "==" to trigger __eq__(), not "!=".
    if isinstance(other, PredicateObject):
        matches = other == value
    elif callable(other) and not isinstance(other, type):
        matches = other(value)
    else:
        matches = get_predicate(other) == value

    if not matches:
        return _make_difference(value, other, show_expected)
    elif isinstance(matches, BaseDifference):
        return matches
    return None


def _require_predicate_expected(value, other):
    return _require_predicate(value, other, show_expected=True)


def _require_predicate_from_iterable(data, other):
    if data is NOTFOUND:
        return Invalid(None)  # <- EXIT!

    if isinstance(data, tuple):
        data = [data]

    if callable(other) and not isinstance(other, type):
        predicate = other
    else:
        predicate = get_predicate(other)

    diffs = (_require_predicate(value, predicate) for value in data)
    diffs = (x for x in diffs if x)

    first_element, diffs = iterpeek(diffs)
    if first_element:  # If not empty, return diffs.
        return diffs
    return None


def _get_msg_and_func(data, requirement):
    """
    Each validation-function must accept an iterable of differences,
    a single difference, or None.
    """
    # Check for special cases--*requirement* types
    # that trigger a particular validation method.
    if not isinstance(requirement, (str, tuple)) and \
               isinstance(requirement, collections.Sequence):
        return 'does not match sequence order', _require_sequence

    if isinstance(requirement, collections.Set):
        return 'does not satisfy set membership', _require_set

    # If *requirement* did not match any of the special cases
    # above, then return an appropriate equality function.
    if isinstance(data, (tuple, BaseElement)):    # <- Based on *data* not
        equality_func = _require_predicate        #    *requirement* like
    else:                                         #    the rest.
        equality_func = _require_predicate_from_iterable

    if isinstance(requirement, _regex_type):
        equality_msg = 'does not satisfy regex {0!r}'.format(requirement.pattern)
    elif isinstance(requirement, (PredicateObject, BaseElement)):
        equality_msg = 'does not satisfy {0!r}'.format(requirement)
    else:
        equality_msg = 'does not satisfy requirement'

    return equality_msg, equality_func


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

        _, require_func = _get_msg_and_func(actual, expected)
        if require_func is _require_predicate:
            require_func = _require_predicate_expected
        diff = require_func(actual, expected)
        if diff:
            if not isinstance(diff, (tuple, BaseElement)):
                diff = list(diff)
            yield key, diff

    mapping_items = getattr(mapping, 'iteritems', mapping.items)()
    for key, expected in mapping_items:
        if key not in data_keys:
            _, require_func = _get_msg_and_func(NOTFOUND, expected)
            if require_func is _require_predicate:
                require_func = _require_predicate_expected
            diff = require_func(NOTFOUND, expected)
            if not isinstance(diff, (tuple, BaseElement)):
                diff = list(diff)
            yield key, diff


def _normalize_mapping_result(result):
    """Accepts an iterator of dictionary items and returns a DictItems
    object or None.
    """
    first_element, result = iterpeek(result)
    if first_element:
        assert len(first_element) == 2, 'expects tuples of key-value pairs'
        return DictItems(result)  # <- EXIT!
    return None


def _normalize_data(data):
    if isinstance(data, Query):
        return data()  # <- EXIT! (Returns Result for lazy evaluation.)

    pandas = sys.modules.get('pandas', None)
    if pandas:
        try:
            if isinstance(data, pandas.Series):
                assert data.index.is_unique
                return DictItems(data.iteritems())  # <- EXIT!

            if isinstance(data, pandas.DataFrame):
                assert data.index.is_unique
                gen = ((x[0], x[1:]) for x in data.itertuples())
                if len(data.columns) == 1:
                    gen = ((k, v[0]) for k, v in gen)  # Unwrap if 1-tuple.
                return DictItems(gen)  # <- EXIT!

        except AssertionError:
            cls_name = data.__class__.__name__
            raise ValueError(('{0} index contains duplicates, must '
                              'be unique').format(cls_name))

    numpy = sys.modules.get('numpy', None)
    if numpy and isinstance(data, numpy.ndarray):
        # Two-dimentional array, recarray, or structured array.
        if data.ndim == 2 or (data.ndim == 1 and len(data.dtype) > 1):
            data = (tuple(x) for x in data)
            return Result(data, evaluation_type=list)  # <- EXIT!

        # One-dimentional array, recarray, or structured array.
        if data.ndim == 1:
            if len(data.dtype) == 1:         # Unpack single-valued recarray
                data = (x[0] for x in data)  # or structured array.
            else:
                data = iter(data)
            return Result(data, evaluation_type=list)  # <- EXIT!

    return data


def _normalize_requirement(requirement):
    requirement = _normalize_data(requirement)

    if isinstance(requirement, Result):
        return requirement.fetch()  # <- Eagerly evaluate.

    if isinstance(requirement, DictItems):
        return dict(requirement)

    if isinstance(requirement, collections.Iterable) \
            and exhaustible(requirement):
        cls_name = requirement.__class__.__name__
        raise TypeError(("exhaustible type '{0}' cannot be used "
                         "as a requirement").format(cls_name))

    return requirement


def _get_invalid_info(data, requirement):
    """If data is invalid, return a 2-tuple containing a default-message
    string and an iterable of differences. If data is not invalid,
    return None.
    """
    data = _normalize_data(data)
    if isinstance(data, collections.Mapping):
        data = getattr(data, 'iteritems', data.items)()

    requirement = _normalize_requirement(requirement)

    # Get default-message and differences (if any exist).
    if isinstance(requirement, collections.Mapping):
        default_msg = 'does not satisfy mapping requirement'
        diffs = _apply_mapping_requirement(data, requirement)
        diffs = _normalize_mapping_result(diffs)
    elif _is_collection_of_items(data):
        first_item, data = iterpeek(data)
        default_msg, require_func = _get_msg_and_func(first_item[1], requirement)
        diffs = ((k, require_func(v, requirement)) for k, v in data)
        iter_to_list = lambda x: x if isinstance(x, BaseElement) else list(x)
        diffs = ((k, iter_to_list(v)) for k, v in diffs if v)
        diffs = _normalize_mapping_result(diffs)
    else:
        default_msg, require_func = _get_msg_and_func(data, requirement)
        diffs = require_func(data, requirement)
        if isinstance(diffs, BaseDifference):
            diffs = [diffs]

    if not diffs:
        return None
    return (default_msg, diffs)


class ValidationError(AssertionError):
    """This exception is raised when data validation fails."""

    __module__ = 'datatest'

    def __init__(self, differences, description=None):
        if isinstance(differences, BaseDifference):
            differences = [differences]
        elif not nonstringiter(differences):
            msg = 'expected an iterable of differences, got {0!r}'
            raise TypeError(msg.format(differences.__class__.__name__))

        # Normalize *differences* argument.
        if _is_collection_of_items(differences):
            differences = dict(differences)
        elif exhaustible(differences):
            differences = list(differences)

        if not differences:
            raise ValueError('differences container must not be empty')

        # Initialize properties.
        self._differences = differences
        self._description = description
        self._should_truncate = None
        self._truncation_notice = None

    @property
    def differences(self):
        """A collection of "difference" objects to describe elements
        in the data under test that do not satisfy the requirement.
        """
        return self._differences

    @property
    def description(self):
        """An optional description of the failed requirement."""
        return self._description

    @property
    def args(self):
        """The tuple of arguments given to the exception constructor."""
        return (self._differences, self._description)

    def __str__(self):
        # Prepare a format-differences callable.
        if isinstance(self._differences, dict):
            begin, end = '{', '}'
            all_keys = sorted(self._differences.keys(), key=_safesort_key)
            def sorted_value(key):
                value = self._differences[key]
                if nonstringiter(value):
                    sort_args = lambda diff: _safesort_key(diff.args)
                    return sorted(value, key=sort_args)
                return value
            iterator = iter((key, sorted_value(key)) for key in all_keys)
            format_diff = lambda x: '    {0!r}: {1!r},'.format(x[0], x[1])
        else:
            begin, end = '[', ']'
            sort_args = lambda diff: _safesort_key(diff.args)
            iterator = iter(sorted(self._differences, key=sort_args))
            format_diff = lambda x: '    {0!r},'.format(x)

        # Format differences as a list of strings and get line count.
        if self._should_truncate:
            line_count = 0
            char_count = 0
            list_of_strings = []
            for x in iterator:                  # For-loop used to build list
                line_count += 1                 # iteratively to optimize for
                diff_string = format_diff(x)    # memory (in case the iter of
                char_count += len(diff_string)  # diffs is extremely long).
                if self._should_truncate(line_count, char_count):
                    line_count += sum(1 for x in iterator)
                    end = '    ...'
                    if self._truncation_notice:
                        end += '\n\n{0}'.format(self._truncation_notice)
                    break
                list_of_strings.append(diff_string)
        else:
            list_of_strings = [format_diff(x) for x in iterator]
            line_count = len(list_of_strings)

        # Prepare count-of-differences string.
        count_message = '{0} difference{1}'.format(
            line_count,
            '' if line_count == 1 else 's',
        )

        # Prepare description string.
        if self._description:
            description = '{0} ({1})'.format(self._description, count_message)
        else:
            description = count_message

        # Prepare final output.
        output = '{0}: {1}\n{2}\n{3}'.format(
            description,
            begin,
            '\n'.join(list_of_strings),
            end,
        )
        return output

    def __repr__(self):
        cls_name = self.__class__.__name__
        if self.description:
            return '{0}({1!r}, {2!r})'.format(cls_name, self.differences, self.description)
        return '{0}({1!r})'.format(cls_name, self.differences)


def valid(data, requirement):
    """Return True if *data* satisfies *requirement* else return False."""
    if _get_invalid_info(data, requirement):
        return False
    return True


def validate(data, requirement, msg=None):
    """Raise a :exc:`ValidationError` if *data* does not satisfy
    *requirement* (or pass without error if data is valid).

    The given *requirement* can be a single predicate, a mapping
    of predicates, or a list of predicates (see :ref:`predicate-docs`
    for details).

    For values that fail to satisfy their predicates, "difference"
    objects are generated and used to create a :exc:`ValidationError`.
    If a predicate function returns a difference, the result is
    counted as a failure and the returned difference is used in
    place of an automatically generated one.

    **Single Predicates:** When *requirement* is a single predicate,
    all of the values in *data* are checked for the same
    criteria---*data* can be a single value (including strings),
    a mapping, or an iterable::

        data = [1, 3, 5, 7]

        def isodd(x):  # <- Predicate function
            return x % 2 == 1

        datatest.validate(data, isodd)

    **Mappings:** When *requirement* is a dictionary or other
    mapping, the values in *data* are checked against predicates
    of the same key (requires that *data* is also a mapping)::

        data = {
            'A': 1,
            'B': 2,
            'C': ...
        }

        requirement = {  # <- Mapping of predicates
            'A': 1,
            'B': 2,
            'C': ...
        }

        datatest.validate(data, requirement)

    **Sequences:** When *requirement* is list (or other non-tuple,
    non-string sequence), the values in *data* are checked for
    matching order (requires that *data* is a sequence)::

        data = ['A', 'B', 'C', ...]

        requirement = ['A', 'B', 'C', ...]  # <- Sequence of predicates

        datatest.validate(data, requirement)
    """
    # Setup traceback-hiding for pytest integration.
    __tracebackhide__ = lambda excinfo: excinfo.errisinstance(ValidationError)

    # Perform validation.
    invalid_info = _get_invalid_info(data, requirement)
    if invalid_info:
        default_msg, differences = invalid_info  # Unpack values.
        raise ValidationError(differences, msg or default_msg)
    return True
