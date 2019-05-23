
.. module:: datatest

.. meta::
    :description: An overview of the "datatest" Python package, describing
                  its features and basic operation with examples.
    :keywords: introduction, datatest, examples


##################
A Tour of Datatest
##################

This document introduces :doc:`datatest </index>`'s support for
validation, error reporting, and acceptance declarations.


**********
Validation
**********

In this example, we assert that the data values are members of
the *requirement* **set**:

.. tabs::

    .. group-tab:: Pytest

        The :func:`validate` function checks that the *data* under
        test satisfies a given *requirement*:

        .. literalinclude:: /_static/tutorial/test_intro1.py
            :lines: 4-13
            :lineno-match:
            :emphasize-lines: 10

    .. group-tab:: Unittest

        The :meth:`self.assertValid() <DataTestCase.assertValid>`
        method checks that the *data* under test satisfies a given
        *requirement*:

        .. literalinclude:: /_static/tutorial/test_intro1_unit.py
            :lines: 4-15
            :lineno-match:
            :emphasize-lines: 12


**The requirement's type determines how the data is validated---changing
the type will change the method of validation.** Above, we checked for
set membership by providing a :py:class:`set` requirement.


When *requirement* is a **function**, data is valid when the function
returns True:

.. tabs::

    .. group-tab:: Pytest

        .. literalinclude:: /_static/tutorial/test_intro1.py
            :pyobject: test_using_function
            :lineno-match:

    .. group-tab:: Unittest

        .. literalinclude:: /_static/tutorial/test_intro1_unit.py
            :pyobject: ExampleTests.test_using_function
            :lineno-match:


When *requirement* is a **type**, data is valid when values are
instances of the given type:

.. tabs::

    .. group-tab:: Pytest

        .. literalinclude:: /_static/tutorial/test_intro1.py
            :pyobject: test_using_type
            :lineno-match:

    .. group-tab:: Unittest

        .. literalinclude:: /_static/tutorial/test_intro1_unit.py
            :pyobject: ExampleTests.test_using_type
            :lineno-match:


When *requirement* is a **regular expression** pattern, data
is valid when it matches the given pattern:

.. tabs::

    .. group-tab:: Pytest

        .. literalinclude:: /_static/tutorial/test_intro1.py
            :pyobject: test_using_regex
            :lineno-match:

    .. group-tab:: Unittest

        .. literalinclude:: /_static/tutorial/test_intro1_unit.py
            :pyobject: ExampleTests.test_using_regex
            :lineno-match:


More Information
----------------

.. tabs::

    .. group-tab:: Pytest

        * For a complete list of validation behaviors see :func:`validate`.
        * For a complete list of predicate objects, see :ref:`predicate-docs`.
        * Download a collection of examples:
          :download:`test_intro1.py </_static/tutorial/test_intro1.py>`
        * Run the examples with the following command:

            .. code-block:: none

                pytest test_intro1.py


    .. group-tab:: Unittest

        * For a complete list of validation behaviors see :meth:`self.assertValid()
          <DataTestCase.assertValid>`.
        * For a complete list of predicate objects, see :ref:`predicate-docs`.
        * Download a collection of examples:
          :download:`test_intro1_unit.py </_static/tutorial/test_intro1_unit.py>`
        * Run the examples with the following command:

            .. code-block:: none

                python -m datatest test_intro1_unit.py


********
Failures
********

When validation fails, a :class:`ValidationError` is
raised. A ValidationError contains a collection of
difference objects---one difference for each element
in *data* that fails to satisfy the *requirement*.

In the following test, we assert that values in the
list ``['A', 'B', 'C', 'D']`` are members of the set
``{'A', 'B'}``. This test fails because the values
``'C'`` and ``'D'`` are not members of the set:

.. tabs::

    .. group-tab:: Pytest

        .. literalinclude:: /_static/tutorial/test_intro2.py
            :lines: 4-14
            :lineno-match:

        The test fails with the following message:

        .. code-block:: none
            :emphasize-lines: 10-13

            _____________________________ test_set_membership ______________________________

                def test_set_membership():
                    """Check for set membership."""
                    data = ['A', 'B', 'C', 'D']

                    requirement = {'A', 'B'}

            >       validate(data, required_elements)
            E       ValidationError: does not satisfy set membership (2 differences): [
                        Extra('C'),
                        Extra('D'),
                    ]

            test_example.py:14: ValidationError


    .. group-tab:: Unittest

        .. literalinclude:: /_static/tutorial/test_intro2_unit.py
            :lines: 4-14
            :lineno-match:

        The test fails with the following message:

        .. code-block:: none
            :emphasize-lines: 7-10

            ======================================================================
            FAIL: test_set_membership (test_unittesting.MyTest)
            ----------------------------------------------------------------------
            Traceback (most recent call last):
              File "/my/projects/folder/test_example.py", line 14, in test_set_membership
                self.assertValid(data, requirement)
            datatest.ValidationError: does not satisfy set membership (2 differences): [
                Extra('C'),
                Extra('D'),
            ]


