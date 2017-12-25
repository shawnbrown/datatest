# -*- coding: utf-8 -*-
import inspect
from math import isnan
from numbers import Number
from .utils.builtins import *
from .utils import abc
from .utils import collections
from .utils import contextlib
from .utils import functools
from .utils import itertools

from .utils.misc import _is_consumable
from .utils.misc import _get_arg_lengths
from .utils.misc import _expects_multiple_params
from .utils.misc import _make_decimal
from .utils.misc import string_types
from .dataaccess import _is_collection_of_items
from .dataaccess import BaseElement
from .dataaccess import DictItems

from .validation import ValidationError
from .difference import BaseDifference
from .difference import Missing
from .difference import Extra
from .difference import Invalid
from .difference import Deviation


__datatest = True  # Used to detect in-module stack frames (which are
                   # omitted from output).


__all__ = [
    'BaseAllowance',
    'ElementAllowance',
    'allowed_missing',
    'allowed_extra',
    'allowed_invalid',
    'allowed_deviation',
    'allowed_percent_deviation',
    'allowed_specific',
    'allowed_key',
    'allowed_args',
    'allowed_limit',
]


def _is_mapping_type(obj):
    return isinstance(obj, collections.Mapping) or \
                _is_collection_of_items(obj)


class BaseAllowance(abc.ABC):
    """Context manager to allow certain differences without
    triggering a test failure. *group_filterfalse* should
    accept an iterable of difference and return an iterable
    of only those differences which are **not** allowed.
    """
    def __init__(self, msg=None):
        """Initialize object values."""
        self.msg = msg

    def __or__(self, other):
        return NotImplemented

    def __and__(self, other):
        return NotImplemented

    def __enter__(self):
        return self

    def item_filterfalse(self, key, value):
        """Return key-value tuple if difference is not allowed, else
        return None.
        """
        raise NotImplementedError()

    def group_filterfalse(self, group):
        """Filter iterable and yield items that are not allowed."""
        raise NotImplementedError()

    def all_filterfalse(self, iterable):
        if isinstance(iterable, collections.Mapping):
            iterable = getattr(iterable, 'iteritems', iterable.items)()

        if _is_collection_of_items(iterable):
            for key, diff in iterable:
                if isinstance(diff, (BaseElement, Exception)):
                    # Error is a single element.
                    filtered = self.group_filterfalse(iter([(key, diff)]))
                    if isinstance(filtered, collections.Mapping):
                        filtered = filtered.items()
                    filtered = list(filtered)
                    if filtered:
                        yield filtered[0]
                else:
                    # Error is a container of multiple elements.
                    diff = self.group_filterfalse((key, d) for d in diff)
                    diff = list(d for key, d in diff)
                    if diff:
                        yield key, diff
        else:
            filtered = self.group_filterfalse(iterable)
            if _is_mapping_type(filtered):
                raise TypeError('returned mapping output for non-mapping input')
            for diff in filtered:
                yield diff

    def __exit__(self, exc_type, exc_value, tb):
        # Setup traceback-hiding for pytest integration.
        __tracebackhide__ = lambda excinfo: excinfo.errisinstance(ValidationError)

        # Apply filterfalse or reraise non-validation error.
        if exc_type and not issubclass(exc_type, ValidationError):
            raise exc_value
        differences = getattr(exc_value, 'differences', [])
        differences = self.all_filterfalse(differences)

        # Check container types.
        mappable_in = _is_mapping_type(getattr(exc_value, 'differences', None))
        mappable_out = _is_mapping_type(differences)

        # Check if any differences were returned.
        try:
            first_item = next(iter(differences))
            if _is_consumable(differences):  # Rebuild if consumable.
                differences = itertools.chain([first_item], differences)
        except StopIteration:
            return True  # <- EXIT!

        # Handle mapping input with iterable-of-items output.
        if (mappable_in and not mappable_out
                and isinstance(first_item, collections.Sized)
                and len(first_item) == 2):
            differences = DictItems(differences)
            mappable_out = True

        # Verify type compatibility.
        if mappable_in != mappable_out:
            message = ('received {0!r} collection but returned '
                       'incompatible {1!r} collection')
            output_cls = differences.__class__.__name__
            input_cls = exc_value.differences.__class__.__name__
            raise TypeError(message.format(input_cls, output_cls))

        # Extend message with allowance message.
        message = getattr(exc_value, 'message', '')
        if self.msg:
            message = '{0}: {1}'.format(self.msg, message)

        # Build new ValidationError with remaining differences.
        exc = ValidationError(message, differences)

        # Re-raised error inherits truncation behavior of original.
        exc._should_truncate = exc_value._should_truncate
        exc._truncation_notice = exc_value._truncation_notice

        exc.__cause__ = None  # <- Suppress context using verbose
        raise exc             #    alternative to support older Python
                              #    versions--see PEP 415 (same as
                              #    effect as "raise ... from None").


