
.. module:: datatest

.. meta::
    :description: datatest API
    :keywords: datatest, Selector, Query, Result, working_directory


#############
Data Handling
#############


*****************
working_directory
*****************

.. autoclass:: working_directory


********
Selector
********

.. autoclass:: Selector

    .. automethod:: from_csv

    .. automethod:: from_excel

    .. autoattribute:: fieldnames

    .. automethod:: __call__


*****
Query
*****

.. autoclass:: Query

    .. classmethod:: from_object(source, select, **where)
                     from_object(object)

        Creates a query and associates it with the given object.

        If the object is a Selector, you must provide a *select*
        argument and may also narrow the selection with keyword
        arguments::

            source = Selector(...)
            query = Query.from_object(source, 'A')

        A non-Selector container may also be used::

            list_object = [1, 2, 3, 4]
            query = Query.from_object(list_object)

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


******
Result
******

.. autoclass:: Result

    .. attribute:: evaluation_type

        The type of instance returned by the
        :meth:`fetch <Result.fetch>` method.

    .. automethod:: fetch

    .. attribute:: __wrapped__

        The underlying iterator---useful when introspecting
        or rewrapping.
