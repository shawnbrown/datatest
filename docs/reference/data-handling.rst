
.. currentmodule:: datatest

.. meta::
    :description: Datatest Data Handling API Reference
    :keywords: datatest, data handling, API


###########################
Data Handling API Reference
###########################


*****************
working_directory
*****************

.. autoclass:: working_directory

    .. tip::

        Take care when using pytest's fixture finalization in combination
        with "session" or "module" level fixtures. In these cases, you
        should use :func:`working_directory` as a context manager (inside
        the function) and avoid using it as a decorator (outside the
        function):

        .. code-block:: python
            :emphasize-lines: 3

            @pytest.fixture(scope='session')
            def connection():
                with working_directory(__file__):
                    conn = ...  # Establish database connection.
                yield conn
                conn.close()

        The example above restores the original working directory as
        soon as the ``with`` statement finishes. But if the decorator
        form was used, the original directory wouldn't be restored
        until *after* the fixture is finalized---not usually what
        you want.


******************
RepeatingContainer
******************

.. autoclass:: RepeatingContainer


Validating RepeatingContainer Results
=====================================

When comparing the *data under test* against a set of similarly-shaped
*reference data*, it's common to perform the same operations on both
data sources. When queries and selections become more complex, this
duplication can grow cumbersome. But duplication can be mitigated by
using a :class:`RepeatingContainer` object.

A RepeatingContainer is compatible with many types of
objects---:class:`pandas.DataFrame`, :class:`squint.Select`, etc.

In the following example, a RepeatingContainer is created with two
objects. Then, an operation is forwarded to each object in the group.
Finally, the results are unpacked and validated:

.. tabs::

    .. group-tab:: With Pandas

        Below, the indexing and method calls
        ``...[['A', 'C']].groupby('A').sum()`` are forwarded to each
        :class:`pandas.DataFrame` and the results are returned inside
        a new RepeatingContainer:

        .. code-block:: python
            :emphasize-lines: 9

            import datatest as dt
            import pandas as pd

            compare = RepeatingContainer([
                pd.read_csv('data_under_test.csv'),
                pd.read_csv('reference_data.csv'),
            ])

            result = compare[['A', 'C']].groupby('A').sum()

            data, requirement = result
            dt.validate(data, requirement)

    .. group-tab:: With Squint

        Below, the method calls ``...({'A': 'C'}).sum()`` are forwarded to
        each :class:`squint.Select` and the results are returned inside a
        new RepeatingContainer:

        .. code-block:: python
            :emphasize-lines: 9

            from datatest import validate
            from squint import Select

            compare = RepeatingContainer([
                Select('data_under_test.csv'),
                Select('reference_data.csv'),
            ])

            result = compare({'A': 'C'}).sum()

            data, requirement = result
            validate(data, requirement)


The example above can be expressed even more concisely using
Python's asterisk unpacking (``*``) to unpack the values directly
inside the :func:`validate` call itself:

.. tabs::

    .. group-tab:: With Pandas

        .. code-block:: python
            :emphasize-lines: 9

            import datatest as dt
            import pandas as pd

            compare = RepeatingContainer([
                pd.read_csv('data_under_test.csv'),
                pd.read_csv('reference_data.csv'),
            ])

            dt.validate(*compare[['A', 'C']].groupby('A').sum())

    .. group-tab:: With Squint

        .. code-block:: python
            :emphasize-lines: 9

            from datatest import validate
            from squint import Select

            compare = RepeatingContainer([
                Select('data_under_test.csv'),
                Select('reference_data.csv'),
            ])

            validate(*compare({'A': 'C'}).sum())


*******************
Deprecated Features
*******************

.. autoclass:: get_reader(obj, *args, **kwds)

    .. automethod:: from_csv

    .. automethod:: from_dicts

    .. automethod:: from_namedtuples

    .. automethod:: from_datatest

    .. automethod:: from_pandas

    .. automethod:: from_excel

    .. automethod:: from_dbf


.. autoclass:: Select

    .. automethod:: load_data

    .. autoattribute:: fieldnames

    .. automethod:: __call__

    .. automethod:: create_index


.. class:: Query(columns, **where)
           Query(select, columns, **where)

    A class to query data from a source object. Queries can be
    created, modified, and passed around without actually computing
    the result---computation doesn't occur until the query object
    itself or its :meth:`fetch` method is called.

    The given *columns* and *where* arguments can be any values
    supported by :meth:`Select.__call__`.

    Although Query objects are usually created by :meth:`calling
    <datatest.Select.__call__>` an existing Select, it's
    possible to create them independent of any single data source::

        query = Query('A')

    .. deprecated:: 0.9.7
        Use the :mod:`squint` project instead.

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

    .. automethod:: unwrap

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
