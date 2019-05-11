# -*- coding: utf-8 -*-
from __future__ import division
import difflib
import inspect
from math import isnan
from numbers import Number
from ._compatibility.builtins import *
from ._compatibility import abc
from ._compatibility.collections import defaultdict
from ._compatibility.collections.abc import Mapping
from ._compatibility import contextlib
from ._compatibility import functools
from ._compatibility import itertools

from ._utils import exhaustible
from ._utils import nonstringiter
from ._predicate import MatcherBase
from ._predicate import get_matcher
from ._utils import _get_arg_lengths
from ._utils import _expects_multiple_params
from ._utils import _make_decimal
from ._utils import string_types
from ._query.query import BaseElement

from .validation import ValidationError
from .difference import BaseDifference
from .difference import Missing
from .difference import Extra
from .difference import Invalid
from .difference import Deviation


__datatest = True  # Used to detect in-module stack frames (which are
                   # omitted from output).


__all__ = [
    'accepted',
    'AcceptedMissing',
    'AcceptedExtra',
    'AcceptedInvalid',
    'AcceptedKeys',
    'AcceptedArgs',
    'AcceptedDeviation',
    'AcceptedPercent',
    'AcceptedSpecific',
    'AcceptedLimit',
    'AcceptedFuzzy',
    'allowed',  # <- Deprecated API.
]


class BaseAcceptance(abc.ABC):
    """Context manager base class to accept certain differences without
    triggering a test failure.
    """
    def __init__(self, msg=None):
        """Initialize object values."""
        self.msg = msg
        self.priority = getattr(self, 'priority', 100)  # Use existing priority
                                                        # if already defined.
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
        self.priority = max(left.priority, right.priority)

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
        if first.priority > second.priority:
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
        if first.priority > second.priority:
            first, second = second, first

        # The acceptance protocol is stateful so it's important to use
        # short-circuit evaluation to avoid calling the second acceptance
        # unnecessarily. If `first` returns True, then `second` should
        # not be called.
        return first.call_predicate(item) or second.call_predicate(item)


class AcceptedMissing(BaseAcceptance):
    """Accepts :class:`Missing` values without triggering a test
    failure.
    """
    def __repr__(self):
        return super(AcceptedMissing, self).__repr__()

    def call_predicate(self, item):
        return isinstance(item[1], Missing)


class AcceptedExtra(BaseAcceptance):
    """Accepts :class:`Extra` values without triggering a test failure."""
    def __repr__(self):
        return super(AcceptedExtra, self).__repr__()

    def call_predicate(self, item):
        return isinstance(item[1], Extra)


class AcceptedInvalid(BaseAcceptance):
    """Accepts :class:`Invalid` values without triggering a test
    failure.
    """
    def __repr__(self):
        return super(AcceptedInvalid, self).__repr__()

    def call_predicate(self, item):
        return isinstance(item[1], Invalid)


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

    def __repr__(self):
        cls_name = self.__class__.__name__
        msg_part = ', msg={0!r}'.format(self.msg) if self.msg else ''
        obj_name = getattr(self.function, '__name__', repr(self.function))
        return '{0}({1}{2})'.format(cls_name, obj_name, msg_part)

    def call_predicate(self, item):
        key = item[0]
        return self.function(key)


class AcceptedArgs(BaseAcceptance):
    """Accepted differences whose 'args' satisfy the given *predicate*
    (see :ref:`predicate-docs` for details).
    """
    def __init__(self, predicate, msg=None):
        super(AcceptedArgs, self).__init__(msg)

        matcher = get_matcher(predicate)
        def function(x):
            return matcher == x
        function.__name__ = repr(matcher)

        self.function = function

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


