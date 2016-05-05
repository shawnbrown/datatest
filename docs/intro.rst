
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

As an example, consider a simple file (users.csv) with the following format:

    =======  ======
    user_id  active
    =======  ======
    999      Y
    1000     Y
    1001     N
    ...      ...
    =======  ======


Here is a short script (test_users.py) to test the data in this file:

.. code-block:: python

    import datatest


    def setUpModule():
        global subjectData
        subjectData = datatest.CsvSource('users.csv')


    class TestUserData(datatest.DataTestCase):
        def test_columns(self):
            """Check that column names match required set."""
            required = {'user_id', 'active'}
            self.assertDataColumns(required)

        def test_user_id(self):
            """Check that 'user_id' column contains digits."""
            def required(x):  # <- Helper function.
                return x.isdigit()
            self.assertDataSet('user_id', required)

        def test_active(self):
            """Check that 'active' column contains valid codes."""
            required = {'Y', 'N'}
            self.assertDataSet('active', required)


    if __name__ == '__main__':
        datatest.main()


Download :download:`basic_example.zip <_static/basic_example.zip>` to try it
for yourself.


Step-by-step Breakdown
----------------------

1. Define subjectData (the data under test):
    To interface with our data, we create a data source and assign it to the
    variable ``subjectData``:

    .. code-block:: python
        :emphasize-lines: 3

        def setUpModule():
            global subjectData
            subjectData = datatest.CsvSource('users.csv')

2. Check column names (against a set of values):
    To check the columns, we define a *required* set of names and pass it to
    :meth:`assertDataColumns() <datatest.DataTestCase.assertDataColumns>`:

    .. code-block:: python
        :emphasize-lines: 4

        class TestUserData(datatest.DataTestCase):
            def test_columns(self):
                required = {'user_id', 'active'}
                self.assertDataColumns(required)

    This assertion automatically checks the *required* set against the data in
    the ``subjectData`` defined earlier.

3. Check "user_id" values (with a helper-function):
    To assert that the "user_id" column contains only digits, we define a
    *reqired* helper-function and pass it to :meth:`assertDataSet()
    <datatest.DataTestCase.assertDataSet>`.  The helper-function in this
    example takes a single value and returns ``True`` if the value is a digit
    or ``False`` if not:

    .. code-block:: python
        :emphasize-lines: 4

            def test_user_id(self):
                def required(x):  # <- Helper function.
                    return x.isdigit()
                self.assertDataSet('user_id', required)

4. Check "active" values (against a set of values):
    To check that the "active" column contains only "Y" or "N" values, we
    define a *required* set of values and pass it to :meth:`assertDataSet()
    <datatest.DataTestCase.assertDataSet>`:

    .. code-block:: python
        :emphasize-lines: 3

            def test_active(self):
                required = {'Y', 'N'}
                self.assertDataSet('active', required)

.. note::

    This example uses a :class:`CsvSource <datatest.CsvSource>` to access data
    from a CSV file.  Other data sources can access data in a variety of
    formats (Excel, pandas, SQL, etc.).

.. note::
    Loading files from disk and establishing database connections are
    relatively slow operations.  So it's best to minimize the number of times
    a data source object is created.  Typically, ``subjectData`` is defined at
    the module-level, however, if the data is only used within a single class,
    then defining it at the class-level is also acceptable:

    .. code-block:: python
        :emphasize-lines: 4

        class TestUsers(datatest.DataTestCase):
            @classmethod
            def setUpClass(cls):
                cls.subjectData = datatest.CsvSource('users.csv')


Reference Data
==============

In the previous example, we checked our data against sets and functions but
it's also possible to check our data against other data sources.

For this next example, we will test the 2014 Utah Crime Statistics Report
(utah_2014_crime_details.csv).  This file contains 1,048 records and **if a
county was missing from the file or if a number miscopied, the errors would
not be immediately obvious**:

    ======  =====================  ========  =========
    county  agency                 crime     incidents
    ======  =====================  ========  =========
    BEAVER  BEAVER COUNTY SHERIFF  arson     0
    BEAVER  BEAVER COUNTY SHERIFF  assault   1
    BEAVER  BEAVER COUNTY SHERIFF  burglary  18
    BEAVER  BEAVER COUNTY SHERIFF  homicide  1
    BEAVER  BEAVER COUNTY SHERIFF  larceny   78
    ...     ...                    ...       ...
    ======  =====================  ========  =========

