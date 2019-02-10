# -*- coding: utf-8 -*-
import difflib
from numbers import Number
from types import FunctionType
from ._compatibility.builtins import *
from ._compatibility import abc
from ._compatibility.collections.abc import Hashable
from ._compatibility.collections.abc import Iterable
from ._compatibility.collections.abc import Mapping
from ._compatibility.collections.abc import Sequence
from ._compatibility.collections.abc import Set
from ._compatibility.functools import wraps
from ._compatibility.itertools import chain
from .difference import BaseDifference
from .difference import Extra
from .difference import Missing
from .difference import _make_difference
from .difference import NOTFOUND
from ._normalize import normalize
from ._predicate import Predicate
from ._query.query import BaseElement
from ._utils import IterItems
from ._utils import iterpeek
from ._utils import nonstringiter


def _build_description(obj):
    """Build failure description for required_predicate() or
    for a group-requirement function that does not return its
    own description.
    """
    if obj is NOTFOUND:
        return obj  # <- EXIT!

    if isinstance(obj, FunctionType):
        docstring = getattr(obj, '__doc__', None)
        if docstring:
            first_line = docstring.lstrip().partition('\n')[0]
            description = first_line.rstrip()
            if description:
                return description  # <- EXIT!

    name = getattr(obj, '__name__', None)
    if name:
        if name.startswith('<'):  # E.g., "<lambda>".
            obj_repr = name
        else:
            if callable(obj) and not isinstance(obj, type):
                obj_repr = "{0}()".format(name)
            else:
                obj_repr = "'{0}'".format(name)
    else:
        obj_repr = repr(obj)

    return 'does not satisfy {0}'.format(obj_repr)


def _wrap_differences(differences, func):
    """A generator function to wrap and iterable of differences
    and verify that each item returned is a difference object.
    If any non-difference objects are encountered, a TypeError
    is raised.

    The given *differences* should be an iterable of difference
    objects and *func* should be the group requirement function
    used to generate the differences.
    """
    for value in differences:
        if not isinstance(value, BaseDifference):
            func_name = getattr(func, '__name__', func.__class__.__name__)
            cls_name = value.__class__.__name__
            message = ('iterable from group requirement {0!r} must '
                       'contain difference objects, got {1!r}: {2!r}')
            raise TypeError(message.format(func_name, cls_name, value))
        yield value


def _normalize_requirement_result(result, func):
    """Takes the *result* of a requirement function as well as the
    *func* itself and returns a normalized differences-description
    2-tuple or None.
    """
    if (isinstance(result, Sequence)
            and len(result) == 2
            and not isinstance(result[1], BaseDifference)):
        differences, description = result
    else:
        differences = result
        description = _build_description(func)

    if not isinstance(differences, Iterable):
        func_name = getattr(func, '__name__', func.__class__.__name__)
        bad_type = differences.__class__.__name__
        message = ('requirement function {0!r} should return a single '
                   'iterable or a tuple containing an iterable and a '
                   'string description, got {1!r}: {2!r}')
        raise TypeError(message.format(func_name, bad_type, differences))

    first_item, differences = iterpeek(differences, NOTFOUND)
    if first_item is NOTFOUND:
        return None
    differences = _wrap_differences(differences, func)
    return differences, description


def group_requirement(func):
    """A decorator for group requirement functions. A group requirement
    function should accept an iterable and return values appropriate
    for instantiating a :exc:`ValidationError` (either an iterable of
    differences or a 2-tuple containing an iterable of differences and
    a description).
    """
    if getattr(func, '_group_requirement', False):
        return func  # <- EXIT!

    @wraps(func)
    def wrapper(iterable, *args, **kwds):
        result = func(iterable, *args, **kwds)
        return _normalize_requirement_result(result, func)

    wrapper._group_requirement = True
    return wrapper


