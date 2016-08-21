
.. module:: datatest

#############
API Reference
#############


************
DataTestCase
************

.. autoclass:: datatest.DataTestCase

    .. autoattribute:: subject
    .. autoattribute:: reference

    .. automethod:: assertValid

    .. _assert-methods:

    +-----------------------------------------------------------------+------------------------------------------+
    | Subject method                                                  | Checks :attr:`subject` to assure that    |
    +=================================================================+==========================================+
    | :meth:`assertSubjectColumns(required=None)                      | column names match *required*            |
    | <datatest.DataTestCase.assertSubjectColumns>`                   |                                          |
    +-----------------------------------------------------------------+------------------------------------------+
    | :meth:`assertSubjectSet(columns, required=None)                 | one or more *columns* contains           |
    | <datatest.DataTestCase.assertSubjectSet>`                       | *required*                               |
    +-----------------------------------------------------------------+------------------------------------------+
    | :meth:`assertSubjectSum(column, keys, required=None)            | sums of *column* values, grouped by      |
    | <datatest.DataTestCase.assertSubjectSum>`                       | *keys*, match *required* dict            |
    +-----------------------------------------------------------------+------------------------------------------+
    | :meth:`assertSubjectRegex(column, required)                     | *required*.search(val) for each val in   |
    | <datatest.DataTestCase.assertSubjectRegex>`                     | *column*                                 |
    +-----------------------------------------------------------------+------------------------------------------+
    | :meth:`assertSubjectNotRegex(column, required)                  | not *required*.search(val) for each val  |
    | <datatest.DataTestCase.assertSubjectNotRegex>`                  | in *column*                              |
    +-----------------------------------------------------------------+------------------------------------------+
    | :meth:`assertSubjectUnique(columns)                             | values in *columns* are unique and       |
    | <datatest.DataTestCase.assertSubjectUnique>`                    | contain no duplicates                    |
    +-----------------------------------------------------------------+------------------------------------------+

    .. automethod:: assertSubjectColumns
    .. automethod:: assertSubjectSet
    .. automethod:: assertSubjectSum
    .. automethod:: assertSubjectRegex
    .. automethod:: assertSubjectNotRegex
    .. automethod:: assertSubjectUnique


    +---------------------------------------------------------+------------------------------------------+
    | Context Manager                                         | Allows                                   |
    +=========================================================+==========================================+
    | :meth:`allowOnly(differences) <DataTestCase.allowOnly>` | only specified *differences*             |
    +---------------------------------------------------------+------------------------------------------+
    | :meth:`allowAny(**kwds) <DataTestCase.allowAny>`        | differences of any type that match given |
    |                                                         | :ref:`keyword filters <kwds-filter>`     |
    +---------------------------------------------------------+------------------------------------------+
    | :meth:`allowMissing() <DataTestCase.allowMissing>`      | :class:`Missing <datatest.Missing>`      |
    |                                                         | differences                              |
    +---------------------------------------------------------+------------------------------------------+
    | :meth:`allowExtra() <DataTestCase.allowExtra>`          | :class:`Extra <datatest.Extra>`          |
    |                                                         | differences                              |
    +---------------------------------------------------------+------------------------------------------+
    | :meth:`allowLimit(number) <DataTestCase.allowLimit>`    | given *number* of differences of any     |
    |                                                         | type                                     |
    +---------------------------------------------------------+------------------------------------------+
    | :meth:`allowDeviation(tolerance)                        | :class:`Deviations <datatest.Deviation>` |
    | <DataTestCase.allowDeviation>`                          | of plus or minus given *tolerance*       |
    +---------------------------------------------------------+------------------------------------------+
    | :meth:`allowPercentDeviation(tolerance)                 | :class:`Deviations <datatest.Deviation>` |
    | <DataTestCase.allowPercentDeviation>`                   | of plus or minus given *tolerance*       |
    |                                                         | percentage                               |
    +---------------------------------------------------------+------------------------------------------+

    .. automethod:: allowOnly

    .. automethod:: allowAny

    .. automethod:: allowMissing

    .. automethod:: allowExtra

    .. automethod:: allowLimit

    .. method:: allowDeviation(tolerance, /, msg=None, **kwds_filter)
                allowDeviation(lower, upper, msg=None, **kwds_filter)

        A convenience wrapper for :class:`allow_deviation`.

        .. code-block:: python

            with self.allowDeviation(5):  # tolerance of +/- 5
                self.assertSubjectSum('column2', keys=['column1'])

        .. THE ABOVE DEFINITION SHOULD BE REPLICATED FROM THE DOCSTRING IN
           THE datatest.case SUB-PACKAGE.  THE "AUTOCLASS" FUNCTIONALITY
           IS NOT USED IN THIS CASE BECAUSE THIS CLASS' __init__ METHOD
           HAS TWO SIGNATURES.

    .. method:: allowPercentDeviation(tolerance, /, msg=None, **kwds_filter)
                allowPercentDeviation(lower, upper, msg=None, **kwds_filter)

        A convenience wrapper for :class:`allow_percent_deviation`.

        .. code-block:: python

            with self.allowPercentDeviation(0.02):  # tolerance of +/- 2%
                self.assertSubjectSum('column2', keys=['column1'])

        .. THE ABOVE DEFINITION SHOULD BE REPLICATED FROM THE DOCSTRING IN
           THE datatest.case SUB-PACKAGE.  THE "AUTOCLASS" FUNCTIONALITY
           IS NOT USED IN THIS CASE BECAUSE THIS CLASS' __init__ METHOD
           HAS TWO SIGNATURES.

    .. note:: The "``tolerance, /``" part of these method signatures
              mean that *tolerance* is a positional-only parameter---it
              cannot be specified using keyword syntax.


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


