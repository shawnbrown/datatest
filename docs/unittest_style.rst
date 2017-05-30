
.. module:: datatest

.. meta::
    :description: datatest API for unittest-style testing
    :keywords: datatest, unittest, data wrangling


##################
Unittest-Style API
##################


*************
Basic Example
*************

.. code-block:: python

    import datatest

    class TestMyData(datatest.DataTestCase):
        @classmethod
        def setUpClass(cls):
            data = [
                {'is_active': 'Y', 'member_id': 105},
                {'is_active': 'Y', 'member_id': 104},
                {'is_active': 'Y', 'member_id': 103},
                {'is_active': 'N', 'member_id': 102},
                {'is_active': 'N', 'member_id': 101},
                {'is_active': 'N', 'member_id': 100},
            ]
            cls.source = datatest.DataSource(data)

        def test_is_active(self):
            allowed_values = {'Y', 'N'}
            self.assertValid(self.source('is_active'), allowed_values)

        def test_member_id(self):
            def positive_integer(x):  # <- Helper function.
                return isinstance(x, int) and x > 0
            self.assertValid(self.source('member_id'), positive_integer)

    if __name__ == '__main__':
        datatest.main()


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

The syntax and command-line options (``-f``, ``-v``, etc.) are the same
as unittest---see the
`unittest documentation <http://docs.python.org/library/unittest.html#command-line-interface>`_
for full details.

.. note::

    Unlike unittest, datatest's default behavior runs test cases and
    methods **in order** (ordered first by module name and then by
    line number).


************
DataTestCase
************

.. autoclass:: DataTestCase

    .. automethod:: assertValid

    .. automethod:: allowedMissing

    .. automethod:: allowedExtra

    .. automethod:: allowedInvalid

    .. method:: allowedDeviation(tolerance, /, msg=None)
                allowedDeviation(lower, upper, msg=None)

        Allows numeric :class:`Deviations <datatest.Deviation>`
        within a given *tolerance* without triggering a test
        failure::

            with self.allowedDeviation(5):  # tolerance of +/- 5
                data = ...
                requirement = ...
                self.assertValid(data, requirement)

        Specifying different *lower* and *upper* bounds::

            with self.allowedDeviation(-2, 3):  # tolerance from -2 to +3
                data = ...
                requirement = ...
                self.assertValid(data, requirement)

        Deviations within the given range are suppressed while those
        outside the range will trigger a test failure.

        Empty values (None, empty string, etc.) are treated as zeros
        when performing comparisons.

    .. method:: allowedPercentDeviation(tolerance, /, msg=None)
                allowedPercentDeviation(lower, upper, msg=None)

        Allows :class:`Deviations <datatest.Deviation>` with
        percentages of error within a given *tolerance* without
        triggering a test failure::

            with self.allowedPercentDeviation(0.03):  # tolerance of +/- 3%
                data = ...
                requirement = ...
                self.assertValid(data, requirement)

        Specifying different *lower* and *upper* bounds::

            with self.allowedPercentDeviation(-0.02, 0.01):  # tolerance from -2% to +1%
                data = ...
                requirement = ...
                self.assertValid(data, requirement)

        Deviations within the given range are suppressed while those
        outside the range will trigger a test failure.

        Empty values (None, empty string, etc.) are treated as zeros
        when performing comparisons.

    .. automethod:: allowedSpecific

    .. automethod:: allowedKey

    .. automethod:: allowedArgs

    .. automethod:: allowedLimit

    .. note::
        In the deviation methods above, *tolerance* is a positional-only
        parameter---it cannot be specified using keyword syntax.


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
