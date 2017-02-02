
.. module:: datatest

#############
API Reference
#############


.. _kwds-filter:

Filter by Keywords (using \*\*kwds_filter)
==========================================

Many datatest methods support optional keyword arguments to quickly filter the
data being tested.  For example, adding ``state='Ohio'`` to a data assertion
would limit the test to those records where the "state" column contains the
value "Ohio"::

    self.assertSubjectSet('postal_code', state='Ohio')

Multiple keywords can be used to further narrow the data being tested.  The
keyword filter ``state='Ohio', city='Columbus'`` limits the test to records
where the "state" column contains the value "Ohio" *and* the "city" column
contains the value "Columbus"::

    self.assertSubjectSet('postal_code', state='Ohio', city='Columbus')

Keyword arguments can also contain multiple values.  Using ``state=['Indiana',
'Ohio']`` limits the test to records where the "state" column contains the
value "Indiana" *or* the value "Ohio"::

    self.assertSubjectSet('postal_code', state=['Indiana', 'Ohio'])


.. _data-sources:

************
Data Sources
************

Data source objects are used to access data in various formats.

+---------------------------------------------+-----------------------------------------+
| Class                                       | Loads                                   |
+=============================================+=========================================+
| :class:`CsvSource(file)                     | CSV from path or file-like object       |
| <datatest.CsvSource>`                       | *file*                                  |
+---------------------------------------------+-----------------------------------------+
| :class:`SqliteSource(connection, table)     | *table* from SQLite *connection*        |
| <datatest.SqliteSource>`                    |                                         |
+---------------------------------------------+-----------------------------------------+
| :class:`ExcelSource(path, worksheet=None)   | Excel *worksheet* from XLSX or XLS      |
| <datatest.ExcelSource>`                     | *path*, defaults to the first worksheet |
|                                             | if None (requires :mod:`xlrd` package)  |
+---------------------------------------------+-----------------------------------------+
| :class:`PandasSource(df)                    | pandas DataFrame *df* (requires         |
| <datatest.PandasSource>`                    | :mod:`pandas`)                          |
+---------------------------------------------+-----------------------------------------+
| :class:`MultiSource(*sources)               | multiple data *sources* which can be    |
| <datatest.MultiSource>`                     | treated as single data source           |
+---------------------------------------------+-----------------------------------------+
| :class:`AdapterSource(source, interface)    | existing *source* with column names     |
| <datatest.AdapterSource>`                   | adapted to the given *interface*        |
+---------------------------------------------+-----------------------------------------+

.. autoclass:: datatest.BaseSource(...)

    .. automethod:: __repr__

    .. automethod:: columns

    .. automethod:: __iter__

    .. method:: filter_rows(**kwds)

        Returns iterable of dictionary rows (like
        :class:`csv.DictReader`) filtered by keywords.  E.g., where
        column1=value1, column2=value2, etc.

    .. method:: distinct(columns, **kwds_filter)

        Returns :class:`CompareSet` of distinct values or distinct tuples of
        values if given multiple *columns*.

    .. automethod:: sum

    .. automethod:: count

    .. automethod:: mapreduce


CsvSource
=========
.. autoclass:: datatest.CsvSource
   :members: create_index


SqliteSource
============
.. autoclass:: datatest.SqliteSource
   :members: create_index, from_records


-----------


.. _extra-sources:


ExcelSource
===========
.. autoclass:: datatest.ExcelSource
   :members: create_index


PandasSource
============
.. autoclass:: datatest.PandasSource


-----------


MultiSource
===========
.. autoclass:: datatest.MultiSource

    Data is aligned by column name and empty cells are filled with the
    given *missing* value (defaults to empty string):

    .. image:: _static/multisource.*


AdapterSource
=============
.. autoclass:: datatest.AdapterSource


******************
Comparison Objects
******************


CompareSet
==========
.. autoclass:: datatest.CompareSet
    :members: make_rows, compare


CompareDict
===========
.. autoclass:: datatest.CompareDict
    :members: make_rows, compare

    .. py:attribute:: key_names

        Column names for result keys.


**********************
Errors and Differences
**********************

.. autoexception:: datatest.DataError

    .. autoattribute:: differences

Differences
===========

.. autoclass:: datatest.Missing


.. autoclass:: datatest.Extra


.. autoclass:: datatest.Invalid


.. autoclass:: datatest.Deviation



**********
Allowances
**********

+---------------------------------------------------------+------------------------------------------+
| Context Manager                                         | Allows                                   |
+=========================================================+==========================================+
| :class:`allow_only(differences) <datatest.allow_only>`  | only specified *differences*             |
+---------------------------------------------------------+------------------------------------------+
| :class:`allow_any(**kwds_func) <datatest.allow_any>`    | differences of any type that match given |
|                                                         | :ref:`keyword filters <kwds-filter>`     |
+---------------------------------------------------------+------------------------------------------+
| :class:`allow_missing() <datatest.allow_missing>`       | :class:`Missing <datatest.Missing>`      |
|                                                         | differences                              |
+---------------------------------------------------------+------------------------------------------+
| :class:`allow_extra() <datatest.allow_extra>`           | :class:`Extra <datatest.Extra>`          |
|                                                         | differences                              |
+---------------------------------------------------------+------------------------------------------+
| :class:`allow_limit(number) <datatest.allow_limit>`     | given *number* of differences of any     |
|                                                         | type                                     |
+---------------------------------------------------------+------------------------------------------+
| :class:`allow_deviation(tolerance)                      | :class:`Deviations <datatest.Deviation>` |
| <datatest.allow_deviation>`                             | of plus or minus given *tolerance*       |
+---------------------------------------------------------+------------------------------------------+
| :class:`allow_percent_deviation(tolerance)              | :class:`Deviations <datatest.Deviation>` |
| <datatest.allow_percent_deviation>`                     | of plus or minus given *tolerance*       |
|                                                         | percentage                               |
+---------------------------------------------------------+------------------------------------------+

.. autoclass:: datatest.allow_only


.. autoclass:: datatest.allow_any


.. autoclass:: datatest.allow_missing


.. autoclass:: datatest.allow_extra


.. autoclass:: datatest.allow_limit


.. class:: allow_deviation(tolerance, /, msg=None, **kwds_func)
           allow_deviation(lower, upper, msg=None, **kwds_func)

    Context manager that allows :class:`Deviations <datatest.Deviation>`
    within a given *tolerance* without triggering a test failure::

        with datatest.allow_deviation(5):  # tolerance of +/- 5
            ...

    Specifying different *lower* and *upper* bounds::

        with datatest.allow_deviation(-2, 3):  # tolerance from -2 to +3
            ...

    Deviations within the given range are suppressed while those
    outside the range will trigger a test failure.

    Empty values (None, empty string, etc.) are treated as zeros when
    performing comparisons.


.. class:: allow_percent_deviation(tolerance, /, msg=None, **kwds_func)
           allow_percent_deviation(lower, upper, msg=None, **kwds_func)

    Context manager that allows :class:`Deviations <datatest.Deviation>`
    within a given percentage of error without triggering a test
    failure::

        with datatest.allow_percent_deviation(0.03):  # tolerance of +/- 3%
            ...

    Specifying different *lower* and *upper* bounds::

        with datatest.allow_percent_deviation(-0.02, 0.01):  # tolerance from -2% to +1%
            ...

    Deviations within the given range are suppressed while those
    outside the range will trigger a test failure.

    Empty values (None, empty string, etc.) are treated as zeros when
    performing comparisons.


.. autoclass:: datatest.allow_iter
