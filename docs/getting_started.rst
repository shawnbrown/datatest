
Getting Started
===============

`datatest` is designed to work, primarily, with tabular data
stored in spreadsheet files or database tables but it's also possible
to create custom data sources for other data formats.  To use `datatest`
effectively, users should be familiar with Python's standard `unittest`
package, regular expressions, and with the data they want to audit.


Basic Example
-------------

As an example, assume we want to audit the data in the following CSV
file (**myfile.csv**):

    =========  ======  =========
    member_id  active  region
    =========  ======  =========
    999        Y       Midwest
    1000       Y       South
    1001       N       Northeast
    ...        ...     ...
    =========  ======  =========

With the following script, we can verify that our file uses the correct
column names, that `member_id` contains only numbers, `active` contains
only "Y" or "N" values, and `region` contains only valid region codes
(**test_myfile.py**)::

    import datatest

    def setUpModule():
        global subjectData
        subjectData = datatest.CsvDataSource('myfile.csv')

    class TestMyData(datatest.DataTestCase):

        def test_columns(self):
            """Test for required column names."""
            columns = {'member_id', 'region', 'active'}
            self.assertColumnSet(columns)

        def test_format(self):
            """Test that 'member_id' contains only digits."""
            self.assertValueRegex('member_id', '\d+')

        def test_set_membership(self):
            """Test that 'active' and 'region' use valid codes."""
            self.assertValueSubset('active', {'Y', 'N'})

            regions = {'Midwest', 'Northeast', 'South', 'West'}
            self.assertValueSubset('region', regions)

    if __name__ == '__main__':
        datatest.main()


Typically, data sources should be defined inside a `setUpModule()`
function (as shown above).  However, if a data source is only referenced
within a single class, then defining it inside a `setUpClass()` method
is also acceptable::

    import datatest

    class TestMyData(datatest.DataTestCase):
        @classmethod
        def setUpClass(cls):
            cls.subjectData = datatest.CsvDataSource('myfile.csv')

        def test_columns(self):
            ...


Using Reference Data
--------------------

!!! TODO !!!


Allowing Discrepancies
----------------------

!!! TODO !!!


Command-Line Interface
----------------------

!!! TODO !!!

