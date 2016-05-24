
.. meta::
    :description: Test-driven data preparation can provide much-needed
                  structure to guide the workflow of data preparation,
                  itself.
    :keywords: test-driven data preparation


************************
Introduction to Datatest
************************

In the practice of data science, data preparation is a huge part of the job.
Practitioners often spend 50 to 80 percent of their time wrangling data [1]_
[2]_ [3]_ [4]_.  This critically important phase is time-consuming,
unglamorous, and often poorly structured.

Using :mod:`datatest` to implement :ref:`test-driven data preparation
<test-driven-data-preparation>` can offer a disciplined approach to an
otherwise messy process.

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
            self.assertDataColumns(required={'user_id', 'active'})

        def test_user_id(self):
            def must_be_digit(x):  # <- Helper function.
                return str(x).isdigit()
            self.assertDataSet('user_id', required=must_be_digit)

        def test_active(self):
            self.assertDataSet('active', required={'Y', 'N'})

    if __name__ == '__main__':
        datatest.main()

..
    NOTE: The "Basic Example" code uses the *required* argument as
    a keyword to be more explicit for developers new to reading
    code written using datatest.


Step-by-step Explanation
------------------------

To try it for yourself, download and run
:download:`basic_example.zip <_static/basic_example.zip>` after reviewing the
following steps.

1. Define subjectData (the data under test):
    To interface with our data, we create a data source and assign it to the
    variable :meth:`subjectData <datatest.DataTestCase.subjectData>`:

    .. code-block:: python
        :emphasize-lines: 3

        def setUpModule():
            global subjectData
            subjectData = datatest.CsvSource('users.csv')

    Here, we use a :class:`CsvSource <datatest.CsvSource>` to access data
    from a CSV file.  Data in other formats can be accessed with
    :ref:`other data sources <data-sources>`.

2. Check column names (against a set of values):
    To check the columns, we pass a *required* set of names to
    :meth:`assertDataColumns() <datatest.DataTestCase.assertDataColumns>`:

    .. code-block:: python
        :emphasize-lines: 3

        class TestUserData(datatest.DataTestCase):
            def test_columns(self):
                self.assertDataColumns(required={'user_id', 'active'})

    This assertion automatically checks the *required* set against the column
    names in the :meth:`subjectData <datatest.DataTestCase.subjectData>`
    defined earlier.

3. Check "user_id" values (with a helper-function):
    To assert that the "user_id" column contains only digits, we define a
    *reqired* helper-function and pass it to :meth:`assertDataSet()
    <datatest.DataTestCase.assertDataSet>`.  The helper-function in this
    example takes a single value and returns ``True`` if the value is a digit
    or ``False`` if not:

    .. code-block:: python
        :emphasize-lines: 4

            def test_user_id(self):
                def must_be_digit(x):  # <- Helper function.
                    return x.isdigit()
                self.assertDataSet('user_id', required=must_be_digit)

    This assertion applies the *required* function to all of the data in the
    "user_id" column.  The test passes if the helper function returns True
    for all values.

4. Check "active" values (against a set of values):
    To check that the "active" column contains only "Y" or "N" values, we
    pass a *required* set of values to :meth:`assertDataSet()
    <datatest.DataTestCase.assertDataSet>`:

    .. code-block:: python
        :emphasize-lines: 2

            def test_active(self):
                self.assertDataSet('active', required={'Y', 'N'})

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


Understanding Failure Messages
==============================

When a data assertion fails, a :class:`DataAssertionError
<datatest.DataAssertionError>` is raised that contains a list of differences
detected in the subjectData (the data under test).  To demonstrate this, we
will use the same tests shown in the previous example but we'll check a CSV file
that contains a number of data errors---these errors will trigger test failures.

Download and run :download:`failure_message_example.zip
<_static/failure_message_example.zip>` to see for yourself.

..
    NOTE: The "Understanding Failure Messages" code is the same as the
    "Basic Example" code except that the *required* argument is passed
    positionally---not as a keyword argument.  Passing arguments by
    keyword can create verbose code and since it's optional, we want to
    acclimate readers of datatest code with how tests are commonly
    written.

1. Check column names (against a set of values):
    To check the columns, we call :meth:`assertDataColumns(...)
    <datatest.DataTestCase.assertDataColumns>`.  But we detect a number of
    differences in this new file:

    .. code-block:: none
        :emphasize-lines: 3,6-9

        Traceback (most recent call last):
          File "test_users_fail.py", line 13, in test_columns
            self.assertDataColumns({'user_id', 'active'})
        datatest.error.DataAssertionError: mandatory test failed, stopping
        early: different column names:
         Extra('USER_ID'),
         Extra('ACTIVE'),
         Missing('user_id'),
         Missing('active')

    The column names are written in uppercase but our test checks for "user_id"
    and "active" (written with lowercase letters).  So the uppercase values are
    seen as :class:`Extra <datatest.Extra>`, while the lowercase ones are
    considered :class:`Missing <datatest.Missing>`.  To correct for this, we
    convert the CSV column names to lowercase and the failure goes away.