class BaseAllowance2(abc.ABC):
    """Context manager to allow certain differences without
    triggering a test failure.
    """
    def __init__(self, msg=None):
        """Initialize object values."""
        self.msg = msg

    ######################################
    # Hook methods for allowance protocol.
    ######################################
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

    ####################################
    # Operators for boolean composition.
    ####################################
    @abc.abstractmethod
    def __and__(self, other):
        return NotImplemented

    @abc.abstractmethod
    def __or__(self, other):
        return NotImplemented

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
        if isinstance(iterable, collections.Mapping):
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
        is_not_mapping = not isinstance(differences, collections.Mapping)

        stream = self._serialized_items(differences)
        stream = self._filterfalse(stream)
        differences = self._deserialized_items(stream)

        if not differences:
            return True  # <- EXIT!

        if is_not_mapping:
            assert len(differences) == 1
            differences = differences.popitem()[1]
            if isinstance(differences, BaseDifference):
                differences = [differences]

        # Extend message with allowance message.
        message = getattr(exc_value, 'message', '')
        if self.msg:
            message = '{0}: {1}'.format(self.msg, message)

        # Build new ValidationError with remaining differences.
        exc = ValidationError(message, differences)

        # Re-raised error inherits truncation behavior of original.
        exc._should_truncate = exc_value._should_truncate
        exc._truncation_notice = exc_value._truncation_notice

        exc.__cause__ = None  # <- Suppress context using verbose
        raise exc             #    alternative to support older Python
                              #    versions--see PEP 415 (same as
                              #    effect as "raise ... from None").


class BaseMixin(BaseAllowance2):
    """Base class for mixins to support composition of allowances."""
    def __init__(self, left, right, msg=None):
        self.left = left
        self.right = right
        self.msg = msg

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


class LogicalAndMixin(BaseMixin):
    """Mixin class to combine allowances using logical AND condition."""
    def __init__(self, left, right, msg=None):
        if not msg:
            msg = '({0} <and> {1})'.format(
                left.msg or left.__class__.__name__,
                right.msg or right.__class__.__name__,
            )
        super(LogicalAndMixin, self).__init__(left, right, msg)

    def call_predicate(self, item):
        return (self.left.call_predicate(item)
                and self.right.call_predicate(item))


class LogicalOrMixin(BaseMixin):
    """Mixin class to combine allowances using logical OR condition."""
    def __init__(self, left, right, msg=None):
        if not msg:
            msg = '({0} <or> {1})'.format(
                left.msg or left.__class__.__name__,
                right.msg or right.__class__.__name__,
            )
        super(LogicalOrMixin, self).__init__(left, right, msg)

    def call_predicate(self, item):
        return (self.left.call_predicate(item)
                or self.right.call_predicate(item))


class ElementAllowance2(BaseAllowance2):
    def __and__(self, other):
        if not isinstance(other, ElementAllowance2):
            return NotImplemented
        new_cls = type('ComposedElementAllowance',
                       (LogicalAndMixin, ElementAllowance2), {})
        return new_cls(left=self, right=other)

    def __or__(self, other):
        if not isinstance(other, ElementAllowance2):
            return NotImplemented
        new_cls = type('ComposedElementAllowance',
                       (LogicalOrMixin, ElementAllowance2), {})
        return new_cls(left=self, right=other)


