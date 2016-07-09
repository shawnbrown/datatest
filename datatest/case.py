# -*- coding: utf-8 -*-
from __future__ import division
import inspect
import re
from unittest import TestCase

from .utils.builtins import *
from .utils import collections

from .compare import CompareSet  # TODO!!!: Remove after assertSubjectColumns fixed!
from .compare import BaseCompare
from .differences import _make_decimal
from .differences import Extra  # TODO: Move when assertSubjectUnique us moved.
from .error import DataError
from .sources.base import BaseSource


__datatest = True  # Used to detect in-module stack frames (which are
                   # omitted from output).

_re_type = type(re.compile(''))


from .allow import _walk_diff
from .allow import _BaseAllowance

from .allow import _AllowOnly
from .allow import _AllowAny
from .allow import _AllowMissing
from .allow import _AllowExtra
from .allow import _AllowDeviation
from .allow import _AllowPercentDeviation


class DataTestCase(TestCase):
    """This class wraps and extends unittest.TestCase and implements
    additional properties and methods for testing data quality.  When a
    data assertion fails, it raises a :class:`DataError` which contains
    a list of detected errors.

    In addition to the new functionality, the familiar TestCase methods
    (like setUp, assertEqual, etc.) are still available.
    """
    @property
    def subject(self):
        """A data source containing the data under test---the *subject*
        of the tests.  A :attr:`subject` can be defined at the
        class-level or at the module-level.

        When defining :attr:`subject` at the module-level, this property
        will reach into its parent scopes and return the :attr:`subject`
        from the nearest enclosed scope::

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
        """An optional data source containing data that is trusted to
        be correct.  A :attr:`reference` can be defined at the
        class-level or at the module-level.  This property will return
        the :attr:`reference` from the nearest enclosed scope.

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

    def assertEqual(self, first, second, msg=None):
        """Fail if the two objects are unequal as determined by the '=='
        operator.

        If the *first* argument is a datatest comparison object
        (:class:`CompareSet`, :class:`CompareDict`, etc.), a failure
        will raise the differences between *first* and *second*::

            def test_column1(self):
                first = self.subject.set('col1')     # The set() method
                second = self.reference.set('col1')  # returns a CompareSet.
                self.assertEqual(first, second)

        If the *second* argument is a helper-function (or other
        callable), it is used as a key which must return True for
        acceptable values::

            def test_column1(self):
                compare_obj = self.subject.set('col1')
                def length_of_one(x):  # <- Helper function.
                    return len(str(x)) == 1
                self.assertEqual(compare_obj, length_of_one)
        """
        if isinstance(first, BaseCompare):
            if callable(second):
                equal = first.all(second)
                default_msg = 'first object contains invalid items'
            else:
                equal = first == second
                default_msg = 'first object does not match second object'

            if not equal:
                differences = first.compare(second)
                self.fail(msg or default_msg, differences)

        else:
            super(DataTestCase, self).assertEqual(first, second, msg)
            # Called super() using older convention for 2.x support.

    def assertSubjectColumns(self, required=None, msg=None):
        """Test that the column names of :attr:`subject` match the
        *required* values.  The *required* argument can be a collection,
        callable, data source, or None::

            def test_columns(self):
                required_names = {'col1', 'col2'}
                self.assertSubjectColumns(required_names)

        If *required* is omitted, the column names from
        :attr:`reference` are used in its place::

            def test_columns(self):
                self.assertSubjectColumns()
        """
        # TODO: Explore the idea of implementing CompareList to assert
        # column order.
        subject_set = CompareSet(self.subject.columns())
        required = self._normalize_required(required, 'columns')
        msg = msg or 'different column names'
        self.assertEqual(subject_set, required, msg)

    def assertSubjectSet(self, columns, required=None, msg=None, **kwds_filter):
        """Test that the column or *columns* in :attr:`subject` contain
        the *required* values::

            def test_column1(self):
                required_values = {'a', 'b'}
                self.assertSubjectSet('col1', required_values)

        If *columns* is a sequence of strings, we can check for distinct
        groups of values::

            def test_column1and2(self):
                required_groups = {('a', 'x'), ('a', 'y'), ('b', 'x'), ('b', 'y')}
                self.assertSubjectSet(['col1', 'col2'], required_groups)

        If the *required* argument is a helper-function (or other
        callable), it is used as a key which must return True for
        acceptable values::

            def test_column1(self):
                def length_of_one(x):  # <- Helper function.
                    return len(str(x)) == 1
                self.assertSubjectSet('col1', length_of_one)

        If the *required* argument is omitted, then values from
        :attr:`reference` will be used in its place::

            def test_column1(self):
                self.assertSubjectSet('col1')

            def test_column1and2(self):
                self.assertSubjectSet(['col1', 'col2'])
        """
        subject_set = self.subject.distinct(columns, **kwds_filter)
        required = self._normalize_required(required, 'distinct', columns, **kwds_filter)
        msg = msg or 'different {0!r} values'.format(columns)
        self.assertEqual(subject_set, required, msg)

    def assertSubjectSum(self, column, keys, required=None, msg=None, **kwds_filter):
        """Test that the sum of *column* in :attr:`subject`, when
        grouped by *keys*, matches a dict of *required* values::

            per_dept = {'finance': 146564,
                        'marketing': 152530,
                        'research': 158397}
            self.assertSubjectSum('budget', 'department', per_dept)

        Grouping by multiple *keys*::

            dept_quarter = {('finance', 'q1'): 85008,
                            ('finance', 'q2'): 61556,
                            ('marketing', 'q1'): 86941,
                            ('marketing', 'q2'): 65589,
                            ('research', 'q1'): 93454,
                            ('research', 'q2'): 64943}
            self.assertSubjectSum('budget', ['department', 'quarter'], dept_quarter)

        If *required* argument is omitted, then values from
        :attr:`reference` are used in its place::

            self.assertSubjectSum('budget', ['department', 'quarter'])
        """
        subject_dict = self.subject.sum(column, keys, **kwds_filter)
        required = self._normalize_required(required, 'sum', column, keys, **kwds_filter)
        msg = msg or 'different {0!r} sums'.format(column)
        self.assertEqual(subject_dict, required, msg)

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
        """Context manager to allow specific *differences* without
        triggering a test failure::

            differences = [
                Extra('foo'),
                Missing('bar'),
            ]
            with self.allowOnly(differences):
                self.assertSubjectSet('column1')

        If the raised differences do not match *differences*, the test
        will fail with a :class:`DataError` of the remaining
        differences.

        In the above example, *differences* is a list but it is also
        possible to pass a single difference or a dictionary.

        Using a single difference::

            with self.allowOnly(Extra('foo')):
                self.assertSubjectSet('column2')

        When using a dictionary, the keys are strings that provide
        context (for future reference and derived reports) and the
        values are the individual difference objects themselves::

            differences = {
                'Totals from state do not match totals from county.': [
                    Deviation(+436, 38032, town='Springfield'),
                    Deviation(-83, 8631, town='Union')
                ],
                'Some small towns were omitted from county report.': [
                    Deviation(-102, 102, town='Anderson'),
                    Deviation(-177, 177, town='Westfield')
                ]
            }
            with self.allowOnly(differences):
                self.assertSubjectSum('population', ['town'])
        """
        return _AllowOnly(differences, self, msg)

    def allowAny(self, number=None, msg=None, **kwds_filter):
        """Allows a given *number* of differences (of any kind) without
        triggering a test failure::

            with self.allowAny(10):  # Allows up to ten differences.
                self.assertSubjectSet('city_name')

        If *number* is omitted, allows an unlimited number of
        differences as long as they match a given keyword filter::

            with self.allowAny(city_name='not a city'):
                self.assertSubjectSum('population', ['city_name'])

        If the count of differences exceeds the given *number*, the
        test case will fail with a :class:`DataError` containing all
        observed differences.
        """
        return _AllowAny(self, number, msg, **kwds_filter)

    def allowMissing(self, number=None, msg=None):
        """Context manager to allow for missing values without
        triggering a test failure::

            with self.allowMissing():  # Allows Missing differences.
                self.assertSubjectSet('column1')
        """
        return _AllowMissing(self, number, msg)

    def allowExtra(self, number=None, msg=None):
        """Context manager to allow for extra values without triggering
        a test failure::

            with self.allowExtra():  # Allows Extra differences.
                self.assertSubjectSet('column1')
        """
        return _AllowExtra(self, number, msg)

    def allowDeviation(self, lower, upper=None, msg=None, **kwds_filter):
        """
        allowDeviation(tolerance, /, msg=None, **kwds_filter)
        allowDeviation(lower, upper, msg=None, **kwds_filter)

        Context manager to allow for deviations from required
        numeric values without triggering a test failure.

        Allowing deviations of plus-or-minus a given *tolerance*::

            with self.allowDeviation(5):  # tolerance of +/- 5
                self.assertSubjectSum('column2', keys=['column1'])

        Specifying different *lower* and *upper* bounds::

            with self.allowDeviation(-2, 3):  # tolerance from -2 to +3
                self.assertSubjectSum('column2', keys=['column1'])

        All deviations within the accepted tolerance range are
        suppressed but those that exceed the range will trigger
        a test failure.
        """
        if msg == None and isinstance(upper, str):
            msg = upper   # Adjust positional 'msg' for "tolerance" syntax.
            upper = None

        if upper == None:
            tolerance = lower
            assert tolerance >= 0, ('tolerance should not be negative, '
                                    'for full control of lower and upper '
                                    'bounds, use "lower, upper" syntax.')
            lower, upper = -tolerance, tolerance

        assert lower <= upper
        return _AllowDeviation(lower, upper, self, msg, **kwds_filter)

    def allowPercentDeviation(self, lower, upper=None, msg=None, **kwds_filter):
        """
        allowPercentDeviation(tolerance, /, msg=None, **kwds_filter)
        allowPercentDeviation(lower, upper, msg=None, **kwds_filter)

        Context manager to allow for deviations from required numeric
        values within a given error percentage without triggering a test
        failure.

        Allowing deviations of plus-or-minus a given *tolerance*::

            with self.allowDeviation(0.02):  # tolerance of +/- 2%
                self.assertSubjectSum('column2', keys=['column1'])

        Specifying different *lower* and *upper* bounds::

            with self.allowDeviation(-0.02, 0.03):  # tolerance from -2% to +3%
                self.assertSubjectSum('column2', keys=['column1'])

        All deviations within the accepted tolerance range are
        suppressed but those that exceed the range will trigger a test
        failure.
        """
        if msg == None and isinstance(upper, str):
            msg = upper   # Adjust positional 'msg' for "tolerance" syntax.
            upper = None

        if upper == None:
            tolerance = lower
            assert tolerance >= 0, ('tolerance should not be negative, '
                                    'for full control of lower and upper '
                                    'bounds, use "lower, upper" syntax.')
            lower, upper = -tolerance, tolerance

        assert lower <= upper
        return _AllowPercentDeviation(lower, upper, self, msg, **kwds_filter)

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