**Difference objects describe each invalid element and can
be one of of four types:** :class:`Missing`, :class:`Extra`,
:class:`Deviation` or :class:`Invalid`. The error above included
an Extra difference but other validation methods (determined by
the *requirement* type) can give other differences.


The following test performs a tuple comparison but it fails on
``('A', 2)`` because the ``2`` is not a float type. This failure
raises an :class:`Invalid` difference:

.. tabs::

    .. group-tab:: Pytest

        .. literalinclude:: /_static/tutorial/test_intro2.py
            :pyobject: test_using_tuple
            :lineno-match:

        .. code-block:: none
            :emphasize-lines: 12-15

            _______________________________ test_using_tuple _______________________________

                def test_using_tuple():
                    """Check that tuples of values satisfy corresponding tuple of
                    requirements.
                    """
                    data = [('A', 1.0), ('A', 2), ('B', 3.0)]

                    requirement = ('A', float)

            >       validate(data, requirement)
            E       ValidationError: does not satisfy requirement (2 differences): [
                        Invalid(('A', 2)),
                        Invalid(('B', 3.0)),
                    ]

            test_intro2.py:58: ValidationError


    .. group-tab:: Unittest

        .. literalinclude:: /_static/tutorial/test_intro2_unit.py
            :pyobject: ExampleTests.test_using_tuple
            :lineno-match:

        .. code-block:: none
            :emphasize-lines: 8-11

            ======================================================================
            FAIL: test_using_tuple (test_intro2_unit.ExampleTests)
            Check that tuples of values satisfy corresponding tuple of
            ----------------------------------------------------------------------
            Traceback (most recent call last):
              File "/my/projects/folder/test_intro2_unit.py", line 53, in test_using_tuple
                self.assertValid(data, requirement)
            datatest.ValidationError: does not satisfy requirement (2 differences): [
                Invalid(('A', 2)),
                Invalid(('B', 3.0)),
            ]


The following test compares the values of corresponding dictionary keys.
It fails because some of the values don't match (for "C": ``299`` ≠ ``300``
and "D": ``405`` ≠ ``400``). Failed numeric comparisons raise
:class:`Deviation` differences:

.. tabs::

    .. group-tab:: Pytest

        .. literalinclude:: /_static/tutorial/test_intro2.py
            :pyobject: test_using_dict
            :lineno-match:

        .. code-block:: none
            :emphasize-lines: 18-21

            _______________________________ test_using_dict ________________________________

                def test_using_dict():
                    """Check that values satisfy requirements of matching keys."""
                    data = {
                        'A': 100,
                        'B': 200,
                        'C': 299,
                        'D': 405,
                    }
                    requirement = {
                        'A': 100,
                        'B': 200,
                        'C': 300,
                        'D': 400,
                    }
            >       validate(data, requirement)
            E       ValidationError: does not satisfy mapping requirement (2 differences): {
                        'C': Deviation(-1, 300),
                        'D': Deviation(+5, 400),
                    }

            test_intro2.py:75: ValidationError


    .. group-tab:: Unittest

        .. literalinclude:: /_static/tutorial/test_intro2_unit.py
            :pyobject: ExampleTests.test_using_dict
            :lineno-match:

        .. code-block:: none
            :emphasize-lines: 8-11

            ======================================================================
            FAIL: test_using_dict (test_intro2_unit.ExampleTests)
            Check that values satisfy requirements of matching keys.
            ----------------------------------------------------------------------
            Traceback (most recent call last):
              File "/my/projects/folder/test_intro2_unit.py", line 69, in test_using_dict
                self.assertValid(data, requirement)
            ValidationError: does not satisfy mapping requirement (2 differences): {
                'C': Deviation(-1, 300),
                'D': Deviation(+5, 400),
            }


For more information, see :ref:`difference-docs`.


