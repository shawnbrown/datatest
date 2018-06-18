
.. module:: datatest

.. meta::
    :description: How to check for outliers.
    :keywords: datatest, detect outliers


######################
How to Detect Outliers
######################

To detect outliers, we can use a "factory function" to build appropriate
predicates for testing. The code below uses this approach to implement
the *Tukey fence* method for outlier labeling.

You can copy the following function to use in your own tests:

.. code-block:: python

    from statistics import median
    import datatest


    def make_outlier_check(obj, multiplier=2.2):
        """Makes outlier detector using Tukey fence/interquartile method.

        Default multiplier of 2.2 based on "Fine-Tuning Some Resistant
        Rules for Outlier Labeling" by Hoaglin and Iglewicz (1987).
        """
        def predicate_factory(values):
            values = sorted(values)
            midpoint = int(round(len(values) / 2.0))
            q1 = median(values[:midpoint])
            q3 = median(values[midpoint:])
            kprime = (q3 - q1) * multiplier
            lower_fence = q1 - kprime
            upper_fence = q3 + kprime
            def outlier_predicate(value):
                return lower_fence <= value <= upper_fence
            return outlier_predicate

        query = datatest.Query.from_object(obj)
        return query.apply(predicate_factory)


.. note::

    The code above relies on :py:func:`statistics.median` which is new
    in Python 3.4. If you are running an older version of Python, you
    can use the following ``median()`` function instead:

    .. code-block:: python

        def median(iterable):
            values = sorted(iterable)
            index = (len(values) - 1) / 2.0
            if index % 1:
                lower = int(index - 0.5)
                upper = int(index + 0.5)
                return (values[lower] + values[upper]) / 2.0
            return values[int(index)]


Example Usage
=============

Use of ``make_outlier_check()`` is demonstrated below:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 6,16

            ...

            def test_outliers1():
                data = [12, 5, 8, 5, 76, 7, 20]  # <- 76 is an outlier

                outlier_check = make_outlier_check(data)
                datatest.validate(data, outlier_check)


            def test_outliers2():
                data = {
                    'A': [12, 5, 8, 5, 76, 7, 20],  # <- 76 is an outlier
                    'B': [81, 74, 77, 74, 8, 76, 89],  # <- 8 is an outlier
                }

                outlier_check = make_outlier_check(data)
                datatest.validate(data, outlier_check)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 8,17

            ...

            class MyTest(datatest.DataTestCase):

                def test_outliers1(self):
                    data = [12, 5, 8, 5, 76, 7, 20]  # <- 76 is an outlier

                    outlier_check = make_outlier_check(data)
                    self.assertValid(data, outlier_check)

                def test_outliers2(self):
                    data = {
                        'A': [12, 5, 8, 5, 76, 7, 20],  # <- 76 is an outlier
                        'B': [81, 74, 77, 74, 8, 76, 89],  # <- 8 is an outlier
                    }

                    outlier_check = make_outlier_check(data)
                    self.assertValid(data, outlier_check)


The function builds separate predicates for each group of values. In
the case of ``test_outliers1()``, there is only one group so it builds
one predicate function. But in ``test_outliers2()``, it builds two
separate predicates---with lower and upper fences appropriate to each
group of values.


..
    https://www.itl.nist.gov/div898/handbook/eda/section3/eda35h.htm
