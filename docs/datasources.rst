
************
Data Sources
************

Data source objects are used to access data in various formats.

+----------------------------------+---------------------------------------+
| Class                            | Loads                                 |
+==================================+=======================================+
| :class:`CsvDataSource(f)         | CSV file *f* (path or file-like       |
| <datatest.CsvDataSource>`        | object)                               |
+----------------------------------+---------------------------------------+
| :class:`SqliteDataSource(c, t)   | table *t* from SQLite connection *c*  |
| <datatest.SqliteDataSource>`     |                                       |
+----------------------------------+---------------------------------------+

|

.. autoclass:: datatest.CsvDataSource

.. autoclass:: datatest.SqliteDataSource


The following "wrapper" classes can be used to alter an existing data
source object:

+----------------------------------------------+-----------------------------------------+
| Class                                        | Loads                                   |
+==============================================+=========================================+
| :class:`FilteredDataSource(f, s)             | wrapper that filters source *s* to      |
| <datatest.FilteredDataSource>`               | records where function *f* returns True |
+----------------------------------------------+-----------------------------------------+
| :class:`MultiDataSource(*s)                  | wrapper for multiple sources *s* that   |
| <datatest.MultiDataSource>`                  | act as a single data source             |
+----------------------------------------------+-----------------------------------------+
| :class:`UniqueDataSource(s, c)               | wrapper that filters source *s* to      |
| <datatest.UniqueDataSource>`                 | unique values in list of columns *c*    |
+----------------------------------------------+-----------------------------------------+

These wrappers allow for a great deal of flexibility but extensive use
could make testing slow.  If you find that testing has become slow
because of a wrapper, you may be able to improve performance by loading
it into a faster class that supports the :meth:`from_source`
constructor::

    subjectData = datatest.SqliteDataSource.from_source(subjectData)


.. autoclass:: datatest.FilteredDataSource

.. autoclass:: datatest.MultiDataSource

.. autoclass:: datatest.UniqueDataSource


Common Methods
==============
Data sources implement a common set of methods which are used by
DataTestCase to access data and report meaningful failure messages.
Typically, these methods are used indirectly via DataTestCase but it is
also possible to call them directly:


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



*******************
Custom Data Sources
*******************

If you need to test data in a format that's not currently supported,
you can make your own custom data source.  You do this by subclassing
:class:`BaseDataSource` and implementing the basic, common methods.

As a starting point, you can use one of the following templates:

+-------------------------------+------------------------------------------+
| Template File                 | Used for...                              |
+===============================+==========================================+
| :download:`native_template.py | Formats with fast, built-in access to    |
| <_static/template.py>`        | stored data (e.g., SQL, pandas, etc.)    |
+-------------------------------+------------------------------------------+
| :download:`loader_template.py | Storage formats with no fast access to   |
| <_static/template.py>`        | data (internally reuses SqliteDataSource |
|                               | for faster performance).                 |
+-------------------------------+------------------------------------------+

|

.. autoclass:: datatest.BaseDataSource
    :members: __init__, __repr__, columns, slow_iter, sum, count, unique

