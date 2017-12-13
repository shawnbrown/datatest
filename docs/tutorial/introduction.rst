
.. meta::
    :description: An introduction and basic examples demonstrating the
                  datatest Python package.
    :keywords: introduction, datatest


############
Introduction
############

For unittest-style validation, the :class:`DataTestCase <datatest.DataTestCase>`
extends the standard :py:class:`unittest.TestCase` with methods for asserting
validity and managing discrepancies.

The basic structure of a datatest suite mirrors that of a unittest suite:

.. code-block:: python

    import datatest


    class TestExample(datatest.DataTestCase):
        def test_one(self):
            ...

        def test_two(self):
            ...


    if __name__ == '__main__':
        datatest.main()


**********
Validation
**********

Data is validated by calling :meth:`assertValid(data, requirement)
<datatest.DataTestCase.assertValid>` to assert that *data* satisfies
the given *requirement*. The requirement's **type** determines how
the data is validated.

When *requirement* is a :py:class:`set`, the elements of data are
tested for membership in this set:

.. code-block:: python

        def test_membership_in_set(self):
            data = ['x', 'x', 'y', 'y', 'z', 'z']
            requirement = {'x', 'y', 'z'}  # <- set
            self.assertValid(data, requirement)


When *requirement* is a **function** (or other callable type), the
elements are passed to the function one at a time. When the function
returns true, an element is considered valid:

.. code-block:: python

        def test_function_returns_true(self):
            data = ['X', 'X', 'Y', 'Y']
            def requirement(x):  # <- callable (helper function)
                return x.isupper()
            self.assertValid(data, requirement)


When *requirement* is a :py:func:`compiled <re.compile>`
**regular expression**, elements are valid if they match the
given pattern:

.. code-block:: python

        def test_regex_matches(self):
            data = ['foo', 'foo', 'foo', 'bar', 'bar', 'bar']
            requirement = re.compile('^\w\w\w$')  # <- regex object
            self.assertValid(data, requirement)


When *requirement* is a string, non-container, non-callable, or
non-regex object, then elements are checked for equality:

.. code-block:: python

        def test_equality(self):
            data = ['x', 'x', 'x']
            requirement = 'x'  # <- other (not container, callable, or regex)
            self.assertValid(data, requirement)


When *requirement* is a **sequence** (list, tuple, etc.), elements are
checked for equality and order:

.. code-block:: python

        def test_order(self):
            data = ['x', 'x', 'y', 'y', 'z', 'z']
            requirement = ['x', 'x', 'y', 'y', 'z', 'z']  # <- sequence
            self.assertValid(data, requirement)


When *requirement* is a :py:class:`dict` (or other mapping), elements
of matching keys are validated according to the requirement value's
type:

.. code-block:: python

        def test_mapping(self):
            data = {'x': 'foo', 'y': 'bar'}
            requirement = {'x': 'foo', 'y': 'bar'}  # <- mapping
            self.assertValid(data, requirement)


You can run the above examples (:download:`test_validation.py
</_static/test_validation.py>`) to see this behavior yourself.

.. note::
    In the above examples, we used the variable names *data* and
    *requirement* to help explain the validation behavior. But in
    practice, it helps to use more descriptive names because these
    labels are used when reporting validation errors.


**************
Error Messages
**************

When validation fails, a :class:`ValidationError <datatest.ValidationError>`
is raised. A ValidationError contains the differences detected in the
*data* under test. To demonstrate this we will reuse tests from before,
but this time the *data* will contain invalid elements which will
trigger test case failures.

In the following test, we assert that *data* contains all of the elements
in the required set:

.. code-block:: python

    def test_membership_in_set(self):
        data = ['x', 'x2', 'y', 'y', 'z', 'z']  # <- "x2" not in required set
        required_elements = {'x', 'y', 'z'}
        self.assertValid(data, required_elements)

But this assertion fails because ``'x2'`` does not appear in the
requirement but it does appear in the data. The test fails with an
:class:`Extra <datatest.Extra>` difference:

.. code-block:: none
    :emphasize-lines: 4-6

    Traceback (most recent call last):
      File "docs/_static/test_errors.py", line 10, in test_membership_in_set
        self.assertValid(data, required_elements)
    datatest.ValidationError: does not satisfy set membership (1 difference): [
        Extra('x2'),
    ]


Here, we use a helper-function to assert that all of the elements are
uppercase:

.. code-block:: python

    def test_function_returns_true(self):
        data = ['X', 'X', 'Y', 'y']
        def uppercase(x):
            return x.isupper()
        self.assertValid(data, uppercase)

Because ``'y'`` is lower-case, the test fails with an :class:`Invalid
<datatest.Invalid>` difference:

.. code-block:: none
    :emphasize-lines: 4-6

    Traceback (most recent call last):
      File "docs/_static/test_errors.py", line 16, in test_function_returns_true
        self.assertValid(data, uppercase)
    datatest.ValidationError: does not satisfy 'uppercase' condition (1 difference): [
        Invalid('y'),
    ]


