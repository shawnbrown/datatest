
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
