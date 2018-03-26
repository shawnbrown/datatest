
.. module:: datatest

.. meta::
    :description: An overview of the "datatest" Python package, describing
                  its features and basic operation with examples.
    :keywords: introduction, datatest, examples


##################
A Tour of Datatest
##################

Datatest provides validation tools for test driven data-wrangling.
It supports both `pytest <https://pytest.org/>`_-style and
:py:mod:`unittest`-style testing conventions. Users can assert
validity and manage discrepancies using whichever framework they
choose.


**********
Validation
**********

.. tabs::

    .. group-tab:: Pytest

        The :func:`validate` function checks that the *data* under
        test satisfies a given *requirement*:

        .. code-block:: python
            :emphasize-lines: 10

            from datatest import validate


            def test_set_membership():

                data = ['A', 'B', 'A']

                requirement = {'A', 'B'}

                validate(data, requirement)


    .. group-tab:: Unittest

        The :meth:`self.assertValid() <DataTestCase.assertValid>`
        method checks that the *data* under test satisfies a given
        *requirement*:

        .. code-block:: python
            :emphasize-lines: 12

            from datatest import DataTestCase


            class MyTest(DataTestCase):

                def test_set_membership(self):

                    data = ['A', 'B', 'A']

                    requirement = {'A', 'B'}

                    self.assertValid(data, requirement)


In the example above, the requirement is a :py:class:`set`, so the data
is validated by checking for membership in this set.

The requirement's type determines how the data is validated---changing
the type will change the method of validation.

When *requirement* is a function, data is valid when the function
returns True. When *requirement* is a regular expression pattern, data
is valid when it matches the given pattern. For a complete list of
available types and behaviors, see :ref:`predicate-docs`.

A few examples follow:


.. tabs::

    .. group-tab:: Pytest

        .. code-block:: python

            from datatest import validate

            ...

            def test_using_function():
                """Check that function returns True."""
                data = [2, 4, 6]

                def iseven(x):
                    return x % 2 == 0

                validate(data, iseven)


            def test_using_type():
                """Check that values are of the given type."""
                data = [0.0, 1.0, 2.0]
                validate(data, float)


            def test_using_regex():
                """Check that values match the given pattern."""
                data = ['bake', 'cake', 'bake']
                regex = re.compile('[bc]ake')
                validate(data, regex)

            ...

        You can download the full set of examples
        (:download:`test_intro1.py </_static/test_intro1.py>`)
        and run them with the following command:

        .. code-block:: none

            pytest test_intro1.py

    .. group-tab:: Unittest

        .. code-block:: python

            from datatest import DataTestCase


            class MyTests(DataTestCase):

                ...

                def test_using_function(self):
                    """Check that function returns True."""
                    data = [2, 4, 6]

                    def iseven(x):
                        return x % 2 == 0

                    self.assertValid(data, iseven)

                def test_using_type(self):
                    """Check that values are of the given type."""
                    data = [0.0, 1.0, 2.0]
                    self.assertValid(data, float)

                def test_using_regex(self):
                    """Check that values match the given pattern."""
                    data = ['bake', 'cake', 'bake']
                    regex = re.compile('[bc]ake')
                    self.assertValid(data, regex)

                ...

        You can download the full set of examples
        (:download:`test_intro1unit.py </_static/test_intro1unit.py>`)
        and run them with the following command:

        .. code-block:: none

            python -m datatest test_intro1unit.py


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

        .. code-block:: python

            from datatest import validate


            def test_set_membership():

                data = ['A', 'B', 'C']

                requirement = {'A', 'B'}

                validate(data, requirement)


        The test fails with the following message:

        .. code-block:: none
            :emphasize-lines: 10-12

            _____________________________ test_set_membership ______________________________

                def test_set_membership():

                    data = ['A', 'B', 'C']

                    requirement = {'A', 'B'}

            >       validate(data, required_elements)
            E       ValidationError: does not satisfy set membership (1 difference): [
                        Extra('C'),
                    ]

            test_example.py:11: ValidationError


    .. group-tab:: Unittest

        .. code-block:: python

            from datatest import DataTestCase


            class MyTest(DataTestCase):

                def test_set_membership(self):

                    data = ['A', 'B', 'C']

                    requirement = {'A', 'B'}

                    self.assertValid(data, requirement)


        The test fails with the following message:

        .. code-block:: none
            :emphasize-lines: 7-9

            ======================================================================
            FAIL: test_set_membership (test_unittesting.MyTest)
            ----------------------------------------------------------------------
            Traceback (most recent call last):
              File "/my/projects/folder/test_example.py", line 12, in test_set_membership
                self.assertValid(data, requirement)
            datatest.ValidationError: does not satisfy set membership (1 difference): [
                Extra('C'),
            ]

