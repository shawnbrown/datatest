
.. module:: datatest

.. meta::
    :description: How to check for outliers.
    :keywords: datatest, detect outliers


#########################
How to Check for Outliers
#########################

To detect outliers, you can use the :meth:`validate.outliers` method
which implements an interquartile/*Tukey fence* approach for outlier
labeling.

Some common methods for outlier detection are sensitive to extreme
values and can perform poorly when applied to skewed distributions.
The Tukey fence method is provided because it's resistant to extreme
values and applies to both normal and slightly skewed distributions.

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 6,14

            from datatest import validate


            def test_outliers1():
                data = [54, 44, 42, 46, 87, 48, 56, 52]  # <- 87 is an outlier
                validate.outliers(data, multiplier=2.2)


            def test_outliers2():
                data = {
                    'A': [54, 44, 42, 46, 87, 48, 56, 52],  # <- 87 is an outlier
                    'B': [87, 83, 60, 85, 97, 91, 95, 93],  # <- 60 is an outlier
                }
                validate.outliers(data, multiplier=2.2)

    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 7,14

            from datatest import DataTestCase


            class MyTest(DataTestCase):
                def test_outliers1(self):
                    data = [54, 44, 42, 46, 87, 48, 56, 52]  # <- 87 is an outlier
                    self.assertValidOutliers(data, multiplier=2.2)

                def test_outliers2(self):
                    data = {
                        'A': [54, 44, 42, 46, 87, 48, 56, 52],  # <- 87 is an outlier
                        'B': [87, 83, 60, 85, 97, 91, 95, 93],  # <- 60 is an outlier
                    }
                    self.assertValidOutliers(data, multiplier=2.2)

Once potential outliers have been identified, you need to decide
how best to address them---there is no single rule for determining
what to do. Potential outliers provide a starting point for further
investigation.

In some cases, these extreme values are legitimate and you will want to
increase the *multiplier* or allow them (see :ref:`allowance-docs`).
In other cases, you may determine that your data contains values from
two separate distributions and the test itself needs to be restructured.
Or you could discover that they represent data processing errors or
other erroneous values that should be excluded altogether.

For more on multipliers, see the :meth:`outliers() <validate.outliers>`
reference documentation.


How it Works
============

To use this approach most effectively, it helps to understand how
it works. The following example explains the technique in detail
using the same data as the ``test_outliers1()`` example above:

   .. math::

        \begin{array}{ccccccccccccccc}
        54 && 44 && 42 && 46 && 87 && 48 && 56 && 52 \\
        \end{array}

1. Determine the first and third quartiles. First, sort the values
   in ascending order. Then, split the data in half at its median.
   The first quartile (**Q1**) is the median of the lower half and
   the third quartile (**Q3**) is the median of the upper half:

   .. math::

        \begin{array}{c}
            \begin{array}{ccc}
                \mathbf{Q1}\;(45) && \mathbf{Q3}\;(55) \\
                \downarrow && \downarrow \\
                \begin{array}{ccccccc}42 && 44 && 46 && 48\end{array}
                    && \begin{array}{ccccccc}52 && 54 && 56 && 87\end{array}
            \end{array} \\
            \uparrow \\
            median\;(50) \\
        \end{array}

2. Get the interquartile range (**IQR**) by taking the third quartile
   and subtracting the first quartile from it:

   .. math::

        \mathbf{IQR = Q3 - Q1}

   .. math::

        10 = 55 - 45

3. Calculate a lower and upper limit using the values determined in
   the previous steps:

   .. math::

        \mathbf{\text{lower limit} = Q1 - (IQR \times multiplier)}

   .. math::

        23 = 45 - (10 \times 2.2)

   .. math::

        \mathbf{\text{upper limit} = Q3 + (IQR \times multiplier)}

   .. math::

        77 = 55 + (10 \times 2.2)

5. Check that values are within the determined limits. Any value less
   than the lower limit (23) or greater than the upper limit (77) is
   considered a potential outlier. In the given data, there is one
   potential outlier:

   .. math::

        87