class GroupAllowance(BaseAllowance2):
    def __and__(self, other):
        if isinstance(other, GroupAllowance):
            left = self
            right = other
        elif isinstance(other, ElementAllowance2):
            left = other           # By putting the ElementAllowance on the
            right = self           # left, a logical short-circuit skips the
        else:                      # GroupAllowance's call_predicate() on the
            return NotImplemented  # right--which is the desired behavior.

        new_cls = type('ComposedGroupAllowance',
                       (LogicalAndMixin, GroupAllowance), {})
        return new_cls(left, right)

    def __rand__(self, other):
        return self.__and__(other)

    def __or__(self, other):
        if isinstance(other, GroupAllowance):
            left = self
            right = other
        elif isinstance(other, ElementAllowance2):
            left = other           # By putting the ElementAllowance on the
            right = self           # left, a logical short-circuit skips the
        else:                      # GroupAllowance's call_predicate() on the
            return NotImplemented  # right--which is the desired behavior.

        new_cls = type('ComposedGroupAllowance',
                       (LogicalOrMixin, GroupAllowance), {})
        return new_cls(left, right)

    def __ror__(self, other):
        return self.__or__(other)


class CollectionAllowance(BaseAllowance2):
    def __and__(self, other):
        if isinstance(other, CollectionAllowance):
            left = self
            right = other
        elif isinstance(other, (GroupAllowance, ElementAllowance2)):
            left = other           # By putting the element/group on the left,
            right = self           # a logical short-circuit skips the
        else:                      # CollectionAllowance's call_predicate() on
            return NotImplemented  # the right--which is the desired behavior.

        new_cls = type('ComposedCollectionAllowance',
                       (LogicalAndMixin, CollectionAllowance), {})
        return new_cls(left, right)

    def __rand__(self, other):
        return self.__and__(other)

    def __or__(self, other):
        if isinstance(other, CollectionAllowance):
            left = self
            right = other
        elif isinstance(other, (GroupAllowance, ElementAllowance2)):
            left = other
            right = self
        else:
            return NotImplemented

        new_cls = type('ComposedCollectionAllowance',
                       (LogicalOrMixin, CollectionAllowance), {})
        return new_cls(left, right)

    def __ror__(self, other):
        return self.__or__(other)


class allowed_missing(ElementAllowance2):
    def call_predicate(self, item):
        return isinstance(item[1], Missing)


class allowed_extra(ElementAllowance2):
    def call_predicate(self, item):
        return isinstance(item[1], Extra)


class allowed_invalid(ElementAllowance2):
    def call_predicate(self, item):
        return isinstance(item[1], Invalid)


class allowed_key(ElementAllowance2):
    """The given *function* should accept a number of arguments
    equal the given key elements. If key is a single value (string
    or otherwise), *function* should accept one argument. If key
    is a three-tuple, *function* should accept three arguments.
    """
    def __init__(self, function, msg=None):
        self.function = function
        super(allowed_key, self).__init__(msg)

    def call_predicate(self, item):
        key = item[0]
        if isinstance(key, BaseElement):
            return self.function(key)
        return self.function(*key)


class allowed_args(ElementAllowance2):
    """The given *function* should accept a number of arguments equal
    the given elements in the 'args' attribute. If args is a single
    value (string or otherwise), *function* should accept one argument.
    If args is a three-tuple, *function* should accept three arguments.
    """
    def __init__(self, function, msg=None):
        self.function = function
        super(allowed_args, self).__init__(msg)

    def call_predicate(self, item):
        args = item[1].args
        if isinstance(args, BaseElement):
            return self.function(args)
        return self.function(*args)


def _normalize_deviation_args(lower, upper, msg):
    """Normalize deviation allowance arguments to support both
    "tolerance" and "lower, upper" signatures. This helper function
    is intended for internal use.
    """
    if isinstance(upper, str) and msg is None:
        upper, msg = None, msg  # Shift values if using "tolerance" syntax.

    if upper == None:
        tolerance = lower
        assert tolerance >= 0, ('tolerance should not be negative, '
                                'for full control of lower and upper '
                                'bounds, use "lower, upper" syntax')
        lower, upper = -tolerance, tolerance
    lower = _make_decimal(lower)
    upper = _make_decimal(upper)
    assert lower <= upper
    return (lower, upper, msg)