.. tabs::

    .. group-tab:: Pytest

        Download a collection of failure examples:

            :download:`test_intro2.py </_static/tutorial/test_intro2.py>`

        Run them with the following command:

        .. code-block:: none

            pytest test_intro2.py


    .. group-tab:: Unittest

        Download a collection of failure examples:

            :download:`test_intro2_unit.py </_static/tutorial/test_intro2_unit.py>`

        Run them with the following command:

            .. code-block:: none

                python -m datatest test_intro2_unit.py


***********
Acceptances
***********

Sometimes a failing test cannot be addressed by changing the data
itself. Perhaps two equally-authoritative sources disagree, perhaps
it's important to keep the original data unchanged, perhaps a lack
of information makes correction impossible. For cases like these,
datatest can accept certain discrepancies when users judge that doing
so is appropriate.

Acceptances are context managers that operate on a ValidationError's
collection of differences.

Normally the following test would fail because the values ``'C'``
and ``'D'`` are not members of the set (as shown previously). But if
we decide that :class:`Extra` differences are acceptible, we can add
an acceptance so the test will pass:

.. tabs::

    .. group-tab:: Pytest

        Calling :meth:`accepted(Extra) <accepted>` returns a context
        manager that accepts Extra differences without triggering a
        test failure:

        .. code-block:: python
            :emphasize-lines: 11
            :lineno-start: 4

            from datatest import validate
            from datatest import accepted


            def test_using_set():
                """Check for set membership."""
                data = ['A', 'B', 'C', 'D']

                requirement = {'A', 'B'}

                with accepted(Extra):
                    validate(data, requirement)

    .. group-tab:: Unittest

        Calling :meth:`self.accepted(Extra) <datatest.DataTestCase.accepted>`
        returns a context manager that accepts Extra differences without
        triggering a test failure:

        .. code-block:: python
            :emphasize-lines: 11
            :lineno-start: 4

            import datatest


            class ExampleTests(datatest.DataTestCase):
                def test_using_set(self):
                    """Check for set membership."""
                    data = ['A', 'B', 'C', 'D']

                    requirement = {'A', 'B'}

                    with self.accepted(Extra):
                        self.assertValid(data, requirement)


Datatest provides several different acceptances so users can
precisely specify the criteria by which differences should be
accepted. In the following example, numeric differences are
accepted by their magnitude:

.. tabs::

    .. group-tab:: Pytest

        Calling :meth:`accepted.tolerance(5) <accepted.tolerance>`
        returns a context manager that accepts Deviations up to
        plus-or-minus five without triggering a test failure:

        .. code-block:: python
            :emphasize-lines: 15
            :lineno-start: 61

            def test_using_dict():
                """Check that values satisfy requirements of matching keys."""
                data = {
                    'A': 100,
                    'B': 200,
                    'C': 299,
                    'D': 405,
                }
                requirement = {
                    'A': 100,
                    'B': 200,
                    'C': 300,
                    'D': 400,
                }
                with accepted.tolerance(5):  # accepts ±5
                    validate(data, requirement)

    .. group-tab:: Unittest

        Calling :meth:`self.acceptedTolerance(5) <DataTestCase.acceptedTolerance>`
        returns a context manager that accepts Deviations up to
        plus-or-minus five without triggering a test failure:

        .. code-block:: python
            :emphasize-lines: 15
            :lineno-start: 55

                def test_using_dict(self):
                    """Check that values satisfy requirements of matching keys."""
                    data = {
                        'A': 100,
                        'B': 200,
                        'C': 299,
                        'D': 405,
                    }
                    requirement = {
                        'A': 100,
                        'B': 200,
                        'C': 300,
                        'D': 400,
                    }
                    with self.acceptedTolerance(5):  # accepts ±5
                        self.assertValid(data, requirement)

    For a list of all possible acceptances see :ref:`acceptance-docs`.


***********
Other Tools
***********

Datatest also provides a few utilities for handling data:

:class:`working_directory`
    Context manager and decorator to temporarily set a working
    directory.

:class:`get_reader() <datatest.get_reader>`
    Get a csv.reader-like interface for pandas DataFrames, MS Excel
    worksheets, etc.

:class:`Select`, :class:`Query`, and :class:`Result`
    Select and query tabular data that can be tested for validity.

:class:`RepeatingContainer`
    Operate on a group of objects together instead of repeating
    the same methods and operations on each individual object
    (useful when comparing one source of data against another).
