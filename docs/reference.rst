
*****************
Package Reference
*****************

.. _assert-methods:

Column Assertions
=================

Column assertions operate on the column names (or header rows) of a data
source:

+---------------------------------------------------+----------------------------------------------+
| Method                                            | Checks that                                  |
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
| Method                                       | Checks that                                        |
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
| :meth:`assertValueCount(c, g)                | count of subject rows == sum of reference vals in  |
| <datatest.DataTestCase.assertValueCount>`    | column *c* for each group of *g*                   |
+----------------------------------------------+----------------------------------------------------+
| :meth:`assertValueRegex(c, r)                | *r*.search(val) for subject vals in column *c*     |
| <datatest.DataTestCase.assertValueRegex>`    |                                                    |
+----------------------------------------------+----------------------------------------------------+
| :meth:`assertValueNotRegex(c, r)             | not *r*.search(val) for subject vals in column *c* |
| <datatest.DataTestCase.assertValueNotRegex>` |                                                    |
+----------------------------------------------+----------------------------------------------------+


Optional Keyword Filters
------------------------

All of the value assertion methods, above, support optional keyword
arguments for quickly filtering the rows to be tested.

The following example asserts that the subject's ``postal_code`` values
match the reference's ``postal_code`` values but only for records where
the ``state`` equals ``'Ohio'`` and the ``city`` equals ``'Columbus'``::

    self.assertValueSet('postal_code', state='Ohio', city='Columbus')

The next example makes this same assertion but for records where the
``state`` equals ``'Indiana'`` *or* ``'Ohio'``::

    self.assertValueSet('postal_code', state=['Indiana', 'Ohio'])


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

+----------------------------------------------+---------------------------------------+
| Class                                        | Loads                                 |
+==============================================+=======================================+
| :class:`CsvDataSource(file)                  | CSV from *file* (path or file-like    |
| <datatest.CsvDataSource>`                    | object)                               |
+----------------------------------------------+---------------------------------------+
| :class:`SqliteDataSource(connection, table)  | SQLite *table* from given             |
| <datatest.SqliteDataSource>`                 | *connection*                          |
+----------------------------------------------+---------------------------------------+


Common Methods
--------------

.. py:method:: columns()

    Return a list or tuple of column names.


.. py:method:: slow_iter()

    Return an iterable of dictionary rows (like ``csv.DictReader``).


.. py:method:: sum(column, **filter_by)

    Return sum of values in *column*.


.. py:method:: count(**filter_by)

    Return count of rows.


.. py:method:: unique(*column, **filter_by)

    Return iterable of tuples containing unique *column* values


.. py:method:: set(column, **filter_by)

    Convenience function for unwrapping single *column* results from
    ``unique`` and returning as a set.

-----------------------

.. autoclass:: datatest.CsvDataSource


.. autoclass:: datatest.SqliteDataSource


.. autoclass:: datatest.BaseDataSource



Data Source Wrappers
====================

+----------------------------------------------+---------------------------------------+
| Class                                        | Loads                                 |
+==============================================+=======================================+
| :class:`FilteredDataSource(function, source) | wrapper that filters *source* to      |
| <datatest.FilteredDataSource>`               | records where *function* returns true |
+----------------------------------------------+---------------------------------------+
| :class:`MultiDataSource(*sources)            | wrapper for multiple *sources* that   |
| <datatest.MultiDataSource>`                  | act as a single data source           |
+----------------------------------------------+---------------------------------------+
| :class:`UniqueDataSource(source, columns)    | wrapper that filters *source* to      |
| <datatest.UniqueDataSource>`                 | unique values in list of *columns*    |
+----------------------------------------------+---------------------------------------+

|

.. autoclass:: datatest.FilteredDataSource


.. autoclass:: datatest.MultiDataSource


.. autoclass:: datatest.UniqueDataSource


Errors and Differences
======================

.. autoclass:: datatest.DataAssertionError
   :members:


.. autoclass:: datatest.ExtraColumn
   :members:


.. autoclass:: datatest.MissingColumn
   :members:


.. autoclass:: datatest.ExtraValue
   :members:


.. autoclass:: datatest.MissingValue
   :members:


.. autoclass:: datatest.ExtraSum
   :members:


.. autoclass:: datatest.MissingSum
   :members:


Test Runner Program
===================

.. autoclass:: datatest.DataTestRunner
   :members:
   :inherited-members:


.. autoclass:: datatest.DataTestProgram(module='__main__', defaultTest=None, argv=None, testRunner=datatest.DataTestRunner, testLoader=unittest.TestLoader, exit=True, verbosity=1, failfast=None, catchbreak=None, buffer=None, warnings=None)
   :members:
   :inherited-members:

|

.. autoclass:: datatest.main
   :members:
   :inherited-members:
