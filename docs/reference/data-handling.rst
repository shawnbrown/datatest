
.. module:: datatest

.. meta::
    :description: Datatest Data Handling API Reference
    :keywords: datatest, data handling, API


###########################
Data Handling API Reference
###########################


************
Loading Data
************

.. autoclass:: working_directory


.. autoclass:: get_reader(obj, *args, **kwds)

    .. automethod:: from_csv

    .. automethod:: from_dicts

    .. automethod:: from_namedtuples

    .. automethod:: from_datatest

    .. automethod:: from_pandas

    .. automethod:: from_excel

    .. automethod:: from_dbf


*************************
Selecting & Querying Data
*************************

.. autoclass:: Selector

    .. automethod:: load_data

        .. figure:: /_static/multisource.svg
           :figwidth: 75%
           :alt: Data can be loaded from multiple files.

           When multiple sources are loaded into a single Selector,
           data is aligned by fieldname and missing fields receive
           empty strings.

    .. autoattribute:: fieldnames

    .. automethod:: __call__

    .. automethod:: create_index


.. class:: Query(columns, **where)
           Query(selector, columns, **where)

    A class to query data from a source object. Queries can be
    created, modified, and passed around without actually computing
    the result---computation doesn't occur until the query object
    itself or its :meth:`fetch` method is called.

    The given *columns* and *where* arguments can be any values
    supported by :meth:`Selector.__call__`.

    Although Query objects are usually created by :meth:`calling
    <datatest.Selector.__call__>` an existing Selector, it's
    possible to create them independent of any single data source::

        query = Query('A')

    .. automethod:: from_object

    .. automethod:: sum

    .. automethod:: count

    .. automethod:: avg

    .. automethod:: min

    .. automethod:: max

    .. automethod:: distinct

    .. automethod:: apply

    .. automethod:: map

    .. automethod:: filter

    .. automethod:: reduce

    .. automethod:: flatten

    .. automethod:: execute

    .. automethod:: fetch

    .. automethod:: to_csv


.. autoclass:: Result

    .. attribute:: evaluation_type

        The type of instance returned by the
        :meth:`fetch <Result.fetch>` method.

    .. automethod:: fetch

    .. attribute:: __wrapped__

        The underlying iterator---useful when introspecting
        or rewrapping.


**********
ProxyGroup
**********

.. autoclass:: ProxyGroup


.. tip::

    When comparing the data under test against a set of
    similarly-shaped reference data, it's common to perform the same
    operations on both data sources. Duplicate queries and selections
    can grow cumbersome when working with :class:`Selector`,
    ``pandas.DataFrame`` or other object types. This duplication can
    be mitigated by using a :class:`ProxyGroup`.

    In the following example, a ProxyGroup with two DataFrames is
    created. Then, the operation ``...[['A', 'C']].groupby('A').sum()``
    is forwarded to each DataFrame in the group. Finally, the results
    are unpacked and validated::

        ...

        compare = ProxyGroup([
            pandas.read_csv('data_under_test.csv'),
            pandas.read_csv('reference_data.csv'),
        ])

        result = compare[['A', 'C']].groupby('A').sum()

        data, requirement = result
        validate(data, requirement)

    The example above can be expressed even more concisely by unpacking
    the results directly in the :func:`validate` call itself:

    .. code-block:: python
        :emphasize-lines: 8

        ...

        compare = ProxyGroup([
            pandas.read_csv('data_under_test.csv'),
            pandas.read_csv('reference_data.csv'),
        ])

        validate(*compare[['A', 'C']].groupby('A').sum())


*****************
Composite Objects
*****************

.. autoclass:: CompositeSelector

.. autoclass:: CompositeQuery


Working With Composite Objects
==============================

Composite objects are useful when you need to compare data from
multiple sources that are similarly shaped (i.e., they have many
of the same column names). Rather than select the same columns
and build the same queries for each data source, you can wrap
them in a composite object and build the query once::

    select1 = Selector('detailed_data.csv')
    select2 = Selector('summary_reference.csv')
    compare = CompositeSelector(select1, select2)

    comparison = compare({'county': 'population'}).sum()

