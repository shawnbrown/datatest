
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


Validating ProxyGroup Results
=============================

When comparing the data-under-test against a set of similarly-shaped
reference data, it's common to perform the same operations on both
data sources. When queries and selections become more complex, this
duplication can grow cumbersome. But the duplication can be mitigated
by using a :class:`ProxyGroup`.

A ProxyGroup can wrap many types of objects (:class:`Selector`,
pandas ``DataFrame``, etc.). In the following example, a ProxyGroup
is created with two objects. Then, an operation is forwarded to each
object in the group. Finally, the results are unpacked and validated:

.. tabs::

    .. group-tab:: Selector Example

        Below, the operation ``...({'A': 'C'}).sum()`` is forwarded to
        each :class:`Selector` and the results are returned inside a
        new ProxyGroup object:

        .. code-block:: python
            :emphasize-lines: 8

            ...

            compare = ProxyGroup([
                Selector('data_under_test.csv'),
                Selector('reference_data.csv'),
            ])

            result = compare({'A': 'C'}).sum()

            data, requirement = result
            validate(data, requirement)

    .. group-tab:: DataFrame Example

        Below, the operation ``...[['A', 'C']].groupby('A').sum()`` is
        forwarded to each ``DataFrame`` and the results are returned
        inside a new ProxyGroup object:

        .. code-block:: python
            :emphasize-lines: 8

            ...

            compare = ProxyGroup([
                pandas.read_csv('data_under_test.csv'),
                pandas.read_csv('reference_data.csv'),
            ])

            result = compare[['A', 'C']].groupby('A').sum()

            data, requirement = result
            validate(data, requirement)


The example above can be expressed even more concisely by unpacking
the result values directly in the :func:`validate` call itself:

.. tabs::

    .. group-tab:: Selector Example

        .. code-block:: python
            :emphasize-lines: 8

            ...

            compare = ProxyGroup([
                Selector('data_under_test.csv'),
                Selector('reference_data.csv'),
            ])

            validate(*compare({'A': 'C'}).sum())

    .. group-tab:: DataFrame Example

        .. code-block:: python
            :emphasize-lines: 8

            ...

            compare = ProxyGroup([
                pandas.read_csv('data_under_test.csv'),
                pandas.read_csv('reference_data.csv'),
            ])

            validate(*compare[['A', 'C']].groupby('A').sum())

