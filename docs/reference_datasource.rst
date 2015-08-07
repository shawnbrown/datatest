
************
Data Sources
************

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
==============

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


Reference
=========

.. autoclass:: datatest.FilteredDataSource


.. autoclass:: datatest.MultiDataSource


.. autoclass:: datatest.UniqueDataSource


Custom Data Sources
===================

To make a custom data source, you need to write your own
:class:`BaseDataSource <datatest.BaseDataSource>` subclass.  You can
download :download:`template.py <_static/template.py>` to use as a
starting point (includes basic methods and unit tests).


How To
------


Class Template
``````````````

::

    import datatest

    class MyDataSource(datatest.BaseDataSource):
        def __init__(self):
            """Initialize self."""
            return NotImplemented

        def __repr__(self):
            """Return a string representation of the data source."""
            return NotImplemented

        def columns(self):
            """Return a sequence (e.g. a list) of column names."""
            return NotImplemented

        def slow_iter(self):
            """Return iterable of dict rows (like csv.DictReader)."""
            return NotImplemented

        #def sum(column, **filter_by):
        #    """Return sum of values in column."""

        #def count(column, **filter_by):
        #    """Return count of non-empty values in column."""

        #def unique(*column, **filter_by)
        #    """Return iterable of tuples of unique column values."""

