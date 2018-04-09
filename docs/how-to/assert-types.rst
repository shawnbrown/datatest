
.. module:: datatest

.. meta::
    :description: How to assert data types.
    :keywords: datatest, reference data


########################
How to Assert Data Types
########################

To check that data is of a particular type, you can pass a
type object (e.g., a class) as the *requirement* value
(see :ref:`predicate-docs`).

In the following example, we use the type :py:class:`float`
as the *requirement*. The elements in *data* are considered
valid if they are float instances:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 8

            from datatest import validate


            def test_data_types():

                data = [0.0, 1.0, 2.0]

                validate(data, float)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 10

            from datatest import DataTestCase


            class MyTest(DataTestCase):

                def test_data_types(self):

                    data = [0.0, 1.0, 2.0]

                    self.assertValid(data, float)
