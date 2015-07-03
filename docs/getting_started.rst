
***************
Getting Started
***************

:mod:`datatest` is designed to work, primarily, with tabular data
stored in spreadsheet files or database tables but it's also possible
to create custom data sources for other data formats.  To use
datatest effectively, users should be familiar with Python's standard
`unittest <http://docs.python.org/library/unittest.html>`_ package,
regular expressions, and with the data they want to audit.


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

We want to test for the following conditions:

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

        def test_format(self):
            """Test that 'member_id' & 'hours_volunteered' use only digits."""
            self.assertValueRegex('member_id', '^\d+$')
            self.assertValueRegex('hours_volunteered', '^\d+$')

        def test_label_sets(self):
            """Test that 'active' and 'region' use valid codes."""
            self.assertValueSubset('active', {'Y', 'N'})

            regions = {'Midwest', 'Northeast', 'South', 'West'}
            self.assertValueSubset('region', regions)

    if __name__ == '__main__':
        datatest.main()


The data we want to test is called the subject data and it should be
defined as a module-level or class-level property named ``subjectData``.
Typically, it is defined at the module level inside a  ``setUpModule()``
function (as shown above).  However, if it is only referenced within a
single class, then defining it inside a ``setUpClass()`` method is also
acceptable::

    import datatest

    class TestFormatAndLabels(datatest.DataTestCase):
        @classmethod
        def setUpClass(cls):
            cls.subjectData = datatest.CsvDataSource('members.csv')

        def test_columns(self):
            ...


Using Reference Data
====================

In the previous example, the ``test_label_sets()`` method specifies its
required values directly in the method itself. While this works for
many situations, large collections of reference data will oftentimes
need to be stored in an external source (a file or database).

To continue our previous example, we can use the following table as
reference data (**regional_report.csv**):

    =========  ==============  ==================
    region     active_members   hours_volunteered
    =========  ==============  ==================
    Midwest    39              97
    Northeast  23              59
    South      14              32
    West       33              76
    =========  ==============  ==================

By loading this data into a variable named ``referenceData``, we can
easily integrate it into our test script::

    import datatest

    def setUpModule():
        global subjectData
        global referenceData
        subjectData = datatest.CsvDataSource('members.csv')
        referenceData = datatest.CsvDataSource('regional_report.csv')

    class TestTotals(datatest.DataTestCase):

        def test_region(self):
            """Test that subject 'region' matches reference 'region'."""
            self.assertValueSet('region')

        def test_active(self):
            """Test for count of active members by region."""
            self.assertValueCount('active_members', ['region'], active='Y')

        def test_hours(self):
            """Test that sum of 'hours_volunteered' matches by region."""
            self.assertValueSum('hours_volunteered', ['region'])


Acceptable Error
================

When encountering a :class:`DataAssertionError <datatest.DataAssertionError>`,
a test fails with a list of detected differences.  Sometimes, these
differences are acceptable and should not trigger a test failure.

To explicitly accept individual differences, use the
:meth:`acceptDifference <datatest.DataTestCase.acceptDifference>`
context manager::

    def test_population(self):
        diff = [
            ExtraSum(+8, 11771, county='Warren', city='Franklin'),
            MissingSum(-27, 3184, county='Lake', city='Madison'),
        ]
        with self.acceptDifference(diff):
            self.assertValueSum('population', ['county', 'city'])

To accept several numeric differences at once, you can use the
:meth:`acceptTolerance <datatest.DataTestCase.acceptTolerance>` or
:meth:`acceptPercentTolerance <datatest.DataTestCase.acceptPercentTolerance>`
methods::

    def test_households(self):
        with self.acceptTolerance(10):
            self.assertValueCount('households', ['county', 'city'])


Command-Line Interface
======================

The datatest module can be used from the command line just like
unittest. To run datatest with test discovery, use the following
command::

    python -m datatest

Run tests from specific modules, classes or individual methods with::

    python -m datatest test_module1 test_module2
    python -m datatest test_module.TestClass
    python -m datatest test_module.TestClass.test_method

The syntax and command-line options (``-f``, ``-v``, etc.) are the same
as unittest---see the
`unittest documentation <http://docs.python.org/library/unittest.html#command-line-interface>`_
for full details.
