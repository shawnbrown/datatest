
.. module:: datatest

.. meta::
    :description: datatest API for unittest-style testing
    :keywords: datatest, unittest, data-wrangling


################
Unittest Support
################


*************
Basic Example
*************

This short example demonstrates unittest-style testing of data in
a CSV file (:download:`mydata.csv </_static/mydata.csv>`):

.. code-block:: python

    import datatest


    def setUpModule():
        global select
        with datatest.working_directory(__file__):
            select = datatest.Select('mydata.csv')


    class TestMyData(datatest.DataTestCase):
        def test_header(self):
            fieldnames = select.fieldnames
            required_names = ['user_id', 'active']
            self.assertValid(fieldnames, required_names)

        def test_active_column(self):
            active = select({'active'})
            expected_values = {'Y', 'N'}
            self.assertValid(active, expected_values)

        def test_user_id_column(self):
            user_id = select(['user_id'])
            def positive_int(x):  # <- Helper function.
                return int(x) > 0
            self.assertValid(user_id, positive_int)


    if __name__ == '__main__':
        datatest.main()


A data test-case is created by subclassing
:class:`datatest.DataTestCase` and individual
tests are defined with methods whose names
start with "``test``".

Inside each method, a call to :meth:`self.assertValid()
<DataTestCase.assertValid>` checks that the data satisfies
a given requirement.


.. _unittest-style-invocation:

**********************
Command-Line Interface
**********************

The datatest module can be used from the command line just like
unittest. To run the program with `test discovery
<http://docs.python.org/library/unittest.html#test-discovery>`_
use the following command::

    python -m datatest

Run tests from specific modules, classes, or individual methods with::

    python -m datatest test_module1 test_module2
    python -m datatest test_module.TestClass
    python -m datatest test_module.TestClass.test_method

The syntax and command-line options (``-f``, ``-v``, etc.) are the
same as unittest---see unittest's `command-line documentation
<http://docs.python.org/library/unittest.html#command-line-interface>`_
for full details.

.. note::

    Tests are ordered by **file name** and then by **line number**
    (within each file) when running datatest from the command-line.

..
    Unlike strict unit testing, data preparation tests are often
    dependant on one another---this strict order-by-line-number
    behavior lets users design test suites appropriately.
    For example, asserting the population of a city will always
    fail when the 'city' column is missing. So it's appropriate
    to validate column names *before* validating the contents of
    each column.


************
DataTestCase
************

.. autoclass:: DataTestCase

    .. automethod:: assertValid

    .. automethod:: assertValidPredicate

    .. automethod:: assertValidApprox

    .. automethod:: assertValidFuzzy

    .. automethod:: assertValidInterval

    .. automethod:: assertValidSet

    .. automethod:: assertValidSubset

    .. automethod:: assertValidSuperset

    .. automethod:: assertValidUnique

    .. automethod:: assertValidOrder

    .. attribute:: maxDiff

        This attribute controls the maximum length of diffs output by
        assert methods that report diffs on failure. It defaults to
        80*8 characters.

        Setting ``maxDiff`` to ``None`` means that there is no maximum
        length for diffs::

            self.maxDiff = None

        This attribute affects :meth:`assertValid()` as well as any
        inherited methods like assertSequenceEqual(), assertDictEqual()
        and assertMultiLineEqual().

    .. automethod:: accepted

    .. automethod:: acceptedKeys

    .. automethod:: acceptedArgs

    .. method:: acceptedTolerance(tolerance, /, msg=None)
                acceptedTolerance(lower, upper, msg=None)

        Accepts numeric :class:`Deviations <datatest.Deviation>`
        within a given *tolerance* without triggering a test
        failure::

            with self.acceptedTolerance(5):  # tolerance of +/- 5
                data = ...
                requirement = ...
                self.assertValid(data, requirement)

        Specifying different *lower* and *upper* bounds::

            with self.acceptedTolerance(-2, 3):  # tolerance from -2 to +3
                data = ...
                requirement = ...
                self.assertValid(data, requirement)

        Deviations within the given range are suppressed while those
        outside the range will trigger a test failure.

        Empty values (None, empty string, etc.) are treated as zeros
        when performing comparisons.

    .. method:: acceptedPercent(tolerance, /, msg=None)
                acceptedPercent(lower, upper, msg=None)

        Accepts :class:`Deviations <datatest.Deviation>` with
        percentages of error within a given *tolerance* without
        triggering a test failure::

            with self.acceptedPercent(0.03):  # tolerance of +/- 3%
                data = ...
                requirement = ...
                self.assertValid(data, requirement)

        Specifying different *lower* and *upper* bounds::

            with self.acceptedPercent(-0.02, 0.01):  # tolerance from -2% to +1%
                data = ...
                requirement = ...
                self.assertValid(data, requirement)

        Deviations within the given range are suppressed while those
        outside the range will trigger a test failure.

        Empty values (None, empty string, etc.) are treated as zeros
        when performing comparisons.

    .. automethod:: acceptedFuzzy

    .. automethod:: acceptedCount


*******************
Test Runner Program
*******************

.. py:decorator:: mandatory

    A decorator to mark whole test cases or individual methods as
    mandatory.  If a mandatory test fails, DataTestRunner will stop
    immediately (this is similar to the ``--failfast`` command line
    argument behavior)::

        @datatest.mandatory
        class TestFileFormat(datatest.DataTestCase):
            def test_columns(self):
                ...

.. py:decorator:: skip(reason)

    A decorator to unconditionally skip a test::

        @datatest.skip('Not finished collecting raw data.')
        class TestSumTotals(datatest.DataTestCase):
            def test_totals(self):
                ...

.. py:decorator:: skipIf(condition, reason)

    A decorator to skip a test if the condition is true.

.. py:decorator:: skipUnless(condition, reason)

    A decorator to skip a test unless the condition is true.

.. autoclass:: DataTestRunner
    :members:
    :inherited-members:

.. autoclass:: DataTestProgram(module='__main__', defaultTest=None, argv=None, testRunner=datatest.DataTestRunner, testLoader=unittest.TestLoader, exit=True, verbosity=1, failfast=None, catchbreak=None, buffer=None, warnings=None)
    :members:
    :inherited-members:

|

.. autoclass:: main
   :members:
   :inherited-members:
