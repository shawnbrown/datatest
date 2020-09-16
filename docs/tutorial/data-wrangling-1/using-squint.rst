
.. meta::
    :description: Test-driven data preparation can provide much-needed
                  structure to guide the workflow of data preparation,
                  itself.
    :keywords: tidy data, data cleansing


#######################################
Tidying a File (a Test Driven Approach)
#######################################

This example will demonstrate how datatest can structure the
data-wrangling process. We will take a messy CSV file and---using
a test driven approach---iteratively step through the data and make
corrections. When we're finished, the file will contain tidy data
in the following format:

    =======  ======
    user_id  active
    =======  ======
    0999F    Y
    1000C    Y
    1001C    N
    ...      ...
    =======  ======


*****************
Files to Download
*****************

To follow along and perform these steps yourself, download the
following files:

.. tabs::

    .. group-tab:: Pytest

        * **Test Script:** :download:`test_users.py </_static/test_users.py>`
        * **Messy CSV File:** :download:`users.csv </_static/users.csv>`

    .. group-tab:: Unittest

        * **Test Script:** :download:`test_users_unit.py </_static/test_users_unit.py>`
        * **Messy CSV File:** :download:`users.csv </_static/users.csv>`


*****************
Running the Tests
*****************

To help direct our work, we will stop at the first test failure
rather than running all of the tests at once. After addressing
the failing test, we will re-run our test script and move on to
the next failure. Throughout the process, we will run and re-run
our test script multiple times.

.. tabs::

    .. group-tab:: Pytest

        Use the following command to run tests during this process:

        .. code-block:: none

            pytest -x test_users.py

        The ``-x`` option stops pytest on the first error or failed test.


    .. group-tab:: Unittest

        Use the following command to run tests during this process:

        .. code-block:: none

            python -m datatest -f test_users_unit.py

        The unittest-style ``-f`` option stops the test runner on the
        first failure or error.


************************
Step-by-Step Explanation
************************

0. Define Fixture
=================

Test "fixtures" are objects or processes that help set up the
prerequesites needed to run our tests. They can also manage any
clean-up needed after we are finished testing.

For this example, the script defines a :class:`Select` object
containing data from the **users.csv** file as our fixture:

.. tabs::

    .. group-tab:: Pytest

        .. literalinclude:: /_static/test_users.py
            :pyobject: users
            :lineno-match:


    .. group-tab:: Unittest

        .. literalinclude:: /_static/test_users_unit.py
            :pyobject: setUpModule
            :lineno-match:


1. Check Column Names
=====================

To check the column names of our file we will compare the :attr:`fieldnames
<Select.fieldnames>` property against a :py:class:`set` of required names:

.. tabs::

    .. group-tab:: Pytest

        .. literalinclude:: /_static/test_users.py
            :pyobject: test_columns
            :lineno-match:


        When running the script, the test above raises the following failure:

        .. code-block:: none
            :emphasize-lines: 11-14

            _________________________________ test_columns _________________________________

            users = <datatest.Select object at 0x7fdca2983c18>
            Data from 1 source:
             users.csv

                @pytest.mark.mandatory
                def test_columns(users):
            >       validate(users.fieldnames, {'user_id', 'active'})
            E       ValidationError: does not satisfy set membership (4 differences): [
                        Extra('ACTIVE'),
                        Extra('USER_ID'),
                        Missing('active'),
                        Missing('user_id'),
                    ]

            test_users.py:15: ValidationError


    .. group-tab:: Unittest

        .. literalinclude:: /_static/test_users_unit.py
            :pyobject: TestUserData.test_columns
            :lineno-match:


        When running the script, the test above raises the following failure:

        .. code-block:: none
            :emphasize-lines: 8-11

            ======================================================================
            FAIL: test_columns (test_users_unit.TestUserData)
            ----------------------------------------------------------------------
            Traceback (most recent call last):
              File "test_users_unit.py", line 17, in test_columns
                self.assertValid(users.fieldnames, {'user_id', 'active'})
            ValidationError: does not satisfy set membership (4 differences): [
                Extra('ACTIVE'),
                Extra('USER_ID'),
                Missing('active'),
                Missing('user_id'),
            ]

Our test checks for "user_id" and "active" (written in lowercase
letters) but the column names in the file are uppercase. Since the
uppercase names are not expected, they are considered :class:`Extra`
and since the lowercase names are expected but absent, they are
considered :class:`Missing`.

