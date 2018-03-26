
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

    .. automethod:: from_query

    .. automethod:: from_pandas

    .. automethod:: from_excel

    .. automethod:: from_dbf


*************************
Selecting & Querying Data
*************************

.. autoclass:: Selector

    .. automethod:: load_data

    .. autoattribute:: fieldnames

    .. automethod:: __call__

    .. automethod:: create_index


.. class:: Query(columns, **where)
           Query(selector, columns, **where)

    A class to query data from a source object. Queries can be
    created, modified, and passed around without actually computing
    the result---computation doesn't occur until the query object
    itself or its :meth:`fetch` method is called.

    The *columns* argument must be a container of one field name (a
    string) or of an inner-container of multiple filed names. The
    optional *where* keywords can narrow a selection to rows where
    fields match specified values.

    Although Query objects are usually created by
    :meth:`calling <datatest.Selector.__call__>` an existing
    Selector object like a function, it's possible to create
    them independent of any single data source::

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

    .. automethod:: fetch

    .. automethod:: __call__


.. autoclass:: Result

    .. attribute:: evaluation_type

        The type of instance returned by the
        :meth:`fetch <Result.fetch>` method.

    .. automethod:: fetch

    .. attribute:: __wrapped__

        The underlying iterator---useful when introspecting
        or rewrapping.