def required_predicate(requirement, show_expected=False):
    """Accepts a *requirement* object and returns a group requirement
    that tests for a predicate.
    """
    @group_requirement
    def _required_predicate(iterable):  # Closes over *requirement*
                                        # and *show_expected*.
        def generate_differences(requirement, iterable):
            predicate = Predicate(requirement)
            for element in iterable:
                result = predicate(element)
                if not result:
                    yield _make_difference(element, requirement, show_expected)
                elif isinstance(result, BaseDifference):
                    yield result

        differences = generate_differences(requirement, iterable)
        description = _build_description(requirement)
        return differences, description

    return _required_predicate


def required_set(requirement):
    """Returns a group requirement function that checks for set membership."""
    @group_requirement
    def _required_set(iterable):  # Closes over *requirement*.
        matches = set()
        extras = set()
        for element in iterable:
            if element in requirement:
                matches.add(element)
            else:
                extras.add(element)  # <- Build set of Extras so we
                                     #    do not return duplicates.
        missing = (x for x in requirement if x not in matches)

        differences = chain(
            (Missing(x) for x in missing),
            (Extra(x) for x in extras),
        )
        return differences, 'does not satisfy set membership'

    return _required_set


def _deephash(obj):
    """Return a "deep hash" value for the given object. If the
    object can not be deep-hashed, a TypeError is raised.
    """
    # Adapted from "deephash" Copyright 2017 Shawn Brown, Apache License 2.0.
    already_seen = {}

    def _hashable_proxy(obj):
        if isinstance(obj, Hashable) and not isinstance(obj, tuple):
            return obj  # <- EXIT!

        # Guard against recursive references in compound objects.
        obj_id = id(obj)
        if obj_id in already_seen:
            return already_seen[obj_id]  # <- EXIT!
        else:
            already_seen[obj_id] = object()  # Token for duplicates.

        # Recurse into compound object to make hashable proxies.
        if isinstance(obj, Sequence):
            proxy = tuple(_hashable_proxy(x) for x in obj)
        elif isinstance(obj, Set):
            proxy = frozenset(_hashable_proxy(x) for x in obj)
        elif isinstance(obj, Mapping):
            items = ((k, _hashable_proxy(v)) for k, v in IterItems(obj))
            proxy = frozenset(items)
        else:
            message = 'unhashable type: {0!r}'.format(obj.__class__.__name__)
            raise TypeError(message)
        return obj.__class__, proxy

    try:
        return hash(obj)
    except TypeError:
        return hash(_hashable_proxy(obj))


def required_sequence(requirement):
    if not isinstance(requirement, Sequence):
        cls_name = requirement.__class__.__name__
        message = 'must be sequence, got {0!r}'.format(cls_name)
        raise TypeError(message)

    @group_requirement
    def _required_sequence(iterable):  # Closes over *requirement*.

        def generate_differences(iterable, sequence):
            if not isinstance(iterable, Sequence):
                iterable = list(iterable)  # <- Needs to be subscriptable.

            try:
                matcher = difflib.SequenceMatcher(a=iterable, b=requirement)
            except TypeError:
                # Fall-back to slower "deep hash" only if needed.
                data_proxy = tuple(_deephash(x) for x in iterable)
                required_proxy = tuple(_deephash(x) for x in requirement)
                matcher = difflib.SequenceMatcher(a=data_proxy, b=required_proxy)

            for tag, istart, istop, jstart, jstop in matcher.get_opcodes():
                if tag == 'insert':
                    jvalues = sequence[jstart:jstop]
                    for value in jvalues:
                        yield Missing((istart, value))
                elif tag == 'delete':
                    ivalues = iterable[istart:istop]
                    for index, value in enumerate(ivalues, start=istart):
                        yield Extra((index, value))
                elif tag == 'replace':
                    ivalues = iterable[istart:istop]
                    jvalues = sequence[jstart:jstop]

                    ijvalues = zip(ivalues, jvalues)
                    for index, (ival, jval) in enumerate(ijvalues, start=istart):
                        yield Missing((index, jval))
                        yield Extra((index, ival))

                    ilength = istop - istart
                    jlength = jstop - jstart
                    if ilength < jlength:
                        for value in jvalues[ilength:]:
                            yield Missing((istop, value))
                    elif ilength > jlength:
                        remainder = ivalues[jlength:]
                        new_start = istart + jlength
                        for index, value in enumerate(remainder, start=new_start):
                            yield Extra((index, value))

        differences = generate_differences(iterable, requirement)
        return differences, 'does not match required sequence'

    return _required_sequence


