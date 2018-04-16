
.. module:: datatest

.. meta::
    :description: How to check for outliers.
    :keywords: datatest, detect outliers


######################
How to Detect Outliers
######################


.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 38

            from statistics import median
            from datatest import validate, Query


            def check_for_outliers(data, multiplier=2.2):
                """Check for outliers using Tukey Fence/interquartile method."""
                # Default multiplier of 2.2 based on "Fine-Tuning Some Resistant
                # Rules for Outlier Labeling" by Hoaglin and Iglewicz (1987).
                def make_predicate(grp):
                    grp = sorted(grp)
                    midpoint = len(grp) / 2
                    if midpoint % 1 == 0:
                        midpoint = int(midpoint)
                        q1 = median(grp[:midpoint])
                        q3 = median(grp[midpoint:])
                    else:
                        q1 = median(grp[:int(midpoint - 0.5)])
                        q3 = median(grp[int(midpoint + 0.5):])
                    gprime = (q3 - q1) * multiplier  # Close over multiplier.
                    lower = q1 - gprime
                    upper = q3 + gprime
                    def predicate(value):
                        return lower <= value <= upper  # Close over lower & upper.
                    return predicate

                query = Query.from_object(data)
                requirement = query.apply(make_predicate)

                __tracebackhide__ = True
                msg = 'outliers beyond interquartile range * {0}'.format(multiplier)
                validate(data, requirement, msg)


            def test_outliers():

                data = [12, 5, 8, 5, 76, 7, 20]

                check_for_outliers(data)


    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 39

            from statistics import median
            from datatest import DataTestCase, Query


            class MyTest(DataTestCase):

                def checkForOutliers(self, data, multiplier=2.2):
                    """Check for outliers using Tukey Fence/interquartile method."""
                    # Default multiplier of 2.2 based on "Fine-Tuning Some Resistant
                    # Rules for Outlier Labeling" by Hoaglin and Iglewicz (1987).
                    def make_predicate(grp):
                        grp = sorted(grp)
                        midpoint = len(grp) / 2
                        if midpoint % 1 == 0:
                            midpoint = int(midpoint)
                            q1 = median(grp[:midpoint])
                            q3 = median(grp[midpoint:])
                        else:
                            q1 = median(grp[:int(midpoint - 0.5)])
                            q3 = median(grp[int(midpoint + 0.5):])
                        gprime = (q3 - q1) * multiplier  # Close over multiplier.
                        lower = q1 - gprime
                        upper = q3 + gprime
                        def predicate(value):
                            return lower <= value <= upper  # Close over lower & upper.
                        return predicate

                    query = Query.from_object(data)
                    requirement = query.apply(make_predicate)

                    msg = 'outliers beyond interquartile range * {0}'.format(multiplier)
                    self.assertValid(data, requirement, msg)


                def test_outliers(self):

                    data = [12, 5, 8, 5, 76, 7, 20]

                    self.checkForOutliers(data)


.. note::

    The previous code relies on the :py:func:`statistics.median`
    function (new in Python 3.4). If you are running an older
    version of Python, you can use the following ``median()``
    function instead:

    .. code-block:: python

        def median(iterable):
            values = sorted(iterable)
            index = (len(values) - 1) / 2.0
            if index % 1 == 0:
                median = values[int(index)]
            else:
                upper = int(index + 0.5)
                lower = int(index - 0.5)
                median = (values[upper] + values[lower]) / 2.0
            return median

..
    https://www.itl.nist.gov/div898/handbook/eda/section3/eda35h.htm
