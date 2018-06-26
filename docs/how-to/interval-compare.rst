
.. module:: datatest

.. meta::
    :description: How to assert an interval.
    :keywords: datatest, reference data


#########################
How to Assert an Interval
#########################

To check that data elements are within a given interval, you
can use a helper function as the *requirement* value (see
:ref:`predicate-docs`).

In the following example, we define a helper function to check
that an element is between ``5`` and ``10`` (inclusive). Elements
in *data* are considered valid when our function returns ``True``:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 8-10

            import datatest


            def test_interval():

                data = [5, 7, 4, 5, 9]

                def interval(x):
                    """from 5 to 10"""
                    return 5 <= x <= 10

                datatest.validate(data, interval)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 10-12

            import datatest


            class MyTest(datatest.DataTestCase):

                def test_interval(self):

                    data = [5, 7, 4, 5, 9]

                    def interval(x):
                        """from 5 to 10"""
                        return 5 <= x <= 10

                    self.assertValid(data, interval)


========================
Reusable Helper Function
========================

If you are asserting intervals many times, you may want to define
a reusable helper function:


.. code-block:: python

    import operator
    import datatest


    def make_interval(low, high, inclusive=True):
        op = operator.le if inclusive else operator.lt

        def interval(x):
            return op(low, x) and op(x, high)

        interval.__doc__ = 'from {0} to {1}'.format(low, high)

        return interval


Use of this helper function is demonstrated below:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 7

            ...

            def test_interval():

                data = [5, 7, 4, 5, 9]

                interval = make_interval(5, 10)

                datatest.validate(data, interval)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 9

            ...

            class MyTest(datatest.DataTestCase):

                def test_interval(self):

                    data = [5, 7, 4, 5, 9]

                    interval = make_interval(5, 10)

                    self.assertValid(data, interval)
