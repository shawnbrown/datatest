"""Acceptance classes and functions."""

from __future__ import absolute_import
from __future__ import division

__all__ = [
    'accepted',
    'AcceptedDifferences',
    'AcceptedKeys',
    'AcceptedArgs',
    'AcceptedTolerance',
    'AcceptedPercent',
    'AcceptedCount',
    'AcceptedFuzzy',
]

import difflib
import inspect
from numbers import Number
from ._compatibility.builtins import *
from ._compatibility import abc
from ._compatibility.collections import defaultdict
from ._compatibility.collections.abc import Mapping
from ._compatibility import contextlib
from ._compatibility import itertools

from ._utils import BaseElement
from ._utils import exhaustible
from ._utils import nonstringiter
from ._vendor.predicate import get_matcher
from .validation import ValidationError
from .differences import (
    BaseDifference,
    Missing,
    Extra,
    Invalid,
)


__datatest = True  # Used to detect in-module stack frames (which are
                   # omitted from output).

class BaseAcceptance(abc.ABC):
    """Context manager base class to accept certain differences without
    triggering a test failure.
    """
    def __init__(self, msg=None):
        """Initialize object values."""
        self.msg = msg

    @property
    @abc.abstractmethod
    def scope(self):
        """Return a set of scope strings associated with the
        acceptance.
        """
        raise NotImplementedError

    # Scope precedence determines order of operations.
    # The currently recognized scopes are "element",
    # "group", and "whole".
    _precedence = {
        frozenset(['element']): 1,
        frozenset(['group', 'element']): 2,
        frozenset(['group']): 3,
        frozenset(['whole', 'element']): 4,
        frozenset(['whole', 'group', 'element']): 5,
        frozenset(['whole', 'group']): 6,
        frozenset(['whole']): 7,
    }

    @classmethod
    def _get_precedence(cls, acceptance):
        """Return numeric precedence for given acceptance object."""
        try:
            number = cls._precedence[frozenset(acceptance.scope)]
        except KeyError:
            import warnings
            message = 'unrecognized scope {0!r}'.format(acceptance.scope)
            warnings.warn(message.format(message), UserWarning)
            number = 0
        return number

    @abc.abstractmethod
    def __repr__(self):
        cls_name = self.__class__.__name__
        msg_part = 'msg={0!r}'.format(self.msg) if self.msg else ''
        return '{0}({1})'.format(cls_name, msg_part)

    #######################################
    # Hook methods for acceptance protocol.
    #######################################
    def start_collection(self):
        """Called first before any group or predicate checking."""

    def start_group(self, key):
        """Called before processing each group."""

    @abc.abstractmethod
    def call_predicate(self, item):
        """Call once for each item."""
        return False

    def end_group(self, key):
        """Called after processing each group."""

    def end_collection(self):
        """Called last after all items have been checked."""

    ##################################################
    # Methods and operators for union and intersection
    ##################################################
    def intersection(self, other):
        """Return a new acceptance that allows only those
        differences accepted by both the current acceptance
        and the given *other* acceptance.
        """
        return self.__and__(other)

    def __and__(self, other):
        if not isinstance(other, BaseAcceptance):
            return NotImplemented
        return IntersectedAcceptance(self, other)

    def union(self, other):
        """Return a new acceptance that allows any difference
        accepted by either the current acceptance or the given
        *other* acceptance.
        """
        return self.__or__(other)

    def __or__(self, other):
        if not isinstance(other, BaseAcceptance):
            return NotImplemented
        return UnionedAcceptance(self, other)

    ###############################################
    # Data handling methods for context management.
    ###############################################
    def _filterfalse(self, serialized):
        self.start_collection()

        def make_key(item):
            return item[0]
        grouped = itertools.groupby(serialized, key=make_key)

        for key, group in grouped:
            self.start_group(key)
            for item in group:
                if self.call_predicate(item):
                    continue
                yield item
            self.end_group(key)

        self.end_collection()

    @staticmethod
    def _serialized_items(iterable):
        if isinstance(iterable, Mapping):
            for key in iterable:
                value = iterable[key]
                if isinstance(value, (BaseElement, Exception)):
                    yield (key, value)
                else:
                    for subvalue in value:
                        yield (key, subvalue)
        else:
            for value in iterable:
                yield (None, value)

    @staticmethod
    def _deserialized_items(iterable):
        def make_key(item):
            return item[0]

        grouped = itertools.groupby(iterable, key=make_key)

        def make_value(group):
            value = [item[1] for item in group]
            if len(value) == 1:
                return value.pop()
            return value

        return dict((key, make_value(group)) for key, group in grouped)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type and not issubclass(exc_type, ValidationError):
            raise exc_value

        differences = getattr(exc_value, 'differences', [])
        is_not_mapping = not isinstance(differences, Mapping)

        stream = self._serialized_items(differences)
        stream = self._filterfalse(stream)
        differences = self._deserialized_items(stream)

        if not differences:
            return True  # <- EXIT!

        __tracebackhide__ = True  # Set pytest flag to hide traceback.

        if is_not_mapping:
            assert len(differences) == 1
            differences = differences.popitem()[1]
            if isinstance(differences, BaseDifference):
                differences = [differences]

        # Extend description with acceptance message.
        if self.msg:
            if exc_value.description:
                message = '{0}: {1}'.format(self.msg, exc_value.description)
            else:
                message = self.msg
        else:
            message = exc_value.description

        # Build new ValidationError with remaining differences.
        exc = ValidationError(differences, message)

        # Re-raised error inherits truncation behavior of original.
        exc._should_truncate = exc_value._should_truncate
        exc._truncation_notice = exc_value._truncation_notice

        exc.__cause__ = None  # <- Suppress context using verbose
        raise exc             #    alternative to support older Python
                              #    versions--see PEP 415 (same as
                              #    effect as "raise ... from None").