def _get_group_requirement(requirement, show_expected=False):
    """Make sure *requirement* is a group requirement."""
    if getattr(requirement, '_group_requirement', False):
        return requirement

    if isinstance(requirement, Set):
        return required_set(requirement)

    if (not isinstance(requirement, BaseElement)
            and isinstance(requirement, Sequence)):
        return required_sequence(requirement)

    return required_predicate(requirement, show_expected)


def _data_vs_requirement(data, requirement):
    """Validate *data* using *requirement* and return any differences."""
    # Handle *data* that is a container of multiple elements.
    if not isinstance(data, BaseElement):
        requirement = _get_group_requirement(requirement)
        return requirement(data)  # <- EXIT!

    # Handle *data* that is a single-value BaseElement.
    requirement = _get_group_requirement(requirement, show_expected=True)
    result = requirement([data])
    if result:
        differences, description = result
        differences = list(differences)
        if len(differences) == 1:
            differences = differences[0]  # Unwrap if single difference.
        return differences, description
    return None


def _datadict_vs_requirement(data, requirement):
    """Apply *requirement* object to mapping of *data* values and
    return a mapping of any differences and a description.
    """
    if isinstance(data, Mapping):
        data_items = IterItems(data)
    elif isinstance(data, IterItems):
        data_items = data
    else:
        raise TypeError('data must be mapping or iterable of key-value items')

    requirement = _get_group_requirement(requirement)

    differences = dict()
    for key, value in data_items:
        result = _data_vs_requirement(value, requirement)
        if result:
            differences[key] = result

    if not differences:
        return None  # <- EXIT!

    # Get first description from results.
    itervalues = getattr(differences, 'itervalues', differences.values)()
    description = next((x for _, x in itervalues), None)

    # Format dictionary values and finalize description.
    for key, value in IterItems(differences):
        diffs, desc = value
        differences[key] = diffs
        if description and description != desc:
            description = None

    return differences, description


def _datadict_vs_requirementdict(data, requirement):
    """Apply mapping of *requirement* values to a mapping of *data*
    values and return a mapping of any differences and a description
    or None.
    """
    if isinstance(data, Mapping):
        data_items = IterItems(data)
    elif isinstance(data, IterItems):
        data_items = data
    else:
        raise TypeError('data must be mapping or iterable of key-value items')

    data_keys = set()
    differences = dict()

    for key, actual in data_items:
        data_keys.add(key)
        expected = requirement.get(key, NOTFOUND)
        result = _data_vs_requirement(actual, expected)
        if result:
            differences[key] = result

    for key, expected in IterItems(requirement):
        if key not in data_keys:
            result = _data_vs_requirement([], expected)  # Try empty container.
            if not result:
                diff = _make_difference(NOTFOUND, expected)
                result = (diff, NOTFOUND)
            differences[key] = result

    if not differences:
        return None  # <- EXIT!

    # Get first description from results.
    itervalues = getattr(differences, 'itervalues', differences.values)()
    filtered = (x for _, x in itervalues if x is not NOTFOUND)
    description = next(filtered, None)

    # Format dictionary values and finalize description.
    for key, value in IterItems(differences):
        diffs, desc = value
        differences[key] = diffs
        if description and description != desc and desc is not NOTFOUND:
            description = None

    return differences, description


def whole_requirement(func):
    """A decorator for whole requirement functions. A whole requirement
    function should accept a *data* object and return values appropriate
    for instantiating a :exc:`ValidationError` (either an iterable of
    differences or a 2-tuple containing an iterable of differences and
    a description).
    """
    if getattr(func, '_whole_requirement', False):
        return func  # <- EXIT!

    func._whole_requirement = True
    return func

    @wraps(func)
    def wrapper(data):
        result = func(data)
        return _normalize_requirement_result(result, func)

    wrapper._whole_requirement = True
    return wrapper


