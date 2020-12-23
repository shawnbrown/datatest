
.. currentmodule:: datatest

.. meta::
    :description: An introduction to using Pandas together with Datatest.
    :keywords: datatest, pandas, validate, testing, DataFrame, Series, Index


#########################
Validating Pandas Objects
#########################

The :mod:`pandas` data analysis package is commonly used for data
work. This page explains how datatest handles the validation of
|DataFrame|, |Series|, |Index|, and |MultiIndex| objects.

.. |DataFrame| replace:: :class:`DataFrame <pandas.DataFrame>`
.. |Series| replace:: :class:`Series <pandas.Series>`
.. |Index| replace:: :class:`Index <pandas.Index>`
.. |MultiIndex| replace:: :class:`MultiIndex <pandas.MultiIndex>`
.. |extension accessors| replace:: :ref:`extension accessors <pandas:ecosystem.accessors>`


.. admonition:: Accessor Syntax
    :class: note

    Examples on this page use the ``validate`` accessor:

    .. code-block:: python

        # Accessor syntax:

        df['A'].validate({'x', 'y', 'z'})

    We could also use the equivalent non-accessor syntax:

    .. code-block:: python

        # Basic syntax:

        dt.validate(df['A'], {'x', 'y', 'z'})


DataFrame
=========

For validation, :class:`DataFrame <pandas.DataFrame>` objects using
the default index type are treated as sequences. DataFrames using an
index of any other type are treated as mappings:

.. tabs::

    .. group-tab:: Default Index

        .. code-block:: python
            :linenos:

            import pandas as pd
            import datatest as dt

            dt.register_accessors()

            df = pd.DataFrame(data={'A': ['foo', 'bar', 'baz', 'qux'],
                                    'B': [10, 20, 'x', 'y']})


            requirement = [
                ('foo', 10),
                ('bar', 20),
                ('baz', 'x'),
                ('qux', 'y'),
            ]

            df.validate(requirement)

        Since no index was specified, ``df`` uses the default
        :class:`RangeIndex <pandas.RangeIndex>` type---which tells
        :func:`validate()` to treat the DataFrame as a sequence.

    .. group-tab:: Specified Index

        .. code-block:: python
            :linenos:

            import pandas as pd
            import datatest as dt

            dt.register_accessors()

            df = pd.DataFrame(data={'A': ['foo', 'bar', 'baz', 'qux'],
                                    'B': [10, 20, 'x', 'y']},
                              index=['I', 'II', 'III', 'IV'])

            requirement = {
                'I': ('foo', 10),
                'II': ('bar', 20),
                'III': ('baz', 'x'),
                'IV': ('qux', 'y'),
            }

            df.validate(requirement)

        In this example, we've specified an index and therefore ``df``
        is handled as a mapping.


The distinction between implicit and explicit indexing is also
apparent in error reporting. Compare the examples on each of the
tabs below:

.. tabs::

    .. group-tab:: Default Index

        .. code-block:: python
            :linenos:

            import pandas as pd
            import datatest as dt

            dt.register_accessors()

            df = pd.DataFrame(data={'A': ['foo', 'bar', 'baz', 'qux'],
                                    'B': [10, 20, 'x', 'y']})


            df.validate((str, int))


        .. code-block:: none
            :emphasize-lines: 5-6

            Traceback (most recent call last):
              File "example.py", line 10, in <module>
                df.validate((str, int))
            datatest.ValidationError: does not satisfy `(str, int)` (2 differences): [
                Invalid(('baz', 'x')),
                Invalid(('qux', 'y')),
            ]

        Since the DataFrame was treated as a sequence, the error includes
        a sequence of differences.

    .. group-tab:: Specified Index

        .. code-block:: python
            :linenos:

            import pandas as pd
            import datatest as dt

            dt.register_accessors()

            df = pd.DataFrame(data={'A': ['foo', 'bar', 'baz', 'qux'],
                                    'B': [10, 20, 'x', 'y']},
                              index=['I', 'II', 'III', 'IV'])

            df.validate((str, int))


        .. code-block:: none
            :emphasize-lines: 5-6

            Traceback (most recent call last):
              File "example.py", line 10, in <module>
                df.validate((str, int))
            datatest.ValidationError: does not satisfy `(str, int)` (2 differences): {
                'III': Invalid(('baz', 'x')),
                'IV': Invalid(('qux', 'y')),
            }

        In this example, the DataFrame was treated as a mapping, so the
        error includes a mapping of differences.


Series
======

:class:`Series <pandas.Series>` objects are handled the same way as
DataFrames. Series with a default index are treated as sequences and
Series with explicitly defined indexes are treated as mappings:

.. tabs::

    .. group-tab:: Default Index

        .. code-block:: python
            :linenos:

            import pandas as pd
            import datatest as dt

            dt.register_accessors()

            s = pd.Series(data=[10, 20, 'x', 'y'])


            requirement = [10, 20, 'x', 'y']

            s.validate(requirement)

    .. group-tab:: Specified Index

        .. code-block:: python
            :linenos:

            import pandas as pd
            import datatest as dt

            dt.register_accessors()

            s = pd.Series(data=[10, 20, 'x', 'y'],
                          index=['I', 'II', 'III', 'IV'])

            requirement = {'I': 10, 'II': 20, 'III': 'x', 'IV': 'y'}

            s.validate(requirement)


Like before, the sequence and mapping handling is also apparent
in the error reporting:

.. tabs::

    .. group-tab:: Default Index

        .. code-block:: python
            :linenos:

            import pandas as pd
            import datatest as dt

            dt.register_accessors()

            s = pd.Series(data=[10, 20, 'x', 'y'])


            s.validate(int)


        .. code-block:: none
            :emphasize-lines: 5-6

            Traceback (most recent call last):
              File "example.py", line 9, in <module>
                s.validate(int)
            datatest.ValidationError: does not satisfy `int` (2 differences): [
                Invalid('x'),
                Invalid('y'),
            ]

    .. group-tab:: Specified Index

        .. code-block:: python
            :linenos:

            import pandas as pd
            import datatest as dt

            dt.register_accessors()

            s = pd.Series(data=[10, 20, 'x', 'y'],
                          index=['I', 'II', 'III', 'IV'])

            s.validate(int)


        .. code-block:: none
            :emphasize-lines: 5-6

            Traceback (most recent call last):
              File "example.py", line 9, in <module>
                s.validate(int)
            datatest.ValidationError: does not satisfy `int` (2 differences): {
                'III': Invalid('x'),
                'IV': Invalid('y'),
            }


Index and MultiIndex
====================

:class:`Index <pandas.Index>` and :class:`MultiIndex <pandas.MultiIndex>`
objects are all treated as sequences:

.. code-block:: python
    :linenos:

    import pandas as pd
    import datatest as dt

    dt.register_accessors()

    index = pd.Index(['I', 'II', 'III', 'IV'])
    requirement = ['I', 'II', 'III', 'IV']
    index.validate(requirement)

    multi = pd.MultiIndex.from_tuples([
        ('I', 'a'),
        ('II', 'b'),
        ('III', 'c'),
        ('IV', 'd'),
    ])
    requirement = [('I', 'a'), ('II', 'b'), ('III', 'c'), ('IV', 'd')]
    multi.validate(requirement)
