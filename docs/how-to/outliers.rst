
.. currentmodule:: datatest

.. meta::
    :description: How to check for outliers.
    :keywords: datatest, detect outliers


#########################
How to Check for Outliers
#########################

There are many techniques for detecting outliers and no single
approach can work for all cases. This page describes an often
useful approach based on the interquartile/*Tukey fence* method
for outlier detection.

Other common methods for outlier detection are sensitive to extreme
values and can perform poorly when applied to skewed distributions.
The Tukey fence method is resistant to extreme values and applies
to both normal and slightly skewed distributions.

You can copy the following ``RequiredOutliers`` class to use in
your own tests:

.. code-block:: python
    :linenos:

    from statistics import median
    from datatest import validate
    from datatest.requirements import adapts_mapping
    from datatest.requirements import RequiredInterval


    @adapts_mapping
    class RequiredOutliers(RequiredInterval):
        """Require that data does not contain outliers."""
        def __init__(self, values, multiplier=2.2):
            values = sorted(values)

            if len(values) >= 2:
                midpoint = int(round(len(values) / 2.0))
                q1 = median(values[:midpoint])
                q3 = median(values[midpoint:])
                iqr = q3 - q1
                lower = q1 - (iqr * multiplier)
                upper = q3 + (iqr * multiplier)
            elif values:
                lower = upper = values[0]
            else:
                lower = upper = 0

            super().__init__(lower, upper)

    ...


In "Exploratory Data Analysis" by John W. Tukey (1977), a multiplier
of 1.5 was proposed for labeling outliers and 3.0 was proposed for
labeling "far out" outliers. The default *multiplier* of ``2.2``
is based on "Fine-Tuning Some Resistant Rules for Outlier Labeling"
by Hoaglin and Iglewicz (1987).


.. note::

    The code above relies on :py:func:`statistics.median` which is new
    in Python 3.4. If you are running an older version of Python, you
    can use the following ``median()`` function instead:

    .. code-block:: python

        def median(iterable):
            values = sorted(iterable)
            n = len(values)
            if n == 0:
                raise ValueError('no median for empty iterable')
            i = n // 2
            if n % 2 == 1:
                return values[i]
            return (values[i - 1] + values[i]) / 2.0


Example Usage
=============

The following example uses the ``RequiredOutliers`` class defined
earlier to check for outliers in a list of values:

.. code-block:: python
    :emphasize-lines: 4
    :linenos:
    :lineno-start: 28

    ...

    data = [54, 44, 42, 46, 87, 48, 56, 52]  # <- 87 is an outlier
    requirement = RequiredOutliers(data, multiplier=2.2)
    validate(data, requirement)


.. code-block:: none

    ValidationError: elements `x` do not satisfy `23.0 <= x <= 77.0` (1 difference): [
        Deviation(+10.0, 77.0),
    ]


You can also use the class to validate mappings of values as well:

.. code-block:: python
    :emphasize-lines: 7
    :linenos:
    :lineno-start: 33

    ...

    data = {
        'A': [54, 44, 42, 46, 87, 48, 56, 52],  # <- 87 is an outlier
        'B': [87, 83, 60, 85, 97, 91, 95, 93],  # <- 60 is an outlier
    }
    requirement = RequiredOutliers(data, multiplier=2.2)
    validate(data, requirement)


.. code-block:: none

    ValidationError: does not satisfy mapping requirements (2 differences): {
        'A': [Deviation(+10.0, 77.0)],
        'B': [Deviation(-2.0, 62.0)],
    }


Addressing Outliers
===================

Once potential outliers have been identified, you need to decide
how best to address them---there is no single best practice for
determining what to do. Potential outliers provide a starting point
for further investigation.

In some cases, these extreme values are legitimate and you will
want to increase the *multiplier* or explicitly accept them
(see :ref:`acceptance-docs`). In other cases, you may determine that
your data contains values from two separate distributions and the
test itself needs to be restructured. Or you could discover that
the values represent data processing errors or other special cases
and they should be excluded altogether.


How it Works
============

To use this approach most effectively, it helps to understand how
it works. The following example explains the technique in detail
using the same data as the first example given above:

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

..
    There is no rigorous way to define outliers that is independent of
    the context in which the data was produced and its intended use.