def requirement_handler(requirement):
    """Returns a while requirement function that provides default
    validation behavior.
    """
    @whole_requirement
    def _requirement_handler(data):
        """Default requirement handler."""
        if isinstance(requirement, Mapping):
            result = _datadict_vs_requirementdict(data, requirement)
        elif isinstance(data, (Mapping, IterItems)):
            result = _datadict_vs_requirement(data, requirement)
        else:
            result = _data_vs_requirement(data, requirement)
        return result

    return _requirement_handler


def _get_required_func(requirement):
    """Returns a whole-object requirement handler."""
    if getattr(requirement, '_whole_requirement', False):
        return requirement
    return requirement_handler(requirement)


##############################
# Abstract Requirement Classes
##############################

class BaseRequirement(abc.ABC):
    @abc.abstractmethod
    def check_data(self, data):
        raise NotImplementedError()

    def _verify_difference(self, obj):
        """Raise an error if *obj* is not a subclass of BaseDifference."""
        if not isinstance(obj, BaseDifference):
            slf_name = self.__class__.__name__
            obj_name = obj.__class__.__name__
            message = ('values returned from {0} must be '
                       'difference objects, got {1}: {2!r}')
            raise TypeError(message.format(slf_name, obj_name, obj))

    def _wrap_difference_group(self, group):
        """A generator function to wrap an iterable of differences and
        verify that each value is a difference object.
        """
        for value in group:
            self._verify_difference(value)
            yield value

    def _wrap_difference_items(self, items):
        """A generator function to wrap an iterable of key/value pairs
        and verify that each value is a difference or an iterable of
        difference objects.
        """
        for key, value in items:
            if nonstringiter(value):
                value = self._wrap_difference_group(value)
            else:
                self._verify_difference(value)
            yield key, value

    def _normalize(self, result):
        """Return a normalized *result* as a 2-tuple (containing an
        iterable of differences and a string description) or None.
        """
        if (isinstance(result, Sequence)
                and len(result) == 2
                and not isinstance(result[1], BaseDifference)):
            differences, description = result
        else:
            differences = result
            description = ''

        if not description:
            description = 'does not satisfy {0}'.format(self.__class__.__name__)

        if not isinstance(differences, Iterable):
            slf_name = self.__class__.__name__
            dff_name = differences.__class__.__name__
            message = (
                '{0!r} should return an iterable or a tuple containing '
                'an iterable and a string description, got {1!r}: {2!r}'
            )
            raise TypeError(message.format(slf_name, dff_name, differences))

        first_item, differences = iterpeek(differences, NOTFOUND)

        if first_item is NOTFOUND:
            return None  # <- EXIT!

        if isinstance(first_item, tuple):
            differences = self._wrap_difference_items(differences)
        else:
            differences = self._wrap_difference_group(differences)
        return differences, description

    def __call__(self, data):
        result = self.check_data(data)
        return self._normalize(result)


class ItemsRequirement(BaseRequirement):
    @abc.abstractmethod
    def check_items(self, items):
        raise NotImplementedError()

    def check_data(self, data):
        data = normalize(data, lazy_evaluation=True)
        if isinstance(data, Mapping):
            data = IterItems(data)
        return self.check_items(data)


_INCONSISTENT = object()  # Marker for inconsistent descriptions.

