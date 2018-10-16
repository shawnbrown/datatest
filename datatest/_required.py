# -*- coding: utf-8 -*-
from ._compatibility.builtins import *
from ._compatibility import abc
from ._compatibility.collections.abc import Iterable
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
