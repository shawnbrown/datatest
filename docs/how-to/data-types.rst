
.. currentmodule:: datatest

.. meta::
    :description: How to assert data types.
    :keywords: datatest, reference data


##########################
How to Validate Data Types
##########################

To check that data is of a particular type, you can pass a
type object (i.e., a class) as the *requirement* value
(see :ref:`predicate-docs`).

In the following example, we use the :py:class:`float` type
as the *requirement*. The elements in *data* are considered
valid if they are float instances:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 8

            from datatest import validate


            def test_float_types():

                data = [0.0, 1.0, 2.0]

                validate(data, float)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 10

            from datatest import DataTestCase


            class MyTest(DataTestCase):

                def test_float_types(self):

                    data = [0.0, 1.0, 2.0]

                    self.assertValid(data, float)


In this example, we use the :py:class:`str` type as the
*requirement*. The elements in *data* are considered
valid if they are strings:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 8

            from datatest import validate


            def test_str_types():

                data = ['a', 'b', 'c']

                validate(data, str)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 10

            from datatest import DataTestCase


            class MyTest(DataTestCase):

                def test_str_types(self):

                    data = ['a', 'b', 'c']

                    self.assertValid(data, str)


You can also use a **predicate tuple** to test the types contained
in tuples. The elements in *data* are considered valid if the tuples
contain a number followed by a string:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 9

            from numbers import Number
            from datatest import validate


            def test_multiple_types():

                data = [(0.0, 'a'), (1.0, 'b'), (2, 'c'), (3, 'd')]

                validate(data, (Number, str))

    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 11

            from numbers import Number
            from datatest import DataTestCase


            class MyTest(DataTestCase):

                def test_multiple_types(self):

                    data = [(0.0, 'a'), (1.0, 'b'), (2, 'c'), (3, 'd')]

                    self.assertValid(data, (Number, str))

In the example above, the :py:class:`Number <numbers.Number>` base
class is used to check for numbers of any type (:py:class:`int`,
:py:class:`float`, :py:class:`complex`, :py:class:`Decimal
<decimal.Decimal>`, etc.).
