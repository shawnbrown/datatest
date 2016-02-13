
************
Data Sources
************

Data source objects are used to access data in various formats.  For
additional sources, see :ref:`optional data sources <extra-sources>`
(below).

+----------------------------------------+---------------------------------------------+
| Class                                  | Loads                                       |
+========================================+=============================================+
| :class:`CsvSource(f)                   | CSV file *f* (path or file-like object)     |
| <datatest.CsvSource>`                  |                                             |
+----------------------------------------+---------------------------------------------+
| :class:`SqliteSource(c, t)             | table *t* from SQLite connection *c*        |
| <datatest.SqliteSource>`               |                                             |
+----------------------------------------+---------------------------------------------+
| :class:`MultiSource(*s)                | wrapper for multiple sources *s* that       |
| <datatest.MultiSource>`                | acts as a single data source                |
+----------------------------------------+---------------------------------------------+
| :class:`ExcelSource(p, worksheet=None) | Excel *worksheet* from XLSX or XLS path *p* |
| <datatest.ExcelSource>`                | (defaults to the first worksheet if None),  |
|                                        | requires `xlrd                              |
|                                        | <http://pypi.python.org/pypi/xlrd>`_        |
+----------------------------------------+---------------------------------------------+
| :class:`PandasSource(df)               | DataFrame *df*, requires `pandas            |
| <datatest.PandasSource>`               | <http://pypi.python.org/pypi/pandas>`_      |
+----------------------------------------+---------------------------------------------+

|

.. autoclass:: datatest.CsvSource
   :members: create_index

.. autoclass:: datatest.SqliteSource
   :members: create_index, from_records

.. autoclass:: datatest.MultiSource

    Data is aligned by column name and missing values are filled with empty
    strings:

        .. image:: _static/multisource.*

--------

.. _extra-sources:

If you have the appropriate, optional dependencies installed, datatest
provides a variety of other data sources:

.. autoclass:: datatest.ExcelSource

.. autoclass:: datatest.PandasSource
   :members: from_records


Common Methods
==============
Data sources implement a common set of methods which are used by
DataTestCase to access data and report meaningful failure messages.
Typically, these methods are used indirectly via DataTestCase but it is
also possible to call them directly:


.. py:method:: __iter__()

    Return an iterable of dictionary rows (like ``csv.DictReader``).


.. py:method:: columns()

    Return a list or tuple of column names.


.. py:method:: distinct(column, **filter_by)

    Return ResultSet containing distinct *column* values.


.. py:method:: sum(column, group_by=None, **filter_by)

    Returns sum of *column* grouped by *group_by* as ResultMapping.


.. py:method:: count(group_by=None, **filter_by)

    Returns count of rows grouped by *group_by* as ResultMapping.


.. py:method:: reduce(function, column, group_by=None, initializer=None, **filter_by)

    Apply *function* of two arguments cumulatively to the values in *column*,
    from left to right, so as to reduce the iterable to a single value.  If
    *column* is a string, the values are passed to *function* unchanged.  But
    if *column* is, itself, a function, it should accept a single dict-row and
    return a single value.  If *group_by* is omitted, the raw result is
    returned, otherwise returns a ResultMapping object.


*******************
Custom Data Sources
*******************

If you need to test data in a format that's not currently supported,
you can make your own custom data source.  You do this by subclassing
:class:`BaseSource` and implementing the basic, common methods.

As a starting point you can use this :download:`template.py
<_static/template.py>` file to write and test your custom data source.

.. autoclass:: datatest.BaseSource
    :members: __init__, __repr__, __iter__, columns, distinct, sum, count, reduce


*******************
Data Source Results
*******************

Querying a data source with various methods will return a ResultSet or a
ResultMapping.

.. autoclass:: datatest.ResultSet
    :members: make_rows, compare

.. autoclass:: datatest.ResultMapping
    :members: make_rows, compare

    .. py:attribute:: key_names

        Column names for result keys.