class GroupRequirement(BaseRequirement):
    @abc.abstractmethod
    def check_group(self, group):
        raise NotImplementedError()

    def check_items(self, items, autowrap=True):
        differences = []
        description = ''
        check_group = self.check_group

        for key, value in items:
            if isinstance(value, BaseElement) and autowrap:
                value = [value]  # Wrap element to treat it as a group.
                diff, desc = check_group(value)
                diff = list(diff)
                if len(diff) == 1:
                    diff = diff[0]  # Unwrap if single difference.
                if not diff:
                    continue
            else:
                diff, desc = check_group(value)
                first_element, diff = iterpeek(diff, None)
                if not first_element:
                    continue

            differences.append((key, diff))

            if description == desc or description is _INCONSISTENT:
                continue

            if not description:
                description = desc
            else:
                description = _INCONSISTENT

        if description is _INCONSISTENT:
            description = ''
        return differences, description

    def check_data(self, data):
        data = normalize(data, lazy_evaluation=True)

        if isinstance(data, Mapping):
            data = IterItems(data)

        if isinstance(data, IterItems):
            return self.check_items(data)

        if isinstance(data, BaseElement):
            data = [data]
        return self.check_group(data)


##############################
# Concrete Requirement Classes
##############################

class RequiredPredicate(GroupRequirement):
    """A requirement to test data for predicate matches."""
    def __init__(self, obj, show_expected=False):
        self._pred = Predicate(obj)
        self._obj = obj
        self.show_expected = show_expected

    def _get_differences(self, group):
        pred = self._pred
        obj = self._obj
        show_expected = self.show_expected
        for element in group:
            result = pred(element)
            if not result:
                yield _make_difference(element, obj, show_expected)
            elif isinstance(result, BaseDifference):
                yield result

    def check_group(self, group):
        differences = self._get_differences(group)
        description = _build_description(self._obj)
        return differences, description

    def check_items(self, items):
        pred = self._pred
        obj = self._obj
        show_expected = self.show_expected
        check_group = self.check_group

        differences = []
        for key, value in items:
            if isinstance(value, BaseElement):
                result = pred(value)
                if not result:
                    diff = _make_difference(value, obj, show_expected)
                elif isinstance(result, BaseDifference):
                    diff = result
                else:
                    continue
            else:
                diff, desc = check_group(value)
                first_element, diff = iterpeek(diff, None)
                if not first_element:
                    continue
            differences.append((key, diff))

        description = _build_description(obj)
        return differences, description


class RequiredSet(GroupRequirement):
    """A requirement to test data for set membership."""
    def __init__(self, requirement):
        self._set = set(requirement)

    def check_group(self, group):
        requirement = self._set

        matches = set()
        extras = set()
        for element in group:
            if element in requirement:
                matches.add(element)
            else:
                extras.add(element)  # <- Build set of Extras so we
                                     #    do not return duplicates.
        missing = (x for x in requirement if x not in matches)

        differences = chain(
            (Missing(x) for x in missing),
            (Extra(x) for x in extras),
        )
        return differences, 'does not satisfy set membership'


class RequiredOrder(GroupRequirement):
    """A requirement to test data for element order."""
    def __init__(self, sequence):
        if not isinstance(sequence, Sequence):
            cls_name = sequence.__class__.__name__
            message = 'must be sequence, got {0!r}'.format(cls_name)
            raise TypeError(message)
        self.sequence = sequence

    def _generate_differences(self, group):
        if not isinstance(group, Sequence):
            group = list(group)  # <- Needs to be subscriptable.

        requirement = self.sequence

        try:
            # Try sequences directly.
            matcher = difflib.SequenceMatcher(a=group, b=requirement)
        except TypeError:
            # Fall-back to slower proxy method when needed.
            data_proxy = tuple(_deephash(x) for x in group)
            required_proxy = tuple(_deephash(x) for x in requirement)
            matcher = difflib.SequenceMatcher(a=data_proxy, b=required_proxy)

        for tag, istart, istop, jstart, jstop in matcher.get_opcodes():
            if tag == 'insert':
                jvalues = requirement[jstart:jstop]
                for value in jvalues:
                    yield Missing((istart, value))
            elif tag == 'delete':
                ivalues = group[istart:istop]
                for index, value in enumerate(ivalues, start=istart):
                    yield Extra((index, value))
            elif tag == 'replace':
                ivalues = group[istart:istop]
                jvalues = requirement[jstart:jstop]

                ijvalues = zip(ivalues, jvalues)
                for index, (ival, jval) in enumerate(ijvalues, start=istart):
                    yield Missing((index, jval))
                    yield Extra((index, ival))

                ilength = istop - istart
                jlength = jstop - jstart
                if ilength < jlength:
                    for value in jvalues[ilength:]:
                        yield Missing((istop, value))
                elif ilength > jlength:
                    remainder = ivalues[jlength:]
                    new_start = istart + jlength
                    for index, value in enumerate(remainder, start=new_start):
                        yield Extra((index, value))

    def check_group(self, group):
        differences = self._generate_differences(group)
        return differences, 'does not match required sequence'


