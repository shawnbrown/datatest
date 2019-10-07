# -*- coding: utf-8 -*-
"""This module defines requirement classes used internally by datatest."""
from __future__ import absolute_import
from __future__ import division

import difflib
import re
from numbers import Number
from types import FunctionType
from ._compatibility.builtins import *
from ._compatibility import abc
from ._compatibility.collections.abc import Hashable
from ._compatibility.collections.abc import Iterable
from ._compatibility.collections.abc import Mapping
from ._compatibility.collections.abc import Sequence
from ._compatibility.collections.abc import Set
from ._compatibility.functools import partial
from ._compatibility.functools import wraps
from ._compatibility.itertools import chain
from ._compatibility.itertools import zip_longest
from .differences import (
    BaseDifference,
    Extra,
    Invalid,
    Missing,
    _make_difference,
    NOVALUE,
)
from ._normalize import normalize
from ._vendor.predicate import Predicate
from ._vendor.squint import BaseElement
from ._utils import IterItems
from ._utils import iterpeek
from ._utils import nonstringiter
from ._utils import string_types


def _build_description(obj):
    """Build failure description for required_predicate() or
    for a group-requirement function that does not return its
    own description.
    """
    if obj is NOVALUE:
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


##############################
# Abstract Requirement Classes
##############################

class BaseRequirement(abc.ABC):
    """A class to check that the data fulfills a specific need
    or expectation. All requirement classes must inherit from
    BaseRequirement.
    """
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

        first_item, differences = iterpeek(differences, NOVALUE)

        if first_item is NOVALUE:
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
    """A class to check that items or mappings of data fulfill a
    specific need or expectation.
    """
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
    """A class to check that groups of data fulfill a specific need
    or expectation.
    """
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
        self._pred = self.predicate_factory(obj)
        self._obj = obj
        self.show_expected = show_expected

    def predicate_factory(self, obj):
        if isinstance(obj, Predicate):
            return obj
        return Predicate(obj)

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
        if self.__class__ is not RequiredPredicate:
            return super(RequiredPredicate, self).check_items(items)

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


class RequiredRegex(RequiredPredicate):
    """Require that strings match the given regular expression."""
    def __init__(self, obj, flags=0, show_expected=False):
        self.flags = flags
        super(RequiredRegex, self).__init__(obj, show_expected=show_expected)

    def predicate_factory(self, obj):
        """Return Predicate object where string components have been
        replaced with compiled regular expression objects.
        """
        flags = self.flags

        def regex_or_orig(a):
            if isinstance(a, string_types):
                return re.compile(a, flags)
            return a

        if isinstance(obj, tuple):
            return Predicate(tuple(regex_or_orig(x) for x in obj))
        return Predicate(regex_or_orig(obj))


class RequiredApprox(RequiredPredicate):
    """Require that numeric values are approximately equal.

    Values compare as equal if their difference rounded to the
    given number of decimal places (default 7) equals zero, or
    if the difference between values is less than or equal to
    the given delta.
    """
    def __init__(self, obj, places=None, delta=None, show_expected=False):
        if places is None:
            places = 7
        self.places = places
        self.delta = delta
        super(RequiredApprox, self).__init__(obj, show_expected=show_expected)

    @staticmethod
    def approx_delta(delta, value, other):
        try:
            return abs(other - value) <= delta
        except TypeError:
            return False

    @staticmethod
    def approx_places(places, value, other):
        try:
            return round(abs(other - value), places) == 0
        except TypeError:
            return False

    def predicate_factory(self, obj):
        """Return Predicate object where string components have been
        replaced with approx_delta() or approx_delta() function.
        """
        delta = self.delta
        if delta is not None:
            approx_equal = partial(self.approx_delta, delta)
        else:
            approx_equal = partial(self.approx_places, self.places)

        def approx_or_orig(x):
            if isinstance(x, Number):
                return partial(approx_equal, x)
            return x

        if isinstance(obj, tuple):
            return Predicate(tuple(approx_or_orig(x) for x in obj))
        return Predicate(approx_or_orig(obj))

    def _get_description(self):
        if self.delta is not None:
            return 'not equal within delta of {0}'.format(self.delta)
        return 'not equal within {0} decimal places'.format(self.places)

    def check_group(self, group):
        differences, _ = super(RequiredApprox, self).check_group(group)
        return differences, self._get_description()


