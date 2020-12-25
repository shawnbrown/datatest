
.. currentmodule:: datatest

.. meta::
    :description: How to assert data types.
    :keywords: datatest, reference data


##########################
How to Validate Data Types
##########################

To check that data is of a particular type, call :func:`validate`
with a type as the *requirement* argument (see :ref:`predicate-docs`).


Simple Type Checking
====================

In the following example, we use the :py:class:`float` type as the
*requirement*. The elements in *data* are considered valid if they
are float instances:

.. code-block:: python
    :emphasize-lines: 4
    :linenos:

    from datatest import validate

    data = [0.0, 1.0, 2.0]
    validate(data, float)


In this example, we use the :py:class:`str` type as the
*requirement*. The elements in *data* are considered
valid if they are strings:

.. code-block:: python
    :emphasize-lines: 4
    :linenos:

    from datatest import validate

    data = ['a', 'b', 'c']
    validate(data, str)


Using a Tuple of Types
======================

You can also use a **predicate tuple** to test the types contained
in tuples. The elements in *data* are considered valid if the tuples
contain a number followed by a string:

.. code-block:: python
    :emphasize-lines: 5
    :linenos:

    from numbers import Number
    from datatest import validate

    data = [(0.0, 'a'), (1.0, 'b'), (2, 'c'), (3, 'd')]
    validate(data, (Number, str))

In the example above, the :py:class:`Number <numbers.Number>` base
class is used to check for numbers of any type (:py:class:`int`,
:py:class:`float`, :py:class:`complex`, :py:class:`Decimal
<decimal.Decimal>`, etc.).


Checking Pandas Types
=====================

.. admonition:: Type Inference and Conversion
    :class: note

    .. raw:: html

       <details>
       <summary><a>A Quick Refresher</a></summary>

    Import the :mod:`pandas` package:

    .. code-block:: python

        >>> import pandas as pd

    **INFERENCE**

    When a column's values are all integers (``1``, ``2``, and ``3``),
    then Pandas infers an integer dtype:

    .. code-block:: python
        :emphasize-lines: 5

        >>> pd.Series([1, 2, 3])
        0    1
        1    2
        2    3
        dtype: int64

    When a column's values are a mix of integers (``1`` and ``3``)  and
    floating point numbers (``2.0``), then Pandas will infer a floating
    point dtype---notice that the original integers have been coerced
    into float values:

    .. code-block:: python
        :emphasize-lines: 5

        >>> pd.Series([1, 2.0, 3])
        0    1.0
        1    2.0
        2    3.0
        dtype: float64

    When certain non-numeric types are present, ``'three'``, then pandas
    will use a generic "object" dtype:

    .. code-block:: python
        :emphasize-lines: 5

        >>> pd.Series([1, 2.0, 'three'])
        0        1
        1        2
        2    three
        dtype: object

    **CONVERSION**

    When a dtype is specified, ``dtype=float``, Pandas will attempt to
    convert values into the given type. Here, the integers are explicitly
    converted into float values:

    .. code-block:: python
        :emphasize-lines: 5

        >>> pd.Series([1, 2, 3], dtype=float)
        0    1.0
        1    2.0
        2    3.0
        dtype: float64

    In this example, integers and floating point numbers are converted
    into string values, ``dtype=str``:

    .. code-block:: python
        :emphasize-lines: 5

        >>> pd.Series([1, 2.0, 3], dtype=str)
        0      1
        1    2.0
        2      3
        dtype: object

    When a value cannot be converted into a specified type, an error
    is raised:

    .. code-block:: python
        :emphasize-lines: 16

        >>> pd.Series([1, 2.0, 'three'], dtype=int)
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
          File "~/myproject/venv/lib64/python3.8/site-packages/pandas/core/series.py", line
          327, in __init__
            data = sanitize_array(data, index, dtype, copy, raise_cast_failure=True)
          File "~/myproject/venv/lib64/python3.8/site-packages/pandas/core/construction.py",
           line 447, in sanitize_array
            subarr = _try_cast(data, dtype, copy, raise_cast_failure)
          File "~/myproject/venv/lib64/python3.8/site-packages/pandas/core/construction.py",
           line 555, in _try_cast
            maybe_cast_to_integer_array(arr, dtype)
          File "~/myproject/venv/lib64/python3.8/site-packages/pandas/core/dtypes/cast.py",
          line 1674, in maybe_cast_to_integer_array
            casted = np.array(arr, dtype=dtype, copy=copy)
        ValueError: invalid literal for int() with base 10: 'three'


    **SEE ALSO**

    For more details, see the Pandas documentation regarding
    :ref:`pandas:basics.object_conversion`.

    .. raw:: html

       </details>


