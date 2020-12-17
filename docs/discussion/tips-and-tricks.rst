
.. currentmodule:: datatest

.. meta::
    :description: Tips and tricks for better testing with datatest.
    :keywords: data, testing, tips, fixture


################################
Tips and Tricks for Data Testing
################################

This document is intended for users who are already familiar with
datatest and its features. It's a grab-bag of ideas and patterns
you can use in your own code.


Using methodcaller()
====================

It's common to have helper functions that simply call a method
on an object. For example:

.. code-block:: python
    :linenos:

    from datatest import validate

    data = [...]

    def is_upper(x):  # <- Helper function.
        return x.isupper()

    validate(data, is_upper)


In the case above, our helper function calls the ``isupper()``
method. But instead of defining a function for this, we can
simply use :py:func:`operator.methodcaller`:

.. code-block:: python
    :emphasize-lines: 5
    :linenos:

    from datatest import validate
    from operator import methodcaller

    data = [...]
    validate(data, methodcaller('isupper'))


RepeatingContainer and Argument Unpacking
=========================================

The :class:`RepeatingContainer` class is useful for comparing
similarly shaped data sources:

.. code-block:: python
    :linenos:

    from datatest import validate, working_directory
    import pandas as pd

    with working_directory(__file__):
        compare = RepeatingContainer([
            pd.read_csv('data_under_test.csv'),
            pd.read_csv('reference_data.csv'),
        ])


You can use *iterable unpacking* to get the individual results
for validation:

.. code-block:: python
    :linenos:
    :lineno-start: 8

    ...

    result = compare[['A', 'C']].groupby('A').sum()
    data, requirement = result  # Unpack result items.

    dt.validate(data, requirement)


But you can make this even more succinct by unpacking the arguments
directly inside the :func:`validate` call itself---via the asterisk
prefix, ``*``:

.. code-block:: python
    :emphasize-lines: 3
    :linenos:
    :lineno-start: 8

    ...

    validate(*compare[['A', 'C']].groupby('A').sum())


Failure Message Handling
========================

If validation fails and you've provided a *msg* argument, its
value is used in the error message. But if no *msg* is given,
then :func:`validate` will automatically generate its own message.

This example includes a *msg* value so the error message reads
``Values should be even numbers.``:

.. code-block:: python
    :linenos:

    from datatest import validate

    data = [2, 4, 5, 6, 8, 10, 11]

    def is_even(x):
        """Should be even."""
        return x % 2 == 0

    msg = 'Values should be even numbers.'
    validate(data, is_even, msg=msg)

.. code-block:: none
    :emphasize-lines: 4

    Traceback (most recent call last):
      File "example.py", line 10, in <module>
        validate(data, is_even, msg=msg)
    datatest.ValidationError: Values should be even numbers. (2 differences): [
        Invalid(5),
        Invalid(11),
    ]


1. Docstring Message
--------------------

If validation fails but no *msg* was given, then the first line of the
*requirement*'s :term:`python:docstring` is used. For this reason, it's
useful to start your docstrings with *normative* language, e.g., "must
be...", "should have...", "needs to...", "requires...", etc.

In the following example, the docstring ``Should be even.`` is used in
the error:

.. code-block:: python
    :linenos:

    from datatest import validate

    def is_even(x):
        """Should be even."""
        return x % 2 == 0

    data = [2, 4, 5, 6, 8, 10, 11]
    validate(data, is_even)

.. code-block:: none
    :emphasize-lines: 4

    Traceback (most recent call last):
      File "example.py", line 8, in <module>
        validate(data, is_even)
    datatest.ValidationError: Should be even. (2 differences): [
        Invalid(5),
        Invalid(11),
    ]


2. __name__ Message
-------------------

If validation fails but there's no *msg* and no docstring, then the
*requirement*'s :py:attr:`__name__ <python:definition.__name__>` will
be used to construct a message.

In this example, the function's name, ``is_even``, is used in the error:

.. code-block:: python
    :linenos:

    from datatest import validate

    def is_even(x):
        return x % 2 == 0

    data = [2, 4, 5, 6, 8, 10, 11]
    validate(data, is_even)

.. code-block:: none
    :emphasize-lines: 4

    Traceback (most recent call last):
      File "example.py", line 7, in <module>
        validate(data, is_even)
    datatest.ValidationError: does not satisfy is_even() (2 differences): [
        Invalid(5),
        Invalid(11),
    ]


3. __repr__() Message
---------------------

If validation fails but there's no *msg*, no docstring, and no
``__name__``, then the *requirement*'s representation is used
(i.e., the result of its :meth:`__repr__() <object.__repr__>`
method).


Template Tests
==============

If you need to integrate multiple published datasets, you might want to
prepare a template test suite. The template can serve as a starting point
for validating each datatset. In the template scripts, you can prompt
users for action by explicitly failing with an instruction message:

.. tabs::

    .. group-tab:: pytest

        We can use :func:`pytest.fail` to fail with a message to the user:

        .. code-block:: python
            :emphasize-lines: 4
            :linenos:
            :lineno-start: 21

            ...

            def test_state(data):
                pytest.fail('Set requirement to appropriate state abbreviation.')
                validate(data['state'], requirement='XX')


        .. code-block:: none

            =================================== FAILURES ===================================
            __________________________________ test_state __________________________________

                def test_state(data):
            >       pytest.fail('Set requirement to appropriate state abbreviation.')
            E       Failed: Set requirement to appropriate state abbreviation.

            example.py:24: Failed
            =========================== short test summary info ============================
            FAILED example.py::test_state - Failed: Set requirement to appropriate state...
            ========================= 1 failed, 41 passed in 0.14s =========================


        When you see this failure, you can remove the ``pytest.fail()``
        line and add the needed state abbreviation:

        .. code-block:: python
            :linenos:
            :lineno-start: 21

            ...

            def test_state(data):
                validate(data['state'], requirement='CA')

    .. group-tab:: unittest

        We can use :meth:`TestCase.fail() <unittest.TestCase.fail>` to
        fail with a message to the user (``DataTestCase`` inherits from
        ``unittest.TestCase`` and has access to all of its parent's
        methods):

        .. code-block:: python
            :emphasize-lines: 5
            :linenos:
            :lineno-start: 21

            ...

            class MyTest(DataTestCase):
                def test_state(self):
                    self.fail('Set requirement to appropriate state abbreviation.')
                    self.assertValid(self.data['state'], requirement='XX')

        .. code-block:: none

            ======================================================================
            FAIL: test_state (example.MyTest)
            ----------------------------------------------------------------------
            Traceback (most recent call last):
              File "example.py", line 25, in test_state
                self.fail('Set requirement to appropriate state abbreviation.')
            AssertionError: Set requirement to appropriate state abbreviation.

            ----------------------------------------------------------------------
            Ran 42 tests in 0.130s

            FAILED (failures=1)


        When you see this failure, you can remove the ``self.fail()``
        line and add the needed state abbreviation:

        .. code-block:: python
            :linenos:
            :lineno-start: 21

            ...

            class MyTest(DataTestCase):
                def test_state(self):
                    self.assertValid(self.data['state'], requirement='CA')


Using a Function Factory
========================

If you find yourself writing multiple helper functions that perform
similar actions, consider writing a *function factory* instead. A
function factory is a function that makes other functions.

.. tabs::

    .. group-tab:: Using a Factory

        In the following example, the ``ends_with()`` function makes helper
        functions:

        .. code-block:: python
            :linenos:

            from datatest import validate

            def ends_with(suffix):  # <- Helper function factory.
                suffix = suffix.lower()
                def helper(x):
                    return x.lower().endswith(suffix)
                helper.__doc__ = f'should end with {suffix!r}'
                return helper

            data1 = [...]
            validate(data1, ends_with('.csv'))

            data2 = [...]
            validate(data2, ends_with('.txt'))

            data3 = [...]
            validate(data3, ends_with('.ini'))

    .. group-tab:: No Factory

        Instead of a factory, this example uses separate helper functions:

        .. code-block:: python
            :linenos:

            from datatest import validate

            def ends_with_csv(x):  # <- Helper function.
                """should end with '.csv'"""
                return x.lower().endswith('.csv')

            def ends_with_txt(x):  # <- Helper function.
                """should end with '.txt'"""
                return x.lower().endswith('.txt')

            def ends_with_ini(x):  # <- Helper function.
                """should end with '.ini'"""
                return x.lower().endswith('.ini')

            data1 = [...]
            validate(data1, ends_with_csv)

            data2 = [...]
            validate(data2, ends_with_txt)

            data3 = [...]
            validate(data3, ends_with_ini)


Lambda Expressions
==================

It's common to use simple helper functions like the one below:

.. code-block:: python
    :linenos:

    from datatest import validate

    def is_even(n):  # <- Helper function.
        return n % 2 == 0

    data = [...]
    validate(data, is_even)


If your helper function is a single statement, you could also
write it as a :term:`lambda expression <python:lambda>`:

.. code-block:: python
    :emphasize-lines: 4
    :linenos:

    from datatest import validate

    data = [...]
    validate(data, lambda n: n % 2 == 0)


But you should be careful with lambdas because they don't have names or
docstrings. If the validation fails without an explicit *msg* value, the
default message can't provide any useful context---it would read "does
not satisfy <lambda>".

So if you use a lambda, it's good practice to provide a *msg* argument,
too:

.. code-block:: python
    :emphasize-lines: 4
    :linenos:

    from datatest import validate

    data = [...]
    validate(data, lambda n: n % 2 == 0, msg='shoud be even')


Skip Missing Test Fixtures (pytest)
===================================

Usually, you want a test to fail if a required fixture is unavailable.
But in some cases, you may want to skip tests that rely on one fixture
while continuing to run tests that rely on other fixtures.

To do this, you can call :func:`pytest.skip` from within the fixture
itself. Tests that rely on this fixture will be automatically skipped
when the data source is unavailable:

.. code-block:: python
    :emphasize-lines: 12
    :linenos:

    import pytest
    import pandas as pd
    from datatest import working_directory

    @pytest.fixture(scope='module')
    @working_directory(__file__)
    def data_source1():
        file_path = 'data_source1.csv'
        try:
            return pd.read_csv(file_path)
        except FileNotFoundError:
            pytest.skip(f'cannot find {file_path}')

    ...


Test Configuration With conftest.py (pytest)
============================================

To share the same fixture with multiple test modules, you can move the
fixture function into a separate file named ``conftest.py``. See more
from the pytest docs: :ref:`Sharing Fixture Functions <pytest:conftest>`.


..
    POSSIBLE FUTURE ADDITIONS

    Give Yourself More Context
        Dictionary Comparison
        Wildcards

    Acceptances with wildcards.

    Parametrized acceptances (pytest).

    Load DataFrames with 'str' dtypes to prevent type inference from hiding
    potential errors.

    Discuss versions of unittest and addModuleCleanup?

    If tests could damage data, add second fixture to make a deepcopy.

    Adding extra command line options when calling main():

        if __name__ == '__main__':
            import sys
            sys.exit(pytest.main(sys.argv + ['-v', '-n', '1', '-s']))
