
.. meta::
    :description: Test-driven data preparation can provide much-needed
                  structure to guide the workflow of data preparation,
                  itself.
    :keywords: test-driven data preparation


************
Introduction
************

:mod:`datatest` is designed to work with tabular data stored in spreadsheet
files or database tables but it's also possible to create custom data sources
for other formats.  To use datatest effectively, users should be familiar with
Python's standard `unittest <http://docs.python.org/library/unittest.html>`_
library and with the data they want to test.

In the practice of data science, data preparation is a huge part of the job.
Practitioners often spend 50 to 80 percent of their time wrangling data [1]_
[2]_ [3]_ [4]_.  This critically important phase is time-consuming,
unglamorous, and often poorly structured.  Using datatest to implement
:ref:`test-driven data preparation <test-driven-data-preparation>` can offer
a disciplined approach to an otherwise messy process.

A datatest suite can facilitate quick edit-test cycles which help guide the
selection, cleaning, integration, and formatting of data.  Data tests can also
help to automate check-lists, measure progress, and promote best practices.


Basic Example
=============

As an example, consider a simple file with the following format
(**users.csv**):

    =======  ======
    user_id  active
    =======  ======
    999      Y
    1000     Y
    1001     N
    ...      ...
    =======  ======

Here is a short script to test the data from this file::

    import datatest


    def setUpModule():
        global subjectData
        subjectData = datatest.CsvSource('users.csv')


    class TestUserData(datatest.DataTestCase):
        def test_columns(self):
            """Check that file uses required column names."""
            required = {'user_id', 'active'}
            self.assertDataColumns(required)

        def test_user_id(self):
            """Check that 'user_id' column contains digits."""
            def isdigit(x):  # <- Helper function.
                return x.isdigit()
            self.assertDataSet('user_id', isdigit)

        def test_active(self):
            """Check that 'active' column contains valid codes."""
            required = {'Y', 'N'}
            self.assertDataSet('active', required)


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
``assertData...()`` methods.

Loading files from disk and establishing database connections are relatively
expensive operations.  It's best to minimize the number of times a data source
object is created.  Typically, ``subjectData`` is defined at the module-level:

.. code-block:: python
    :emphasize-lines: 3-5

    import datatest

    def setUpModule():
        global subjectData
        subjectData = datatest.CsvSource('users.csv')

    class TestUserData(datatest.DataTestCase):
        def test_columns(self):
            ...

However, if the data is only used within a single class, then defining it
at the class-level is also acceptable:

.. code-block:: python
    :emphasize-lines: 4-6

    import datatest

    class TestUserData(datatest.DataTestCase):
        @classmethod
        def setUpClass(cls):
            cls.subjectData = datatest.CsvSource('users.csv')

        def test_columns(self):
            ...


Reference Data
==============

Datatest also supports the use of reference data from external sources (files
or databases).  While our first example defined its requirements directly in
the methods themselves, doing so becomes inconvenient when working with large
amounts of required values.

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
a list of detected differences:

.. code-block:: none

    Traceback (most recent call last):
      File "test_members.py", line 15, in test_region_labels
        self.assertValueSet('region')
    datatest.case.DataAssertionError: different 'region' values:
     Extra('North-east'),
     Missing('Northeast')

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
        self.assertDataSum('population', ['county'])
    datatest.case.DataAssertionError: different 'population' values:
     Deviation(-25, 3184, county='Lake'),
     Deviation(+8, 11771, county='Warren')

If we've determined that these differences are allowable, we can use the
:meth:`allowOnly <datatest.DataTestCase.allowOnly>` context manager so the
test runs without failing::

    def test_population(self):
        diff = [
            Deviation(-25, 3184, county='Lake'),
            Deviation(+8, 11771, county='Warren'),
        ]
        with self.allowOnly(diff):
            self.assertDataSum('population', ['county'])

To allow several numeric differences at once, you can use the
:meth:`allowDeviation <datatest.DataTestCase.allowDeviation>`
or :meth:`allowPercentDeviation
<datatest.DataTestCase.allowPercentDeviation>` methods::

    def test_households(self):
        with self.allowDeviation(25):
            self.assertDataSum('population', ['county'])


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


.. _test-driven-data-preparation:

Test-Driven Data Preparation
============================

A :mod:`datatest` suite can help organize and guide the data preparation
workflow.  It can also help supplement or replace check-lists and progress
reports.


Structuring a Test Suite
------------------------

The structure of a datatest suite defines a data preparation workflow.
The first tests should address essential prerequisites and the following
tests should focus on specific requirements.  Test cases and methods are
run *in order* (by line number).

Typically, data tests should be defined in the following order:

 1. load data sources (asserts that expected source data is present)
 2. check for expected column names
 3. validate format of values (data type or other regex)
 4. assert set-membership requirements
 5. assert sums, counts, or cross-column values

.. note::

    Datatest implements strictly ordered tests but don't expect other tools to
    do the same.  Ordered tests are useful when testing data but not so useful
    when testing software.  In fact, ordered testing of software can lead to
    problems if side-effects from one test affect the outcome of following
    tests.


Data Preparation Workflow
-------------------------

Using a quick edit-test cycle, users can:

 1. focus on a failing test
 2. make small changes to the data
 3. re-run the suite to check that the test now passes
 4. then, move on to the next failing test

The work of cleaning and formatting data takes place outside of the
datatest package itself.  Users can work with with the tools they find
the most productive (Excel, `pandas <http://pandas.pydata.org/>`_, R,
sed, etc.).


.. rubric:: Footnotes

.. [1] "Data scientists, according to interviews and expert estimates, spend
        from 50 percent to 80 percent of their time mired in this more mundane
        labor of collecting and preparing unruly digital data..." Steve Lohraug
        in *For Big-Data Scientists, 'Janitor Work' Is Key Hurdle to Insights*.
        Retrieved from http://www.nytimes.com/2014/08/18/technology/for-big-data-scientists-hurdle-to-insights-is-janitor-work.html

.. [2] "This [data preparation step] has historically taken the largest part
        of the overall time in the data mining solution process, which in some
        cases can approach 80% of the time." *Dynamic Warehousing: Data Mining
        Made Easy* (p. 19)

.. [3] Online poll of data mining practitioners: `[see image] <_static/data_prep_poll.png>`_,
       *Data preparation (Oct 2003)*.
       Retrieved from http://www.kdnuggets.com/polls/2003/data_preparation.htm
       [While this poll is quite old, the situation has not changed
       drastically.]

.. [4] "As much as 80% of KDD is about preparing data, and the remaining 20%
        is about mining." *Data Mining for Design and Manufacturing* (p. 44)