To correct for this, we convert the CSV column names to lowercase
using our data manipulation tool of choice (e.g., a spreadsheet
program, Pandas, etc.). After correcting the column names, we can
re-run our script to see that this test now passes and we can move
on to the next failing test.


2. Check "user_id" Column
=========================

For the "user_id" field, we will check for a custom format---some
digits followed by one uppercase letter (e.g., ``'1056A'``). When
a value uses a required format it is said to be "well-formed". We
will define a helper function that returns ``True`` for well-formed
values and ``False`` for malformed values.

.. tabs::

    .. group-tab:: Pytest

        .. literalinclude:: /_static/test_users.py
            :pyobject: test_user_id
            :lineno-match:


        The test above raises the following failure:

        .. code-block:: none
            :emphasize-lines: 14-15

            _________________________________ test_user_id _________________________________

            users = <datatest.Select object at 0x7f45031b02e8>
            Data from 1 source:
             users.csv

                def test_user_id(users):

                    def is_wellformed(x):  # <- Helper function.
                        return x[:-1].isdigit() and x[-1:].isupper()

            >       validate(users('user_id'), is_wellformed)
            E       ValidationError: does not satisfy 'is_wellformed' (2 differences): [
                        Invalid('1056a'),
                        Invalid('1099b'),
                    ]

            test_users.py:23: ValidationError


    .. group-tab:: Unittest

        .. literalinclude:: /_static/test_users_unit.py
            :pyobject: TestUserData.test_user_id
            :lineno-match:


        The test above raises the following failure:

        .. code-block:: none
            :emphasize-lines: 8-9

            ======================================================================
            FAIL: test_user_id (test_users_unit.TestUserData)
            ----------------------------------------------------------------------
            Traceback (most recent call last):
              File "test_users_unit.py", line 24, in test_user_id
                self.assertValid(users('user_id'), is_wellformed)
            ValidationError: does not satisfy 'is_wellformed' (2 differences): [
                Invalid('1056a'),
                Invalid('1099b'),
            ]

In the "user_id" column there are two malformed values. To correct
these errors we can open the CSV file (e.g., in a spreadsheet program)
and change ``'1056a'`` to ``'1056A'`` and ``'1099b'`` to ``'1099B'``.
After resaving the file, we can re-run the script and confirm that this
test passes before moving on to the next failure.


3. Check "active" Column
========================

For the "active" field, we will check that it contains the values
``'Y'`` and ``'N'``:


.. tabs::

    .. group-tab:: Pytest

        .. literalinclude:: /_static/test_users.py
            :pyobject: test_active
            :lineno-match:


        The test above raises the following failure:

        .. code-block:: none
            :emphasize-lines: 10-14

            _________________________________ test_active __________________________________

            users = <datatest.Select object at 0x7f1ec781a2e8>
            Data from 1 source:
             users.csv

                def test_active(users):
            >       validate(users({'active'}), {'Y', 'N'})
            E       ValidationError: does not satisfy set membership (5 differences): [
                        Missing('N'),
                        Extra('NO'),
                        Extra('YES'),
                        Extra('n'),
                        Extra('y'),
                    ]

            test_users.py:27: ValidationError


    .. group-tab:: Unittest

        .. literalinclude:: /_static/test_users_unit.py
            :pyobject: TestUserData.test_active
            :lineno-match:


        The test above raises the following failure:

        .. code-block:: none
            :emphasize-lines: 8-12

            ======================================================================
            FAIL: test_active (test_users_unit.TestUserData)
            ----------------------------------------------------------------------
            Traceback (most recent call last):
              File "test_users_unit.py", line 27, in test_active
                self.assertValid(users({'active'}), {'Y', 'N'})
            ValidationError: does not satisfy set membership (5 differences): [
                Missing('N'),
                Extra('NO'),
                Extra('YES'),
                Extra('n'),
                Extra('y'),
            ]

Above, we see several data errors which are common when integrating
data from multiple sources. To correct for these errors, we change
``'YES'`` to ``'Y'``, ``'NO'`` to ``'N'``, and convert the remaining
lowercase values to uppercase (``'y'`` to ``'Y'`` and ``'n'`` to
``'N'``). With these changes made, the test will pass and we can
trust that our data meets the specified requirements.


***********************
Save Tests to Run Later
***********************

Once the data has been prepared and validated, it can be useful
to keep the test script and data file together for future use.
If the file is ever altered or appended to, you can simply re-run
the script to make sure the data is still valid. And if someone
else needs to independently verify the data, they can review the
test script and run it themselves to make sure the tidying process
has been completed.

