
.. module:: datatest

.. meta::
    :description: working with data sources
    :keywords: datatest, DataSource, DataQuery, DataResult


################
Data Sources API
################

It's important to have a convinient and expressive way to load
and query data. Datatest provides a :class:`DataSource` class
that should cover many common use cases. But users already familiar
with other tools (Pandas, SQLAlchemy, etc.) should feel free to
use them instead.

..  To help use third-party data sources, datatest includes a number of
    helper functions to quickly load data into a variety of ORMs and DALs.


***********************
Load and Query Examples
***********************

The following code samples demonstrate ways to load and query
data using a :class:`DataSource`. In these examples, we will
use the data below:

    ===  ===  =====
    one  two  three
    ===  ===  =====
     a    x    100
     a    x    100
     b    x    100
     b    y    100
     c    y    100
     c    y    100
    ===  ===  =====


Loading Data
============

Load our data from a CSV file (:download:`example.csv
<_static/example.csv>`)::

    >>> import datatest
    >>> source = datatest.DataSource.from_csv('example.csv')


Column Names
============

You can get a list of column names from source with the
:meth:`columns() <DataSource.columns>` method::

    >>> source.columns()
    ['one', 'two', 'three']


Selecting Data
==============

Calling our source like a function returns a :class:`DataQuery`
for the specified column or columns. The :meth:`execute()
<DataQuery.execute>` method runs the query and returns the
results.

Select elements from column **one** as a :py:class:`list`::

    >>> source(['one']).execute()
    ['a', 'a', 'b', 'b', 'c', 'c']

Select elements from column **one** as a :py:class:`set`::

    >>> source({'one'}).execute()
    {'a', 'b', 'c'}

The container type used in the selection determines the container type
returned in the result. Selecting a column as a list will return a
list of elements. Selecting the same column as a set will return a set
of elements. Because :py:class:`set` objects can not contain duplicates,
the second result has only one element for each unique value in the
source.


Multiple Columns
----------------

Select elements from columns **one** and **two** using a list of
:py:class:`tuple` values::

    >>> source([('one', 'two')]).execute()  # Returns a list of tuples.
    [('a', 'x'),
     ('a', 'x'),
     ('b', 'x'),
     ('b', 'y'),
     ('c', 'y'),
     ('c', 'y')]

Select elements from columns **one** and **two** using a set of tuple
values::

    >>> source({('one', 'two')}).execute()  # Returns a set of tuples.
    {('a', 'x'),
     ('b', 'x'),
     ('b', 'y'),
     ('c', 'y')}


Groups of Columns
-----------------

Group and select column elements using a :py:class:`dict`::

    >>> source({'one': ['three']}).execute()  # Grouped by key.
    {'a': ['100', '100'],
     'b': ['100', '100'],
     'c': ['100', '100']}

Group and select column elements using a :py:class:`dict` with a
:py:class:`tuple` of keys::

    >>> source({('one', 'two'): ['three']}).execute()
    {('a', 'x'): ['100', '100'],
     ('b', 'x'): ['100'],
     ('b', 'y'): ['100'],
     ('c', 'y'): ['100', '100']}

When selecting groups of elements, you must provide a dictionary with
a single key-value pair. As before, the selection types determine the
result types but keep in mind that dictionary keys must be `immutable
<http://docs.python.org/3/glossary.html#term-immutable>`_
(:py:class:`str`, :py:class:`tuple`, :py:class:`frozenset`, etc.).


Narrowing a Selection
---------------------

Selections can be narrowed to rows that satisfy given keyword
arguments.

Narrow a selection to rows where column **two** equals "x"::

    >>> source([('one', 'two')], two='x').execute()
    [('a', 'x'),
     ('a', 'x'),
     ('b', 'x')]

The keyword column does not have to be in the selected result::

    >>> source(['one'], two='x').execute()
    ['a',
     'a',
     'b']

Narrow a selection to rows where column **one** equals "a" *or* "b"::

    >>> source([('one', 'two')], one=['a', 'b']).execute()
    [('a', 'x'),
     ('a', 'x'),
     ('b', 'x'),
     ('b', 'y')]

Narrow a selection to rows where column **one** equals "b" *and*
column **two** equals "y"::

    >>> source([('one', 'two')], one='b', two='y').execute()
    [('b', 'y')]  # Only 1 row matches these keyword conditions.


Query Operations
================

:meth:`Sum <DataQuery.sum>` the values from column **three**::

    >>> source(['three']).sum().execute()
    600

Group by column **one** and sum the values from column **three** (for
each group)::

    >>> source({'one': ['three']}).sum().execute()
    {'a': 200,
     'b': 200,
     'c': 200}

Group by columns **one** and **two** and sum the values from column
**three**::

    >>> source({('one', 'two'): ['three']}).sum().execute()
    {('a', 'x'): 200,
     ('b', 'x'): 100,
     ('b', 'y'): 100,
     ('c', 'y'): 200}

Select :meth:`distinct <DataQuery.distinct>` values::

    >>> source(['one']).distinct().execute()
    ['a', 'b', 'c']

:meth:`Map <DataQuery.map>` values with a function::

    >>> def uppercase(x):
    ...     return str(x).upper()
    ...
    >>> source(['one']).map(uppercase).execute()
    ['A', 'A', 'B', 'B', 'C', 'C']

:meth:`Reduce <DataQuery.reduce>` values with a function::

    >>> def concatenate(x, y):
    ...     return '{0}{1}'.format(x, y)
    ...
    >>> source(['one']).reduce(concatenate).execute()
    'aabbcc'

:meth:`Filter <DataQuery.filter>` values with a function::

    >>> def not_c(x):
    ...     return x != 'c'
    ...
    >>> source(['one']).filter(not_c).execute()
    ['a', 'a', 'b', 'b']

Multiple methods can be chained together:

    >>> def uppercase(x):
    ...     return str(x).upper()
    ...
    >>> def concatenate(x, y):
    ...     return '{0}{1}'.format(x, y)
    ...
    >>> source(['one']).map(uppercase).reduce(concatenate).execute()
    'AABBCC'


**********
DataSource
**********

.. autoclass:: DataSource

    .. automethod:: from_csv

    .. automethod:: from_excel

    .. automethod:: columns

    .. automethod:: __call__


*********
DataQuery
*********

.. autoclass:: DataQuery

    .. attribute:: default_source

        A property for setting a predetermined :class:`DataSource`
        to use when :meth:`execute` is called without a *source*
        argument.

        When a query is created from a DataSource call, this property
        is assigned automatically. When a query is created directly,
        the value defaults to None (and setting it is optional).

    .. automethod:: sum

    .. automethod:: count

    .. automethod:: avg

    .. automethod:: min

    .. automethod:: max

    .. automethod:: distinct

    .. automethod:: map

    .. automethod:: filter

    .. automethod:: reduce

    .. automethod:: execute

    .. automethod:: __call__


**********
DataResult
**********

.. autoclass:: DataResult

    .. attribute:: evaluation_type

        The type of instance returned by the
        :meth:`evaluate <DataResult.evaluate>` method.

    .. automethod:: evaluate

    .. attribute:: __wrapped__

        The underlying iterator---useful when introspecting
        or rewrapping.


*****************
working_directory
*****************

.. autoclass:: working_directory
