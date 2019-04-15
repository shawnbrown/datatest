
.. module:: datatest

.. meta::
    :description: An overview of the "datatest" Python package, describing
                  its features and basic operation with examples.
    :keywords: introduction, datatest, examples


##################
A Tour of Datatest
##################

This document introduces :doc:`datatest </index>`'s support for
validation, error reporting, and allowance declarations.


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


For a complete list of available types and behaviors, see :ref:`predicate-docs`.


.. tabs::

    .. group-tab:: Pytest

        Download a collection of examples:

            :download:`test_intro1.py </_static/tutorial/test_intro1.py>`

        Run them with the following command:

        .. code-block:: none

            pytest test_intro1.py


    .. group-tab:: Unittest

        Download a collection of examples:

            :download:`test_intro1_unit.py </_static/tutorial/test_intro1_unit.py>`

        Run them with the following command:

            .. code-block:: none

                python -m datatest test_intro1_unit.py


********
Failures
********

When validation fails, a :class:`ValidationError` is
raised. A ValidationError contains a collection of
difference objects---one difference for each element
in *data* that fails to satisfy the *requirement*.

In the following test, we assert that values in the list
``['A', 'B', 'C']`` are members of the set ``{'A', 'B'}``.
This test fails because the value ``'C'`` is not a member
of the set:

.. tabs::

    .. group-tab:: Pytest

        .. literalinclude:: /_static/tutorial/test_intro2.py
            :lines: 4-14
            :lineno-match:

        The test fails with the following message:

        .. code-block:: none
            :emphasize-lines: 10-12

            _____________________________ test_set_membership ______________________________

                def test_set_membership():
                    """Check for set membership."""
                    data = ['A', 'B', 'C']

                    requirement = {'A', 'B'}

            >       validate(data, required_elements)
            E       ValidationError: does not satisfy set membership (1 difference): [
                        Extra('C'),
                    ]

            test_example.py:14: ValidationError


    .. group-tab:: Unittest

        .. literalinclude:: /_static/tutorial/test_intro2_unit.py
            :lines: 4-14
            :lineno-match:

        The test fails with the following message:

        .. code-block:: none
            :emphasize-lines: 7-9

            ======================================================================
            FAIL: test_set_membership (test_unittesting.MyTest)
            ----------------------------------------------------------------------
            Traceback (most recent call last):
              File "/my/projects/folder/test_example.py", line 14, in test_set_membership
                self.assertValid(data, requirement)
            datatest.ValidationError: does not satisfy set membership (1 difference): [
                Extra('C'),
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
            :emphasize-lines: 12-14

            _______________________________ test_using_tuple _______________________________

                def test_using_tuple():
                    """Check that tuples of values satisfy corresponding tuple of
                    requirements.
                    """
                    data = [('A', 0.0), ('A', 1.0), ('A', 2)]

                    requirement = ('A', float)

            >       validate(data, requirement)
            E       ValidationError: does not satisfy requirement (1 difference): [
                        Invalid(('A', 2)),
                    ]

            test_intro2.py:58: ValidationError


    .. group-tab:: Unittest

        .. literalinclude:: /_static/tutorial/test_intro2_unit.py
            :pyobject: ExampleTests.test_using_tuple
            :lineno-match:

        .. code-block:: none
            :emphasize-lines: 8-10

            ======================================================================
            FAIL: test_using_tuple (test_intro2_unit.ExampleTests)
            Check that tuples of values satisfy corresponding tuple of
            ----------------------------------------------------------------------
            Traceback (most recent call last):
              File "/my/projects/folder/test_intro2_unit.py", line 53, in test_using_tuple
                self.assertValid(data, requirement)
            datatest.ValidationError: does not satisfy requirement (1 difference): [
                Invalid(('A', 2)),
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


**********
Allowances
**********

Sometimes a failing test cannot be addressed by changing the data
itself. Perhaps two equally-authoritative sources disagree, perhaps
it's important to keep the original data unchanged, perhaps a lack
of information makes correction impossible. For cases like these,
datatest can allow certain discrepancies when users judge that doing
so is appropriate.

Allowances are context managers that operate on a ValidationError's
collection of differences.

Normally the following test would fail because the value ``'C'``
is not a member of the set (as shown previously). But if we decide
that :class:`Extra` differences are acceptible, we can add an
allowance so the test will pass:

.. tabs::

    .. group-tab:: Pytest

        Calling :meth:`allowed.extra` returns a context manager
        that allows Extra differences without triggering a test
        failure:

        .. code-block:: python
            :emphasize-lines: 11
            :lineno-start: 4

            from datatest import validate
            from datatest import allowed


            def test_using_set():
                """Check for set membership."""
                data = ['A', 'B', 'C']

                requirement = {'A', 'B'}

                with allowed.extra():
                    validate(data, requirement)

    .. group-tab:: Unittest

        Calling :meth:`self.allowedExtra() <datatest.DataTestCase.allowedExtra>`
        returns a context manager that allows Extra differences without
        triggering a test failure:

        .. code-block:: python
            :emphasize-lines: 11
            :lineno-start: 4

            import datatest


            class ExampleTests(datatest.DataTestCase):
                def test_using_set(self):
                    """Check for set membership."""
                    data = ['A', 'B', 'C']

                    requirement = {'A', 'B'}

                    with self.allowedExtra():
                        self.assertValid(data, requirement)


Datatest provides several different allowances so users can
precisely specify the criteria by which differences should be
allowed. In the following example, numeric differences are
allowed by their magnitude:

.. tabs::

    .. group-tab:: Pytest

        Calling :meth:`allowed.deviation(5) <allowed.deviation>`
        returns a context manager that allows Deviations up to
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
                with allowed.deviation(5):  # allows ±5
                    validate(data, requirement)

    .. group-tab:: Unittest

        Calling :meth:`self.allowedDeviation(5) <DataTestCase.allowedDeviation>`
        returns a context manager that allows Deviations up to
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
                    with self.allowedDeviation(5):  # allows ±5
                        self.assertValid(data, requirement)

    For a list of all possible allowances see :ref:`allowance-docs`.


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

:class:`Selector`, :class:`Query`, and :class:`Result`
    Select and query tabular data that can be tested for validity.

:class:`RepeatingContainer`
    Operate on a group of objects together instead of repeating
    the same methods and operations on each individual object
    (useful when comparing one source of data against another).
