
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
            :emphasize-lines: 8-9

            from datatest import validate


            def test_interval():

                data = [5, 7, 4, 5, 9]

                def from5to10(x):
                    return 5 <= x <= 10  # <- Interval comparison.

                validate(data, from5to10)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 10-11

            from datatest import DataTestCase


            class MyTest(DataTestCase):

                def test_interval(self):

                    data = [5, 7, 4, 5, 9]

                    def from5to10(x):
                        return 5 <= x <= 10  # <- Interval comparison.

                    self.assertValid(data, from5to10)


========================
Reusable Helper Function
========================

If you are asserting intervals multiple times, you may want to
define a reusable helper function:

.. code-block:: python

    def interval(low, high, inclusive=True):
        """Returns a predicate function that asserts an interval."""

        if inclusive:
            def func(x):
                return low <= x <= high
        else:
            def func(x):
                return low < x < high

        func.__name__ = 'interval({0}, {1}{2})'.format(
            low,
            high,
            '' if inclusive else ', inclusive=False',
        )
        return func


Use of this helper function is demonstrated below:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 9

            from datatest import validate

            ...

            def test_interval():

                data = [5, 7, 4, 5, 9]

                validate(data, interval(5, 10))


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 11

            from datatest import DataTestCase

            ...

            class MyTest(DataTestCase):

                def test_interval(self):

                    data = [5, 7, 4, 5, 9]

                    self.assertValid(data, interval(5, 10))