2. Check "user_id" values (with a helper-function):
    To check the "user_id" column, we call :meth:`assertDataSet(...)
    <datatest.DataTestCase.assertDataSet>` with a helper function:

    .. code-block:: none
        :emphasize-lines: 3,5-6

        Traceback (most recent call last):
          File "test_users_fail.py", line 19, in test_user_id
            self.assertDataSet('user_id', must_be_digit)
        datatest.error.DataAssertionError: different 'user_id' values:
         Invalid('1056A'),
         Invalid('1099B')

    The helper function, ``must_be_digit()``, asserts that the "user_id" values
    contain only digits.  Any ID values that contain non-digit characters are
    seen as :class:`Invalid <datatest.Invalid>` (in this case, "1056A" and
    "1099B").  To correct for this, we remove the letters "A" and "B" which
    allows the test to pass.

3. Check "active" values (against a set of values):
    To check the "active" column, we call :meth:`assertDataSet(...)
    <datatest.DataTestCase.assertDataSet>` to make sure it contains
    the required values ("Y" and "N"):

    .. code-block:: none
        :emphasize-lines: 3,5-9

        Traceback (most recent call last):
          File "test_users_fail.py", line 23, in test_active
            self.assertDataSet('active', {'Y', 'N'})
        datatest.error.DataAssertionError: different 'active' values:
         Extra('YES'),
         Extra('NO'),
         Extra('y'),
         Extra('n'),
         Missing('N')

    Above, we see several data errors which are common when integrating
    data from multiple sources.  To correct for these errors, we convert
    "YES" to "Y", "NO" to "N", and change the remaining lowercase values
    to uppercase ("y" to "Y" and "n" to "N").  With these changes made,
    the test will pass and we can trust that our data is valid.


Reference Data
==============

In the previous examples, we checked our data against sets and functions but
it's also possible to check our data against other data sources.

For this next example, we will test the 2014 Utah Crime Statistics Report
(utah_2014_crime_details.csv).  This file contains 1,048 records and **if a
single county was missing or if a few numbers were mis-copied, the errors
would not be immediately obvious**:

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
(utah_2014_crime_summary.csv) as reference data.  This summary file
contains the county names and total incidents reported:

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


Step-by-step Explanation
------------------------

To try it for yourself, download and run :download:`reference_data_example.zip
<_static/reference_data_example.zip>` after reviewing the following steps.

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

    Our ``referenceData`` only contains the columns "county" and "incidents".
    Since reference data is trusted to be correct, the two additional columns
    in the ``subjectData`` (the columns "agency" and "crime") are seen as extra.
    But as writers of this test, we understand that our subject data is supposed
    to contain more detail and these extra columns are perfectly acceptable.  To
    account for this, we **allow** these differences by putting our assertion
    inside an :meth:`allowExtra() <datatest.DataTestCase.allowExtra>` context
    manager.

3. Check "county" values (against referenceData):
    To check the "county" values against our reference data, we call
    :meth:`assertDataSet() <datatest.DataTestCase.assertDataSet>` and pass
    in the column name (omitting *required* argument):

    .. code-block:: python
        :emphasize-lines: 2

            def test_county(self):
                self.assertDataSet('county')

4. Check the sum of "incidents" grouped by "county" (against referenceData):
    To check that the sum of incidents by county matches the number
    listed in the ``referenceData``, we call :meth:`assertDataSum()
    <datatest.DataTestCase.assertDataSum>` and pass in the column we want
    to sum as well as the columns we want to group by:

    .. code-block:: python
        :emphasize-lines: 2

            def test_incidents(self):
                self.assertDataSum('incidents', keys=['county'])


Allowed Differences
===================

.. todo::
    Rewrite this section and include a downloadable, working example.

Sometimes differences cannot be reconciled---they could represent a
disagreement between two authoritative sources or a lack of information
could make correction impossible.  In any case, there are situations
where it is legitimate to allow certain discrepancies for the purposes
of data processing.

In the following example, there are two discrepancies (eight more in
Warren County and 25 less in Lake County)::

    Traceback (most recent call last):
      File "test_survey.py", line 35, in test_population
        self.assertDataSum('population', ['county'])
    datatest.case.DataAssertionError: different 'population' values:
     Deviation(-25, 3184, county='Lake'),
     Deviation(+8, 11771, county='Warren')

If we've determined that these differences are allowable, we can use the
:meth:`allowOnly <datatest.DataTestCase.allowOnly>` context manager so
the test runs without failing:

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

.. epigraph::

    Unix was not designed to stop you from doing stupid things, because that
    would also stop you from doing clever things. ---Doug Gwyn

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

    Datatest executes strictly ordered tests (ordered by package name
    then line number).


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

.. [3] Online poll of data mining practitioners: `See image <_static/data_prep_poll.png>`_,
       *Data preparation (Oct 2003)*.
       Retrieved from http://www.kdnuggets.com/polls/2003/data_preparation.htm
       [While this poll is quite old, the situation has not changed
       drastically.]

.. [4] "As much as 80% of KDD is about preparing data, and the remaining 20%
        is about mining." *Data Mining for Design and Manufacturing* (p. 44)