The error above included an :class:`Extra` difference but other
validation methods (determined by the *requirement* type) can give
other difference types.

Difference objects describe each invalid element and can
be one of of four types: :class:`Missing`, :class:`Extra`,
:class:`Deviation` or :class:`Invalid`.

In the following examples, a failed tuple comparison raises
an :class:`Invalid` difference and failed numeric comparisons
raise :class:`Deviation` differences:

.. tabs::

    .. group-tab:: Pytest

        .. code-block:: none
            :emphasize-lines: 12-14,32-36

            ...

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

            test_intro2.py:49: ValidationError
            _______________________________ test_using_dict ________________________________

                def test_using_dict():
                    """Check that values satisfy requirements of matching keys."""
                    data = {
                        'A': 101,
                        'B': 205,
                        'C': 297,
                    }
                    requirement = {
                        'A': 100,
                        'B': 200,
                        'C': 300,
                    }
            >       validate(data, requirement)
            E       ValidationError: does not satisfy mapping requirement (3 differences): {
                        'A': Deviation(+1, 100),
                        'B': Deviation(+5, 200),
                        'C': Deviation(-3, 300),
                    }

            test_intro2.py:64: ValidationError

            ...

        You can download a collection of example failures
        (:download:`test_intro2.py </_static/test_intro2.py>`)
        and run them with the following command:

        .. code-block:: none

            pytest test_intro2.py

    .. group-tab:: Unittest

        .. code-block:: none
            :emphasize-lines: 10-12,21-25

            ...

            ======================================================================
            FAIL: test_using_tuple (test_intro2unit.ExampleTests)
            Check that tuples of values satisfy corresponding tuple of
            ----------------------------------------------------------------------
            Traceback (most recent call last):
              File "/my/projects/folder/test_intro2unit.py", line 45, in test_using_tuple
                self.assertValid(data, requirement)
            datatest.ValidationError: does not satisfy requirement (1 difference): [
                Invalid(('A', 2)),
            ]

            ======================================================================
            FAIL: test_using_dict (test_intro2unit.ExampleTests)
            Check that values satisfy requirements of matching keys.
            ----------------------------------------------------------------------
            Traceback (most recent call last):
              File "/my/projects/folder/test_intro2unit.py", line 59, in test_using_dict
                self.assertValid(data, requirement)
            datatest.ValidationError: does not satisfy mapping requirement (3 differences): {
                'A': Deviation(+1, 100),
                'B': Deviation(+5, 200),
                'C': Deviation(-3, 300),
            }

            ...

        You can download a collection of example failures
        (:download:`test_intro2unit.py </_static/test_intro2unit.py>`)
        and run them with the following command:

        .. code-block:: none

            python -m datatest test_intro2unit.py


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

            from datatest import validate
            from datatest import allowed


            def test_set_membership():

                data = ['A', 'B', 'C']

                requirement = {'A', 'B'}

                with allowed.extra():
                    validate(data, requirement)

    .. group-tab:: Unittest

        Calling :meth:`self.allowedExtra() <datatest.DataTestCase.allowedExtra>`
        returns a context manager that allows Extra differences without
        triggering a test failure:

        .. code-block:: python
            :emphasize-lines: 12

            from datatest import DataTestCase


            class MyTest(DataTestCase):

                def test_set_membership(self):

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
            :emphasize-lines: 18

            from datatest import validate
            from datatest import allowed

            ...

            def test_using_dict():
                """Check that values satisfy requirements of matching keys."""
                data = {
                    'A': 101,
                    'B': 205,
                    'C': 297,
                }
                requirement = {
                    'A': 100,
                    'B': 200,
                    'C': 300,
                }
                with allowed.deviation(5):  # allows ±5
                    validate(data, requirement)

            ...

        For a list of all possible allowances see :ref:`allowance-docs`.


    .. group-tab:: Unittest

        Calling :meth:`self.allowedDeviation(5) <DataTestCase.allowedDeviation>`
        returns a context manager that allows Deviations up to
        plus-or-minus five without triggering a test failure:

        .. code-block:: python
            :emphasize-lines: 20

            from datatest import DataTestCase


            class MyTests(DataTestCase):

                ...

                def test_using_dict(self):
                    """Check that values satisfy requirements of matching keys."""
                    data = {
                        'A': 101,
                        'B': 205,
                        'C': 297,
                    }
                    requirement = {
                        'A': 100,
                        'B': 200,
                        'C': 300,
                    }
                    with self.allowedDeviation(5):  # allows ±5
                        self.assertValid(data, required_values)

                ...

        For a list of all possible allowances see
        :meth:`allowance methods <datatest.DataTestCase.allowedMissing>`.


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
