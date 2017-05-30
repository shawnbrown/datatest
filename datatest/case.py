# -*- coding: utf-8 -*-
from __future__ import division
import inspect
from unittest import TestCase

from .utils.builtins import *
from .utils import collections
from .utils import contextlib

from .dataaccess import DataQuery
from .dataaccess import DataResult

from .require import _get_differences
from .errors import ValidationError

__datatest = True  # Used to detect in-module stack frames (which are
                   # omitted from output).

from .allow import allowed_missing
from .allow import allowed_extra
from .allow import allowed_invalid
from .allow import allowed_deviation
from .allow import allowed_percent_deviation
from .allow import allowed_specific
from .allow import allowed_key
from .allow import allowed_args
from .allow import allowed_limit


class DataTestCase(TestCase):
    """This class extends :py:class:`unittest.TestCase` with methods
    for asserting data validity. In addition to the new functionality,
    familiar methods (like setUp, addCleanup, etc.) are still
    available.
    """
    @property
    def subject(self):
        """A convenience property that references the data under
        test---the *subject* of the tests.  A subject can be defined at
        the module-level or at the class-level.  This property will
        return the :attr:`subject` from the nearest enclosed scope.

        Module-level declaration::

            def setUpModule():
                global subject
                subject = datatest.CsvSource('myfile.csv')

        Class-level declaration::

            class TestMyFile(datatest.DataTestCase):
                @classmethod
                def setUpClass(cls):
                    cls.subject = datatest.CsvSource('myfile.csv')

        This property is required when using the :meth:`assertValid`
        method's helper-function shorthand.
        """
        if hasattr(self, '_subject_data'):
            return self._subject_data
        return self._find_data_source('subject')

    @subject.setter
    def subject(self, value):
        self._subject_data = value

    @property
    def reference(self):
        """A convenience property that references data trusted to be
        correct.  A reference can be defined at the module-level or at
        the class-level.  This property will return the
        :attr:`reference` from the nearest enclosed scope.

        Module-level declaration::

            def setUpModule():
                global subject, reference
                subject = datatest.CsvSource('myfile.csv')
                reference = datatest.CsvSource('myreference.csv')

        Class-level declaration::

            class TestMyFile(datatest.DataTestCase):
                @classmethod
                def setUpClass(cls):
                    cls.subject = datatest.CsvSource('myfile.csv')
                    cls.reference = datatest.CsvSource('myreference.csv')

        This property is required when using the :meth:`assertValid`
        method's helper-function shorthand.
        """
        if hasattr(self, '_reference_data'):
            return self._reference_data
        return self._find_data_source('reference')

    @reference.setter
    def reference(self, value):
        self._reference_data = value

    @staticmethod
    def _find_data_source(name):
        # TODO: Make this method play nice with getattr() when
        # attribute is missing.
        stack = inspect.stack()
        stack.pop()  # Skip record of current frame.
        for record in stack:   # Bubble-up stack looking for name.
            frame = record[0]
            if name in frame.f_globals:
                return frame.f_globals[name]  # <- EXIT!
        raise NameError('cannot find {0!r}'.format(name))

    def assertValid(self, data, requirement, msg=None):
        """Fail if the *data* under test does not satisfy the
        *requirement*.

        The given *data* can be a set, sequence, iterable, mapping,
        or other object. The *requirement* type determines how the
        data is validated (see below).

        **Set membership:** When *requirement* is a set, elements
        in *data* are checked for membership in this set. On failure,
        :class:`Missing` or :class:`Extra` errors are raised::

            def test_mydata(self):
                data = ...
                requirement = {'A', 'B', 'C', ...}  # <- set
                self.assertValid(data, requirement)

        **Regular expression match:** When *requirement* is a regular
        expression object, elements in *data* are checked to see if
        they match the given pattern. On failure, :class:`Invalid`
        errors are raised::

            def test_mydata(self):
                data = ...
                requirement = re.compile(r'^\S.*\S$|^\S?$')  # <- regex
                self.assertValid(data, requirement)

        **Sequence order:** When *requirement* is a list or other
        sequence, elements in *data* are checked for matching order
        and value. On failure, an :py:class:`AssertionError` is
        raised::

            def test_mydata(self):
                data = ...
                requirement = ['A', 'B', 'C', ...]  # <- sequence
                self.assertValid(data, requirement)

        **Mapping comparison:** When *requirement* is a dict (or other
        mapping), elements of matching keys are checked for equality.
        This comparison also requires *data* to be a mapping. On
        failure, :class:`Invalid` or :class:`Deviation` errors are
        raised::

            def test_mydata(self):
                data = ...  # <- Should also be a mapping.
                requirement = {'A': 1, 'B': 2, 'C': ...}  # <- mapping
                self.assertValid(data, requirement)

        **Function comparison:** When *requirement* is a function or
        other callable, elements in *data* are checked to see if they
        evaluate to True. When the function returns False,
        :class:`Invalid` errors are raised::

            def test_mydata(self):
                data = ...
                def requirement(x):  # <- callable (helper function)
                    return x.isupper()
                self.assertValid(data, requirement)

        **Other comparison:** When *requirement* does not match any
        previously specified type (e.g., str, float, etc.), elements
        in *data* are checked to see if they are equal to the given
        object. On failure, an :class:`Invalid` or :class:`Deviation`
        error is raised::

            def test_mydata(self):
                data = ...
                requirement = 'FOO'
                self.assertValid(data, requirement)
        """
        if isinstance(data, DataQuery):          # If data is a DataQuery,
            data = data.execute(evaluate=False)  # lazily evaluate it.

        if isinstance(requirement, DataQuery):     # If requirement is
            requirement = requirement.execute()    # a DataQuery or
        elif isinstance(requirement, DataResult):  # DataResult, we must
            requirement = requirement.evaluate()   # eagerly evaluate it.

        errors = _get_differences(data, requirement)
        if not errors:
            return None  # <- EXIT!

        if not msg and not isinstance(errors, Exception):
            name = getattr(requirement, '__name__',
                           requirement.__class__.__name__)
            msg = 'data does not satisfy {0!r} requirement'.format(name)

        self.fail(msg, errors)

    def fail(self, msg, errors=None):
        if isinstance(errors, Exception):
            if msg:
                args = errors.args
                if isinstance(args[0], str):
                    first_arg = '{0}\n{1}'.format(msg, args[0])
                    args = args[1:]
                else:
                    first_arg = msg
                errors.args = (first_arg,) + args
            raise errors
        elif errors:
            raise ValidationError(msg, errors)
        else:
            raise self.failureException(msg)

    #def assertUnique(self, data, msg=None):
    #    pass

    def allowedMissing(self, msg=None):
        """Allows :class:`Missing` errors without triggering a test
        failure::

            with self.allowedMissing():
                data = {'A', 'B'}  # <- 'C' is missing
                requirement = {'A', 'B', 'C'}
                self.assertValid(data, requirement)
        """
        return allowed_missing(msg)

    def allowedExtra(self, msg=None):
        """Allows :class:`Extra` errors without triggering a test
        failure::

            with self.allowedExtra():
                data = {'A', 'B', 'C', 'D'}  # <- 'D' is extra
                requirement = {'A', 'B', 'C'}
                self.assertValid(data, requirement)
        """
        return allowed_extra(msg)

    def allowedInvalid(self, msg=None):
        """Allows :class:`Invalid` errors without triggering a test
        failure::

            with self.allowedInvalid():
                data = {'x': 'A', 'y': 'E'}  # <- 'E' is invalid
                requirement = {'x': 'A', 'y': 'B'}
                self.assertValid(data, requirement)
        """
        return allowed_invalid(msg)

    def allowedDeviation(self, lower, upper=None, msg=None):
        """
        allowedDeviation(tolerance, /, msg=None)
        allowedDeviation(lower, upper, msg=None)

        See documentation for full details.
        """
        return allowed_deviation(lower, upper, msg)

    def allowedPercentDeviation(self, lower, upper=None, msg=None):
        """
        allowedPercentDeviation(tolerance, /, msg=None)
        allowedPercentDeviation(lower, upper, msg=None)

        See documentation for full details.
        """
        return allowed_percent_deviation(lower, upper, msg)

    def allowedSpecific(self, errors, msg=None):
        """Allows specified *errors* without triggering a test
        failure::

            errors = [
                Missing('C')
                Extra('D'),
            ]
            with self.allowedSpecific(errors):
                data = {'A', 'B', 'D'}  # <- 'D' extra, 'C' missing
                requirement = {'A', 'B', 'C'}
                self.assertValid(data, requirement)

        The *errors* argument can be a :py:obj:`list` or :py:obj:`dict`
        of data errors or a single :class:`DataError`.
        """
        return allowed_specific(errors, msg)

    def allowedKey(self, function, msg=None):
        """Allow errors in a mapping where *function* returns True.
        For each error, *function* will receive the associated
        mapping **key** unpacked into one or more arguments.
        """
        return allowed_key(function, msg)

    def allowedArgs(self, function, msg=None):
        """Allows errors where *function* returns True. For the 'args'
        attribute of each error (a tuple), *function* must accept the
        number of arguments unpacked from 'args'.
        """
        return allowed_args(function, msg)

    def allowedLimit(self, number, msg=None):
        """Allows a limited *number* of data errors (of any type)
        without triggering a test failure::

            with self.allowedLimit(10):  # Allows up to ten errors.
                data = ...
                requirement = ...
                self.assertValid(data, requirement)

        If the count of data errors exceeds the given *number*, the
        test will fail with a :class:`ValidationError` containing all
        observed differences.
        """
        return allowed_limit(number, msg)