class RequiredFuzzy(RequiredPredicate):
    """Require that strings match with a similarity greater than
    or equal to *cutoff* (default 0.6).

    Similarity measures are determined using the ratio() method
    of the difflib.SequenceMatcher class. The values range from
    1.0 (exactly the same) to 0.0 (completely different).
    """
    def __init__(self, obj, cutoff=0.6, show_expected=False):
        self.cutoff = cutoff
        super(RequiredFuzzy, self).__init__(obj, show_expected=show_expected)

    def predicate_factory(self, obj):
        """Return Predicate object where string components have been
        replaced with fuzzy_match() function.
        """
        cutoff = self.cutoff
        def fuzzy_match(cutoff, a, b):
            try:
                matcher = difflib.SequenceMatcher(a=a, b=b)
                return matcher.ratio() >= cutoff
            except TypeError:
                return False

        def fuzzy_or_orig(a):
            if isinstance(a, string_types):
                return partial(fuzzy_match, cutoff, a)
            return a

        if isinstance(obj, tuple):
            return Predicate(tuple(fuzzy_or_orig(x) for x in obj))
        return Predicate(fuzzy_or_orig(obj))

    def check_group(self, group):
        differences, description = super(RequiredFuzzy, self).check_group(group)
        fuzzy_info = '{0}, fuzzy matching at ratio {1} or greater'
        description = fuzzy_info.format(description, self.cutoff)
        return differences, description


class RequiredInterval(RequiredPredicate):
    """Require that values are within given interval."""
    def __init__(self, min=None, max=None, show_expected=False):
        left_bounded = min is not None
        right_bounded = max is not None

        if left_bounded and right_bounded:
            if not min <= max:
                raise ValueError("'min' must not be greater than 'max'")

            def interval(element):
                try:
                    if min <= element <= max:
                        return True
                    if element < min:
                        return _make_difference(element, min, show_expected)
                    if element > max:
                        return _make_difference(element, max, show_expected)
                except TypeError:
                    pass
                return Invalid(element)

            description = 'elements `x` do not satisfy `{0!r} <= x <= {1!r}`' 
            description = description.format(min, max)

        elif left_bounded:
            def interval(element):
                try:
                    if min <= element:
                        return True
                    if element < min:
                        return _make_difference(element, min, show_expected)
                except TypeError:
                    pass
                return Invalid(element)

            description = 'does not satisfy minimum expected value of {0!r}'.format(min)

        elif right_bounded:
            def interval(element):
                try:
                    if element <= max:
                        return True
                    if element > max:
                        return _make_difference(element, max, show_expected)
                except TypeError:
                    pass
                return Invalid(element)

            description = 'does not satisfy maximum expected value of {0!r}'.format(max)

        else:
            raise TypeError("must provide at least one: 'min' or 'max'")

        self._description = description
        super(RequiredInterval, self).__init__(interval, show_expected=show_expected)

    def check_group(self, group):
        differences, _ = super(RequiredInterval, self).check_group(group)
        return differences, self._description


class RequiredSet(GroupRequirement):
    """A requirement to test data for set membership."""
    def __init__(self, requirement):
        if not isinstance(requirement, Set):
            requirement = set(requirement)
        self._set = requirement

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


class RequiredOrder(GroupRequirement):
    """A requirement to test data for element order."""
    def __init__(self, sequence):
        if not isinstance(sequence, Sequence):
            sequence = list(sequence)
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
        return differences, 'does not match required order'


class RequiredSequence(GroupRequirement):
    """A requirement to test elements in data against an *iterable*
    of predicate matches (compared by iteration order).
    """
    def __init__(self, iterable, factory=None):
        if not nonstringiter(iterable):
            iterable = [iterable]
        self.iterable = iterable
        if not factory:
            factory = RequiredPredicate
        self.factory = factory

    def _generate_differences(self, group):
        factory = self.factory

        zipped = zip_longest(group, self.iterable, fillvalue=NOVALUE)
        for actual, expected in zipped:
            if factory is RequiredPredicate:
                pred = Predicate(expected)
                result = pred(actual)
                if not result:
                    yield _make_difference(actual, expected, show_expected=True)
                elif isinstance(result, BaseDifference):
                    yield result
            else:
                # Get requirement.
                requirement = factory(expected)
                if isinstance(requirement, RequiredPredicate):
                    requirement.show_expected = True

                # Check element as group and yield unwrapped result.
                diff, desc = requirement.check_group([actual])
                diff = list(diff)
                if diff:
                    if len(diff) > 1:
                        msg = 'expected 0 or 1 differences, got {0}: {1!r}'
                        raise ValueError(msg.format(len(diff), diff))
                    yield diff[0]

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
    def __init__(self, mapping, factory=None):
        if not isinstance(mapping, Mapping):
            mapping = dict(mapping)
        self.mapping = mapping
        self._factory = factory

    def abstract_factory(self, obj):
        """Return a group requirement type appropriate for the given
        *obj* or None if *obj* is already a GroupRequirement instance.
        """
        if self._factory:
            return self._factory

        if isinstance(obj, GroupRequirement):
            return None

        if isinstance(obj, Set):
            return RequiredSet

        if isinstance(obj, Sequence) and not isinstance(obj, BaseElement):
            return RequiredOrder

        return RequiredPredicate

    @staticmethod
    def _update_description(current, new):
        if current == new or current is _INCONSISTENT or new is NOVALUE:
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

            expected = required_mapping.get(key, NOVALUE)
            factory = self.abstract_factory(expected)

            if isinstance(value, BaseElement):
                if factory is RequiredPredicate:
                    # Skip requirement and use Predicate directly.
                    # Note: Performance benchmarking shows that this
                    # optimization can finish in 72% of the time it
                    # takes for the unoptimized case.
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
                else:
                    # Get requirement.
                    requirement = factory(expected) if factory else expected
                    if isinstance(requirement, RequiredPredicate):
                        requirement.show_expected = True

                    # Check element as group and unwrap single element result.
                    diff, desc = requirement.check_group([value])
                    diff = list(diff)
                    if len(diff) == 1:
                        diff = diff[0]  # Unwrap if single difference.
                    if diff:
                        differences.append((key, diff))
                        description = self._update_description(description, desc)
            else:
                # Normal group handling (`value` is already a group).
                requirement = factory(expected) if factory else expected
                diff, desc = requirement.check_group(value)
                first_item, diff = iterpeek(diff, None)
                if first_item:
                    differences.append((key, diff))
                    description = self._update_description(description, desc)

        # Check for expected keys that are missing from items.
        for key, expected in IterItems(required_mapping):
            if key not in keys_seen:
                factory = self.abstract_factory(expected)
                requirement = factory(expected) if factory else expected

                diff, desc = requirement.check_group([])  # Try empty container.
                first_item, diff = iterpeek(diff, None)
                if not first_item:
                    diff = _make_difference(NOVALUE, expected)
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

    if isinstance(obj, Iterable) and not isinstance(obj, BaseElement):
        return RequiredSequence(obj)

    return RequiredPredicate(obj)


def adapts_mapping(cls):
    """A decorator for group requirement classes that adds handling
    for mappings::

        from datatest.requirements import adapts_mapping
        from datatest.requirements import RequiredInterval


        @adapts_mapping
        class CustomInterval(RequiredInterval):
            def __init__(self, value):
                half = value / 2.0
                double = value * 2.0
                super().__init__(lower=half, upper=double)

    When given a mapping, the decorated class returns a mapping of
    multiple group requirements::

        requirement = CustomInterval({'A': 10, 'B': 2})

    The adapted mapping in the previous example is equivalent to the
    following::

        requirement = RequiredMapping({
            'A': CustomInterval(10),
            'B': CustomInterval(2),
        })

    The treatment of non-mapping objects is unchanged by the decorator::

        requirement = CustomInterval(10)
    """
    if not issubclass(cls, GroupRequirement):
        raise TypeError('decorated class must inherit from GroupRequirement')

    orig_new = cls.__new__

    # Discard additional arguments if calling object.__new__().
    if orig_new is object.__new__:
        orig_new = lambda C, *args, **kwds: object.__new__(C)

    @wraps(orig_new)
    def wrapped_new(C, *args, **kwds):
        if args and isinstance(args[0], (Mapping, IterItems)):
            obj, args = args[0], args[1:]
            def factory(val):
                requirement = orig_new(C, val, *args, **kwds)
                if isinstance(requirement, C):
                    requirement.__init__(val, *args, **kwds)
                return requirement
            return RequiredMapping(obj, factory)
        return orig_new(C, *args, **kwds)

    # Needed for Python 2.x, Pypy, and some version of PyPy3.
    wrapped_new = staticmethod(wrapped_new)

    cls.__new__ = wrapped_new
    return cls
