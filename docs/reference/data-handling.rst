
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

.. autoclass:: DataQuery

    .. classmethod:: from_object(source, select, **where)
                     from_object(object)

        Creates a query and associates it with the given object.

        If the object is a DataSource, you must provide a *select*
        argument and may also narrow the selection with keyword
        arguments::

            source = DataSource(...)
            query = DataQuery.from_object(source, 'A')

        A non-DataSource container may also be used::

            list_object = [1, 2, 3, 4]
            query = DataQuery.from_object(list_object)

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

    .. automethod:: fetch

    .. automethod:: __call__


**********
DataResult
**********

.. autoclass:: DataResult

    .. attribute:: evaluation_type

        The type of instance returned by the
        :meth:`fetch <DataResult.fetch>` method.

    .. automethod:: fetch

    .. attribute:: __wrapped__

        The underlying iterator---useful when introspecting
        or rewrapping.
