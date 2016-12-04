
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

    .. method:: assertValid(data, requirement, msg=None)

        Fail if *data* does not satisfy *requirement*.

        .. code-block:: python

            def test_mydata(self):
                data = ...
                requirement = ...
                self.assertValid(data, requirement)

        The *data* can be a set, mapping, sequence, iterable, or
        other object. The *requirement* type determines how the
        *data* is checked:

        +-------------------------------------+--------------------+
        |                                     | When *requirement* |
        | Check that *data* values...         | is...              |
        +=====================================+====================+
        | are members of set                  | set                |
        +-------------------------------------+--------------------+
        | return True when passed to callable | callable           |
        +-------------------------------------+--------------------+
        | match regular expression pattern    | regex object       |
        +-------------------------------------+--------------------+
        | equal string or object              | str or other       |
        +-------------------------------------+--------------------+
        | equal string or object of matching  | mapping            |
        | key                                 |                    |
        +-------------------------------------+--------------------+
        | equal string or object in matching  | sequence           |
        | order                               |                    |
        +-------------------------------------+--------------------+

        **Alternative Method Signature:**

        When using reference data, it's common to make pairs of calls
        using the same parameters (one for the :attr:`subject` and one
        for the :attr:`reference`).  To reduce this duplication,
        :meth:`assertValid` provides an alternative, helper-function
        shorthand.

        .. method:: assertValid(function, /, msg=None)

            Helper-function shorthand::

                def test_population(self):
                    def helperfn(x):
                        return x('population', state='TX').sum()
                    self.assertValid(helperfn)

            Equivalent test without helper-function::

                def test_population(self):
                    data = self.subject('population', state='TX').sum()
                    requirement = self.reference('population', state='TX').sum()
                    self.assertValid(data, requirement)

            When provided, a helper-function fetches data from both
            :attr:`subject` and :attr:`reference` before comparing the
            results.  Without it, two separate calls would be required.

    .. automethod:: allowOnly

    .. automethod:: allowAny

    .. automethod:: allowMissing

    .. automethod:: allowExtra

    .. automethod:: allowLimit

    .. method:: allowDeviation(tolerance, /, msg=None, **kwds_func)
                allowDeviation(lower, upper, msg=None, **kwds_func)

        alias of :class:`allow_deviation`

        .. code-block:: python

            with self.allowDeviation(5):  # tolerance of +/- 5
                data = ...
                requirement = ...
                self.assertValid(data, requirement)

        .. code-block:: python

            with datatest.allowDeviation(-2, 3):  # tolerance from -2 to +3
                data = ...
                requirement = ...
                self.assertValid(data, requirement)

    .. method:: allowPercentDeviation(tolerance, /, msg=None, **kwds_func)
                allowPercentDeviation(lower, upper, msg=None, **kwds_func)

        alias of :class:`allow_percent_deviation`

        .. code-block:: python

            with self.allowPercentDeviation(0.03):  # tolerance of +/- 3%
                data = ...
                requirement = ...
                self.assertValid(data, requirement)

        .. code-block:: python

            with self.allowPercentDeviation(-0.02, 0.01):  # tolerance from -2% to +1%
                data = ...
                requirement = ...
                self.assertValid(data, requirement)

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
