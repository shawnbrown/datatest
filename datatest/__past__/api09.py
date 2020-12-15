"""Backward compatibility for version 0.9 API."""
from __future__ import absolute_import

import datatest
from datatest._compatibility.collections.abc import Mapping
from datatest._compatibility.collections.abc import Set
from datatest._normalize import normalize
from datatest._utils import IterItems


class RequiredSubset_090(datatest.requirements.GroupRequirement):
    """Implements inverted subset behavior from 0.9.x API."""
    def __init__(self, requirement):
        if not isinstance(requirement, Set):
            requirement = set(requirement)
        self._set = requirement

    def check_group(self, group):
        missing = self._set.copy()
        for element in group:
            if not missing:
                break
            missing.discard(element)

        differences = (Missing(element) for element in missing)
        description = 'must contain all elements of given requirement'
        return differences, description


class RequiredSuperset_090(datatest.requirements.GroupRequirement):
    """Implements inverted superset behavior from 0.9.x API."""

    def __init__(self, requirement):
        if not isinstance(requirement, Set):
            requirement = set(requirement)
        self._set = requirement

    def check_group(self, group):
        superset = self._set
        extras = set()
        for element in group:
            if element not in superset:
                extras.add(element)

        differences = (Extra(element) for element in extras)
        description = 'may only contain elements of given requirement'
        return differences, description



class ValidateType(datatest.validation.ValidateType):
    def subset(self, data, requirement, msg=None):
        """Implements API 0.9.x subset behavior."""
        __tracebackhide__ = datatest.validation._pytest_tracebackhide

        requirement = normalize(requirement, lazy_evaluation=False, default_type=set)

        if isinstance(requirement, (Mapping, IterItems)):
            factory = RequiredSubset_090
            requirement = datatest.requirements.RequiredMapping(requirement, factory)
        else:
            requirement = RequiredSubset_090(requirement)

        self(data, requirement, msg=msg)

    def superset(self, data, requirement, msg=None):
        """Implements API 0.9.x superset behavior."""
        __tracebackhide__ = datatest.validation._pytest_tracebackhide

        requirement = normalize(requirement, lazy_evaluation=False, default_type=set)

        if isinstance(requirement, (Mapping, IterItems)):
            factory = RequiredSuperset_090
            requirement = datatest.requirements.RequiredMapping(requirement, factory)
        else:
            requirement = RequiredSuperset_090(requirement)

        self(data, requirement, msg=msg)


datatest.validate = ValidateType()