When comparing dictionaries, a dictionary of differences is raised if
validation fails:

.. code-block:: python

    def test_mapping1(self):
        data = {
            'x': 'foo',
            'y': 'BAZ',  # <- required value is 'bar'
        }
        required_values = {
            'x': 'foo',
            'y': 'bar',
        }
        self.assertValid(data, required_values)

For the key ``'y'``, the value under test is ``'BAZ'`` but the expected
value is ``'bar'``. The test fails with a dictionary of this
:class:`Invalid <datatest.Invalid>` difference:

.. code-block:: none
    :emphasize-lines: 4-6

    Traceback (most recent call last):
      File "docs/_static/test_errors.py", line 42, in test_mapping1
        self.assertValid(data, required_values)
    datatest.ValidationError: does not satisfy mapping requirement (1 difference): {
        'y': Invalid('BAZ', 'bar'),
    }


When comparing numbers, numeric deviations are raised when differences
are encountered:

.. code-block:: python

    def test_mapping2(self):
        data = {
            'x': 11,
            'y': 13,
        }
        required_values = {
            'x': 10,
            'y': 15,
        }
        self.assertValid(data, required_values)

A :class:`Deviation <datatest.Deviation>` shows the numeric difference
between the value under test and the expected value:

.. code-block:: none
    :emphasize-lines: 4-7

    Traceback (most recent call last):
      File "docs/_static/test_errors.py", line 53, in test_mapping2
        self.assertValid(data, required_values)
    datatest.ValidationError: does not satisfy mapping requirement (2 differences): {
        'x': Deviation(+1, 10),
        'y': Deviation(-2, 15),
    }


You can run the above examples (:download:`test_errors.py
</_static/test_errors.py>`) and change the values to see how differences
are handled. When running these tests, you can use the ``-f`` command
line flag to stop at the first error.


**********
Allowances
**********

It's not always possible to correct certain data errors. Sometimes,
two equally authoritative sources report different results. Sometimes,
a lack of information makes correction impossible. In any case, there
are situations where it's appropriate to allow certain discrepancies
for the purposes of data processing.

.. sidebar:: Similar Context Managers

    Allowances are similar, in concept, to the Standard Library's
    :py:func:`contextlib.suppress` and :py:meth:`TestCase.assertRaises()
    <unittest.TestCase.assertRaises>` context managers. But rather
    than acting on an error itself, allowances operate on a
    collection of difference objects.

Datatest provides allowances in the form of context managers.
Allowances operate on a ValidationError's collection of differences.
Allowing **all** of an error's differences will suppress the error
entirely. While allowing **some** of them will re-raise the error
with the remaining differences.

Revisiting the set-membership failure above, we might decide that it's
appropriate to allow :class:`Extra <datatest.Extra>` differences without
triggering a test failure. To do this, we use the :meth:`allowedExtra()
<datatest.DataTestCase.allowedExtra>` context manager:

.. code-block:: python
    :emphasize-lines: 4

    def test_membership_in_set(self):
        data = ['x', 'x2', 'y', 'y', 'z', 'z']  # <- "x2" is extra
        required_elements = {'x', 'y', 'z'}
        with self.allowedExtra():
            self.assertValid(data, required_elements)

Numeric deviations can be allowed with the
:meth:`allowedDeviation() <datatest.DataTestCase.allowedDeviation>` or
:meth:`allowedPercentDeviation() <datatest.DataTestCase.allowedPercentDeviation>`
context managers:

.. code-block:: python
    :emphasize-lines: 10

    def test_mapping2(self):
        data = {
            'x': 11,  # <- +1
            'y': 13,  # <- -2
        }
        required_values = {
            'x': 10,
            'y': 15,
        }
        with self.allowedDeviation(2):  # allows +/- 2
            self.assertValid(data, required_values)

Sometimes, statistical outliers or mismatched data create a situation
where a more-general allowance would be too broad, misleading, or
otherwise unsuitable. In cases like this, we can allow individually
specified differences with the :meth:`allowedSpecific()
<datatest.DataTestCase.allowedSpecific>` context manager.

Below for the key of ``'z'``, the value under test is ``1000``
but the required value is ``20``. While we could allow this with
``allowedDeviation(980)``, doing so is overly-vague given we are
testing values that should range from 10 to 20. A more appropriate
solution is to allow a single specified difference:

.. code-block:: python
    :emphasize-lines: 13-15,17

    def test_mapping3(self):
        data = {
            'x': 10,
            'y': 15,
            'z': 1000,
        }
        required_values = {
            'x': 10,
            'y': 15,
            'z': 20,
        }

        known_outliers = self.allowedSpecific({
            'z': Deviation(+980, 20),
        })

        with known_outliers:
            self.assertValid(data, required_values)
