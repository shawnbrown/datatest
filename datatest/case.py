# -*- coding: utf-8 -*-
from __future__ import division
import inspect
from unittest import TestCase

from .utils.builtins import *
from .utils import collections

from .dataaccess.source import DataQuery
from .dataaccess.source import DataResult

from .compare import _compare_mapping
from .compare import _compare_sequence
from .compare import _compare_set
from .compare import _compare_other

from .error import DataError

__datatest = True  # Used to detect in-module stack frames (which are
                   # omitted from output).

from .allow import allow_any
from .allow import allow_missing
from .allow import allow_extra
from .allow import allow_deviation
from .allow import allow_percent_deviation
from .allow import allow_limit
from .allow import allow_only


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

    def assertValid(self, data, requirement=None, msg=None):
        """Fail if the *data* under test does not satisfy the
        *requirement*.

        The given *data* can be a set, sequence, iterable, mapping,
        or other object. The *requirement* type determines how the
        data is validated.

        **Set membership:** When *requirement* is a set, elements
        in *data* are checked for membership in this set. On failure,
        :class:`Missing` or :class:`Extra` errors are raised::

            def test_mydata(self):
                data = ...
                requirement = {'A', 'B', 'C', ...}  # <- set
                self.assertValid(data, requirement)

        **Regular expression match:** When *requirement* is a regular
        expression, elements in *data* are checked to see if they match
        the given pattern. On failure, :class:`Invalid` errors are
        raised::

            def test_mydata(self):
                data = ...
                requirement = re.compile(r'^[ ]+|[ ]$')  # <- regex
                self.assertValid(data, requirement)

        **Sequence order:** When *requirement* is a list or other
        sequence, elements in *data* are checked for matching order and
        value::

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
        # TODO: "If the function raises or returns an error derived
        #        from :class:`DataError`, this error is used instead"

        # TODO: Sequence order:
        #       "On failure, an :py:class:`AssertionError` is raised"

        # Evaluate query and result objects.
        if isinstance(data, DataQuery):
            data = data.execute()
        elif isinstance(data, DataResult):
            data = data.evaluate()

        if isinstance(requirement, DataQuery):
            requirement = requirement.execute()
        elif isinstance(requirement, DataResult):
            requirement = requirement.evaluate()

        # If using *function* signature, normalize arguments and get data.
        if callable(data) and (not requirement or isinstance(requirement, str)):
            function, data = data, None         # Shuffle arguments
            if not msg:                         # to fit *function*
                msg, requirement = requirement, None  # signature.
            data = function(self.subject)
            requirement = function(self.reference)

        # Get appropriate comparison function (as determined by
        # *requirement*).
        if isinstance(requirement, collections.Mapping):
            compare = _compare_mapping
            default_msg = 'data does not match mapping requirement'
        elif (isinstance(requirement, collections.Sequence)
                and not isinstance(requirement, str)):
            compare = _compare_sequence
            default_msg = 'order and values do not match sequence requirement'
        elif isinstance(requirement, collections.Set):
            compare = _compare_set
            default_msg = 'data does not match set requirement'
        else:
            compare = _compare_other
            default_msg = 'data does not satisfy object requirement'

        # Apply comparison function and fail if there are any differences.
        differences = compare(data, requirement)
        if differences:
            self.fail(msg or default_msg, differences)

    #def assertUnique(self, data, msg=None):
    #    pass

    def allowOnly(self, differences, msg=None):
        """Context manager to allow specified *differences* without
        triggering a test failure::

            differences = [
                Extra('X'),
                Missing('Y')
            ]
            with self.allowOnly(differences):
                data = ...
                requirement = ...
                self.assertValid(data, requirement)

        The *differences* argument can be a :py:obj:`list` or
        :py:obj:`dict` of differences or a single difference.
        """
        #return allow_only(differences, msg)
        return allow_only(differences)

    def allowAny(self, msg=None, **kwds_func):
        """Allows differences that match given keyword functions
        without triggering a test failure::

            def is_unknown(x):
                return x == 'unknown'

            with self.allowAny(keys=is_unknown):
                data = ...
                required = ...
                self.assertValid(data, requirement)
        """
        #return allow_any(msg, **kwds_func)
        return allow_any(**kwds_func)

    def allowMissing(self, msg=None, **kwds_func):
        """Allows :class:`Missing` values without triggering a test
        failure::

            with self.allowMissing():
                data = ...
                requirement = ...
                self.assertValid(data, requirement)
        """
        return allow_missing(**kwds_func)
        #return allow_missing(msg, **kwds_func)

    def allowExtra(self, msg=None, **kwds_func):
        """Allows :class:`Extra` values without triggering a test
        failure::

            with self.allowExtra():
                data = ...
                requirement = ...
                self.assertValid(data, requirement)
        """
        return allow_extra(**kwds_func)
        #return allow_extra(msg, **kwds_func)

    def allowLimit(self, number, msg=None, **kwds_func):
        """Context manager to allow a limited *number* of differences
        (of any type) without triggering a test failure::

            with self.allowLimit(10):  # Allow up to ten differences.
                data = ...
                requirement = ...
                self.assertValid(data, requirement)

        If the count of differences exceeds the given *number*, the test
        will fail with a :class:`DataError` containing all observed
        differences.
        """
        return allow_limit(number, **kwds_func)
        #return allow_limit(number, msg, **kwds_func)

    def allowDeviation(self, lower, upper=None, msg=None, **kwds_func):
        """
        allowDeviation(tolerance, /, msg=None, **kwds_func)
        allowDeviation(lower, upper, msg=None, **kwds_func)

        See documentation for full details.
        """
        return allow_deviation(lower, upper, **kwds_func)
        #return allow_deviation(lower, upper, msg, **kwds_func)

    def allowPercentDeviation(self, lower, upper=None, msg=None, **kwds_func):
        """
        allowPercentDeviation(tolerance, /, msg=None, **kwds_func)
        allowPercentDeviation(lower, upper, msg=None, **kwds_func)

        See documentation for full details.
        """
        return allow_percent_deviation(lower, upper, **kwds_func)
        #return allow_percent_deviation(lower, upper, msg, **kwds_func)

    def fail(self, msg, differences=None):
        """Signals a test failure unconditionally, with *msg* for the
        error message.  If *differences* is provided, a
        :class:`DataError` is raised instead of an AssertionError.
        """
        if differences:
            try:
                subject = self.subject
            except NameError:
                subject = None
            try:
                required = self.reference
            except NameError:
                required = None
            raise DataError(msg, differences, subject, required)
        else:
            raise self.failureException(msg)


# Prettify default signature of methods that accept multiple signatures.
try:
    # For DataTestCase.assertValid(), remove default parameter.
    _sig = inspect.signature(DataTestCase.assertValid)
    _self, _data, _required, _msg = _sig.parameters.values()
    _required = _required.replace(default=inspect.Parameter.empty)
    _sig = _sig.replace(parameters=[_self, _data, _required, _msg])
    DataTestCase.assertValid.__signature__ = _sig

    # For DataTestCase.allowDeviation(), build "tolerance" signature.
    _sig = inspect.signature(DataTestCase.allowDeviation)
    _self, _lower, _upper, _msg, _kwds_filter = _sig.parameters.values()
    _self = _self.replace(kind=inspect.Parameter.POSITIONAL_ONLY)
    _tolerance = inspect.Parameter('tolerance', inspect.Parameter.POSITIONAL_ONLY)
    _sig = _sig.replace(parameters=[_self, _tolerance, _msg, _kwds_filter])
    DataTestCase.allowDeviation.__signature__ = _sig

    # For DataTestCase.allowPercentDeviation(), build "tolerance" signature.
    _sig = inspect.signature(DataTestCase.allowPercentDeviation)
    _self, _lower, _upper, _msg, _kwds_filter = _sig.parameters.values()
    _self = _self.replace(kind=inspect.Parameter.POSITIONAL_ONLY)
    _tolerance = inspect.Parameter('tolerance', inspect.Parameter.POSITIONAL_ONLY)
    _sig = _sig.replace(parameters=[_self, _tolerance, _msg, _kwds_filter])
    DataTestCase.allowPercentDeviation.__signature__ = _sig
except AttributeError:  # Fails for Python 3.2 and earlier.
    pass
