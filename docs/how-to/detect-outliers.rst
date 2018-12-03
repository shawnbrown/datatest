
.. module:: datatest

.. meta::
    :description: How to check for outliers.
    :keywords: datatest, detect outliers


######################
How to Detect Outliers
######################

To detect outliers, we can use a group-requirement to implement
the *Tukey fence*/interquartile method for outlier labeling.
Many common methods for outlier detection are sensitive to
extreme values and can perform poorly when applied to skewed
distributions. The Tukey fence method is provided because it
is less sensitive to extreme values and applies to both normal
and skewed dsitributions.

You can copy the following ``outliers`` requirement to use in
your own tests:

.. code-block:: python

    from decimal import Decimal
    from statistics import median
    from datatest import validate
    from datatest import group_requirement
    from datatest import Deviation


    @group_requirement
    def outliers(iterable):
        """should not contain outlier values

        This requirement uses the Tukey fence/interquartile method
        for outlier labeling. The internal multiplier of 2.2 is based
        on "Fine-Tuning Some Resistant Rules for Outlier Labeling"
        by Hoaglin and Iglewicz (1987).
        """
        iterable = sorted(iterable)

        # Build lower and upper fences.
        midpoint = int(round(len(iterable) / 2.0))
        q1 = median(iterable[:midpoint])
        q3 = median(iterable[midpoint:])
        multiplier = 2.2  # Hoaglin/Iglewicz multiplier.
        kprime = (q3 - q1) * multiplier
        lower_fence = q1 - kprime
        upper_fence = q3 + kprime

        # Round fences so differences are easier to read.
        smallest = iterable[0]
        if isinstance(smallest, float):
            smallest = str(smallest)
        ndigits =  abs(Decimal(smallest).as_tuple().exponent)
        lower_fence = round(lower_fence, ndigits)
        upper_fence = round(upper_fence, ndigits)

        # Check values.
        for value in iterable:
            if value < lower_fence:
                yield Deviation(value - lower_fence, lower_fence)
            elif value > upper_fence:
                yield Deviation(value - upper_fence, upper_fence)


Example Usage
=============

Use of the ``outliers`` requirement is demonstrated below:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 6,14

            ...

            def test_outliers1():
                data = [12, 5, 8, 37, 5, 7, 15]  # <- 37 is an outlier

                validate(data, outliers)


            def test_outliers2():
                data = {
                    'A': [12, 5, 8, 37, 5, 7, 15],  # <- 37 is an outlier
                    'B': [81, 74, 77, 58, 76, 89],  # <- 58 is an outlier
                }
                validate(data, outliers)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 10,17

            from datatest import DataTestCase

            ...

            class MyTest(DataTestCase):

                def test_outliers1(self):
                    data = [12, 5, 8, 37, 5, 7, 15]  # <- 37 is an outlier

                    self.assertValid(data, outliers)

                def test_outliers2(self):
                    data = {
                        'A': [12, 5, 8, 37, 5, 7, 15],  # <- 37 is an outlier
                        'B': [81, 74, 77, 58, 76, 89],  # <- 58 is an outlier
                    }
                    self.assertValid(data, outliers)


.. note::

    The ``outliers`` requirement uses the :py:func:`statistics.median`
    function which is new in Python 3.4. If you are running an older
    version of Python, you can use the following ``median()`` function
    instead:

    .. code-block:: python

        def median(iterable):
            values = sorted(iterable)
            index = (len(values) - 1) / 2.0
            if index % 1:
                lower = int(index - 0.5)
                upper = int(index + 0.5)
                return (values[lower] + values[upper]) / 2.0
            return values[int(index)]


..
    https://www.itl.nist.gov/div898/handbook/eda/section3/eda35h.htm