class RequiredMapping(ItemsRequirement):
    """A requirement to test a mapping of data against a *mapping*
    of required objects.

    If given, an *abstract_factory* should be a callable of one
    argument that accepts a value and returns an appropriate
    GroupRequirement factory or None. If None is returned, the
    default auto-detection is used instead.
    """
    def __init__(self, mapping, abstract_factory=None):
        if not isinstance(mapping, Mapping):
            mapping = dict(mapping)
        self.mapping = mapping
        self._abstract_factory = abstract_factory

    def abstract_factory(self, obj):
        """Return a group requirement type appropriate for the given
        *obj* or None if *obj* is already a GroupRequirement instance.
        """
        if self._abstract_factory:
            factory = self._abstract_factory(obj)
            if factory:
                return factory

        if isinstance(obj, GroupRequirement):
            return None

        if isinstance(obj, Set):
            return RequiredSet

        if isinstance(obj, Sequence) and not isinstance(obj, BaseElement):
            return RequiredOrder

        return RequiredPredicate

    @staticmethod
    def _update_description(current, new):
        if current == new or current is _INCONSISTENT or new is NOTFOUND:
            return current

        if not current:
            return new

        return _INCONSISTENT

    def check_items(self, items):
        required_mapping = self.mapping
        differences = []
        description = ''

        # Check values using requirement of corresponding key.
        keys_seen = set()
        for item in items:
            try:
                key, value = item
            except ValueError:
                msg = ('item {0!r} is not a valid key/value pair; {1} '
                       'expects a mapping or iterable of key/value pairs')
                raise ValueError(msg.format(item, self.__class__.__name__))

            keys_seen.add(key)

            expected = required_mapping.get(key, NOTFOUND)
            req_type = self.abstract_factory(expected)

            if isinstance(value, BaseElement):
                if req_type is RequiredPredicate:
                    # Skip requirement and use Predicate directly.
                    pred = Predicate(expected)
                    result = pred(value)
                    if not result:
                        diff = _make_difference(value, expected, show_expected=True)
                        differences.append((key, diff))
                        desc = _build_description(expected)
                        description = self._update_description(description, desc)
                    elif isinstance(result, BaseDifference):
                        differences.append((key, result))
                        desc = _build_description(expected)
                        description = self._update_description(description, desc)
                    continue  # <- CONTINUE!
                else:
                    # Change single-element into a group.
                    value = [value]

            requirement = req_type(expected) if req_type else expected

            diff, desc = requirement.check_group(value)
            first_item, diff = iterpeek(diff, None)
            if first_item:
                differences.append((key, diff))
                description = self._update_description(description, desc)

        # Check for expected keys that are missing from items.
        for key, expected in IterItems(required_mapping):
            if key not in keys_seen:
                req_type = self.abstract_factory(expected)
                requirement = req_type(expected) if req_type else expected

                diff, desc = requirement.check_group([])  # Try empty container.
                first_item, diff = iterpeek(diff, None)
                if not first_item:
                    diff = _make_difference(NOTFOUND, expected)
                differences.append((key, diff))
                description = self._update_description(description, desc)

        if description is _INCONSISTENT or not description:
            description = 'does not satisfy mapping requirements'
        return differences, description


def get_requirement(obj):
    """Return a requirement instance appropriate for the given *obj*."""
    if isinstance(obj, BaseRequirement):
        return obj

    obj = normalize(obj, lazy_evaluation=False)

    if isinstance(obj, Mapping):
        return RequiredMapping(obj)

    if isinstance(obj, Set):
        return RequiredSet(obj)

    if isinstance(obj, Sequence) and not isinstance(obj, BaseElement):
        return RequiredOrder(obj)

    return RequiredPredicate(obj)