class CombinedAcceptance(BaseAcceptance):
    """Base class for combining acceptances using Boolean composition."""
    def __init__(self, left, right, msg=None):
        self.left = left
        self.right = right
        self.msg = msg

    @property
    def scope(self):
        """Return a combined set scope strings."""
        return self.left.scope | self.right.scope

    def start_collection(self):
        self.left.start_collection()
        self.right.start_collection()

    def start_group(self, key):
        self.left.start_group(key)
        self.right.start_group(key)

    def end_group(self, key):
        self.left.end_group(key)
        self.right.end_group(key)

    def end_collection(self):
        self.left.end_collection()
        self.right.end_collection()


class IntersectedAcceptance(CombinedAcceptance):
    """Base class to accept only those differences allowed by both
    given acceptances.
    """
    def __repr__(self):
        return '({0!r} & {1!r})'.format(self.left, self.right)

    def call_predicate(self, item):
        first, second = self.left, self.right

        # Acceptances with a larger precedence number must go on the
        # right-hand side to ensure proper short-circuit behavior.
        if self._get_precedence(first) > self._get_precedence(second):
            first, second = second, first

        # The acceptance protocol is stateful so it's important to use
        # short-circuit evaluation to avoid calling the second acceptance
        # unnecessarily. If `first` returns False, then `second` should
        # not be called.
        return first.call_predicate(item) and second.call_predicate(item)


class UnionedAcceptance(CombinedAcceptance):
    """Base class to accept differences allowed by either given
    acceptance.
    """
    def __repr__(self):
        return '({0!r} | {1!r})'.format(self.left, self.right)

    def call_predicate(self, item):
        first, second = self.left, self.right

        # Acceptances with a larger precedence number must go on the
        # right-hand side to ensure proper short-circuit behavior.
        if self._get_precedence(first) > self._get_precedence(second):
            first, second = second, first

        # The acceptance protocol is stateful so it's important to use
        # short-circuit evaluation to avoid calling the second acceptance
        # unnecessarily. If `first` returns True, then `second` should
        # not be called.
        return first.call_predicate(item) or second.call_predicate(item)


