# -*- coding: utf-8 -*-
from ._compatibility.builtins import *
from ._compatibility import abc
from ._compatibility.collections.abc import Iterable
from .difference import BaseDifference
from .difference import Extra
from .difference import Missing
from .difference import Invalid
from ._utils import iterpeek
from ._utils import nonstringiter


class Requirement(abc.ABC):
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
    def _verify_filterfalse(iterable):
        """Verify that filterfalse() returns a non-string iterable of
        differences.
        """
        if not nonstringiter(iterable):
            cls_name = iterable.__class__.__name__
            message = ('filterfalse() must return non-string iterable, '
                       'got {0!r} instead')
            raise TypeError(message.format(cls_name))

        for value in iterable:
            if not isinstance(value, BaseDifference):
                cls_name = value.__class__.__name__
                message = ('filterfalse() result must contain difference '
                           'objects, got {0}: {1!r}')
                raise TypeError(message.format(cls_name, value))
            yield value

    def __call__(self, iterable):
        filtered = self.filterfalse(iterable)
        normalized = self._verify_filterfalse(filtered)
        first_element, normalized = iterpeek(normalized)
        if first_element:
            return normalized
        return None


class PredicateRequirement(Requirement):
    def __init__(self, predicate):
        self.predicate = predicate

    def filterfalse(self, iterable):
        predicate = self.predicate  # Assign locally to avoid dot-lookups.

        for element in iterable:
            result = predicate(element)
            if not result:
                yield Invalid(element)
            elif isinstance(result, BaseDifference):
                yield result

    @property
    def msg(self):
        return 'does not satisfy {0}'.format(self.predicate)


class SetRequirement(Requirement):
    def __init__(self, requirement):
        self.requirement = requirement

    def filterfalse(self, iterable):
        requirement = self.requirement  # Assign locally to avoid dot-lookup.

        matching_elements = set()
        extra_elements = set()
        for element in iterable:
            if element in requirement:
                matching_elements.add(element)
            else:
                extra_elements.add(element)

        for element in requirement:
            if element not in matching_elements:
                yield Missing(element)

        for element in extra_elements:
            yield Extra(element)

    @property
    def msg(self):
        return 'does not satisfy set membership'
