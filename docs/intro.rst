
.. meta::
    :description: An introduction and basic examples demonstrating the
                  datatest Python package.
    :keywords: introduction, datatest


************
Introduction
************

.. note::

    These documents reference the current development build of
    :mod:`datatest` (|version|).

.. warning::

    As of |today|, this development build is undergoing several
    changes.  Large portions of the previous introduction have
    been temporarily removed.  A comprehensive introduction will
    be rewritten once the new features have been fully implemented.

    For now, please refer to the :doc:`unittest_style_api` for
    development build documentation.


Basic Example
=============

As an example, consider a simple file (users.csv) with the following format:

    =======  ======
    user_id  active
    =======  ======
    999      Y
    1000     Y
    1001     N
    ...      ...
    =======  ======


Here is a short script (test_users.py) to test the data in this file:

.. code-block:: python

    import datatest

    def setUpModule():
        global subject
        subject = datatest.CsvSource('users.csv')  # <- Data under test.

    class TestUserData(datatest.DataTestCase):
        def setUp(self):
            global subject
            self.subject = subject

        def test_columns(self):
            columns = self.subject.columns()
            self.assertValid(columns, {'user_id', 'active'})

        def test_user_id(self):
            def must_be_digit(x):  # <- Helper function.
                return str(x).isdigit()
            user_id = self.subject.distinct('user_id')
            self.assertValid(user_id, must_be_digit)

        def test_active(self):
            active = self.subject.distinct('active')
            self.assertValid(active, {'Y', 'N'})

    if __name__ == '__main__':
        datatest.main()


Understanding Failure Messages
==============================

When a data assertion fails, a :class:`DataError <datatest.DataError>` is
raised that contains a list of differences detected in the subject (the data
under test).  To demonstrate this, we will use the same tests shown in the
previous example but we'll check a CSV file that contains a number of data
errors---these errors will trigger test failures.

..
    NOTE: The "Understanding Failure Messages" code is the same as the
    "Basic Example" code except that the *required* argument is passed
    positionally---not as a keyword argument.  Passing arguments by
    keyword can create verbose code and since it's optional, we want to
    acclimate readers of datatest code with how tests are commonly
    written.

1. Check column names (against a set of values):
    To check the columns, we call :meth:`assertSubjectColumns(…)
    <datatest.DataTestCase.assertSubjectColumns>`.  But we detect a number of
    differences in this new file:

    .. code-block:: none
        :emphasize-lines: 3,6-9

        Traceback (most recent call last):
          File "test_users_fail.py", line 13, in test_columns
            self.assertValid(columns, {'user_id', 'active'})
        datatest.error.DataError: mandatory test failed, stopping
        early: different column names:
         Extra('USER_ID'),
         Extra('ACTIVE'),
         Missing('user_id'),
         Missing('active')

    The column names are written in uppercase but our test checks for "user_id"
    and "active" (written with lowercase letters).  So the uppercase values are
    seen as :class:`Extra <datatest.Extra>`, while the lowercase ones are
    considered :class:`Missing <datatest.Missing>`.  To correct for this, we
    convert the CSV column names to lowercase and the failure goes away.

2. Check "user_id" values (with a helper-function):
    To check the "user_id" column, we call :meth:`assertSubjectSet(…)
    <datatest.DataTestCase.assertSubjectSet>` with a helper function:

    .. code-block:: none
        :emphasize-lines: 3,5-6

        Traceback (most recent call last):
          File "test_users_fail.py", line 19, in test_user_id
            self.assertValid(user_id, must_be_digit)
        datatest.error.DataError: different 'user_id' values:
         Invalid('1056A'),
         Invalid('1099B')

    The helper function, ``must_be_digit()``, asserts that the "user_id" values
    contain only digits.  Any ID values that contain non-digit characters are
    seen as :class:`Invalid <datatest.Invalid>` (in this case, "1056A" and
    "1099B").  To correct for this, we remove the letters "A" and "B" which
    allows the test to pass.

3. Check "active" values (against a set of values):
    To check the "active" column, we call :meth:`assertSubjectSet(…)
    <datatest.DataTestCase.assertSubjectSet>` to make sure it contains
    the required values ("Y" and "N"):

    .. code-block:: none
        :emphasize-lines: 3,5-9

        Traceback (most recent call last):
          File "test_users_fail.py", line 23, in test_active
            self.assertValid(active, {'Y', 'N'})
        datatest.error.DataError: different 'active' values:
         Extra('YES'),
         Extra('NO'),
         Extra('y'),
         Extra('n'),
         Missing('N')

    Above, we see several data errors which are common when integrating
    data from multiple sources.  To correct for these errors, we convert
    "YES" to "Y", "NO" to "N", and change the remaining lowercase values
    to uppercase ("y" to "Y" and "n" to "N").  With these changes made,
    the test will pass and we can trust that our data is valid.