class AcceptedDifferences(BaseAcceptance):
    """Accepts differences that match *obj* without triggering a test
    failure. The given *obj* can be a difference class, a difference
    instance, or a collection of instances.

    When *obj* is a difference class, differences are accepted if they
    are instances of the class. When *obj* is a difference instance or
    collection of instances, then differences are accepted if they
    compare as equal to one of the accepted instances.

    If given, the *scope* can be ``'element'``, ``'group'``, or
    ``'whole'``. An element-wise scope will accept all differences
    that have a match in *obj*. A group-wise scope will accept one
    difference per match in *obj* per group. A whole-error scope will
    accept one difference per match in *obj* over the ValidationError
    as a whole.

    If unspecified, *scope* will default to ``'element'`` if *obj* is
    a single element and ``'group'`` if *obj* is a collection of
    elements. If *obj* is a mapping, the scope is limited to the group
    of differences associated with a given key (which effectively
    treats whole-error scopes the same as group-wise scopes).
    """
    def __init__(self, obj, msg=None, scope=None):
        if scope not in (None, 'element', 'group', 'whole'):
            message = "scope may be 'element', 'group', or 'whole', got {0}"
            raise ValueError(message.format(scope))

        super(AcceptedDifferences, self).__init__(msg)
        self._scope = scope

        normalize = self._normalize_differences
        if isinstance(obj, Mapping):
            if hasattr(obj, 'iteritems'):
                items = obj.iteritems()
            else:
                items = obj.items()
            self._obj = dict((k, normalize(v)) for k, v in items)
        else:
            self._obj = normalize(obj)

        # Working attributes for checking groups of differences.
        self._current_scope = None
        self._current_allowance = None
        self._current_check = None

    @staticmethod
    def _normalize_differences(obj):
        """Raise a TypeError if *obj* is anything other than a
        difference type, a difference instance, or a collection
        of difference instances. If *obj* is verified, pass without
        error (returns implicit None).
        """
        if not nonstringiter(obj):
            if isinstance(obj, type):
                if not issubclass(obj, BaseDifference):
                    msg = 'type must be subclass of BaseDifference, got {0}'
                    raise TypeError(msg.format(obj.__name__))
            elif not isinstance(obj, BaseDifference):
                msg = 'instance must be difference, got {0!r} ({1})'
                raise TypeError(msg.format(obj, obj.__class__.__name__))
        elif isinstance(obj, Mapping):
            msg = 'expected difference or non-mapping of differences, got mapping {0!r}'
            raise TypeError(msg.format(obj))
        else:
            if nonstringiter(obj) and \
                    (exhaustible(obj) or not hasattr(obj, 'remove')):
                obj = list(obj)  # <- Normalize *obj* container.

            for val in obj:
                if not isinstance(val, BaseDifference):
                    msg = 'must contain difference instances, got {0!r} ({1})'
                    raise TypeError(msg.format(val, val.__class__.__name__))
        return obj

    @property
    def scope(self):
        """Return scope as a frozenset."""
        scope = self._scope

        if not scope:
            if nonstringiter(self._obj):
                scope = 'group'
            else:
                scope = 'element'

        return frozenset([scope])

    def start_group(self, key):
        """Called before processing each group."""
        # Get current allowance object.
        obj = self._obj
        if isinstance(obj, Mapping):
            current_allowance = obj.get(key, [])
        elif nonstringiter(obj):
            if self._scope == 'whole':
                current_allowance = obj  # Use a single persistent object.
            else:
                current_allowance = list(obj)  # Make a copy for each group.
        else:
            current_allowance = obj

        # Get current scope and check function.
        if isinstance(current_allowance, type):
            default_scope = 'element'
            current_allowance = [current_allowance]
            # Will check for matching differences using isinstance().
            current_check = \
                lambda x: current_allowance and isinstance(x, current_allowance[0])
        else:
            if nonstringiter(current_allowance):
                default_scope = 'group'
                if not hasattr(current_allowance, 'remove'):
                    current_allowance = list(current_allowance)
            else:
                default_scope = 'element'
                current_allowance = [current_allowance]
            # Will check for matching differences using `in` operator.
            current_check = lambda x: x in current_allowance

        # Set "scope", "allowance", and "check" function for current group.
        self._current_scope = self._scope or default_scope
        self._current_allowance = current_allowance
        self._current_check = current_check

    def call_predicate(self, item):
        """Call once for each element."""
        _, diff = item

        if self._current_check(diff):
            if self._current_scope != 'element':
                self._current_allowance.remove(diff)
            return True
        return False

    def __repr__(self):
        cls_name = self.__class__.__name__

        if isinstance(self._obj, type):
            obj_part = self._obj.__name__
        else:
            obj_part = repr(self._obj)

        if self.msg:
            msg_part = ', msg={0!r}'.format(self.msg)
        else:
            msg_part = ''

        if self._scope:
            scope_part = ', scope={0!r}'.format(self._scope)
        else:
            scope_part = ''

        return '{0}({1}{2}{3})'.format(cls_name, obj_part, msg_part, scope_part)


