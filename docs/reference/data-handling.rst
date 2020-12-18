
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
        should use :func:`working_directory` as a context manager---not
        as a decorator.

        In the first example below, the original working directory is
        restored immediately when the ``with`` statement ends. But
        in the second example, the original directory isn't restored
        until after the entire session is finished (not usually what
        you want):

        .. code-block:: python
            :emphasize-lines: 5

            # Correct:

            @pytest.fixture(scope='session')
            def connection():
                with working_directory(__file__):
                    conn = ...  # Establish database connection.
                yield conn
                conn.close()

        .. code-block:: python
            :emphasize-lines: 4

            # Wrong:

            @pytest.fixture(scope='session')
            @working_directory(__file__)
            def connection():
                conn = ...  # Establish database connection.
                yield conn
                conn.close()

        When a fixture does not require finalization or if the fixture
        is short-lived (e.g., a function-level fixture) then either
        form is acceptible.


.. _pandas-accessor-docs:

****************
Pandas Accessors
****************

Datatest provides an optional :ref:`extension accessor
<pandas:ecosystem.accessors>` for integrating validation
directly with pandas objects.

.. autofunction:: register_accessors


Accessor Equivalencies
======================

Below, you can compare the accessor syntax against the equivalent
non-accessor syntax:

.. tabs::

    .. group-tab:: Accessor Syntax

        .. code-block:: python

            import datatest as dt
            dt.register_accessors()
            ...

            df.columns.validate({'A', 'B', 'C'})      # Index

            df['A'].validate({'x', 'y', 'z'})         # Series

            df['C'].validate.interval(10, 30)         # Series

            df[['A', 'C']].validate((str, int))       # DataFrame

    .. group-tab:: Non-accessor Syntax

        .. code-block:: python

            import datatest as dt

            ...

            dt.validate(df.columns, {'A', 'B', 'C'})  # Index

            dt.validate(df['A'], {'x', 'y', 'z'})     # Series

            dt.validate.interval(df['C'], 10, 30)     # Series

            dt.validate(df[['A', 'C']], (str, int))   # DataFrame


Here is the full list of accessor equivalencies:

.. table::
    :widths: auto

    ======================================= ==================================================================
    Accessor Expression                     Equivalent Non-accessor Expression
    ======================================= ==================================================================
    ``obj.validate(requirement)``           :class:`validate(obj, requirement) <validate>`
    ``obj.validate.predicate(requirement)`` :class:`validate.predicate(obj, requirement) <validate.predicate>`
    ``obj.validate.regex(requirement)``     :class:`validate.regex(obj, requirement) <validate.regex>`
    ``obj.validate.approx(requirement)``    :class:`validate.approx(obj, requirement) <validate.approx>`
    ``obj.validate.fuzzy(requirement)``     :class:`validate.fuzzy(obj, requirement) <validate.fuzzy>`
    ``obj.validate.interval(min, max)``     :class:`validate.interval(obj, min, max) <validate.interval>`
    ``obj.validate.set(requirement)``       :class:`validate.set(obj, requirement) <validate.set>`
    ``obj.validate.subset(requirement)``    :class:`validate.subset(obj, requirement) <validate.subset>`
    ``obj.validate.superset(requirement)``  :class:`validate.superset(obj, requirement) <validate.superset>`
    ``obj.validate.unique()``               :class:`validate.unique(obj) <validate.unique>`
    ``obj.validate.order(requirement)``     :class:`validate.order(obj, requirement) <validate.order>`
    ======================================= ==================================================================


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
