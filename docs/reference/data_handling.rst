
.. module:: datatest

.. meta::
    :description: datatest API
    :keywords: datatest, DataSource, DataQuery, DataResult, working_directory


#############
Data Handling
#############


*****************
working_directory
*****************

.. autoclass:: working_directory


**********
DataSource
**********

.. autoclass:: DataSource

    .. automethod:: from_csv

    .. automethod:: from_excel

    .. autoattribute:: fieldnames

    .. automethod:: __call__


*********
DataQuery
*********

.. class:: DataQuery(select, **where)
           DataQuery(defaultsource, select, **where)

    A class to query data from a :class:`DataSource` object.
    Queries can be created, modified and passed around without
    actually computing the result---computation doesn't occur
    until the :meth:`execute` method is called.

    The *select* argument must be a container of one field name (a
    string) or of an inner-container of multiple filed names. The
    optional *where* keywords can narrow a selection to rows where
    fields match specified values. A *defaultsource* can be provided
    to associate the query with a specific DataSource object.

    Queries are usually created from an existing source (the
    originating source is automatically associated with the new
    query)::

        source = DataSource(...)
        query = source(['A'])  # <- DataQuery created from source.

    Queries can be created directly as well::

        source = DataSource(...)
        query = DataQuery(source, ['A'])  # <- Direct initialization.

    Queries can also be created independent of any single data source::

        query = DataQuery(['A'])

    .. attribute:: defaultsource

        A property for setting a predetermined :class:`DataSource`
        to use when :meth:`execute` is called without a *source*
        argument.

        When a query is created from a DataSource call, this property
        is assigned automatically. When a query is created directly,
        the value can be passed explicitly or it can be omitted.

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
