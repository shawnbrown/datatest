"""Validation and comparison handling."""
import sys
from ._compatibility.collections.abc import Iterable
from ._compatibility.collections.abc import Iterator
from ._compatibility.collections.abc import Mapping
from ._required import get_requirement
from ._required import BaseRequirement
from ._utils import IterItems
from ._utils import exhaustible
from ._utils import iterpeek
from ._utils import nonstringiter
from ._utils import _safesort_key
from ._query.query import (
    BaseElement,
    Query,
    Result,
)
from .difference import (
    BaseDifference,
    _make_difference,
    NOTFOUND,
)


__all__ = [
    'validate',
    'valid',
    'ValidationError',
]


def _normalize_data(data):
    if isinstance(data, Query):
        return data.execute()  # <- EXIT! (Returns Result for lazy evaluation.)

    pandas = sys.modules.get('pandas', None)
    if pandas:
        is_series = isinstance(data, pandas.Series)
        is_dataframe = isinstance(data, pandas.DataFrame)

        if (is_series or is_dataframe) and not data.index.is_unique:
            cls_name = data.__class__.__name__
            raise ValueError(('{0} index contains duplicates, must '
                              'be unique').format(cls_name))

        if is_series:
            return IterItems(data.iteritems())  # <- EXIT!

        if is_dataframe:
            gen = ((x[0], x[1:]) for x in data.itertuples())
            if len(data.columns) == 1:
                gen = ((k, v[0]) for k, v in gen)  # Unwrap if 1-tuple.
            return IterItems(gen)  # <- EXIT!

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


# THINK ABOUT MOVING THE FOLLOWING CODE DIRECTLY INTO
# THE required() FUNCTION'S AUTO-DETECTION BEHAVIOR.
def _normalize_requirement(requirement):
    if isinstance(requirement, BaseRequirement):
        return requirement

    requirement = _normalize_data(requirement)

    if isinstance(requirement, Result):
        return requirement.fetch()  # <- Eagerly evaluate.

    if isinstance(requirement, IterItems):
        return dict(requirement)

    if isinstance(requirement, Iterable) and exhaustible(requirement):
        cls_name = requirement.__class__.__name__
        raise TypeError(("exhaustible type '{0}' cannot be used "
                         "as a requirement").format(cls_name))

    return requirement


class ValidationError(AssertionError):
    """This exception is raised when data validation fails."""

    __module__ = 'datatest'

    def __init__(self, differences, description=None):
        if isinstance(differences, BaseDifference):
            differences = [differences]
        elif not nonstringiter(differences):
            msg = 'expected an iterable or mapping of differences, got {0}'
            raise TypeError(msg.format(differences.__class__.__name__))

        # Convert dictionary update sequences to dict.
        if not isinstance(differences, Mapping):
            first_item, differences = iterpeek(differences)
            if not isinstance(first_item, BaseDifference):
                try:
                    differences = dict(differences)
                except (TypeError, ValueError) as err:
                    msg = (
                        'expected differences or valid dictionary '
                        'update sequences, found {0}: {1!r}'
                    ).format(first_item.__class__.__name__, first_item)
                    err_cls = err.__class__
                    init_err = err_cls(msg)
                    init_err.__cause__ = getattr(err, '__cause__', None)
                    raise init_err

        # Eagerly evaluate lazy-iterables.
        if isinstance(differences, Mapping):
            for k, v in IterItems(differences):
                if nonstringiter(v) and exhaustible(v):
                    differences[k] = list(v)
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


def validate(data, requirement, msg=None):
    """Raise a :exc:`ValidationError` if *data* does not satisfy
    *requirement* or pass without error if data is valid.

    This is a rich comparison function---the given *data* and
    *requirement* arguments can be mappings, iterables, or other
    objects. An optional *msg* string can be provided to describe
    the validation.

    Required Predicate:
        When *requirement* is a function, tuple, string, or
        non-iterable object, it is used to construct a
        :class:`Predicate` for testing elements in *data*:

        .. code-block:: python
            :emphasize-lines: 5-6

            from datatest import validate

            data = [2, 4, 6, 8]

            def iseven(x):  # <- Used as predicate
                return x % 2 == 0

            validate(data, iseven)

        If the predicate returns False, an :class:`Invalid` or
        :class:`Deviation` difference is generated. If the predicate
        returns a difference object, the difference is used as-is (see
        :ref:`difference-docs`). When the predicate returns any other
        truthy value, an element is considered valid.

    **Required Set:**
        When *requirement* is a set, the elements in *data* are checked
        for membership in the set:

        .. code-block:: python
            :emphasize-lines: 5

            from datatest import validate

            data = ['a', 'a', 'b', 'b', 'c', 'c']

            required_set = {'a', 'b', 'c'}

            validate(data, required_set)

        If the elements in *data* do not match the required set, then
        :class:`Missing` and :class:`Extra` differences are generated.

    **Required Order:**
        When *requirement* is a non-tuple, non-string sequence, the
        *data* is checked for element order:

        .. code-block:: python
            :emphasize-lines: 5

            from datatest import validate

            data = ['A', 'B', 'C', ...]

            required_order = ['A', 'B', 'C', ...]  # <- Sequence of elements

            validate(data, required_order)

        If elements do not match the required order, :class:`Missing`
        and :class:`Extra` differences are returned. Each difference
        will contain a two-tuple whose first item is the slice-index
        where the difference starts (in the data under test) and whose
        second item is the non-matching value itself.

    **Required Mapping:**
        When *requirement* is a dictionary or other mapping, the values
        in *data* are checked against required objects of the same key
        (*data* must also be a mapping):

        .. code-block:: python
            :emphasize-lines: 5

            from datatest import validate

            data = {'A': 1, 'B': 2, 'C': ...}

            required_dict = {'A': 1, 'B': 2, 'C': ...}  # <- Mapping object

            datatest.validate(data, required_dict)

        If values do not satisfy the corresponding required object,
        then differences are generated according to each object type.
        If an object itself is a nested mapping, it is treated as a
        predicate object.

    **Other Requirement:**
        When *requirement* is a subclass of :class:`BaseRequirement`,
        it performs all checks and difference generation directly.

    .. note::
        The :func:`validate` function will either raise an exception
        or pass without errors. To get an explicit True/False return
        value, use the :func:`valid` function instead.
    """
    # Setup traceback-hiding for pytest integration.
    __tracebackhide__ = lambda excinfo: excinfo.errisinstance(ValidationError)

    data = _normalize_data(data)
    requirement = _normalize_requirement(requirement)

    requirement_object = get_requirement(requirement)
    result = requirement_object(data)  # <- Apply requirement.

    if result:
        differences, description = result
        message = msg or description or 'does not satisfy requirement'
        raise ValidationError(differences, message)


def valid(data, requirement):
    """Return True if *data* satisfies *requirement* else return False.

    See :func:`validate` for supported *data* and *requirement* values
    and detailed validation behavior.
    """
    try:
        validate(data, requirement)
    except ValidationError:
        return False
    return True
