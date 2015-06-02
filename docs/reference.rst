
Package Reference
=================


Test Case
------------

.. autoclass:: datatest.DataTestCase
   :members:


Data Sources
------------

A key feature introduced by `datatest` is the data source interface.
Data sources implement a common set of methods which are used by
DataTestCase to access data and report meaningful failure messages.

.. autoclass:: datatest.BaseDataSource
   :members: __init__, __str__, slow_iter, columns, set, sum, count, groups

.. autoclass:: datatest.SqliteDataSource
   :members:
   :inherited-members:

.. autoclass:: datatest.CsvDataSource
   :members:
   :inherited-members:

.. autoclass:: datatest.MultiDataSource
   :members:
   :inherited-members:


Errors and Differences
----------------------

.. autoclass:: datatest.DataAssertionError
   :members:

.. autoclass:: datatest.ExtraColumn
   :members:

.. autoclass:: datatest.ExtraValue
   :members:

.. autoclass:: datatest.ExtraSum
   :members:

.. autoclass:: datatest.MissingColumn
   :members:

.. autoclass:: datatest.MissingValue
   :members:

.. autoclass:: datatest.MissingSum
   :members:


Test Runner Program
-------------------

.. autoclass:: datatest.DataTestRunner
   :members:

.. autoclass:: datatest.DataTestProgram(module='__main__', defaultTest=None, argv=None, testRunner=datatest.DataTestRunner, testLoader=unittest.TestLoader, exit=True, verbosity=1, failfast=None, catchbreak=None, buffer=None, warnings=None)
   :members:

.. autoclass:: datatest.main
   :members:
