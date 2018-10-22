# -*- coding: utf-8 -*-
import difflib
from ._compatibility.builtins import *
from ._compatibility import abc
from ._compatibility.collections.abc import Hashable
from ._compatibility.collections.abc import Iterable
from ._compatibility.collections.abc import Mapping
from ._compatibility.collections.abc import Sequence
from ._compatibility.collections.abc import Set
from .difference import BaseDifference
from .difference import Extra
from .difference import Missing
from .difference import _make_difference
from ._predicate import Predicate
from ._utils import iterpeek
from ._utils import nonstringiter


class Required(abc.ABC):
    """Base class for Required objects."""
    @property
    @abc.abstractmethod
    def msg(self):
        raise NotImplementedError

    @abc.abstractmethod
    def filterfalse(self, iterable):
        """Return a non-string iterable of differences for values in
        *iterable* that do not satisfy the requirement.
        """
        raise NotImplementedError

    @staticmethod
    def _verify_filterfalse(filtered):
        """A generator function to wrap the results of filteredfalse()
        and verify that each item returned is a difference object. If
        any invalid values are returned, a TypeError is raised.
        """
        if not nonstringiter(filtered):
            cls_name = filtered.__class__.__name__
            message = ('filterfalse() must return non-string iterable, '
                       'got {0!r} instead')
            raise TypeError(message.format(cls_name))

        for value in filtered:
            if not isinstance(value, BaseDifference):
                cls_name = value.__class__.__name__
                message = ('filterfalse() result must contain difference '
                           'objects, got {0}: {1!r}')
                raise TypeError(message.format(cls_name, value))
            yield value

    def __call__(self, iterable):
        filtered = self.filterfalse(iterable)
        verified = self._verify_filterfalse(filtered)
        first_element, verified = iterpeek(verified)
        if first_element:
            return verified
        return None


class RequiredPredicate(Required):
    def __init__(self, predicate):
        if not isinstance(predicate, Predicate):
            predicate = Predicate(predicate)
        self.predicate = predicate

    def filterfalse(self, iterable, show_expected):
        predicate = self.predicate  # Assign directly in local scope
        obj = predicate.obj         # to avoid dot-lookups.

        for element in iterable:
            result = predicate(element)
            if not result:
                yield _make_difference(element, obj, show_expected)

            elif isinstance(result, BaseDifference):
                yield result

    def __call__(self, iterable, show_expected=False):
        # Get differences using *show_expected* argument.
        filtered = self.filterfalse(iterable, show_expected)
        normalized = self._verify_filterfalse(filtered)
        first_element, normalized = iterpeek(normalized)
        if first_element:
            return normalized
        return None

    @property
    def msg(self):
        return 'does not satisfy: {0}'.format(self.predicate)


class RequiredSet(Required):
    def __init__(self, requirement):
        self.requirement = requirement

    def filterfalse(self, iterable):
        requirement = self.requirement  # Assign locally to avoid dot-lookups.

        matching_elements = set()
        extra_elements = set()
        for element in iterable:
            if element in requirement:
                matching_elements.add(element)
            else:
                extra_elements.add(element)  # <- Build set of Extras so we
                                             #    do not return duplicates.
        for element in requirement:
            if element not in matching_elements:
                yield Missing(element)

        for element in extra_elements:
            yield Extra(element)

    @property
    def msg(self):
        return 'does not satisfy set membership'


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


class RequiredSequence(Required):
    """Require a specified sequence of objects. If the candidate
    sequence does not match the required sequence, Missing and Extra
    differences will be returned.

    Each difference will contain a two-tuple whose first item is the
    starting slice-index (of the candidate) where the difference occurs
    and whose second item is the non-matching value itself::

        >>> required = RequiredSequence(['a', 'b', 'c'])
        >>> candidate = ['a', 'b', 'x']
        >>> diffs = required(candidate)
        >>> list(diffs)
        [Missing((2, 'c')), Extra((2, 'x'))]

    In the example above, the differences occur at slice-index 2:

        required sequence   ->  [ 'a', 'b', 'c', ]
        candidate sequence  ->  [ 'a', 'b', 'x', ]
                                 ^    ^    ^    ^
                                 |    |    |    |
        slice index         ->   0    1    2    3
    """
    def __init__(self, sequence):
        if not isinstance(sequence, Sequence):
            cls_name = sequence.__class__.__name__
            message = 'must be sequence, got {0!r}'.format(cls_name)
            raise TypeError(message)
        self.sequence = sequence

    def filterfalse(self, iterable):
        if not isinstance(iterable, Sequence):
            iterable = list(iterable)  # <- Needs to be subscriptable.
        sequence = self.sequence  # <- Assign locally to avoid dot-lookups.

        try:
            matcher = difflib.SequenceMatcher(a=iterable, b=sequence)
        except TypeError:
            # Fall-back to slower "deep hash" only if needed.
            data_proxy = tuple(_deephash(x) for x in iterable)
            required_proxy = tuple(_deephash(x) for x in sequence)
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

    @property
    def msg(self):
        return 'does not match required sequence'