# Prettify default signature of methods that accept multiple signatures.
# This only works for Python 3.3 and newer--older versions will simply
# have the original method sigture.
with contextlib.suppress(AttributeError):
    # For DataTestCase.allowedDeviation(), build "tolerance" signature.
    _sig = inspect.signature(DataTestCase.allowedDeviation)
    _self, _lower, _upper, _msg = _sig.parameters.values()
    _self = _self.replace(kind=inspect.Parameter.POSITIONAL_ONLY)
    _tolerance = inspect.Parameter('tolerance', inspect.Parameter.POSITIONAL_ONLY)
    _sig = _sig.replace(parameters=[_self, _tolerance, _msg])
    DataTestCase.allowedDeviation.__signature__ = _sig

    # For DataTestCase.allowedPercentDeviation(), build "tolerance" signature.
    _sig = inspect.signature(DataTestCase.allowedPercentDeviation)
    _self, _lower, _upper, _msg = _sig.parameters.values()
    _self = _self.replace(kind=inspect.Parameter.POSITIONAL_ONLY)
    _tolerance = inspect.Parameter('tolerance', inspect.Parameter.POSITIONAL_ONLY)
    _sig = _sig.replace(parameters=[_self, _tolerance, _msg])
    DataTestCase.allowedPercentDeviation.__signature__ = _sig