class AcceptedKeys(BaseAcceptance):
    """Accepts differences whose associated keys satisfy the given
    *predicate* (see :ref:`predicate-docs` for details).
    """
    def __init__(self, predicate, msg=None):
        super(AcceptedKeys, self).__init__(msg)

        matcher = get_matcher(predicate)
        def function(x):
            return matcher == x
        function.__name__ = repr(matcher)

        self.function = function

    @property
    def scope(self):
        """Return scope as a frozenset."""
        return frozenset(['element'])

    def __repr__(self):
        cls_name = self.__class__.__name__
        msg_part = ', msg={0!r}'.format(self.msg) if self.msg else ''
        obj_name = getattr(self.function, '__name__', repr(self.function))
        return '{0}({1}{2})'.format(cls_name, obj_name, msg_part)

    def call_predicate(self, item):
        key = item[0]
        return self.function(key)


class AcceptedArgs(BaseAcceptance):
    """Accepts differences whose 'args' satisfy the given *predicate*
    (see :ref:`predicate-docs` for details).
    """
    def __init__(self, predicate, msg=None):
        super(AcceptedArgs, self).__init__(msg)

        matcher = get_matcher(predicate)
        def function(x):
            return matcher == x
        function.__name__ = repr(matcher)

        self.function = function

    @property
    def scope(self):
        """Return scope as a frozenset."""
        return frozenset(['element'])

    def __repr__(self):
        cls_name = self.__class__.__name__
        msg_part = ', msg={0!r}'.format(self.msg) if self.msg else ''
        obj_name = getattr(self.function, '__name__', repr(self.function))
        return '{0}({1}{2})'.format(cls_name, obj_name, msg_part)

    def call_predicate(self, item):
        args = item[1].args
        if len(args) == 1:
            args = args[0]  # Unwrap single-item tuple.
        return self.function(args)


def _normalize_deviation_args(lower, upper, msg):
    """Normalize deviation acceptance arguments to support both
    "tolerance" and "lower, upper" signatures. This helper function
    is intended for internal use.
    """
    if isinstance(upper, str) and msg is None:
        upper, msg = None, msg  # Shift values if using "tolerance" syntax.

    if upper == None:
        tolerance = lower
        if tolerance != abs(tolerance):
            raise ValueError('tolerance should not be negative, '
                             'for full control of lower and upper '
                             'bounds, use "lower, upper" syntax')
        lower, upper = -tolerance, tolerance

    if lower > upper:
        raise ValueError('lower must not be greater than upper, got '
                         '{0} (lower) and {1} (upper)'.format(lower, upper))
    return (lower, upper, msg)


class AcceptedTolerance(BaseAcceptance):
    """AcceptedTolerance(tolerance, /, msg=None)
    AcceptedTolerance(lower, upper, msg=None)

    Context manager that accepts quantative differences within a
    given tolerance without triggering a test failure.

    See documentation for full details.
    """
    def __init__(self, lower, upper=None, msg=None):
        lower, upper, msg = _normalize_deviation_args(lower, upper, msg)
        self.lower = lower
        self.upper = upper
        super(AcceptedTolerance, self).__init__(msg)

    @property
    def scope(self):
        """Return scope as a frozenset."""
        return frozenset(['element'])

    def __repr__(self):
        cls_name = self.__class__.__name__

        if self.msg:
            msg_repr = ', msg={0!r}'.format(self.msg)
        else:
            msg_repr = ''

        if -self.lower == self.upper:
            repr_string = '{0}({1!r}{2})'.format(
                cls_name,
                self.upper,
                msg_repr,
            )
        else:
            repr_string = '{0}(lower={1!r}, upper={2!r}{3})'.format(
                cls_name,
                self.lower,
                self.upper,
                msg_repr,
            )
        return repr_string

    @staticmethod
    def _get_deviation_expected(diff):
        """Takes a difference object and returns a tuple containing its
        *deviation* and *expected* values or raises a TypeError.
        """
        try:
            # If diff is Deviation-like, get `deviation` and `expected`.
            deviation = diff.deviation
            expected = diff.expected
        except AttributeError:
            # Else, try to derive `deviation` and `expected`.
            args = diff.args
            len_args = len(args)
            if (isinstance(diff, Missing)
                    and len_args == 1
                    and isinstance(args[0], Number)):
                deviation = -args[0]
                expected = args[0]
            elif (isinstance(diff, (Extra, Invalid))
                    and len_args == 1
                    and isinstance(args[0], Number)):
                deviation = args[0]
                expected = 0
            elif isinstance(diff, Invalid) and len_args == 2:
                try:
                    expected = args[1]
                    deviation = args[0] - expected
                except TypeError:
                    expected = args[1] or 0
                    deviation = (args[0] or 0) - expected
            else:
                raise TypeError

        return deviation or 0, expected or 0

    def call_predicate(self, item):
        _, diff = item  # Unpack item (discarding key).
        try:
            deviation, _ = self._get_deviation_expected(diff)
        except TypeError:
            return False  # <- EXIT!
        return self.lower <= deviation <= self.upper