To verify our subject data, we will use a county-level summary file
(utah_2014_crime_summary.csv) as reference data.  This summary file contains the
county names and total incidents reported:

    =========  =========
    county     incidents
    =========  =========
    BEAVER     105
    BOX ELDER  1153
    CACHE      1482
    CARBON     646
    DAGGETT    9
    ...        ...
    =========  =========

The following script (test_utah_2014_crime_details.py) demonstrates the use
of reference data.  Unlike the previous example, the assertion calls in this
script don't pass a *required* argument---when *required* is omitted, values
from ``referenceData`` are used in its place:

.. code-block:: python

    import datatest


    def setUpModule():
        global subjectData
        global referenceData
        subjectData = datatest.CsvSource('utah_2014_crime_details.csv')
        referenceData = datatest.CsvSource('utah_2014_crime_summary.csv')


    class TestDetails(datatest.DataTestCase):
        def test_columns(self):
            """Check that column names match those in reference data."""
            with self.allowExtra():
                self.assertDataColumns()

        def test_county(self):
            """Check that 'county' column matches reference data."""
            self.assertDataSet('county')

        def test_incidents(self):
            """Check that sum of 'incidents' (grouped by 'county') matches
            reference data."""
            self.assertDataSum('incidents', keys=['county'])


    if __name__ == '__main__':
        datatest.main()

Download :download:`reference_data_example.zip <_static/reference_data_example.zip>`
to try it for yourself.


Step-by-step Breakdown
----------------------

1. Define subjectData (data under test) and referenceData (data trusted to be correct):
    In addition to ``subjectData``, we load our reference data and assign it
    to the variable ``referenceData``:

    .. code-block:: python
        :emphasize-lines: 5

        def setUpModule():
            global subjectData
            global referenceData
            subjectData = datatest.CsvSource('utah_2014_crime_details.csv')
            referenceData = datatest.CsvSource('utah_2014_crime_summary.csv')

2. Check column names (against referenceData):
    To check the columns against our reference file, we call
    :meth:`assertDataColumns() <datatest.DataTestCase.assertDataColumns>`
    with no arguments.  Since we've omitted the *required* argument, the
    method compares the ``subjectData`` columns against the ``referenceData``
    columns:

    .. code-block:: python
        :emphasize-lines: 4

        class TestDetails(datatest.DataTestCase):
            def test_columns(self):
                with self.allowExtra():
                    self.assertDataColumns()

    Comparing the data sources reveals two differences---the columns "agency"
    and "crime".  These columns are not part of the reference data so they're
    seen as extra.  But because our subject data contains more detail, we
    understand that these extra columns are acceptable so we allow them by
    putting our assertion inside the :meth:`allowExtra()
    <datatest.DataTestCase.allowExtra>` context manager.

3. Check "county" values (against referenceData):
    To check the "county" values against our reference data, we call
    :meth:`assertDataSet() <datatest.DataTestCase.assertDataSet>` and pass
    in the column name (omitting *required* argument):

    .. code-block:: python
        :emphasize-lines: 2

            def test_county(self):
                self.assertDataSet('county')

4. Check sum of "incidents" grouped by "county" (against referenceData).
    To check that the sum of incidents by county matches the number
    listed in the ``referenceData``, we call :meth:`assertDataSum()
    <datatest.DataTestCase.assertDataSum>` and pass in the column we want
    to sum as well as the columns we want to group by:

    .. code-block:: python
        :emphasize-lines: 2

            def test_incidents(self):
                self.assertDataSum('incidents', keys=['county'])


Understanding Errors
====================

When the data in the ``subjectData`` differs from the *required* data
(or ``referenceData`` if *required* is omitted), a test will fail with a
:class:`DataAssertionError <datatest.DataAssertionError>` containing
a list of detected differences.

A good way to understand how errors work is to download the previous examples
(:download:`basic_example.zip <_static/basic_example.zip>`
and :download:`reference_data_example.zip <_static/reference_data_example.zip>`)
and change the values in the subject data file.

.. code-block:: none
    :emphasize-lines: 5-6

    Traceback (most recent call last):
      File "test_members.py", line 15, in test_region_labels
        self.assertValueSet('region')
    datatest.DataAssertionError: different 'region' values:
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
test runs without failing:

.. code-block:: python
    :emphasize-lines: 6

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
<datatest.DataTestCase.allowPercentDeviation>` methods:

.. code-block:: python
    :emphasize-lines: 2

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

.. epigraph::
    Unix was not designed to stop you from doing stupid things, because that
    would also stop you from doing clever things. --Doug Gwyn

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
