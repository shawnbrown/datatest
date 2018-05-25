
.. module:: datatest

.. meta::
    :description: How to check for outliers.
    :keywords: datatest, detect outliers


######################
How to Detect Outliers
######################

To detect outliers, we can use a "factory function" to build appropriate
predicates for validating data. The following code uses this approach to
implement the *Tukey fence* method for outlier labeling:


.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 33,41

            from statistics import median
            from datatest import validate, Query


            def check_for_outliers(data, multiplier=2.2):
                """Check for outliers using Tukey fence/interquartile method.

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
                    def predicate(value):
                        return lower_fence <= value <= upper_fence
                    return predicate

                query = Query.from_object(data)
                requirement = query.apply(predicate_factory)

                __tracebackhide__ = True
                msg = 'outliers beyond interquartile range * {0}'.format(multiplier)
                validate(data, requirement, msg)


            def test_outliers1():
                data = [12, 5, 8, 5, 76, 7, 20]  # <- 76 is an outlier
                check_for_outliers(data)


            def test_outliers2():
                data = {
                    'A': [12, 5, 8, 5, 76, 7, 20],  # <- 76 is an outlier
                    'B': [81, 74, 77, 74, 8, 76, 89],  # <- 8 is an outlier
                }
                check_for_outliers(data)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 33,40

            from statistics import median
            from datatest import DataTestCase, Query


            class MyTest(DataTestCase):

                def checkForOutliers(self, data, multiplier=2.2):
                    """Check for outliers using Tukey fence/interquartile method.

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
                        def predicate(value):
                            return lower_fence <= value <= upper_fence
                        return predicate

                    query = Query.from_object(data)
                    requirement = query.apply(predicate_factory)

                    msg = 'outliers beyond interquartile range * {0}'.format(multiplier)
                    self.assertValid(data, requirement, msg)

                def test_outliers1(self):
                    data = [12, 5, 8, 5, 76, 7, 20]  # <- 76 is an outlier
                    self.checkForOutliers(data)

                def test_outliers2(self):
                    data = {
                        'A': [12, 5, 8, 5, 76, 7, 20],  # <- 76 is an outlier
                        'B': [81, 74, 77, 74, 8, 76, 89],  # <- 8 is an outlier
                    }
                    self.checkForOutliers(data)


In the code above, we use :meth:`Query.apply` to build a separate
predicate for each group of values. In the case of ``test_outliers1()``,
there is only one group so this creates one predicate function. But
in ``test_outliers2()``, this creates two separate predicates---with
lower and upper fences appropriate to each group of values.


.. note::

    The previous code relies on :py:func:`statistics.median` which
    is new in Python 3.4. But if you are running an older version of
    Python, you can use the following ``median()`` function instead:

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
