
.. module:: datatest

.. meta::
    :description: How to control difference objects.
    :keywords: datatest, differences


#################################
How to Control Difference Objects
#################################

When using a predicate function (see :ref:`predicate-docs`),
datatest will generate difference objects when the function
returns ``False``. By default, an :class:`Invalid` type is
generated but it's possible to change this behavior.

When a predicate function returns a difference object (instead
of ``False``), this difference is used in place of the automatically
generated one.

Below, the helper-function ``max100()`` returns ``True`` if values
are less than or equal to 100 and it returns a :class:`Deviation`
when values are greater than 100:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 11

            from datatest import validate, Deviation


            def test_max_value():

                data = [98, 99, 100, 101, 102]

                def max100(x):  # <- Helper function.
                    if x <= 100:
                        return True
                    return Deviation(x - 100, 100)

                validate(data, max100)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 13

            from datatest import DataTestCase, Deviation


            class MyTest(DataTestCase):

                def test_max_value(self):

                    data = [98, 99, 100, 101, 102]

                    def max100(x):  # <- Helper function.
                        if x <= 100:
                            return True
                        return Deviation(x - 100, 100)

                    self.assertValid(data, max100)
