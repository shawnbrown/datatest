
***************
Getting Started
***************

:mod:`datatest` is designed to work, primarily, with tabular data
stored in spreadsheet files or database tables but it's also possible
to create custom data sources for other data formats.  To use
datatest effectively, users should be familiar with Python's standard
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
        subjectData = datatest.CsvDataSource('members.csv')


    class TestFormatAndLabels(datatest.DataTestCase):
        def test_columns(self):
            """Test for required column names."""
            columns = {'member_id', 'region', 'active', 'hours_volunteered'}
            self.assertColumnSet(columns)

        def test_numeric(self):
            """Test that numeric columns contain only digits."""
            self.assertValueRegex('member_id', '^\d+$')
            self.assertValueRegex('hours_volunteered', '^\d+$')

        def test_active_labels(self):
            """Test that 'active' column contains valid codes."""
            self.assertValueSubset('active', {'Y', 'N'})

        def test_region_labels(self):
            """Test that 'region' column contains valid codes."""
            regions = {'Midwest', 'Northeast', 'South', 'West'}
            self.assertValueSubset('region', regions)


    if __name__ == '__main__':
        datatest.main()


The data we want to test---the subject of our tests---is stored in
a property named ``subjectData``.  This property is referenced,
internally, by the ``assertValue...()`` and ``assertColumn...()``
methods.

``subjectData`` is typically defined at the module-level inside a ``setUpModule()``
function---as shown in the previous example.  However, if it is only
referenced within a single class, then defining it inside a
``setUpClass()`` method is also acceptable::


    import datatest


    class TestFormatAndLabels(datatest.DataTestCase):
        @classmethod
        def setUpClass(cls):
            cls.subjectData = datatest.CsvDataSource('members.csv')

        def test_columns(self):
            ...


Using Reference Data
====================

Datatest also supports the use of reference data from external sources
(files or databases).  While the tests in our first example specify
their required values directly in the methods themselves, doing so
becomes inconvenient when working with large amounts of reference data.

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
        subjectData = datatest.CsvDataSource('members.csv')
        referenceData = datatest.CsvDataSource('regional_report.csv')


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


Errors
======

When encountering a :class:`DataAssertionError <datatest.DataAssertionError>`,
a data test fails with a list of detected differences.


Acceptable Errors
=================

Sometimes, it's undesirable for certain differences to trigger a test
failure.  To mark specific differences as acceptable, use the
:meth:`acceptDifference <datatest.DataTestCase.acceptDifference>`
context manager::

    def test_population(self):
        diff = [
            ExtraSum(+8, 11771, county='Warren'),
            MissingSum(-25, 3184, county='Lake'),
        ]
        with self.acceptDifference(diff):
            self.assertValueSum('population', ['county'])

To accept several numeric differences at once, you can use the
:meth:`acceptTolerance <datatest.DataTestCase.acceptTolerance>` or
:meth:`acceptPercentTolerance <datatest.DataTestCase.acceptPercentTolerance>`
methods::

    def test_households(self):
        with self.acceptTolerance(25):
            self.assertValueCount('population', ['county'])


Command-Line Interface
======================

The datatest module can be used from the command line just like
unittest. To run the program with test discovery, use the following
command::

    python -m datatest

Run tests from specific modules, classes, or individual methods with::

    python -m datatest test_module1 test_module2
    python -m datatest test_module.TestClass
    python -m datatest test_module.TestClass.test_method

The syntax and command-line options (``-f``, ``-v``, etc.) are the same
as unittest---see the
`unittest documentation <http://docs.python.org/library/unittest.html#command-line-interface>`_
for full details.
