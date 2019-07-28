
.. module:: datatest

.. meta::
    :description: datatest API for pandas integration
    :keywords: datatest, pandas, validate, validation


##################
Pandas Integration
##################

Datatest can validate :mod:`pandas` objects the same way it validates
built-in types:

* :class:`Index <pandas.Index>` objects are validated as sequences.
* :class:`Series <pandas.Series>` objects are validated as sequences.
* :class:`DataFrame <pandas.DataFrame>` objects are validated as
  mappings where each index element is a key and associated data
  elements are values. If the DataFrame contains multiple columns,
  data elements are wrapped in a tuple.


********
Examples
********

The following examples demonstrate how datatest handles pandas
objects. The examples will use the following DataFrame:

.. code-block:: python

    import pandas as pd
    import datatest as dt


    df = pd.DataFrame(
        data=[
            ['x', 'foo', 20],
            ['x', 'foo', 30],
            ['y', 'foo', 10],
            ['y', 'bar', 20],
            ['z', 'bar', 10],
            ['z', 'bar', 10],
        ],
        columns=['A', 'B', 'C'],
    )

    ...


Index
=====

In this example, we check that the values in ``df.columns`` (an Index)
are members of the set ``{'A', 'B', 'C'}``:

.. code-block:: python

    dt.validate(df.columns, {'A', 'B', 'C'})

This is roughly equivalent to:

.. code-block:: python

    dt.validate(['A', 'B', 'C'], {'A', 'B', 'C'})


Series
======

In this example, we check that the values in ``df['A']`` (a Series)
are members of the set ``{'x', 'y', 'z'}``:

.. code-block:: python

    dt.validate(df['A'], {'x', 'y', 'z'})

This is roughly equivalent to:

.. code-block:: python

    dt.validate(['x', 'x', 'y', 'y', 'z', 'z'], {'x', 'y', 'z'})


DataFrame
=========

In the following example, we check that the records of
``df[['A', 'C']]`` (a DataFrame) contain an integer and
a string:

.. code-block:: python

    dt.validate(df[['A', 'C']], (str, int))

This is roughly equivalent to:

.. code-block:: python

    dt.validate(
        {
            0: ('x', 20),
            1: ('x', 30),
            2: ('y', 10),
            3: ('y', 20),
            4: ('z', 10),
            5: ('z', 10),
        },
        (str, int)
    )


.. hint::

    As noted earlier, DataFrames are treated as mappings where
    indexes are keys and data elements are values. The following
    examples show some simple DataFrame objects and their equivalent
    mapping representations.

    Consider the following:

    .. code-block:: python

        >>> import pandas as pd
        >>> data = [['x', 1], ['y', 2], ['z', 3]]
        >>> my_df = pd.DataFrame(data, columns=['A', 'B'])
        >>> my_df
           A  B
        0  x  1
        1  y  2
        2  z  3

    Validation treats the above DataFrame the same as the following
    dictionary of tuple records:

    .. code-block:: python

        >>> my_dict = {
        ...     0: ('x', 1),
        ...     1: ('y', 2),
        ...     2: ('z', 3),
        ... }

    For single column DataFrames, values are not wrapped in tuples:

    .. code-block:: python

        >>> import pandas as pd
        >>> my_df = pd.DataFrame(['x', 'y', 'x'], columns=['A'])
        >>> my_df
           A
        0  x
        1  y
        2  z

    Validation treats the above DataFrame the same as the following
    dictionary of values:

    .. code-block:: python

        >>> my_dict = {
        ...     0: 'x',
        ...     1: 'y',
        ...     2: 'z',
        ... }


.. _pandas-accessor-docs:

***************************************
Accessors (Alternate Validation Syntax)
***************************************

Accessors provide an alternate syntax for validation. While
they do not provide additional functionality, some users may
prefer the more integrated style.

.. autofunction:: register_accessors


Accessor Equivalencies
======================

The following examples demonstrate the "validate" accessor for
Index, Series, and DataFrame objects. The equivalent non-accessor
syntax is included for comparison:

.. tabs::

    .. group-tab:: Accessor Syntax

        .. code-block:: python

            df.columns.validate({'A', 'B', 'C'})  # Index accessor

            df['A'].validate({'x', 'y', 'z'})     # Series accessor

            df['C'].validate.interval(10, 30)     # Series accessor

            df[['A', 'C']].validate((str, int))   # DataFrame accessor

    .. group-tab:: Non-accessor Syntax

        .. code-block:: python

            dt.validate(df.columns, {'A', 'B', 'C'})

            dt.validate(df['A'], {'x', 'y', 'z'})

            dt.validate.interval(df['C'], 10, 30)

            dt.validate(df[['A', 'C']], (str, int))


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

