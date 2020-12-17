# -*- coding: utf-8 -*-
from __future__ import division
import inspect
from unittest import TestCase
from ._compatibility.builtins import *
from ._compatibility import contextlib

from .validation import validate
from .validation import ValidationError
from .validation import _pytest_tracebackhide
from .acceptances import (
    AcceptedDifferences,
    AcceptedTolerance,
    AcceptedPercent,
    AcceptedKeys,
    AcceptedArgs,
    AcceptedFuzzy,
    AcceptedCount,
)
from . import differences


__unittest = True  # Hides internal stack frames from unittest output.


class DataTestCase(TestCase):
    """This optional wrapper class provides an interface that is
    consistent with established unittest conventions. This class
    extends |TestCase| with methods for asserting validity and
    accepting differences. In addition, familiar methods and attributes
    (like |setUp|, |maxDiff|, |assertions| etc.) are also available.

    .. |TestCase| replace:: :py:class:`unittest.TestCase`
    .. |setUp| replace:: :py:meth:`setUp() <unittest.TestCase.setUp>`
    .. |maxDiff| replace:: :py:attr:`maxDiff <unittest.TestCase.maxDiff>`
    .. |assertions| replace:: :ref:`assertions <python:assert-methods>`
    """
    maxDiff = getattr(TestCase, 'maxDiff', 80 * 8)  # Uses default in 3.1 and 2.6.

    def _apply_validation(self, function, *args, **kwds):
        """Wrapper to call *function* (with given *args and **kwds)
        and manage truncation behavior if a ValidationError is raised.

        The *function* must be a callable object and it should pass
        silently or raise a ValidationError.
        """
        try:
            function(*args, **kwds)
        except ValidationError as err:
            def should_truncate(line_count, char_count):
                return self.maxDiff and (char_count > self.maxDiff)
            err._should_truncate = should_truncate

            err._truncation_notice = \
                'Diff is too long. Set self.maxDiff to None to see it.'

            raise err

    def assertValid(self, data, requirement, msg=None):
        """Wrapper for :func:`validate`."""
        __tracebackhide__ = _pytest_tracebackhide
        self._apply_validation(validate, data, requirement, msg=msg)

    def assertValidApprox(self, data, requirement, places=None, msg=None, delta=None):
        """Wrapper for :meth:`validate.approx`."""
        __tracebackhide__ = _pytest_tracebackhide
        self._apply_validation(validate.approx, data, requirement,
                               places=places, msg=msg, delta=delta)

    def assertValidFuzzy(self, data, requirement, cutoff=0.6, msg=None):
        """Wrapper for :meth:`validate.fuzzy`."""
        __tracebackhide__ = _pytest_tracebackhide
        self._apply_validation(validate.fuzzy, data, requirement,
                               cutoff=cutoff, msg=msg)

    def assertValidInterval(self, data, min=None, max=None, msg=None):
        """Wrapper for :meth:`validate.interval`."""
        __tracebackhide__ = _pytest_tracebackhide
        self._apply_validation(validate.interval, data, min, max, msg=msg)

    def assertValidOrder(self, data, sequence, msg=None):
        """Wrapper for :meth:`validate.order`."""
        __tracebackhide__ = _pytest_tracebackhide
        self._apply_validation(validate.order, data, sequence, msg=msg)

    def assertValidPredicate(self, data, requirement, msg=None):
        """Wrapper for :meth:`validate.predicate`."""
        __tracebackhide__ = _pytest_tracebackhide
        self._apply_validation(validate.predicate, data, requirement, msg=msg)

    def assertValidRegex(self, data, requirement, flags=0, msg=None):
        """Wrapper for :meth:`validate.regex`."""
        __tracebackhide__ = _pytest_tracebackhide
        self._apply_validation(validate.regex, data, requirement, flags=flags, msg=msg)

    def assertValidSet(self, data, requirement, msg=None):
        """Wrapper for :meth:`validate.set`."""
        __tracebackhide__ = _pytest_tracebackhide
        self._apply_validation(validate.set, data, requirement, msg=msg)

    def assertValidSubset(self, data, requirement, msg=None):
        """Wrapper for :meth:`validate.subset`."""
        __tracebackhide__ = _pytest_tracebackhide
        self._apply_validation(validate.subset, data, requirement, msg=msg)

    def assertValidSuperset(self, data, requirement, msg=None):
        """Wrapper for :meth:`validate.superset`."""
        __tracebackhide__ = _pytest_tracebackhide
        self._apply_validation(validate.superset, data, requirement, msg=msg)

    def assertValidUnique(self, data, msg=None):
        """Wrapper for :meth:`validate.unique`."""
        __tracebackhide__ = _pytest_tracebackhide
        self._apply_validation(validate.unique, data, msg=msg)

    def accepted(self, obj, msg=None, scope=None):
        """Wrapper for :func:`accepted`."""
        return AcceptedDifferences(obj, msg=msg, scope=scope)

    def acceptedKeys(self, predicate, msg=None):
        """Wrapper for :meth:`accepted.keys`."""
        return AcceptedKeys(predicate, msg)

    def acceptedArgs(self, predicate, msg=None):
        """Wrapper for :meth:`accepted.args`."""
        return AcceptedArgs(predicate, msg)

    def acceptedTolerance(self, lower, upper=None, msg=None):
        """
        acceptedTolerance(tolerance, /, msg=None)
        acceptedTolerance(lower, upper, msg=None)

        Wrapper for :meth:`accepted.tolerance`.
        """
        return AcceptedTolerance(lower, upper=upper, msg=msg)

    def acceptedPercent(self, lower, upper=None, msg=None):
        """
        acceptedPercent(tolerance, /, msg=None)
        acceptedPercent(lower, upper, msg=None)

        Wrapper for :meth:`accepted.percent`.
        """
        return AcceptedPercent(lower, upper, msg)

    def acceptedFuzzy(self, cutoff=0.6, msg=None):
        """Wrapper for :meth:`accepted.fuzzy`."""
        return AcceptedFuzzy(cutoff=cutoff, msg=msg)

    def acceptedCount(self, number, msg=None, scope=None):
        """Wrapper for :meth:`accepted.count`."""
        return AcceptedCount(number, msg=msg, scope=scope)


# Prettify default signature of methods that accept multiple signatures.
# This only works for Python 3.3 and newer--older versions will simply
# have the original method sigture.
with contextlib.suppress(AttributeError):  # inspect.Signature() is new in 3.3
    DataTestCase.acceptedTolerance.__signature__ = inspect.Signature([
        inspect.Parameter('self', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('tolerance', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('msg', inspect.Parameter.POSITIONAL_OR_KEYWORD, default=None),
    ])

    DataTestCase.acceptedPercent.__signature__ = inspect.Signature([
        inspect.Parameter('self', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('tolerance', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('msg', inspect.Parameter.POSITIONAL_OR_KEYWORD, default=None),
    ])
