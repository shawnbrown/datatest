
.. module:: datatest

.. meta::
    :description: How to assert an interval.
    :keywords: datatest, reference data


#########################
How to Assert an Interval
#########################

To check that data elements are within a given interval, you can
define a helper function to use as the *requirement* value (see
:ref:`predicate-docs`).

In the following example, we define a simple helper function to
check that an element is between ``5`` and ``10``. Elements in
*data* are considered valid when our function returns ``True``:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 8-9

            from datatest import validate


            def test_interval():

                data = [5, 7, 4, 5, 9]

                def from5to10(x):
                    return 5 <= x <= 10

                validate(data, from5to10)

    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 10-11

            from datatest import DataTestCase


            class MyTest(DataTestCase):

                def test_interval(self):

                    data = [5, 7, 4, 5, 9]

                    def from5to10(x):
                        return 5 <= x <= 10

                    self.assertValid(data, from5to10)


========================
Reusable Helper Function
========================

If you are asserting intervals many times or need to handle differences
as :class:`Deviation` objects (instead of :class:`Invalid` objects) you
can use the following ``interval()`` function in your own tests:

.. code-block:: python

    import operator
    from datatest import Deviation


    def interval(low, high, inclusive=True):
        if low > high:
            raise ValueError('low must be less than high')
        op = operator.le if inclusive else operator.lt

        def _interval(value):
            if not op(low, value):
                return Deviation(value - low, low)
            if not op(value, high):
                return Deviation(value - high, high)
            return True

        exclusive = ', exclusive' if not inclusive else ''
        description = 'values should range from {0} to {1}{2}'
        _interval.__doc__ = description.format(low, high, exclusive)
        return _interval


Example Usage
=============

Use of the ``interval()`` function is demonstrated below:

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