class allowed_deviation(ElementAllowance2):
    """allowed_deviation(tolerance, /, msg=None)
    allowed_deviation(lower, upper, msg=None)

    Context manager that allows Deviations within a given tolerance
    without triggering a test failure.

    See documentation for full details.
    """
    def __init__(self, lower, upper=None, msg=None):
        lower, upper, msg = _normalize_deviation_args(lower, upper, msg)
        self.lower = lower
        self.upper = upper
        super(allowed_deviation, self).__init__(msg)

    def call_predicate(self, item):
        diff = item[1]
        deviation = diff.deviation or 0
        if isnan(deviation) or isnan(diff.expected or 0):
            return False
        return self.lower <= deviation <= self.upper

with contextlib.suppress(AttributeError):  # inspect.Signature() is new in 3.3
    allowed_deviation.__init__.__signature__ = inspect.Signature([
        inspect.Parameter('self', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('tolerance', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('msg', inspect.Parameter.POSITIONAL_OR_KEYWORD),
    ])


class allowed_percent_deviation(ElementAllowance2):
    def __init__(self, lower, upper=None, msg=None):
        lower, upper, msg = _normalize_deviation_args(lower, upper, msg)
        self.lower = lower
        self.upper = upper
        super(allowed_percent_deviation, self).__init__(msg)

    def call_predicate(self, item):
        diff = item[1]
        percent_deviation = diff.percent_deviation or 0
        if isnan(percent_deviation) or isnan(diff.expected or 0):
            return False
        return self.lower <= percent_deviation <= self.upper

with contextlib.suppress(AttributeError):  # inspect.Signature() is new in 3.3
    allowed_percent_deviation.__init__.__signature__ = inspect.Signature([
        inspect.Parameter('self', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('tolerance', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('msg', inspect.Parameter.POSITIONAL_OR_KEYWORD),
    ])


class allowed_specific(GroupAllowance):
    def __init__(self, differences, msg=None):
        if isinstance(differences, collections.Mapping):
            differences = dict(differences)
        self.differences = differences
        self._allowed = None  # Property to hold diffs during processing.
        super(allowed_specific, self).__init__(msg)

    def start_group(self, key):
        try:
            allowed = self.differences.get(key, [])
        except AttributeError:
            allowed = self.differences

        if isinstance(allowed, BaseElement):
            self._allowed = [allowed]
        else:
            self._allowed = list(allowed)

    def call_predicate(self, item):
        diff = item[1]
        if diff in self._allowed:
            self._allowed.remove(diff)
            return True
        return False

    def end_collection(self):
        self._allowed = None


class allowed_limit(CollectionAllowance):
    def __init__(self, number, msg=None):
        self.number = number
        self._count = None  # Property to hold count of diffs during processing.
        super(allowed_limit, self).__init__(msg)

    def start_collection(self):
        self._count = 0

    def call_predicate(self, item):
        self._count += 1
        return self._count <= self.number

    def end_collection(self):
        self._count = None


class ElementAllowance(BaseAllowance):
    """Allow differences where *predicate* returns True. For each
    difference, *predicate* will receive two arguments---a **key**
    and **difference**---and should return True if the difference
    is allowed or False if it is not.
    """
    def __init__(self, predicate, msg=None):
        self.predicate = predicate
        super(ElementAllowance, self).__init__(msg)

    def item_filterfalse(self, key, value):
        if self.predicate(key, value):
            return None
        return key, value

    def group_filterfalse(self, group):
        predicate = self.predicate              # Using predicate() directly
        for key, difference in group:           # is more efficient than
            if not predicate(key, difference):  # calling item_filterfalse().
                yield key, difference

    def all_filterfalse(self, iterable):
        if _is_mapping_type(iterable):
            return super(ElementAllowance, self).all_filterfalse(iterable)  # <- EXIT!

        iterable = ((None, difference) for difference in iterable)
        filtered = super(ElementAllowance, self).all_filterfalse(iterable)
        return (diff for key, diff in filtered)  # 'key' intentionally discarded

    def __or__(self, other):
        if not isinstance(other, ElementAllowance):
            return NotImplemented

        pred1 = self.predicate
        pred2 = other.predicate
        def predicate(*args, **kwds):
            return pred1(*args, **kwds) or pred2(*args, **kwds)
        return ElementAllowance(predicate)

    def __and__(self, other):
        if not isinstance(other, ElementAllowance):
            return NotImplemented

        pred1 = self.predicate
        pred2 = other.predicate
        def predicate(*args, **kwds):
            return pred1(*args, **kwds) and pred2(*args, **kwds)
        return ElementAllowance(predicate)
