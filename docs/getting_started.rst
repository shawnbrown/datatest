
***************
Getting Started
***************

:mod:`datatest` is designed to work with tabular data stored in
spreadsheet files or database tables but it's also possible to create
custom data sources for other formats.  To use datatest effectively,
users should be familiar with Python's standard
`unittest <http://docs.python.org/library/unittest.html>`_ package and
the data they want to audit.


Basic Example
=============

As an example, assume we want to audit the data in the following CSV
file (**members.csv**):

    =========  ======  =========  =================
    member_id  active  region     hours_volunteered
    =========  ======  =========  =================
    999        Y       Midwest    6
    1000       Y       South      2
    1001       N       Northeast  0
    ...        ...     ...        ...
    =========  ======  =========  =================

We want to test that...

 * expected column names are present
 * **member_id** and **hours_volunteered** columns contain only numbers
 * **active** column contains only "Y" or "N" values
 * **region** column contains only valid region codes

The following script implements these tests::

    import datatest


    def setUpModule():
        global subjectData
        subjectData = datatest.CsvSource('members.csv')


    class TestFormatAndLabels(datatest.DataTestCase):
        def test_columns(self):
            """Test for required column names."""
            columns = {'member_id', 'region', 'active', 'hours_volunteered'}
            self.assertColumnSet(columns)

        def test_numeric(self):
            """Test that numeric columns contain only digits."""
            only_digits = '^\d+$'  # Regex pattern.
            self.assertValueRegex('member_id', only_digits)
            self.assertValueRegex('hours_volunteered', only_digits)

        def test_active_labels(self):
            """Test that 'active' column contains valid codes."""
            self.assertValueSubset('active', {'Y', 'N'})

        def test_region_labels(self):
            """Test that 'region' column contains valid codes."""
            regions = {'Midwest', 'Northeast', 'South', 'West'}
            self.assertValueSubset('region', regions)


    if __name__ == '__main__':
        datatest.main()


.. note::

    This example uses a :class:`CsvSource <datatest.CsvSource>` to access data
    from a CSV file.  Other data sources can access data in a variety of
    formats (Excel, pandas, SQL, etc.).


Subject Data (Data Under Test)
==============================

The data under test---the *subject* of our tests---is stored in a property
named ``subjectData``.  This property is accessed, internally, by the
``assertValue...()`` and ``assertColumn...()`` methods.

``subjectData`` is typically defined at the module-level inside a
``setUpModule()`` function---as shown in the first example.  However, if
it is only referenced within a single class, then defining it inside a
``setUpClass()`` method is also acceptable::

    import datatest


    class TestFormatAndLabels(datatest.DataTestCase):
        @classmethod
        def setUpClass(cls):
            cls.subjectData = datatest.CsvSource('members.csv')

        def test_columns(self):
            ...


Reference Data
==============

Datatest also supports the use of reference data from external sources
(files or databases).  While the tests in our first example include
their required values directly in the methods themselves, doing so
becomes inconvenient when working with larger amounts of reference data.

To continue testing the data from our first example, we can use the
following table as reference data (**regional_report.csv**):

    =========  ==============  ==================
    region     active_members   hours_volunteered
    =========  ==============  ==================
    Midwest    39              97
    Northeast  23              59
    South      14              32
    West       33              76
    =========  ==============  ==================

By loading this data into a variable named ``referenceData``, we can
easily integrate it into a test script::

    import datatest


    def setUpModule():
        global subjectData
        global referenceData
        subjectData = datatest.CsvSource('members.csv')
        referenceData = datatest.CsvSource('regional_report.csv')


    class TestLabels(datatest.DataTestCase):
        def test_region_labels(self):
            """Check that subject values equal reference values in
               the 'region' column."""
            self.assertValueSet('region')


    class TestTotals(datatest.DataTestCase):
        def test_hours(self):
            """Check that the sum of subject values equals the sum of
               reference values in the 'hours_volunteered' column for
               each 'region' group."""
            self.assertValueSum('hours_volunteered', ['region'])

        def test_active(self):
            """Check that the count of subject rows equals the total
               reference value in the 'active_members' column for rows
               where 'active' equals 'Y' for each 'region' group."""
            self.assertValueCount('active_members', ['region'], active='Y')


The tests in the above example automatically use the ``subjectData``
and ``referenceData`` sources defined in the ``setUpModule()`` function.


Understanding Errors
====================

When data errors are found, tests will fail with a
:class:`DataAssertionError <datatest.DataAssertionError>` that contains
a list of detected differences::

    Traceback (most recent call last):
      File "test_members.py", line 15, in test_region_labels
        self.assertValueSet('region')
    datatest.case.DataAssertionError: different 'region' values:
     ExtraItem('North-east'),
     MissingItem('Northeast')

This error tells us that values in the "region" column of our
``subjectData`` do not match the values of our ``referenceData``.  The
``subjectData`` contains the extra value "North-east" (which is not
included in the ``referenceData``) and it's missing the value
"Northeast" (which *is* included in the ``referenceData``).

Pairs of conspicuous differences, as shown above, are common when the
subject and reference files use differing codes.  Replacing "North-east"
with "Northeast" in the ``subjectData`` will correct this error and
allow the test to pass.


.. note::

    If a non-data failure occurs (like a syntax error or a standard
    unittest failure), then a standard :class:`AssertionError` is raised
    rather than a :class:`DataAssertionError
    <datatest.DataAssertionError>`.


Allowed Error
=============

Sometimes differences cannot be reconciled---they could represent a
disagreement between two authoritative sources or a lack of information could
make correction impossible.  In any case, there are situations where it is
legitimate to allow certain discrepancies for the purposes of data processing.

In the following example, there are two discrepancies (eight more in
Warren County and 25 less in Lake County)::

    Traceback (most recent call last):
      File "test_survey.py", line 35, in test_population
        self.assertValueSum('population', ['county'])
    datatest.case.DataAssertionError: different 'population' values:
     InvalidNumber(-25, 3184, county='Lake'),
     InvalidNumber(+8, 11771, county='Warren')

If we've determined that these differences are allowable, we can use
the :meth:`allowSpecified
<datatest.DataTestCase.allowSpecified>` context manager so the
test runs without failing::

    def test_population(self):
        diff = [
            InvalidNumber(-25, 3184, county='Lake'),
            InvalidNumber(+8, 11771, county='Warren'),
        ]
        with self.allowSpecified(diff):
            self.assertValueSum('population', ['county'])

To allow several numeric differences at once, you can use the
:meth:`allowDeviation <datatest.DataTestCase.allowDeviation>`
or :meth:`allowPercentDeviation
<datatest.DataTestCase.allowPercentDeviation>` methods::

    def test_households(self):
        with self.allowDeviation(25):
            self.assertValueCount('population', ['county'])


Command-Line Interface
======================

The datatest module can be used from the command line just like
unittest. To run the program with :ref:`test discovery <test-discovery>`,
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

.. _test-discovery:
.. note::

    The **test discovery** process searches for tests in the current
    directory (including package folders and sub-package folders) or in
    a specified directory.  To learn more, see the unittest
    documentation on `Test Discovery
    <https://docs.python.org/3/library/unittest.html#test-discovery>`_.
