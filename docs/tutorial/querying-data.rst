
.. module:: datatest

.. meta::
    :description: Use datatest's DataSource, DataQuery, and DataResult
                  classes to handle the data under test.
    :keywords: datatest, DataSource, DataQuery, DataResult, working_directory


#############
Querying Data
#############

Datatest provides built-in classes for loading, querying, and
iterating over the data under test. Although users familiar with
other tools (Pandas, SQLAlchemy, etc.) should feel encouraged
to use whatever they find to be most productive.

..  To help use third-party data sources, datatest includes
    a number of helper functions to quickly load data into
    a variety of ORMs and DALs.

The following examples demonstrate datatest's :class:`DataSource`,
:class:`DataQuery`, and :class:`DataResult` classes. Users can
follow along and type the commands themselves at Python's
interactive prompt (``>>>``). For these examples, we will use
the following data:

    ===  ===  ===
     A    B    C
    ===  ===  ===
     x   foo   20
     x   foo   30
     y   foo   10
     y   bar   20
     z   bar   10
     z   bar   10
    ===  ===  ===


Loading Data
============

You can load the data from a CSV file (:download:`example.csv
</_static/example.csv>`) with :meth:`DataSource.from_csv`::

    >>> import datatest
    >>> source = datatest.DataSource.from_csv('example.csv')


Getting Field Names
===================

You can get a list of field names with :attr:`fieldnames
<DataSource.fieldnames>`::

    >>> source.fieldnames
    ['A', 'B', 'C']


.. sidebar:: The execute() Method

    In the following examples, we call :meth:`execute() <DataQuery.execute>`
    to eagerly evaluate the queries and display their results. In daily
    use, it's more efficient to leave off the "``.execute()``" part and
    validate the *un-executed* queries instead (which takes advantage of
    lazy evaluation).


Selecting Data
==============

Calling our source like a function returns a :class:`DataQuery`
for the specified field or fields.

Select elements from column **A**::

    >>> source('A').execute()
    ['x', 'x', 'y', 'y', 'z', 'z']

Select elements from column **A** as a :py:class:`set`::

    >>> source({'A'}).execute()
    {'x', 'y', 'z'}

Select elements from column **A** as a :py:class:`tuple`::

    >>> source(('A',)).execute()
    ('x', 'x', 'y', 'y', 'z', 'z')

The container type used in the selection determines the container
type returned in the result. You can think of the selection as a
template that describes the values and data types returned by the
query. When the outer container type is not specified, it defaults
to a :py:class:`list`. In the first example we selected ``'A'``
which is used as shorthand for ``['A']``::

    >>> source(['A']).execute()
    ['x', 'x', 'y', 'y', 'z', 'z']


Multiple Columns
----------------

Select elements from columns **A** and **B** as a list of tuples::

    >>> source(('A', 'B')).execute()  # Returns a list of tuples.
    [('x', 'foo'),
     ('x', 'foo'),
     ('y', 'foo'),
     ('y', 'bar'),
     ('z', 'bar'),
     ('z', 'bar')]

Select elements from columns **A** and **B** as a set of tuples::

    >>> source({('A', 'B')}).execute()  # Returns a set of tuples.
    {('x', 'foo'),
     ('y', 'foo'),
     ('y', 'bar'),
     ('z', 'bar')}

Compatible sequence and set types can be selected as inner and
outer containers as needed.

In addition to lists, tuples, and sets, users can also select
:py:class:`frozensets <frozenset>`, :py:func:`namedtuples
<collections.namedtuple>`, etc. However, normal object
limitations still apply---for example, sets can not contain
mutable objects like lists or other sets.


Groups of Columns
-----------------

:py:class:`dict`

Select groups of elements from column **A** that contain lists
of elements from column **B**::

    >>> source({'A': 'B'}).execute()  # Grouped by key.
    {'x': ['foo', 'foo'],
     'y': ['foo', 'bar'],
     'z': ['bar', 'bar']}

Select groups of elements from column **A** that contain
:py:class:`sets <set>` of elements from column **B**::

     >>> source({'A': {'B'}}).execute()  # Grouped by key.
     {'x': {'foo'},
      'y': {'foo', 'bar'},
      'z': {'bar'}}

Select groups of elements from columns **A** and **B** (using
a :py:class:`tuple`) that contain lists of elements from column
**C**::

    >>> source({('A', 'B'): 'C'}).execute()
    {('x', 'foo'): ['20', '30'],
     ('y', 'foo'): ['10'],
     ('y', 'bar'): ['20'],
     ('z', 'bar'): ['10', '10']}

When selecting groups of elements, you must provide a dictionary with
a single key-value pair. As before, the selection types determine the
result types, but keep in mind that dictionary keys must be `immutable
<http://docs.python.org/3/glossary.html#term-immutable>`_
(:py:class:`str`, :py:class:`tuple`, :py:class:`frozenset`, etc.).


Narrowing a Selection
=====================

Selections can be narrowed to rows that satisfy given keyword
arguments.

Narrow a selection to rows where column **B** equals "foo"::

    >>> source(('A', 'B'), B='foo').execute()
    [('x', 'foo'), ('x', 'foo'), ('y', 'foo')]

The keyword column does not have to be in the selected result::

    >>> source('A', B='foo').execute()
    ['x', 'x', 'y']

Narrow a selection to rows where column **A** equals "x" *or* "y"::

    >>> source(('A', 'B'), A=['x', 'y']).execute()
    [('x', 'foo'),
     ('x', 'foo'),
     ('y', 'foo'),
     ('y', 'bar')]

Narrow a selection to rows where column **A** equals "y" *and*
column **B** equals "bar"::

    >>> source([('A', 'B', 'C')], A='y', B='bar').execute()
    [('y', 'bar', '20')]

Only one row matches the above keyword conditions.


Additional Operations
=====================

:meth:`Sum <DataQuery.sum>` the values from column **C**::

    >>> source('C').sum().execute()
    100

Group by column **A** and sum the values from column **C** (for
each group)::

    >>> source({'A': 'C'}).sum().execute()
    {'x': 50, 'y': 30, 'z': 20}

Group by columns **A** and **B** and sum the values from column
**C**:

    >>> source({('A', 'B'): 'C'}).sum().execute()
    {('x', 'foo'): 50,
     ('y', 'foo'): 10,
     ('y', 'bar'): 20,
     ('z', 'bar'): 20}

Select :meth:`distinct <DataQuery.distinct>` values:

    >>> source('A').distinct().execute()
    ['x', 'y', 'z']

:meth:`Map <DataQuery.map>` values with a function:

    >>> def uppercase(value):
    ...     return str(value).upper()
    ...
    >>> source(['A']).map(uppercase).execute()
    ['X', 'X', 'Y', 'Y', 'Z', 'Z']


:meth:`Filter <DataQuery.filter>` values with a function:

    >>> def not_z(value):
    ...     return value != 'z'
    ...
    >>> source(['A']).filter(not_z).execute()
    ['x', 'x', 'y', 'y']

Multiple methods can be chained together:

    >>> def not_z(value):
    ...     return value != 'z'
    ...
    >>> def uppercase(value):
    ...     return str(value).upper()
    ...
    >>> source(['A']).filter(not_z).map(uppercase).execute()
    ['X', 'X', 'Y', 'Y']
