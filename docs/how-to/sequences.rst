
.. py:currentmodule:: datatest

.. meta::
    :description: How to validate sequences.
    :keywords: datatest, sequences, order


#########################
How to Validate Sequences
#########################

To check for a specific sequence, you can pass an iterable object
(other than a set, mapping, tuple or string) as the *requirement*
argument:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 8

            from datatest import validate


            def test_sequence():

                data = ['A', 'B', 'X', 'C', 'D']

                requirement = ['A', 'B', 'C', 'D']  # <- a list

                validate(data, requirement)

    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 10

            from datatest import DataTestCase


            class MyTest(DataTestCase):

                def test_sequence(self):

                    data = ['A', 'B', 'X', 'C', 'D']

                    requirement = ['A', 'B', 'C', 'D']  # <- a list

                    self.assertValid(data, requirement)


Elements in the *data* and *requirement* lists are compared by
sequence position. The items at index position 0 are compared to
each other, then items at index position 1 are compared to each
other, and so on:

.. math::

    \begin{array}{cccc}
    \hline
    \textbf{index} & \textbf{data} & \textbf{requirement} & \textbf{result} \\
    \hline
    0 & \textbf{A} & \textbf{A} & \textrm{matches} \\
    1 & \textbf{B} & \textbf{B} & \textrm{matches} \\
    2 & \textbf{X} & \textbf{C} & \textrm{doesn't match} \\
    3 & \textbf{C} & \textbf{D} & \textrm{doesn't match} \\
    4 & \textbf{D} & no\;value & \textrm{doesn't match} \\
    \hline
    \end{array}


In this example, there are three differences:

.. code-block:: none

    ValidationError: does not match required sequence (3 differences): [
        Invalid('X', expected='C'),
        Invalid('C', expected='D'),
        Extra('D'),
    ]


Enumerated Sequences
--------------------

While the previous example works well for short lists, the error
does not describe **where** in your sequence the differences occur.
To get the index positions associated with any differences, you
can :py:func:`enumerate` your *data* and *requirement* objects:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python
            :emphasize-lines: 10

            from datatest import validate


            def test_enumerated_sequence():

                data = ['A', 'B', 'X', 'C', 'D']

                requirement = ['A', 'B', 'C', 'D']

                validate(enumerate(data), enumerate(requirement))

    .. group-tab:: Unittest

        .. code-block:: python
            :emphasize-lines: 12

            from datatest import DataTestCase


            class MyTest(DataTestCase):

                def test_enumerated_sequence(self):

                    data = ['A', 'B', 'X', 'C', 'D']

                    requirement = ['A', 'B', 'C', 'D']

                    self.assertValid(enumerate(data), enumerate(requirement))


A required **enumerate object** is treated as a mapping. The keys
for any differences will correspond to their index positions:

.. code-block:: none

    ValidationError: does not satisfy mapping requirements (3 differences): {
        2: Invalid('X', expected='C'),
        3: Invalid('C', expected='D'),
        4: Extra('D'),
    }


Element Order
-------------

When comparing elements by sequence position, one mis-alignment can
create differences for all following elements. If this behavior
is not desireable, you may want to check for relative order instead.

.. tabs::

    .. group-tab:: Pytest

        If you want to check the relative order of elements rather than
        their index positions, you can use :meth:`validate.order`:

        .. code-block:: python
            :emphasize-lines: 10

            from datatest import validate


            def test_sequence_order():

                data = ['A', 'B', 'X', 'C', 'D']

                requirement = ['A', 'B', 'C', 'D']

                validate.order(data, requirement)

    .. group-tab:: Unittest

        If you want to check the relative order of elements rather than
        their index positions, you can use :meth:`assertValidOrder()
        <DataTestCase.assertValidOrder>`:

        .. code-block:: python
            :emphasize-lines: 12

            from datatest import DataTestCase


            class MyTest(DataTestCase):

                def test_sequence_order(self):

                    data = ['A', 'B', 'X', 'C', 'D']

                    requirement = ['A', 'B', 'C', 'D']

                    self.assertValidOrder(data, requirement)


When checking for relative order, this method tries to align
elements into contiguous matching subsequences. This reduces
the number of non-matches:

.. math::

    \begin{array}{cccc}
    \hline
    \textbf{index} & \textbf{data} & \textbf{requirement} & \textbf{result} \\
    \hline
    0 & \textbf{A} & \textbf{A} & \textrm{matches} \\
    1 & \textbf{B} & \textbf{B} & \textrm{matches} \\
    2 & \textbf{X} & no\;value & \textrm{doesn't match} \\
    3 & \textbf{C} & \textbf{C} & \textrm{matches} \\
    4 & \textbf{D} & \textbf{D} & \textrm{matches} \\
    \hline
    \end{array}

Differences are reported as two-tuples containing the index (in *data*)
where the difference occurs and the non-matching value. In the earlier
examples, we saw that validating by index position produced three
differences. But in this example, validating the same sequences by
relative order produces only one difference:

.. code-block:: none

    ValidationError: does not match required order (1 difference): [
         Extra((2, 'X')),
    ]

