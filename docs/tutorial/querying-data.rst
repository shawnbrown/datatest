
.. currentmodule:: datatest

.. meta::
    :description: Use datatest's Select, Query, and Result
                  classes to handle the data under test.
    :keywords: datatest, Select, Query, Result, working_directory

.. highlight:: python

.. _querying-data:

#############
Querying Data
#############

Datatest provides built-in classes for selecting, querying, and
iterating over the data under test. Although users familiar with
other tools (Pandas, SQLAlchemy, etc.) should feel encouraged
to use whatever they find to be most productive.

The following examples demonstrate datatest's :class:`Select`,
:class:`Query`, and :class:`Result` classes. Users can follow along
and type the commands themselves at Python's interactive prompt
(``>>>``). For these examples, we will use the following data:

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
</_static/example.csv>`) into a :class:`Select` object::

    >>> import datatest
    >>> select = datatest.Select('example.csv')


Getting Field Names
===================

You can get a list of field names with the :attr:`fieldnames
<Select.fieldnames>` attribute::

    >>> select.fieldnames
    ['A', 'B', 'C']


.. sidebar:: The fetch() Method

    In the following examples, we call :meth:`fetch() <Query.fetch>`
    to eagerly evaluate the queries and display their results. In daily
    use, it's more efficient to leave off the "``.fetch()``" part and
    validate the *un-fetched* queries instead (which takes advantage of
    lazy evaluation).


Selecting Data
==============

Calling our select object like a function returns a :class:`Query`
for the specified field or fields.

Select elements from column **A**::

    >>> select('A').fetch()
    ['x', 'x', 'y', 'y', 'z', 'z']

Select elements from column **A** as a :py:class:`set`::

    >>> select({'A'}).fetch()
    {'x', 'y', 'z'}

Select elements from column **A** as a :py:class:`tuple`::

    >>> select(('A',)).fetch()
    ('x', 'x', 'y', 'y', 'z', 'z')

The container type used in the selection determines the container
type returned in the result. You can think of the selection as a
template that describes the values and data types returned by the
query.

When specifying an outer container type, the container must hold
only one item. When an outer container type is not specified, it
defaults to a :py:class:`list`. So when the first example used
``select('A')``, that was actually shorthand for ``select(['A'])``.


Multiple Columns
----------------

Select elements from columns **A** and **B** as a list of tuples::

    >>> select(('A', 'B')).fetch()  # Returns a list of tuples.
    [('x', 'foo'),
     ('x', 'foo'),
     ('y', 'foo'),
     ('y', 'bar'),
     ('z', 'bar'),
     ('z', 'bar')]

Select elements from columns **A** and **B** as a set of tuples::

    >>> select({('A', 'B')}).fetch()  # Returns a set of tuples.
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

When only one container type is given, it is used as an outer
container if it holds a single item and as an inner container
if it holds multiple items (outer container selections can not
contain multiple items). If you want to select a single-item
inner container, you must specify both outer and inner containers
(e.g., ``select([{'A'}])``).

As before, when an outer container type is not specified, it
defaults to a :py:class:`list`. So when the earlier example
used ``select(('A', 'B'))``, that was shorthand for
``select([('A', 'B')])``.


Groups of Columns
-----------------

Selecting groups of elements is accomplished using a
:py:class:`dict` or other mapping type. The key specifies
how the elements are grouped and the value specifies the
fields from which elements are selected.

For each unique value of column **A**, we select a list of
elements from column **B**::

    >>> select({'A': 'B'}).fetch()
    {'x': ['foo', 'foo'],
     'y': ['foo', 'bar'],
     'z': ['bar', 'bar']}

As before, the types used in the selection determine the
types returned in the result. For unique values of column
**A**, we can select a :py:class:`set` of elements from
column **B** with the following::

     >>> select({'A': {'B'}}).fetch()
     {'x': {'foo'},
      'y': {'foo', 'bar'},
      'z': {'bar'}}

To group by multiple columns, we use a :py:class:`tuple` of
key fields. For each unique tuple of **A** and **B**, we select
a list of elements from column **C**::

    >>> select({('A', 'B'): 'C'}).fetch()
    {('x', 'foo'): ['20', '30'],
     ('y', 'foo'): ['10'],
     ('y', 'bar'): ['20'],
     ('z', 'bar'): ['10', '10']}

Although selection types can be specified as needed, remember
that dictionary keys must be `immutable
<http://docs.python.org/3/glossary.html#term-immutable>`_
(:py:class:`str`, :py:class:`tuple`, :py:class:`frozenset`, etc.).


Narrowing a Selection
=====================

Selections can be narrowed to rows that satisfy given keyword
arguments.

Narrow a selection to rows where column **B** equals "foo"::

    >>> select(('A', 'B'), B='foo').fetch()
    [('x', 'foo'), ('x', 'foo'), ('y', 'foo')]

The keyword column does not have to be in the selected result::

    >>> select('A', B='foo').fetch()
    ['x', 'x', 'y']

Narrow a selection to rows where column **A** equals "x" *or* "y"::

    >>> select(('A', 'B'), A=['x', 'y']).fetch()
    [('x', 'foo'),
     ('x', 'foo'),
     ('y', 'foo'),
     ('y', 'bar')]

Narrow a selection to rows where column **A** equals "y" *and*
column **B** equals "bar"::

    >>> select([('A', 'B', 'C')], A='y', B='bar').fetch()
    [('y', 'bar', '20')]

Only one row matches the above keyword conditions.


Additional Operations
=====================

:class:`Query` objects also support methods for operating
on selected values.

:meth:`Sum <Query.sum>` the elements from column **C**::

    >>> select('C').sum().fetch()
    100

Group by column **A** the sums of elements from column **C**::

    >>> select({'A': 'C'}).sum().fetch()
    {'x': 50, 'y': 30, 'z': 20}

Group by columns **A** and **B** the sums of elements from column
**C**::

    >>> select({('A', 'B'): 'C'}).sum().fetch()
    {('x', 'foo'): 50,
     ('y', 'foo'): 10,
     ('y', 'bar'): 20,
     ('z', 'bar'): 20}

Select :meth:`distinct <Query.distinct>` elements::

    >>> select('A').distinct().fetch()
    ['x', 'y', 'z']

:meth:`Map <Query.map>` elements with a function::

    >>> def uppercase(value):
    ...     return str(value).upper()
    ...
    >>> select('A').map(uppercase).fetch()
    ['X', 'X', 'Y', 'Y', 'Z', 'Z']

:meth:`Filter <Query.filter>` elements with a function::

    >>> def not_z(value):
    ...     return value != 'z'
    ...
    >>> select('A').filter(not_z).fetch()
    ['x', 'x', 'y', 'y']

Since each method returns a new Query, it's possible to
chain together multiple method calls to transform the data
as needed::

    >>> def not_z(value):
    ...     return value != 'z'
    ...
    >>> def uppercase(value):
    ...     return str(value).upper()
    ...
    >>> select('A').filter(not_z).map(uppercase).fetch()
    ['X', 'X', 'Y', 'Y']
