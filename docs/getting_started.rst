
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

    =========  =========  ======
    member_id  region     active
    =========  =========  ======
    999        Midwest    Y
    1000       South      Y
    1001       Northeast  N
    ...        ...        ...
    =========  =========  ======

With the following script, we can verify that the CSV file uses the
correct column names, that `member_id` contains only numbers, `region`
contains only valid region codes, and `active` contains only "Y" or "N"
values (**test_myfile.py**)::

    import datatest

    def setUpModule():
        global subjectData
        subjectData = datatest.CsvDataSource('myfile.csv')

    class TestMyData(datatest.DataTestCase):

        def test_columns(self):
            """Test for required column names."""
            columns = {'member_id', 'region', 'active'}
            self.assertDataColumnSet(columns)

        def test_member_id(self):
            """Test that 'member_id' contains only digits."""
            self.assertDataRegex('member_id', '\d+')

        def test_region(self):
            """Test that 'region' contains valid region names."""
            regions = {'Midwest', 'Northeast', 'South', 'West'}
            self.assertDataSubset('region', regions)

        def test_active(self):
            """Test that 'active' contains 'Y' or 'N'."""
            self.assertDataSubset('active', {'Y', 'N'})

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


Using `trustedData`
-------------------

!!! TODO !!!


Allowing Discrepancies
--------------------------

!!! TODO !!!


Command-Line Interface
----------------------

!!! TODO !!!