Check the types for each row of elements within a :class:`DataFrame`:

.. tabs::

    .. group-tab:: Passing

        .. code-block:: python
            :emphasize-lines: 9
            :linenos:

            import pandas as pd
            import datatest as dt

            dt.register_accessors()

            df = pd.DataFrame(data={'A': ['foo', 'bar', 'baz', 'qux'],
                                    'B': [10, 20, 30, 40]})

            df.validate((str, int))

    .. group-tab:: Failing

        .. code-block:: python
            :emphasize-lines: 9
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
              File "example.py", line 9, in <module>
                df.validate((str, int))
            datatest.ValidationError: does not satisfy `(str, int)` (2 differences): [
                Invalid(('baz', 'x')),
                Invalid(('qux', 'y')),
            ]


Check the type of each element, one column at a time:

.. tabs::

    .. group-tab:: Passing

        .. code-block:: python
            :emphasize-lines: 9-10
            :linenos:

            import pandas as pd
            import datatest as dt

            dt.register_accessors()

            df = pd.DataFrame(data={'A': ['foo', 'bar', 'baz', 'qux'],
                                    'B': [10, 20, 30, 40]})

            df['A'].validate(str)
            df['B'].validate(int)

    .. group-tab:: Failing

        .. code-block:: python
            :emphasize-lines: 9-10
            :linenos:

            import pandas as pd
            import datatest as dt

            dt.register_accessors()

            df = pd.DataFrame(data={'A': ['foo', 'bar', 'baz', 'qux'],
                                    'B': [10, 20, 'x', 'y']})

            df['A'].validate(str)
            df['B'].validate(int)

        .. code-block:: none
            :emphasize-lines: 5-6

            Traceback (most recent call last):
              File "example.py", line 10, in <module>
                df['B'].validate(int)
            datatest.ValidationError: does not satisfy `int` (2 differences): [
                Invalid('x'),
                Invalid('y'),
            ]


Check the ``dtypes`` of the columns themselves (not the elements they
contain):

.. tabs::

    .. group-tab:: Passing

        .. code-block:: python
            :emphasize-lines: 10-14
            :linenos:

            import pandas as pd
            import numpy as np
            import datatest as dt

            dt.register_accessors()

            df = pd.DataFrame(data={'A': ['foo', 'bar', 'baz', 'qux'],
                                    'B': [10, 20, 30, 40]})

            required = {
                'A': np.dtype(object),
                'B': np.dtype(int),
            }
            df.dtypes.validate(required)

    .. group-tab:: Failing

        .. code-block:: python
            :emphasize-lines: 10-14
            :linenos:

            import pandas as pd
            import numpy as np
            import datatest as dt

            dt.register_accessors()

            df = pd.DataFrame(data={'A': ['foo', 'bar', 'baz', 'qux'],
                                    'B': [10, 20, 'x', 'y']})

            required = {
                'A': np.dtype(object),
                'B': np.dtype(int),
            }
            df.dtypes.validate(required)

        .. code-block:: none
            :emphasize-lines: 5

            Traceback (most recent call last):
              File "example.py", line 14, in <module>
                df.dtypes.validate(required)
            datatest.ValidationError: does not satisfy `dtype('int64')` (1 difference): {
                'B': Invalid(dtype('O'), expected=dtype('int64')),
            }


NumPy Types
===========

With :py:class:`Predicate` matching, you can use Python's built-in
:py:class:`str`, :py:class:`int`, :py:class:`float`, and :py:class:`complex`
to validate types in NumPy arrays:

.. code-block:: python
    :emphasize-lines: 9
    :linenos:

    import numpy as np
    import datatest as dt

    a = np.array([(1, 12.25),
                  (2, 33.75),
                  (3, 101.5)],
                 dtype='int32, float32')

    dt.validate(a, (int, float))


You can also use NumPy's own generic types (e.g., ``np.character``,
``np.integer``, ``np.floating``, etc.):

.. code-block:: python
    :emphasize-lines: 9
    :linenos:

    import numpy as np
    import datatest as dt

    a = np.array([(1, 12.25),
                  (2, 33.75),
                  (3, 101.5)],
                 dtype='int32, float32')

    dt.validate(a, (np.integer, np.floating))


To validate types with greater precision, you can always use NumPy's
specific dtypes (``np.uint32``, ``np.float64``, etc.). For more details
on NumPy types see:

* https://numpy.org/doc/stable/reference/arrays.scalars.html
* https://numpy.org/doc/stable/reference/arrays.dtypes.html
