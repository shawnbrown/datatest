# -*- coding: utf-8 -*-
from __future__ import division
import inspect
import re
from unittest import TestCase

from .utils.builtins import *
from .utils import collections
from .utils import itertools

from .compare import CompareSet  # TODO!!!: Remove after assertSubjectColumns fixed!
from .compare import CompareDict  # TODO!!!: Remove after assertSubjectColumns fixed!
from .compare import BaseCompare

from .compare import _compare_mapping
from .compare import _compare_sequence
from .compare import _compare_set
from .compare import _compare_other

from .differences import _make_decimal
from .differences import Extra  # TODO: Move when assertSubjectUnique us moved.
from .differences import Missing  # TODO: Move when assertSubjectUnique us moved.

from .error import DataError
from .sources.base import BaseSource


__datatest = True  # Used to detect in-module stack frames (which are
                   # omitted from output).

_re_type = type(re.compile(''))


from .allow import allow_only
from .allow import allow_any
from .allow import allow_missing
from .allow import allow_extra
from .allow import allow_limit
from .allow import allow_deviation
from .allow import allow_percent_deviation


class DataTestCase(TestCase):
    """This class wraps and extends unittest.TestCase and implements
    additional properties and methods for testing data quality.  In
    addition to the new functionality, familiar methods (like setUp,
    addCleanup, etc.) are still available---see
    :py:class:`unittest.TestCase` for full details.
    """
    @property
    def subject(self):
        """This property contains the data under test---the *subject*
        of the tests.  A subject must be defined to use any of the
        "assertSubject…" methods (e.g., :meth:`assertSubjectColumns`,
        :meth:`assertSubjectSet`, etc.).  It must be a data source
        object.

        A subject can be defined at the class-level or at the
        module-level.  This property will return the :attr:`subject`
        from the nearest enclosed scope.

        Module-level declaration::

            def setUpModule():
                global subject
                subject = datatest.CsvSource('myfile.csv')

        Class-level declaration::

            class TestMyFile(datatest.DataTestCase):
                @classmethod
                def setUpClass(cls):
                    cls.subject = datatest.CsvSource('myfile.csv')
        """
        if hasattr(self, '_subject_data'):
            return self._subject_data
        return self._find_data_source('subject')

    @subject.setter
    def subject(self, value):
        self._subject_data = value

    @property
    def reference(self):
        """This property contains data that is trusted to be correct.
        A reference data source is optional.  It's used by the
        "assertSubject…" methods when their *required* argument is
        omitted.

        A reference can be defined at the class-level or at the
        module-level.  This property will return the :attr:`reference`
        from the nearest enclosed scope.

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

    def _normalize_required(self, required, method, *args, **kwds):
        """If *required* is None, query data from :attr:`reference`; if
        it is another data source, query from this other source; else,
        return unchanged.
        """
        if required == None:
            required = self.reference

        if isinstance(required, BaseSource):
            fn = getattr(required, method)
            required = fn(*args, **kwds)

        return required

    def assertValid(self, data, required=None, msg=None):
        """
        self.assertValid(data, required, msg=None)
        self.assertValid(function, /, msg=None)

        Fail if *data* does not satisfy *required* object as
        determined by an appropriate validation operation.
        """
        # If using *function* signature, normalize arguments and get data.
        if callable(data) and (not required or isinstance(required, str)):
            function, data = data, None         # Shuffle arguments
            if not msg:                         # to fit *function*
                msg, required = required, None  # signature.
            data = function(self.subject)
            required = function(self.reference)

        # Get appropriate comparison function (as determined by
        # *required* argument).
        if isinstance(required, collections.Mapping):
            compare = _compare_mapping
            default_msg = 'data does not match required mapping'
        elif (isinstance(required, collections.Sequence)
                and not isinstance(required, str)):
            compare = _compare_sequence
            default_msg = 'order and values do not match required sequence'
        elif isinstance(required, collections.Set):
            compare = _compare_set
            default_msg = 'data does not match required set'
        else:
            compare = _compare_other
            default_msg = 'data does not satisfy required object'

        # Apply comparison function and fail if there are any differences.
        differences = compare(data, required)
        if differences:
            self.fail(msg or default_msg, differences)

    def assertEqual(self, first, second, msg=None):
        """Fail if *first* does not satisfy *second* as determined by
        appropriate validation comparison.

        If *first* and *second* are comparable, a failure will raise a
        DataError containing the differences between the two::

            def test_column1(self):
                first = self.subject.distinct('col1')
                second = self.reference.distinct('col1')
                self.assertEqual(first, second)

        If the *second* argument is a helper-function (or other
        callable), it is used as a key which must return True for
        acceptable values::

            def test_column1(self):
                compare_obj = self.subject.distinct('col1')
                def uppercase(x):  # <- Helper function.
                    return str(x).isupper()
                self.assertEqual(compare_obj, uppercase)
        """
        if not isinstance(first, BaseCompare):
            if isinstance(first, str) or not isinstance(first, collections.Container):
                first = CompareSet([first])
            elif isinstance(first, collections.Set):
                first = CompareSet(first)
            elif isinstance(first, collections.Mapping):
                first = CompareDict(first)

        if callable(second):
            equal = first.all(second)
            default_msg = 'first object contains invalid items'
        else:
            equal = first == second
            default_msg = 'first object does not match second object'

        if not equal:
            differences = first.compare(second)
            self.fail(msg or default_msg, differences)

    def assertSubjectUnique(self, columns, msg=None, **kwds_filter):
        """Test that values in column or *columns* of :attr:`subject`
        are unique.  Any duplicate values are raised as Extra
        differences.

        .. warning::

            This method is unoptimized---it performs all operations
            in-memory. Avoid using this method on data sets that exceed
            available memory.

        .. todo::

            Optimize for memory usage (see issue #9 in development
            repository). Move functionality into compare.py when
            preparing for better py.test integration.
        """
        if isinstance(columns, str):
            get_value = lambda row: row[columns]
        elif isinstance(columns, collections.Sequence):
            get_value = lambda row: tuple(row[column] for column in columns)
        else:
            raise TypeError('colums must be str or sequence')

        seen_before = set()
        extras = set()
        for row in self.subject.filter_rows(**kwds_filter):
            values =get_value(row)
            if values in seen_before:
                extras.add(values)
            else:
                seen_before.add(values)

        if extras:
            differences = sorted([Extra(x) for x in extras])
            default_msg = 'values in {0!r} are not unique'.format(columns)
            self.fail(msg or default_msg, differences)

    def assertSubjectRegex(self, column, required, msg=None, **kwds_filter):
        """Test that *column* in :attr:`subject` contains values that
        match a *required* regular expression::

            def test_date(self):
                wellformed = r'\d\d\d\d-\d\d-\d\d'  # Matches YYYY-MM-DD.
                self.assertSubjectRegex('date', wellformed)

        The *required* argument must be a string or a compiled regular
        expression object (it can not be omitted).
        """
        subject_result = self.subject.distinct(column, **kwds_filter)
        if not isinstance(required, _re_type):
            required = re.compile(required)
        func = lambda x: required.search(x) is not None
        msg = msg or 'non-matching {0!r} values'.format(column)
        self.assertEqual(subject_result, func, msg)

    def assertSubjectNotRegex(self, column, required, msg=None, **kwds_filter):
        """Test that *column* in :attr:`subject` contains values that
        do **not** match a *required* regular expression::

            def test_name(self):
                bad_whitespace = r'^\s|\s$'  # Leading or trailing whitespace.
                self.assertSubjectNotRegex('name', bad_whitespace)

        The *required* argument must be a string or a compiled regular
        expression object (it can not be omitted).
        """
        subject_result = self.subject.distinct(column, **kwds_filter)
        if not isinstance(required, _re_type):
            required = re.compile(required)
        func = lambda x: required.search(x) is None
        msg = msg or 'matching {0!r} values'.format(column)
        self.assertEqual(subject_result, func, msg)

    def allowOnly(self, differences, msg=None):
        """A convenience wrapper for :class:`allow_only`.

        .. code-block:: python

            differences = [
                Extra('foo'),
                Missing('bar'),
            ]
            with self.allowOnly(differences):
                self.assertSubjectSet('column1')
        """
        return allow_only(differences, msg)

    def allowAny(self, msg=None, **kwds):
        """A convenience wrapper for :class:`allow_any`.

        .. code-block:: python

            with self.allowAny(town='unknown'):
                self.assertSubjectSum('population', ['town'])
        """
        return allow_any(msg, **kwds)

    def allowMissing(self, msg=None, **kwds):
        """A convenience wrapper for :class:`allow_missing`.

        .. code-block:: python

            with self.allowMissing():
                self.assertSubjectSet('column1')
        """
        return allow_missing(msg, **kwds)

    def allowExtra(self, msg=None, **kwds):
        """A convenience wrapper for :class:`allow_extra`.

        .. code-block:: python

            with self.allowExtra():
                self.assertSubjectSet('column1')
        """
        return allow_extra(msg, **kwds)

    def allowLimit(self, number, msg=None, **kwds):
        """A convenience wrapper for :class:`allow_limit`.

        .. code-block:: python

            with self.allowLimit(10):  # Allow up to ten differences.
                self.assertSubjectSet('column1')
        """
        return allow_limit(number, msg, **kwds)

    def allowDeviation(self, lower, upper=None, msg=None, **kwds):
        """
        allowDeviation(tolerance, /, msg=None, **kwds)
        allowDeviation(lower, upper, msg=None, **kwds)

        A convenience wrapper for :class:`allow_deviation`.

        .. code-block:: python

            with self.allowDeviation(5):  # tolerance of +/- 5
                self.assertSubjectSum('column2', keys=['column1'])
        """
        # NOTE: CHANGES TO THE ABOVE DOCSTRING SHOULD BE REPLICATED IN
        # THE DOCUMENTATION (.RST FILE)!  This docstring is not included
        # using the Sphinx "autoclass" directive because there is no way
        # to automatically handle multiple file signatures for Python.
        return allow_deviation(lower, upper, msg, **kwds)

    def allowPercentDeviation(self, lower, upper=None, msg=None, **kwds):
        """
        allowPercentDeviation(tolerance, /, msg=None, **kwds)
        allowPercentDeviation(lower, upper, msg=None, **kwds)

        A convenience wrapper for :class:`allow_percent_deviation`.

        .. code-block:: python

            with self.allowPercentDeviation(0.02):  # tolerance of +/- 2%
                self.assertSubjectSum('column2', keys=['column1'])
        """
        # NOTE: CHANGES TO THE ABOVE DOCSTRING SHOULD BE REPLICATED IN
        # THE DOCUMENTATION (.RST FILE)!  This docstring is not included
        # using the Sphinx "autoclass" directive because there is no way
        # to automatically handle multiple file signatures for Python.
        return allow_percent_deviation(lower, upper, msg, **kwds)

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