#########################################
# Additional Concrete Requirement Classes
#########################################

class RequiredUnique(GroupRequirement):
    """A requirement to test that elements are unique."""
    @staticmethod
    def _generate_differences(group):
        seen = set()
        for element in group:
            if element in seen:
                yield Extra(element)
            else:
                seen.add(element)

    def check_group(self, group):
        if isinstance(group, BaseElement):
            cls_name = group.__class__.__name__
            msg = 'expected non-tuple, non-string sequence, got {0}: {1!r}'
            raise ValueError(msg.format(cls_name, group))

        differences = self._generate_differences(group)
        return differences, 'elements should be unique'

    def check_data(self, data):
        data = normalize(data, lazy_evaluation=True)

        if isinstance(data, Mapping):
            data = IterItems(data)

        if isinstance(data, IterItems):
            return self.check_items(data, autowrap=False)

        return self.check_group(data)


class RequiredSubset(GroupRequirement):
    """Require that data contains all elements of *subset*."""
    def __init__(self, subset):
        if not isinstance(subset, Set):
            subset = set(subset)
        self._subset = subset

    def check_group(self, group):
        missing = self._subset.copy()
        for element in group:
            if not missing:
                break
            missing.discard(element)

        differences = (Missing(element) for element in missing)
        description = 'must contain all elements of given subset'
        return differences, description


class RequiredSuperset(GroupRequirement):
    """Require that data contains only elements of *superset*."""
    def __init__(self, superset):
        if not isinstance(superset, Set):
            superset = set(superset)
        self._superset = superset

    def check_group(self, group):
        superset = self._superset
        extras = set()
        for element in group:
            if element not in superset:
                extras.add(element)

        differences = (Extra(element) for element in extras)
        description = 'may contain only elements of given superset'
        return differences, description


class RequiredApprox(RequiredPredicate):
    """Require that numeric values are approximately equal.

    Values compare as equal if their difference rounded to the
    given number of decimal places (default 7) equals zero, or
    if the difference between values is less than or equal to
    the given delta.
    """
    def __new__(cls, obj, places=None, delta=None, show_expected=False):
        # If numeric, return new RequiredApprox (normal behavior).
        if isinstance(obj, Number):
            return super(RequiredApprox, cls).__new__(cls)

        # If mapping, use RequiredMapping with abstract factory.
        if isinstance(obj, (Mapping, IterItems)):
            def abstract_factory(value):
                if isinstance(value, Number):
                    def make_approx(val):
                        return RequiredApprox(val, places=places, delta=delta)
                    return make_approx  # <- Concrete factory.
                return None

            return RequiredMapping(obj, abstract_factory=abstract_factory)

        # If not numeric or mapping, use auto-detected type.
        return get_requirement(obj)

    def __init__(self, obj, places=None, delta=None, show_expected=False):
        if delta is not None and places is not None:
            raise TypeError('specify delta or places not both')

        if places is None:
            places = 7

        if delta is not None:
            def approx_equal(element):  # <- Closes over obj and delta.
                try:
                    return abs(element - obj) <= delta
                except TypeError:
                    return False
        else:
            def approx_equal(element):  # <- Closes over obj and places.
                try:
                    return round(abs(element - obj), places) == 0
                except TypeError:
                    return False

        self._pred = approx_equal
        self._obj = obj
        self.show_expected = show_expected
        self.places = places
        self.delta = delta

    def _get_description(self):
        if self.delta is not None:
            return 'not equal within delta of {0}'.format(self.delta)
        return 'not equal within {0} decimal places'.format(self.places)

    def check_group(self, group):
        differences, _ = super(RequiredApprox, self).check_group(group)
        return differences, self._get_description()

    def check_items(self, group):
        differences, _ = super(RequiredApprox, self).check_items(group)
        return differences, self._get_description()