# Prettify signature of allowDeviation() and allowPercentDeviation() by
# making the "tolerance" syntax the default option when introspected.
try:
    # DataTestCase.allowDeviation():
    _sig = inspect.signature(DataTestCase.allowDeviation)
    _self, _lower, _upper, _msg, _kwds_filter = _sig.parameters.values()
    _self = _self.replace(kind=inspect.Parameter.POSITIONAL_ONLY)
    _tolerance = inspect.Parameter('tolerance', inspect.Parameter.POSITIONAL_ONLY)
    _sig = _sig.replace(parameters=[_self, _tolerance, _msg, _kwds_filter])
    DataTestCase.allowDeviation.__signature__ = _sig
    # DataTestCase.allowPercentDeviation():
    _sig = inspect.signature(DataTestCase.allowPercentDeviation)
    _self, _lower, _upper, _msg, _kwds_filter = _sig.parameters.values()
    _self = _self.replace(kind=inspect.Parameter.POSITIONAL_ONLY)
    _tolerance = inspect.Parameter('tolerance', inspect.Parameter.POSITIONAL_ONLY)
    _sig = _sig.replace(parameters=[_self, _tolerance, _msg, _kwds_filter])
    DataTestCase.allowPercentDeviation.__signature__ = _sig
except AttributeError:  # Fails for Python 3.2 and earlier.
    pass