*********************
Error and Differences
*********************

.. autoclass:: datatest.DataError

    .. autoattribute:: differences

-----------------

.. autoclass:: datatest.BaseDifference(...)

    .. autoattribute:: value
    .. autoattribute:: required
    .. autoattribute:: kwds

.. autoclass:: datatest.Extra
   :members:

.. autoclass:: datatest.Missing
   :members:

.. autoclass:: datatest.Invalid
   :members:

.. autoclass:: datatest.Deviation
   :members:


**********
Allowances
**********

.. autoclass:: datatest.allow_only
   :members:

.. autoclass:: datatest.allow_any
   :members:

.. autoclass:: datatest.allow_missing
   :members:

.. autoclass:: datatest.allow_extra
   :members:

.. autoclass:: datatest.allow_limit
   :members:

.. class:: allow_deviation(tolerance, /, msg=None, **kwds)
           allow_deviation(lower, upper, msg=None, **kwds)

    Context manager to allow for deviations from required numeric values
    without triggering a test failure.

    Allowing deviations of plus-or-minus a given *tolerance*::

        with datatest.allow_deviation(5):  # tolerance of +/- 5
            ...

    Specifying different *lower* and *upper* bounds::

        with datatest.allow_deviation(-2, 3):  # tolerance from -2 to +3
            ...

    All deviations within the accepted tolerance range are suppressed
    but those outside the range will trigger a test failure.

    When allowing deviations, empty values (like None or empty string)
    are treated as zeros.

    .. THE ABOVE DEFINITION SHOULD BE REPLICATED FROM THE DOCSTRING IN
       THE datatest.allow SUB-PACKAGE.  THE "AUTOCLASS" FUNCTIONALITY
       IS NOT USED IN THIS CASE BECAUSE THIS CLASS' __init__ METHOD
       HAS TWO SIGNATURES.

.. class:: allow_percent_deviation(tolerance, /, msg=None, **kwds)
           allow_percent_deviation(lower, upper, msg=None, **kwds)

    Context manager to allow for deviations from required numeric values
    within a given error percentage without triggering a test failure.

    Allowing deviations of plus-or-minus a given *tolerance*::

        with datatest.allow_percent_deviation(0.02):  # tolerance of +/- 2%
            ...

    Specifying different *lower* and *upper* bounds::

        with datatest.allow_percent_deviation(-0.02, 0.03):  # tolerance from -2% to +3%
            ...

    All deviations within the accepted tolerance range are suppressed
    but those that exceed the range will trigger a test failure.

    When allowing deviations, empty values (like None or empty string)
    are treated as zeros.

    .. THE ABOVE DEFINITION SHOULD BE REPLICATED FROM THE DOCSTRING IN
       THE datatest.allow SUB-PACKAGE.  THE "AUTOCLASS" FUNCTIONALITY
       IS NOT USED IN THIS CASE BECAUSE THIS CLASS' __init__ METHOD
       HAS TWO SIGNATURES.

.. autoclass:: datatest.allow_each
   :members:

.. autoclass:: datatest.allow_iter
   :members:


*******************
Test Runner Program
*******************

.. py:decorator:: datatest.mandatory

    A decorator to mark whole test cases or individual methods as
    mandatory.  If a mandatory test fails, DataTestRunner will stop
    immediately (this is similar to the ``--failfast`` command line
    argument behavior)::

        @datatest.mandatory
        class TestFileFormat(datatest.DataTestCase):
            def test_columns(self):
                ...

.. py:decorator:: datatest.skip(reason)

    A decorator to unconditionally skip a test::

        @datatest.skip('Not finished collecting raw data.')
        class TestSumTotals(datatest.DataTestCase):
            def test_totals(self):
                ...

.. py:decorator:: datatest.skipIf(condition, reason)

    A decorator to skip a test if the condition is true.

.. py:decorator:: datatest.skipUnless(condition, reason)

    A decorator to skip a test unless the condition is true.

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
