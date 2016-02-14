
.. module:: datatest

###############
Module Contents
###############


************
DataTestCase
************

This class inherits from
`unittest.TestCase <http://docs.python.org/library/unittest.html#unittest.TestCase>`_
and adds additional properties and methods to help with testing data.
In addition to the new functionality, the familiar ``TestCase`` methods
(like ``setUp``, ``assertEqual``, etc.) are still available.

.. autoclass:: datatest.DataTestCase

    .. autoattribute:: subjectData
    .. autoattribute:: referenceData

    .. _assert-methods:

    Column assertions operate on the column names (or header row) of a
    data source:

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

    .. automethod:: assertColumnSet
    .. automethod:: assertColumnSubset
    .. automethod:: assertColumnSuperset

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
    | :meth:`assertValueSuperset(c)                | subject vals >= reference vals in column *c*       |
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

    .. automethod:: assertValueSet
    .. automethod:: assertValueSubset
    .. automethod:: assertValueSuperset
    .. automethod:: assertValueSum
    .. automethod:: assertValueCount
    .. automethod:: assertValueRegex
    .. automethod:: assertValueNotRegex

    +-----------------------------------------------------+------------------------------------------+
    | Context Manager                                     | Allows                                   |
    +=====================================================+==========================================+
    | :meth:`allowSpecified(diff)                         | specified collection of *differences*    |
    | <datatest.DataTestCase.allowSpecified>`             |                                          |
    +-----------------------------------------------------+------------------------------------------+
    | :meth:`allowUnspecified(number)                     | given *number* of unspecified            |
    | <datatest.DataTestCase.allowUnspecified>`           | differences                              |
    +-----------------------------------------------------+------------------------------------------+
    | :meth:`allowDeviation(deviation)                    | positive or negative numeric differences |
    | <datatest.DataTestCase.allowDeviation>`             | equal to or less than *deviation*        |
    +-----------------------------------------------------+------------------------------------------+
    | :meth:`allowDeviationUpper(deviation)               | positive numeric differences             |
    | <datatest.DataTestCase.allowDeviationUpper>`        | equal to or less than *deviation*        |
    +-----------------------------------------------------+------------------------------------------+
    | :meth:`allowDeviationLower(deviation)               | negative numeric differences             |
    | <datatest.DataTestCase.allowDeviationLower>`        | equal to or less than *deviation*        |
    +-----------------------------------------------------+------------------------------------------+
    | :meth:`allowPercentDeviation(deviation)             | positive or negative numeric differences |
    | <datatest.DataTestCase.allowPercentDeviation>`      | equal to or less than *deviation* as a   |
    |                                                     | percentage of the matching reference     |
    +-----------------------------------------------------+------------------------------------------+

    .. automethod:: allowSpecified
    .. automethod:: allowUnspecified
    .. automethod:: allowDeviation
    .. automethod:: allowDeviationUpper
    .. automethod:: allowDeviationLower
    .. automethod:: allowPercentDeviation


Optional Keyword Filters (using \*\*filter_by)
==============================================

All of the value assertion methods, above, support optional keyword
arguments to quickly filter the rows to be tested.

The following example asserts that the subject's ``postal_code`` values
match the reference's ``postal_code`` values but only for records where
the ``state`` equals ``'Ohio'`` and the ``city`` equals ``'Columbus'``::

    self.assertValueSet('postal_code', state='Ohio', city='Columbus')

The next example makes this same assertion but for records where the
``state`` equals ``'Indiana'`` *or* ``'Ohio'``::

    self.assertValueSet('postal_code', state=['Indiana', 'Ohio'])


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


CsvSource
=========
.. autoclass:: datatest.CsvSource
   :members: create_index


SqliteSource
============
.. autoclass:: datatest.SqliteSource
   :members: create_index, from_records


MultiSource
===========
.. autoclass:: datatest.MultiSource

    Data is aligned by column name and missing values are filled with empty
    strings:

        .. image:: _static/multisource.*

--------

.. _extra-sources:

If you have the appropriate, optional dependencies installed, datatest
provides a variety of other data sources:


ExcelSource
===========
.. autoclass:: datatest.ExcelSource


PandasSource
============
.. autoclass:: datatest.PandasSource
   :members: from_records


*******************
Data Source Methods
*******************

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


***************
Results Objects
***************

Querying a data source with various methods will return a ResultSet or a
ResultMapping.


ResultSet
=========
.. autoclass:: datatest.ResultSet
    :members: make_rows, compare


ResultMapping
=============
.. autoclass:: datatest.ResultMapping
    :members: make_rows, compare

    .. py:attribute:: key_names

        Column names for result keys.


**********************
Errors and Differences
**********************

.. autoclass:: datatest.DataAssertionError
   :members:

.. autoclass:: datatest.ExtraItem
   :members:

.. autoclass:: datatest.MissingItem
   :members:

.. autoclass:: datatest.InvalidItem
   :members:

.. autoclass:: datatest.InvalidNumber
   :members:


*******************
Test Runner Program
*******************

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