with contextlib.suppress(AttributeError):  # inspect.Signature() is new in 3.3
    AcceptedTolerance.__init__.__signature__ = inspect.Signature([
        inspect.Parameter('self', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('tolerance', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('msg', inspect.Parameter.POSITIONAL_OR_KEYWORD, default=None),
    ])


class AcceptedPercent(AcceptedTolerance):
    """AcceptedPercent(tolerance, /, msg=None)
    AcceptedPercent(lower, upper, msg=None)

    Context manager that accepts percentages of error within a
    given tolerance without triggering a test failure:

    See documentation for full details.
    """
    def call_predicate(self, item):
        _, diff = item  # Unpack item (discarding key).
        try:
            deviation, expected = self._get_deviation_expected(diff)
        except TypeError:
            return False  # <- EXIT!

        if not expected:
            return not deviation  # <- EXIT!
        percent_error = deviation / expected  # Make percent error.
        return self.lower <= percent_error <= self.upper

with contextlib.suppress(AttributeError):  # inspect.Signature() is new in 3.3
    AcceptedPercent.__init__.__signature__ = inspect.Signature([
        inspect.Parameter('self', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('tolerance', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('msg', inspect.Parameter.POSITIONAL_OR_KEYWORD, default=None),
    ])


class AcceptedFuzzy(BaseAcceptance):
    """Context manager that accepts Invalid string differences without
    triggering a test failure if the actual value and the expected
    value match with a similarity greater than or equal to *cutoff*
    (default 0.6).

    Similarity measures are determined using the ratio() method of
    the :py:class:`difflib.SequenceMatcher` class. The values range
    from 0.0 (completely different) to 1.0 (exactly the same):
    """
    def __init__(self, cutoff=0.6, msg=None):
        self.cutoff = cutoff
        super(AcceptedFuzzy, self).__init__(msg)

    @property
    def scope(self):
        """Return scope as a frozenset."""
        return frozenset(['element'])

    def __repr__(self):
        cls_name = self.__class__.__name__
        msg_part = ', msg={0!r}'.format(self.msg) if self.msg else ''
        return '{0}(cutoff={1!r}{2})'.format(cls_name, self.cutoff, msg_part)

    def call_predicate(self, item):
        diff = item[1]

        try:
            a = diff.invalid
            b = diff.expected
        except AttributeError:
            return False  # <- EXIT!

        try:
            matcher = difflib.SequenceMatcher(a=a, b=b)
            similarity = matcher.ratio()
        except TypeError:
            return False  # <- EXIT!

        return similarity >= self.cutoff


class AcceptedCount(BaseAcceptance):
    """Accepted up to a given *number* of differences without
    triggering a test failure.
    """
    def __init__(self, number, msg=None, scope=None):
        if not isinstance(number, Number):
            err_msg = 'number must be a numeric type, got {0}'
            raise TypeError(err_msg.format(number.__class__.__name__))

        if scope not in (None, 'group', 'whole'):
            if scope == 'element':
                raise ValueError("count does not accept 'element' scope")
            message = "scope may be 'group' or 'whole', got {0}"
            raise ValueError(message.format(scope))

        self.number = number
        self.msg = msg
        self._scope = scope
        self._count = None  # Properties to hold working values
        self._limit = None  # during acceptance checking.

    @property
    def scope(self):
        """Return scope as a frozenset."""
        return frozenset([self._scope or 'whole'])

    def __repr__(self):
        cls_name = self.__class__.__name__
        msg_part = ', msg={0!r}'.format(self.msg) if self.msg else ''
        scope_part = ', scope={0!r}'.format(self._scope) if self._scope else ''
        return '{0}({1!r}{2}{3})'.format(cls_name, self.number, msg_part, scope_part)

    def start_collection(self):
        self._limit = self.number
        self._count = 0

    def start_group(self, key):
        if self._scope == 'group':
            self._limit = self.number
            self._count = 0

    def call_predicate(self, item):
        self._count += 1
        return self._count <= self._limit


##########################################
# Factory object for pytest-style testing.
##########################################

class AcceptedFactoryType(object):
    """Returns a context manager that accepts differences that match
    *obj* without triggering a test failure. The given *obj* can be a
    difference class, a difference instance, or a collection of
    instances.

    When *obj* is a difference class, differences are accepted if they
    are instances of the class. When *obj* is a difference instance or
    collection of instances, then differences are accepted if they
    compare as equal to one of the accepted instances.

    If given, the *scope* can be ``'element'``, ``'group'``, or
    ``'whole'``. An element-wise scope will accept all differences
    that have a match in *obj*. A group-wise scope will accept one
    difference per match in *obj* per group. A whole-error scope will
    accept one difference per match in *obj* over the ValidationError
    as a whole.

    If unspecified, *scope* will default to ``'element'`` if *obj* is
    a single element and ``'group'`` if *obj* is a collection of
    elements. If *obj* is a mapping, the scope is limited to the group
    of differences associated with a given key (which effectively
    treats whole-error scopes the same as group-wise scopes).

    **Accepted Type:**

        When *obj* is a class (:class:`Missing`, :class:`Extra`,
        :class:`Deviation`, :class:`Invalid`, etc.), differences
        are accepted if they are instances of the class.

        The following example accepts all instances of the ``Missing``
        class:

        .. code-block:: python
            :emphasize-lines: 7

            from datatest import validate, accepted, Missing

            data = ['A', 'B']

            requirement = {'A', 'B', 'C'}

            with accepted(Missing):
                validate(data, requirement)

        Without this acceptance, the validation would have failed with
        the following error:

        .. code-block:: none

            ValidationError: does not satisfy set membership (1 difference): [
                Missing('C'),
            ]

    **Accepted Difference:**

        When *obj* is an instance, differences are accepted if
        they match the instance exactly.

        The following example accepts all differences that match
        ``Extra('D')``:

        .. code-block:: python
            :emphasize-lines: 7

            from datatest import validate, accepted, Extra

            data = ['A', 'B', 'C', 'D']

            requirement = {'A', 'B', 'C'}

            with accepted(Extra('D')):
                validate(data, requirement)

        Without this acceptance, the validation would have failed
        with the following error:

        .. code-block:: none

            ValidationError: does not satisfy set membership (1 difference): [
                Extra('D'),
            ]

    **Accepted Collection:**

        When *obj* is a collection of difference instances, then an
        error's differences are accepted if they match an instance in
        the given collection:

        .. code-block:: python
            :emphasize-lines: 7-10

            from datatest import validate, accepted, Missing, Extra

            data = ['x', 'y', 'q']

            requirement = {'x', 'y', 'z'}

            known_issues = accepted([
                Extra('q'),
                Missing('z'),
            ])

            with known_issues:
                validate(data, requirement)

        A dictionary of acceptances can accept groups of differences
        by matching key:

        .. code-block:: python
            :emphasize-lines: 10-13

            from datatest import validate, accepted, Missing, Extra

            data = {
                'A': ['x', 'y', 'q'],
                'B': ['x', 'y'],
            }

            requirement = {'x', 'y', 'z'}

            known_issues = accepted({
                'A': [Extra('q'), Missing('z')],
                'B': [Missing('z')],
            })

            with known_issues:
                validate(data, requirement)
    """
    def __call__(self, obj, msg=None, scope=None):
        return AcceptedDifferences(obj, msg=msg, scope=scope)

    def keys(self, predicate, msg=None):
        """Returns a context manager that accepts differences whose
        associated keys satisfy the given *predicate* (see
        :ref:`predicate-docs` for details).

        The following example accepts differences associated with the
        key ``'B'``:

        .. code-block:: python
            :emphasize-lines: 7

            from datatest import validate, accepted

            data = {'A': 'x', 'B': 'y'}

            requirement = 'x'

            with accepted.keys('B'):
                validate(data, requirement)

        Without this acceptance, the validation would have failed with
        the following error:

        .. code-block:: none

            ValidationError: does not satisfy 'x' (1 difference): {
                'B': Invalid('y'),
            }
        """
        return AcceptedKeys(predicate, msg)

    def args(self, predicate, msg=None):
        """Returns a context manager that accepts differences whose
        :attr:`args <BaseDifference.args>` satisfy the given
        *predicate* (see :ref:`predicate-docs` for details).

        The example below accepts differences that contain the value
        ``'y'``:

        .. code-block:: python
            :emphasize-lines: 7

            from datatest import validate, accepted

            data = {'A': 'x', 'B': 'y'}

            requirement = 'x'

            with accepted.args('y'):
                validate(data, requirement)

        Without this acceptance, the validation would have failed with
        the following error:

        .. code-block:: none

            ValidationError: does not satisfy 'x' (1 difference): {
                'B': Invalid('y'),
            }
        """
        return AcceptedArgs(predicate, msg)

    def tolerance(self, lower, upper=None, msg=None):
        """accepted.tolerance(tolerance, /, msg=None)
        accepted.tolerance(lower, upper, msg=None)

        Returns a context manager that accepts quantative differences
        within a given tolerance without triggering a test failure.

        See documentation for full details.
        """
        return AcceptedTolerance(lower, upper=upper, msg=msg)

    def percent(self, lower, upper=None, msg=None):
        """accepted.percent(tolerance, /, msg=None)
        accepted.percent(lower, upper, msg=None)

        Returns a context manager that accepts percentages of error
        within a given tolerance without triggering a test failure:

        See documentation for full details.
        """
        return AcceptedPercent(lower, upper, msg)

    def fuzzy(self, cutoff=0.6, msg=None):
        """Returns a context manager that accepts invalid strings
        that match their expected value with a similarity greater
        than or equal to *cutoff* (default 0.6). Similarity measures
        are determined using :py:meth:`SequenceMatcher.ratio()
        <difflib.SequenceMatcher.ratio>` from the Standard Library's
        :py:mod:`difflib` module. The values range from ``1.0``
        (exactly the same) to ``0.0`` (completely different).

        The following example accepts string differences that match
        with a ratio of ``0.6`` or greater:

        .. code-block:: python
            :emphasize-lines: 7

            from datatest import validate, accepted

            data = {'A': 'aax', 'B': 'bbx'}

            requirement = {'A': 'aaa', 'B': 'bbb'}

            with accepted.fuzzy(cutoff=0.6):
                validate(data, requirement)

        Without this acceptance, the validation would have failed with
        the following error:

        .. code-block:: none

            ValidationError: does not satisfy mapping requirements (2 differences): {
                'A': Invalid('aax', expected='aaa'),
                'B': Invalid('bbx', expected='bbb'),
            }
        """
        return AcceptedFuzzy(cutoff=cutoff, msg=msg)

    def count(self, number, msg=None, scope=None):
        """Returns a context manager that accepts up to a given
        *number* of differences without triggering a test failure. If
        the count of differences exceeds the given *number*, the test
        case will fail with a :class:`ValidationError` containing the
        remaining differences.

        The following example accepts up to ``2`` differences:

        .. code-block:: python
            :emphasize-lines: 7

            from datatest import validate, accepted

            data = ['A', 'B', 'A', 'C']

            requirement = 'A'

            with accepted.count(2):
                validate(data, requirement)

        Without this acceptance, the validation would have failed with
        the following error:

        .. code-block:: none

            ValidationError: does not satisfy 'A' (2 differences): [
                Invalid('B'),
                Invalid('C'),
            ]
        """
        return AcceptedCount(number, msg=msg, scope=scope)

    def __repr__(self):
        default_repr = super(AcceptedFactoryType, self).__repr__()
        name_start = default_repr.index(self.__class__.__name__)
        no_module_prefix = default_repr[name_start:]  # Slice-off module.
        return '<' + no_module_prefix


with contextlib.suppress(AttributeError):  # inspect.Signature() is new in 3.3
    AcceptedFactoryType.tolerance.__signature__ = inspect.Signature([
        inspect.Parameter('self', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('tolerance', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('msg', inspect.Parameter.POSITIONAL_OR_KEYWORD, default=None),
        inspect.Parameter('percent', inspect.Parameter.KEYWORD_ONLY, default=False),
    ])

    AcceptedFactoryType.percent.__signature__ = inspect.Signature([
        inspect.Parameter('self', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('tolerance', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('msg', inspect.Parameter.POSITIONAL_OR_KEYWORD, default=None),
        inspect.Parameter('percent', inspect.Parameter.KEYWORD_ONLY, default=False),
    ])


accepted = AcceptedFactoryType()  # Use as instance.
