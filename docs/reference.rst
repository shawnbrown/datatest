
Package Reference
=================


DataTestCase
--------------

This class inherits from `unittest.TestCase` and adds additional
properties and methods to help with testing data.

Column methods operate on the column names (or header rows) of a data
source:

+---------------------------------------------------+----------------------------------------------+
| Column method                                     | Checks that                                  |
+===================================================+==============================================+
| :meth:`assertDataColumnSet()                      | subject columns == trusted columns           |
| <datatest.DataTestCase.assertDataColumnSet>`      |                                              |
+---------------------------------------------------+----------------------------------------------+
| :meth:`assertDataColumnSubset()                   | subject columns <= trusted columns           |
| <datatest.DataTestCase.assertDataColumnSubset>`   |                                              |
+---------------------------------------------------+----------------------------------------------+
| :meth:`assertDataColumnSuperset()                 | subject columns >= trusted columns           |
| <datatest.DataTestCase.assertDataColumnSuperset>` |                                              |
+---------------------------------------------------+----------------------------------------------+

Value methods operate on the values within a given column:

+---------------------------------------------------+---------------------------------------------------+
| Value method                                      | Checks that                                       |
+===================================================+===================================================+
| :meth:`assertDataSet(column)                      | subject vals == trusted vals in given `column`    |
| <datatest.DataTestCase.assertDataSet>`            |                                                   |
+---------------------------------------------------+---------------------------------------------------+
| :meth:`assertDataSubset(column)                   | subject vals <= trusted vals in given `column`    |
| <datatest.DataTestCase.assertDataSubset>`         |                                                   |
+---------------------------------------------------+---------------------------------------------------+
| :meth:`assertDataSuperset(column)                 | subject vals <= trusted vals in given `column`    |
| <datatest.DataTestCase.assertDataSuperset>`       |                                                   |
+---------------------------------------------------+---------------------------------------------------+
| :meth:`assertDataSum(column, group_by)            | sum of subject vals == sum of trusted vals in     |
| <datatest.DataTestCase.assertDataSum>`            | given `column` for each group in `group_by`       |
+---------------------------------------------------+---------------------------------------------------+
| :meth:`assertDataRegex(column, regex)             | `regex`.search(val) for each val in `column`      |
| <datatest.DataTestCase.assertDataRegex>`          |                                                   |
+---------------------------------------------------+---------------------------------------------------+
| :meth:`assertDataNotRegex(column, regex)          | not `regex`.search(val) for each val in `column`  |
| <datatest.DataTestCase.assertDataNotRegex>`       |                                                   |
+---------------------------------------------------+---------------------------------------------------+

**Filters:**
The value methods above can also accept key word arguments to filter the
rows being tested (e.g., ``mycolumn='someval'``).

The following code will
assert that the subject values match the trusted values for the `city`
column but only for records where `state` equals "Ohio"::

        self.assertDataSet('city', state='Ohio')

|

.. autoclass:: datatest.DataTestCase
   :members:


Data Sources
--------------

Data sources implement a common set of methods which are used by
DataTestCase to access data and report meaningful failure messages.

+---------------------------------------------+--------------------------------------+
| Class                                       | Loads                                |
+=============================================+======================================+
| :class:`SqliteDataSource(connection, table) | SQLite table from given connection   |
| <datatest.SqliteDataSource>`                | object                               |
+---------------------------------------------+--------------------------------------+
| :class:`CsvDataSource(file)                 | CSV file from file path or           |
| <datatest.CsvDataSource>`                   | file-like object                     |
+---------------------------------------------+--------------------------------------+
| :class:`MultiDataSource(*sources)           | multiple data sources and integrates |
| <datatest.MultiDataSource>`                 | them into a single data source       |
+---------------------------------------------+--------------------------------------+

|

.. autoclass:: datatest.BaseDataSource
   :members: __init__, __str__, slow_iter, columns, set, sum, count, groups

--------------

.. autoclass:: datatest.SqliteDataSource
   :members:
   :inherited-members:

--------------

.. autoclass:: datatest.CsvDataSource
   :members:
   :inherited-members:

--------------

.. autoclass:: datatest.MultiDataSource
   :members:
   :inherited-members:


Errors and Differences
----------------------

.. autoclass:: datatest.DataAssertionError
   :members:

--------------

.. autoclass:: datatest.ExtraColumn
   :members:

--------------

.. autoclass:: datatest.MissingColumn
   :members:

--------------

.. autoclass:: datatest.ExtraValue
   :members:

--------------

.. autoclass:: datatest.MissingValue
   :members:

--------------

.. autoclass:: datatest.ExtraSum
   :members:

--------------

.. autoclass:: datatest.MissingSum
   :members:


Test Runner Program
-------------------

.. autoclass:: datatest.DataTestRunner
   :members:

--------------

.. autoclass:: datatest.DataTestProgram(module='__main__', defaultTest=None, argv=None, testRunner=datatest.DataTestRunner, testLoader=unittest.TestLoader, exit=True, verbosity=1, failfast=None, catchbreak=None, buffer=None, warnings=None)
   :members:

--------------

.. autoclass:: datatest.main
   :members:
