
.. module:: datatest

.. meta::
    :description: How to assert an interval.
    :keywords: datatest, testing, intervals, ranges


#########################
How to Validate Intervals
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
            :emphasize-lines: 8-10

            from datatest import validate


            def test_interval():

                data = [5, 7, 4, 5, 9]

                def from5to10(x):
                    """values should range from 5 to 10"""
                    return 5 <= x <= 10

                validate(data, from5to10)

    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 10-12

            from datatest import DataTestCase


            class MyTest(DataTestCase):

                def test_interval(self):

                    data = [5, 7, 4, 5, 9]

                    def from5to10(x):
                        """values should range from 5 to 10"""
                        return 5 <= x <= 10

                    self.assertValid(data, from5to10)


The example above will produce :class:`Invalid` differences when the
function returns False. You can change this to produce :class:`Deviation`
differences instead with the following code:

.. code-block:: python

    def from5to10(x):
        """values should range from 5 to 10"""
        low, high = 5, 10
        if x < low:
            return Deviation(x - low, low)
        if x > high:
            return Deviation(x - high, high)
        return True


========================
Custom Requirement Class
========================

If you need to assert intervals in many different tests, you may want
to define a custom requirement class to limit code duplication. The
following ``RequiredInterval`` class can be used for this purpose:

.. code-block:: python

    import operator
    from datatest import requirements
    from datatest import Deviation


    class RequiredInterval(requirements.GroupRequirement):
        def __init__(self, low, high, inclusive=True):
            if not low < high:
                raise ValueError('low must be less than high')
            self.low = low
            self.high = high
            self.op = operator.le if inclusive else operator.lt

        def _get_differences(self, group):
            low, high, op = self.low, self.high, self.op
            for element in group:
                if not op(low, element):
                    yield Deviation(element - low, low)
                elif not op(element, high):
                    return Deviation(element - high, high)

        def check_group(self, group):
            """Takes an iterable *group* of elements, returns a tuple
            containing an iterable of differences and a description.
            """
            differences = self._get_differences(group)
            description = 'values should range from {0} to {1}{2}'.format(
                self.low,
                self.high,
                '' if self.op is operator.le else ', exclusive'
            )
            return differences, description


Use of the custom ``RequiredInterval`` class is demonstrated below:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 9

            from datatest import validate

            ...

            def test_interval():

                data = [5, 7, 4, 5, 9]

                validate(data, RequiredInterval(5, 10))


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 11

            from datatest import DataTestCase

            ...

            class MyTest(DataTestCase):

                def test_interval(self):

                    data = [5, 7, 4, 5, 9]

                    self.assertValid(data, RequiredInterval(5, 10))