class AcceptedDeviation(BaseAcceptance):
    """AcceptedDeviation(tolerance, /, msg=None)
    AcceptedDeviation(lower, upper, msg=None)

    Context manager that accepts Deviations within a given tolerance
    without triggering a test failure.

    See documentation for full details.
    """
    def __init__(self, lower, upper=None, msg=None):
        lower, upper, msg = _normalize_deviation_args(lower, upper, msg)
        self.lower = lower
        self.upper = upper
        super(AcceptedDeviation, self).__init__(msg)

    def __repr__(self):
        cls_name = self.__class__.__name__
        msg_part = ', msg={0!r}'.format(self.msg) if self.msg else ''
        if -self.lower ==  self.upper:
            return '{0}({1!r}{2})'.format(cls_name, self.upper, msg_part)
        return '{0}(lower={1!r}, upper={2!r}{3})'.format(cls_name,
                                                         self.lower,
                                                         self.upper,
                                                         msg_part)

    def call_predicate(self, item):
        diff = item[1]
        try:
            deviation = diff.deviation or 0
        except AttributeError:
            return False

        if isnan(deviation) or isnan(diff.expected or 0):
            return False
        return self.lower <= deviation <= self.upper

with contextlib.suppress(AttributeError):  # inspect.Signature() is new in 3.3
    AcceptedDeviation.__init__.__signature__ = inspect.Signature([
        inspect.Parameter('self', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('tolerance', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('msg', inspect.Parameter.POSITIONAL_OR_KEYWORD, default=None),
    ])


class AcceptedPercent(BaseAcceptance):
    """AcceptedPercent(tolerance, /, msg=None)
    AcceptedPercent(lower, upper, msg=None)

    Context manager that accepts Deviations within a given percent
    tolerance without triggering a test failure.

    See documentation for full details.
    """
    def __init__(self, lower, upper=None, msg=None):
        lower, upper, msg = _normalize_deviation_args(lower, upper, msg)
        self.lower = lower
        self.upper = upper
        super(AcceptedPercent, self).__init__(msg)

    def __repr__(self):
        cls_name = self.__class__.__name__
        msg_part = ', msg={0!r}'.format(self.msg) if self.msg else ''
        if -self.lower ==  self.upper:
            return '{0}({1!r}{2})'.format(cls_name, self.upper, msg_part)
        return '{0}(lower={1!r}, upper={2!r}{3})'.format(cls_name,
                                                         self.lower,
                                                         self.upper,
                                                         msg_part)

    def call_predicate(self, item):
        diff = item[1]

        try:
            deviation = diff.deviation
            expected = diff.expected
        except AttributeError:
            return False

        if expected:
            percent_error = (deviation or 0) / expected
        elif not deviation:
            percent_error = 0
        else:
            return False  # <- EXIT!

        if isnan(percent_error):
            return False
        return self.lower <= percent_error <= self.upper

with contextlib.suppress(AttributeError):  # inspect.Signature() is new in 3.3
    AcceptedPercent.__init__.__signature__ = inspect.Signature([
        inspect.Parameter('self', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('tolerance', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('msg', inspect.Parameter.POSITIONAL_OR_KEYWORD, default=None),
    ])


class AcceptedTolerance(BaseAcceptance):
    """AcceptedTolerance(tolerance, /, msg=None, *, percent=False)
    AcceptedTolerance(lower, upper, msg=None, *, percent=False)

    Context manager that accepts numeric differences within a given
    tolerance without triggering a test failure.

    See documentation for full details.
    """
    def __init__(self, lower, upper=None, msg=None, percent=False):  # TODO: Make percent kwonly.
        lower, upper, msg = _normalize_deviation_args(lower, upper, msg)
        self.lower = lower
        self.upper = upper
        self.percent = percent
        super(AcceptedTolerance, self).__init__(msg)

    def __repr__(self):
        cls_name = self.__class__.__name__

        if self.msg:
            msg_repr = ', msg={0!r}'.format(self.msg)
        else:
            msg_repr = ''

        if self.percent:
            percent_repr = ', percent={0!r}'.format(self.percent)
        else:
            percent_repr = ''

        if -self.lower == self.upper:
            repr_string = '{0}({1!r}{2}{3})'.format(
                cls_name,
                self.upper,
                msg_repr,
                percent_repr,
            )
        else:
            repr_string = '{0}(lower={1!r}, upper={2!r}{3}{4})'.format(
                cls_name,
                self.lower,
                self.upper,
                msg_repr,
                percent_repr,
            )
        return repr_string

    def call_predicate(self, item):
        _, diff = item  # Unpack item (discarding key).

        # Get deviation and expected value if type and values are compatible.
        try:
            deviation = diff.deviation
            expected = diff.expected
        except AttributeError:
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
                    try:
                        expected = args[1] or 0
                        deviation = (args[0] or 0) - expected
                    except TypeError:
                        return False
            else:
                return False  # <- EXIT!

        error = deviation or 0
        if self.percent:
            if not expected:
                return not error  # <- EXIT!
            error = error / expected  # Make percent error.

        return self.lower <= error <= self.upper


class AcceptedFuzzy(BaseAcceptance):
    """Context manager that accepts Invalid string differences without
    triggering a test failure if the actual value and the expected
    value match with a similarity greater than or equal to *cutoff*
    (default 0.6).

    Similarity measures are determined using the ratio() method
    of the difflib.SequenceMatcher class. The values range from
    1.0 (exactly the same) to 0.0 (completely different).
    """
    def __init__(self, cutoff=0.6, msg=None):
        self.cutoff = cutoff
        super(AcceptedFuzzy, self).__init__(msg)

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


class AcceptedDifferences(BaseAcceptance):
    """Accepts differences that match *obj* without triggering a test
    failure. The given *obj* can be a difference class, a difference
    instance, or a container of difference instances.

    When *obj* is a class, differences are accepted if they are
    instances of the class. When *obj* is a difference or collection
    of differences, then an error's differences are accepted if they
    compare as equal to one of the accepted differences.

    If given, the *scope* can be ``'element'``, ``'group'``, or
    ``'whole'``. An element-wise scope will accept any difference that
    has a match in *obj*. A group-wise scope will accept one difference
    per match in *obj* per group. A whole-error scope will accept one
    difference per match in *obj* over the ValidationError as a whole.

    If unspecified, *scope* will default to ``'element'`` if *obj* is a
    single element and ``'group'`` if *obj* is a container of elements.
    If *obj* is a mapping, the scope is applied for each key/value
    pair (and whole-error scopes are, instead, treated as group-wise
    scopes).
    """
    def __init__(self, obj, msg=None, scope=None):
        if scope not in (None, 'element', 'group', 'whole'):
            message = "scope may be 'element', 'group', or 'whole', got {0}"
            raise ValueError(message.format(scope))

        super(AcceptedDifferences, self).__init__(msg)
        self._scope = scope

        if isinstance(obj, Mapping):
            self._obj = obj
        elif nonstringiter(obj) and (scope is None or scope == 'group'):
            self._obj = defaultdict(lambda: list(obj))  # Copy for each group.
        else:  # For 'element' or 'whole' scopes.
            self._obj = defaultdict(lambda: obj)  # Single persistent object.

    def start_group(self, key):
        """Called before processing each group."""
        try:
            current_allowance = self._obj[key]  # Can't use get() with defaultdict.
        except KeyError:
            current_allowance = []

        if isinstance(current_allowance, type):
            default_scope = 'element'
            current_allowance = [current_allowance]
            current_check = \
                lambda x: current_allowance and isinstance(x, current_allowance[0])
        else:
            if nonstringiter(current_allowance):
                default_scope = 'group'
            else:
                default_scope = 'element'
                current_allowance = [current_allowance]
            current_check = lambda x: x in current_allowance

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
        return super(AcceptedDifferences, self).__repr__()


class AcceptedSpecific(BaseAcceptance):
    """Accepts specific *differences* without triggering a
    test failure.
    """
    def __init__(self, differences, msg=None):
        if not isinstance(differences, (BaseDifference, list, set, dict)):
            raise TypeError(
                'differences must be a list, dict, or a single difference, '
                'got {0} type instead'.format(differences.__class__.__name__)
            )
        self.differences = differences
        self.msg = msg
        self._accepted = dict()         # Properties to hold working values
        self._predicate_keys = dict()  # during acceptance checking.

    @property
    def priority(self):
        return 200

    def __repr__(self):
        cls_name = self.__class__.__name__
        msg_part = ', msg={0!r}'.format(self.msg) if self.msg else ''
        return '{0}({1!r}{2})'.format(cls_name, self.differences, msg_part)

    def start_collection(self):
        self._predicate_keys = dict()  # Clear _predicate_keys

        # Normalize and copy mutable containers, assign to "_accepted".
        diffs = self.differences
        if isinstance(diffs, BaseDifference):
            accepted = defaultdict(lambda: [diffs])
        elif isinstance(diffs, (list, set)):
            accepted = defaultdict(lambda: list(diffs))
        elif isinstance(diffs, dict):
            accepted = dict()
            for key, value in diffs.items():
                matcher = get_matcher(key)
                if isinstance(matcher, MatcherBase):
                    self._predicate_keys[key]= matcher

                if isinstance(value, (list, set)):
                    accepted[key] = list(value)  # Make a copy.
                else:
                    accepted[key] = [value]
        else:
            raise TypeError(
                'differences must be a list, dict, or a single difference, '
                'got {0} type instead'.format(accepted.__class__.__name__)
            )
        self._accepted = accepted

    def call_predicate(self, item):
        key, diff = item
        try:
            self._accepted[key].remove(diff)
            return True
        except KeyError:
            matches = dict()

            # See if key compares as equal to any predicate-keys.
            for match_key, match_pred in self._predicate_keys.items():
                if match_pred == key:
                    matches[match_key] = match_pred

            if not matches:
                return False
            elif len(matches) == 1:
                try:
                    match_key = next(iter(matches.keys()))
                    self._accepted[match_key].remove(diff)
                    return True
                except ValueError:
                    return False
            else:
                msg = (
                    'the key {0!r} matches multiple predicates: {1}'
                ).format(key, ', '.join(repr(x) for x in matches.values()))
                exc = KeyError(msg)
                exc.__cause__ = None
                raise exc

        except ValueError:
            return False


class AcceptedLimit(BaseAcceptance):
    """Accepted up to a given *number* of differences without
    triggering a test failure.
    """
    def __init__(self, number, msg=None):
        if not isinstance(number, Number):
            err_msg = 'number must be a numeric type, got {0}'
            raise TypeError(err_msg.format(number.__class__.__name__))

        self.number = number
        self.msg = msg
        self._count = None  # Properties to hold working values
        self._limit = None  # during acceptance checking.

    def __repr__(self):
        cls_name = self.__class__.__name__
        msg_part = ', msg={0!r}'.format(self.msg) if self.msg else ''
        return '{0}({1!r}{2})'.format(cls_name, self.number, msg_part)

    @property
    def priority(self):
        return 300

    def start_collection(self):
        self._limit = self.number
        self._count = 0

    def call_predicate(self, item):
        self._count += 1
        return self._count <= self._limit


##########################################
# Factory object for pytest-style testing.
##########################################

class AcceptedFactoryType(object):
    """Accept differences without triggering a test failure."""

    def __repr__(self):
        default_repr = super(AcceptedFactoryType, self).__repr__()
        name_start = default_repr.index(self.__class__.__name__)
        no_module_prefix = default_repr[name_start:]  # Slice-off module.
        return '<' + no_module_prefix

    def missing(self, msg=None):
        """Accepts :class:`Missing` values without triggering a
        test failure:

        .. code-block:: python
            :emphasize-lines: 7

            from datatest import validate, accepted

            data = ['B', 'C']

            requirement = {'A', 'B', 'C'}

            with accepted.missing():
                validate(data, requirement)  # Raises Missing('A')
        """
        return AcceptedMissing(msg)

    def extra(self, msg=None):
        """Accepts :class:`Extra` values without triggering a
        test failure:

        .. code-block:: python
            :emphasize-lines: 7

            from datatest import validate, accepted

            data = ['A', 'B', 'C']

            requirement = {'A', 'B'}

            with accepted.extra():
                validate(data, requirement)  # Raises Extra('C')
        """
        return AcceptedExtra(msg)

    def invalid(self, msg=None):
        """Accepts :class:`Invalid` values without triggering a
        test failure:

        .. code-block:: python
            :emphasize-lines: 7

            from datatest import validate, accepted

            data = ['A', 'B', 'A']

            requirement = 'A'

            with accepted.invalid():
                validate(data, requirement)  # Raises Invalid('B')
        """
        return AcceptedInvalid(msg)

    def keys(self, predicate, msg=None):
        """Accepts differences whose associated keys satisfy the given
        *predicate* (see :ref:`predicate-docs` for details):

        .. code-block:: python
            :emphasize-lines: 7

            from datatest import validate, accepted

            data = {'A': 'x', 'B': 'y'}

            requirement = 'x'

            with accepted.keys('B'):
                validate(data, requirement)  # Raises dictionary
                                             # {'B': Invalid('y')}
        """
        return AcceptedKeys(predicate, msg)

    def args(self, predicate, msg=None):
        """Accepts differences whose :attr:`args <BaseDifference.args>`
        satisfy the given *predicate* (see :ref:`predicate-docs` for
        details):

        .. code-block:: python
            :emphasize-lines: 7

            from datatest import validate, accepted

            data = {'A': 'x', 'B': 'y'}

            requirement = 'x'

            with accepted.args('y'):
                validate(data, requirement)  # Raises dictionary
                                             # {'B': Invalid('y')}
        """
        return AcceptedArgs(predicate, msg)

    def fuzzy(self, cutoff=0.6, msg=None):
        """Accepted invalid strings that match their expected value
        with a similarity greater than or equal to *cutoff* (default
        0.6).

        Similarity measures are determined using the ratio() method of
        the difflib.SequenceMatcher class. The values range from 1.0
        (exactly the same) to 0.0 (completely different):

        .. code-block:: python
            :emphasize-lines: 7

            from datatest import validate, accepted

            data = {'A': 'aax', 'B': 'bbx'}

            requirement = {'A': 'aaa', 'B': 'bbb'}

            with accepted.fuzzy():
                validate(data, requirement)
        """
        return AcceptedFuzzy(cutoff=cutoff, msg=msg)

    def deviation(self, lower, upper=None, msg=None):
        """accepted.deviation(tolerance, /, msg=None)
        accepted.deviation(lower, upper, msg=None)

        Context manager that accepts Deviations within a given
        tolerance without triggering a test failure.

        See documentation for full details.
        """
        return AcceptedDeviation(lower, upper, msg)

    def percent(self, lower, upper=None, msg=None):
        """accepted.percent(tolerance, /, msg=None)
        accepted.percent(lower, upper, msg=None)

        Context manager that accepts Deviations within a given
        percent tolerance without triggering a test failure.

        See documentation for full details.
        """
        return AcceptedPercent(lower, upper, msg)

    def specific(self, differences, msg=None):
        """Accepts specific *differences* without triggering a
        test failure:

        .. code-block:: python
            :emphasize-lines: 7-10

            from datatest import validate, accepted, Extra, Missing

            data = ['x', 'y', 'q']

            requirement = {'x', 'y', 'z'}

            known_issues = accepted.specific([
                Extra('q'),
                Missing('z'),
            ])

            with known_issues:
                validate(data, requirement)

        When data is a mapping, the specified differences are
        accepted from each group independently:

        .. code-block:: python
            :emphasize-lines: 10-13

            from datatest import validate, accepted, Extra, Missing

            data = {
                'A': ['x', 'y', 'q'],
                'B': ['x', 'y'],
            }

            requirement = {'x', 'y', 'z'}

            known_issues = accepted.specific([  # Accepts all given
                Extra('q'),                     # differences from
                Missing('z'),                   # both 'A' and 'B'.
            ])

            with known_issues:
                validate(data, requirement)

        A dictionary of acceptances can be used to define individual
        sets of differences per group:

        .. code-block:: python
            :emphasize-lines: 10-13

            from datatest import validate, accepted, Extra, Missing

            data = {
                'A': ['x', 'y', 'q'],
                'B': ['x', 'y'],
            }

            requirement = {'x', 'y', 'z'}

            known_issues = accepted.specific({     # Using dict
                'A': [Extra('q'), Missing('z')],   # of accepted
                'B': Missing('z'),                 # differences.
            })

            with known_issues:
                validate(data, requirement)

        A dictionary of acceptances can use predicate-keys to treat
        multiple groups as a single group (see :ref:`predicate-docs`
        for details):

        .. code-block:: python
            :emphasize-lines: 10-13

            from datatest import validate, accepted

            data = {
                'A': ['x', 'y', 'q'],
                'B': ['x', 'y'],
            }

            requirement = {'x', 'y', 'z'}

            known_issues = accepted.specific({
                # Use predicate key, an ellipsis wildcard.
                ...: [Extra('q'), Missing('z'), Missing('z')]
            })

            with known_issues:
                validate(data, requirement)
        """
        return AcceptedSpecific(differences, msg)

    def limit(self, number, msg=None):
        """Accepts up to a given *number* of differences without
        triggering a test failure:

        .. code-block:: python
            :emphasize-lines: 7

            from datatest import validate, accepted

            data = ['A', 'B', 'A', 'C']

            requirement = 'A'

            with accepted.limit(2):
                validate(data, requirement)  # Raises [Invalid('B'),
                                             #         Invalid('C')]

        If the count of differences exceeds the given *number*, the test
        case will fail with a :class:`ValidationError` containing the
        remaining differences.
        """
        return AcceptedLimit(number, msg)


accepted = AcceptedFactoryType()  # Use as instance.


##########################
# Deprecated 'allowed' API
##########################

class allowed(abc.ABC):
    def __new__(cls, *args, **kwds):
        msg = ("Can't instantiate abstract class allowed, use constructor "
               "methods like allowed.missing(), allowed.extra(), etc.")
        raise TypeError(msg)

    @staticmethod
    def _warn(new_name):
        import warnings
        message = "'allowed' API is deprecated, use {0} instead".format(new_name)
        warnings.warn(message, DeprecationWarning, stacklevel=3)

    @classmethod
    def missing(cls, msg=None):
        cls._warn('accepted.missing()')
        return AcceptedMissing(msg)

    @classmethod
    def extra(cls, msg=None):
        cls._warn('accepted.extra()')
        return AcceptedExtra(msg)

    @classmethod
    def invalid(cls, msg=None):
        cls._warn('accepted.invalid()')
        return AcceptedInvalid(msg)

    @classmethod
    def keys(cls, predicate, msg=None):
        cls._warn('accepted.keys()')
        return AcceptedKeys(predicate, msg)

    @classmethod
    def args(cls, predicate, msg=None):
        cls._warn('accepted.args()')
        return AcceptedArgs(predicate, msg)

    @classmethod
    def fuzzy(cls, cutoff=0.6, msg=None):
        cls._warn('accepted.fuzzy()')
        return AcceptedFuzzy(cutoff=cutoff, msg=msg)

    @classmethod
    def deviation(cls, lower, upper=None, msg=None):
        cls._warn('accepted.deviation()')
        return AcceptedDeviation(lower, upper, msg)

    @classmethod
    def percent(cls, lower, upper=None, msg=None):
        cls._warn('accepted.percent()')
        return AcceptedPercent(lower, upper, msg)

    @classmethod
    def percent_deviation(cls, lower, upper=None, msg=None):
        cls._warn('accepted.percent()')
        return AcceptedPercent(lower, upper, msg)

    @classmethod
    def specific(cls, differences, msg=None):
        cls._warn('accepted.specific()')
        return AcceptedSpecific(differences, msg)

    @classmethod
    def limit(cls, number, msg=None):
        cls._warn('accepted.limit()')
        return AcceptedLimit(number, msg)
