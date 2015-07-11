
*****************
Package Reference
*****************

.. _assert-methods:

Column Assertions
=================

Column assertions operate on the column names (or header rows) of a data
source:

+---------------------------------------------------+----------------------------------------------+
| Column method                                     | Checks that                                  |
+===================================================+==============================================+
| :meth:`assertColumnSet()                          | subject columns == reference columns         |
| <datatest.DataTestCase.assertColumnSet>`          |                                              |
+---------------------------------------------------+----------------------------------------------+
| :meth:`assertColumnSubset()                       | subject columns <= reference columns         |
| <datatest.DataTestCase.assertColumnSubset>`       |                                              |
+---------------------------------------------------+----------------------------------------------+
| :meth:`assertColumnSuperset()                     | subject columns >= reference columns         |
| <datatest.DataTestCase.assertColumnSuperset>`     |                                              |
+---------------------------------------------------+----------------------------------------------+


Value Assertions
================

Value assertions operate on the values within a given column:

+----------------------------------------------+----------------------------------------------------+
| Value method                                 | Checks that                                        |
+==============================================+====================================================+
| :meth:`assertValueSet(c)                     | subject vals == reference vals in column *c*       |
| <datatest.DataTestCase.assertValueSet>`      |                                                    |
+----------------------------------------------+----------------------------------------------------+
| :meth:`assertValueSubset(c)                  | subject vals <= reference vals in column *c*       |
| <datatest.DataTestCase.assertValueSubset>`   |                                                    |
+----------------------------------------------+----------------------------------------------------+
| :meth:`assertValueSuperset(c)                | subject vals <= reference vals in column *c*       |
| <datatest.DataTestCase.assertValueSuperset>` |                                                    |
+----------------------------------------------+----------------------------------------------------+
| :meth:`assertValueSum(c, g)                  | sum of subject vals == sum of reference vals in    |
| <datatest.DataTestCase.assertValueSum>`      | column *c* for each group of *g*                   |
+----------------------------------------------+----------------------------------------------------+
| :meth:`assertValueRegex(c, r)                | *r*.search(val) for subject vals in column *c*     |
| <datatest.DataTestCase.assertValueRegex>`    |                                                    |
+----------------------------------------------+----------------------------------------------------+
| :meth:`assertValueNotRegex(c, r)             | not *r*.search(val) for subject vals in column *c* |
| <datatest.DataTestCase.assertValueNotRegex>` |                                                    |
+----------------------------------------------+----------------------------------------------------+


`**filter_by` Keyword Aguments
------------------------------

The value methods above accept optional keyword arguments to filter the
rows being tested (e.g., ``mycolumn='someval'``).

The following code will assert that the subject values match the
reference values for the ``city`` column but only for records where
``state`` equals "Ohio"::

        self.assertDataSet('city', state='Ohio')


Accept Methods
==============

+-------------------------------------------------+------------------------------------------+
| Accept method                                   | Accepts that                             |
+=================================================+==========================================+
| :meth:`acceptDifference(diff)                   | differences match those in *diff*        |
| <datatest.DataTestCase.acceptDifference>`       |                                          |
+-------------------------------------------------+------------------------------------------+
| :meth:`acceptTolerance(tolerance)               | absolute values of numeric differences   |
| <datatest.DataTestCase.acceptTolerance>`        | are equal to or less than *tolerance*    |
+-------------------------------------------------+------------------------------------------+
| :meth:`acceptPercentTolerance(tolerance)        | percentage values of numeric differences |
| <datatest.DataTestCase.acceptPercentTolerance>` | are equal to or less than *tolerance*    |
+-------------------------------------------------+------------------------------------------+


DataTestCase
============

This class inherits from
`unittest.TestCase <http://docs.python.org/library/unittest.html#unittest.TestCase>`_
and adds additional properties and methods to help with testing data.

.. autoclass:: datatest.DataTestCase
   :members:


Data Sources
============

Data sources implement a common set of methods which are used by
DataTestCase to access data and report meaningful failure messages.

+---------------------------------------------+--------------------------------------+
| Class                                       | Loads                                |
+=============================================+======================================+
| :class:`CsvDataSource(file)                 | CSV file from file path or           |
| <datatest.CsvDataSource>`                   | file-like object                     |
+---------------------------------------------+--------------------------------------+
| :class:`SqliteDataSource(connection, table) | SQLite table from given connection   |
| <datatest.SqliteDataSource>`                | object                               |
+---------------------------------------------+--------------------------------------+
| :class:`MultiDataSource(*sources)           | multiple data sources and integrates |
| <datatest.MultiDataSource>`                 | them into a single data source       |
+---------------------------------------------+--------------------------------------+

|

.. autoclass:: datatest.CsvDataSource
   :members:
   :inherited-members:

--------------

.. autoclass:: datatest.SqliteDataSource
   :members:
   :inherited-members:

--------------

.. autoclass:: datatest.MultiDataSource
   :members:
   :inherited-members:

--------------

.. autoclass:: datatest.BaseDataSource
   :members: __init__, __str__, slow_iter, columns, unique, set, sum, count


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
