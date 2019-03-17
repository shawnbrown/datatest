# -*- coding: utf-8 -*-
"""Validation and comparison handling."""
import sys
from ._compatibility.collections.abc import Iterable
from ._compatibility.collections.abc import Iterator
from ._compatibility.collections.abc import Mapping
from ._compatibility.collections.abc import Set
from ._compatibility.functools import partial
from .difference import BaseDifference
from ._normalize import normalize
from ._query.query import BaseElement
from . import requirements
from ._utils import IterItems
from ._utils import exhaustible
from ._utils import iterpeek
from ._utils import nonstringiter
from ._utils import _safesort_key

__all__ = [
    'validate',
    'valid',
    'ValidationError',
]


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


class ValidateType(object):
    """Raise a :exc:`ValidationError` if *data* does not satisfy
    *requirement* or pass without error if data is valid.

    This is a rich comparison object---the given *data* and
    *requirement* arguments can be mappings, iterables, or other
    objects. An optional *msg* string can be provided to describe
    the validation.

    .. _predicate-validation:

    **Predicate Validation:**

        When *requirement* is a callable, tuple, string, or
        non-iterable object, it is used to construct a
        :class:`Predicate` for testing elements in *data*:

        .. code-block:: python
            :emphasize-lines: 8

            from datatest import validate

            data = [2, 4, 6, 8]

            def iseven(x):
                return x % 2 == 0

            validate(data, iseven)  # <- callable used as predicate

        If the predicate returns False, then an :class:`Invalid` or
        :class:`Deviation` difference is generated. If the predicate
        returns a difference object, that object is used in place of
        a generated difference (see :ref:`difference-docs`). When the
        predicate returns any other truthy value, an element is
        considered valid.

    .. _set-validation:

    **Set Validation:**

        When *requirement* is a set, the elements in *data* are checked
        for membership in the set:

        .. code-block:: python
            :emphasize-lines: 7

            from datatest import validate

            data = ['a', 'a', 'b', 'b', 'c', 'c']

            required_set = {'a', 'b', 'c'}

            validate(data, required_set)  # <- tests for set membership

        If the elements in *data* do not match the required set, then
        :class:`Missing` and :class:`Extra` differences are generated.

    **Sequence Validation:**

        When *requirement* is an iterable type other than a set,
        mapping, tuple or string, then *data* is validated as a
        sequence of elements. Elements are checked for predicate
        matches against required objects of the same position (both
        *data* and *requirement* should yield values in a predictable
        order):

        .. code-block:: python
            :emphasize-lines: 7

            from datatest import validate

            data = ['A', 'B', 'C', ...]

            sequence = ['A', 'B', 'C', ...]

            validate(data, sequence)  # <- compare elements by position

        For details on predicate matching, see :class:`Predicate`.

    **Mapping Validation:**

        When *requirement* is a dictionary or other mapping, the values
        in *data* are checked against required objects of the same key
        (*data* must also be a mapping):

        .. code-block:: python
            :emphasize-lines: 7

            from datatest import validate

            data = {'A': 1, 'B': 2, 'C': ...}

            required_dict = {'A': 1, 'B': 2, 'C': ...}

            validate(data, required_dict)  # <- compares values

        If values do not satisfy the corresponding required object,
        then differences are generated according to each object type.
        If an object itself is a nested mapping, it is treated as a
        predicate object.

    **Requirement Object Validation:**

        When *requirement* is a subclass of :class:`BaseRequirement`,
        it is used to check data and generate differences directly.
    """
    def __call__(self, data, requirement, msg=None):
        # Setup traceback-hiding for pytest integration.
        __tracebackhide__ = lambda excinfo: excinfo.errisinstance(ValidationError)

        requirement_object = requirements.get_requirement(requirement)
        result = requirement_object(data)  # <- Apply requirement.

        if result:
            differences, description = result
            message = msg or description or 'does not satisfy requirement'
            raise ValidationError(differences, message)

    @staticmethod
    def _get_predicate_requirement(requirement, factory):
        """Return appropriate requirement object for explicit predicate
        validation. If *requirement* is a mapping or sequence, return
        RequiredMapping or RequiredSequence (using the given *factory*
        function) or else call *factory* and return RequiredPredicate
        directly.
        """
        requirement = normalize(requirement, lazy_evaluation=False)
        def wrapped_factory(obj):
            if (isinstance(obj, Iterable)
                    and not isinstance(obj, Set)
                    and not isinstance(obj, BaseElement)):
                return requirements.RequiredSequence(obj, factory)
            return factory(obj)

        if isinstance(requirement, (Mapping, IterItems)):
            return requirements.RequiredMapping(requirement, wrapped_factory)
        return wrapped_factory(requirement)

    def predicate(self, data, requirement, msg=None):
        """Use *requirement* to construct a :class:`Predicate` and
        check elements in *data* for matches (see :ref:`predicate
        validation <predicate-validation>` for more details).
        """
        __tracebackhide__ = lambda excinfo: excinfo.errisinstance(ValidationError)
        factory = requirements.RequiredPredicate
        requirement = self._get_predicate_requirement(requirement, factory)
        self(data, requirement, msg=msg)

    def approx(self, data, requirement, places=None, msg=None, delta=None):
        """Require that numeric values are approximately equal. The
        given *requirement* can be a single element or a mapping.

        Values compare as equal if their difference rounded to the
        given number of decimal places (default 7) equals zero, or
        if the difference between values is less than or equal to
        the given delta:

        .. code-block:: python
            :emphasize-lines: 7

            from datatest import validate

            data = {'A': 1.3125, 'B': 8.6875}

            requirement = {'A': 1.31, 'B': 8.69}

            validate.approx(data, requirement, places=2)

        It is appropriate to use :meth:`validate.approx` when checking
        for nominal values---where some deviation is considered an
        intrinsic feature of the data. But when deviations represent an
        undesired-but-acceptible variation, :meth:`allowed.deviation`
        would be more fitting.
        """
        __tracebackhide__ = lambda excinfo: excinfo.errisinstance(ValidationError)
        factory = partial(requirements.RequiredApprox, places=places, delta=delta)
        requirement = self._get_predicate_requirement(requirement, factory)
        self(data, requirement, msg=msg)

    def fuzzy(self, data, requirement, cutoff=0.6, msg=None):
        """Require that strings match with a similarity greater than
        or equal to *cutoff* (default ``0.6``).

        Similarity measures are determined using
        :py:meth:`SequenceMatcher.ratio()
        <difflib.SequenceMatcher.ratio>` from the Standard Library's
        :py:mod:`difflib` module. The values range from ``1.0``
        (exactly the same) to ``0.0`` (completely different).

        .. code-block:: python
            :emphasize-lines: 15

            from datatest import validate

            data = {
                'MO': 'Saint Louis',
                'NY': 'New York',  # <- does not meet cutoff
                'OH': 'Cincinatti',
            }

            requirement = {
                'MO': 'St. Louis',
                'NY': 'New York City',
                'OH': 'Cincinnati',
            }

            validate.fuzzy(data, requirement, cutoff=0.8)
        """
        __tracebackhide__ = lambda excinfo: excinfo.errisinstance(ValidationError)
        factory = partial(requirements.RequiredFuzzy, cutoff=cutoff)
        requirement = self._get_predicate_requirement(requirement, factory)
        self(data, requirement, msg=msg)

    def set(self, data, requirement, msg=None):
        """Check that the set of elements in *data* matches the set
        of elements in *requirement* (applies :ref:`set validation
        <set-validation>` using a *requirement* of any iterable type).
        """
        __tracebackhide__ = lambda excinfo: excinfo.errisinstance(ValidationError)

        requirement = normalize(requirement, lazy_evaluation=False, default_type=set)

        if isinstance(requirement, (Mapping, IterItems)):
            factory = requirements.RequiredSet
            requirement = requirements.RequiredMapping(requirement, factory)
        else:
            requirement = requirements.RequiredSet(requirement)

        self(data, requirement, msg=msg)

    def subset(self, data, requirement, msg=None):
        """Check that *requirement* is a subset of *data* (i.e., that
        all elements in *requirement* are also contained in *data*):

        .. code-block:: python
            :emphasize-lines: 7

            from datatest import validate

            data = ['A', 'B', 'C', 'D']

            requirement = {'A', 'B', 'C'}

            validate.subset(data, requirement)
        """
        __tracebackhide__ = lambda excinfo: excinfo.errisinstance(ValidationError)

        requirement = normalize(requirement, lazy_evaluation=False, default_type=set)

        if isinstance(requirement, (Mapping, IterItems)):
            factory = requirements.RequiredSubset
            requirement = requirements.RequiredMapping(requirement, factory)
        else:
            requirement = requirements.RequiredSubset(requirement)

        self(data, requirement, msg=msg)

    def superset(self, data, requirement, msg=None):
        """Check that *requirement* is a superset of *data* (i.e., that
        all elements in *data* are also contained in *requirement*):

        .. code-block:: python
            :emphasize-lines: 7

            from datatest import validate

            data = ['A', 'B', 'C']

            requirement = {'A', 'B', 'C', 'D'}

            validate.superset(data, requirement)
        """
        __tracebackhide__ = lambda excinfo: excinfo.errisinstance(ValidationError)

        requirement = normalize(requirement, lazy_evaluation=False, default_type=set)

        if isinstance(requirement, (Mapping, IterItems)):
            factory = requirements.RequiredSuperset
            requirement = requirements.RequiredMapping(requirement, factory)
        else:
            requirement = requirements.RequiredSuperset(requirement)

        self(data, requirement, msg=msg)

    def unique(self, data, msg=None):
        """Require that elements in *data* are unique:

        .. code-block:: python
            :emphasize-lines: 5

            from datatest import validate

            data = [1, 2, 3, ...]

            validate.unique(data)
        """
        __tracebackhide__ = lambda excinfo: excinfo.errisinstance(ValidationError)
        self(data, requirements.RequiredUnique(), msg=msg)

    def order(self, data, sequence, msg=None):
        """Check that elements in *data* match the order of elements
        in *sequence*:

        .. code-block:: python
            :emphasize-lines: 7

            from datatest import validate

            data = ['A', 'C', 'D', 'F', ...]

            required_order = ['A', 'B', 'C', 'D', ...]

            validate.order(data, required_order)

        If elements do not match the required order, :class:`Missing`
        and :class:`Extra` differences are raised. Each difference
        will contain a two-tuple whose first value is the index where
        the difference occurs in *data* and whose second value is the
        non-matching element itself.

        In the given example, *data* is missing ``'B'`` at index 1
        and contains an extra ``'F'`` at index 3:

        .. code-block:: none

                                        extra
                                          |
                                          v
                   data: ['A', 'C', 'D', 'F', ...]

            requirement: ['A', 'B', 'C', 'D', ...]
                                ^
                                |
                             missing

        The validation fails with the following error:

        .. code-block:: none

            ValidationError: does not match required order (2 differences): [
                Missing((1, 'B')),
                Extra((3, 'F')),
            ]

        Notice there are no differences for ``'C'`` and ``'D'``
        because their order matches the *requirement*---even though
        their index positions are different.
        """
        __tracebackhide__ = lambda excinfo: excinfo.errisinstance(ValidationError)

        requirement = normalize(sequence, lazy_evaluation=False, default_type=list)

        if isinstance(requirement, (Mapping, IterItems)):
            factory = requirements.RequiredOrder
            requirement = requirements.RequiredMapping(requirement, factory)
        else:
            requirement = requirements.RequiredOrder(requirement)

        self(data, requirement, msg=msg)

    def outliers(self, data, requirement=None, multiplier=2.2, msg=None,
                 rounding=True):
        """Check *data* for outliers using the Tukey
        fence/interquartile range method for outlier labeling.

        The Tukey fence method determines a range of values that
        elements in *data* are expected to fall within. When elements
        fall outside the expected range, they are considered outliers.
        The expected range can be broadened or narrowed by increasing
        or decreasing the *multiplier*.

        If *requirement* is given, it is used in place of *data* to
        calculate the expected range of values. Elements in *data* are
        then compared against this range. The *requirement* should be
        a collection of numbers or a mapping of collections.

        When *rounding* is True, the lower and upper bounds of the
        expected range are rounded to precise float representations.

        Checking a list of values:

        .. code-block:: python
            :emphasize-lines: 5

            from datatest import validate

            data = [12, 5, 8, 37, 5, 7, 15]  # <- 37 is an outlier

            validate.outliers(data)

        Checking a mapping of multiple lists:

        .. code-block:: python
            :emphasize-lines: 8

            from datatest import validate

            data = {
                'A': [12, 5, 8, 37, 5, 7, 15],  # <- 37 is an outlier
                'B': [83, 75, 78, 50, 76, 89],  # <- 50 is an outlier
            }

            validate.outliers(data)

        In "Exploratory Data Analysis" by Tukey (1977), a multiplier of
        1.5 was proposed for labeling outliers and 3.0 was proposed for
        labeling "far out" outliers. The default *multiplier* of ``2.2``
        is based on "Fine-Tuning Some Resistant Rules for Outlier
        Labeling" by Hoaglin and Iglewicz (1987).
        """
        __tracebackhide__ = lambda excinfo: excinfo.errisinstance(ValidationError)

        if requirement is None:
            requirement = data

        normalized = normalize(
            requirement,
            lazy_evaluation=False,
            default_type=list,
        )
        if requirement is data and nonstringiter(data) and exhaustible(data):
            data = normalized  # Use non-exhaustible version.

        if isinstance(normalized, (Mapping, IterItems)):
            factory = partial(requirements.RequiredOutliers, multiplier=multiplier, rounding=rounding)
            requirement = requirements.RequiredMapping(normalized, factory)
        else:
            requirement = requirements.RequiredOutliers(
                normalized,
                multiplier=multiplier,
                rounding=rounding,
            )

        self(data, requirement, msg=msg)


validate = ValidateType()  # Use as instance.


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
